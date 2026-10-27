"""Targeted local evidence/Diff checks. Synthetic AI responses test validation only."""
import json,os,shutil,sys,time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
PRIVATE=ROOT/'docs/writing-quality/private-checks'
from tempfile import TemporaryDirectory
_BOOTSTRAP=TemporaryDirectory(prefix='novel-quality-test-')
_BOOTROOT=Path(_BOOTSTRAP.name)/'workspace'
shutil.copytree(ROOT/'desktop/preview-template',_BOOTROOT)
os.environ['NOVEL_WORKSPACE']=str(_BOOTROOT)
os.environ['NOVEL_STUDIO_DATA']=str(Path(_BOOTSTRAP.name)/'data/workspaces')
sys.path.insert(0,str(ROOT/'web/backend'))
from app.config import Settings
from app.creative.reviews import Start,Decide
from app.creative.quality import Replacement,Preferences,preferences,put_preferences,local_findings,source_package,finalize,terms,replacement
from app.studio_tools import Decision,normalized
from app.errors import ConsoleError

@pytest.fixture
def center(tmp_path,monkeypatch):
    root=tmp_path/'workspace';shutil.copytree(ROOT/'desktop/preview-template',root)
    monkeypatch.setenv('NOVEL_WORKSPACE',str(root))
    monkeypatch.setenv('NOVEL_STUDIO_DATA',str(tmp_path/'data/workspaces'))
    from app.main import create_app
    app=create_app(Settings(workspace=root));service=app.state.literary_review
    p=next((root/'projects').glob('novel_*')).name
    return service,p,root/'projects'/p

def doc(center,text,path='chapters/chapter-98/draft.txt'):
    service,p,root=center;f=root/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(text,encoding='utf-8');return path

def test_local_exact_minimum_diff_reject_accept_and_history(center):
    service,p,root=center;path=doc(center,'😀她，，走了。\n其他句子不变。\n')
    result=service.start(p,Start(path=path,mode='proofread',engine='local'));report=service.get(p,result['report_id'])
    assert report['anchors'][0]['evidence'][0]['locations'][0]['start']==3
    before=(root/path).read_bytes();candidate=replacement(service,p,report['id'],Replacement(issue=0))
    service.tools.decide(p,candidate['id'],Decision(action='reject',originalHash=candidate['originalHash']))
    assert (root/path).read_bytes()==before and service.get(p,report['id'])['decisions']['0']['action']=='reject'
    with pytest.raises(ConsoleError):replacement(service,p,report['id'],Replacement(issue=0))
    # A new report is an explicit author recheck, not silent revival of rejection.
    result=service.start(p,Start(path=path,mode='proofread',engine='local'));report=service.get(p,result['report_id']);candidate=replacement(service,p,report['id'],Replacement(issue=0))
    saved=service.tools.decide(p,candidate['id'],Decision(action='accept',originalHash=candidate['originalHash'],candidate=candidate['candidate']))
    assert (root/path).read_text(encoding='utf-8')=='😀她，走了。\n其他句子不变。\n'
    receipt=service.get(p,report['id'])['decisions']['0'];assert receipt['action']=='accept' and receipt['pre_revision']
    assert service.get(p,report['id'])['source_current'] is False
    with pytest.raises(ConsoleError):service.tools.decide(p,candidate['id'],Decision(action='accept',originalHash=candidate['originalHash'],candidate=candidate['candidate']))
    assert saved['requires_state_revalidation']

def test_final_creates_separate_revision_and_empty_deletion(center):
    service,p,root=center;path=doc(center,'她，，走了。','chapters/chapter-98/final.txt');old=(root/path).read_bytes()
    report=service.start(p,Start(path=path,mode='proofread',engine='local'))['result'];candidate=replacement(service,p,report['id'],Replacement(issue=0))
    result=service.tools.decide(p,candidate['id'],Decision(action='accept',originalHash=candidate['originalHash'],candidate='，'))
    assert result['file']['path']!=path and (root/path).read_bytes()==old
    path=doc(center,'行末空白  \n');report=service.start(p,Start(path=path,mode='proofread',engine='local'))['result'];candidate=replacement(service,p,report['id'],Replacement(issue=0))
    service.tools.decide(p,candidate['id'],Decision(action='accept',originalHash=candidate['originalHash'],candidate=''))
    assert (root/path).read_text(encoding='utf-8')=='行末空白\n'

