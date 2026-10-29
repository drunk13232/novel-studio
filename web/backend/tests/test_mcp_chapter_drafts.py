"""Actual local services and official MCP stdio, never a remote AI substitute."""
import asyncio,json,os,sys,time
from types import SimpleNamespace
from pathlib import Path
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client,StdioServerParameters
from test_creative_maps_audio import local
from app.assistant.models import AssistantSettings,Start,Context
from app.assistant.service import Session
from app.assistant.mcp_bridge import Bridge
from app.assistant.codex_mcp import Runner
from app.ai.controls import RequestControls
from app.errors import ConsoleError

def scoped(local):
 c,app,p=local
 doc=c.post(f'/api/projects/{p}/studio/drafts',json={'number':1,'title':'Original draft'});assert doc.status_code==201,doc.text
 s=Session(app.state.assistant,Start(instruction='Save an isolated original candidate',context=Context(project=p)),AssistantSettings(mode='draft',manuscript=True,max_steps=64))
 s.manager=app.state.assistant.manager(p);s.model=SimpleNamespace(id='LOCAL_PROTOCOL_TEST');s.provider=SimpleNamespace(provider_id='local-action',display_name='Local protocol test')
 return c,app,p,s,doc.json()

def body(doc,text='Original candidate 正文。'):
 return {'number':1,'revision':doc['etag'],'content':text,'note':'Original test only'}

def test_stage_persists_real_diff_without_touching_manuscript(local):
 c,app,p,s,doc=scoped(local);result=s.call('stage_chapter_draft',body(doc))
 assert result['ok'];row=result['result'];assert row['status']=='PROPOSED' and row['requires_author_acceptance']
 assert app.state.registry.workspace(p).content(doc['path'])['content']==doc['content']
 candidate=app.state.studio_tools.candidate(p,row['id']);assert candidate['candidate']=='Original candidate 正文。'
 r=s.call('read_chapter_candidate',{'id':row['id'],'limit':5})
 assert r['ok'] and r['result']['partial'] and r['result']['text']=='Origi'
 assert r['result']['not_canon'] and r['result']['source_current']
 assert app.state.studio_tools.draft_view(p,row['id'])['source_current']

def test_no_permission_stale_archive_and_protected_source(local):
 c,app,p,s,doc=scoped(local);s.settings.manuscript=False
 assert not s.call('stage_chapter_draft',body(doc))['ok']
 s.settings.manuscript=True
 assert not s.call('stage_chapter_draft',{**body(doc),'revision':'a'*64})['ok']
 ws=app.state.registry.workspace(p);ws.save(doc['path'],doc['content']+'Author edit',doc['etag'])
 assert not s.call('stage_chapter_draft',body(doc))['ok']
 # Original protection is enforced before candidates can be staged.
 app.state.studio_tools.doc=lambda *a:{**doc,'editable':False}
 assert not s.call('stage_chapter_draft',body(doc))['ok']

def test_suggestion_mode_requires_confirmation_and_cancel_does_not_write(local):
 c,app,p,s,doc=scoped(local);s.settings.mode='suggest'
 r=s.call('stage_chapter_draft',body(doc));assert r['pending_confirmation']
 assert not list((app.state.registry.workspace(p).root/'metadata/studio/candidates').glob('*.json'))
 s.stop();assert app.state.registry.workspace(p).content(doc['path'])['content']==doc['content']

def test_model_stage_honors_author_timeout_and_remaining_deadline():
 now=time.monotonic();r=Runner.__new__(Runner);r.session=SimpleNamespace(deadline=now+230,ai_controls=RequestControls(parameters={'timeout':240}))
 assert 229<r.model_timeout()<=230
 r.session.deadline=time.monotonic()+12;assert 11<r.model_timeout()<=12
 r.session.ai_controls=RequestControls();r.session.deadline=time.monotonic()+300;assert r.model_timeout()==90


