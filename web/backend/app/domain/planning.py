"""Author planning only. Stable file IDs; no story State mutation."""
import copy,json,re,uuid
from datetime import datetime
from typing import Literal
from pydantic import Field
import yaml
from app.errors import ConsoleError
from app.domain.characters import Strict,Text

class Links(Strict):
    advance:list[str]=Field(default_factory=list)
    open:list[str]=Field(default_factory=list)
    close:list[str]=Field(default_factory=list)
class Foreshadows(Strict):
    introduce:list[str]=Field(default_factory=list)
    advance:list[str]=Field(default_factory=list)
    resolve:list[str]=Field(default_factory=list)
class Arc(Strict):
    character:str
    start:Text=None
    end:Text=None
class Target(Strict):
    chapters:int|None=Field(default=None,ge=1,le=100)
    words:int|None=Field(default=None,ge=0)
class Volume(Strict):
    schema_version:Literal['0.5']='0.5'
    id:str=Field(pattern=r'^volume_[0-9a-f]{32}$')
    number:int=Field(ge=1)
    title:Text=None
    status:Literal['CONCEPT','PLANNED','ACTIVE','COMPLETED','REVISED']='CONCEPT'
    purpose:Text=None
    premise:Text=None
    start_state:Text=None
    end_state:Text=None
    main_conflict:Text=None
    character_arcs:list[Arc]=Field(default_factory=list)
    relationship_arcs:list[str]=Field(default_factory=list)
    plot_threads:Links=Field(default_factory=Links)
    foreshadowing:Foreshadows=Field(default_factory=Foreshadows)
    major_beats:list[str]=Field(default_factory=list)
    climax:Text=None
    aftermath:Text=None
    target:Target=Field(default_factory=Target)
    constraints:list[str]=Field(default_factory=list)
    open_questions:list[str]=Field(default_factory=list)
class POV(Strict):
    character:Text=None
class Scene(Strict):
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    order:int=Field(ge=1)
    pov:Text=None
    location:Text=None
    characters:list[str]=Field(default_factory=list)
    purpose:Text=None
    entry_state:Text=None
    conflict:Text=None
    beat:Text=None
    turn:Text=None
    exit_state:Text=None
    temporal_mode:Literal['PRESENT','FLASHBACK','FLASHFORWARD']='PRESENT'
class ChapterCard(Strict):
    schema_version:Literal['0.5']='0.5'
    id:str=Field(pattern=r'^chapter_[0-9a-f]{32}$')
    number:int=Field(ge=1)
    order:int=Field(ge=1)
    title:Text=None
    status:Literal['IDEA','PLANNED','DRAFTING','DRAFTED','REVIEWING','REVISED','FINAL']='IDEA'
    planning_level:Literal['SKELETON','DETAILED']='SKELETON'
    volume:str=''
    pov:POV=Field(default_factory=POV)
    story_time:Text=None
    temporal_mode:Literal['PRESENT','FLASHBACK','FLASHFORWARD']='PRESENT'
    location:Text=None
    purpose:Text=None
    chapter_goal:Text=None
    characters:list[str]=Field(default_factory=list)
    character_goals:dict[str,str]=Field(default_factory=dict)
    character_arcs_advanced:list[str]=Field(default_factory=list)
    conflict:Text=None
    scenes:list[Scene]=Field(default_factory=list,max_length=30)
    turn:Text=None
    outcome:Text=None
    emotional_change:Text=None
    plot_threads:Links=Field(default_factory=Links)
    foreshadowing:Foreshadows=Field(default_factory=Foreshadows)
    knowledge_changes_expected:list[str]=Field(default_factory=list)
    state_changes_expected:list[str]=Field(default_factory=list)
    must_include:list[str]=Field(default_factory=list)
    must_not_include:list[str]=Field(default_factory=list)
    ending_hook:Text=None
    notes:Text=None
    depends_on:list[str]=Field(default_factory=list)
class PlanAction(Strict):
    action:Literal['add','save','delete','merge','split','move','reorder']
    volume_id:str
    chapter_id:str|None=None
    chapter_ids:list[str]=Field(default_factory=list,max_length=100)
    target_volume:str|None=None
    card:dict|None=None
    etags:dict[str,str]=Field(default_factory=dict)
    confirm:Literal[True]
    confirm_written:bool=False
def dump(value):return yaml.safe_dump(value,allow_unicode=True,sort_keys=False)
def linked(value):return set(x for rows in value.values() for x in rows)

