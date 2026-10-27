"""Scoped orchestration and author-control contracts. Model doubles are MOCK only."""
import asyncio,json,os,shutil,sys,threading,time
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
ROOT=Path(__file__).resolve().parents[3];BOOT=TemporaryDirectory(prefix='novel-director-');boot=Path(BOOT.name)/'workspace';shutil.copytree(ROOT/'desktop/preview-template',boot)
os.environ['NOVEL_WORKSPACE']=str(boot);os.environ['NOVEL_STUDIO_DATA']=str(Path(BOOT.name)/'data');sys.path.insert(0,str(ROOT/'web/backend'))
from app.creative.director import Create,Control,Patch,Rewrite,Candidate,Plan,Step,Limits
from app.creative.writing import ContextChoice,Approval
from app.studio_tools import Decision,normalized,utf16_index
from app.errors import ConsoleError

@pytest.fixture
def lab(tmp_path,monkeypatch):
    w=tmp_path/'workspace';shutil.copytree(ROOT/'desktop/preview-template',w);monkeypatch.setenv('NOVEL_WORKSPACE',str(w));monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'data'));monkeypatch.setenv('NOVEL_STATIC_DIR',str(tmp_path/'no-static-assets'))
    from app.main import create_app
    from app.config import Settings
    app=create_app(Settings(workspace=w));s=app.state.creative_director;p=next((w/'projects').glob('novel_*')).name;pr=w/'projects'/p
    path='chapters/chapter-90/draft.txt';f=pr/path;f.parent.mkdir(parents=True);f.write_text('江予把信纸放下。周栖没有说话。\n','utf8');d=s.tools.doc(p,path);actor=s.tools.characters.list(p)[0]['canonical']['id'];ctx=s.writing.preview(p,ContextChoice(path=path,revision=d['etag'],pov=actor));s.writing.approve(p,ctx['id'],Approval(context_hash=ctx['context_hash'],confirm=True))
    return s,p,pr,path,d,ctx

def new(lab,mode='quick',**kw):
    s,p,pr,path,d,c=lab;return s.create(p,Create(path=path,revision=d['etag'],context_id=c['id'],goal='完成一场克制的对话，保留合作关系。',mode=mode,executor=kw.pop('executor','codex'),start=utf16_index(normalized(d),len(normalized(d))),end=utf16_index(normalized(d),len(normalized(d))),**kw))

def body(row,action,**kw):return Control(etag=row['etag'],epoch=row['epoch'],task_id=row.get('active_task'),action=action,confirm_plan=True,**kw)
class Fake:
    def __init__(self,prompt,planned=False,slow=False):self.prompt=prompt;self.planned=planned;self.slow=slow;self.stop=threading.Event();self.role='WRITER';self.selected_ai={'backend':'MOCK','provider_name':'Test fixture','model':'test-only'}
    def close(self):self.stop.set()
    interrupt=close
    def start_task(self,prompt,emit,**kw):
        if self.planned:
            plan=Plan(summary='人物用行动表达立场。',steps=[Step(title='谈判',instruction='先让人物提出条件，再面对现实阻力。')],methods=['context','scene','character'],method_application=['限制角色知识','用选择推进冲突','保持两人的表达差异'])
            return {'status':'completed','output':plan.model_dump_json()}
        text='她把门留着。' if '冷静谈判' in prompt else '江予没有追问。周栖把船票收了起来。'
        if self.slow:text*=5
        for t in [text[i:i+2] for i in range(0,len(text),2)]:
            if self.stop.is_set():return {'status':'interrupted','output':''}
            emit('llm_delta',t,{'delta':t});time.sleep(.025 if self.slow else .001)
        return {'status':'completed','output':text}

def fake(monkeypatch,slow=False):
    calls=[]
    def build(center,p,group,prompt,model=None,**kw):
        a=Fake(prompt,group=='scene_design',slow and group!='scene_design');calls.append((group,prompt,a));return a
    monkeypatch.setattr('app.creative.director.adapter',build);return calls