def test_official_mcp_accepts_large_utf8_candidate_and_reopens(local):
 c,app,p,s,doc=scoped(local);bridge=Bridge(s);text='独立原创测试段落。'*1200
 assert len(json.dumps(body(doc,text),ensure_ascii=False).encode())>20000
 async def verify():
  env={**os.environ,'NOVEL_MCP_URL':bridge.url,'NOVEL_MCP_CAP':bridge.token,'PYTHONPATH':str(Path(__file__).resolve().parents[1])}
  async with stdio_client(StdioServerParameters(command=sys.executable,args=['-m','app.assistant.mcp_server'],env=env)) as (reader,writer):
   async with ClientSession(reader,writer) as mcp:
    await mcp.initialize();tools=await mcp.list_tools();names={x.name for x in tools.tools}
    assert {'stage_chapter_draft','read_chapter_candidate'}<=names
    r=await mcp.call_tool('stage_chapter_draft',body(doc,text));assert not r.is_error,r
    value=r.structured_content;assert value['ok'];receipt=value['result']
    r=await mcp.call_tool('read_chapter_candidate',{'id':receipt['id'],'limit':8000});assert not r.is_error
    assert r.structured_content['result']['text']==text[:8000]
    pending=await mcp.call_tool('start_creative_writing',{'number':1,'context_id':'ctx_'+'a'*32,'goal':'Author approval test only'})
    assert not pending.is_error and pending.structured_content['pending_confirmation']
    assert pending.structured_content['ok'] is False
    s.stop()
    assert app.state.registry.workspace(p).content(doc['path'])['content']==doc['content']
 try:asyncio.run(verify())
 finally:bridge.close()


def test_incremental_candidate_is_versioned_not_an_overwrite(local):
 c,app,p,s,doc=scoped(local)
 first=s.call('stage_chapter_draft',body(doc,'第一段正文。'))['result']
 second=s.call('stage_chapter_draft',{**body(doc,'第二段正文。'),'parent_id':first['id']})['result']
 assert first['id']!=second['id']
 assert app.state.studio_tools.candidate(p,first['id'])['candidate']=='第一段正文。'
 assert app.state.studio_tools.candidate(p,second['id'])['candidate']=='第一段正文。\n\n第二段正文。'
 assert second['counts']['han']==10
 # Author-edited candidate cannot be silently folded into another generated version.
 from app.studio_tools import CandidateDraft
 t=app.state.studio_tools;v=t.draft_view(p,second['id']);t.save_draft(p,second['id'],CandidateDraft(etag=v['etag'],text='Author edit'))
 assert not s.call('stage_chapter_draft',{**body(doc,'More'),'parent_id':second['id']})['ok']
 assert app.state.registry.workspace(p).content(doc['path'])['content']==doc['content']


def test_candidate_reference_is_explicit_bounded_and_stale_checked(local):
 c,app,p,s,doc=scoped(local)
 from app.creative.writing import ContextChoice,Approval
 from app.studio_tools import CandidateDraft
 from app.library.storage import write
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
 candidate=s.call('stage_chapter_draft',body(doc,'独立的候选原文。\n\n'*500))['result']
 writing=app.state.writing_assist
 base=ContextChoice(path=doc['path'],revision=doc['etag'])
 empty=writing.preview(p,base);explicit=writing.preview(p,base.model_copy(update={'candidate_ids':[]}))
 assert 'candidate_ids' not in empty['choice'] and empty['context_hash']==explicit['context_hash']
 row=writing.preview(p,base.model_copy(update={'candidate_ids':[candidate['id']]}))
 source=next(x for x in row['sources'] if x['id']=='candidate:'+candidate['id'])
 assert source['basis']=='AUTHOR_SELECTED_DRAFT_NOT_CANON_NOT_ACTOR_KNOWLEDGE'
 assert len(source['text'])<=8020 and 'SELECTED_DRAFT_NOT_CANON' in row['warnings']
 writing.approve(p,row['id'],Approval(context_hash=row['context_hash'],confirm=True))
 v=app.state.studio_tools.draft_view(p,candidate['id']);app.state.studio_tools.save_draft(p,candidate['id'],CandidateDraft(etag=v['etag'],text='Author changed this candidate'))
 with pytest.raises(ConsoleError):writing.use_context(p,row['id'])
 assert app.state.registry.workspace(p).content(doc['path'])['content']==doc['content']

def test_writer_context_discovery_does_not_approve_or_start_model(local):
 c,app,p,s,doc=scoped(local)
 from app.creative.writing import ContextChoice,Approval
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
 r=s.call('get_approved_writing_context',{'number':1});assert r['ok'] and r['result']['needs_author_review']
 v=app.state.writing_assist.preview(p,ContextChoice(path=doc['path'],revision=doc['etag']))
 assert s.call('get_approved_writing_context',{'number':1})['result']['contexts']==[]
 with pytest.raises(ConsoleError):app.state.assistant.actions.execute(s,'start_creative_writing',{'number':1,'context_id':v['id'],'goal':'Original test writing'})
 app.state.writing_assist.approve(p,v['id'],Approval(context_hash=v['context_hash'],confirm=True))
 found=s.call('get_approved_writing_context',{'number':1})['result'];assert found['contexts'][0]['id']==v['id'] and not found['needs_author_review']
 assert not list((app.state.registry.workspace(p).root/'metadata/studio/director').glob('*.json'))


