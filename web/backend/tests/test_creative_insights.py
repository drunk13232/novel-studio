"""Narrative signal and reader-profile checks with isolated files.

Deterministic calculations execute locally. Inference uses an explicitly marked
capture adapter; no real model, personal project or credential is accessed.
"""
import asyncio,copy,json,re,threading
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.errors import ConsoleError
from app.library.storage import digest,write,safe
from app.studio_tools import StudioTools,normalized,utf16_slice,utf16_index
from app.creative.creative_insights import CreativeInsights,routes
from app.creative.insight_models import CurveAnalyze,CurveOverride,CurveSettings,PersonaSave,PersonaRemove,ReaderPrepare,ReaderApprove,ReaderNext,ReaderRetry
from app.creative.reviews import ReviewCenter,Start
from app.creative.narrative_curve import signals

class CaptureTask:
    def __init__(self,id,prompt,complete):self.id=id;self.prompt=prompt;self.complete=complete;self.status='QUEUED';self.error=None;self.result=None;self.private_text=False
    def public(self):return {'id':self.id,'status':self.status,'error':self.error,'result':self.result}

class CaptureManager:
    def __init__(self):self.tasks={}
    def prepared(self,*args,**kw):
        task=CaptureTask('mock_'+str(len(self.tasks)),args[1],args[5]);self.tasks[task.id]=task;return task
    def get(self,id):
        if id not in self.tasks:raise ConsoleError('task missing',404)
        return self.tasks[id]
    async def cancel(self,id):self.get(id).status='CANCELLED'
    def finish(self,id,output):
        task=self.get(id);task.result=task.complete(json.dumps(output,ensure_ascii=False));task.status='SUCCEEDED';return task.result

@pytest.fixture
def lab(tmp_path,monkeypatch):
    roots={};cards=[]
    for n in range(1,5):cards.append({'id':'chapter_'+str(n),'number':n,'title':'隔离章节'+str(n),'volume':'v1' if n<3 else 'v2','order':n,'kind':'chapter','draft':f'chapters/chapter-{n}/draft.txt','final':None})
    for project in ['p1','p2']:
        root=tmp_path/project;root.mkdir();roots[project]=root
        for row in cards:
            file=root/row['draft'];file.parent.mkdir(parents=True);file.write_text('# 章节标题\n😀小岚遇到危险，听见枪声。她感到恐惧，又看见希望。\n“我们不能放弃。”',encoding='utf8')
        for folder in ['state','settings','characters','bible']:
            (root/folder).mkdir();(root/folder/'protected.yaml').write_text('secret: AUTHOR_PRIVATE_FIXTURE\n',encoding='utf8')
    manifests={p:{'title':'隔离测试作品','writing':{'form':'novel'}} for p in roots};counts={'body_reads':0}
    def checked(p):
        if p not in roots:raise ConsoleError('foreign project',404)
        return roots[p]
    def content(p,path):
        counts['body_reads']+=1;file=safe(checked(p),path)
        if not file.is_file():raise ConsoleError('missing manuscript',404)
        raw=file.read_bytes();text=raw.decode('utf8');return {'path':path,'content':text,'line_ending':'CRLF' if '\r\n' in text else 'LF','etag':digest(raw)}
    workspaces={p:SimpleNamespace(root=root,_save_lock=threading.RLock(),content=lambda path,p=p:content(p,path)) for p,root in roots.items()}
    def catalog(p,**kw):checked(p);assert kw.get('include_auxiliary') is False;assert kw.get('include_text_counts') is False;return {'chapters':copy.deepcopy(cards)}
    registry=SimpleNamespace(engine=tmp_path/'isolated-engine',get=lambda p:copy.deepcopy(manifests[p]) if p in manifests else checked(p),workspace=lambda p:workspaces[p] if p in workspaces else checked(p),book_center=SimpleNamespace(catalog=catalog))
    planning=SimpleNamespace(rows=lambda p,kind:copy.deepcopy(cards if kind=='chapter' else []))
    characters=SimpleNamespace(writable=lambda p:workspaces[p] if p in workspaces else checked(p))
    tools=StudioTools(registry,planning,characters,None,None,tmp_path/'config')
    matrix_state={'chapters':cards,'tracks':[],'derived_tracks':[],'characters':{'hero':'小岚'}}
    matrix=SimpleNamespace(get=lambda p:copy.deepcopy(matrix_state))
    model_config={'temperature':0.5,'model':'test::modelA'}
    class Params:
        max_output_tokens=2000
        def model_dump(self):return {'max_output_tokens':self.max_output_tokens,'temperature':model_config['temperature']}
    provider=SimpleNamespace(provider_id='test',display_name='Isolated model stub',base_url='https://not-contacted.invalid/v1')
    model=SimpleNamespace(id='modelA',display_name='Captured test model',protocol='chat_completions',parameters=Params(),context_length=128000,output_limit=4000,capabilities={},input_price=1.,output_price=2.,currency='USD')
    def controls(p,task,model=None):
        checked(p);ref=model or model_config['model'];return SimpleNamespace(model=ref,parameters={},context=SimpleNamespace(output_reserve=2000),model_dump=lambda:{'model':ref,'temperature':model_config['temperature']})
    def choose(p,task,ref):
        checked(p)
        if ref=='offline':raise ConsoleError('configured provider unavailable',503)
        return (None,None) if ref=='codex' else (provider,model)
    center=SimpleNamespace(controls_for=controls,choose=choose)
    manager=CaptureManager();reviews=ReviewCenter(registry,characters,tools,None,center,lambda p:manager,None)
    reviews.techniques=lambda *a:('Isolated existing reviewer contract.',[])
    monkeypatch.setattr('app.creative.reviews.adapter',lambda *a,**kw:SimpleNamespace(selected_ai={'backend':'MOCK_VALIDATION_NOT_REAL_AI','model':'captured'}))
    service=CreativeInsights(tools,matrix,reviews)
    return SimpleNamespace(service=service,curve=service.curve,readers=service.readers,reviews=reviews,tools=tools,roots=roots,root=roots['p1'],cards=cards,manifests=manifests,matrix=matrix_state,counts=counts,manager=manager,config=model_config)