def test_stale_body_and_related_evidence_are_rejected(center):
    service,p,root=center;path=doc(center,'她，，走了。');report=service.start(p,Start(path=path,mode='proofread',engine='local'))['result']
    (root/path).write_text('作者已改过：她走了。',encoding='utf-8')
    with pytest.raises(ConsoleError):replacement(service,p,report['id'],Replacement(issue=0))
    assert not service.get(p,report['id'])['source_current']

def build_report(center,path,findings,mode='proofread',related=None):
    service,p,root=center;b=Start(path=path,mode=mode,related_paths=related or [])
    d=service.tools.doc(p,path);body=normalized(d);sources,coverage=source_package(service,p,b,d,body,terms(service,p))
    return finalize(service,p,b,d,body,sources,coverage,findings,'人工构造的校验输入',[],{'backend':'VALIDATION_FIXTURE_NOT_AI'},0)

def issue(path,quote,**kw):return {'kind':'TYPO','message':'校验候选','evidence':[{'path':path,'quote':quote}],'replacement':'建议字','confidence':'HIGH',**kw}

def test_unlocatable_and_unselected_evidence_never_replace(center):
    path=doc(center,'真实原文。');r=build_report(center,path,[issue(path,'捏造原文'),issue('chapters/chapter-99/draft.txt','未授权章')])
    assert all(x['classification']=='REVIEWER_ERROR' and x['replacement'] is None for x in r['report']['issues'])

def test_project_dictionary_protects_names_and_remembers_scope(center):
    service,p,root=center;path=doc(center,'岑雾绫向门外走。她，，停住。')
    prefs=preferences(service,p);put_preferences(service,p,Preferences(etag=prefs['etag'],terms=['岑雾绫']))
    report=build_report(center,path,[issue(path,'岑雾绫')]);assert report['report']['issues'][0]['classification']=='PROTECTED_TERM'
    report=service.start(p,Start(path=path,mode='proofread',engine='local'))['result'];etag=service.get(p,report['id'])['etag']
    service.decide(p,report['id'],Decide(etag=etag,issue=0,action='ignore',ignore_scope='file'))
    again=service.start(p,Start(path=path,mode='proofread',engine='local'))['result'];assert again['report']['issues'][0]['ignored']
    other=doc(center,'她，，停住。','chapters/chapter-99/draft.txt');again=service.start(p,Start(path=other,mode='proofread',engine='local'))['result'];assert not again['report']['issues'][0]['ignored']

def test_cross_chapter_needs_two_current_sources_and_never_math_claim(center):
    service,p,root=center;path=doc(center,'纪遥拿出已熔毁的唯一钥匙。');other=doc(center,'纪遥亲眼看见唯一钥匙熔毁。','chapters/chapter-97/draft.txt')
    finding=issue(path,'纪遥拿出已熔毁的唯一钥匙。',kind='CONTINUITY',evidence=[{'path':path,'quote':'纪遥拿出已熔毁的唯一钥匙。'},{'path':other,'quote':'纪遥亲眼看见唯一钥匙熔毁。'}])
    report=build_report(center,path,[finding],mode='cross_chapter',related=[other]);assert report['report']['issues'][0]['classification']=='TEXT_POTENTIAL_CONFLICT'
    assert report['report']['issues'][0]['replacement'] is None and not report['report']['issues'][0]['math_verified']
    (root/other).write_text('原始证据已改写。',encoding='utf-8');assert not service.get(p,report['id'])['evidence_current']
    report=build_report(center,path,[issue(path,'纪遥拿出已熔毁的唯一钥匙。',kind='KNOWLEDGE')],mode='cross_chapter');assert report['report']['issues'][0]['classification']=='INSUFFICIENT_EVIDENCE'

def test_incremental_existing_fts_only_reads_changed_body(center,monkeypatch):
    service,p,root=center;path=doc(center,'关键词：银钥匙。');service.tools.index(p)
    ws=service.registry.workspace(p);read=ws.content;calls=[]
    def counted(path,*args,**kwargs):
        if path.startswith('chapters/'):calls.append(path)
        return read(path,*args,**kwargs)
    monkeypatch.setattr(ws,'content',counted);service.tools.index(p);assert calls==[]
    (root/path).write_text('关键词：金钥匙。',encoding='utf-8');service.tools.index(p);assert calls==[path]
    assert service.tools.search(p,'金钥匙') and not service.tools.search(p,'银钥匙')

