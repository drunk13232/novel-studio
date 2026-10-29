"""Author UI adapters over existing notes, index, anchors, revisions and backups.
No Writer input, semantic reviewer, Canon migration or independent task engine.
"""
import json,re,uuid,threading,io
from typing import Literal
from fastapi import APIRouter,UploadFile,File
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.library.storage import safe,read,write,write_bytes,checkpoint,digest,now,revisions
from app.library.document_parse import file_type,decode
from app.studio_tools import normalized,utf16_index,utf16_slice,Decision
from app.library.knowledge import AnchorRequest

from app.creative.literary_models import CoreDetails
from app.planning_center import Schedule, plan_overview, impact_preview

class Entry(BaseModel):
    model_config=ConfigDict(extra='forbid')
    etag:str;id:str='';kind:str=Field(pattern='^(inspiration|todo|revision)$')
    text:str=Field(min_length=1,max_length=20000);path:str='';character:str=''
    tags:list[str]=Field(default_factory=list,max_length=20)
    priority:str=Field(default='normal',pattern='^(low|normal|high)$')
    status:str=Field(default='OPEN',pattern='^(OPEN|IN_PROGRESS|DONE|IGNORED|ARCHIVED)$')
    category:str=Field(default='idea',max_length=50);note:str=Field(default='',max_length=4000)
    source:str=Field(default='AUTHOR',max_length=500);severity:str=Field(default='SUGGESTION',pattern='^(MUST_FIX|SHOULD_FIX|SUGGESTION|STYLE_ONLY)$')
    literary:CoreDetails|None=None
    schedule:Schedule|None=None
    annotation_id:str='';start:int=Field(default=0,ge=0);exact:str=Field(default='',max_length=2000);revision:str=''
class ImportCommit(BaseModel):
    model_config=ConfigDict(extra='forbid')
    etag:str;confirm:bool=False;single:bool=False;volume_id:str=''
    chapters:list[dict]=Field(min_length=1,max_length=200)