def analyze(lab,**kwargs):return lab.curve.analyze('p1',CurveAnalyze(**({'whole_book':True}|kwargs)))
def persona(lab,name='悬疑读者'):
    row=lab.readers.save('p1',PersonaSave(etag=lab.readers.index('p1')['etag'],persona={'name':name,'age_group':'成人（假设）','preferences':'喜欢有依据的悬念','abandonment_triggers':'连续不交代基本目标','payment_willingness':'仅为假设，不推断真实付费','focus':'suspense'}))
    return next(profile for profile in row['profiles'] if profile['name']==name)
def prepare(lab,profiles=None,**kwargs):
    profiles=profiles or [persona(lab)];return lab.readers.prepare('p1',ReaderPrepare(persona_ids=[p['id'] for p in profiles],**({'whole_book':True,'model':'test::modelA'}|kwargs)))
def approve(lab,panel):return lab.readers.approve('p1',panel['id'],ReaderApprove(etag=panel['etag'],preview_hash=panel['preview_hash'],confirm=True))
def next_(lab,panel):return asyncio.run(lab.readers.next('p1',panel['id'],ReaderNext(etag=panel['etag'],confirm=True)))
def point(state,id='chapter_1',series='book'):return next(p for p in state['points'] if p['chapter_id']==id and p['series_id']==series)
def protected(root):return {str(p.relative_to(root)):p.read_bytes() for folder in ['chapters','state','settings','characters','bible'] for p in (root/folder).rglob('*') if p.is_file()}

def test_local_curve_exact_evidence_cache_and_private_files_unchanged(lab):
    before=protected(lab.root);initial=lab.curve.index('p1');assert not lab.counts['body_reads'];assert point(initial)['tension'] is None
    state=analyze(lab);assert 0<=point(state)['tension']<=10;assert 0<=point(state)['emotion']<=10
    for evidence in point(state)['evidence']:
        text=normalized(lab.tools.doc('p1',evidence['path']));assert utf16_slice(text,evidence['start'],evidence['end'])==evidence['quote'];assert evidence['current'] and evidence['document_revision']
    reads=lab.counts['body_reads'];analyze(lab);assert lab.counts['body_reads']==reads
    assert before==protected(lab.root);assert not lab.manager.tasks
    assert (lab.root/'metadata/studio/narrative-curve.json').exists()

