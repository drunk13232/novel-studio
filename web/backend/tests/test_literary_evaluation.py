"""Focused evaluation checks: MOCK inference, real scope/evidence/checkpoint services."""
import asyncio,copy,json
import pytest
from test_writing_assist import service,context
from app.creative.evaluation import Evaluation,weighted,fingerprint
from app.creative.evaluation_models import Request,Create,Run,Selection,Compare,Bridge,Target
from app.creative.evaluation_rubrics import defaults
from app.errors import ConsoleError
from app.studio_tools import utf16_index

TEXT='😀江予把空白申请放在灯下。\n“我替你交。”周栖说。\n江予按住纸角：“我还没有决定。”\n周栖收回手，把铜钥匙放在桌边。'

def setup(service,monkeypatch):
 s,p,root=service;context(service,TEXT);ev=Evaluation(s.reviews,s.literary_core) if hasattr(s,'reviews') else Evaluation(s.literary_core.reviews,s.literary_core)
 class A:
  selected_ai={'backend':'MOCK_NOT_REAL_AI','model':'fixture','provider_id':'fixture'}
  def close(self):pass
  def interrupt(self):pass
 monkeypatch.setattr('app.creative.evaluation.adapter',lambda *a,**kw:A())
 return ev,p,root

def request(ev,p,scope='chapter',**kw):
 rubric=defaults()[0]['rubric'];rubric['dimensions']=[v for v in rubric['dimensions'] if v['id'] in ['style','thought']]
 return Request(scope=scope,rubric=rubric,model='codex',targets=[{'path':'chapters/chapter-2/draft.txt'}],**kw)

def create(ev,p,b):return ev.create(p,Create(request=b,preview_hash=ev.preview(p,b)['preview_hash'],confirm=True))

def output(packet,bad=False):
 data=json.loads(packet.split('\nEVALUATION_DATA\n')[1]);q=[]
 if 'full_text_segments' in data:
  x=data['full_text_segments'][0];q=[{'source_id':x['source_id'],'quote':x['text'][:24]}]
 else:
  for c in data['completed_full_text_reading_cards']:
   q+=c['assessment']['dimensions'][0]['evidence'][:1]
 dims=[{'dimension':v['id'],'status':'SCORED' if v['id']=='style' else 'INSUFFICIENT_EVIDENCE','score':73 if v['id']=='style' else None,'rationale':'动作及停顿具有局部节奏，未提供长线完整证据。','strengths':['用动作表达拒绝。'],'weaknesses':['单个场景可支持的判断有限。'],'evidence':[{'source_id':q[0]['source_id'],'quote':'不在原文中的句子'}] if bad else q[:2],'uncertainty':'仅依据提供的范围。','alternative':'停顿也可能是犹豫。','influential_judgment':'局部动作承载信息。','suggestion':'保留停顿。'} for v in data['rubric']['dimensions'] if v['enabled']]
 return json.dumps({'summary':'局部语言具有动作感，不能外推全书。','horizon':data['maximum_horizon'],'dimensions':dims,'limitations':['MOCK 只验证协议与保护，不验证文学质量。']},ensure_ascii=False)

async def batch(ev,p,id,calls=20,**kw):
 r=ev.get(p,id);task=ev.run(p,id,Run(etag=r['etag'],calls=calls,seconds=60,confirm=True,**kw));await ev.center.manager(p).get(task['id']).runner
 real_task=ev.center.manager(p).get(task['id']);assert real_task.status in ['SUCCEEDED','CANCELLED'],real_task.error
 return ev.get(p,id)

def mock_calls(monkeypatch,seen):
 def call(a,packet,emit,output_schema,cancelled):
  seen.append(packet);return {'status':'completed','output':output(packet)}
 monkeypatch.setattr('app.creative.tasks.call',call)