async def done(s,p,row):
    t=s.manager(p).get(row['active_task']);await asyncio.wait_for(t.runner,8);return s.get(p,row['id'])

def test_quick_mode_uses_only_chosen_executor_and_guarded_insert(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,pr,path,d,c=lab
    async def scenario():
        row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],limits=Limits(api_budget=None)));assert 'api_budget' in row['limits'] and row['limits']['api_budget'] is None
        row=await s.control(p,row['id'],body(row,'run'));row=await done(s,p,row)
        assert not s.buffers
        assert row['status']=='CANDIDATE' and row['draft'] and len(calls)==1 and calls[0][0]=='cowrite'
        original=(pr/path).read_bytes();v=s.stage(p,row['id'],Candidate(etag=row['etag']));assert (pr/path).read_bytes()==original
        out=s.tools.decide(p,v['candidate']['id'],Decision(action='accept',originalHash=v['candidate']['originalHash'],candidate=v['candidate']['candidate']))
        assert normalized(out['file'])==normalized(d)+row['draft']
    asyncio.run(scenario())

def test_director_delivers_actual_selected_skill_bodies_and_requires_author(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,*_=lab
    async def scenario():
        row=new(lab,'director');row=await s.control(p,row['id'],body(row,'plan'));row=await done(s,p,row)
        assert row['status']=='PLAN_REVIEW' and not row['draft'] and row['skill_proof']
        assert 'METHOD context' in calls[0][1] and '待解决' not in row['draft']
        with pytest.raises(ConsoleError):await s.control(p,row['id'],Control(etag=row['etag'],action='run',confirm_plan=False))
        row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='作者保留的开场。',instruction='只规划尚未完成的谈判。'))
        row=await s.control(p,row['id'],body(row,'plan'));row=await done(s,p,row)
        assert '作者保留的开场。' in calls[1][1] and '只规划尚未完成的谈判。' in calls[1][1]
        row=await s.control(p,row['id'],body(row,'run'));row=await done(s,p,row);assert row['draft'].startswith('作者保留的开场。') and len(calls)==3
    asyncio.run(scenario())

def test_interrupt_retains_received_text_and_latest_directions_take_effect(lab,monkeypatch):
    calls=fake(monkeypatch,True);s,p,*_=lab
    async def scenario():
        row=new(lab);row=await s.control(p,row['id'],body(row,'run'));old=dict(row)
        for _ in range(100):
            await asyncio.sleep(.01)
            if s.buffers.get((p,row['id'],row['epoch'])):break
        row=s.get(p,row['id']);await s.control(p,row['id'],body(row,'interrupt'));await s.manager(p).get(old['active_task']).runner;row=s.get(p,row['id']);assert row['draft'] and not row['active_task']
        kept=row['draft'];row=s.patch(p,row['id'],Patch(etag=row['etag'],instruction='保留已有片段，接下来改为冷静谈判。'))
        row=await s.control(p,row['id'],body(row,'run'));active=dict(row)
        with pytest.raises(ConsoleError):await s.control(p,row['id'],body(old,'interrupt'))
        row=await done(s,p,row);assert row['draft'].startswith(kept) and '她把门留着' in row['draft'] and '冷静谈判' in calls[-1][1]
    asyncio.run(scenario())

def test_pause_only_stops_subsequent_steps_and_plan_reorder_preserves_completion(lab,monkeypatch):
    fake(monkeypatch,True);s,p,*_=lab
    async def scenario():
        row=new(lab,'deep');pl=Plan(summary='两场景',steps=[Step(title='第一场',instruction='保留冲突'),Step(title='第二场',instruction='面对后果')]);row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=pl))
        row=await s.control(p,row['id'],body(row,'run',auto_continue=True));await asyncio.sleep(.08);row=s.get(p,row['id']);await s.control(p,row['id'],body(row,'pause'));row=await done(s,p,row)
        assert row['completed']==[0] and row['status']=='PAUSED'
        row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='调整顺序',steps=list(reversed(pl.steps)))))
        assert row['completed']==[1]
    asyncio.run(scenario())

