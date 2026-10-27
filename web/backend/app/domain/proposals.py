"""Reviewed multi-file changes with a rollback journal; never writes story State."""
import base64
import difflib
import hashlib
import os
import re
import uuid
from typing import Literal
from pydantic import Field
from app.domain.characters import Strict
from app.errors import ConsoleError
from app.atomic import replace
from app.projects.service import write_yaml,now

class Operation(Strict):
    path:str=Field(min_length=1,max_length=300)
    action:Literal['write','delete']='write'
    content:str=Field(max_length=2*1024*1024)
class ProposalEdit(Strict):
    version:int=Field(ge=1)
    operations:list[Operation]=Field(min_length=1,max_length=500)

class Proposals:
    def __init__(self,registry):self.registry=registry
    def path(self,id):
        if not re.fullmatch(r'change_[0-9a-f]{32}',id):raise ConsoleError('无效候选 ID',403)
        return 'metadata/domain-proposals/'+id+'.yaml'
    def get(self,project,id):
        value=self.registry.workspace(project).yaml_file(self.path(id))
        if value.get('project_id')!=project:raise ConsoleError('候选不属于当前小说',404)
        return value
    def target(self,ws,path):
        # State paths are permitted only for internal new-character bootstrap
        # and rollback journals. Candidate validators reject every State op.
        if not path.startswith(('characters/','outlines/')) and not re.fullmatch(r'state/characters/[A-Za-z0-9_-]{1,64}\.yaml',path):raise ConsoleError('候选/事务目标范围错误',403)
        return ws.resolve(path)
    def stage(self,project,kind,operations,explanation,skills,bases,validate):
        ws=self.registry.workspace(project)
        if len({op['path'] for op in operations})!=len(operations):raise ConsoleError('重复候选路径',422)
        validate(operations)
        id='change_'+uuid.uuid4().hex
        diffs=[]
        for operation in operations:
            p=self.target(ws,operation['path']);old=ws.content(operation['path'])['content'] if p.exists() else ''
            diffs.append(''.join(difflib.unified_diff(old.replace('\r\n','\n').splitlines(True),operation['content'].replace('\r\n','\n').splitlines(True),fromfile=operation['path']+' (current)',tofile=operation['path']+' (proposed)')))
        value={'id':id,'project_id':project,'kind':kind,'version':1,'status':'PROPOSED','operations':operations,'explanation':explanation,'diff':'\n'.join(diffs),'skills':skills,'bases':bases,'created_at':now()}
        write_yaml(ws.resolve(self.path(id)),value);return value
    def update(self,project,id,version,operations,validate):
        if self.registry.get(project)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
        old=self.get(project,id)
        if old['version']!=version or old['status']!='PROPOSED':raise ConsoleError('候选版本或状态已变化',409)
        if {x['path'] for x in operations}!={x['path'] for x in old['operations']}:raise ConsoleError('编辑候选不能改变目标集合',409)
        if len({op['path'] for op in operations})!=len(operations):raise ConsoleError('重复候选路径',422)
        validate(operations);ws=self.registry.workspace(project);diff=[]
        for op in operations:
            p=self.target(ws,op['path']);current=ws.content(op['path'])['content'] if p.exists() else ''
            diff.append(''.join(difflib.unified_diff(current.replace('\r\n','\n').splitlines(True),op['content'].replace('\r\n','\n').splitlines(True),fromfile=op['path']+' (current)',tofile=op['path']+' (proposed)')))
        old.update(operations=operations,version=version+1,diff='\n'.join(diff));write_yaml(ws.resolve(self.path(id)),old);return old
    def discard(self,project,id,version):
        if self.registry.get(project)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
        value=self.get(project,id)
        if value['version']!=version or value['status']!='PROPOSED':raise ConsoleError('候选版本或状态已变化',409)
        value.update(status='DISCARDED',version=version+1);write_yaml(self.registry.workspace(project).resolve(self.path(id)),value);return value
    def commit(self,project,id,version,validate,after=None,initialize=None):
        with self.registry.lock:
            ws=self.registry.workspace(project);value=self.get(project,id)
            if self.registry.get(project)['status']['phase']=='ARCHIVED':raise ConsoleError('归档项目只读',409)
            if value['version']!=version or value['status']!='PROPOSED':raise ConsoleError('候选已变化',409)
            for path,etag in value['bases'].items():
                p=ws.resolve(path)
                current=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
                if current!=etag:raise ConsoleError('候选资料基线已改变，请重新生成：'+path,409)
            validate(value['operations'])
            backup={};payloads={}
            initializations=initialize(value) if initialize else []
            for op in initializations:
                if not re.fullmatch(r'state/characters/[A-Za-z0-9_-]{1,64}\.yaml',op['path']) or ws.resolve(op['path']).exists():raise ConsoleError('人物 State 初始化仅允许不存在的空容器目标',409)
            for op in value['operations']+initializations:
                p=self.target(ws,op['path']);data=p.read_bytes() if p.exists() else None
                backup[op['path']]=base64.b64encode(data).decode() if data is not None else None
                content=op['content'].replace('\r\n','\n')
                if data and b'\r\n' in data:content=content.replace('\n','\r\n')
                payloads[op['path']]=content.encode('utf-8-sig' if data and data.startswith(b'\xef\xbb\xbf') else 'utf8') if op.get('action','write')!='delete' else None
            journal={'status':'PENDING','change_id':id,'backups':backup,'new_hashes':{p:hashlib.sha256(b).hexdigest() if b is not None else None for p,b in payloads.items()}}
            jp=ws.resolve('metadata/transactions/'+id+'.yaml');write_yaml(jp,journal)
            try:
                for path,data in payloads.items():self.write(self.target(ws,path),data)
                if after:after(value)
                journal['status']='COMPLETE';write_yaml(jp,journal)
                value.update(status='ACCEPTED',version=version+1);write_yaml(ws.resolve(self.path(id)),value)
            except Exception:
                self.rollback(ws,journal);journal['status']='ROLLED_BACK';write_yaml(jp,journal);raise
            return value
    @staticmethod
    def write(path,data):
        if data is None:
            if path.exists():path.unlink()
            return
        path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.transaction-'+uuid.uuid4().hex)
        with temp.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        replace(temp,path)
    def rollback(self,ws,journal):
        for path,encoded in journal['backups'].items():
            p=self.target(ws,path);old=base64.b64decode(encoded) if encoded is not None else None
            current=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
            if current not in {hashlib.sha256(old).hexdigest() if old is not None else None,journal['new_hashes'][path]}:raise ConsoleError('事务恢复发现外部修改，保留日志并停止：'+path,409)
            self.write(p,old)
    def recover(self,project):
        ws=self.registry.workspace(project)
        for f in ws.list_files():
            if not f['path'].startswith('metadata/transactions/'):continue
            journal=ws.yaml_file(f['path'])
            if journal.get('status')=='PENDING':
                self.rollback(ws,journal);journal['status']='ROLLED_BACK';write_yaml(ws.resolve(f['path']),journal)
            elif journal.get('status')=='COMPLETE':
                proposal=self.get(project,journal['change_id'])
                if proposal['status']=='PROPOSED':
                    proposal.update(status='ACCEPTED',version=proposal['version']+1)
                    write_yaml(ws.resolve(self.path(proposal['id'])),proposal)
