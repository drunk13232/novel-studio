"""Targeted local contracts; no network, model-quality claims or real user files."""
import json,os,shutil,sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest
from pydantic import ValidationError
ROOT=Path(__file__).resolve().parents[3]
BOOT=TemporaryDirectory(prefix='novel-autonomous-test-');WS=Path(BOOT.name)/'workspace';shutil.copytree(ROOT/'desktop/preview-template',WS)
os.environ['NOVEL_WORKSPACE']=str(WS);os.environ['NOVEL_STUDIO_DATA']=str(Path(BOOT.name)/'data/workspaces');sys.path.insert(0,str(ROOT/'web/backend'))
from app.config import Settings
from app.errors import ConsoleError
from app.creative.writing import ContextChoice,Approval
from app.creative.writing_tools import ScopeSave,WritingAction,ActionSave,Etag,Lookup,saved_scope,save_scope,actions,save_action,delete_action,describe_candidate,candidate_history,lookup
from app.studio_tools import normalized,text_hash,Decision,SelectionRequest,utf16_index

@pytest.fixture
def author(tmp_path,monkeypatch):
    root=tmp_path/'workspace';shutil.copytree(ROOT/'desktop/preview-template',root);monkeypatch.setenv('NOVEL_WORKSPACE',str(root));monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'data/workspaces'))
    from app.main import create_app
    app=create_app(Settings(workspace=root));s=app.state.writing_assist;p=next((root/'projects').glob('novel_*')).name;pr=root/'projects'/p
    path='chapters/chapter-90/draft.txt';f=pr/path;f.parent.mkdir(parents=True);f.write_text('江予拿起信纸。周栖在门边等待。',encoding='utf-8')
    return s,p,pr,path

def choice(s,p,path):
    d=s.tools.doc(p,path);pov=s.tools.characters.list(p)[0]['canonical']['id']
    return ContextChoice(path=path,revision=d['etag'],pov=pov,budget=12000)

def test_reference_choices_persist_but_never_restore_approval_and_cas(author):
    s,p,root,path=author;b=choice(s,p,path);b.queries=['信纸'];b.pinned=['character:'+b.pov]
    before=saved_scope(s,p,path);saved=save_scope(s,p,ScopeSave(etag=before['etag'],choice=b))
    assert saved['scope']['choice']['queries']==['信纸'] and saved['scope']['choice']['pinned']==b.pinned
    assert saved['scope']['writer_review_required'] and not saved['approval_restored']
    assert 'revision' not in saved['scope']['choice'] and 'context_id' not in saved['scope']['choice']
    with pytest.raises(ConsoleError):save_scope(s,p,ScopeSave(etag=before['etag'],choice=b))
    # A new service read sees the same existing preference file, not browser cache.
    assert saved_scope(s,p,path)['scope']==saved['scope']
    context=s.preview(p,ContextChoice(**{**saved['scope']['choice'],'path':path,'revision':b.revision}))
    with pytest.raises(ConsoleError):s.use_context(p,context['id'])
    other='chapters/chapter-91/draft.txt';f=root/other;f.parent.mkdir();f.write_text('另一篇草稿。',encoding='utf-8')
    assert saved_scope(s,p,other)['scope'] is None
    with pytest.raises(ConsoleError):saved_scope(s,'novel_missing',path)

def test_writing_actions_crud_scoped_etag_and_no_privileged_fields(author):
    s,p,root,path=author;pref=actions(s,p);t=WritingAction(name='克制对白',action='dialogue',instruction='保留诉求，减少解释。',candidate_count=2,directions=['克制','犹豫'])
    saved=save_action(s,p,ActionSave(etag=pref['etag'],template=t));id=saved['saved_id'];assert actions(s,p)['templates'][0]['name']=='克制对白'
    with pytest.raises(ConsoleError):save_action(s,p,ActionSave(etag=pref['etag'],template=t))
    with pytest.raises(ValidationError):WritingAction.model_validate({**t.model_dump(),'model':'another-provider','shell':'echo nope'})
    assert not actions(s,p)['contains_model_or_permissions']
    updated=save_action(s,p,ActionSave(etag=saved['etag'],template=WritingAction(**{**t.model_dump(),'id':id,'instruction':'保留事实，使用短句。'})))
    assert updated['templates'][0]['instruction']=='保留事实，使用短句。'
    removed=delete_action(s,p,id,Etag(etag=updated['etag']));assert not removed['templates']
    with pytest.raises(ConsoleError):delete_action(s,p,id,Etag(etag=removed['etag']))

def test_candidate_recovery_is_readonly_after_decision_or_source_change(author):
    s,p,root,path=author;d=s.tools.doc(p,path);c=s.tools.stage_replacement(p,path,d['etag'],0,2,'江予','江予',{'fixture':True})
    listed=candidate_history(s,p,path);assert listed['total']==1 and listed['candidates'][0]['source_current']
    restored=describe_candidate(s,p,c['id']);assert restored['can_accept'] and not restored['read_only_history']
    original=(root/path).read_bytes();s.tools.decide(p,c['id'],Decision(action='reject',originalHash=c['originalHash']));assert (root/path).read_bytes()==original
    assert describe_candidate(s,p,c['id'])['read_only_history']
    c=s.tools.stage_replacement(p,path,d['etag'],0,2,'江予','江予',{'fixture':True});(root/path).write_text('作者已经写了新内容。',encoding='utf-8')
    assert not describe_candidate(s,p,c['id'])['can_accept']
    with pytest.raises(ConsoleError):s.tools.decide(p,c['id'],Decision(action='accept',originalHash=c['originalHash'],candidate='修改'))