def test_manual_draft_partial_rewrite_and_source_conflict(lab,monkeypatch):
    fake(monkeypatch);s,p,pr,path,d,c=lab
    async def scenario():
        row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='第一段保留。第二段需要修改。第三段保留。'))
        quote='第二段需要修改。';start=row['draft'].index(quote);row=s.rewrite(p,row['id'],Rewrite(etag=row['etag'],start=start,end=start+len(quote),quote=quote,instruction='改为冷静谈判。'))
        row=await s.control(p,row['id'],body(row,'run'));row=await done(s,p,row)
        assert row['draft']=='第一段保留。她把门留着。第三段保留。'
        (pr/path).write_text('作者的新正文。','utf8')
        with pytest.raises(ConsoleError):s.stage(p,row['id'],Candidate(etag=row['etag']))
    asyncio.run(scenario())

def test_limits_secrets_and_cross_project_records(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab
    async def scenario():
        row=new(lab,limits=Limits(max_calls=1));row=await s.control(p,row['id'],body(row,'run'));row=await done(s,p,row)
        with pytest.raises(ConsoleError):await s.control(p,row['id'],body(row,'run'))
        with pytest.raises(ConsoleError):s.patch(p,row['id'],Patch(etag=row['etag'],instruction='不要暗示某个人是凶手。'))
        with pytest.raises(ConsoleError):s.get('novel_missing',row['id'])
        assert s.tools.doc(p,lab[3])['etag']==lab[4]['etag']
    asyncio.run(scenario())


def test_api_budget_unknown_prices_blocks_before_any_upstream_call(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,*_=lab
    from app.ai.models import Provider,Model
    s.center.put(Provider(provider_id='fixture',display_name='Local fixture',base_url='http://127.0.0.1:9164',available_models=[Model(id='local-fixture',chat_token_parameter='max_tokens')]))
    async def scenario():
        row=new(lab,executor='fixture::local-fixture',limits=Limits(api_budget=1))
        with pytest.raises(ConsoleError,match='缺少模型价格'):await s.control(p,row['id'],body(row,'run'))
        assert not calls and s.get(p,row['id'])['calls']==0
    asyncio.run(scenario())


def test_candidate_review_evidence_cannot_target_manuscript(lab,monkeypatch):
    s,p,pr,path,d,c=lab
    class Reviewer(Fake):
        def start_task(self,prompt,emit,**kw):
            assert 'WriterView' not in prompt or 'author_only' not in prompt
            return {'status':'completed','output':json.dumps({'verdict':'WARN','summary':'仅候选文本审查。','issues':[{'severity':'minor','message':'语句可更具体。','evidence':['候选里的对白。'],'priority':'SUGGESTION','confidence':'HIGH','code':'DIALOGUE','paragraph':1}]},ensure_ascii=False)}
    monkeypatch.setattr('app.creative.reviews.adapter',lambda *a,**kw:Reviewer('',False))
    from app.creative.reviews import Candidate as ReviewCandidate,Decide
    from app.creative.director import Review
    async def scenario():
        row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='候选里的对白。'))
        result=s.review(p,row['id'],Review(etag=row['etag']));assert result['status']=='REVIEWING' and result['active_task']==result['task']['id'];await s.manager(p).get(result['task']['id']).runner
        after=s.get(p,row['id']);assert after['status']=='REVIEW_READY' and not after['active_task'] and after['calls']==1 and after['seconds_used']>0
        assert after['seconds_used']==s.get(p,row['id'])['seconds_used']
        report=s.reviews.get(p,result['review_id']);assert report['source_kind']=='CREATIVE_CANDIDATE' and report['anchors'][0]['evidence'][0]['verified']
        with pytest.raises(ConsoleError):s.reviews.candidate(p,report['id'],ReviewCandidate(issue=0))
        with pytest.raises(ConsoleError):s.reviews.decide(p,report['id'],Decide(etag=report['etag'],issue=0,action='todo'))
        assert (pr/path).read_text('utf8')==normalized(d)
    asyncio.run(scenario())


