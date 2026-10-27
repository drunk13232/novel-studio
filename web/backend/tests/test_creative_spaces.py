"""Small cross-space contracts. Fake inference is MOCK; math uses the real engine."""
import asyncio,copy,json,uuid
import pytest
from test_creative_director import lab,new,body,done,fake
from app.creative.materials import Materials,Take,Edit,Origin
from app.creative.writing import ContextChoice,Approval
from app.creative.director import Create
from app.roleplay.service import Roleplay
from app.roleplay.models import Create as SceneCreate,Persona,Actor,Scene
from app.world_logic.service import WorldLogic
from app.world_logic.engine import run
from app.errors import ConsoleError
from app.library.storage import write,safe,uid,now
import yaml

@pytest.fixture
def spaces(lab):
    s,p,pr,path,d,ctx=lab;w=WorldLogic(s.tools.registry,s.tools.registry.knowledge,s.manager,s.center);r=Roleplay(s.tools.registry,s.tools.characters,s.writing.workbench,s.manager,s.center,w)
    return Materials(s.writing,r,w),r,w,lab

def conversation(spaces,text='我可以留下，但你得把条件说清楚。'):
    m,r,w,(s,p,pr,path,d,ctx)=spaces;actor=s.tools.characters.list(p)[0]['canonical']['id'];v=r.create(p,SceneCreate(title='隔离情景',persona=Persona(name='作者'),actors=[Actor(source_id=actor)],scene=Scene(chapter=90)))
    raw=r.checked(p,v['id']);branch=r.branch(raw,raw['active_branch']);node=r.append(p,raw,branch,raw['actors'][0],text,'npc');r.save(p,raw)
    return Take(kind='roleplay',source_id=v['id'],branch_id=branch['id'],node_ids=[node['id']],origin=Origin(path=path,revision=d['etag'],quote='江予把信纸放下。'),confirm=True)

def test_roundtrip_uses_existing_notes_and_requires_new_writer_approval(spaces):
    m,r,w,(s,p,pr,path,d,ctx)=spaces;b=conversation(spaces);before=(pr/path).read_bytes();v=m.take(p,b);assert m.take(p,b)['note_id']==v['note_id'];assert not v['canon_changed'] and not v['writer_approval']
    assert len([n for n in s.writing.workbench.entries(p)['notes'] if n.get('category')=='creative_material'])==1
    req=ContextChoice(**{**ctx['choice'],'material_ids':[v['note_id']]});packet=s.writing.preview(p,req)
    assert packet['status']!='APPROVED' and any(x['kind']=='creative_material' and x['basis']=='AUTHOR_SELECTED_HYPOTHESIS_NOT_CANON' for x in packet['packet']['sources'])
    with pytest.raises(ConsoleError):s.writing.use_context(p,packet['id'])
    s.writing.approve(p,packet['id'],Approval(context_hash=packet['context_hash'],confirm=True));assert s.writing.use_context(p,packet['id'])
    notes=m.list(p);m.edit(p,v['note_id'],Edit(etag=notes['etag'],text='改成另一种选择，仍只是场景假设。'))
    with pytest.raises(ConsoleError):s.writing.use_context(p,packet['id'])
    assert (pr/path).read_bytes()==before

def test_hidden_material_is_blocked_without_echoing_secret(spaces):
    m,r,w,(s,p,pr,path,d,ctx)=spaces
    card=next((pr/'characters').glob('*.yaml'));raw=yaml.safe_load(card.read_text('utf8'));secret='ISOLATED_AUTHOR_SECRET_DO_NOT_SEND'
    raw.setdefault('secrets',{})['author_only']=[secret];card.write_text(yaml.safe_dump(raw,allow_unicode=True),'utf8')
    v=m.take(p,conversation(spaces,'条件性方案：'+secret))
    with pytest.raises(ConsoleError) as failure:s.writing.preview(p,ContextChoice(**{**ctx['choice'],'material_ids':[v['note_id']]}))
    assert secret not in str(failure.value)

def test_stale_origin_and_foreign_branch_cannot_create_material(spaces):
    m,r,w,(s,p,pr,path,d,ctx)=spaces;b=conversation(spaces);b.branch_id='branch_'+uuid.uuid4().hex
    with pytest.raises(ConsoleError):m.take(p,b)
    b=conversation(spaces);(pr/path).write_text('作者已保存新内容。','utf8')
    with pytest.raises(ConsoleError):m.take(p,b)
    with pytest.raises(ConsoleError):m.take('novel_foreign',b)

