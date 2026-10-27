"""Chapter-local what-if drafts over existing revisions and guarded manuscript saves.

Only the original canonical manuscript path participates in writing/search/export.
Alternatives are data under history/, never additional chapter files or Canon.
"""
import copy
import json
import re
import threading
from pathlib import PurePosixPath
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from app.errors import ConsoleError
from app.library.storage import checkpoint, digest, now, read, revision_content, safe, write, write_bytes
from app.writing_metrics import writing_origin

MAX_VERSIONS=30
MAX_STATE_BYTES=24*1024*1024
ID=r'version_[a-f0-9]{32}'
HASH=r'^[a-f0-9]{64}$'

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class VersionSave(Strict):
    path:str=Field(max_length=260)
    state_etag:str=Field(pattern=HASH)
    request_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=1500)
    content:str=Field(default='',max_length=2*1024*1024)
    version_etag:str=Field(default='',max_length=64)
class VersionArchive(Strict):
    path:str=Field(max_length=260)
    state_etag:str=Field(pattern=HASH)
    archived:bool=True
    confirm:bool=False
class VersionSwitch(Strict):
    path:str=Field(max_length=260)
    state_etag:str=Field(pattern=HASH)
    version_id:str=Field(pattern='^'+ID+'$')
    version_etag:str=Field(pattern=HASH)
    main_etag:str=Field(pattern=HASH)
    request_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    mode:str=Field(default='switch',pattern=r'^(switch|revision)$')
    confirm:bool=False
class VersionRecovery(Strict):
    path:str=Field(max_length=260)
    state_etag:str=Field(pattern=HASH)
    main_etag:str=Field(pattern=HASH)
    operation_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    recovery_etag:str=Field(pattern=HASH)
    request_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    confirm:bool=False
class VersionUndo(Strict):
    path:str=Field(max_length=260)
    state_etag:str=Field(pattern=HASH)
    request_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    confirm:bool=False

def _error(code,status=409):raise ConsoleError(code,status,code='VERSIONS_'+code)
def _bytes(value):return json.dumps(value,ensure_ascii=False,indent=2).encode('utf8')
def _normalized(text):return text.replace('\r\n','\n')
def _vhash(row):return digest(_bytes({key:row.get(key) for key in ('id','name','description','content','archived')}))

