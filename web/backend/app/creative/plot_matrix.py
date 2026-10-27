"""Planning projections over existing ChapterCards and StudioTools preferences.
No new story database or Canon authority. All user edits are author planning.
"""
import json,re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from fastapi import APIRouter
from app.errors import ConsoleError
from app.library.storage import uid,now,write,safe,checkpoint
from app.studio_tools import normalized,text_hash,utf16_index
from app.models.requests import TaskRequest,TaskOptions
from app.projects.foundation import schema
from .tasks import adapter,metadata

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Milestone(Strict):
    chapter_id:str=Field(pattern=r'^chapter_[0-9a-f]{32}$')
    scene_ids:list[str]=Field(default_factory=list,max_length=30)
    stage:str=Field(default='',max_length=120)
    goal:str=Field(default='',max_length=600)
    belief:str=Field(default='',max_length=600)
    relationship:str=Field(default='',max_length=600)
    decision:str=Field(default='',max_length=600)
    emotion:str=Field(default='',max_length=600)
    basis:Literal['PLANNED','TEXT_OBSERVATION']='PLANNED'
    source_path:str=Field(default='',max_length=300)
    quote:str=Field(default='',max_length=1500)
    revision:str=Field(default='',max_length=64)
class Track(Strict):
    id:str=Field(default_factory=lambda:uid('line'),pattern=r'^line_[0-9a-f]{32}$')
    name:str=Field(min_length=1,max_length=120)
    kind:Literal['main','sub','growth','relationship','custom']='custom'
    character_ids:list[str]=Field(default_factory=list,max_length=12)
    origin_thread:str=Field(default='',max_length=100)
    milestones:list[Milestone]=Field(default_factory=list,max_length=1000)
class Save(Strict):
    etag:str=Field(min_length=64,max_length=64)
    board_etag:str=Field(min_length=64,max_length=64)
    tracks:list[Track]=Field(max_length=100)
    confirm:Literal[True]
class Suggest(Strict):
    model:str|None=Field(default=None,max_length=250)
    goal:str=Field(default='',max_length=1500)
    chapter_ids:list[str]=Field(min_length=1,max_length=20)
class Suggestion(Strict):
    summary:str=Field(max_length=2000)
    tracks:list[Track]=Field(max_length=12)
    unknowns:list[str]=Field(default_factory=list,max_length=20)