def test_real_solver_result_returns_as_hypothesis_with_provenance(spaces):
    m,r,w,(s,p,pr,path,d,ctx)=spaces;definition=json.loads((w.resources/'templates/travel.json').read_text('utf8'))
    definition['experiment_id']='exp_'+uuid.uuid4().hex
    for a in definition['assumptions']:a['accepted']=True
    from types import SimpleNamespace
    from app.world_logic.service import fingerprint
    saved=w.save(p,definition);frozen=w.freeze(p,definition['experiment_id'],SimpleNamespace(etag=saved['etag'],reason='Isolated author confirmation'))
    definition=frozen['definition']
    result=run(definition);assert result['status']=='PASS';id=uid('run')
    write(safe(w.root(p),'reports/'+id+'.json'),{**result,'id':id,'project_id':p,'definition':definition,'experiment_id':definition['experiment_id'],'definition_version':1,'definition_fingerprint':fingerprint(definition),'acceptance_fingerprint':fingerprint(definition['acceptance_rules']),'created_at':now()})
    v=m.take(p,Take(kind='world_report',source_id=id,origin=Origin(path=path,revision=d['etag']),confirm=True));note=v['material'];assert '3.0' in note['text'] and '所需时间' in note['text'];assert json.loads(note['note'])['epistemic']=='CONDITIONAL_SOLVER_RESULT_NOT_CANON'
    assert (pr/path).read_text('utf8').startswith('江予把信纸')

def test_director_binds_author_selected_scene_option(spaces,monkeypatch):
    m,r,w,(s,p,pr,path,d,ctx)=spaces;id=uid('scene');option={'title':'谈判','approach':'各自提出条件','beats':['把杯子推过去','保留半扇门'],'emotion':'克制','consequence':'仍可合作'}
    write(s.writing.path(p,'scene',id),{'id':id,'project_id':p,'source_path':path,'source_revision':d['etag'],'kind':'options','result':{'options':[option]}})
    row=s.create(p,Create(path=path,revision=d['etag'],context_id=ctx['id'],goal='继续此场景。',executor='codex',scene_id=id));assert row['scene_reference']['value']==option
    assert '把杯子推过去' in s.writer_prompt(row,s.context(p,row),0)
    with pytest.raises(ConsoleError):s.create(p,Create(path=path,revision=d['etag'],context_id=ctx['id'],goal='错误选项。',executor='codex',scene_id=id,scene_option=2))


def test_uncommitted_scene_uses_previous_committed_knowledge(spaces):
    m,r,w,(s,p,pr,path,d,ctx)=spaces;b=conversation(spaces);row=r.checked(p,b.source_id);snap=row['actors'][0]['snapshot']
    assert snap['requested_scene_chapter']==90 and snap['as_of_chapter']<90 and snap['knowledge_notice']
    view=r.preview(p,row['id'],b.branch_id,row['actors'][0]['id']);assert view['self']['as_of_chapter']==snap['as_of_chapter'] and not view['canonical_authority']


def test_optional_visual_brief_is_scoped_and_needs_no_external_engine(spaces):
    from app.creative.visual import Visual,Brief,Launch,Config
    from app.library.assets import Assets
    from app.library.bible import Bible
    m,r,w,(s,p,pr,path,d,ctx)=spaces;v=Visual(s.tools,m,Assets(s.tools.registry,Bible(s.tools.registry)))
    assert not v.probe(p)['available']
    before=(pr/path).read_bytes();b=v.brief(p,Brief(origin=Origin(path=path,revision=d['etag'],quote='江予把信纸放下。'),scene='渡口两个人物，一封信。',camera='中景，视线平齐。'))
    assert v.get_brief(p,b['id'])['camera']=='中景，视线平齐。' and b['authority'].endswith('NOT_CANON')
    with pytest.raises(ConsoleError):v.get_brief('novel_foreign',b['id'])
    with pytest.raises(ConsoleError):v.launch(p,Launch(brief_id=b['id'],confirm=True))
    pref=v.config(p)
    with pytest.raises(ConsoleError):v.configure(p,Config(etag=pref['etag'],executable='powershell.exe',template='',confirm_trusted=True))
    assert (pr/path).read_bytes()==before