def test_unknown_stays_null_and_author_overrides_version_bound(lab):
    file=lab.root/lab.cards[0]['draft'];file.write_text('月亮挂在屋顶，钟表指向六点。','utf8');state=analyze(lab)
    assert point(state)['status']=='INSUFFICIENT_SIGNALS' and point(state)['tension'] is None
    state=lab.curve.override('p1',CurveOverride(etag=state['etag'],chapter_id='chapter_1',tension=7.5,emotion=4,note='作者认为此处有潜在冲突'))
    assert point(state)['tension']==7.5 and point(state)['local_tension'] is None and point(state)['override_current']
    reopened=type(lab.curve)(lab.tools,lab.curve.matrix).index('p1');assert point(reopened)['override']['note'].startswith('作者')
    file.write_text('月亮换了位置。','utf8');stale=lab.curve.index('p1');assert point(stale)['tension'] is None and not point(stale)['override_current']
    with pytest.raises(ConsoleError):lab.curve.override('p1',CurveOverride(etag=stale['etag'],chapter_id='chapter_1',tension=8))
    clean=lab.curve.override('p1',CurveOverride(etag=stale['etag'],chapter_id='chapter_1',clear=True));assert point(clean)['override'] is None

def test_flat_spans_strict_threshold_unknown_break_and_cross_volume(lab):
    state=analyze(lab)
    for n in range(1,5):state=lab.curve.override('p1',CurveOverride(etag=state['etag'],chapter_id='chapter_'+str(n),tension=2,note='作者判断'))
    state=lab.curve.settings('p1',CurveSettings(etag=state['etag'],flat_count=3,flat_threshold=2));assert not state['flat_spans']
    state=lab.curve.settings('p1',CurveSettings(etag=state['etag'],flat_count=3,flat_threshold=3));assert state['flat_spans'][0]['chapter_ids']==[c['id'] for c in lab.cards]
    (lab.root/lab.cards[1]['draft']).write_text('无信号的描写。','utf8');state=analyze(lab);assert not state['flat_spans'];assert not point(state,'chapter_2')['override_current']

def test_plans_are_not_observed_and_character_overlay_has_real_evidence(lab):
    lab.matrix['tracks']=[{'id':'planned','name':'计划冲突','milestones':[{'chapter_id':'chapter_1','basis':'PLANNED','emotion':'恐惧'}]}]
    state=analyze(lab,character_ids=['hero'],track_ids=['planned']);assert point(state,series='track:planned')['tension'] is None
    assert point(state,series='track:planned')['status']=='PLANNED_NOT_MEASURED'
    assert point(state,series='character:hero')['status']=='CHARACTER_LOCAL_CONTEXT_NOT_INNER_STATE'
    assert point(state,series='character:hero')['evidence']
    d=lab.tools.doc('p1',lab.cards[0]['draft']);lab.matrix['tracks'][0]['milestones'][0].update(basis='TEXT_OBSERVATION',source_path=lab.cards[0]['draft'],revision=d['etag'],quote='小岚遇到危险')
    state=analyze(lab,track_ids=['planned']);assert point(state,series='track:planned')['tension']>0

def test_empty_short_anthology_graceful_and_owned_targets(lab):
    lab.cards.clear();state=lab.curve.index('p1');assert state['chapters']==[] and state['points']==[]
    lab.manifests['p1']['writing']={'form':'anthology'};assert lab.curve.index('p1')['availability_note']=='ANTHOLOGY_SELECT_MEMBER'
    lab.manifests['p1']['writing']={'form':'short','body_id':'story_'+'a'*32};path='chapters/story/draft.txt';(lab.root/path).parent.mkdir(parents=True);(lab.root/path).write_text('希望尚未熄灭。','utf8');lab.cards.append({'id':'story_'+'a'*32,'number':0,'title':'短篇','volume':'','kind':'story','draft':path})
    assert len(analyze(lab)['chapters'])==1
    with pytest.raises(ConsoleError):analyze(lab,whole_book=False,chapter_ids=['foreign_chapter'])

