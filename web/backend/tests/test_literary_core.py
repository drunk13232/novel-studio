"""2.12 focused safety/integration checks. Inference doubles are explicitly MOCK."""
import json,copy,time
import pytest
from test_writing_assist import service,context,approve
from app.creative.literary_models import CoreDetails,Save,Event,Evidence,Adopt,Profile,ReportCard,Execute
from app.creative.reviews import Start
from app.creative.writing import ContextChoice,SceneStart
from app.studio_tools import normalized,text_hash,utf16_index
from app.errors import ConsoleError

BODY='江予把空白申请放在灯下。\n“我替你交。”周栖说。\n江予按住纸角：“我还没有决定。”\n周栖收回手，把那把铜钥匙放在桌边。雨水顺着他的袖口滴下来。'

def setup(service):
 s,p,root=service;c=context(service,BODY);core=s.literary_core;return core,s,p,root,c

def evidence(c,quote='那把铜钥匙'):
 a=BODY.index(quote);return Evidence(path=c['choice']['path'],revision=c['choice']['revision'],start=utf16_index(BODY,a),end=utf16_index(BODY,a+len(quote)),quote=quote)

def note(core,p,kind='thought',**kwargs):
 d=CoreDetails(kind=kind,title='选择的代价',**kwargs)
 return core.save(p,Save(etag=core.notes.entries(p)['etag'],text='关怀何时变成替人决定？',details=d,confirm=True))['record']

def capture(core,p,monkeypatch):
 box={}
 class A:selected_ai={'backend':'MOCK_VALIDATION_NOT_REAL_AI'}
 monkeypatch.setattr('app.creative.literary_core.adapter',lambda *a,**kw:A())
 class T:
  private_text=False
  def public(self):return {'id':'fixture','status':'QUEUED'}
 def prepared(req,prompt,*args,**kwargs):box.update(prompt=prompt,complete=args[3],schema=args[2]);return T()
 monkeypatch.setattr(core.reviews.manager(p),'prepared',prepared);return box

def analysis(quote='江予按住纸角：“我还没有决定。”'):
 return {'summary':'关怀与选择之间存在张力，并没有唯一答案。','findings':[{'dimension':'人物选择','claim':'按住纸角的动作保留了自主决定的空间。','classification':'AI_INTERPRETATION','evidence':[{'source_id':'body','quote':quote}],'alternative':'也可能是在避免承担选择的风险。','missing_premise':'尚未交代周栖此前被拒绝的经历。','limitation':'只依据本次选段，不能决定人物长期立场。','suggestion':'可以让下一次选择出现具体代价。','writer_instruction':'让行动承载立场，保留停顿。'}],'counter_readings':[{'perspective':'保护的合理理由','interpretation':'替交申请也可能是在帮助对方应付截止时间。','evidence':[{'source_id':'body','quote':'“我替你交。”周栖说。'}],'limitation':'文中未给出截止时间，这只是条件性解释。'}],'style_directives':['以动作与停顿承载情绪。','保留人物尚未说完的意思。'],'questions':['申请是否有明确截止时间？'],'limitations':['单一模型解释，不构成独立评审或文学定论。']}

def test_author_questions_positions_sources_restore_and_no_canon_writes(service):
 core,s,p,root,c=setup(service);before={str(f):f.read_bytes() for folder in ['state','characters','settings'] for f in (root/folder).rglob('*') if f.is_file()}
 char=c['packet']['pov'];card=note(core,p,question='关怀与服从如何产生冲突？',positions=[{'character':char,'stance':'保留选择','choice':'按住申请','cost':'可能错过机会','challenge':'别人是在帮忙'}],links=[{'type':'character','id':char}],evidence=[evidence(c)])
 index=core.index(p);assert index['records'][0]['id']==card['id'];assert card['evidence_current'];assert card['literary']['positions'][0]['cost']=='可能错过机会'
 assert core.card(p,card['id'])['record_sha256']==card['record_sha256']
 assert all(__import__('pathlib').Path(f).read_bytes()==v for f,v in before.items())
 with pytest.raises(ConsoleError):core.card(p+'bad',card['id'])

