"""Focused correctness gates. Mock model tests are never remote-AI evidence."""
import asyncio,json
import pytest
from app.errors import ConsoleError
from app.creative.director import Candidate,Patch,Plan,Step
from app.creative.director_delivery import DeliveryUpdate,project_delivery,update_delivery
from test_creative_director import lab,new,done,body,fake,Fake

def test_empty_model_completion_does_not_complete_prose(lab,monkeypatch):
    class Empty(Fake):
        def start_task(self,*args,**kwargs):return {'status':'completed','output':''}
    monkeypatch.setattr('app.creative.director.adapter',lambda *args,**kw:Empty(''))
    s,p,*_=lab
    async def run():
        row=new(lab);row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        assert row['status']=='FAILED' and not row['completed'] and row['calls']==1
        assert row['failure']['code']=='NO_PROSE' and not row['delivery']['text_produced']
        assert row['resume_checkpoint']['step_id']==row['plan']['steps'][0]['step_id']
    asyncio.run(run())

def test_partial_output_resumes_same_fixed_step_without_replaying_completed(lab,monkeypatch):
    s,p,*_=lab;seen=[];partial='她推开半扇门。风把裙边吹起来。'
    class Stream(Fake):
        def start_task(self,prompt,emit,**kwargs):
            seen.append(prompt)
            if len(seen)==1:
                emit('llm_delta',partial,{'delta':partial});raise TimeoutError('timed out')
            payload=json.JSONDecoder().raw_decode(prompt[prompt.index('{'):])[0];assert payload['already_completed_draft']==partial
            assert payload['resume_checkpoint']['step_index']==0
            return {'status':'completed','output':'她扶住门框，继续往前走。'}
    monkeypatch.setattr('app.creative.director.adapter',lambda *args,**kw:Stream(''))
    async def run():
        row=new(lab);id=row['id'];row=await done(s,p,await s.control(p,id,body(row,'run')))
        assert row['status']=='FAILED' and row['draft']==partial and row['failure']['code']=='TIMEOUT'
        row=s.get(p,id);row=await done(s,p,await s.control(p,id,body(row,'run')))
        assert row['id']==id and row['calls']==2 and row['completed']==[0]
        assert row['draft']==partial+'她扶住门框，继续往前走。' and row['resume_checkpoint'] is None
    asyncio.run(run())

def test_delivery_distinguishes_prose_length_step_and_adoption(lab,monkeypatch):
    fake(monkeypatch);s,p,*_=lab
    async def run():
        row=new(lab,goal_han=1000);row=await done(s,p,await s.control(p,row['id'],body(row,'run')))
        assert row['status']=='CANDIDATE' and row['delivery']['steps_complete']
        assert row['delivery']['length_state']=='BELOW_TARGET' and not row['delivery']['author_adopted']
        original=row['etag'];one=s.stage(p,row['id'],Candidate(etag=original));two=s.stage(p,row['id'],Candidate(etag=original));three=s.stage(p,row['id'],Candidate(etag=two['record']['etag']))
        assert one['candidate']['id']==two['candidate']['id']==three['candidate']['id']
        assert two['idempotent_replay'] and three['idempotent_replay']
    asyncio.run(run())

def test_preflight_is_local_no_model_call_no_record_or_limit_change(lab,monkeypatch):
    calls=fake(monkeypatch);s,p,*_=lab;row=new(lab)
    row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='两步',steps=[Step(title='开场',instruction='面对阻力'),Step(title='下一步',instruction='行动之后')])) )
    before=s.path(p,row['id']).read_bytes();value=s.preflight(p,row['id'])
    assert not value['model_called'] and len(value['steps'])==2 and value['steps'][0]['basis']=='CURRENT_EXACT_PAYLOAD'
    assert value['steps'][1]['basis']=='FUTURE_OUTPUT_CHARACTER_UPPER_BOUND'
    assert s.path(p,row['id']).read_bytes()==before and s.get(p,row['id'])['calls']==0
    assert all(a.stop.is_set() for _,_,a in calls)

def test_book_delivery_explicit_pin_and_stale_detection(lab):
    s,p,pr,path,doc,ctx=lab;original=(pr/path).read_bytes()
    baseline=project_delivery(s,p)
    assert path in {c['path'] for c in baseline['chapters']}
    row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='新段落仍然只是作者候选。'))
    v=s.stage(p,row['id'],Candidate(etag=row['etag']))
    result=update_delivery(s,p,DeliveryUpdate(etag=baseline['etag'],path=path,candidate_id=v['candidate']['id']))
    selected=next(c for c in result['chapters'] if c['path']==path)
    assert selected['basis']=='SELECTED_UNADOPTED_CANDIDATE' and result['delivery_han']>result['manuscript_han']
    assert (pr/path).read_bytes()==original and result['author_adoption_required']
    (pr/path).write_bytes(original+'另写一句。'.encode())
    changed=project_delivery(s,p);assert path in changed['invalid_paths'] and changed['state']=='PARTIAL_COVERAGE'

def test_book_target_change_needs_author_reason_and_keeps_old_version(lab):
    s,p,*_=lab;before=project_delivery(s,p)
    with pytest.raises(ConsoleError):update_delivery(s,p,DeliveryUpdate(etag=before['etag'],target_han=100000))
    after=update_delivery(s,p,DeliveryUpdate(etag=before['etag'],target_han=100000,reason='作者明确设定本次全书交付目标'))
    assert after['target_han']==100000 and after['goal_versions'][-1]['target_han']==before['target_han']
    with pytest.raises(ConsoleError):update_delivery(s,p,DeliveryUpdate(etag=before['etag'],target_han=50000,reason='过期窗口'))

