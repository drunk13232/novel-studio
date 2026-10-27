"""Bounded author-confirmed replacement, extending the existing workbench services.

Only manuscript paths are eligible. A server-frozen preview is the authority for
each application; client offsets, replacement text and filesystem paths are not.
"""
import bisect
import json
import re
import threading
import time
import uuid
from datetime import datetime,timedelta,timezone
from typing import Literal

from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.library.storage import checkpoint,digest,now,read,revision_content,safe,write,write_bytes
from app.studio_tools import normalized
from app.writing_metrics import writing_origin
from app.projects.writing_config import writing

BODY=re.compile(r'^chapters/(?:chapter-\d+|story)/(?:draft|final|manual-[a-z0-9-]+)\.(?:txt|md)$')
MAX_HITS=2000
MAX_FILES=1000
MAX_BYTES=64*1024*1024
REGEX_TIMEOUT=.15
SEARCH_SECONDS=8

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class ReplaceQuery(Strict):
    query:str=Field(min_length=1,max_length=300)
    replacement:str=Field(default='',max_length=2000)
    mode:Literal['literal','regex']='literal'
    case_sensitive:bool=True
    whole_word:bool=False
    scope:Literal['book','volume','chapters','paths']='book'
    volume:str=Field(default='',max_length=100)
    chapter_ids:list[str]=Field(default_factory=list,max_length=2000)
    paths:list[str]=Field(default_factory=list,max_length=2000)
    names_mode:Literal['protect','only','all']='protect'
class ReplaceApply(Strict):
    preview_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    hit_ids:list[str]=Field(default_factory=list,max_length=MAX_HITS)
    skip_ids:list[str]=Field(default_factory=list,max_length=MAX_HITS)
    restore_skip_ids:list[str]=Field(default_factory=list,max_length=MAX_HITS)
    all_remaining:bool=False
    include_protected_names:bool=False
    expected_count:int=Field(ge=0,le=MAX_HITS)
    confirm:bool=False
class ReplaceUndo(Strict):confirm:bool=False

def _engine():
    try:import regex;return regex
    except ImportError:raise ConsoleError('正则搜索组件未安装；请使用完整发行版或安装项目依赖',503,code='REPLACE_ENGINE_UNAVAILABLE') from None

def _compile(b):
    engine=_engine();pattern=engine.escape(b.query) if b.mode=='literal' else b.query
    if b.whole_word:pattern=r'(?<!\w)(?:'+pattern+r')(?!\w)'
    try:
        compiled=engine.compile(pattern,engine.VERSION1|(0 if b.case_sensitive else engine.IGNORECASE))
        if compiled.search('',timeout=REGEX_TIMEOUT):raise ConsoleError('不支持空文本或零宽匹配，请填写实际要替换的文字',422,code='REPLACE_ZERO_WIDTH')
        return compiled
    except (engine.error,OverflowError) as error:raise ConsoleError('正则表达式无效：'+str(error)[:200],422,code='REPLACE_REGEX_INVALID') from None
    except TimeoutError:raise ConsoleError('正则表达式运行超时，请简化表达式',422,code='REPLACE_REGEX_TIMEOUT') from None

def _replacement(match,text,regex_mode):
    if not regex_mode:return text
    # A deliberately small replacement grammar, not executable expressions.
    # Validate expansion size before joining possibly large captured groups.
    parts=[];size=0;i=0
    while i<len(text):
        if text[i]!='\\':part=text[i];i+=1
        else:
            i+=1
            if i>=len(text):raise ConsoleError('替换文本末尾的反斜杠需要写成 \\\\',422,code='REPLACE_REPLACEMENT_INVALID')
            char=text[i]
            if char=='g' and text[i+1:i+2]=='<':
                end=text.find('>',i+2)
                if end<0:raise ConsoleError('分组引用缺少 >',422,code='REPLACE_REPLACEMENT_INVALID')
                group=text[i+2:end];i=end+1
                try:part=match.group(int(group) if group.isdigit() else group) or ''
                except (IndexError,KeyError):raise ConsoleError('替换文本引用了不存在的正则分组',422,code='REPLACE_REPLACEMENT_INVALID') from None
            elif char.isdigit() and char!='0':
                end=i+1
                if text[end:end+1].isdigit():end+=1
                try:part=match.group(int(text[i:end])) or ''
                except IndexError:raise ConsoleError('替换文本引用了不存在的正则分组',422,code='REPLACE_REPLACEMENT_INVALID') from None
                i=end
            elif char in {'n','r','t','\\'}:part={'n':'\n','r':'\r','t':'\t','\\':'\\'}[char];i+=1
            else:raise ConsoleError('不支持的替换转义；仅支持分组、\\n、\\r、\\t 和反斜杠',422,code='REPLACE_REPLACEMENT_INVALID')
        size+=len(part)
        if size>65536:raise ConsoleError('单处替换展开超过 64K 字符，请缩小匹配范围',413)
        parts.append(part)
    return ''.join(parts)