def test_profiles_persist_project_isolate_and_conflicts(lab):
    before=protected(lab.root);p=persona(lab);assert lab.readers.index('p1')['profiles'][0]['id']==p['id'];assert lab.readers.index('p2')['profiles']==[]
    with pytest.raises(ConsoleError):lab.readers.save('p1',PersonaSave(etag='0'*64,persona={'name':'未授权覆盖'}))
    with pytest.raises(ConsoleError):lab.readers.save('p2',PersonaSave(etag=lab.readers.index('p2')['etag'],persona={'id':p['id'],'name':'错误作品'}))
    assert before==protected(lab.root)

def test_reader_preview_exact_paths_noncontinuous_chunks_budget_and_no_ai(lab):
    profiles=[persona(lab,'甲'),persona(lab,'乙')];panel=prepare(lab,profiles,whole_book=False,chapter_ids=['chapter_1','chapter_3'],max_calls=3)
    assert panel['preview']['requests']==4 and not panel['preview']['can_approve'];assert panel['chunks']==2
    assert {s['path'] for s in panel['sources']}=={lab.cards[0]['draft'],lab.cards[2]['draft']}
    assert all(s['revision']==lab.tools.doc('p1',s['path'])['etag'] for s in panel['sources'])
    assert not lab.manager.tasks
    with pytest.raises(ConsoleError):approve(lab,panel)
    panel=prepare(lab,profiles,max_calls=2);assert panel['preview']['requests']==2 and panel['preview']['input_tokens_upper_estimate']>0
    assert panel['preview']['cost_estimate']>0;ready=approve(lab,panel);assert ready['status']=='READY' and not lab.manager.tasks
    with pytest.raises(ConsoleError):lab.readers.approve('p1',panel['id'],ReaderApprove(etag=ready['etag'],preview_hash='0'*64,confirm=True))

def test_reader_limits_partial_coverage_and_unavailable_model_no_fallback(lab):
    (lab.root/lab.cards[0]['draft']).write_text('字'*95001,'utf8');(lab.root/lab.cards[1]['draft']).write_text('','utf8');panel=prepare(lab)
    assert panel['preview']['coverage']=='PARTIAL_COVERAGE' and len(panel['preview']['blocked'])==2
    assert all(not c['source_ids'] or 'chapter_1' not in c['source_ids'] for c in panel['cells']);assert not lab.manager.tasks
    with pytest.raises(ConsoleError):prepare(lab,[persona(lab,'不可用模型')],model='offline')
    assert not lab.manager.tasks

def test_reader_manifest_requires_consent_and_rechecks_text_and_model(lab):
    panel=prepare(lab)
    with pytest.raises(ConsoleError):next_(lab,panel)
    panel=approve(lab,panel);lab.config['temperature']=0.9
    with pytest.raises(ConsoleError):next_(lab,panel)
    lab.config['temperature']=0.5;(lab.root/lab.cards[0]['draft']).write_text('新的正文，旧范围不再适用。','utf8')
    with pytest.raises(ConsoleError):next_(lab,panel)
    assert not lab.manager.tasks


def report_output():return {'verdict':'WARN','summary':'虚构画像可能对这一段悬念感兴趣。','summary_evidence':['我们不能放弃。'],'issues':[], 'reader_reactions':[{'kind':'moving','comment':'这句拒绝放弃表现了人物的希望。','evidence':['我们不能放弃。'],'uncertainty':'这只是当前画像下的模型意见。'},{'kind':'abandonment','comment':'此引用不存在，不能定位。','evidence':['未写过的对白。'],'uncertainty':'证据不足，不代表真实弃读。'}]}