def test_saved_dialogue_retains_only_safe_candidate_pointer(local):
 c,app,p,s,doc=scoped(local);s.settings.save_conversation=True
 candidate=s.call('stage_chapter_draft',body(doc,'Private candidate text must stay out of dialogue tool receipts'))['result']
 s.output='Saved candidate';s.chat_status='SUCCEEDED';s.ended=True
 app.state.assistant.conversations.put(s)
 from app.assistant.conversations import Conversations,ChatStep
 rows=Conversations(app.state.assistant.root).page(p,s.persona,s.chat_model)['rows']
 assert rows[-1]['steps'][0]['candidate_id']==candidate['id']
 assert rows[-1]['steps'][0]['candidate_path']==doc['path']
 assert 'Private candidate text' not in json.dumps(rows)
 from pydantic import ValidationError
 with pytest.raises(ValidationError):ChatStep(tool='stage_chapter_draft',status='已完成',candidate_id='a'*32,candidate_path='../another-project/final.txt')


def test_candidate_insertion_uses_exact_unique_anchor_and_preserves_old(local):
 c,app,p,s,doc=scoped(local)
 one=s.call('stage_chapter_draft',body(doc,'开端。\n\n唯一转折。\n\n结尾。'))['result']
 two=s.call('stage_chapter_draft',{**body(doc,'新增的中间场景。'),'parent_id':one['id'],'insert_before':'唯一转折。'})
 assert two['ok']
 assert app.state.studio_tools.candidate(p,two['result']['id'])['candidate']=='开端。\n\n新增的中间场景。\n\n唯一转折。\n\n结尾。'
 assert app.state.studio_tools.candidate(p,one['id'])['candidate']=='开端。\n\n唯一转折。\n\n结尾。'
 assert not s.call('stage_chapter_draft',{**body(doc),'parent_id':one['id'],'insert_before':'不存在'})['ok']
 duplicated=s.call('stage_chapter_draft',body(doc,'重复。重复。'))['result']
 assert not s.call('stage_chapter_draft',{**body(doc),'parent_id':duplicated['id'],'insert_before':'重复。'})['ok']


def test_director_body_candidate_preserves_chapter_heading_when_extended(local):
 c,app,p,s,doc=scoped(local)
 from app.studio_tools import utf16_index
 original=doc['content'];length=utf16_index(original,len(original))
 parent=app.state.studio_tools.stage_replacement(p,doc['path'],doc['etag'],length,length,'','Existing writer prose.\n\nEnd.',{'kind':'creative-director'},allow_insert=True,limit=32000)
 result=s.call('stage_chapter_draft',{**body(doc,'New middle scene.'),'parent_id':parent['id'],'insert_before':'End.'})
 assert result['ok'],result
 text=app.state.studio_tools.candidate(p,result['result']['id'])['candidate']
 assert text.startswith(original) and 'New middle scene.\n\nEnd.' in text
 assert app.state.registry.workspace(p).content(doc['path'])['content']==original

def test_partial_director_patch_cannot_be_treated_as_whole_chapter(local):
 c,app,p,s,doc=scoped(local);ws=app.state.registry.workspace(p)
 full=doc['content']+'Real beginning. Middle. Real ending.';doc=ws.save(doc['path'],full,doc['etag'])
 from app.studio_tools import utf16_index
 a=full.index('Middle.');b=a+len('Middle.')
 parent=app.state.studio_tools.stage_replacement(p,doc['path'],doc['etag'],utf16_index(full,a),utf16_index(full,b),'Middle.','New middle.',{'kind':'creative-director'},allow_insert=True,limit=32000)
 assert not s.call('stage_chapter_draft',{**body(doc),'parent_id':parent['id']})['ok']
 assert ws.content(doc['path'])['content']==full


def test_paid_resume_still_requires_fixed_confirmation_but_stop_is_local():
 from app.assistant.actions import TOOLS
 assert TOOLS['start_creative_writing'].level==3
 assert TOOLS['resume_creative_writing'].level==3
 assert TOOLS['stop_creative_writing'].level==1
 assert TOOLS['stage_creative_writing'].level==2