def test_selection_exact_scope_unicode_and_no_automatic_context(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);doc=ev.tools.doc(p,'chapters/chapter-2/draft.txt');quote='江予按住纸角：“我还没有决定。”';i=TEXT.index(quote)
 sel=Selection(path=doc['path'],revision=doc['etag'],start=utf16_index(TEXT,i),end=utf16_index(TEXT,i+len(quote)),quote=quote)
 b=request(ev,p,'selection',selection=sel);v=create(ev,p,b);raw=ev.raw(p,v['id']);packet=ev.packet(p,raw,raw['nodes'][0],0)
 assert quote in packet and '周栖收回手' not in packet and '空白申请' not in packet
 r=ev.validate_result(p,raw,raw['nodes'][0],0,output(packet));assert r['anchors'][0]['evidence'][0]['locations'][0]['start']==sel.start
 assert r['weighted']['score']==73 and r['weighted']['normalized_weights']=={'style':1.0}
 with pytest.raises(ConsoleError):create(ev,p,b.model_copy(update={'selection':sel.model_copy(update={'start':sel.start+1})}))

def test_chapter_range_noncontiguous_and_book_scope(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch)
 for n in [3,7,12]:
  f=root/f'chapters/chapter-{n}/draft.txt';f.parent.mkdir(exist_ok=True);f.write_text(f'第{n}章。'+TEXT,encoding='utf8')
 b=request(ev,p,'chapters');b.targets=[Target(path=f'chapters/chapter-{n}/draft.txt') for n in [3,7,12]]
 v=ev.preview(p,b);assert [s['number'] for s in v['sources']]==[3,7,12] and 1 not in v['gaps']
 r=ev.preview(p,request(ev,p,'range',first=2,last=7));assert [s['number'] for s in r['sources']]==[2,3,7]
 r=ev.preview(p,request(ev,p,'book'));assert len(r['sources'])>=5 and r['estimated_calls']>r['source_count']

def test_invalid_evidence_withdrawn_na_excluded_and_snapshot_conflict(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);b=request(ev,p);v=create(ev,p,b);raw=ev.raw(p,v['id']);n=raw['nodes'][0];packet=ev.packet(p,raw,n,0)
 r=ev.validate_result(p,raw,n,0,output(packet,True));assert r['weighted']['score'] is None and r['withdrawn_quotes']>0 and not r['assessment']['dimensions'][0]['evidence']
 before={str(f):f.read_bytes() for folder in ['state','settings','characters'] for f in (root/folder).rglob('*') if f.is_file()}
 (root/'chapters/chapter-2/draft.txt').write_text(TEXT+'改稿。',encoding='utf8');assert not ev.get(p,v['id'])['is_current']
 with pytest.raises(ConsoleError):asyncio.run(batch(ev,p,v['id']))
 assert all(__import__('pathlib').Path(f).read_bytes()==x for f,x in before.items())

def test_full_text_checkpoint_resume_chapter_comparison_and_no_writes(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);f=root/'chapters/chapter-2/draft.txt';f.write_text(TEXT*220,encoding='utf8');seen=[];mock_calls(monkeypatch,seen)
 before=f.read_bytes();v=create(ev,p,request(ev,p,'book'))
 async def exercise():
  a=await batch(ev,p,v['id'],calls=1);assert a['status']=='PAUSED' and a['models'][0]['weighted'] is None
  count=0
  while a['status']!='COMPLETED' and count<10:a=await batch(ev,p,v['id']);count+=1
  return a
 r=asyncio.run(exercise());assert r['status']=='COMPLETED' and r['models'][0]['coverage']['status']=='FULL_COVERAGE'
 assert r['models'][0]['coverage']['read_characters']==r['models'][0]['coverage']['total_characters'];assert r['models'][0]['weighted']['score']==73
 assert len(seen)==len(r['units']);assert before==f.read_bytes()
 raw=ev.raw(p,r['id']);result=ev.result(p,raw,0,raw['root_node']);assert all(a['evidence'] for a in result['anchors'])
 bridge=ev.bridge(p,r['id'],Bridge(model=0,node=raw['root_node'],dimension='style',etag=r['etag'],confirm=True));assert ev.center.get(p,bridge['review_id'])['evidence_current']
 with pytest.raises(ConsoleError):ev.get(p+'bad',r['id'])
 v2=create(ev,p,request(ev,p));r2=asyncio.run(batch(ev,p,v2['id']));c=ev.compare(p,Compare(ids=[r['id'],r2['id']]));assert 'DIFFERENT_SCOPE' in c['warnings'] and not c['items'][1]['direct_trend']