def test_mock_provider_uses_real_reader_report_evidence_and_side_by_side_history(lab):
    before=protected(lab.root);profiles=[persona(lab,'谨慎读者'),persona(lab,'情感读者')];panel=approve(lab,prepare(lab,profiles,max_calls=2));panel=next_(lab,panel)
    assert panel['calls_started']==1 and len(lab.manager.tasks)==1
    task=lab.manager.get(panel['active_task']['id']);assert 'PUBLIC_READER' in task.prompt and profiles[0]['id'] in task.prompt
    assert 'AUTHOR_PRIVATE_FIXTURE' not in task.prompt and 'canonical_truth' not in task.prompt
    with pytest.raises(ConsoleError):next_(lab,panel)
    row=lab.manager.finish(task.id,report_output());assert row['reader_simulation_not_human_data'];assert len(row['reader_reactions'])==1 and row['reader_reactions'][0]['evidence_verified'];assert row['reader_evidence_filter']['omitted_findings']==1;assert '未写过的对白。' not in json.dumps(row,ensure_ascii=False)
    assert row['ai_metadata']['backend']=='MOCK_VALIDATION_NOT_REAL_AI'
    panel=lab.readers.get('p1',panel['id']);assert panel['cells'][0]['status']=='COMPLETED' and len(panel['reports'])==1
    panel=next_(lab,panel);lab.manager.finish(panel['active_task']['id'],report_output());panel=lab.readers.get('p1',panel['id']);assert panel['status']=='COMPLETED' and len(panel['reports'])==2
    assert {r['report']['reader_persona']['id'] for r in panel['reports']}=={p['id'] for p in profiles}
    lab.readers.remove('p1',profiles[0]['id'],PersonaRemove(etag=lab.readers.index('p1')['etag'],confirm=True))
    reopened=type(lab.readers)(lab.reviews,lab.curve).get('p1',panel['id']);assert len(reopened['profiles'])==2 and len(lab.reviews.list('p1'))==2
    with pytest.raises(ConsoleError):lab.readers.get('p2',panel['id'])
    assert before==protected(lab.root)


def test_mock_cancel_retry_explicit_and_never_exceeds_approved_budget(lab):
    panel=next_(lab,approve(lab,prepare(lab,max_calls=2)));task_id=panel['active_task']['id'];asyncio.run(lab.manager.cancel(task_id));panel=lab.readers.get('p1',panel['id'])
    assert panel['status']=='PAUSED' and panel['cells'][0]['status']=='CANCELLED' and len(lab.manager.tasks)==1
    panel=lab.readers.retry('p1',panel['id'],ReaderRetry(etag=panel['etag'],cell_id='cell_0',confirm=True));assert len(lab.manager.tasks)==1
    panel=next_(lab,panel);task=lab.manager.get(panel['active_task']['id']);task.status='FAILED';panel=lab.readers.get('p1',panel['id'])
    with pytest.raises(ConsoleError):lab.readers.retry('p1',panel['id'],ReaderRetry(etag=panel['etag'],cell_id='cell_0',confirm=True))
    assert panel['calls_started']==2 and len(lab.manager.tasks)==2


def test_selection_reader_reactions_cannot_jump_outside_authorized_selection(lab):
    path=lab.cards[0]['draft'];file=lab.root/path;text='😀希望尚未熄灭。\n门外突然出现危险。';file.write_text(text,'utf8');doc=lab.tools.doc('p1',path);selection='希望尚未熄灭。';start=utf16_index(text,text.index(selection));p=persona(lab)
    lab.reviews.start('p1',Start(path=path,mode='reader',selection=selection,selection_start=start,selection_end=start+utf16_index(selection,len(selection)),source_revision=doc['etag'],reader_persona={k:v for k,v in p.items() if k not in {'updated_at','fictional_profile'}}))
    output=report_output();output['reader_reactions'][0]['evidence']=['希望尚未熄灭。'];output['reader_reactions'][1]['evidence']=['门外突然出现危险。'];row=lab.manager.finish('mock_0',output)
    assert row['reader_reactions'][0]['anchors'][0]['locations'][0]['start']==2
    assert len(row['reader_reactions'])==1 and row['reader_evidence_filter']['omitted_findings']==1