def test_long_goal_initial_plan_and_optional_scene_are_schema_valid(lab):
    s,p,*_=lab;row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],goal_han=2500,plan=Plan(summary='一次实际选择',steps=[Step(title='决定',instruction='继续',scene={'objective':'得到答复','obstacle':'对方拒绝','choice':'付出代价','consequence':'关系变化'})])))
    assert row['goal_han']==2500 and row['plan']['steps'][0]['scene']['obstacle']=='对方拒绝'
    assert row['goal_versions'][-1]['goal_han'] is None


def test_restart_recovers_persisted_partial_and_requires_budget_confirmation(lab):
    s,p,pr,path,doc,ctx=lab;row=new(lab)
    row.update(active_task='lost-process-task',status='GENERATING',partial='已经落盘的半段正文。',active_step=0,calls=1)
    s.put(p,row);fixed=s.get(p,row['id'])
    assert fixed['draft']=='已经落盘的半段正文。' and not fixed['partial']
    assert fixed['resume_checkpoint']['step_index']==0 and fixed['recovery']['seconds_remaining'] is None
    assert fixed['timing_unknown'] and fixed['failure']['code']=='APPLICATION_RESTARTED'
    again=s.get(p,row['id']);assert again['draft']==fixed['draft']
    confirmed=s.patch(p,row['id'],Patch(etag=again['etag'],limits=again['limits']))
    assert not confirmed['timing_unknown'] and confirmed['draft']==fixed['draft']


def test_accepted_delivery_uses_saved_manuscript_and_selection_can_be_cleared(lab):
    from app.studio_tools import Decision
    s,p,pr,path,doc,ctx=lab;row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='作者选择的续写。'))
    staged=s.stage(p,row['id'],Candidate(etag=row['etag']))['candidate'];book=project_delivery(s,p)
    book=update_delivery(s,p,DeliveryUpdate(etag=book['etag'],path=path,candidate_id=staged['id']))
    s.tools.decide(p,staged['id'],Decision(action='accept',originalHash=staged['originalHash'],candidate=staged['candidate']))
    current=project_delivery(s,p);assert not current['invalid_paths']
    assert any(c['basis']=='ADOPTED_MANUSCRIPT' for c in current['chapters'])
    cleared=update_delivery(s,p,DeliveryUpdate(etag=current['etag'],path=path,candidate_id=None));assert not cleared['invalid_paths']

def test_restart_keeps_partial_rewrite_separate_from_the_full_draft(lab):
    s,p,*_=lab;row=new(lab);row.update(draft='完整候选保留。',rewrite={'quote':'候选','start':2,'end':4},partial='新改的一小段',active_task='gone',status='GENERATING',active_step=0)
    s.put(p,row);fixed=s.get(p,row['id'])
    assert fixed['draft']=='完整候选保留。' and not fixed['partial']
    assert fixed['versions'][-1]['draft']=='完整候选保留。' and fixed['versions'][-1]['partial_rewrite']=='新改的一小段'

def test_runtime_default_is_sdk_bundle_and_explicit_override_is_preserved(tmp_path,monkeypatch):
    import codex_cli_bin
    from app.codex.adapter import codex_binary
    from app.errors import CodexUnavailable
    paired=tmp_path/'paired.exe';paired.write_bytes(b'offline test fixture, not executable')
    override=tmp_path/'explicit.exe';override.write_bytes(b'offline test fixture, not executable')
    monkeypatch.delenv('NOVEL_CODEX_BIN',raising=False);monkeypatch.setattr(codex_cli_bin,'bundled_codex_path',lambda:paired)
    assert codex_binary()==paired.resolve()
    monkeypatch.setenv('NOVEL_CODEX_BIN',str(override));assert codex_binary()==override.resolve()
    monkeypatch.delenv('NOVEL_CODEX_BIN');monkeypatch.setattr(codex_cli_bin,'bundled_codex_path',lambda:tmp_path/'missing.exe')
    with pytest.raises(CodexUnavailable):codex_binary()


def test_step_brief_exposes_actual_position_and_exact_repeats_are_not_verdicts(lab):
    from app.creative.writing_contract import observations
    from app.studio_tools import utf16_slice
    s,p,*_=lab;row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],plan=Plan(summary='两部分',steps=[Step(title='开始',instruction='行动'),Step(title='结尾',instruction='保持退出状态')])))
    first=s.execution_brief(p,row['id'],0)['execution_position'];last=s.execution_brief(p,row['id'],1)['execution_position']
    assert first['remaining_after_current']==1 and not first['is_final_enabled_step']
    assert last['remaining_after_current']==0 and last['is_final_enabled_step']
    paragraph='她把信纸折起来，推开半扇门，决定等对方把话说完。'*5;text='🌧️\n\n'+paragraph+'\n\n'+paragraph
    finding=observations(text,{'sources':[]})['repeated_passage_signals'][0]
    assert utf16_slice(text,finding['repeat']['start'],finding['repeat']['end'])==paragraph
    assert finding['status']=='AUTHOR_REVIEW_NOT_AUTOMATIC_ERROR'

def test_new_draft_does_not_claim_old_diff_as_current_and_repeats_refresh(lab):
    s,p,*_=lab;row=new(lab);row=s.patch(p,row['id'],Patch(etag=row['etag'],draft='初版候选。'));v=s.stage(p,row['id'],Candidate(etag=row['etag']))
    assert v['record']['delivery']['candidate_matches_current_draft']
    changed=s.patch(p,row['id'],Patch(etag=v['record']['etag'],draft='作者另行修改后的候选。'))
    assert not changed['delivery']['candidate_staged'] and not changed['delivery']['author_adopted']
    assert not changed['delivery']['candidate_matches_current_draft']
    assert changed['quality_observations']['text_sha256']