def test_clue_plan_is_not_placement_multiple_payoffs_and_exact_evidence(service):
 core,s,p,root,c=setup(service);clue=note(core,p,'clue',secret='铜钥匙实际属于失踪的馆长')
 def event(phase,proof=[]):return core.event(p,clue['id'],Event(etag=core.notes.entries(p)['etag'],phase=phase,text='作者核对正文后的推进',evidence=proof,confirm=True))['record']
 assert not clue['events'] and clue['literary']['phase']=='PLANNED'
 with pytest.raises(ConsoleError):event('PLACED')
 with pytest.raises(ConsoleError):event('RESOLVED',[evidence(c)])
 bad=evidence(c).model_copy(update={'quote':'计划中才有的钥匙'} )
 with pytest.raises(ConsoleError):event('PLACED',[bad])
 for stage in ['PLACED','REINFORCED','PARTIAL','RESOLVED','RESOLVED']:last=event(stage,[evidence(c)])
 assert [e['literary']['phase'] for e in last['events']][-2:]==['RESOLVED','RESOLVED']
 assert all(e['current'] for e in last['evidence_status'])
 (root/c['choice']['path']).write_text('作者改动了证据','utf8');assert not core.card(p,clue['id'])['evidence_current']

def test_writer_secret_filter_handoff_scope_staleness_and_idempotency(service):
 core,s,p,root,c=setup(service);card=note(core,p,'clue',secret='铜钥匙实际属于失踪的馆长',evidence=[evidence(c)])
 raw={k:c['choice'][k] for k in ['path','revision','pov','scene_id']};b=Adopt(**raw,record_sha256=card['record_sha256'],writer_text='让人物通过动作呈现犹豫，使用桌上的铜钥匙作为可见细节。',confirm=True)
 m=core.adopt(p,card['id'],b);assert core.adopt(p,card['id'],b)['note_id']==m['note_id']
 safe=s.preview(p,ContextChoice(**{**c['choice'],'material_ids':[m['note_id']]}));packet=json.dumps(safe['packet'],ensure_ascii=False)
 assert b.writer_text in packet and card['literary']['secret'] not in packet and card['text'] not in packet
 for text in ['不要暗示铜钥匙实际属于失踪的馆长','不要暗示这是隐藏真相']:
  with pytest.raises(ConsoleError):core.adopt(p,card['id'],b.model_copy(update={'writer_text':text}))
 other=s.tools.characters.list(p)[1]['canonical']['id']
 with pytest.raises(ConsoleError):s.preview(p,ContextChoice(**{**safe['choice'],'pov':other}))
 approve(s,p,safe)
 core.event(p,card['id'],Event(etag=core.notes.entries(p)['etag'],phase='INTENTIONALLY_OPEN',text='作者改动了计划',confirm=True))
 with pytest.raises(ConsoleError):s.use_context(p,safe['id'])

def test_evidenced_analysis_alternatives_and_report_note(service,monkeypatch):
 core,s,p,root,c=setup(service);card=note(core,p);box=capture(core,p,monkeypatch)
 core.start_analysis(p,Start(path=c['choice']['path'],mode='literary_thought',literary_ids=[card['id']],lens='伦理冲突',model='codex'))
 assert 'AUTHOR_CHECKER_ONLY' in box['prompt'] and 'IDEOL' not in box['prompt']
 row=box['complete'](json.dumps(analysis(),ensure_ascii=False));assert row['counter_anchors'][0]['evidence'][0]['verified']
 assert all(x['priority']=='SUGGESTION' for x in row['report']['issues']);assert row['literary_analysis']['findings'][0]['missing_premise']
 kept=core.report_card(p,row['id'],ReportCard(etag=core.notes.entries(p)['etag'],finding=0,kind='thought',title='另一种可能',text='这是作者选择保留的条件性解释。',confirm=True))
 assert kept['record']['literary']['origin']=='AI_ACCEPTED' and kept['record']['literary']['evidence']
 assert (root/c['choice']['path']).read_text('utf8')==BODY

@pytest.mark.parametrize('fault',['fabrication','foreign_source','unsupported_claim'])
def test_analysis_rejects_fabricated_evidence(service,monkeypatch,fault):
 core,s,p,root,c=setup(service);box=capture(core,p,monkeypatch);core.start_analysis(p,Start(path=c['choice']['path'],mode='literary_logic'));value=analysis()
 if fault=='fabrication':value['findings'][0]['evidence'][0]['quote']='正文从未写过此事'
 elif fault=='foreign_source':value['findings'][0]['evidence'][0]['source_id']='other_novel'
 else:value['findings'][0]['evidence']=[]
 with pytest.raises(ConsoleError):box['complete'](json.dumps(value,ensure_ascii=False))
 assert not core.reviews.list(p)

