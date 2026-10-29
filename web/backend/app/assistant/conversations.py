"""Private assistant dialogue in the existing AI data root, never Canon or task logs."""
import hashlib,json,re,threading
from app.tasks.storage import atomic_json
from app.library.storage import read,now
from app.roleplay.context import fit
from app.ai.credentials import scrub
from app.errors import ConsoleError
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal

PERSONAS=('assistant','yoshino','rem','haru')
class ChatStep(BaseModel):
    model_config=ConfigDict(extra='forbid')
    tool:str=Field(max_length=100)
    status:str=Field(max_length=100)
    record_id:str|None=Field(default=None,pattern=r'^director_[0-9a-f]{32}$')
    record_path:str|None=Field(default=None,pattern=r'^chapters/(?:story|chapter-[0-9]+)/(?:draft|final|manual-[a-z0-9-]+)\.(?:txt|md)$')
    candidate_id:str|None=Field(default=None,pattern=r'^[0-9a-f]{32}$')
    candidate_path:str|None=Field(default=None,pattern=r'^chapters/(?:story|chapter-[0-9]+)/(?:draft|final|manual-[a-z0-9-]+)\.(?:txt|md)$')
class ChatRow(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(min_length=1,max_length=100)
    at:str=Field(max_length=80)
    instruction:str=Field(max_length=16000)
    output:str=Field(max_length=1000000)
    status:str=Field(max_length=80)
    pending_confirmation:bool=False
    provider:str=Field(default='',max_length=100)
    model:str=Field(default='',max_length=160)
    steps:list[ChatStep]=Field(default_factory=list,max_length=100)
    ai_metadata:dict=Field(default_factory=dict)
class ChatScope(BaseModel):
    model_config=ConfigDict(extra='forbid')
    persona:Literal['assistant','yoshino','rem','haru']
    model:str=Field(min_length=1,max_length=250)
    rows:list[ChatRow]=Field(default_factory=list,max_length=20000)

def checked_scopes(scopes):
    if not isinstance(scopes,list) or len(scopes)>400:raise ConsoleError('助手会话备份规模或结构无效',422)
    rows=[ChatScope.model_validate(v).model_dump() for v in scopes]
    for scope in rows:
        for r in scope['rows']:r['instruction']=clean(r['instruction']);r['output']=clean(r['output'])
    keys=[(v['persona'],model_scope(v['model'])) for v in rows]
    if len(keys)!=len(set(keys)):raise ConsoleError('助手备份包含重复会话作用域',422)
    return rows

def model_scope(model):return 'codex-software' if model in {'codex','codex-software'} else model

def clean(text):
    text=scrub(str(text))
    return re.sub(r'(?i)(?:sk-[a-z0-9_-]{12,}|Bearer\s+[a-z0-9._-]{16,})','[REDACTED_SECRET]',text)

class Conversations:
    def __init__(self,root):self.root=root/'assistant-conversations';self.lock=threading.RLock()
    def path(self,project,persona,model):
        key=json.dumps([project,persona,model_scope(model)],ensure_ascii=False)
        return self.root/(hashlib.sha256(key.encode()).hexdigest()+'.json')
    def register(self,project,persona,model):
        index=read(self.root/'scopes.json',{});path=self.path(project,persona,model)
        index[path.stem]={'project':project,'persona':persona,'model':model_scope(model)}
        atomic_json(self.root/'scopes.json',index)
    def export_project(self,project,models):
        # Scope descriptors contain no dialogue. Legacy files are addressed by known hashes only.
        with self.lock:
            scopes=[v for k,v in read(self.root/'scopes.json',{}).items() if isinstance(v,dict) and v.get('project')==project and v.get('persona') in PERSONAS and self.path(project,v['persona'],v.get('model','')).stem==k]
            scopes += [{'persona':persona,'model':model} for persona in PERSONAS for model in models]
            result={};size=0
            for v in scopes:
                key=(v['persona'],model_scope(v['model']));path=self.path(project,*key)
                if path.is_file() and key not in result:
                    size+=path.stat().st_size
                    if size>23*1024*1024:raise ConsoleError('助手会话备份超过23MiB，请分开导出或取消包含私人记录',413)
                    result[key]={'persona':key[0],'model':key[1],'rows':read(path,[])}
            return checked_scopes(list(result.values()))
    def restored_files(self,project,scopes):
        index=read(self.root/'scopes.json',{});pending={}
        for scope in checked_scopes(scopes):
            persona=scope['persona'];model=model_scope(scope['model']);path=self.path(project,persona,model)
            rows=scope['rows']
            for r in rows:
                r['instruction']=clean(r['instruction']);r['output']=clean(r['output'])
                if r['pending_confirmation'] or r['status'] not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:
                    r['status']='INTERRUPTED';r['pending_confirmation']=False
            pending['assistant-conversations/'+path.name]=rows
            index[path.stem]={'project':project,'persona':persona,'model':model}
        pending['assistant-conversations/scopes.json']=index
        return pending
    def rows(self,project,persona,model):
        with self.lock:return read(self.path(project,persona,model),[])
    def portable_rows(self,project,persona,model):
        """Visible portable text, scoped by project/persona; no native tool data."""
        with self.lock:
            index=read(self.root/'scopes.json',{});paths={self.path(project,persona,model)}
            for key,value in index.items():
                if value.get('project')==project and value.get('persona')==persona:
                    path=self.path(project,persona,value['model'])
                    if path.stem==key:paths.add(path)
            if sum(p.stat().st_size for p in paths if p.is_file())>40000000:raise ConsoleError('此角色跨模型讨论超过40MB，请按模型检索或导出整理',413)
            result={r['id']:r for p in paths for r in read(p,[])}
            return sorted(result.values(),key=lambda r:(r['at'],r['id']))
    def page(self,project,persona,model,query='',before=None,limit=40,portable=False):
        rows=self.portable_rows(project,persona,model) if portable else self.rows(project,persona,model)
        if before:rows=rows[:next((i for i,r in enumerate(rows) if r['id']==before),len(rows))]
        if query:rows=[r for r in rows if query.casefold() in (r['instruction']+'\n'+r['output']).casefold()]
        return {'rows':rows[-limit:],'has_more':len(rows)>limit,'next_before':rows[-limit]['id'] if len(rows)>limit else None,'scope':{'project':project,'persona':persona,'model':model_scope(model)},'models':sorted({model_scope(model),*[v['model'] for k,v in read(self.root/'scopes.json',{}).items() if isinstance(v,dict) and v.get('project')==project and v.get('persona')==persona and isinstance(v.get('model'),str) and self.path(project,persona,v['model']).stem==k]})}
    def context(self,project,persona,model,portable=False):
        # Existing roleplay budget logic; past discussion is data, never approval.
        rows=[r for r in (self.portable_rows(project,persona,model) if portable else self.rows(project,persona,model))[-200:] if r['status']=='SUCCEEDED' and not r.get('pending_confirmation')]
        values=[{'id':r['id'],'instruction':r['instruction'],'reply':r['output'],'model':r.get('model'),'at':r.get('at')} for r in rows]
        return values if portable else fit(values[-12:],10000)
    def put(self,s):
        if not s.settings.save_conversation:return
        if s.chat_digest and not s.ended and not s.cancelled and not s.pending:return
        steps=[]
        for r in s.steps:
            step={'tool':r['tool'],'status':r['status']};result=r.get('result') or {}
            # Persist only a validated local pointer, never manuscript content,
            # prompts, credentials, model output or arbitrary tool payloads.
            if r['status']=='已完成' and result.get('candidate_id') and result.get('path'):
                try:step=ChatStep(**step,candidate_id=result['candidate_id'],candidate_path=result['path']).model_dump(exclude_none=True)
                except ValueError:pass
            if r['status']=='已完成' and result.get('record_id') and result.get('path'):
                try:step=ChatStep(**{**step,'record_id':result['record_id'],'record_path':result['path']}).model_dump(exclude_none=True)
                except ValueError:pass
            steps.append(step)
        row={'id':s.id,'at':s.chat_at,'instruction':clean(s.instruction),'output':clean(s.output),
             'status':'CANCELLED' if s.cancelled else 'WAITING_CONFIRMATION' if s.pending and s.pending['kind']=='confirm' else (s.execution_task.status if s.execution_task else s.chat_status),
             'pending_confirmation':bool(s.pending),'provider':s.provider.display_name if s.provider else '', 'model':s.model.id if s.model else '', 'steps':steps,'ai_metadata':getattr(s,'ai_metadata',{})}
        digest=hashlib.sha256(json.dumps(row,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        if digest==getattr(s,'chat_digest',None):return
        with self.lock:
            path=self.path(s.chat_project,s.persona,s.chat_model);rows=read(path,[])
            i=next((i for i,r in enumerate(rows) if r['id']==s.id),len(rows))
            if i<len(rows):rows[i]=row
            else:rows.append(row)
            if len(json.dumps(rows,ensure_ascii=False).encode())>20000000:raise ConsoleError('此角色与模型的本地聊天记录已达20MB，请先导出或清理；本次结果仍在当前窗口',413)
            atomic_json(path,rows);self.register(s.chat_project,s.persona,s.chat_model);s.chat_digest=digest
    def clear(self,project,persona,model):
        with self.lock:
            atomic_json(self.path(project,persona,model),[]);self.register(project,persona,model)
