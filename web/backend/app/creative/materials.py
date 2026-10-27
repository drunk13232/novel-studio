"""Traceable handoff into existing author notes; never a new fact or memory store."""
import json,re
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from fastapi import APIRouter
from app.errors import ConsoleError
from app.author_workbench import Entry
from app.library.storage import digest
from app.studio_tools import normalized

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class Origin(Strict):
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    chapter:int|None=Field(default=None,ge=0,le=99999)
    quote:str=Field(default='',max_length=6000)
class Take(Strict):
    kind:Literal['roleplay','behavior','world_report','world_proposal']
    source_id:str=Field(min_length=1,max_length=80)
    session_id:str=Field(default='',max_length=80)
    branch_id:str=Field(default='',max_length=80)
    node_ids:list[str]=Field(default_factory=list,max_length=20)
    index:int=Field(default=0,ge=0,le=50)
    origin:Origin
    confirm:Literal[True]
class Edit(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    text:str=Field(min_length=1,max_length=12000)

class Materials:
    def __init__(self,writing,roleplay,world):self.writing=writing;self.notes=writing.workbench;self.roleplay=roleplay;self.world=world
    def list(self,p):
        row=self.notes.entries(p);items=[]
        for n in row['notes']:
            if n.get('category')!='creative_material' or n.get('status') in {'ARCHIVED','IGNORED'}:continue
            try:origin=json.loads(n.get('note','{}'))
            except (ValueError,TypeError):origin={}
            items.append({**n,'provenance':origin,'is_hypothesis':True,'writer_review_required':True})
        return {'etag':row['etag'],'items':items[-200:]}
    def origin(self,p,b):
        doc=self.writing.tools.doc(p,b.path)
        if doc['etag']!=b.revision:raise ConsoleError('返回章节已发生变化，请保存并重新从当前章节进入实验室',409)
        if b.quote and b.quote not in normalized(doc):raise ConsoleError('选段已变化，请重新选择实验素材来源',409)
        return doc
    def take(self,p,b):
        self.writing.tools.writable(p);self.origin(p,b.origin)
        if b.kind=='roleplay':
            s=self.roleplay.get(p,b.source_id,b.branch_id or None);messages=[m for m in s['messages'] if m['id'] in b.node_ids]
            if not messages or len(messages)!=len(set(b.node_ids)):raise ConsoleError('请明确选取当前分支的模拟片段',409)
            text='\n\n'.join(m['speaker_name']+'：'+m['text'] for m in messages);title=s['title'];epistemic='SIMULATED_DIALOGUE_NOT_CANON'
        elif b.kind=='behavior':
            s=self.roleplay.checked(p,b.session_id);a=next((a for a in self.roleplay.analyses(p,b.session_id) if a['id']==b.source_id),None)
            if not a or (b.branch_id and a['branch_id']!=b.branch_id):raise ConsoleError('行为分析不属于当前会话分支',403)
            options=a['value']['possibilities']
            if b.index>=len(options):raise ConsoleError('行为方案不存在',404)
            o=options[b.index];text='\n'.join([o['action'],'依据：'+'；'.join(o['basis']),'前提：'+'；'.join(o['premises']),'可能后果：'+'；'.join(o['consequences']),'不确定：'+'；'.join(o['uncertainty'])]);title=s['title'];epistemic='CONDITIONAL_AI_OPINION'
        elif b.kind=='world_report':
            a=self.world.report(p,b.source_id);title=a['definition']['name'];text='实验问题：'+a['definition']['description']+'\n本次结果：'+a['status']
            text+='\n前提：'+'；'.join(x['text'] for x in a['definition']['assumptions'])
            text+='\n输入：'+'；'.join(x['name']+'='+str(x['value'])+' '+x['unit'] for x in a['definition']['inputs'])
            text+='\n计算：'+'；'.join(x['name']+'='+str(x.get('value'))+' '+x.get('unit','') for x in a.get('outputs',[]))
            text+='\n验收：'+'；'.join(x['name']+'：'+x['status']+' '+x.get('detail','') for x in a.get('acceptance_results',[]))
            text+='\n局限：'+'；'.join(a['definition'].get('limitations',[]))+('；原始来源已变化，请重新核对。' if a.get('source_changes') else '')
            epistemic='CONDITIONAL_SOLVER_RESULT_NOT_CANON'
        else:
            a=self.world.proposal(p,b.source_id)
            if a['status']=='REJECTED' or b.index>=len(a['value']['findings']):raise ConsoleError('推演建议不存在或已拒绝',409)
            o=a['value']['findings'][b.index];title=o['title'];text='\n'.join([title,'成立条件：'+o['condition'],'缺失：'+o['gap'],'建议：'+o['suggestion'],'代价：'+o.get('tradeoffs','')]);epistemic='CONDITIONAL_AI_OPINION'
        if len(text)>12000:raise ConsoleError('素材过长，请减少选取的片段',413)
        provenance={**b.model_dump(exclude={'confirm','origin'}),'origin':{**b.origin.model_dump(exclude={'quote'}),'quote_sha256':digest(b.origin.quote.encode())},'title':title,'epistemic':epistemic,'source_text_sha256':digest(text.encode())}
        key='MATERIAL:'+b.kind+':'+b.source_id+':'+digest(json.dumps(provenance,sort_keys=True,ensure_ascii=False).encode())
        with self.notes.lock:
            rows=self.notes.entries(p);old=next((n for n in rows['notes'] if n.get('source')==key),None)
            if old:return {'note_id':old['id'],'material':old,'canon_changed':False,'writer_approval':False}
            saved=self.notes.save_entry(p,Entry(etag=rows['etag'],kind='inspiration',text=text,path=b.origin.path,revision=b.origin.revision,category='creative_material',source=key,note=json.dumps(provenance,ensure_ascii=False),tags=['CREATIVE_MATERIAL','HYPOTHESIS']))
            item=next(n for n in saved['notes'] if n['source']==key)
            return {'note_id':item['id'],'material':item,'canon_changed':False,'writer_approval':False}
    def edit(self,p,id,b):
        with self.notes.lock:
            r=self.notes.entries(p);n=next((n for n in r['notes'] if n['id']==id and n.get('category')=='creative_material'),None)
            if not n:raise ConsoleError('写作素材不属于当前作品',404)
            values={k:v for k,v in n.items() if k in Entry.model_fields};values.update(etag=b.etag,text=b.text)
            self.notes.save_entry(p,Entry(**values));return self.list(p)

def routes(s):
    r=APIRouter(prefix='/api/projects/{p}/writing-assist/materials')
    @r.get('')
    def list_(p:str):return s.list(p)
    @r.post('')
    def take(p:str,b:Take):return s.take(p,b)
    @r.patch('/{id}')
    def edit(p:str,id:str,b:Edit):return s.edit(p,id,b)
    return r
