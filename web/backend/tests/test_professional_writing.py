"""Focused 2.11 guards. Inference doubles are explicitly MOCK, not AI acceptance."""
import asyncio,json,copy,re
import pytest,yaml
from test_creative_director import lab
from app.creative.plot_matrix import PlotMatrix,Save,Track,Milestone
from app.creative.text_statistics import measure,calculate,Request,snapshot
from app.creative.writing import ContextChoice,Approval
from app.creative.director import Create
from app.creative.reviews import Start
from app.errors import ConsoleError
from app.library.storage import uid

@pytest.fixture
def matrix(lab):
    s,p,pr,path,doc,ctx=lab
    return PlotMatrix(s.tools,s.center),lab

def test_matrix_links_stable_scenes_without_touching_state(matrix):
    m,(s,p,pr,path,d,ctx)=matrix;v=m.get(p);c=v['chapters'][0];before={str(f):f.read_bytes() for f in (pr/'state').rglob('*') if f.is_file()}
    track=Track(name='合作与分歧',kind='relationship',milestones=[Milestone(chapter_id=c['id'],scene_ids=[c['scenes'][0]['id']] if c['scenes'] else [],stage='有条件合作')])
    after=m.save(p,Save(etag=v['etag'],board_etag=v['board_etag'],tracks=[track],confirm=True))
    assert after['tracks'][0]['id']==track.id and after['authority']=='AUTHOR_PLANNING_NOT_STATE'
    assert all(f.read_bytes()==data for f,data in [( __import__('pathlib').Path(k),v) for k,v in before.items()])
    with pytest.raises(ConsoleError):m.save(p,Save(etag=v['etag'],board_etag=v['board_etag'],tracks=[track],confirm=True))

def test_matrix_rejects_foreign_scene_and_unproven_actual_growth(matrix):
    m,(s,p,pr,path,d,ctx)=matrix;v=m.get(p);c=v['chapters'][0]
    for milestone in [Milestone(chapter_id=c['id'],scene_ids=['scene_missing']),Milestone(chapter_id=c['id'],basis='TEXT_OBSERVATION',source_path=path,quote='不存在的证据',revision=d['etag'])]:
        with pytest.raises(ConsoleError):m.save(p,Save(etag=v['etag'],board_etag=v['board_etag'],tracks=[Track(name='候选',milestones=[milestone])],confirm=True))

def test_context_scene_is_approved_filtered_and_stale_plan_rejected(matrix):
    m,(s,p,pr,path,d,ctx)=matrix;v=m.get(p);c=v['chapters'][0];path=c['manuscript_path'];doc=s.tools.doc(p,path)
    scene={'id':'scene_test_safe','order':1,'pov':c['pov']['character'],'location':None,'characters':c['characters'],'purpose':'把信交还，保留合作可能。','entry_state':None,'conflict':'ISOLATED_SECRET','beat':None,'turn':None,'exit_state':None,'temporal_mode':'PRESENT'}
    c={k:v for k,v in c.items() if k not in {'locked','lock_reason','manuscript_path'}};c['scenes']=[scene]
    plan=pr/s.tools.planning.path(c['id'],'chapter');plan.write_text(yaml.safe_dump(json.loads(json.dumps(c)),allow_unicode=True),'utf8')
    char=next((pr/'characters').glob('*.yaml'));ch=yaml.safe_load(char.read_text('utf8'));ch.setdefault('secrets',{})['author_only']=['ISOLATED_SECRET'];char.write_text(yaml.safe_dump(ch,allow_unicode=True),'utf8')
    choice=ContextChoice(path=path,revision=doc['etag'],scene_id=scene['id'],pov=c['pov']['character'] or '')
    out=s.writing.preview(p,choice);source=next(x for x in out['packet']['sources'] if x['id'].startswith('scene-plan:'))
    assert 'ISOLATED_SECRET' not in json.dumps(out,ensure_ascii=False) and '把信交还' in source['text']
    s.writing.approve(p,out['id'],Approval(context_hash=out['context_hash'],confirm=True))
    row=s.create(p,Create(path=path,revision=doc['etag'],context_id=out['id'],goal='继续这一场。',executor='codex'))
    assert row['scene_reference']['basis']=='APPROVED_SCENE_PLAN_NOT_FACT'
    c['scenes'][0]['purpose']='作者修改了计划。';plan.write_text(yaml.safe_dump(json.loads(json.dumps(c)),allow_unicode=True),'utf8')
    with pytest.raises(ConsoleError):s.writing.use_context(p,out['id'])

def test_context_debugger_describes_real_budget_and_exclusion(lab):
    s,p,pr,path,d,c=lab;id=c['sources'][0]['id'];x=s.writing.preview(p,ContextChoice(**{**c['choice'],'exclude':[id]}))
    assert x['diagnostics']['token_estimate_not_usage'] and x['diagnostics']['sent_characters']==x['size']
    assert next(v for v in x['diagnostics']['sources'] if v['id']==id)['reason']=='AUTHOR_EXCLUDED'
    assert all(y['id']!=id for y in x['packet']['sources'])

def test_chinese_measurement_quotes_offsets_and_repeated_evidence():
    body='🙂江予握住船票。江予握住船票。江予握住船票。\n“明天再来。”\n'
    v=measure(body,[('江予',['character_a'])]);assert v['han']==len(re.findall(r'[\u3400-\u9fff]',body))
    assert v['sentences']==4 and v['dialogue_han']==4 and v['character_mentions'][0]['count']==3
    assert any(x['text']=='船票' and x['count']==3 for x in v['repeated_words'])
    first=v['character_mentions'][0]['locations'][0];assert first['start']==2 and first['end']==4
    assert v['scene_basis']=='WHOLE_DOCUMENT_NO_SCENE_BOUNDARIES' and not v['unclosed_quote']
    for r in v['repeated_expressions']:
        for loc in r['locations']:assert loc['exact'] in body