def test_registered_routes_validate_data_without_model_or_desktop(lab):
    app=FastAPI();app.include_router(routes(lab.service));client=TestClient(app);prefix='/api/projects/p1/creative-insights'
    result=client.get(prefix+'/curve');assert result.status_code==200 and result.json()['canon_changed'] is False
    assert client.put(prefix+'/curve/settings',json={'etag':result.json()['etag'],'flat_count':0}).status_code==422
    assert client.post(prefix+'/readers/prepare',json={'persona_ids':[],'whole_book':True}).status_code==422
    assert not lab.manager.tasks


def test_final_is_default_when_draft_also_exists(lab):
    card=lab.cards[0];card['final']='chapters/chapter-1/final.txt';(lab.root/card['final']).write_text('平静，希望依然温暖。','utf8')
    (lab.root/card['draft']).write_text('危险，枪声，死亡，绝望。','utf8');before=protected(lab.root)
    state=analyze(lab);assert state['chapters'][0]['path']==card['final']
    assert all(e['path']==card['final'] for e in point(state)['evidence'])
    panel=prepare(lab);assert panel['sources'][0]['path']==card['final'] and panel['sources'][0]['revision']==lab.tools.doc('p1',card['final'])['etag']
    assert before==protected(lab.root)


def test_curve_total_budget_is_honest_and_retryable(lab,monkeypatch):
    monkeypatch.setattr('app.creative.narrative_curve.MAX_RUN_CHARACTERS',80)
    state=analyze(lab);assert state['last_run']['status']=='INCONCLUSIVE' and state['last_run']['unprocessed_chapter_ids']
    assert any(p['status']=='RUN_INPUT_BUDGET_REACHED' and p['tension'] is None for p in state['points'])
    monkeypatch.setattr('app.creative.narrative_curve.MAX_RUN_CHARACTERS',20000000)
    retried=analyze(lab);assert retried['last_run']['status']=='COMPLETE_SELECTED_SCOPE' and all(p['tension'] is not None for p in retried['points'])
    for chapter in lab.cards:(lab.root/chapter['draft']).write_text('恐惧中出现新的希望。','utf8')
    monkeypatch.setattr('app.creative.narrative_curve.MAX_RUN_SECONDS',0)
    timed=analyze(lab);assert timed['last_run']['status']=='INCONCLUSIVE';assert len(timed['last_run']['unprocessed_chapter_ids'])==len(lab.cards)
    assert all(p['status']=='RUN_TIME_BUDGET_REACHED' and p['tension'] is None and not p['source_current'] for p in timed['points'])


def test_reader_rechecks_every_frozen_source_inside_existing_review(lab,monkeypatch):
    panel=approve(lab,prepare(lab));original=lab.reviews.start
    def changed_between_validation_and_review(project,request):
        assert len(request.reader_source_versions)==4
        (lab.root/lab.cards[1]['draft']).write_text('在本次准备之后变更，未经重新批准。','utf8')
        return original(project,request)
    monkeypatch.setattr(lab.reviews,'start',changed_between_validation_and_review)
    with pytest.raises(ConsoleError):next_(lab,panel)
    assert not lab.manager.tasks


def test_unanalyzed_manuscript_cannot_save_an_unbound_author_override(lab):
    before=lab.curve.index('p1')
    with pytest.raises(ConsoleError):lab.curve.override('p1',CurveOverride(etag=before['etag'],chapter_id='chapter_1',tension=7,note='须先绑定版本'))
    assert not (lab.root/'metadata/studio/narrative-curve.json').exists()


def test_history_sync_is_read_only_and_corrupt_panel_does_not_hide_other_tools(lab):
    panel=next_(lab,approve(lab,prepare(lab)));lab.manager.finish(panel['active_task']['id'],report_output())
    file=lab.readers.path('p1',panel['id']);before=file.read_bytes();bad=file.parent/('panel_'+'f'*32+'.json');bad.write_text('{broken json','utf8')
    index=lab.readers.index('p1');assert index['history'][0]['status']=='COMPLETED' and len(index['history_issues'])==1
    assert index['profiles'] and file.read_bytes()==before and len(lab.manager.tasks)==1
    assert lab.curve.index('p1')['chapters']