def test_cancel_late_result_cannot_complete_and_resume_retries_explicitly(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);v=create(ev,p,request(ev,p));seen=[]
 def call(a,packet,emit,output_schema,cancelled):
  row=ev.raw(p,v['id']);row['cancel_requested']=True;ev.put(p,row)
  return {'status':'completed','output':output(packet)}
 monkeypatch.setattr('app.creative.tasks.call',call)
 r=asyncio.run(batch(ev,p,v['id']));assert r['status']=='CANCELLED' and r['models'][0]['coverage']['read_units']==0
 with pytest.raises(ConsoleError):asyncio.run(batch(ev,p,v['id']))
 mock_calls(monkeypatch,seen);r=asyncio.run(batch(ev,p,v['id'],retry_incomplete=True));assert r['status']=='COMPLETED' and len(seen)==1

def test_partial_unreadable_source_never_produces_final_total(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);(root/'chapters/chapter-2/draft.txt').write_text('',encoding='utf8');(root/'chapters/chapter-2/draft.md').write_text('',encoding='utf8');seen=[];mock_calls(monkeypatch,seen)
 v=create(ev,p,request(ev,p,'book'));r=asyncio.run(batch(ev,p,v['id']));assert r['status']=='PARTIAL_COVERAGE' and r['models'][0]['weighted'] is None
 assert r['models'][0]['coverage']['unreadable'] and r['models'][0]['partial_result']


def test_second_model_versions_rubric_and_frozen_thresholds(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);seen=[];mock_calls(monkeypatch,seen)
 b=request(ev,p);b.second_model='codex';v=create(ev,p,b);r=asyncio.run(batch(ev,p,v['id']));assert r['same_model_repeat'] and len(seen)==2
 original_rubric=copy.deepcopy(r['rubric']);f=root/'chapters/chapter-2/draft.txt';f.write_text(TEXT+'雨停了，江予仍没松手。',encoding='utf8')
 assert not ev.get(p,r['id'])['is_current']
 v2=create(ev,p,b);r2=asyncio.run(batch(ev,p,v2['id']));c=ev.compare(p,Compare(ids=[r['id'],r2['id']]))
 assert 'DIFFERENT_SCOPE' not in c['warnings'] and c['items'][1]['direct_trend']
 assert ev.raw(p,r['id'])['rubric']==original_rubric
 anon=ev.compare(p,Compare(ids=[r['id'],r2['id']],anonymous=True));assert anon['items'][0]['label']=='A' and anon['items'][0]['id'] is None

def test_ended_batch_receipt_cannot_overwrite_a_later_attempt(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);v=create(ev,p,request(ev,p))
 def late(a,packet,emit,output_schema,cancelled):
  r=ev.raw(p,v['id']);r.update(active_attempt='future_batch',active_task=None,status='PAUSED',author_note='newer author note');ev.put(p,r)
  return {'status':'completed','output':output(packet)}
 monkeypatch.setattr('app.creative.tasks.call',late)
 r=asyncio.run(batch(ev,p,v['id']));assert r['status']=='PAUSED' and r['author_note']=='newer author note' and r['models'][0]['coverage']['read_units']==0

def test_horizon_source_identity_and_literary_context_authorization(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);b=request(ev,p);v=create(ev,p,b);raw=ev.raw(p,v['id']);n=raw['nodes'][0];packet=ev.packet(p,raw,n,0);data=json.loads(packet.split('\nEVALUATION_DATA\n')[1]);assert data['target_sources'][0]['number']==2
 value=json.loads(output(packet));value['horizon']='BOOK'
 with pytest.raises(ConsoleError):ev.validate_result(p,raw,n,0,json.dumps(value))
 from app.creative.literary_models import CoreDetails,Save
 record=ev.core.save(p,Save(etag=ev.core.notes.entries(p)['etag'],text='作者选择的思想前提',details=CoreDetails(kind='thought',title='选择与关怀'),confirm=True))['record']
 doc=ev.tools.doc(p,'chapters/chapter-2/draft.txt');sel=Selection(path=doc['path'],revision=doc['etag'],start=2,end=5,quote='江予把')
 b=request(ev,p,'selection',selection=sel);b.literary_ids=[record['id']]
 with pytest.raises(ConsoleError):ev.preview(p,b)
 b.allow_author_context=True;v=create(ev,p,b);assert '作者选择的思想前提' in ev.packet(p,ev.raw(p,v['id']),ev.raw(p,v['id'])['nodes'][0],0)