def test_actual_writer_brief_binds_methods_style_and_freedom(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,pr,path,d,c=lab
    async def scenario():
        row=new(lab)
        brief=s.execution_brief(p,row['id'])
        assert {v['id'] for v in brief['selected_methods']}==set(row['skills'])
        assert brief['fact_boundaries']['free_now'] and brief['fact_boundaries']['author_decision']
        assert all(v['source_hashes'] and v['actions'] for v in brief['selected_methods'])
        row=await s.control(p,row['id'],body(row,'run'));row=await done(s,p,row)
        from app.studio_tools import text_hash
        assert row['execution_receipts'][0]['prompt_sha256']==text_hash(calls[0][1])
        assert row['quality_observations']['semantic_review']=='NOT_RUN'
        assert s.tools.doc(p,path)['etag']==d['etag']
    asyncio.run(scenario())

def test_context_keeps_confirmed_style_ahead_of_distant_prose(lab):
    import yaml
    s,p,pr,path,d,c=lab
    (pr/'settings/style-profile.yaml').write_text(yaml.safe_dump({'rhythm':'STYLE_PRIORITY_MARKER '+('节奏随行动变化。'*50)},allow_unicode=True),'utf8')
    earlier=[]
    for i in range(1,7):
        f=pr/f'chapters/chapter-{i}/draft.txt';f.parent.mkdir(parents=True,exist_ok=True);f.write_text('安全前文场景。'*120,'utf8');earlier.append(f.relative_to(pr).as_posix())
    ctx=s.writing.preview(p,ContextChoice(path=path,revision=d['etag'],previous_paths=earlier,budget=3000))
    assert any(x['kind']=='style' for x in ctx['packet']['sources'])
    assert any(x['id']=='current-text' for x in ctx['packet']['sources'])
    assert ctx['size']<=3000

def test_past_pointers_do_not_claim_falsehood_or_change_text():
    from app.creative.writing_contract import observations
    text='十年前，她在这里失去了家人。现在她重新打开门。'
    report=observations(text,{'sources':[]})
    assert report['past_reference_signals'][0]['status']=='NEEDS_CONTEXT_NOT_PROVEN_ERROR'
    assert observations(text,{'sources':[{'text':text}]})['past_reference_signals']==[]
    assert report['semantic_review']=='NOT_RUN'

def test_unselected_plan_method_cannot_reach_executor(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,*_=lab
    async def scenario():
        row=new(lab)
        row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='不改授权范围',steps=[Step(title='当前场景',instruction='保持当下冲突')],methods=['review'])))
        with pytest.raises(ConsoleError,match='未授权'):await s.control(p,row['id'],body(row,'run'))
        assert not calls and not s.get(p,row['id'])['active_task']
    asyncio.run(scenario())


def test_legacy_step_defaults_preserve_completed_work_and_manual_signals(lab):
    s,p,*_=lab;row=new(lab,'deep')
    row['plan']={'summary':'旧版本检查点','steps':[{'title':'保留','instruction':'当前场景','checks':[],'enabled':True,'needs_author':False}],'methods':[],'method_application':[]}
    row['completed']=[0];s.put(p,row);row=s.get(p,row['id'])
    row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan.model_validate(row['plan'])))
    assert row['completed']==[0]
    row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='十年前，她来过这里。'))
    assert row['quality_observations']['past_reference_signals']
    row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='她打开门。'))
    assert not row['quality_observations']['past_reference_signals']


def test_sparse_chapters_require_explicit_distant_reference(lab):
    s,p,pr,path,d,c=lab
    implicit=s.writing.preview(p,ContextChoice(path=path,revision=d['etag']))
    assert not any(x['id'].startswith('chapter:') for x in implicit['packet']['sources'])
    assert 'NEARBY_CHAPTER_CONTEXT_UNAVAILABLE' in implicit['warnings']
    prior='chapters/chapter-1/draft.txt'
    (pr/prior).write_text('安全的远处前文，需作者显式选用。',encoding='utf8')
    explicit=s.writing.preview(p,ContextChoice(path=path,revision=d['etag'],previous_paths=[prior]))
    assert any(x['id']=='chapter:'+prior for x in explicit['packet']['sources'])