def test_style_observation_profile_scope_and_real_writer_prompt(service,monkeypatch):
 core,s,p,root,c=setup(service);box=capture(core,p,monkeypatch);core.start_analysis(p,Start(path=c['choice']['path'],mode='literary_style'));r=box['complete'](json.dumps(analysis(),ensure_ascii=False))
 assert r['statistics'] and r['report']['issues'][0]['priority']=='STYLE ONLY'
 profile=core.profile(p,r['id'],Profile(title='动作而非解释',directives=['以动作与停顿呈现情绪，保持叙事距离。'],character_id=c['packet']['pov'],confirm=True))
 assert profile['manuscript_sources'][0]['path']==c['choice']['path'];assert profile['applies_to']['character_id']==c['packet']['pov']
 ctx=s.preview(p,ContextChoice(**{**c['choice'],'profile_ids':[profile['id']]}));approve(s,p,ctx)
 assert '以动作与停顿呈现情绪' in json.dumps(ctx['packet'],ensure_ascii=False)
 other=s.tools.characters.list(p)[1]['canonical']['id'];wrong=s.preview(p,ContextChoice(**{**c['choice'],'pov':other,'profile_ids':[profile['id']]}));assert 'STYLE_SCOPE_NOT_APPLICABLE:'+profile['id'] in wrong['warnings']
 # Existing scene adapter receives the selected style, never the full author report.
 from test_writing_assist import capture as scene_capture
 scene_box=scene_capture(s,p,monkeypatch);s.start_scene(p,SceneStart(context_id=ctx['id'],goal='继续人物争执。',count=2))
 assert '以动作与停顿呈现情绪' in scene_box['prompt'] and '保护的合理理由' not in scene_box['prompt']

def test_public_reader_cannot_receive_author_literary_notes(service,monkeypatch):
 core,s,p,root,c=setup(service);card=note(core,p,'clue',secret='下一章作者才揭露的秘密')
 with pytest.raises(ConsoleError):core.reviews.start(p,Start(path=c['choice']['path'],mode='reader',literary_ids=[card['id']]))
 captured={}
 class A:selected_ai={'backend':'MOCK_PUBLIC_READER_NOT_REAL_AI'}
 monkeypatch.setattr('app.creative.reviews.adapter',lambda *a,**kw:A())
 class T:
  private_text=False
  def public(self):return {'id':'reader','status':'QUEUED'}
 def prepared(req,prompt,*a,**kw):captured['prompt']=prompt;return T()
 monkeypatch.setattr(core.reviews.manager(p),'prepared',prepared);core.reviews.start(p,Start(path=c['choice']['path'],mode='reader'))
 assert card['literary']['secret'] not in captured['prompt'] and card['text'] not in captured['prompt']

def test_explicit_dependencies_use_existing_real_networkx_solver(service,monkeypatch):
 core,s,p,root,c=setup(service);before={str(f):f.read_bytes() for f in (root/'state').rglob('*') if f.is_file()}
 deps=[{'before':'取得钥匙','after':'开门','kind':'strict_order','basis':'作者确认：先取得钥匙才能开门。'},{'before':'开门','after':'取得钥匙','kind':'strict_order','basis':'故意构造循环的隔离测试前提。'},{'before':'信任','after':'协作','kind':'causal','basis':'作者声明的条件性影响'},{'before':'协作','after':'信任','kind':'causal','basis':'允许社会因果反馈'}]
 card=note(core,p,'logic',dependencies=deps,evidence=[evidence(c)])
 from app.world_logic.engine import run
 executed={}
 def real_solver(p,id,b):
  frozen=core.world.version(p,id,b.version);executed.update(result=run(frozen['definition']),definition=frozen['definition']);return {'id':'actual_local_solver','status':'SUCCEEDED','report_id':'test'}
 monkeypatch.setattr(core.world,'run',real_solver)
 r=core.experiment(p,card['id'],Execute(record_sha256=card['record_sha256'],confirm=True));assert r['nodes'][0]['name']=='取得钥匙'
 assert executed['result']['status']=='FAIL' and len(executed['result']['dependency_graph']['conflicting_dependencies'])==2
 d=copy.deepcopy(executed['definition']);d['dependencies']=[x for x in d['dependencies'] if x['id']!='dep_2'];out=run(d)
 assert out['status']=='PASS' and out['dependency_graph']['causal_feedback_present']
 assert all(__import__('pathlib').Path(f).read_bytes()==v for f,v in before.items())


def test_legacy_notebook_status_update_keeps_literary_metadata(service):
 core,s,p,root,c=setup(service);card=note(core,p,'clue',secret='作者尚未披露的钥匙来历',evidence=[evidence(c)])
 from app.author_workbench import Entry
 legacy={k:v for k,v in card.items() if k in Entry.model_fields and k!='literary'}
 legacy.update(etag=core.notes.entries(p)['etag'],status='IN_PROGRESS')
 core.notes.save_entry(p,Entry(**legacy));updated=core.card(p,card['id'])
 assert updated['literary']==card['literary'] and updated['evidence_current']
 assert updated['status']=='IN_PROGRESS'
 assert updated['literary']['secret'] not in json.dumps(s.preview(p,ContextChoice(**c['choice']))['packet'],ensure_ascii=False)