class Planning:
    def __init__(self,registry,characters,proposals):
        import threading
        self.registry=registry;self.characters=characters;self.proposals=proposals
        self._rows_cache={};self._rows_lock=threading.RLock()
    def path(self,id,kind):
        if kind not in ['volume','chapter'] or not re.fullmatch(kind+r'_[0-9a-f]{32}',id):raise ConsoleError('无效规划稳定 ID',403)
        return f'outlines/{kind}s/{id}.yaml'
    def rows(self,project,kind):
        ws=self.registry.workspace(project);model=Volume if kind=='volume' else ChapterCard
        from app.library.storage import safe
        directory=safe(ws.root,f'outlines/{kind}s')
        # resolve() rejects junctions/symlinks for every plan before reading it.
        import copy
        with self._rows_lock:
            key=(str(ws.root.resolve()),kind);cached=self._rows_cache.get(key,{});fresh={};values=[]
            # Metadata traversal remains cheap and rejects unsafe paths. Only
            # changed cards are parsed/validated; callers receive mutable copies.
            for f in sorted(directory.rglob('*.yaml')):
                if not f.is_file():continue
                relative=f.relative_to(ws.root).as_posix();file=ws.resolve(relative);stat=file.stat();signature=(stat.st_mtime_ns,stat.st_ctime_ns,stat.st_size)
                prior=cached.get(relative)
                if prior and prior[0]==signature:row=prior[1]
                else:
                    row=model.model_validate(ws.yaml_file(relative)).model_dump();after=file.stat()
                    if signature!=(after.st_mtime_ns,after.st_ctime_ns,after.st_size):raise ConsoleError('章节卡在读取期间变化，请刷新重试',409)
                    self.path(row['id'],kind)
                fresh[relative]=(signature,row);values.append(copy.deepcopy(row))
            self._rows_cache.pop(key,None);self._rows_cache[key]=fresh
            while len(self._rows_cache)>8:self._rows_cache.pop(next(iter(self._rows_cache)))
            return sorted(values,key=lambda r:(r.get('volume',''),r['number']))
    def get(self,project,id,kind):
        ws=self.registry.workspace(project);path=self.path(id,kind);raw=ws.content(path)
        return {'value':(Volume if kind=='volume' else ChapterCard).model_validate(ws.parse_yaml(raw['content'])).model_dump(),'etag':raw['etag'],'path':path}
    def bases(self,project):
        ws=self.registry.workspace(project)
        return {f['path']:ws.content(f['path'])['etag'] for f in ws.list_files() if f['path'].startswith(('outlines/','characters/')) or f['path'] in ['settings/canon-contract.yaml','state/foreshadowing.yaml','state/plot-threads.yaml']}
    def validate(self,project,ops,allow_written=False):
        volumes={r['id']:r for r in self.rows(project,'volume')};chapters={r['id']:r for r in self.rows(project,'chapter')}
        original=copy.deepcopy(chapters);seen=set()
        for op in ops:
            if op['path'] in seen:raise ConsoleError('重复候选路径',422)
            seen.add(op['path']);kind='volume' if op['path'].startswith('outlines/volumes/') else 'chapter'
            id=op['path'].split('/')[-1].removesuffix('.yaml')
            if self.path(id,kind)!=op['path']:raise ConsoleError('规划路径不匹配',403)
            if kind=='chapter' and id in original and original[id]['status'] not in ['IDEA','PLANNED'] and not allow_written:raise ConsoleError('已进入正文阶段；必须额外确认修改/删除已写章节',409)
            table=volumes if kind=='volume' else chapters
            if op.get('action','write')=='delete':
                if id not in table:raise ConsoleError('删除目标不存在',404)
                del table[id];continue
            if op.get('action','write')!='write':raise ConsoleError('无效规划操作',422)
            value=(Volume if kind=='volume' else ChapterCard).model_validate(self.registry.workspace(project).parse_yaml(op['content'])).model_dump()
            if value['id']!=id:raise ConsoleError('稳定 ID 不匹配',422)
            if kind=='chapter' and value['status'] not in ['IDEA','PLANNED'] and (not allow_written or id not in original or value['status']!=original[id]['status']):raise ConsoleError('V0.5 规划不得进入 DRAFTING 或更后阶段',409)
            table[id]=value
        chars={r['canonical']['id'] for r in self.characters.list(project)};ws=self.registry.workspace(project)
        threads=set(ws.yaml_file('state/plot-threads.yaml').get('threads',{}));foresh=set(ws.yaml_file('state/foreshadowing.yaml').get('foreshadowing',{}))
        def refs(v,allowed,label):
            if set(v)-allowed:raise ConsoleError('不存在的当前项目引用：'+label+' '+str(sorted(set(v)-allowed)),422)
        for v in volumes.values():
            refs([a['character'] for a in v['character_arcs']],chars,'人物弧');refs(linked(v['plot_threads']),threads,'剧情线');refs(linked(v['foreshadowing']),foresh,'伏笔')
        numbers=set()
        for c in chapters.values():
            from app.projects.writing_config import writing
            if c['volume'] or writing(self.registry.get(project))['form']=='novel':refs([c['volume']],set(volumes),'卷')
            refs(c['characters']+list(c['character_goals'])+c['character_arcs_advanced']+([c['pov']['character']] if c['pov']['character'] else []),chars,'人物')
            refs(c['depends_on'],set(chapters)-{c['id']},'章节依赖');refs(linked(c['plot_threads']),threads,'剧情线');refs(linked(c['foreshadowing']),foresh,'伏笔')
            key=(c['volume'],c['number'])
            if key in numbers or c['number']!=c['order']:raise ConsoleError('卷内编号重复或 number/order 不一致',422)
            numbers.add(key);scene_ids=set();orders=set()
            for s in c['scenes']:
                refs(s['characters']+([s['pov']] if s['pov'] else []),chars,'场景人物')
                if s['id'] in scene_ids or s['order'] in orders:raise ConsoleError('场景 ID/order 重复',422)
                scene_ids.add(s['id']);orders.add(s['order'])
        degree={id:len(set(c['depends_on'])) for id,c in chapters.items()};followers={id:set() for id in chapters}
        for id,c in chapters.items():
            for dep in c['depends_on']:followers[dep].add(id)
        ready=[id for id,n in degree.items() if n==0];processed=0
        while ready:
            id=ready.pop();processed+=1
            for other in followers[id]:
                degree[other]-=1
                if degree[other]==0:ready.append(other)
        if processed!=len(chapters):raise ConsoleError('章节依赖存在循环',422)
    def board(self,project,volume=None):
        ws=self.registry.workspace(project);volumes=self.rows(project,'volume');allcards=self.rows(project,'chapter');cards=[c for c in allcards if not volume or c['volume']==volume]
        stats={'chapters':len(cards),'pov':{},'threads':{},'foreshadowing':dict.fromkeys(['introduce','advance','resolve'],0),'character_arcs':{}}
        timeline=[];warnings=[];anchor=None;positions={c['id']:c['order'] for c in cards}
        for c in cards:
            cid=c['pov']['character'] or 'UNSET';stats['pov'][cid]=stats['pov'].get(cid,0)+1
            for t in linked(c['plot_threads']):stats['threads'][t]=stats['threads'].get(t,0)+1
            for key,ids in c['foreshadowing'].items():stats['foreshadowing'][key]+=len(ids)
            for cid in c['character_arcs_advanced']:stats['character_arcs'][cid]=stats['character_arcs'].get(cid,0)+1
            warning=[]
            try:time=datetime.fromisoformat(c['story_time']).timestamp() if c['story_time'] else None
            except ValueError:time=None;warning.append('Story Time 未能解析，人工核对')
            if c['temporal_mode']=='PRESENT' and time is not None:
                if anchor is not None and time<anchor:warning.append('时间倒退且未标 FLASHBACK')
                anchor=time
            for dep in c['depends_on']:
                if dep in positions and positions[dep]>=c['order']:warning.append('依赖章节被排在本章之后')
            timeline.append({'id':c['id'],'number':c['number'],'story_time':c['story_time'],'temporal_mode':c['temporal_mode'],'warnings':warning})
            warnings.extend({'chapter_id':c['id'],'message':w} for w in warning)
        seeds={id:v for id,v in ws.yaml_file('state/foreshadowing.yaml').get('foreshadowing',{}).items() if v.get('status') in ['OPEN','DEVELOPING','READY']}
        return {'volumes':volumes,'chapters':cards,'etags':{c['id']:ws.content(self.path(c['id'],'chapter'))['etag'] for c in allcards},'stats':stats,'timeline':timeline,'warnings':warnings,'foreshadowing':seeds,'threads':ws.yaml_file('state/plot-threads.yaml').get('threads',{})}
    def manual(self,project,request):
        self.characters.writable(project);ws=self.registry.workspace(project)
        from app.projects.writing_config import writing
        if request.volume_id or writing(self.registry.get(project))['form']=='novel':self.get(project,request.volume_id,'volume')
        allcards=self.rows(project,'chapter');before={c['id']:copy.deepcopy(c) for c in allcards};cards=[c for c in allcards if c['volume']==request.volume_id]
        for c in allcards:
            if request.etags.get(c['id'])!=ws.content(self.path(c['id'],'chapter'))['etag']:raise ConsoleError('规划已被外部修改，请刷新合并',409)
        selected=next((c for c in cards if c['id']==request.chapter_id),None)
        if request.action in ['save','delete','merge','split','move'] and not selected:raise ConsoleError('当前卷内不存在此章节',404)
        if request.action=='add':
            cards.append(ChapterCard(id='chapter_'+uuid.uuid4().hex,number=len(cards)+1,order=len(cards)+1,volume=request.volume_id,title='新章节').model_dump());allcards+=cards[-1:]
        elif request.action=='save':
            value=ChapterCard.model_validate(request.card).model_dump()
            if value['id']!=selected['id'] or value['volume']!=selected['volume'] or value['number']!=selected['number'] or value['order']!=selected['order']:raise ConsoleError('编辑不能更改 ID、卷或编号；使用移动/排序操作',422)
            selected.clear();selected.update(value)
        elif request.action=='delete':allcards.remove(selected);cards.remove(selected)
        elif request.action=='merge':
            others=[c for c in cards if c['id'] in request.chapter_ids and c['id']!=selected['id']]
            if len(others)!=1:raise ConsoleError('合并须选择当前卷另一章',422)
            other=others[0]
            for key in ['chapter_goal','conflict','turn','outcome','notes']:selected[key]='；'.join(x for x in [selected[key],other[key]] if x) or None
            for key in ['characters','knowledge_changes_expected','state_changes_expected','must_include','must_not_include','depends_on','character_arcs_advanced']:selected[key]=list(dict.fromkeys(selected[key]+other[key]))
            for key in ['plot_threads','foreshadowing']:
                for field in selected[key]:selected[key][field]=list(dict.fromkeys(selected[key][field]+other[key][field]))
            selected['scenes']+=other['scenes']
            for n,s in enumerate(selected['scenes'],1):s['order']=n
            for c in allcards:c['depends_on']=list(dict.fromkeys(selected['id'] if id==other['id'] else id for id in c['depends_on'] if id!=c['id'] and not (c['id']==selected['id'] and id==other['id'])))
            allcards.remove(other);cards.remove(other)
        elif request.action=='split':
            child=copy.deepcopy(selected);child['id']='chapter_'+uuid.uuid4().hex;child['title']=(child['title'] or '章节')+'（后半）';child['depends_on']=[selected['id']]
            mid=max(1,len(selected['scenes'])//2);child['scenes']=selected['scenes'][mid:];selected['scenes']=selected['scenes'][:mid]
            for n,s in enumerate(child['scenes'],1):s['order']=n
            cards.insert(cards.index(selected)+1,child);allcards.append(child)
        elif request.action=='move':
            self.get(project,request.target_volume,'volume');cards.remove(selected);selected['volume']=request.target_volume
            selected['order']=max([c['order'] for c in allcards if c['volume']==request.target_volume and c!=selected]+[0])+1
        elif request.action=='reorder':
            if len(request.chapter_ids)!=len(set(request.chapter_ids)) or set(request.chapter_ids)!={c['id'] for c in cards}:raise ConsoleError('排序必须包含当前卷全部稳定 ID，且各一次',422)
            table={c['id']:c for c in cards};cards=[table[id] for id in request.chapter_ids]
        for n,c in enumerate(cards,1):c['number']=c['order']=n
        for vid in {c['volume'] for c in allcards}-{request.volume_id}:
            for n,c in enumerate(sorted([x for x in allcards if x['volume']==vid],key=lambda c:c['order']),1):c['number']=c['order']=n
        after={c['id']:c for c in allcards};ops=[]
        for id,c in after.items():
            if c!=before.get(id):ops.append({'path':self.path(id,'chapter'),'action':'write','content':dump(c)})
        for id in set(before)-set(after):ops.append({'path':self.path(id,'chapter'),'action':'delete','content':''})
        if not ops:return {'status':'UNCHANGED','diff':''}
        bases=self.bases(project)
        for op in ops:bases.setdefault(op['path'],None)
        validate=lambda ops:self.validate(project,ops,request.confirm_written)
        value=self.proposals.stage(project,'author_planning_'+request.action,ops,'作者明确执行章节 '+request.action,[],bases,validate)
        return self.proposals.commit(project,value['id'],value['version'],validate)