class ChapterVersions:
    def __init__(self,tools):self.tools=tools;self.registry=tools.registry;self.lock=threading.RLock()
    def _binding(self,p,path):
        from app.projects.writing_config import writing
        if writing(self.registry.get(p))['form']=='anthology':_error('SCOPE',403)
        cid,_,_=self.tools.chapter(p,path);ws=self.registry.workspace(p)
        self.tools.doc(p,path)
        key=digest(cid.encode())[:32]
        folder='history/parallel-versions/'+key
        return ws,cid,folder,safe(ws.root,folder+'/versions.json')
    def _preferred(self,p,cid,path):
        # Reuse the same authoritative selection used by book assembly/statistics.
        books=getattr(self.registry,'book_center',None)
        if books:
            rows=books.catalog(p,include_auxiliary=False,include_text_counts=False)['chapters']
            row=next((r for r in rows if r['id']==cid),None)
            if row:
                preferred=(row.get('path') if row.get('kind')=='story' else None) or row.get('final') or row.get('draft')
                if preferred:return preferred
        return path
    def _load(self,p,path):
        ws,cid,folder,file=self._binding(p,path);existed=file.exists()
        if existed:
            if file.stat().st_size>MAX_STATE_BYTES:_error('LIMIT',413)
            blob=file.read_bytes()
            if len(blob)>MAX_STATE_BYTES:_error('LIMIT',413)
            try:state=json.loads(blob)
            except (ValueError,UnicodeError,RecursionError):_error('CORRUPT',422)
            self._validate_state(ws,state,cid)
            main_path=state['main_path']
            if self.tools.chapter(p,main_path)[0]!=cid:_error('CORRUPT',422)
        else:
            main_path=self._preferred(p,cid,path)
            if self.tools.chapter(p,main_path)[0]!=cid:_error('SCOPE',403)
            state={'schema_version':1,'chapter_id':cid,'main_path':main_path,'canonical_id':'version_'+digest(cid.encode())[:32],
                'versions':[{'id':'version_'+digest(cid.encode())[:32],'name':'','description':'','content':'','archived':False,'created_at':'','updated_at':''}],
                'last_switch':None}
            blob=_bytes(state)
        doc=self.tools.doc(p,main_path);doc['_versions_exists']=existed
        return ws,folder,file,state,digest(blob),doc
    def _validate_state(self,ws,state,cid):
        if not isinstance(state,dict) or state.get('schema_version')!=1 or state.get('chapter_id')!=cid:_error('CORRUPT',422)
        rows=state.get('versions')
        if not isinstance(rows,list) or not 1<=len(rows)<=MAX_VERSIONS:_error('CORRUPT',422)
        ids=[]
        for row in rows:
            if not isinstance(row,dict) or not re.fullmatch(ID,str(row.get('id',''))) or not isinstance(row.get('content'),str):_error('CORRUPT',422)
            self._text(ws,row['content']);ids.append(row['id'])
            if not isinstance(row.get('name',''),str) or len(row.get('name',''))>100 or not isinstance(row.get('description',''),str) or len(row.get('description',''))>1500 or not isinstance(row.get('archived'),bool):_error('CORRUPT',422)
        if len(ids)!=len(set(ids)) or state.get('canonical_id') not in ids:_error('CORRUPT',422)
        if not isinstance(state.get('main_path'),str) or next(v for v in rows if v['id']==state['canonical_id']).get('archived'):_error('CORRUPT',422)
    def _snapshot(self,ws,id,path,limit):
        # Validate the actual archived file before the existing revision reader
        # loads it. A damaged/imported journal cannot redirect or inflate reads.
        if not isinstance(id,str) or not re.fullmatch(r'revision_[a-f0-9]{32}',id):_error('CORRUPT',422)
        metadata=safe(ws.root,'history/revisions/'+id+'/revision.json')
        if not metadata.is_file() or metadata.stat().st_size>64*1024:_error('CORRUPT',422)
        try:row=read(metadata,{})
        except (ConsoleError,ValueError,UnicodeError,RecursionError):_error('CORRUPT',422)
        if not isinstance(row,dict) or row.get('path')!=path or not isinstance(row.get('blob'),str) or row['blob']!=id+'/content'+PurePosixPath(path).suffix:_error('CORRUPT',422)
        blob=safe(ws.root,'history/revisions/'+row['blob'])
        if not blob.is_file() or blob.stat().st_size>limit:_error('CORRUPT',422)
        checked,data=revision_content(ws.root,id)
        if checked!=row or len(data)>limit:_error('CORRUPT',422)
        return data
    def _text(self,ws,text):
        value=_normalized(text)
        if '\r' in value or '\x00' in value:_error('TEXT_INVALID',422)
        try:size=len(value.encode('utf8'))
        except UnicodeError:_error('TEXT_INVALID',422)
        if size>ws.max_bytes:_error('TEXT_LIMIT',413)
        return value
    def _blocked(self,ws,folder):
        marker=safe(ws.root,folder+'/pending.json')
        if not marker.exists():return False
        if marker.stat().st_size>1024:return True
        try:
            value=read(marker,{})
            if not isinstance(value,dict) or not re.fullmatch(r'[a-f0-9]{32}',str(value.get('id',''))):return True
            record=self._op_path(ws,folder,value['id'])
            if record.exists() and record.stat().st_size>128*1024:return True
            operation=read(record,{})
            return not isinstance(operation,dict) or operation.get('status') not in {'APPLIED','UNDONE','ROLLED_BACK'}
        except (ConsoleError,OSError,ValueError,RecursionError):return True
    def _ensure_clean(self,ws,folder):
        if self._blocked(ws,folder):_error('RECOVERY_REQUIRED')
    def _mark_pending(self,ws,folder,id):write(safe(ws.root,folder+'/pending.json'),{'id':id})
    def _public(self,p,path,loaded=None):
        ws,folder,file,state,etag,doc=loaded or self._load(p,path)
        rows=[]
        for saved in state['versions']:
            row=copy.deepcopy(saved)
            if row['id']==state['canonical_id']:row['content']=_normalized(doc['content'])
            rows.append({k:v for k,v in row.items() if k!='content' and not k.startswith('_')}|{'etag':_vhash(row),'canonical':row['id']==state['canonical_id'],'characters':len(row['content'])})
        preferred=self._preferred(p,state['chapter_id'],state['main_path'])
        return {'project_id':p,'chapter_id':state['chapter_id'],'main_path':state['main_path'],'requested_path':path,'state_etag':etag,
            'main_etag':doc['etag'],'main_editable':doc['editable'],'canonical_current':preferred==state['main_path'],
            'canonical_id':state['canonical_id'],'recovery_required':self._blocked(ws,folder),'versions':rows,'last_switch':state.get('last_switch'),
            'limits':{'versions':MAX_VERSIONS,'text_bytes':ws.max_bytes,'total_bytes':MAX_STATE_BYTES}}
    def list(self,p,path):
        with self.lock:return self._public(p,path)
    def detail(self,p,path,id):
        with self.lock:
            loaded=self._load(p,path);ws,folder,file,state,etag,doc=loaded
            row=next((copy.deepcopy(v) for v in state['versions'] if v['id']==id),None)
            if not row:_error('NOT_FOUND',404)
            if id==state['canonical_id']:row['content']=_normalized(doc['content'])
            return {'version':{k:v for k,v in row.items() if not k.startswith('_')}|{'etag':_vhash(row),'canonical':id==state['canonical_id']},
                'main_content':_normalized(doc['content']),'state':self._public(p,path,loaded)}
    def _save_state(self,ws,file,state,expected_etag,expected_exists):
        blob=_bytes(state)
        if len(blob)>MAX_STATE_BYTES:_error('LIMIT',413)
        if file.exists()!=expected_exists or expected_exists and digest(file.read_bytes())!=expected_etag:_error('CHANGED')
        if expected_exists:checkpoint(ws.root,file.relative_to(ws.root).as_posix(),'PRE_PARALLEL_VERSION','Parallel version metadata/draft before change')
        if file.exists()!=expected_exists or expected_exists and digest(file.read_bytes())!=expected_etag:_error('CHANGED')
        write_bytes(file,blob);return digest(blob)
    def save(self,p,b,id=None):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            loaded=self._load(p,b.path);ws,folder,file,state,etag,doc=loaded
            self._ensure_clean(ws,folder);content=self._text(ws,b.content);name=b.name.strip()
            if not name:_error('NAME_REQUIRED',422)
            payload=digest(_bytes({'name':name,'description':b.description,'content':content,'id':id}))
            existing=next((v for v in state['versions'] if v['id']==(id or 'version_'+b.request_id)),None)
            if existing and existing.get('_request')==b.request_id:
                if existing.get('_payload')!=payload:_error('REQUEST_REUSED')
                return self.detail(p,b.path,existing['id'])
            if etag!=b.state_etag:_error('CHANGED')
            if id:
                if not existing:_error('NOT_FOUND',404)
                current=self.detail(p,b.path,id)['version']
                if current['etag']!=b.version_etag:_error('CHANGED')
                if id==state['canonical_id'] and content!=_normalized(doc['content']):_error('EDIT_MAIN_IN_EDITOR')
                if existing.get('archived'):_error('ARCHIVED')
                row=existing
            else:
                if existing:_error('REQUEST_REUSED')
                if len(state['versions'])>=MAX_VERSIONS:_error('LIMIT',413)
                row={'id':'version_'+b.request_id,'created_at':now(),'archived':False};state['versions'].append(row)
            row.update(name=name,description=b.description,content=content,updated_at=now(),_request=b.request_id,_payload=payload)
            self._save_state(ws,file,state,etag,doc['_versions_exists'])
            return self.detail(p,b.path,row['id'])
    def archive(self,p,path,id,b):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            ws,folder,file,state,etag,doc=self._load(p,path)
            if not b.confirm:_error('CONFIRM',422)
            self._ensure_clean(ws,folder)
            if etag!=b.state_etag:_error('CHANGED')
            row=next((v for v in state['versions'] if v['id']==id),None)
            if not row:_error('NOT_FOUND',404)
            if id==state['canonical_id']:_error('MAIN_ARCHIVE')
            if bool(row.get('archived'))!=b.archived:
                row.update(archived=b.archived,updated_at=now());self._save_state(ws,file,state,etag,doc['_versions_exists'])
            return self._public(p,path)
    def _op_path(self,ws,folder,id):
        if not re.fullmatch(r'[a-f0-9]{32}',id):_error('NOT_FOUND',404)
        return safe(ws.root,folder+'/operations/'+id+'.json')
    def _existing(self,file,fingerprint):
        if not file.exists():return None
        if file.stat().st_size>128*1024:_error('CORRUPT',422)
        operation=read(file)
        if not isinstance(operation,dict):_error('CORRUPT',422)
        if operation.get('fingerprint')!=fingerprint:_error('REQUEST_REUSED')
        if operation.get('status') not in {'APPLIED','REVIEW_CANDIDATE','UNDONE','RECOVERED'}:_error('RECOVERY_REQUIRED')
        return operation
    def _receipt(self,operation,replayed=False):
        review=bool(operation.get('review_only'))
        return {'id':operation['id'],'status':operation['status'],'path':operation['target'],'paths':[] if review else [operation['target']],
            'canonical_changed':operation['status'] in {'APPLIED','UNDONE','RECOVERED'} and not review,
            'canon_changed':False,'state_changed':False,'knowledge_changed':False,'replayed':replayed,
            'requires_review':review and operation['status']=='REVIEW_CANDIDATE','review_only':review,'version_id':operation.get('to_id')}
    def operations(self,p,path):
        with self.lock:
            ws,folder,file,state,etag,doc=self._load(p,path);base=safe(ws.root,folder+'/operations');rows=[];unavailable=0;scanned=0
            candidates=[]
            for f in base.glob('*.json'):
                try:candidates.append((f.stat().st_mtime_ns,f))
                except OSError:unavailable+=1
            # Two records normally accompany one switch. Inspect a bounded
            # number, counting actual switches rather than undo journals.
            candidates.sort(key=lambda pair:pair[0],reverse=True)
            for _,f in candidates[:1000]:
                scanned+=1
                try:
                    safe(ws.root,f.relative_to(ws.root).as_posix())
                    if f.stat().st_size>128*1024:_error('CORRUPT',422)
                    op=read(f,{})
                    if not isinstance(op,dict) or op.get('id')!=f.stem or not re.fullmatch(r'[a-f0-9]{32}',f.stem):_error('CORRUPT',422)
                    if op.get('action')!='switch':continue
                    if op.get('target')!=state['main_path'] or op.get('main_path')!=state['main_path'] or not isinstance(op.get('status'),str):_error('CORRUPT',422)
                    if any(not isinstance(op.get(key),str) for key in ('at','from_id','to_id','before_name','after_name')) or len(op['at'])>80 or len(op['before_name'])>100 or len(op['after_name'])>100:_error('CORRUPT',422)
                    if not re.fullmatch(ID,op['from_id']) or not re.fullmatch(ID,op['to_id']) or not isinstance(op.get('review_only',False),bool) or not isinstance(op.get('created',False),bool):_error('CORRUPT',422)
                    rows.append({key:op.get(key) for key in ('id','at','status','target','created','review_only','from_id','to_id','before_name','after_name')})
                    if len(rows)>=100:break
                except (ConsoleError,OSError,ValueError,UnicodeError,RecursionError):unavailable+=1
            return {'operations':rows,'unavailable':unavailable,'truncated':scanned<len(candidates),'state':self._public(p,path,(ws,folder,file,state,etag,doc))}
    def _recover(self,ws,state_file,op_file,op,before_state,after_state,before_data,after_data):
        recovered=True;target=ws.resolve(op['target'])
        try:
            current=target.read_bytes()
            if current==after_data:
                checkpoint(ws.root,op['target'],'PARALLEL_FAILED_RECOVERY')
                with writing_origin('VERSION_SWITCH'):ws.save(op['target'],before_data.decode('utf-8-sig'),digest(current))
            elif current!=before_data:recovered=False
        except Exception:recovered=False
        try:
            current=state_file.read_bytes()
            if current==after_state and current!=before_state:write_bytes(state_file,before_state)
            elif current!=before_state:recovered=False
        except Exception:recovered=False
        op['status']='ROLLED_BACK' if recovered else 'RECOVERY_REQUIRED'
        try:write(op_file,op)
        except Exception:pass
        return recovered
    def switch(self,p,b):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            ws,folder,file,state,etag,doc=self._load(p,b.path)
            if not b.confirm:_error('CONFIRM',422)
            op_file=self._op_path(ws,folder,b.request_id);fingerprint=digest(_bytes({'action':'switch',**b.model_dump()}))
            old=self._existing(op_file,fingerprint)
            if old:return self._receipt(old,True)
            self._ensure_clean(ws,folder)
            if b.state_etag!=etag or b.main_etag!=doc['etag']:_error('CHANGED')
            target=next((v for v in state['versions'] if v['id']==b.version_id and not v.get('archived')),None)
            if not target:_error('NOT_FOUND',404)
            if state['canonical_id']==b.version_id:_error('ALREADY_MAIN')
            if _vhash(target)!=b.version_etag:_error('CHANGED')
            if doc['line_ending']=='MIXED':_error('MIXED')
            if b.mode=='switch' and (not doc['editable'] or self._preferred(p,state['chapter_id'],state['main_path'])!=state['main_path']):_error('PROTECTED')
            content=self._text(ws,target['content']);output=content.replace('\n','\r\n') if doc['line_ending']=='CRLF' else content
            after_data=output.encode('utf-8-sig' if doc['bom'] else 'utf8')
            if len(after_data)>ws.max_bytes:_error('TEXT_LIMIT',413)
            before_data=ws.resolve(state['main_path']).read_bytes()
            if digest(before_data)!=doc['etag']:_error('CHANGED')
            before_state=file.read_bytes();before_version=checkpoint(ws.root,state['main_path'],'PRE_VERSION_SWITCH','Author-confirmed parallel version')
            before_state_revision=checkpoint(ws.root,file.relative_to(ws.root).as_posix(),'PRE_VERSION_SWITCH')
            original=next(v for v in state['versions'] if v['id']==state['canonical_id'])
            review_only=b.mode=='revision';target_path=state['main_path']
            op={'id':b.request_id,'action':'switch','fingerprint':fingerprint,'at':now(),'status':'PREPARED','target':target_path,'created':False,'review_only':review_only,
                'main_path':state['main_path'],'from_id':state['canonical_id'],'to_id':target['id'],'before_name':original['name'],'after_name':target['name'],
                'version_etag':_vhash(target),'before_etag':doc['etag'],'after_etag':digest(after_data),'before_revision':before_version['id'],'before_state_revision':before_state_revision['id']}
            if review_only:
                # A protected Final never creates a discoverable chapter draft.
                # Both sides of the review stay frozen in existing checkpoints.
                op.update(status='REVIEW_CANDIDATE',candidate_etag=op['after_etag'],version_etag=_vhash(target),after_etag=doc['etag'])
                write(op_file,op);return self._receipt(op)
            original.update(content=_normalized(doc['content']),updated_at=now());state.update(canonical_id=target['id'],last_switch=b.request_id)
            after_state=_bytes(state)
            op['after_state_etag']=digest(after_state)
            if len(after_state)>MAX_STATE_BYTES:_error('LIMIT',413)
            write(op_file,op);self._mark_pending(ws,folder,b.request_id)
            try:
                if self.tools.doc(p,state['main_path'])['etag']!=doc['etag']:_error('CHANGED')
                with writing_origin('VERSION_SWITCH'):saved=ws.save(target_path,output,doc['etag'])
                if saved['etag']!=op['after_etag']:_error('RECEIPT_MISMATCH')
                if digest(file.read_bytes())!=etag:_error('CHANGED')
                write_bytes(file,after_state)
                op['status']='APPLIED';write(op_file,op)
            except Exception:
                if not self._recover(ws,file,op_file,op,before_state,after_state,before_data,after_data):_error('RECOVERY_REQUIRED')
                raise
            return self._receipt(op)
    def undo(self,p,id,b):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            ws,folder,file,state,etag,doc=self._load(p,b.path)
            if not b.confirm:_error('CONFIRM',422)
            undo_file=self._op_path(ws,folder,b.request_id);fingerprint=digest(_bytes({'action':'undo','operation':id,**b.model_dump()}))
            old=self._existing(undo_file,fingerprint)
            if old:return self._receipt(old,True)
            self._ensure_clean(ws,folder)
            source_file=self._op_path(ws,folder,id);op=read(source_file,{})
            if not isinstance(op,dict):_error('CORRUPT',422)
            if op.get('action')!='switch' or op.get('status') not in {'APPLIED','REVIEW_CANDIDATE'}:_error('UNDO_UNAVAILABLE')
            if etag!=b.state_etag:_error('CHANGED')
            expected_target=state['main_path']
            if op.get('created') or op.get('target')!=expected_target or op.get('main_path')!=state['main_path']:_error('CORRUPT',422)
            if op.get('review_only'):
                undo={'id':b.request_id,'action':'undo','fingerprint':fingerprint,'at':now(),'status':'PREPARED','target':op['target'],'review_only':True,'source':id}
                write(undo_file,undo)
                try:
                    op['status']='UNDONE';write(source_file,op);undo['status']='UNDONE';write(undo_file,undo)
                except Exception:
                    op['status']='REVIEW_CANDIDATE'
                    try:write(source_file,op);undo['status']='ROLLED_BACK';write(undo_file,undo)
                    except Exception:_error('RECOVERY_REQUIRED')
                    raise
                return self._receipt(undo)
            target=self.tools.doc(p,op['target'])
            if not target['editable'] or target['etag']!=op['after_etag']:_error('UNDO_CHANGED')
            if state.get('last_switch')!=id or etag!=op['after_state_etag']:_error('UNDO_CHANGED')
            before_row,before_data=revision_content(ws.root,op['before_revision'])
            state_row,before_state=revision_content(ws.root,op['before_state_revision'])
            if before_row['path']!=state['main_path'] or state_row['path']!=file.relative_to(ws.root).as_posix() or digest(before_data)!=op.get('before_etag'):_error('CORRUPT',422)
            self._text(ws,before_data.decode('utf-8-sig'))
            after_data=ws.resolve(op['target']).read_bytes();after_state=file.read_bytes()
            undo_text=checkpoint(ws.root,op['target'],'PRE_UNDO_VERSION_SWITCH','Undo keeps the completed version recoverable')
            undo_state=checkpoint(ws.root,file.relative_to(ws.root).as_posix(),'PRE_UNDO_VERSION_SWITCH')
            undo={'id':b.request_id,'action':'undo','fingerprint':fingerprint,'at':now(),'status':'PREPARED','target':op['target'],'created':False,'main_path':state['main_path'],'source':id,
                'before_revision':undo_text['id'],'before_state_revision':undo_state['id'],'before_etag':digest(after_data),'after_etag':digest(before_data),
                'after_state_etag':digest(before_state),'source_fingerprint':digest(_bytes(op))}
            write(undo_file,undo);self._mark_pending(ws,folder,b.request_id)
            try:
                if self.tools.doc(p,op['target'])['etag']!=op['after_etag']:_error('UNDO_CHANGED')
                with writing_origin('VERSION_SWITCH'):ws.save(op['target'],before_data.decode('utf-8-sig'),target['etag'])
                if file.read_bytes()!=after_state:_error('UNDO_CHANGED')
                write_bytes(file,before_state)
                op['status']='UNDONE';write(source_file,op);undo['status']='UNDONE';write(undo_file,undo)
            except Exception:
                recovered=True
                try:
                    destination=ws.resolve(op['target'])
                    current=destination.read_bytes()
                    if current==before_data:
                        with writing_origin('VERSION_SWITCH'):ws.save(op['target'],after_data.decode('utf-8-sig'),digest(current))
                    elif current!=after_data:recovered=False
                    current=file.read_bytes()
                    if current==before_state:write_bytes(file,after_state)
                    elif current!=after_state:recovered=False
                except Exception:recovered=False
                undo['status']='ROLLED_BACK' if recovered else 'RECOVERY_REQUIRED'
                if recovered:
                    op['status']='APPLIED'
                    try:write(source_file,op)
                    except Exception:recovered=False;undo['status']='RECOVERY_REQUIRED'
                try:write(undo_file,undo)
                except Exception:pass
                if not recovered:_error('RECOVERY_REQUIRED')
                raise
            return self._receipt(undo)
    def comparison(self,p,path,id):
        with self.lock:
            ws,folder,file,state,etag,doc=self._load(p,path);operation_file=self._op_path(ws,folder,id)
            if operation_file.exists() and operation_file.stat().st_size>128*1024:_error('CORRUPT',422)
            operation=read(operation_file,{})
            if not isinstance(operation,dict) or operation.get('action')!='switch':_error('NOT_FOUND',404)
            if operation.get('id')!=id or operation.get('target')!=state['main_path'] or operation.get('main_path')!=state['main_path']:_error('CORRUPT',422)
            original=self._snapshot(ws,operation.get('before_revision'),state['main_path'],ws.max_bytes)
            snapshot=self._snapshot(ws,operation.get('before_state_revision'),file.relative_to(ws.root).as_posix(),MAX_STATE_BYTES)
            if digest(original)!=operation.get('before_etag'):_error('CORRUPT',422)
            frozen=json.loads(snapshot);self._validate_state(ws,frozen,state['chapter_id'])
            row=next((v for v in frozen['versions'] if v['id']==operation.get('to_id')),None)
            if frozen.get('main_path')!=state['main_path'] or not row:_error('CORRUPT',422)
            if operation.get('version_etag'):
                if _vhash(row)!=operation['version_etag']:_error('CORRUPT',422)
            else:
                # Backward-compatible pre-hardening switch receipts.
                source=original.decode('utf-8-sig');candidate=self._text(ws,row['content'])
                if '\r\n' in source:candidate=candidate.replace('\n','\r\n')
                encoded=candidate.encode('utf-8-sig' if original.startswith(b'\xef\xbb\xbf') else 'utf8')
                if digest(encoded)!=operation.get('candidate_etag',operation.get('after_etag')):_error('CORRUPT',422)
            return {'operation_id':id,'original':self._text(ws,original.decode('utf-8-sig')),'modified':self._text(ws,row['content']),
                'version_name':row['name'],'status':operation['status'],'review_only':bool(operation.get('review_only')),'readonly':True,'canonical_changed':False}
    def _recovery_plan(self,p,path):
        loaded=self._load(p,path);ws,folder,file,state,etag,doc=loaded
        plan={'required':self._blocked(ws,folder),'can_recover':False,'reason':'NOT_NEEDED','main_path':state['main_path'],'state_etag':etag,'main_etag':doc['etag']}
        if not plan['required']:return plan,None
        plan['reason']='INCOMPLETE_HISTORY'
        try:
            marker=safe(ws.root,folder+'/pending.json')
            if marker.stat().st_size>1024:return plan,None
            pending=read(marker,{})
            if not isinstance(pending,dict) or not re.fullmatch(r'[a-f0-9]{32}',str(pending.get('id',''))):return plan,None
            op_file=self._op_path(ws,folder,pending['id'])
            if not op_file.is_file() or op_file.stat().st_size>128*1024:return plan,None
            op=read(op_file,{})
            if not isinstance(op,dict) or op.get('id')!=pending['id'] or op.get('action') not in {'switch','undo'} or op.get('review_only') or op.get('status') not in {'PREPARED','RECOVERY_REQUIRED'}:return plan,None
            plan['operation_id']=op['id'];plan['action']=op['action']
            if op.get('target')!=state['main_path'] or op.get('main_path')!=state['main_path']:return plan,None
            if not all(isinstance(op.get(k),str) and re.fullmatch(HASH,op[k]) for k in ('before_etag','after_etag','after_state_etag')):return plan,None
            before_data=self._snapshot(ws,op.get('before_revision'),state['main_path'],ws.max_bytes)
            before_state=self._snapshot(ws,op.get('before_state_revision'),file.relative_to(ws.root).as_posix(),MAX_STATE_BYTES)
            frozen=json.loads(before_state);self._validate_state(ws,frozen,state['chapter_id'])
            if frozen['main_path']!=state['main_path'] or digest(before_data)!=op['before_etag']:return plan,None
            self._text(ws,before_data.decode('utf-8-sig'))
            plan['original']=_normalized(doc['content']);plan['modified']=_normalized(before_data.decode('utf-8-sig'))
            if not doc['editable'] or self._preferred(p,state['chapter_id'],state['main_path'])!=state['main_path']:
                plan['reason']='PROTECTED';return plan,None
            if doc['etag'] not in {op['before_etag'],op['after_etag']} or etag not in {digest(before_state),op['after_state_etag']}:
                plan['reason']='EXTERNAL_CHANGED';return plan,None
            source_file=source=None
            if op['action']=='undo':
                source_file=self._op_path(ws,folder,op.get('source',''))
                if not source_file.is_file() or source_file.stat().st_size>128*1024:return plan,None
                source=read(source_file,{})
                if not isinstance(source,dict) or source.get('status') not in {'APPLIED','UNDONE'}:return plan,None
                source=dict(source,status='APPLIED')
                if digest(_bytes(source))!=op.get('source_fingerprint'):return plan,None
            token=digest(_bytes({'operation':op,'state_etag':etag,'main_etag':doc['etag'],'before_state':digest(before_state),'source':source}))
            plan.update(can_recover=True,reason='KNOWN_STATE',recovery_etag=token)
            return plan,(loaded,op_file,op,before_data,before_state,source_file,source)
        except (ConsoleError,OSError,ValueError,UnicodeError,RecursionError,KeyError,TypeError):return plan,None
    def recovery(self,p,path):
        with self.lock:return self._recovery_plan(p,path)[0]
    def recover(self,p,b):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            ws,folder,file,state,etag,doc=self._load(p,b.path)
            if not b.confirm:_error('CONFIRM',422)
            receipt_file=self._op_path(ws,folder,b.request_id);fingerprint=digest(_bytes({'action':'recovery',**b.model_dump()}))
            old=self._existing(receipt_file,fingerprint)
            if old:return self._receipt(old,True)
            plan,parts=self._recovery_plan(p,b.path)
            if not parts or not plan['can_recover']:_error('RECOVERY_UNAVAILABLE')
            if (plan['operation_id'],plan['state_etag'],plan['main_etag'],plan['recovery_etag'])!=(b.operation_id,b.state_etag,b.main_etag,b.recovery_etag):_error('CHANGED')
            loaded,op_file,op,before_data,before_state,source_file,source=parts
            checkpoint(ws.root,state['main_path'],'PRE_PARALLEL_RECOVERY','Explicit rollback of incomplete version transaction')
            checkpoint(ws.root,file.relative_to(ws.root).as_posix(),'PRE_PARALLEL_RECOVERY')
            checked,_=self._recovery_plan(p,b.path)
            if checked.get('recovery_etag')!=b.recovery_etag:_error('CHANGED')
            receipt={'id':b.request_id,'action':'recovery','fingerprint':fingerprint,'at':now(),'status':'PREPARED','target':state['main_path'],'main_path':state['main_path'],'created':False,'source':op['id']}
            write(receipt_file,receipt)
            try:
                current=self.tools.doc(p,state['main_path'])
                if current['etag']!=b.main_etag:_error('CHANGED')
                if not current['editable'] or self._preferred(p,state['chapter_id'],state['main_path'])!=state['main_path']:_error('PROTECTED')
                if current['etag']!=digest(before_data):
                    with writing_origin('VERSION_SWITCH'):saved=ws.save(state['main_path'],before_data.decode('utf-8-sig'),current['etag'])
                    if saved['etag']!=digest(before_data):_error('RECEIPT_MISMATCH')
                if digest(file.read_bytes())!=b.state_etag:_error('CHANGED')
                if file.read_bytes()!=before_state:write_bytes(file,before_state)
                if source_file:
                    current=read(source_file,{})
                    if not isinstance(current,dict) or current.get('status') not in {'APPLIED','UNDONE'} or digest(_bytes(dict(current,status='APPLIED')))!=op.get('source_fingerprint'):_error('CHANGED')
                    write(source_file,source)
                op.update(status='ROLLED_BACK',recovered_at=now(),recovery_id=b.request_id);write(op_file,op)
                receipt['status']='RECOVERED';write(receipt_file,receipt)
            except Exception:
                # Keep the original pending marker. No force-overwrite or
                # automatic replay follows a failed author-approved recovery.
                receipt['status']='RECOVERY_REQUIRED'
                try:write(receipt_file,receipt)
                except Exception:pass
                raise
            return self._receipt(receipt)
    def download(self,p,path,id):
        row=self.detail(p,path,id)['version']
        return row['content'].encode('utf-8-sig')

