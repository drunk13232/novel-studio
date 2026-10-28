"""Author-controlled Director freedom; protocol fixtures are MOCK, never remote AI."""
import asyncio,copy
import pytest
from test_creative_director import lab,new,body,done,fake
from test_director_console import protocol
from app.creative.director import Control,Patch,Plan,Step,Fork
from app.ai.controls import RequestControls
from app.errors import ConsoleError


def test_selected_step_runs_only_once_with_its_actual_model_and_parameters(lab,monkeypatch):
    s,p,pr,path,*_=lab;calls=protocol(s,monkeypatch);before=(pr/path).read_bytes()
    async def run():
        row=new(lab,'deep',executor='console_fixture::planner',request_controls=RequestControls(parameters={'temperature':.1,'max_output_tokens':500},context={'budget':131072}))
        row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='Two author steps',steps=[Step(title='First',instruction='First permitted scene.'),Step(title='Second',instruction='Second permitted scene.',executor='console_fixture::writer',request_controls=RequestControls(model='console_fixture::writer',parameters={'temperature':.8,'reasoning_effort':'high','max_output_tokens':128},context={'budget':131072}))])))
        row=await done(s,p,await s.control(p,row['id'],body(row,'run',step_index=1,auto_continue=True)))
        assert row['completed']==[1] and len(calls)==1
        assert calls[0]['model']=='writer' and calls[0]['temperature']==.8 and calls[0]['max_completion_tokens']==128
        assert row['usage'][0]['step_index']==1
        assert s.execution_brief(p,row['id'],0)['current_step']['title']=='First'
        with pytest.raises(ConsoleError):await s.control(p,row['id'],body(row,'run',step_index=1))
        row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        assert row['completed']==[1,0] and calls[1]['model']=='planner' and calls[1]['temperature']==.1
        assert (pr/path).read_bytes()==before
    asyncio.run(run())


def test_model_only_step_change_does_not_reuse_other_model_parameters(lab,monkeypatch):
    s,p,*_=lab;calls=protocol(s,monkeypatch)
    async def run():
        row=new(lab,executor='console_fixture::planner',request_controls=RequestControls(parameters={'temperature':.9},context={'budget':131072}))
        row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='Use model defaults',steps=[Step(title='Scene',instruction='Preserve the scene.',executor='console_fixture::writer')])))
        row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        assert row['status']=='CANDIDATE' and calls[0]['model']=='writer'
        assert 'temperature' not in calls[0]
    asyncio.run(run())


def test_confirmation_is_scoped_to_the_step_that_will_actually_run(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab
    async def run():
        row=new(lab,'deep');row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='Author checkpoint',steps=[Step(title='Safe',instruction='Current action.'),Step(title='Important',instruction='An author-approved consequence.',needs_author=True),Step(title='Disabled',instruction='Not scheduled.',enabled=False,needs_author=True)])))
        row=await done(s,p,await s.control(p,row['id'],body(row,'run',auto_continue=True)))
        assert row['completed']==[0] and row['status']=='PAUSED'
        with pytest.raises(ConsoleError):await s.control(p,row['id'],body(row,'run',step_index=1))
        with pytest.raises(ConsoleError):await s.control(p,row['id'],body(row,'run',step_index=2,continue_important=True))
        row=await done(s,p,await s.control(p,row['id'],body(row,'run',step_index=1,continue_important=True)))
        assert row['completed']==[0,1] and row['calls']==2
    asyncio.run(run())