class EntryState(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(min_length=1,max_length=100)
    status:Literal['OPEN','IN_PROGRESS','DONE','IGNORED','ARCHIVED']|None=None
    trashed:bool|None=None
class EntryStates(BaseModel):
    model_config=ConfigDict(extra='forbid')
    etag:str=Field(pattern=r'^[a-f0-9]{64}$')
    kind:Literal['inspiration','todo','revision']
    updates:list[EntryState]=Field(min_length=1,max_length=100)
class ReplaceRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    query:str=Field(min_length=1,max_length=200);replacement:str=Field(max_length=2000)
    volume:str='';chapter:str='';paths:list[str]=Field(default_factory=list,max_length=100)
    hits:list[dict]=Field(default_factory=list,max_length=500);confirm:bool=False
class Repair(BaseModel):
    model_config=ConfigDict(extra='forbid')
    etag:str;action:str=Field(pattern='^(repair|ignore|defer|delete)$')
    document_revision:str='';start:int=Field(default=0,ge=0);end:int=Field(default=0,ge=0)
    target_type:str='';target_id:str='';confirm:bool=False

class AuthorWorkbench:
    def __init__(self,registry,tools,knowledge,shelf,data):
        self.registry=registry;self.tools=tools;self.knowledge=knowledge;self.shelf=shelf;self.data=data;self.lock=threading.RLock()
    @property
    def global_replace(self):
        with self.lock:
            if not hasattr(self,'_global_replace'):
                from app.global_replace import GlobalReplace
                self._global_replace=GlobalReplace(self)
            return self._global_replace
    def ws(self,p):return self.registry.workspace(p)
    def entries(self,p):return self.shelf.get(p)
    def save_entry(self,p,b):
        ws=self.tools.writable(p)
        with self.lock,self.shelf.lock,ws._save_lock:
            row=self.shelf.get(p)
            if row['etag']!=b.etag:raise ConsoleError('便笺或待办已变化，请刷新后保存',409)
            if b.path:self.tools.doc(p,b.path)
            if b.character and not any(c['canonical']['id']==b.character for c in self.tools.characters.list(p)):raise ConsoleError('人物不属于当前小说',422)
            if b.annotation_id and not any(f.stem==b.annotation_id for f in self.tools.local(p,'annotations').glob('*.json')):raise ConsoleError('批注不属于当前小说',422)
            key='notes' if b.kind=='inspiration' else 'todos' if b.kind=='todo' else 'revision_tasks'
            entries=row.setdefault(key,[]); old=next((v for v in entries if v['id']==b.id),None)
            if b.id and old is None:raise ConsoleError('记录不存在',404)
            if len(entries)>=3000 and not old:raise ConsoleError('请先整理已有记录',422)
            item={**(old or {}),**b.model_dump(exclude={'etag'}),'id':b.id or uuid.uuid4().hex,'at':old.get('at',now()) if old else now(),'updated_at':now(),'canon':False,'project':p}
            # Older notebook clients update status without knowing optional literary metadata.
            # Missing fields preserve the annotation; explicit Literary Core edits remain version checked.
            if old and old.get('literary') and 'literary' not in b.model_fields_set:item['literary']=old['literary']
            if old and 'schedule' not in b.model_fields_set:item['schedule']=old.get('schedule')
            if old:entries[entries.index(old)]=item
            else:entries.append(item)
            row.pop('etag',None);checkpoint(ws.root,'metadata/studio/reading.json','PRE_AUTHOR_NOTE');write(self.shelf.path(p),row);return self.shelf.get(p)
    def update_entry_states(self,p,b):
        """Atomic, reversible notebook state changes; never changes manuscript or Canon.

        The same revision guard is required for Undo. A stale undo cannot overwrite
        a later edit. Validate the entire selection before changing any record.
        """
        ws=self.tools.writable(p)
        with self.lock,self.shelf.lock,ws._save_lock:
            row=self.entries(p)
            if row['etag']!=b.etag:raise ConsoleError('记录已变化，请刷新后重新选择；没有应用任何批量修改',409)
            key={'inspiration':'notes','todo':'todos','revision':'revision_tasks'}[b.kind]
            items={item['id']:item for item in row.get(key,[])}
            ids=[item.id for item in b.updates]
            if len(ids)!=len(set(ids)):raise ConsoleError('重复的记录 ID',422)
            if any(id not in items for id in ids):raise ConsoleError('部分记录不属于当前列表；没有应用任何修改',404)
            if any(not item.model_dump(exclude={'id'},exclude_none=True) for item in b.updates):raise ConsoleError('没有可应用的状态修改',422)
            for item in b.updates:items[item.id].update(**item.model_dump(exclude={'id'},exclude_none=True),updated_at=now())
            row.pop('etag',None);checkpoint(ws.root,'metadata/studio/reading.json','PRE_AUTHOR_NOTE');write(self.shelf.path(p),row)
            return self.entries(p)
    def remove_entry(self,p,kind,id,etag):
        ws=self.tools.writable(p)
        with self.lock,self.shelf.lock,ws._save_lock:
            row=self.entries(p)
            if row['etag']!=etag:raise ConsoleError('记录已变化，请刷新',409)
            key={'inspiration':'notes','todo':'todos','revision':'revision_tasks'}.get(kind)
            item=next((v for v in row.get(key or '',[]) if v['id']==id),None)
            if not item:raise ConsoleError('记录不存在',404)
            item.update(trashed=True,updated_at=now());row.pop('etag',None);checkpoint(ws.root,'metadata/studio/reading.json','PRE_AUTHOR_NOTE');write(self.shelf.path(p),row);return self.entries(p)
    def knowledge_at(self,p,id,chapter=None):
        ws=self.ws(p);char=self.tools.characters.get(p,id);ledger=ws.yaml_file('state/chapter-ledger.yaml').get('entries',[]);committed={x['chapter'] for x in ledger}|{0}
        limit=max(committed) if chapter is None else chapter
        if limit not in committed:raise ConsoleError('只能查看已提交章节或初始化背景',422)
        groups={k:[] for k in ['knows','suspects','false_beliefs','does_not_know','unknown']}
        for fid,fact in ws.yaml_file('state/knowledge-state.yaml').get('facts',{}).items():
            matched=False
            for key,field in [('knows','known_by'),('suspects','suspected_by')]:
                for evidence in fact.get(field,[]):
                    if evidence.get('character_id')!=id:continue
                    n=evidence.get('acquired_chapter',evidence.get('since_chapter'))
                    if isinstance(n,int) and n<=limit and n in committed:
                        groups[key].append({'id':fid,'text':evidence.get('belief') or evidence.get('text') or fact.get('canonical_truth','未设置'),'chapter':n,'event':evidence.get('source_event',''),'source':'state/knowledge-state.yaml','status':'有已提交获得记录'});matched=True
                    elif n is None:groups['unknown'].append({'id':fid,'text':'有当前记录，但缺少获得章节；历史未知','source':'state/knowledge-state.yaml'})
            belief=fact.get('false_beliefs',{}).get(id)
            if belief:
                n=belief.get('acquired_chapter',belief.get('since_chapter'))
                target='false_beliefs' if isinstance(n,int) and n<=limit and n in committed else 'unknown'
                if not isinstance(n,int) or n<=limit:groups[target].append({'id':fid,'text':belief.get('belief','未设置') if target!='unknown' else '错误认知缺少历史凭证','chapter':n,'event':belief.get('source_event',''),'source':'state/knowledge-state.yaml'});matched=True
            if not matched and not any(v['id']==fid for v in groups['unknown']):groups['unknown'].append({'id':fid,'text':'本时期缺少该人物的知识记录；不能推定不知道','source':'state/knowledge-state.yaml'})
        # Explicit does_not_know projection has no history; only current view uses it.
        if chapter is None:
            for fid in char['runtime'].get('knowledge',{}).get('does_not_know',[]):groups['does_not_know'].append({'id':fid,'text':'当前角色投影明确不知道','source':'state/characters/'+id+'.yaml'})
        return {'character':id,'name':char['canonical']['name'],'chapter':limit,'chapters':sorted(committed),'groups':groups,'audience':'AUTHOR','writer_context':False,'note':'没有记录不等于不知道；当前投影不倒推历史。'}
    def relationship_history(self,p):
        ws=self.ws(p);committed={x['chapter'] for x in ws.yaml_file('state/chapter-ledger.yaml').get('entries',[])}|{0};rows=[]
        for rid,rel in ws.yaml_file('state/relationships.yaml').get('relationships',{}).items():
            views=[v for v in rel.get('writer_view',[]) if v.get('since_chapter') in committed]
            views.sort(key=lambda v:v['since_chapter'])
            for i,v in enumerate(views):rows.append({'id':rid+':'+str(i),'characters':rel.get('characters',[]),'before':views[i-1]['text'] if i else '无更早已提交记录','after':v['text'],'chapter':v['since_chapter'],'story_time':v.get('story_time',''),'source':'state/relationships.yaml','direction':'UNSPECIFIED'})
        return rows
    def clues(self,p):
        ws=self.ws(p);data=ws.yaml_file('state/foreshadowing.yaml').get('foreshadowing',{});committed={x['chapter'] for x in ws.yaml_file('state/chapter-ledger.yaml').get('entries',[])}|{0};result=[]
        mapping={'PLANNED':'未展开','UNINTRODUCED':'未展开','INTRODUCED':'正在推进','DEVELOPING':'正在推进','NEAR_PAYOFF':'接近回收','READY':'接近回收','RESOLVED':'已回收','PAID_OFF':'已回收','ABANDONED':'已废弃','DROPPED':'已废弃'}
        values=data.items() if isinstance(data,dict) else [(v['id'],v) for v in data]
        for id,value in values:
            resolved=value.get('resolved_chapter');status=value.get('status','UNKNOWN');valid=resolved in committed and status in {'RESOLVED','PAID_OFF'}
            group=mapping.get(status,'未展开')
            if group=='已回收' and not valid:group='接近回收'
            result.append({**value,'id':id,'group':group,'actual_resolved_chapter':resolved if valid else None,'source':'state/foreshadowing.yaml','note':'计划回收不是已回收','history':[v for v in value.get('writer_view',[]) if v.get('since_chapter') in committed]})
        return result
    def suggestions(self,p,path):
        doc=self.tools.doc(p,path);text=normalized(doc);view=self.knowledge.view(p);names={}
        for n in view['entities']:
            if n['type'] not in {'character','entity','location','faction','item','term','event'}:continue
            labels=[n['name']]
            if n['type']=='character':labels+=self.tools.characters.get(p,n['id'])['canonical'].get('aliases',[])
            for name in labels:
                if isinstance(name,str) and 2<=len(name)<=80:names.setdefault(name,[]).append({'type':n['type'],'id':n['id'],'name':n['name'],'summary':n['summary'][:150]})
        anchors=self.knowledge.anchors(p,path);rows=[]
        for name,targets in names.items():
            for m in re.finditer(re.escape(name),text):
                start=utf16_index(text,m.start());end=utf16_index(text,m.end())
                if any(a['located'] and a['start']==start and a['end']==end for a in anchors):continue
                rows.append({'text':name,'start':start,'end':end,'excerpt':text[max(0,m.start()-25):m.end()+25],'targets':targets,'ambiguous':len(targets)>1,'document_revision':doc['etag'],'path':path,'status':'SUGGESTED'})
                if len(rows)>=300:break
            if len(rows)>=300:break
        return {'suggestions':rows,'writer_context':False,'automatically_confirmed':False}
    def health(self,p):
        ws=self.ws(p);view=self.knowledge.view(p);entities=view['entities'];ids={(n['type'],n['id']) for n in entities};issues=[];names={};actions=read(self.tools.local(p,'repair-actions.json'),{})
        def issue(id,kind,text,**extra):issues.append({'id':id,'kind':kind,'text':text,'status':actions.get(id,{}).get('action','open'),**extra})
        for n in entities:
            names.setdefault((n['type'],n['name']),[]).append(n)
            if not n.get('path'):issue('source:'+n['type']+':'+n['id'],'缺少来源',n['name'],entity=n)
            if n['type']=='event' and not n.get('story_time'):issue('date:'+n['id'],'时间来源缺失',n['name'],entity=n)
            if n['type']=='chapter' and not n.get('path'):issue('chapter:'+n['id'],'章节定位失败',n['name']+' · 尚未写正文',entity=n,severity='INFO')
        for key,group in names.items():
            if len(group)>1:issue('duplicate:'+key[0]+':'+digest(key[1].encode())[:16],'同名歧义',key[1],candidates=group)
        for a in self.knowledge.anchors(p):
            missing=(a['target_type'],a['target_id']) not in ids
            if not a['located'] or missing:
                candidates=[]
                try:
                    doc=self.tools.doc(p,a['path']);text=normalized(doc)
                    for m in list(re.finditer(re.escape(a['anchor']['exact']),text))[:20]:candidates.append({'start':utf16_index(text,m.start()),'end':utf16_index(text,m.end()),'excerpt':text[max(0,m.start()-32):m.end()+32],'document_revision':doc['etag']})
                except ConsoleError:pass
                issue(a['id'],'已删除目标' if missing else '失效正文锚点',a['anchor']['exact'],anchor=a,candidates=candidates)
        for relation in view['associations']['relations']:
            if (relation['source_type'],relation['source_id']) not in ids or (relation['target_type'],relation['target_id']) not in ids:issue('relation:'+relation['id'],'未解析引用',relation.get('description') or relation.get('relation_type','关联'),relation=relation)
        for clue in self.clues(p):
            if not any(e['source_id']==clue['id'] or e['target_id']==clue['id'] for e in view['relations']):issue('clue:'+clue['id'],'伏笔缺少关联',clue.get('title',clue['id']),source=clue['source'])
        for f in safe(ws.root,'state/proposed').glob('*'):
            if f.is_file() and f.suffix in {'.yaml','.yml','.json'}:issue('proposal:'+f.name,'人物状态更新待确认','有尚未提交的 State 候选',source=f.relative_to(ws.root).as_posix())
        return {'issues':issues,'semantics':'NOT_RUN','note':'确定性记录缺项与 AI 文学建议分开；此处不执行语义审稿。'}
    def repair(self,p,id,b):
        ws=self.tools.writable(p)
        with self.lock,ws._save_lock:
            row=next((x for x in self.health(p)['issues'] if x['id']==id),None)
            if not row:raise ConsoleError('问题已变化，请刷新',409)
            old=row.get('anchor');actions=read(self.tools.local(p,'repair-actions.json'),{})
            if old and old['etag']!=b.etag:raise ConsoleError('锚点已变化，请刷新',409)
            if b.action in {'repair','delete'}:
                if not old:raise ConsoleError('请通过来源页面修正实体或关联',409)
                if not b.confirm:raise ConsoleError('修复/删除需要作者确认',409)
                f=self.tools.local(p,'entity-anchors/'+old['id']+'.json');before=f.read_bytes()
                if b.action=='repair':
                    doc=self.tools.doc(p,old['path']);selected=utf16_slice(normalized(doc),b.start,b.end)
                    request=AnchorRequest(path=old['path'],document_revision=b.document_revision,start=b.start,end=b.end,selected_text=selected,target_type=b.target_type or old['target_type'],target_id=b.target_id or old['target_id'],etag='',confirm=True)
                    checkpoint(ws.root,f.relative_to(ws.root).as_posix(),'PRE_RELOCATE','作者确认重新定位');f.unlink()
                    try:new=self.knowledge.anchor(p,request)
                    except Exception:write_bytes(f,before);raise
                else:
                    checkpoint(ws.root,f.relative_to(ws.root).as_posix(),'PRE_UNLINK','作者删除失效引用');f.unlink();new=None
            else:new=None
            entry={'id':id,'action':b.action,'at':now(),'old':old,'new':new,'author_confirmed':b.confirm};actions[id]=entry
            write(self.tools.local(p,'repair-actions.json'),actions)
            log=read(self.tools.local(p,'repair-history.json'),[]);write(self.tools.local(p,'repair-history.json'),[*log,entry])
            return {'saved':True,'new':new}
    def revision_list(self,p,path=''):
        if path:self.tools.doc(p,path)
        candidates=[read(f) for f in self.tools.local(p,'candidates').glob('*.json')]
        return {'revisions':revisions(self.ws(p).root,path or None)[:200],'candidates':[x for x in candidates if x and x.get('project_id')==p and (not path or x.get('path')==path)],'annotations':self.tools.notes(p,path,True) if path else [],'tasks':self.entries(p).get('revision_tasks',[])}
    def chapter_work(self,p,path):
        doc=self.tools.doc(p,path);cid,number,card=self.tools.chapter(p,path);card=card or {}
        shelf=self.entries(p)
        active=lambda rows:[{k:x.get(k) for k in ['id','text','status','priority','source','severity','annotation_id','exact','start','revision']} for x in rows if x.get('path')==path and not x.get('trashed') and x.get('status') not in {'DONE','IGNORED','ARCHIVED'}]
        candidates=[]
        for file in self.tools.local(p,'candidates').glob('*.json'):
            row=read(file)
            if not row or row.get('project_id')!=p or row.get('path')!=path or row.get('status')!='PROPOSED':continue
            draft=row.get('author_draft') or {}
            candidates.append({'id':row['id'],'status':row['status'],'instruction':row.get('instruction') or row.get('advice',''),'created_at':row.get('created_at',''),'source_current':row.get('document_revision')==doc['etag'],'draft_saved_at':max((v.get('updated_at','') for v in draft.get('variants',{}).values()),default='')})
        candidates.sort(key=lambda x:x['draft_saved_at'] or x['created_at'],reverse=True)
        # Existing explicit anchors are evidence; mentions and plans are not committed facts.
        anchors=self.knowledge.anchors(p,path)
        return {'project_id':p,'path':path,'revision':doc['etag'],'chapter_id':cid,'number':number,'plan':{'goal':card.get('purpose') or card.get('goal') or card.get('summary') or '', 'pov':card.get('pov',{}),'location':card.get('location'),'characters':card.get('characters',[]),'planning_only':True},'todos':active(shelf.get('todos',[]))[:60],'revisions':active(shelf.get('revision_tasks',[]))[:60],'candidates':candidates[:30],'candidate_total':len(candidates),'anchors':anchors[:30],'anchor_total':len(anchors),'counts':{'todos':len(active(shelf.get('todos',[]))),'revisions':len(active(shelf.get('revision_tasks',[])))} }
    def import_preview(self,p,blob,name):
        ws=self.tools.writable(p)
        if len(blob)>8*1024*1024:raise ConsoleError('旧稿单次最多 8 MiB',413)
        try:kind=file_type(blob,name)
        except ValueError as e:raise ConsoleError(str(e),422)
        if kind=='pdf':raise ConsoleError('旧稿仅支持 TXT、Markdown、DOCX',422)
        if kind=='docx':
            # Reuse the existing bounded parser process; no new parser engine.
            from app.library.document_parse import extract_worker
            import multiprocessing
            folder=self.tools.local(p,'imports/'+uuid.uuid4().hex);folder.mkdir(parents=True,exist_ok=True)
            original=folder/('original'+'.docx');write_bytes(original,blob);output=folder/'extracted.json'
            process=multiprocessing.get_context('spawn').Process(target=extract_worker,args=(str(original),kind,str(output)));process.start();process.join(40)
            if process.is_alive():process.terminate();process.join();raise ConsoleError('DOCX 解析超时，原始上传已保留',422)
            extracted=read(output,{})
            if extracted.get('status')!='READY':raise ConsoleError('解析未完整完成，原始上传保留；请改用 TXT 或 Markdown',422)
            text='\n'.join(u['text'] for u in extracted['units'])
        else:
            text,_=decode(blob);folder=self.tools.local(p,'imports/'+uuid.uuid4().hex);folder.mkdir(parents=True,exist_ok=True);original=folder/('original'+('.md' if kind=='md' else '.txt'));write_bytes(original,blob)
        if len(text.encode('utf8'))>2*1024*1024:raise ConsoleError('提取正文超过 2 MiB，请拆分后导入',413)
        text=text.replace('\r\n','\n');matches=list(re.finditer(r'(?im)^[ \t]*(?:#{1,6}\s+)?(?:第[零〇一二三四五六七八九十百千两0-9]+[章节回]|chapter\s+\d+)\s*[^\n]*$',text))
        parts=[]
        if matches:
            if text[:matches[0].start()].strip():parts.append({'title':'前言','content':text[:matches[0].start()]})
            for i,m in enumerate(matches):parts.append({'title':m.group().strip().lstrip('#').strip(),'content':text[m.start():matches[i+1].start() if i+1<len(matches) else len(text)]})
        else:parts=[{'title':name.rsplit('.',1)[0],'content':text}]
        if len(parts)>200:raise ConsoleError('单次最多 200 个候选篇章',422)
        stage={'id':folder.name,'name':name[:200],'format':kind,'text':text,'chapters':parts,'original':original.relative_to(ws.root).as_posix(),'status':'PREVIEW','created_at':now()};write(folder/'stage.json',stage)
        return {**stage,'etag':digest((folder/'stage.json').read_bytes()),'note':'请修正拆章后确认；导入仅添加草稿，不覆盖已有 Final。'}
    def import_commit(self,p,id,b):
        ws=self.tools.writable(p)
        if not re.fullmatch(r'[a-f0-9]{32}',id):raise ConsoleError('无效导入 ID',403)
        with self.lock,ws._save_lock:
            folder=self.tools.local(p,'imports/'+id);stage=read(folder/'stage.json',{})
            if not stage or stage.get('status')!='PREVIEW' or digest((folder/'stage.json').read_bytes())!=b.etag:raise ConsoleError('导入预览已变化或已导入',409)
            if not b.confirm:raise ConsoleError('请确认拆章与目标；已有正文不会覆盖',409)
            for part in b.chapters:
                if set(part)-{'title','content'} or not isinstance(part.get('content'),str) or not isinstance(part.get('title'),str) or not part['content'].strip() or len(part['title'])>200:raise ConsoleError('请检查章节标题和正文',422)
            if sum(len(x['content'].encode('utf8')) for x in b.chapters)>2*1024*1024:raise ConsoleError('导入内容过大',413)
            self.data.backup(p,True,'导入旧稿前')
            from app.projects.writing_config import writing,story_row
            form=writing(self.registry.get(p))['form'];created=[];catalog=safe(ws.root,'metadata/manual-chapters.json');before=catalog.read_bytes() if catalog.exists() else None;manual=read(catalog,{})
            volumes=self.tools.planning.rows(p,'volume')
            if not b.single and form=='novel' and b.volume_id not in {v['id'] for v in volumes}:raise ConsoleError('长篇导入请选择已有卷；不会自动创建空卷',422)
            try:
                if b.single:
                    story=story_row(ws,self.registry.get(p))
                    if not story:raise ConsoleError('只有短篇/自由正文支持不拆章导入',422)
                    path='chapters/story/manual-'+uuid.uuid4().hex+'.txt';write_bytes(ws.resolve(path),'\n\n'.join(x['content'] for x in b.chapters).encode('utf8'));created.append(path)
                else:
                    if form in {'short','undecided','anthology'}:raise ConsoleError('请先使用现有模式转换为中篇，或选择短篇不拆章导入',422)
                    existing=self.registry.book_center.catalog(p)['chapters'];last=max([c['number'] for c in existing]+[0])
                    for i,part in enumerate(b.chapters):
                        n=last+i+1;cid='manual_'+digest(('chapter-'+str(n)).encode())[:24];path=f'chapters/chapter-{n}/draft.txt'
                        if ws.resolve(path).exists():raise ConsoleError('目标章节已存在，导入已停止',409)
                        write_bytes(ws.resolve(path),part['content'].encode('utf8'));created.append(path);manual[str(n)]={'id':cid,'title':part['title'],'volume_id':b.volume_id or None,'order':n,'import_id':id}
                    write(catalog,manual)
                stage.update(status='IMPORTED',saved_paths=created,confirmed_at=now());write(folder/'stage.json',stage)
            except Exception:
                for path in created:ws.resolve(path).unlink(missing_ok=True)
                if before is None:catalog.unlink(missing_ok=True)
                else:write_bytes(catalog,before)
                raise
            return {'paths':created,'original':stage['original'],'stable_ids_preserved':True,'canon_changed':False}
    def replacements(self,p,b,apply=False):
        # Existing clients retain their request shape while using the same
        # validated preview, save protection and undo implementation.
        return self.global_replace.legacy_replacements(p,b,apply)
    def compare_snapshot(self,p,id):
        row=next((x for x in self.data.catalog() if x.get('id')==id and x.get('project_id')==p),None)
        if not row:raise ConsoleError('快照不属于当前作品',404)
        from pathlib import Path
        import zipfile
        path=Path(row['path'])
        if not path.is_file() or digest(path.read_bytes())!=row['sha256']:raise ConsoleError('快照校验失败',409)
        manifest=self.data.inspect(path);root=self.ws(p).root;changes=[]
        from app.library.storage import files
        from app.library.data import backup_member
        old={x['path'][8:]:x for x in manifest['files'] if x['path'].startswith('project/')}
        current={rel:f for rel,f in files(root) if backup_member(rel)}
        for rel in sorted(set(old)|set(current)):
            if rel.startswith('storage/'):continue
            state='新增' if rel not in old else '缺失' if rel not in current else '变化' if digest(current[rel].read_bytes())!=old[rel]['sha256'] else '相同'
            if state!='相同':changes.append({'path':rel,'status':state})
        return {'snapshot':id,'name':row.get('note'),'verified':True,'changes':changes,'note':'只比较文件校验；恢复使用原数据中心并保留恢复前版本。'}
    def overview(self,p):
        catalog=self.registry.book_center.catalog(p);entries=self.entries(p);cards={c['id']:c for c in self.tools.planning.rows(p,'chapter')};view=self.knowledge.view(p)
        rows=[]
        for c in catalog['chapters']:
            path=c.get('final') or c.get('draft') or '';card=cards.get(c['id'],{});edges=[x for x in view['relations'] if x['source_id']==c['id'] or x['target_id']==c['id']]
            notes=self.tools.notes(p,path,True) if path else [];todos=[v for v in entries.get('todos',[]) if v.get('path')==path and not v.get('trashed') and v.get('status') not in {'DONE','IGNORED','ARCHIVED'}]
            rows.append({**c,'path':path,'pov':card.get('pov',{}).get('character'),'location':card.get('location'),'characters':card.get('characters',[]),'relations':edges,'todos':len(todos),'annotations':len(notes),'revised_at':max((v['created_at'] for v in revisions(self.ws(p).root,path)),default=None) if path else None,'planning':True})
        return {'chapters':rows,'volumes':catalog['volumes'],'entities':view['entities'],'form':catalog.get('writing',{}).get('form','novel')}

def workbench_routes(s):
    router=APIRouter(prefix='/api/projects/{p}/workbench')
    from fastapi import Query
    from app.global_replace import ReplaceQuery,ReplaceApply,ReplaceUndo
    from app.clue_board import ClueBoardService,ClueBoardUpdate,ClueBoardBatchUpdate
    clue_board=ClueBoardService(s)
    @router.get('/clue-board')
    def clue_board_get(p:str):return clue_board.get(p)
    @router.put('/clue-board')
    def clue_board_update(p:str,b:ClueBoardUpdate):return clue_board.update(p,b)
    @router.post('/clue-board/batch')
    def clue_board_batch(p:str,b:ClueBoardBatchUpdate):return clue_board.batch(p,b)
    @router.get('/replace/catalog')
    def replace_catalog(p:str):return s.global_replace.catalog(p)
    @router.post('/replace/search')
    def replace_search(p:str,b:ReplaceQuery):return s.global_replace.search(p,b)
    @router.get('/replace/previews/{id}')
    def replace_page(p:str,id:str,offset:int=Query(0,ge=0),limit:int=Query(100,ge=1,le=200),revalidate:bool=False):
        return s.global_replace.page(p,id,offset,limit,revalidate=revalidate)
    @router.post('/replace/apply-selection')
    def replace_selection(p:str,b:ReplaceApply):return s.global_replace.apply(p,b)
    @router.get('/replace/batches')
    def replace_batches(p:str):return s.global_replace.batches(p)
    @router.post('/replace/batches/{id}/undo')
    def replace_undo(p:str,id:str,b:ReplaceUndo):return s.global_replace.undo(p,id,b)

    @router.get('/plans')
    def plans(p:str):return plan_overview(s,p)
    @router.get('/impact')
    def impact(p:str,type:str='',id:str='',q:str=''):return impact_preview(s,p,type,id,q)

    @router.get('/entries')
    def entries(p:str):return s.entries(p)
    @router.post('/entries')
    def entry(p:str,b:Entry):return s.save_entry(p,b)
    @router.post('/entries/states')
    def states(p:str,b:EntryStates):return s.update_entry_states(p,b)
    @router.delete('/entries/{kind}/{id}')
    def remove(p:str,kind:str,id:str,etag:str):return s.remove_entry(p,kind,id,etag)
    @router.get('/knowledge')
    def knowledge(p:str,character:str,chapter:int|None=None):return s.knowledge_at(p,character,chapter)
    @router.get('/relationships')
    def history(p:str):return s.relationship_history(p)
    @router.get('/clues')
    def clues(p:str):return s.clues(p)
    @router.get('/suggestions')
    def suggest(p:str,path:str):return s.suggestions(p,path)
    @router.get('/health')
    def health(p:str):return s.health(p)
    @router.post('/repairs/{id}')
    def repair(p:str,id:str,b:Repair):return s.repair(p,id,b)
    @router.get('/chapter-work')
    def chapter_work(p:str,path:str):return s.chapter_work(p,path)
    @router.get('/revisions')
    def revision(p:str,path:str=''):return s.revision_list(p,path)
    @router.post('/imports/preview')
    async def preview(p:str,file:UploadFile=File(...)):
        try:
            blob=await file.read(8*1024*1024+1)
            import asyncio
            return await asyncio.to_thread(s.import_preview,p,blob,file.filename or '旧稿.txt')
        finally:await file.close()
    @router.post('/imports/{id}/commit')
    def commit(p:str,id:str,b:ImportCommit):return s.import_commit(p,id,b)
    @router.post('/replace/preview')
    def replacements(p:str,b:ReplaceRequest):return s.replacements(p,b)
    @router.post('/replace/apply')
    def replace(p:str,b:ReplaceRequest):return s.replacements(p,b,True)
    @router.get('/snapshots/{id}/compare')
    def compare(p:str,id:str):return s.compare_snapshot(p,id)
    @router.get('/overview')
    def overview(p:str):return s.overview(p)
    return router