def test_public_task_status_prevents_premature_completion_and_missing_report_is_explicit(lab,monkeypatch):
    panel=next_(lab,approve(lab,prepare(lab,max_calls=2)));task=lab.manager.get(panel['active_task']['id']);lab.manager.finish(task.id,report_output());original=task.public
    monkeypatch.setattr(task,'public',lambda:{'id':task.id,'status':'RUNNING'})
    assert lab.readers.get('p1',panel['id'])['cells'][0]['status']=='RUNNING'
    monkeypatch.setattr(task,'public',original);path=lab.reviews.path('p1',panel['cells'][0]['review_id']);assert path.resolve().is_relative_to(lab.root.resolve());path.unlink()
    failed=lab.readers.get('p1',panel['id']);assert failed['status']=='PAUSED' and failed['cells'][0]['status']=='FAILED'
    assert failed['cells'][0]['last_error']=='REPORT_UNAVAILABLE' and len(lab.manager.tasks)==1
    retried=lab.readers.retry('p1',panel['id'],ReaderRetry(etag=failed['etag'],cell_id='cell_0',confirm=True));assert 'last_error' not in retried['cells'][0] and len(lab.manager.tasks)==1


def test_lost_task_recovers_only_matching_durable_report_and_preserves_stale_evidence(lab):
    panel=next_(lab,approve(lab,prepare(lab)));task_id=panel['active_task']['id'];lab.manager.finish(task_id,report_output());lab.manager.tasks.pop(task_id)
    (lab.root/lab.cards[0]['draft']).write_text('作者后来明确保存的新版本。','utf8')
    recovered=lab.readers.get('p1',panel['id']);assert recovered['status']=='COMPLETED' and recovered['cells'][0]['recovered_from_report']
    assert not recovered['reports'][0]['report']['source_current'] and not recovered['reports'][0]['report']['evidence_current']
    assert not lab.manager.tasks


def test_missing_task_without_matching_report_stops_instead_of_replaying(lab):
    panel=next_(lab,approve(lab,prepare(lab,max_calls=2)));task_id=panel['active_task']['id'];report=lab.manager.finish(task_id,report_output());lab.manager.tasks.pop(task_id)
    report['reader_persona']['id']='unrelated_profile';write(lab.reviews.path('p1',report['id']),report)
    stopped=lab.readers.get('p1',panel['id']);assert stopped['status']=='PAUSED' and stopped['cells'][0]['status']=='INTERRUPTED'
    assert stopped['cells'][0]['last_error']=='TASK_MISSING_INTERRUPTED' and not stopped['reports'] and not lab.manager.tasks


def test_restart_report_recovery_does_not_override_explicit_cancel(lab):
    panel=next_(lab,approve(lab,prepare(lab,max_calls=2)));task=lab.manager.get(panel['active_task']['id']);lab.manager.finish(task.id,report_output());task.status='CANCELLED'
    cancelled=lab.readers.get('p1',panel['id']);assert cancelled['cells'][0]['status']=='CANCELLED' and not cancelled['cells'][0].get('recovered_from_report')
    # A distinct batch interrupted specifically by backend restart may recover.
    panel=next_(lab,approve(lab,prepare(lab,[persona(lab,'重启恢复画像')])));task=lab.manager.get(panel['active_task']['id']);lab.manager.finish(task.id,report_output());task.status='INTERRUPTED';task.reason='backend_restart'
    recovered=lab.readers.get('p1',panel['id']);assert recovered['cells'][0]['status']=='COMPLETED' and recovered['cells'][0]['recovered_from_report']


def test_whole_book_includes_unwritten_chapter_in_coverage_and_invalid_chunk_rejected(lab):
    lab.cards.append({'id':'chapter_unwritten','number':5,'title':'尚未写出的计划章','volume':'v2','order':5,'kind':'chapter','draft':None,'final':None})
    panel=prepare(lab);assert panel['preview']['source_count']==5 and panel['preview']['readable_count']==4
    assert panel['preview']['blocked'][0]['error']=='UNWRITTEN_CHAPTER' and panel['preview']['coverage']=='PARTIAL_COVERAGE'
    panel=next_(lab,approve(lab,panel));lab.manager.finish(panel['active_task']['id'],report_output());finished=lab.readers.get('p1',panel['id']);assert finished['status']=='PARTIAL_COVERAGE'
    with pytest.raises(ConsoleError):lab.readers.get('p1',panel['id'],1)
    explicit=prepare(lab,[persona(lab,'明确仅看已写章')],whole_book=False,chapter_ids=['chapter_1']);assert explicit['preview']['coverage']=='COMPLETE_SELECTED_TEXT'