def _check_replacement(compiled,text):
    class Groups:
        def group(self,key):
            if isinstance(key,int) and 0<=key<=compiled.groups or isinstance(key,str) and key in compiled.groupindex:return ''
            raise IndexError
    _replacement(Groups(),text,True)

def _astral_indices(text):return [i for i,char in enumerate(text) if ord(char)>0xffff]
def _position(index,astral):return index+bisect.bisect_left(astral,index)
def _name_pattern(terms):
    engine=_engine()
    return engine.compile('|'.join(engine.escape(row['name']) for row in sorted(terms,key=lambda row:-len(row['name']))),engine.VERSION1|engine.IGNORECASE) if terms else None

def _name_spans(pattern,text):
    spans=[]
    if pattern:
        try:
            for match in pattern.finditer(text,overlapped=True,timeout=REGEX_TIMEOUT):
                if len(spans)>=50000:raise ConsoleError('本章专名匹配过多，无法可靠保护；请缩小范围',422)
                spans.append((match.start(),match.end(),match.group()))
        except TimeoutError:raise ConsoleError('专名保护达到安全超时，请缩小范围',422,code='REPLACE_REGEX_TIMEOUT') from None
    starts=[row[0] for row in spans];max_ends=[];last=0
    for _,end,_ in spans:last=max(last,end);max_ends.append(last)
    return spans,starts,max_ends

def _names_at(spans,start,end):
    rows,starts,max_ends=spans
    right=bisect.bisect_left(starts,end);left=bisect.bisect_right(max_ends,start)
    return list(dict.fromkeys(name for begin,stop,name in rows[left:right] if stop>start))

def _locate(hit,text,revision,astral,newlines):
    start,end=hit['_start'],hit['_end'];line=bisect.bisect_left(newlines,start)
    previous=newlines[line-1]+1 if line else 0
    hit.update(start=_position(start,astral),end=_position(end,astral),revision=revision,
        line=line+1,column=_position(start,astral)-_position(previous,astral)+1,
        before=text[max(0,start-45):start],after=text[end:end+45],
        location_text=text[start:end] if end-start<=2000 else None)
def _public_hit(hit):return {key:value for key,value in hit.items() if not key.startswith('_')}