def test_recovered_final_candidate_keeps_original_and_checkpoint(author):
    s,p,root,path=author;path='chapters/chapter-90/final.txt';f=root/path;f.write_text('她，，走了。',encoding='utf-8');d=s.tools.doc(p,path);before=f.read_bytes()
    c=s.tools.stage_replacement(p,path,d['etag'],1,3,'，，','，',{'fixture':True});restored=describe_candidate(s,p,c['id'])
    assert restored['can_accept'];result=s.tools.decide(p,c['id'],Decision(action='accept',originalHash=c['originalHash'],candidate='，'))
    assert f.read_bytes()==before and result['file']['path']!=path and describe_candidate(s,p,c['id'])['read_only_history']


def test_lookup_exact_alias_ambiguity_buffer_and_no_canon_writes(author):
    s,p,root,path=author
    from app.projects.service import write_yaml
    for r in s.tools.characters.list(p):
        v=r['canonical'];v['aliases']=['小江'];write_yaml(root/'characters'/(v['id']+'.yaml'),v)
    before={str(f.relative_to(root)):f.read_bytes() for folder in ['state','characters','settings','chapters'] for f in (root/folder).rglob('*') if f.is_file()}
    d=s.tools.doc(p,path);result=lookup(s,p,Lookup(path=path,revision=d['etag'],start=0,end=2,quote='江予'))
    assert result['audience']=='AUTHOR' and not result['writer_context'] and result['matches'][0]['name']=='江予'
    buffer=lookup(s,p,Lookup(path=path,revision=d['etag'],start=0,end=2,quote='小江',source_mode='buffer'))
    assert buffer['ambiguous'] and len(buffer['matches'])==2 and not buffer['selection_bound_to_disk']
    assert all(x['reason']=='ALIAS' for x in buffer['matches'])
    with pytest.raises(ConsoleError):lookup(s,p,Lookup(path=path,revision=d['etag'],start=0,end=2,quote='小江'))
    assert before=={str(f.relative_to(root)):f.read_bytes() for folder in ['state','characters','settings','chapters'] for f in (root/folder).rglob('*') if f.is_file()}


def test_saved_action_still_uses_existing_writer_checks_and_route(author,monkeypatch):
    s,p,root,path=author
    # This integration reads an optional, separately installed Skill, not a
    # bundled fixture. Missing resource is an explicit SKIP, never an AI PASS.
    from app.integrations.stack import installations
    skill_root=installations(s.registry.engine)['novel']
    if not all((skill_root/name).is_file() for name in ('SKILL.md','references/style-fidelity.md','references/cognition-layers-and-language.md')):
        pytest.skip('Optional novel-writing Skill and its two writing references are not installed; real Skill integration is unverified')
    b=choice(s,p,path);ctx=s.preview(p,b);s.approve(p,ctx['id'],Approval(context_hash=ctx['context_hash'],confirm=True))
    t=WritingAction(name='精简',action='condense',instruction='保持事实和口吻，精简重复。',candidate_count=2,directions=['短句','保留留白']);saved=save_action(s,p,ActionSave(etag=actions(s,p)['etag'],template=t));loaded=actions(s,p)['templates'][0]
    d=s.tools.doc(p,path);text=normalized(d);cid,_,_=s.tools.chapter(p,path);captured={}
    class A:selected_ai={'backend':'MOCK_NOT_AI'}
    monkeypatch.setattr('app.creative.tasks.adapter',lambda *a,**kw:A())
    class T:
        id='fixture';private_text=False
        def public(self):return {'id':self.id,'status':'QUEUED'}
    def prepare(*a,**kw):captured.update(prompt=a[1],kwargs=kw);return T()
    monkeypatch.setattr(s.manager(p),'prepared',prepare)
    request=SelectionRequest(project_id=p,chapter_id=cid,path=path,document_revision=d['etag'],originalHash=text_hash(text),start=0,end=2,selected_text='江予',instruction=loaded['instruction'],candidate_count=loaded['candidate_count'],directions=loaded['directions'],action=loaded['action'],style='none',writing_context_id=ctx['id'])
    s.tools.start(p,request);assert captured['kwargs']['ai_task']=='cowrite' and '精简重复' in captured['prompt'] and '保留留白' in captured['prompt']
    request.instruction='不要透露未授权的作者秘密'
    with pytest.raises(ConsoleError):s.tools.start(p,request)


def test_http_mutation_reuses_existing_search_lease(author):
    # HTTP middleware already owns this OS lease. Background output checks do not.
    from app.tasks.lease import acquire,release
    s,p,root,path=author;b=choice(s,p,path);b.queries=['江予']
    lease=acquire(s.registry.engine,'studio-data.lock')
    try:
        c=s.preview(p,b);s.approve(p,c['id'],Approval(context_hash=c['context_hash'],confirm=True))
        assert s.use_context(p,c['id'],locked=True)['context_hash']==c['context_hash']
        d=s.tools.doc(p,path)
        assert lookup(s,p,Lookup(path=path,revision=d['etag'],start=0,end=2,quote='江予'))['matches']
    finally:release(lease)
    assert s.use_context(p,c['id'])['context_hash']==c['context_hash']