def test_overlay_changes_preserve_other_chapters_book_cache_and_author_priority(lab):
    state=analyze(lab);state=lab.curve.override('p1',CurveOverride(etag=state['etag'],chapter_id='chapter_4',tension=9.2,note='作者优先，非Canon'))
    before=lab.counts['body_reads']
    state=analyze(lab,whole_book=False,chapter_ids=['chapter_1'],character_ids=['hero'])
    assert lab.counts['body_reads']-before==1
    assert point(state,'chapter_4')['override_current'] and point(state,'chapter_4')['tension']==9.2
    assert point(state,'chapter_3')['source_current'] and point(state,'chapter_3')['tension'] is not None
    assert state['coverage']=={'chapters':4,'known_tension':4,'unknown_tension':0}
    state=analyze(lab,whole_book=False,chapter_ids=['chapter_1'])
    assert point(state,'chapter_4')['override_current'] and point(state,'chapter_4')['tension']==9.2


def test_unwritten_chapters_cannot_be_promoted_to_measured_author_score(lab):
    lab.cards.append({'id':'unwritten','number':5,'title':'计划章','volume':'v2','kind':'chapter','draft':None,'final':None})
    state=analyze(lab);assert state['coverage']['unknown_tension']==1
    with pytest.raises(ConsoleError):lab.curve.override('p1',CurveOverride(etag=state['etag'],chapter_id='unwritten',tension=8))
    assert point(state,'unwritten')['tension'] is None


def test_reader_strict_evidence_omits_mixed_claims_and_unanchored_summary(lab):
    panel=next_(lab,approve(lab,prepare(lab)));output=report_output()
    output['summary']='模型捏造的摘要事件';output['summary_evidence']=['模型捏造的证据']
    output['reader_reactions'][0]['evidence'].append('另一条不存在的引文')
    output['issues']=[{'severity':'ERROR','message':'模型捏造的问题','evidence':['并不存在'], 'priority':'MUST FIX'}]
    row=lab.manager.finish(panel['active_task']['id'],output)
    assert row['report']['verdict']=='INCONCLUSIVE' and not row['reader_reactions']
    assert not row['reader_evidence_filter']['summary_verified'] and row['reader_evidence_filter']['omitted_findings']==3
    text=json.dumps(row,ensure_ascii=False)
    for invalid in ['模型捏造','另一条不存在','并不存在','未写过的对白']:assert invalid not in text
    assert row['report']['issues'][0]['suppressed'] and row['anchors'][0]['issue']==0
    raw=lab.reviews.path('p1',row['id']).read_bytes();shown=lab.reviews.get('p1',row['id'])
    assert shown['reader_evidence_filter']==row['reader_evidence_filter'] and lab.reviews.path('p1',row['id']).read_bytes()==raw


def test_old_reader_reports_are_filtered_on_read_without_rewriting_history(lab):
    panel=next_(lab,approve(lab,prepare(lab)));row=lab.manager.finish(panel['active_task']['id'],report_output())
    row['reader_reactions'].append({'kind':'abandonment','comment':'旧报告虚构事件','evidence':['旧报告虚构引文'],'uncertainty':'不确定','anchors':[{'quote':'旧报告虚构引文','verified':False,'locations':[]}]})
    row['report']['reader_reactions'].append({'kind':'abandonment','comment':'旧报告虚构事件','evidence':['旧报告虚构引文'],'uncertainty':'不确定'})
    path=lab.reviews.path('p1',row['id']);write(path,row);before=path.read_bytes()
    shown=lab.reviews.get('p1',row['id']);assert len(shown['reader_reactions'])==1 and '旧报告虚构' not in json.dumps(shown,ensure_ascii=False)
    assert path.read_bytes()==before