def test_literary_voice_not_local_grammar_errors_and_bounds():
    text='“咋了？没咋，甭管我。”门外。脚步。又停了。山沉默着。“走，走，走！”“我……我只是，想回家。”。。。'
    assert not local_findings('chapters/chapter-1/draft.txt',text)
    with pytest.raises(ValueError):Start(path='x',mode='cross_chapter',queries=['x'*101])


def test_alternative_and_old_report_obey_current_dictionary(center):
    service,p,root=center;path=doc(center,'岑雾绫停下来。')
    report=build_report(center,path,[issue(path,'岑雾绫',replacement='岑雾铃',alternatives=['岑雾零'])])
    before=preferences(service,p);put_preferences(service,p,Preferences(etag=before['etag'],terms=['岑雾绫']))
    for choice in [0,1]:
        with pytest.raises(ConsoleError):replacement(service,p,report['id'],Replacement(issue=0,alternative=choice))
    assert (root/path).read_text(encoding='utf-8')=='岑雾绫停下来。'

def test_multiple_same_names_and_partial_character_edits_protected(center):
    from app.creative.quality import protected_change
    assert protected_change('岑雾绫望向岑雾绫。','岑雾绫望向岑雾绫。','岑雾铃望向岑雾绫。',[{'start':0,'end':10}],['岑雾绫'])
    assert protected_change('岑雾绫走。','绫','铃',[{'start':2,'end':3}],['岑雾绫'])
    assert not protected_change('岑雾绫停下下。','岑雾绫停下下。','岑雾绫停下。',[{'start':0,'end':8}],['岑雾绫'])


def test_existing_assistant_registry_mcp_and_source_permissions():
    from types import SimpleNamespace
    from app.assistant.actions import Actions
    from app.assistant.models import AssistantSettings,Page
    from app.assistant.mcp_bridge import MCP_ACTIONS
    from app.assistant.actions import TOOLS
    assert 'start_literary_review' in MCP_ACTIONS and TOOLS['start_literary_review'].level==2
    assert Page(page='literary',report_id='review_'+'1'*32).report_id
    cfg=AssistantSettings(model='codex-software')
    session=SimpleNamespace(project='p',request_model='codex-software',settings=cfg,persona='rem',center=SimpleNamespace(settings=lambda persona,project=None:cfg),front=lambda name,args:{'tool':name,'args':args})
    actions=object.__new__(Actions);actions.registry=SimpleNamespace(get=lambda p:{'id':p})
    plain=Start(path='chapters/chapter-1/draft.txt',mode='proofread',model='unselected-provider/model').model_dump()
    result=actions.execute(session,'start_literary_review',plain)
    assert result['args']['model']=='codex'
    for changed in [{'include_canon':True},{'character_ids':['someone']},{'reference_ids':['public:x']},{'profile_ids':['profile']}]:
        with pytest.raises(ConsoleError):actions.execute(session,'start_literary_review',{**plain,**changed})


def test_ignore_invalidates_open_candidate_without_touching_body(center):
    service,p,root=center;path=doc(center,'她，，停住。');before=(root/path).read_bytes()
    report=service.start(p,Start(path=path,mode='proofread',engine='local'))['result'];candidate=replacement(service,p,report['id'],Replacement(issue=0))
    service.decide(p,report['id'],Decide(etag=service.get(p,report['id'])['etag'],issue=0,action='ignore'))
    with pytest.raises(ConsoleError):service.tools.decide(p,candidate['id'],Decision(action='accept',originalHash=candidate['originalHash'],candidate='，'))
    assert (root/path).read_bytes()==before
    assert service.get(p,report['id'])['decisions']['0']['history']


def test_parallel_same_issue_reuses_one_guarded_candidate(center):
    from concurrent.futures import ThreadPoolExecutor
    service,p,root=center;path=doc(center,'她，，停住。')
    report=service.start(p,Start(path=path,mode='proofread',engine='local'))['result']
    with ThreadPoolExecutor(max_workers=2) as pool:
        calls=[pool.submit(replacement,service,p,report['id'],Replacement(issue=0)) for _ in range(2)]
        ids=[f.result(timeout=5)['id'] for f in calls]
    assert ids[0]==ids[1] and (root/path).read_text(encoding='utf-8')=='她，，停住。'