def test_fork_retains_original_and_has_no_implicit_model_or_adoption(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab
    async def run():
        row=await done(s,p,await s.control(p,(initial:=new(lab))['id'],body(initial,'run')))
        row=s.patch(p,row['id'],Patch(etag=row['etag'],instruction='Preserve the exact character voice.'))
        from app.studio_tools import text_hash
        analysis={'id':'py_'+'c'*32,'project':p,'persona':'yoshino','title':'Local opinion','status':'SUCCEEDED','output':'AUTHOR_ONLY_OPINION_MARKER','director_source':{'record_id':row['id'],'draft_sha256':text_hash(row['draft'])}}
        row=s.attach_analysis(p,row['id'],row['etag'],analysis)
        original=copy.deepcopy(row)
        fork=s.fork(p,row['id'],Fork(etag=row['etag'],goal='Independent attempt',keep_draft=True))
        assert fork['id']!=row['id'] and fork['draft']==row['draft'] and fork['completed']==row['completed']
        assert fork['calls']==0 and not fork['usage'] and not fork['active_task'] and 'candidate_id' not in fork
        assert fork['interventions']==row['interventions'] and fork['analysis_notes']==[]
        prompt=s.writer_prompt(fork,s.context(p,fork),0)
        assert 'Preserve the exact character voice.' in prompt and 'AUTHOR_ONLY_OPINION_MARKER' not in prompt
        fresh=s.fork(p,row['id'],Fork(etag=row['etag'],keep_draft=False))
        assert fresh['draft']=='' and fresh['completed']==[]
        assert s.get(p,row['id'])==original
        with pytest.raises(ConsoleError):s.fork(p,row['id'],Fork(etag='0'*64))
        with pytest.raises(ConsoleError):s.fork('other-project',row['id'],Fork(etag=row['etag']))
    asyncio.run(run())


def test_python_notes_are_idempotent_source_bound_and_never_writer_input(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab;row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='Author-kept candidate.'))
    from app.studio_tools import text_hash
    source_hash=text_hash(row['draft'])
    run={'id':'py_'+'a'*32,'project':p,'persona':'yoshino','title':'Local counts','status':'SUCCEEDED','output':'12 paragraphs','director_source':{'record_id':row['id'],'draft_sha256':source_hash}}
    note=s.attach_analysis(p,row['id'],row['etag'],run,'PRIVATE_ANALYSIS_MARKER_X')
    assert len(note['analysis_notes'])==1 and note['draft']==row['draft']
    assert s.attach_analysis(p,row['id'],note['etag'],run)['etag']==note['etag']
    ctx=s.context(p,note);assert 'PRIVATE_ANALYSIS_MARKER_X' not in s.writer_prompt(note,ctx,0)
    assert 'analysis_notes' not in s.snapshot(p,note['id'],note['etag'])
    updated=s.patch(p,note['id'],Patch(etag=note['etag'],draft='A changed candidate.'))
    assert updated['analysis_notes'][0]['candidate_sha256']!=text_hash(updated['draft'])
    with pytest.raises(ConsoleError):s.attach_analysis(p,row['id'],updated['etag'],{**run,'project':'other-project'})
    with pytest.raises(ConsoleError):s.attach_analysis(p,row['id'],updated['etag'],{**run,'status':'RUNNING'})


def test_duplicate_steps_do_not_inherit_completion_and_legacy_reorder_stays_valid(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab
    async def run():
        row=new(lab);row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        steps=copy.deepcopy(row['plan']['steps']);duplicate=copy.deepcopy(steps[0]);duplicate['step_id']=None
        row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='Duplicate author step',steps=[Step.model_validate(steps[0]),Step.model_validate(duplicate)])))
        assert row['completed']==[0] and row['plan']['steps'][0]['step_id']!=row['plan']['steps'][1]['step_id']
        with pytest.raises(ValueError):Plan(summary='Invalid IDs',steps=[Step.model_validate(row['plan']['steps'][0])]*2)
    asyncio.run(run())


def test_note_removal_preserves_candidate_and_allows_explicit_reattachment(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab;row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='Retained candidate.'))
    from app.studio_tools import text_hash
    run={'id':'py_'+'b'*32,'project':p,'persona':'rem','title':'Count','status':'SUCCEEDED','output':'local result','director_source':{'record_id':row['id'],'draft_sha256':text_hash(row['draft'])}}
    value=s.attach_analysis(p,row['id'],row['etag'],run);removed=s.remove_analysis(p,row['id'],run['id'],value['etag'])
    assert removed['analysis_notes']==[] and removed['draft']==row['draft']
    assert len(s.attach_analysis(p,row['id'],removed['etag'],run)['analysis_notes'])==1


def test_toggling_completed_step_preserves_work_without_repeating_calls(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,*_=lab
    async def run():
        row=new(lab);row=await done(s,p,await s.control(p,row['id'],body(row,'run')));text=row['draft']
        for enabled in [False,True]:
            step=Step.model_validate(row['plan']['steps'][0]);step.enabled=enabled
            row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='Visibility only',steps=[step])))
            assert row['completed']==[0] and row['draft']==text
        with pytest.raises(ConsoleError):await s.control(p,row['id'],body(row,'run'))
        assert len(calls)==1
    asyncio.run(run())