def chapter_version_routes(service):
    router=APIRouter(prefix='/api/projects/{p}/chapter-versions')
    @router.get('')
    def listing(p:str,path:str):return service.list(p,path)
    @router.get('/detail/{id}')
    def detail(p:str,id:str,path:str):return service.detail(p,path,id)
    @router.post('/versions',status_code=201)
    def create(p:str,b:VersionSave):return service.save(p,b)
    @router.put('/versions/{id}')
    def update(p:str,id:str,b:VersionSave):return service.save(p,b,id)
    @router.post('/versions/{id}/archive')
    def archive(p:str,id:str,b:VersionArchive):return service.archive(p,b.path,id,b)
    @router.post('/switch')
    def switch(p:str,b:VersionSwitch):return service.switch(p,b)
    @router.get('/recovery')
    def recovery(p:str,path:str):return service.recovery(p,path)
    @router.post('/recovery')
    def recover(p:str,b:VersionRecovery):return service.recover(p,b)
    @router.get('/operations')
    def operations(p:str,path:str):return service.operations(p,path)
    @router.get('/operations/{id}/comparison')
    def comparison(p:str,id:str,path:str):return service.comparison(p,path,id)
    @router.post('/operations/{id}/undo')
    def undo(p:str,id:str,b:VersionUndo):return service.undo(p,id,b)
    @router.get('/detail/{id}/download')
    def download(p:str,id:str,path:str):return Response(service.download(p,path,id),media_type='text/plain; charset=utf-8',headers={'Content-Disposition':'attachment; filename="parallel-draft-'+id+'.txt"','Cache-Control':'no-store'})
    return router