class GlobalReplace:
    def __init__(self,workbench):
        self.owner=workbench;self.registry=workbench.registry;self.tools=workbench.tools
        self.lock=threading.RLock();self._searches=set()
    def _path(self,p,kind,id):
        if not re.fullmatch(r'[a-f0-9]{32}',id):raise ConsoleError('替换记录不存在',404)
        return self.tools.local(p,'replace-'+kind+'/'+id+'.json')
    def _load(self,p,kind,id):
        value=read(self._path(p,kind,id))
        if not value or value.get('project_id')!=p:raise ConsoleError('替换记录不属于当前小说',404)
        return value
    def catalog(self,p):
        if writing(self.registry.get(p))['form']=='anthology':
            return {'chapters':[],'volumes':[],'default_version':'OPEN_EACH_STORY_SEPARATELY',
                'limits':{'matches':MAX_HITS,'files':MAX_FILES,'bytes':MAX_BYTES,'regex_seconds_per_file':REGEX_TIMEOUT}}
        ws=self.registry.workspace(p);book=self.registry.book_center.catalog(p,include_auxiliary=False,include_text_counts=False);chapters=[]
        for chapter in book['chapters']:
            if chapter.get('kind')=='anthology':continue
            preferred=chapter.get('final') or chapter.get('draft')
            if chapter.get('kind')=='story':preferred=chapter.get('path') or preferred
            folder='chapters/story' if chapter.get('kind')=='story' else 'chapters/chapter-'+str(chapter['number'])
            versions=[]
            for file in safe(ws.root,folder).glob('*'):
                relative=file.relative_to(ws.root).as_posix()
                if file.is_file() and BODY.fullmatch(relative):
                    safe(ws.root,relative);versions.append(relative)
            if not preferred and versions:preferred=max(versions,key=lambda path:safe(ws.root,path).stat().st_mtime_ns)
            chapters.append({'id':chapter['id'],'number':chapter['number'],'title':chapter['title'],
                             'volume':chapter.get('volume') or '', 'path':preferred,'versions':sorted(versions)})
        return {'chapters':chapters,'volumes':book['volumes'],'default_version':'CURRENT_PREFERRED_MANUSCRIPT',
                'limits':{'matches':MAX_HITS,'files':MAX_FILES,'bytes':MAX_BYTES,'regex_seconds_per_file':REGEX_TIMEOUT}}
    def _terms(self,p):
        terms={}
        for row in self.tools.characters.list(p):
            item=row.get('canonical',row)
            for name in [item.get('name'),*item.get('aliases',[])]:
                if isinstance(name,str) and name.strip():terms[name]={'name':name,'kind':'character','id':item.get('id','')}
        for item in self.tools.bible.list(p):
            for name in [item.get('name'),*item.get('aliases',[])]:
                if isinstance(name,str) and name.strip():terms[name]={'name':name,'kind':'entity','id':item.get('id','')}
        if len(terms)>4000 or sum(len(name) for name in terms)>200000:raise ConsoleError('设定专名过多，请先缩小作品或整理别名',422)
        rows=sorted(terms.values(),key=lambda row:row['name'])
        return rows,digest(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode())
    def _selection(self,p,b):
        catalog=self.catalog(p);chapters=catalog['chapters'];paths={path:chapter for chapter in chapters for path in chapter['versions']}
        if b.scope=='volume':
            if not b.volume or b.volume not in {v['id'] for v in catalog['volumes']}:raise ConsoleError('请选择当前小说的卷',422,code='REPLACE_SCOPE_INVALID')
            selected=[c for c in chapters if c['volume']==b.volume]
        elif b.scope=='chapters':
            if not b.chapter_ids or not set(b.chapter_ids)<={c['id'] for c in chapters}:raise ConsoleError('请选择当前小说的有效章节',422,code='REPLACE_SCOPE_INVALID')
            selected=[c for c in chapters if c['id'] in b.chapter_ids]
        elif b.scope=='paths':
            if not b.paths or not set(b.paths)<=set(paths):raise ConsoleError('替换范围只能包含当前小说的正文版本',422,code='REPLACE_SCOPE_INVALID')
            return [(path,paths[path]) for path in dict.fromkeys(b.paths)]
        else:selected=chapters
        return [(c['path'],c) for c in selected if c['path']]
    def search(self,p,b):
        # A cancelled HTTP wait cannot stop a running regex worker. Bound the
        # residual work without holding a lock during scans or blocking saves.
        with self.lock:
            if p in self._searches:raise ConsoleError('本作品上一轮搜索仍在结束中，请稍后手动重试',409,code='REPLACE_SEARCH_BUSY')
            self._searches.add(p)
        try:return self._search(p,b)
        finally:
            with self.lock:self._searches.discard(p)
    def _search(self,p,b):
        compiled=_compile(b)
        if b.mode=='regex':_check_replacement(compiled,b.replacement)
        selection=self._selection(p,b);terms,term_hash=self._terms(p)
        names=_name_pattern(terms)
        id=uuid.uuid4().hex;hits=[];documents={};errors=[];bytes_read=0;started=time.monotonic();has_more=False;scanned=0;expanded=0
        for path,chapter in selection:
            if scanned>=MAX_FILES or time.monotonic()-started>SEARCH_SECONDS:has_more=True;break
            try:doc=self.tools.doc(p,path)
            except ConsoleError as error:errors.append({'path':path,'reason':str(error),'code':error.code,'status':error.status});continue
            if bytes_read+doc['size']>MAX_BYTES:has_more=True;break
            text=normalized(doc);bytes_read+=doc['size'];scanned+=1;astral=_astral_indices(text);newlines=[i for i,c in enumerate(text) if c=='\n']
            try:
                spans=_name_spans(names,text)
                documents[path]={'revision':doc['etag'],'protected':not doc['editable'],'title':chapter['title']}
                for match in compiled.finditer(text,timeout=REGEX_TIMEOUT):
                    if match.start()==match.end():raise ConsoleError('不支持零宽匹配，请填写实际要替换的文字',422,code='REPLACE_ZERO_WIDTH')
                    if len(hits)>=MAX_HITS:has_more=True;break
                    # Names may overlap; include any span intersecting this hit.
                    protected=_names_at(spans,match.start(),match.end())
                    if b.names_mode=='only' and not protected:continue
                    replacement=_replacement(match,b.replacement,b.mode=='regex').replace('\r\n','\n')
                    if '\r' in replacement:raise ConsoleError('替换文本包含单独的回车符，请使用 \\n 或 \\r\\n 表示换行',422,code='REPLACE_REPLACEMENT_INVALID')
                    expanded+=len(replacement)
                    if expanded>8*1024*1024:raise ConsoleError('替换预览展开超过 8 MiB，请缩小范围',413)
                    hits.append({'id':uuid.uuid4().hex,'path':path,'chapter_id':chapter['id'],'title':chapter['title'],
                        'start':_position(match.start(),astral),'end':_position(match.end(),astral),'_start':match.start(),'_end':match.end(),
                        'revision':doc['etag'],'match':match.group()[:500],'match_truncated':len(match.group())>500,
                        '_matched_hash':digest(match.group().encode()),'_replacement':replacement,'replacement':replacement[:1000],
                        'replacement_truncated':len(replacement)>1000,'before':text[max(0,match.start()-45):match.start()],
                        'after':text[match.end():match.end()+45],'protected':not doc['editable'],'protected_names':list(dict.fromkeys(protected)),
                        'default_selected':replacement!=match.group() and (not protected or b.names_mode!='protect'),
                        'status':'PENDING' if replacement!=match.group() else 'UNCHANGED'})
                    _locate(hits[-1],text,doc['etag'],astral,newlines)
                if has_more:break
            except TimeoutError:raise ConsoleError('正则搜索或专名保护超时；未修改任何正文，请简化表达式或缩小范围',422,code='REPLACE_REGEX_TIMEOUT') from None
        value={'id':id,'project_id':p,'query':b.model_dump(),'created_at':now(),'expires_at':(datetime.now(timezone.utc)+timedelta(hours=2)).isoformat(),
            'term_hash':term_hash,'documents':documents,'hits':hits,'has_more':has_more,'errors':errors,
            '_scope_paths':[path for path,_ in selection],
            'coverage':{'requested_files':len(selection),'scanned_files':scanned,'bytes_read':bytes_read,'complete':not has_more and not errors},
            'status':'PREVIEW','preview_hash':digest(json.dumps(b.model_dump(),sort_keys=True).encode())}
        write(self._path(p,'previews',id),value)
        return self._page(value,0,100)
    def _page(self,value,offset,limit):
        limit=min(200,max(1,limit));offset=max(0,offset)
        return {key:value[key] for key in ['id','project_id','query','created_at','expires_at','has_more','errors','coverage','status','preview_hash']}|{
            'hits':[_public_hit(h) for h in value['hits'][offset:offset+limit]],'total_hits':len(value['hits']),
            'remaining':sum(h['status']=='PENDING' for h in value['hits']),'offset':offset,'limit':limit,
            'more_pages':offset+limit<len(value['hits']),'protected_name_hits':sum(bool(h['protected_names']) for h in value['hits']),
            'pending_name_hits':sum(h['status']=='PENDING' and bool(h['protected_names']) for h in value['hits']),
            'pending_regular_hits':sum(h['status']=='PENDING' and not h['protected_names'] for h in value['hits']),
            'applied_hits':sum(h['status']=='APPLIED' for h in value['hits']),
            'skipped_hits':sum(h['status']=='SKIPPED' for h in value['hits']),
            'unchanged_hits':sum(h['status']=='UNCHANGED' for h in value['hits']),
            'can_apply':value['status']=='PREVIEW' and datetime.now(timezone.utc)<datetime.fromisoformat(value['expires_at'])}
    def page(self,p,id,offset=0,limit=100,revalidate=False):
        value=self._load(p,'previews',id);result=self._page(value,offset,limit)
        if not revalidate:return result
        validation={'status':'VALID','reason':'MATCHED_SAVED_VERSIONS','checked_files':0};started=time.monotonic();bytes_read=0
        if not result['can_apply']:validation.update(status='EXPIRED',reason='PREVIEW_NO_LONGER_ACTIVE')
        else:
            try:
                if self._terms(p)[1]!=value['term_hash']:validation.update(status='STALE',reason='NAMES_CHANGED')
                elif '_scope_paths' in value and sorted(path for path,_ in self._selection(p,ReplaceQuery.model_validate(value['query'])))!=sorted(value['_scope_paths']):validation.update(status='STALE',reason='SCOPE_CHANGED')
                else:
                    for path,document in value['documents'].items():
                        if validation['checked_files']>=MAX_FILES or time.monotonic()-started>SEARCH_SECONDS:
                            validation.update(status='UNVERIFIED',reason='REVALIDATION_LIMIT');break
                        doc=self.tools.doc(p,path);bytes_read+=doc['size']
                        if bytes_read>MAX_BYTES:validation.update(status='UNVERIFIED',reason='REVALIDATION_LIMIT');break
                        validation['checked_files']+=1
                        if doc['etag']!=document['revision']:validation.update(status='STALE',reason='DOCUMENT_CHANGED');break
            except ConsoleError:validation.update(status='STALE',reason='SOURCE_UNAVAILABLE')
        return {**result,'can_apply':validation['status']=='VALID','validation':validation}
    def apply(self,p,b):
        ws=self.tools.writable(p)
        with self.lock,self.owner.lock,ws._save_lock:
            preview=self._load(p,'previews',b.preview_id)
            if preview['status']!='PREVIEW':raise ConsoleError('此预览已撤销或需要恢复，请重新搜索',409,code='REPLACE_PREVIEW_EXPIRED')
            if datetime.now(timezone.utc)>=datetime.fromisoformat(preview['expires_at']):raise ConsoleError('替换预览已过期，请重新搜索',409,code='REPLACE_PREVIEW_EXPIRED')
            if not b.confirm:raise ConsoleError('请确认替换位置、数量与修订方式',409)
            known={hit['id']:hit for hit in preview['hits']}
            if any(len(ids)!=len(set(ids)) for ids in [b.hit_ids,b.skip_ids,b.restore_skip_ids]) or not (set(b.hit_ids)|set(b.skip_ids)|set(b.restore_skip_ids))<=set(known):raise ConsoleError('替换位置不属于此预览',422)
            if set(b.hit_ids)&set(b.skip_ids):raise ConsoleError('同一位置不能同时替换与跳过',422)
            if b.restore_skip_ids and (b.hit_ids or b.skip_ids or b.all_remaining):raise ConsoleError('重新加入的候选需要独立核对，不能同时执行正文替换',422)
            if any(known[id]['status']!='SKIPPED' for id in b.restore_skip_ids):raise ConsoleError('只有已跳过的位置可以重新加入',409)
            if any(known[id]['status']!='PENDING' for id in [*b.hit_ids,*b.skip_ids]):raise ConsoleError('此位置已处理，请刷新预览；没有重复执行',409)
            rows=[h for h in preview['hits'] if h['status']=='PENDING' and h['id'] not in b.skip_ids and
                  (b.all_remaining or h['id'] in b.hit_ids) and (b.include_protected_names or not h['protected_names'])]
            if len(rows)!=b.expected_count:raise ConsoleError('待替换数量或专名权限已变化，请重新核对预览',409)
            if not rows and not b.skip_ids and not b.restore_skip_ids:raise ConsoleError('请选择要替换或跳过的位置',422)
            terms,term_hash=self._terms(p)
            if term_hash!=preview['term_hash']:raise ConsoleError('人物或世界观专名已变化，请重新搜索',409)
            if not rows:
                for id in b.skip_ids:known[id]['status']='SKIPPED'
                pattern=_name_pattern(terms)
                for id in b.restore_skip_ids:
                    hit=known[id];doc=self.tools.doc(p,hit['path'])
                    if doc['etag']!=preview['documents'][hit['path']]['revision']:raise ConsoleError('正文版本已变化，请重新搜索',409,code='REPLACE_REVISION_CHANGED')
                    hit['protected_names']=list(dict.fromkeys([*hit['protected_names'],*_names_at(_name_spans(pattern,normalized(doc)),hit['_start'],hit['_end'])]))
                    hit['default_selected']=not hit['protected_names'];hit['status']='PENDING'
                write(self._path(p,'previews',preview['id']),preview)
                return {'batch':{'id':'','count':0,'files':[],'status':'SKIPPED' if b.skip_ids else 'RESTORED'},
                    'preview':self._page(preview,0,100),'paths':[],'status':'SKIPPED' if b.skip_ids else 'RESTORED',
                    'replaced':0,'skipped':len(b.skip_ids),'restored':len(b.restore_skip_ids),'canon_changed':False}
            name_pattern=_name_pattern(terms)
            groups={}
            for hit in rows:groups.setdefault(hit['path'],[]).append(hit)
            changes=[]
            for path,items in groups.items():
                doc=self.tools.doc(p,path)
                if doc['etag']!=preview['documents'][path]['revision']:raise ConsoleError('正文已被修改，没有应用本次替换；请重新搜索',409,code='REPLACE_REVISION_CHANGED')
                if doc['line_ending']=='MIXED':raise ConsoleError('混合换行正文需先手动处理',409)
                before=normalized(doc);parts=[];cursor=0
                if sum(len(hit['_replacement']) for hit in items)>8*1024*1024:raise ConsoleError('替换展开过大，请缩小范围',413)
                for hit in sorted(items,key=lambda h:h['_start']):
                    if digest(before[hit['_start']:hit['_end']].encode())!=hit['_matched_hash'] or hit['_start']<cursor:raise ConsoleError('替换定位已变化',409)
                    parts.extend([before[cursor:hit['_start']],hit['_replacement']]);cursor=hit['_end']
                parts.append(before[cursor:]);text=''.join(parts)
                output=text.replace('\n','\r\n') if doc['line_ending']=='CRLF' else text
                if len(output.encode('utf-8-sig' if doc['bom'] else 'utf8'))>ws.max_bytes:raise ConsoleError('替换结果超过正文大小限制',413)
                # Recompute protection before writing: adjacent replacements can
                # create a canonical name around a still-pending match.
                changes.append((path,doc,output,text,items,_name_spans(name_pattern,text)))
            skipped=len(b.skip_ids)
            batch={'id':uuid.uuid4().hex,'project_id':p,'preview_id':preview['id'],'created_at':now(),'status':'APPLYING',
                'count':len(rows),'skipped':skipped,'query':preview['query'],'files':[]}
            write(self._path(p,'batches',batch['id']),batch)
            try:
                for path,doc,output,text,items,new_name_spans in changes:
                    if self.tools.doc(p,path)['etag']!=doc['etag']:raise ConsoleError('保存前正文已变化，请重新搜索',409,code='REPLACE_REVISION_CHANGED')
                    previous=checkpoint(ws.root,path,'PRE_REPLACE','作者确认全局替换')
                    target=path;created=not doc['editable']
                    if created:
                        _,number,_=self.tools.chapter(p,path);target=('chapters/story' if number==0 else f'chapters/chapter-{number}')+'/manual-'+uuid.uuid4().hex+'.txt'
                    blob=ws.resolve(path).read_bytes()
                    if digest(blob)!=doc['etag']:raise ConsoleError('建立修订稿时原文已变化，请重新搜索',409)
                    item={'source':path,'path':target,'created':created,'before_revision':previous['id'],
                        'count':len(items),'title':items[0]['title'],'chapter_id':items[0]['chapter_id'],
                        'before_etag':doc['etag'],'after_revision':digest(output.encode('utf-8-sig' if doc['bom'] else 'utf8')),'before_bom':doc['bom']}
                    # Record the intended hash BEFORE the first mutation. A failed
                    # save of a newly copied Final is included in compensation.
                    batch['files'].append(item)
                    write(self._path(p,'batches',batch['id']),batch)
                    if created:write_bytes(ws.resolve(target),blob)
                    saved=ws.save(target,output,doc['etag'])
                    if saved['etag']!=item['after_revision']:raise ConsoleError('保存回执与替换内容不一致',409)
                    astral=_astral_indices(text);newlines=[i for i,c in enumerate(text) if c=='\n']
                    edits=[(item['_start'],item['_end'],item['_replacement'],item['id']) for item in items]
                    applied={item[3]:item for item in edits}
                    for hit in preview['hits']:
                        if hit['path']!=path:continue
                        shift=sum(len(replacement)-(end-start) for start,end,replacement,_ in edits if end<=hit['_start'])
                        hit['_start']+=shift;hit['_end']+=shift;hit['path']=target
                        if hit['id'] in applied:
                            hit['status']='APPLIED';hit['_end']=hit['_start']+len(applied[hit['id']][2])
                        _locate(hit,text,saved['etag'],astral,newlines)
                        if hit['status']=='PENDING':
                            # Protection is monotonic within a frozen preview.
                            # A partial rename must not silently free the rest of
                            # the same original canonical name for later writes.
                            hit['protected_names']=list(dict.fromkeys([*hit['protected_names'],*_names_at(new_name_spans,hit['_start'],hit['_end'])]))
                            hit['default_selected']=not hit['protected_names']
                        hit['protected']=False if created else hit['protected']
                    preview['documents'][target]={'revision':saved['etag'],'protected':False,'title':doc.get('title','')}
                for id in b.skip_ids:
                    if known[id]['status']=='PENDING':known[id]['status']='SKIPPED'
                batch['status']='APPLIED';write(self._path(p,'batches',batch['id']),batch);write(self._path(p,'previews',preview['id']),preview)
            except Exception:
                self._recover(ws,p,batch)
                if batch['status']=='RECOVERY_REQUIRED':
                    frozen=self._load(p,'previews',preview['id']);frozen['status']='RECOVERY_REQUIRED';write(self._path(p,'previews',preview['id']),frozen)
                    raise ConsoleError('部分保存失败，且出现后续文件变化；未覆盖外部修改。请检查替换历史与 PRE_REPLACE 版本',409,code='REPLACE_RECOVERY_REQUIRED') from None
                raise
            return {'batch':self._batch_public(batch),'preview':self._page(preview,0,100),'paths':[row['path'] for row in batch['files']],
                    'status':'APPLIED','replaced':len(rows),'skipped':skipped,
                    'protected_remaining':sum(h['status']=='PENDING' and bool(h['protected_names']) for h in preview['hits']),
                    'canon_changed':False,'requires_state_revalidation':True}
    def _recover(self,ws,p,batch):
        success=True
        for item in reversed(batch['files']):
            try:
                if item['created'] and not ws.resolve(item['path']).exists():continue
                current=ws.content(item['path'])
                if current['etag']==item['before_etag'] and not item['created']:continue
                if current['etag'] not in ({item['after_revision'],item['before_etag']} if item['created'] else {item['after_revision']}):success=False;continue
                if item['created']:
                    checkpoint(ws.root,item['path'],'REPLACE_FAILED_RECOVERY')
                    if current['etag']!=item['before_etag']:
                        _,blob=revision_content(ws.root,item['before_revision'])
                        with writing_origin('RESTORE'):ws.save(item['path'],blob.decode('utf-8-sig'),current['etag'])
                    ws.resolve(item['path']).unlink()
                else:
                    _,blob=revision_content(ws.root,item['before_revision'])
                    with writing_origin('RESTORE'):ws.save(item['path'],blob.decode('utf-8-sig'),current['etag'])
            except Exception:success=False
        batch['status']='ROLLED_BACK' if success else 'RECOVERY_REQUIRED';write(self._path(p,'batches',batch['id']),batch)
    def _batch_public(self,batch):return {key:batch.get(key) for key in ['id','preview_id','created_at','undone_at','status','count','skipped','query','files']}
    def batches(self,p):
        self.registry.get(p);folder=self.tools.local(p,'replace-batches');rows=[]
        for path in folder.glob('*.json'):
            value=read(path,{})
            if value.get('project_id')==p:rows.append(self._batch_public(value))
        return {'batches':sorted(rows,key=lambda row:row['created_at'],reverse=True)[:100]}
    def undo(self,p,id,b):
        if not b.confirm:raise ConsoleError('请确认撤销整个替换批次',409)
        ws=self.tools.writable(p)
        with self.lock,self.owner.lock,ws._save_lock:
            batch=self._load(p,'batches',id)
            if batch['status']!='APPLIED':raise ConsoleError('此批次已撤销或未成功应用，不能重复撤销',409)
            checked=[]
            for item in batch['files']:
                doc=self.tools.doc(p,item['path'])
                if doc['etag']!=item['after_revision'] or not doc['editable']:raise ConsoleError('批次后正文已有修改，未撤销任何文件；请使用修订历史比较',409,code='REPLACE_REVISION_CHANGED')
                _,blob=revision_content(ws.root,item['before_revision']);checked.append((item,doc,blob))
            # All files are validated before the first mutation. Current contents
            # are checkpointed so even deleting a newly created revision is recoverable.
            undo_blobs={}
            for item,doc,blob in checked:
                receipt=checkpoint(ws.root,item['path'],'PRE_REPLACE_UNDO','撤销全局替换前')
                undo_blobs[item['path']]=revision_content(ws.root,receipt['id'])[1]
            restored=[]
            try:
                for item,doc,blob in checked:
                    if item['created']:
                        if ws.content(item['path'])['etag']!=doc['etag']:raise ConsoleError('撤销期间正文已变化',409)
                        # Reverse only the actual replacement delta. Deleting an
                        # entire revision copy is not a manuscript deletion event.
                        with writing_origin('RESTORE'):ws.save(item['path'],blob.decode('utf-8-sig'),doc['etag'])
                        ws.resolve(item['path']).unlink();restored.append(item['source'])
                    else:
                        with writing_origin('RESTORE'):ws.save(item['path'],blob.decode('utf-8-sig'),doc['etag'])
                        restored.append(item['path'])
            except Exception:
                recovered=True
                # Compensate every file, including a save that wrote successfully
                # before reporting an error. Never overwrite an unrelated edit.
                for item,doc,blob in reversed(checked):
                    try:
                        path=ws.resolve(item['path'])
                        if item['created']:
                            if not path.exists():
                                write_bytes(path,undo_blobs[item['path']])
                                from app.writing_metrics import notify_saved
                                notify_saved(ws.root,item['path'],blob.decode('utf-8-sig'),undo_blobs[item['path']].decode('utf-8-sig'),source='RESTORE')
                            else:
                                current=ws.content(item['path'])
                                if current['etag']==item['after_revision']:continue
                                if current['etag']!=digest(blob):recovered=False;continue
                                with writing_origin('RESTORE'):ws.save(item['path'],undo_blobs[item['path']].decode('utf-8-sig'),current['etag'])
                        else:
                            current=ws.content(item['path'])
                            if current['etag']==item['after_revision']:continue
                            if current['etag']!=digest(blob):recovered=False;continue
                            with writing_origin('RESTORE'):ws.save(item['path'],undo_blobs[item['path']].decode('utf-8-sig'),current['etag'])
                    except Exception:recovered=False
                batch['status']='APPLIED' if recovered else 'UNDO_RECOVERY_REQUIRED';write(self._path(p,'batches',id),batch)
                if not recovered:raise ConsoleError('撤销未能完整恢复，未覆盖外部修改；请检查撤销前历史版本',409,code='REPLACE_RECOVERY_REQUIRED') from None
                raise
            batch['status']='UNDONE';batch['undone_at']=now();write(self._path(p,'batches',id),batch)
            preview=self._load(p,'previews',batch['preview_id']);preview['status']='STALE_AFTER_UNDO';write(self._path(p,'previews',preview['id']),preview)
            return {'batch':self._batch_public(batch),'paths':restored,'status':'UNDONE','canon_changed':False}

    def legacy_replacements(self,p,b,apply=False):
        """Keep old preview/apply endpoints on the same frozen-preview engine.

        Legacy clients receive opaque IDs in their hits. Raw paths/offsets alone
        never authorize a mutation and stale pre-upgrade previews must refresh.
        """
        if not apply:
            scope='paths' if b.paths else 'chapters' if b.chapter else 'volume' if b.volume else 'book'
            result=self.search(p,ReplaceQuery(query=b.query,replacement=b.replacement,scope=scope,
                paths=b.paths,chapter_ids=[b.chapter] if b.chapter else [],volume=b.volume))
            return {'hits':[dict(hit,preview_id=result['id'],excerpt=hit['before']+hit['match']+hit['after'],
                permission='独立修订稿' if hit['protected'] else '草稿保存') for hit in result['hits']],
                'preview_id':result['id'],'limited':result['has_more'] or result['more_pages'],
                'note':'Final 仅产生独立修订稿；专名默认跳过。完整范围与撤销请使用新版全局替换。'}
        ids={hit.get('preview_id') for hit in b.hits}
        if len(ids)!=1 or not b.hits or None in ids:raise ConsoleError('请使用新版预览重新选择位置；未修改任何正文',409)
        id=next(iter(ids));preview=self._load(p,'previews',id)
        if preview['query']['query']!=b.query or preview['query']['replacement']!=b.replacement:raise ConsoleError('查找或替换内容已变化，请重新预览',409)
        known={hit['id']:hit for hit in preview['hits']}
        for hit in b.hits:
            frozen=known.get(hit.get('id'))
            if not frozen or any(hit.get(key)!=frozen[key] for key in ['path','start','end','revision']):raise ConsoleError('替换预览定位不匹配',409)
        return self.apply(p,ReplaceApply(preview_id=id,hit_ids=[hit['id'] for hit in b.hits],
            expected_count=len(b.hits),confirm=b.confirm))