class PlotMatrix:
    def __init__(self,tools,center):self.tools=tools;self.center=center
    def _series(self,p,chapters,threads):
        """One shared planning projection, without manuscript scans or a new authority."""
        pref=self.tools.preference(p,'plot-matrix');tracks=pref['value'].get('tracks',[])
        chars={c['canonical']['id']:c['canonical']['name'] for c in self.tools.characters.list(p)}
        linked={t.get('origin_thread') for t in tracks};derived=[]
        for id,thread in threads.items():
            if id in linked:continue
            milestones=[{'chapter_id':c['id'],'scene_ids':[],'stage':'','basis':'PLANNED'} for c in chapters if id in sum(c['plot_threads'].values(),[])]
            derived.append({'id':'thread:'+id,'name':thread.get('title') or thread.get('name') or thread.get('summary') or id,'kind':'main' if thread.get('type')=='MAIN' else 'sub','origin_thread':id,'character_ids':[],'milestones':milestones,'readonly':True})
        for id,name in chars.items():
            milestones=[{'chapter_id':c['id'],'scene_ids':[],'stage':c.get('emotional_change') or c.get('outcome') or '', 'goal':c.get('character_goals',{}).get(id,''),'basis':'PLANNED'} for c in chapters if id in c['character_arcs_advanced']]
            if milestones:derived.append({'id':'arc:'+id,'name':name,'kind':'growth','character_ids':[id],'milestones':milestones,'readonly':True})
        return {'tracks':tracks,'derived_tracks':derived,'etag':pref['etag'],'characters':chars,'authority':'AUTHOR_PLANNING_NOT_STATE'}
    def series(self,p):
        # The curve needs existing plotline definitions, not chapter lock states,
        # every file's export/heading status, or a second full planning board.
        chapters=self.tools.planning.rows(p,'chapter')
        threads=self.tools.registry.workspace(p).yaml_file('state/plot-threads.yaml').get('threads',{})
        return self._series(p,chapters,threads)
    def get(self,p):
        board=self.tools.board(p);projection=self._series(p,board['chapters'],board['threads'])
        bodies={c['number']:c for c in self.tools.registry.workspace(p).chapters()}
        for card in board['chapters']:
            body=bodies.get(card['number'],{})
            card['manuscript_path']=(body.get('draft') or body.get('final') or '') if sum(c['number']==card['number'] for c in board['chapters'])==1 else ''
        return {**board,**projection}
    def save(self,p,b):
        ws=self.tools.writable(p)
        with self.tools.lock,ws._save_lock:
            before=self.get(p)
            if before['etag']!=b.etag or before['board_etag']!=b.board_etag:raise ConsoleError('章节或矩阵已变化，请刷新后合并；没有覆盖原数据',409)
            cards={c['id']:c for c in before['chapters']};chars=set(before['characters']);ids=set()
            for t in b.tracks:
                if t.id in ids:raise ConsoleError('剧情线稳定 ID 重复',422)
                ids.add(t.id)
                if set(t.character_ids)-chars:raise ConsoleError('人物不属于当前作品',422)
                if t.origin_thread and t.origin_thread not in before['threads']:raise ConsoleError('关联剧情线已经不存在',409)
                chapters=set()
                for m in t.milestones:
                    if m.chapter_id not in cards or m.chapter_id in chapters:raise ConsoleError('章节不存在或重复关联',422)
                    chapters.add(m.chapter_id)
                    if set(m.scene_ids)-{s['id'] for s in cards[m.chapter_id]['scenes']}:raise ConsoleError('场景不存在，请刷新章节卡',409)
                    if m.basis=='TEXT_OBSERVATION':
                        doc=self.tools.doc(p,m.source_path);cid,_,_=self.tools.chapter(p,m.source_path)
                        if cid!=m.chapter_id or doc['etag']!=m.revision or not m.quote.strip() or m.quote not in normalized(doc):raise ConsoleError('实际变化必须有本章当前正文证据；不会用计划补造事实',409)
            checkpoint(ws.root,'metadata/studio/plot-matrix.json',note='author plot matrix before edit')
            self.tools.put_pref(p,'plot-matrix',{'version':1,'tracks':[t.model_dump() for t in b.tracks],'updated_at':now(),'canon':False},b.etag)
            return self.get(p)
    def suggest(self,p,b):
        self.tools.writable(p);board=self.get(p);cards=[c for c in board['chapters'] if c['id'] in b.chapter_ids]
        if len(cards)!=len(set(b.chapter_ids)):raise ConsoleError('请选择当前作品的章节',422)
        data={'audience':'AUTHOR_PLANNER','goal':b.goal,'characters':board['characters'],'chapter_cards':cards,'existing_tracks':board['tracks']}
        prompt='Suggest editable plot lines and growth milestones based only on supplied plans. Plans are not facts. No files, tools or Canon writes. Return Suggestion JSON. Track kind main/sub/growth/relationship/custom; chapter_id and scene_ids must use supplied IDs. Every milestone basis must be PLANNED, source_path/quote/revision empty. No invented past evidence. Empty tracks when evidence is insufficient.\nDATA:'+json.dumps(data,ensure_ascii=False)
        a=adapter(self.center,p,'scene_design',prompt,b.model,role='AUTHOR');id=uid('matrix')
        def complete(output):
            v=Suggestion.model_validate_json(output).model_dump()
            # AI IDs are replaced by application generated stable IDs, proposals only.
            available={c['id']:{s['id'] for s in c['scenes']} for c in cards}
            for t in v['tracks']:
                t['id']=uid('line')
                if set(t['character_ids'])-set(board['characters']):raise ConsoleError('模型引用了未提供的人物',422)
                for m in t['milestones']:
                    if m['chapter_id'] not in available or set(m['scene_ids'])-available[m['chapter_id']]:raise ConsoleError('模型引用了未提供的场景',422)
                    m.update(basis='PLANNED',source_path='',quote='',revision='')
            row={**v,'id':id,'project_id':p,'status':'PROPOSED','board_etag':board['board_etag'],'ai_metadata':metadata(a),'canon_changed':False}
            write(self.tools.local(p,'matrix-proposals/'+id+'.json'),row);return row
        return self.tools.manager(p).prepared(TaskRequest(type='custom_prompt',prompt='剧情线候选（作者规划）',options=TaskOptions(read_only=True,resume=False)),prompt,True,id,schema(Suggestion),complete,adapter=a,ai_task='scene_design',ai_model=b.model,application_actions=True).public()

def routes(s):
    r=APIRouter(prefix='/api/projects/{p}/studio-tools/matrix')
    @r.get('')
    def get(p:str):return s.get(p)
    @r.put('')
    def save(p:str,b:Save):return s.save(p,b)
    @r.post('/suggest',status_code=202)
    async def suggest(p:str,b:Suggest):return s.suggest(p,b)
    return r