def test_statistics_snapshot_before_after_and_foreign_scope(lab):
    s,p,pr,path,d,c=lab;row=calculate(s.reviews,p,Request(path=path));before=(pr/path).read_bytes()
    assert row['method']['basis']=='DETERMINISTIC_MEASUREMENT_NOT_LITERARY_VERDICT'
    (pr/path).write_text('江予把门关上。周栖留下。','utf8');new=calculate(s.reviews,p,Request(path=path,compare_id=row['id']))
    assert new['before_after']['before_revision']!=new['source_revision'] and snapshot(s.reviews,p,row['id'])['source_current'] is False
    assert (pr/path).read_text('utf8')=='江予把门关上。周栖留下。'
    with pytest.raises(ConsoleError):calculate(s.reviews,p,Request(path='../characters/private.yaml'))
    with pytest.raises(ConsoleError):snapshot(s.reviews,'novel_foreign',row['id'])

class ReviewFake:
    def __init__(self,body):self.body=body;self.selected_ai={'backend':'MOCK'}
    def start_task(self,prompt,emit,**kw):return {'status':'completed','output':json.dumps({'verdict':'WARN','summary':'限定范围读者反馈。','issues':[{'severity':'SUGGESTION','message':'留白的动机还不够明确。','evidence':[self.body],'priority':'SUGGESTION','confidence':'MEDIUM'}]},ensure_ascii=False)}
    def close(self):pass

def test_reader_receives_only_contiguous_prose_and_focus(lab,monkeypatch):
    s,p,pr,path,d,c=lab;paths=['chapters/chapter-1/draft.txt','chapters/chapter-2/draft.txt']
    for i,path in enumerate(paths):f=pr/path;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('江予把票递给周栖。' if i==0 else '周栖把票折起来。','utf8')
    seen=[]
    def build(center,project,group,prompt,model=None,**kw):seen.append(prompt);return ReviewFake('周栖把票折起来。')
    monkeypatch.setattr('app.creative.reviews.adapter',build)
    async def go():
        t=s.reviews.start(p,Start(path=paths[0],mode='reader',reader_focus='character',reader_paths=paths))
        task=s.manager(p).get(t['id']);await asyncio.wait_for(task.runner,8)
        assert task.status=='SUCCEEDED',task.error
        row=s.reviews.get(p,t['review_id']);assert row['scope']=='CHAPTER_RANGE' and row['reader_focus']=='character'
        assert row['anchors'][0]['evidence'][0]['path']==paths[1] and row['reader_scope_locked']
        from app.creative.reviews import Decide
        s.reviews.decide(p,row['id'],Decide(etag=row['etag'],issue=0,action='todo'))
        entries=s.writing.workbench.entries(p)
        assert any(n['path']==paths[1] for n in entries['revision_tasks'])
    asyncio.run(go());data=json.loads(seen[0].split('INPUT DATA:\n')[1]);assert data['audience']=='PUBLIC_READER' and data['characters']==[] and 'canon' not in data and 'references' in data
    assert data['reader_focus']=='character' and len(data['visible_range'])==2
    with pytest.raises(ConsoleError):s.reviews.start(p,Start(path=paths[0],mode='reader',include_canon=True))
    f=pr/'chapters/chapter-3/draft.txt';f.parent.mkdir(parents=True,exist_ok=True);f.write_text('第三章。','utf8')
    with pytest.raises(ConsoleError):s.reviews.start(p,Start(path=paths[0],mode='reader',reader_paths=[paths[0],'chapters/chapter-3/draft.txt']))


def test_scene_pov_and_unknown_flashback_never_inherit_present_knowledge(lab):
    s,p,pr,path,d,ctx=lab
    from app.domain.planning import ChapterCard,Scene
    people=[c['canonical']['id'] for c in s.tools.characters.list(p)];vol=s.tools.planning.rows(p,'volume')[0]['id']
    card=ChapterCard(id='chapter_'+'9'*32,number=90,order=90,volume=vol,pov={'character':people[0]},characters=people,story_time='2041-10-03T19:30:00+08:00',scenes=[Scene(id='scene_different_pov',order=1,pov=people[1],characters=people,temporal_mode='FLASHBACK',purpose='回忆一次未注明日期的交谈。')])
    (pr/s.tools.planning.path(card.id,'chapter')).write_text(yaml.safe_dump(card.model_dump(),allow_unicode=True),'utf8')
    value=s.writing.preview(p,ContextChoice(path=path,revision=d['etag'],scene_id='scene_different_pov'))
    assert value['packet']['pov']==people[1] and value['packet']['story_time']=='UNKNOWN'
    assert value['packet']['as_of_committed_chapter']==0 and 'HISTORICAL_TIME_UNKNOWN_NO_RUNTIME_KNOWLEDGE' in value['warnings']
    assert not any(x['kind'] in {'knowledge','state','event','chapter'} for x in value['packet']['sources'])


def test_chapter_title_does_not_inflate_statistics_or_create_fake_scene():
    text='# 第一章 江予\n\n江予握住船票。\n\n***\n周栖接过船票。'
    v=measure(text,[('江予',['one'])])
    assert v['chapter_heading_excluded'] and v['han']==12
    assert len(v['scenes'])==2 and [x['han'] for x in v['scenes']]==[6,6]
    assert v['character_mentions'][0]['count']==1 and v['character_mentions'][0]['locations'][0]['line']==3
    one=measure('# 第一章 标题\n\n正文只有一句。');assert one['scene_basis']=='WHOLE_DOCUMENT_NO_SCENE_BOUNDARIES' and len(one['scenes'])==1 and one['han']==6