def test_long_passage_synthesis_never_expands_to_chapter_horizon(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);text=TEXT*220;path='chapters/chapter-2/draft.txt';(root/path).write_text(text,encoding='utf8');doc=ev.tools.doc(p,path);seen=[];mock_calls(monkeypatch,seen)
 selected=Selection(path=path,revision=doc['etag'],start=0,end=utf16_index(text,len(text)),quote=text)
 v=create(ev,p,request(ev,p,'selection',selection=selected));r=asyncio.run(batch(ev,p,v['id']))
 assert r['status']=='COMPLETED' and len(seen)>1
 assert all(json.loads(p.split('\nEVALUATION_DATA\n')[1])['maximum_horizon']=='LOCAL' for p in seen)
 assert r['models'][0]['result']['assessment']['horizon']=='LOCAL'

def test_evaluation_revision_does_not_forward_author_secret_to_writer(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);seen=[];mock_calls(monkeypatch,seen);v=create(ev,p,request(ev,p));r=asyncio.run(batch(ev,p,v['id']));raw=ev.raw(p,r['id']);file=ev.result_file(p,r['id'],0,r['root_node']);result=json.loads(file.read_text(encoding='utf8'));secret='隐藏钥匙的真正用途仅作者知道';result['assessment']['dimensions'][0]['suggestion']='不要暗示'+secret
 from app.library.storage import write
 write(file,result);bridge=ev.bridge(p,r['id'],Bridge(model=0,node=r['root_node'],dimension='style',etag=r['etag'],confirm=True));assert secret in ev.center.get(p,bridge['review_id'])['report']['issues'][0]['message']
 captured={}
 def start(project,b):captured['request']=b.model_dump();return {'id':'fixture','candidate_id':'fixture'}
 monkeypatch.setattr(ev.tools,'start',start)
 from app.creative.reviews import Candidate
 ev.center.candidate(p,bridge['review_id'],Candidate(issue=0,quote=0,location=0,action='polish',model='codex'))
 assert secret not in json.dumps(captured,ensure_ascii=False)
 assert captured['request']['selected_text'] in TEXT


def test_comparison_flags_changed_applicable_dimension_set(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch);seen=[];mock_calls(monkeypatch,seen);a=create(ev,p,request(ev,p));a=asyncio.run(batch(ev,p,a['id']));b=create(ev,p,request(ev,p));b=asyncio.run(batch(ev,p,b['id']))
 from app.library.storage import write
 f=ev.result_file(p,b['id'],0,b['root_node']);r=json.loads(f.read_text(encoding='utf8'));r['assessment']['dimensions'][1].update(status='SCORED',score=70);r['weighted']=weighted(r['assessment']['dimensions'],b['rubric']);write(f,r)
 c=ev.compare(p,Compare(ids=[a['id'],b['id']]));assert 'DIFFERENT_APPLICABLE_DIMENSIONS' in c['warnings'] and not c['items'][1]['direct_trend']

def test_api_model_parameter_binding_changes_are_not_silently_reused(service,monkeypatch):
 ev,p,root=setup(service,monkeypatch)
 from app.ai.models import Provider,Model,Parameters
 provider=Provider(provider_id='fixture',display_name='LOCAL TEST NOT REAL AI',base_url='http://127.0.0.1:12345/v1',available_models=[Model(id='fixture',parameters=Parameters(temperature=.2))],default_model='fixture')
 ev.center.ai_center.put(provider);one=ev.model(p,'fixture::fixture');provider.available_models[0].parameters.temperature=.7;ev.center.ai_center.put(provider);two=ev.model(p,'fixture::fixture')
 assert one['signature']!=two['signature'] and one['generation_parameters']['temperature']==.2