def test_future_or_excluded_candidate_is_not_silently_a_writer_source(local):
 c,app,p,s,doc=scoped(local)
 from app.creative.writing import ContextChoice
 import sys
 sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
 candidate=s.call('stage_chapter_draft',body(doc,'A safe candidate reference.'))['result']
 with pytest.raises(ConsoleError):app.state.writing_assist.preview(p,ContextChoice(path=doc['path'],revision=doc['etag'],candidate_ids=[candidate['id']],exclude=['candidate:'+candidate['id']]))
 future=c.post(f'/api/projects/{p}/studio/drafts',json={'number':2,'title':'Future'}).json()
 later=s.call('stage_chapter_draft',{'number':2,'revision':future['etag'],'content':'Future chapter draft.'})['result']
 with pytest.raises(ConsoleError):app.state.writing_assist.preview(p,ContextChoice(path=doc['path'],revision=doc['etag'],candidate_ids=[later['id']]))


def test_codex_allocation_failure_is_actionable_and_not_an_auth_failure(tmp_path):
 from app.codex.adapter import CodexAdapter
 from app.errors import CodexUnavailable
 a=CodexAdapter(tmp_path);a.request_id='test';a.timings=[];a._started=time.monotonic();events=[]
 def failure():raise RuntimeError('memory allocation of 536870912 bytes failed')
 with pytest.raises(CodexUnavailable,match='内存分配失败') as error:a._step('initialize','初始化 SDK',lambda *args:events.append(args),failure)
 assert '草稿仍保留' in str(error.value) and '不证明登录失效' in str(error.value)
 assert '536870912' not in str(error.value) and events[-1][2]['phase_status']=='failed'


def test_long_mcp_goal_keeps_full_instructions_but_bounds_plan_summary(local,monkeypatch):
 c,app,p,s,doc=scoped(local)
 from app.creative.writing import ContextChoice,Approval
 sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts'))
 ctx=app.state.writing_assist.preview(p,ContextChoice(path=doc['path'],revision=doc['etag']))
 app.state.writing_assist.approve(p,ctx['id'],Approval(context_hash=ctx['context_hash'],confirm=True))
 s.ai_controls=RequestControls(model='codex');goal='Original author goal. '*90;captured={}
 def create(project,body):
  captured['goal']=body.goal
  return {'id':'director_'+'b'*32,'etag':'c'*64}
 def patch(project,id,body):
  assert len(body.plan.summary)==1500
  assert body.plan.steps[0].instruction=='Write one original scene.'
  raise ConsoleError('STOP_BEFORE_MODEL',409)
 monkeypatch.setattr(app.state.creative_director,'create',create)
 monkeypatch.setattr(app.state.creative_director,'patch',patch)
 with pytest.raises(ConsoleError,match='STOP_BEFORE_MODEL'):
  app.state.assistant.actions.execute(s,'start_creative_writing',{'number':1,'context_id':ctx['id'],'goal':goal,'steps':['Write one original scene.']})
 assert captured['goal']==goal and len(goal)>1500
 assert app.state.registry.workspace(p).content(doc['path'])['content']==doc['content']


def test_saved_history_keeps_safe_director_pointer_without_task_payload(local):
 c,app,p,s,doc=scoped(local);s.settings.save_conversation=True
 s.call('stage_chapter_draft',body(doc))
 s.steps[-1]['result'].update(record_id='director_'+'d'*32,internal_prompt='DO_NOT_PERSIST_INTERNAL_PROMPT')
 s.output='Local task reference only';s.chat_status='SUCCEEDED';s.ended=True
 app.state.assistant.conversations.put(s)
 from app.assistant.conversations import Conversations,ChatStep
 rows=Conversations(app.state.assistant.root).page(p,s.persona,s.chat_model)['rows']
 assert rows[-1]['steps'][0]['record_id']=='director_'+'d'*32
 assert rows[-1]['steps'][0]['record_path']==doc['path']
 assert 'DO_NOT_PERSIST_INTERNAL_PROMPT' not in json.dumps(rows)
 from pydantic import ValidationError
 with pytest.raises(ValidationError):ChatStep(tool='start_creative_writing',status='已完成',record_id='director_'+'e'*32,record_path='../other-project/draft.txt')


def test_routing_error_is_classified_after_large_diagnostic_prefix(tmp_path):
 from app.codex.adapter import CodexAdapter
 from app.errors import CodexUnavailable
 a=CodexAdapter(tmp_path);a.request_id='test';a.timings=[];a._started=time.monotonic()
 def failure():raise RuntimeError('diagnostic prefix '*180+'workspace routing discovery timed out')
 with pytest.raises(CodexUnavailable,match='工作区路由发现失败或超时') as error:a._step('initialize','初始化 SDK',lambda *args:None,failure)
 assert 'diagnostic prefix' not in str(error.value)
