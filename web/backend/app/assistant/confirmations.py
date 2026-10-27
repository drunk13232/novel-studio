"""Frozen, one-shot approvals over the existing Action Registry and TaskManager."""
import hashlib,json,time,uuid
from datetime import datetime,timezone,timedelta
from app.assistant.actions import TOOLS
from app.errors import ConsoleError
from app.library.storage import read,now,safe
from app.tasks.storage import atomic_json
from app.models.requests import TaskRequest,TaskOptions

class Confirmations:
    def __init__(self,center):
        self.center=center;self.path=center.root/'assistant-proposals.json';self.rows=read(self.path,{})
        # Session identities/IPC capabilities are process-owned. Never resume old writes.
        for row in self.rows.values():
            if row['status'] in {'PENDING','EXECUTING'}:row.update(status='CANCELLED',reason='应用已重启，请重新提出操作')
        if self.rows:self.save()
    def expire(self,s):
        with self.center.lock:
            row=self.rows.get(s.pending.get('token')) if s.pending and s.pending.get('kind')=='confirm' else None
            if row and row['status']=='PENDING' and datetime.now(timezone.utc)>=datetime.fromisoformat(row['expires_at']):self.invalidate(s,'EXPIRED','确认已过期')
    def save(self):atomic_json(self.path,self.rows)
    def revision(self,s):
        parts=[]
        if s.project:
            root=self.center.app.state.registry.workspace(s.project).root
            paths=[root/'project.yaml']
            for top in ('characters','bible','state'):
                paths.extend(sorted((root/top).glob('**/*.yaml')))
            if s.context.path:paths.append(safe(root,s.context.path))
            for path in paths:
                if path.is_file():parts.append([str(path.relative_to(root)),hashlib.sha256(path.read_bytes()).hexdigest()])
        return hashlib.sha256(json.dumps(parts,sort_keys=True).encode()).hexdigest()
    def propose(self,s,name,args,row):
        with self.center.lock:
            if s.pending:raise ConsoleError('已有待确认操作，请处理后再发送',409)
            id=row['id'];created=datetime.now(timezone.utc)
            record={'action_id':id,'project_id':s.project,'session_id':s.id,'action_type':name,'validated_parameters':args,'affected_resources':[s.context.path or '当前作品草稿/界面'],'expected_revision':self.revision(s),'risk_level':row['level'],'created_at':created.isoformat(),'expires_at':(created+timedelta(minutes=30)).isoformat(),'status':'PENDING','permissions':s.settings.model_dump(),'reversible':True,'extra_save':False}
            self.rows[id]=record;self.save()
            s.pending={'token':id,'kind':'confirm','tool':name,'arguments':args,'project':s.project,'action_id':id,'affected_resources':record['affected_resources'],'expires_at':record['expires_at'],'reversible':True,'extra_save':False,'message':'审批固定操作，模型回合结束后仍可确认；不会授权其他操作。'}
            row['status']='等待确认';s.timing.mark('confirmation_pending','等待确认');s.timing.save()
            return {'ok':False,'pending_confirmation':True,'action_id':id,'status':'PENDING_CONFIRMATION','message':'应用已保存操作；等待用户确认，不要重复调用或执行后续写入。'}
    def invalidate(self,s,status='CANCELLED',reason='用户停止'):
        with self.center.lock:
            for row in self.rows.values():
                if row['session_id']==s.id and row['status']=='PENDING':
                    row.update(status=status,reason=reason)
                    step=next((x for x in s.steps if x['id']==row['action_id']),None)
                    if step:step.update(status=reason)
            self.save()
            if s.pending and s.pending['kind']=='confirm':s.pending=None
    def approve(self,s,b):
        with self.center.lock:
            record=self.rows.get(b.token)
            if not record or record['session_id']!=s.id:raise ConsoleError('确认不属于本次会话',409)
            if record['status'] in {'EXECUTING','SUCCEEDED'}:
                if b.context is None or b.context.project!=record['project_id']:raise ConsoleError('项目已切换，旧确认无效',409)
                return {'acknowledged':True,'duplicate':True,'status':record['status']}
            if record['status']!='PENDING':raise ConsoleError('确认已拒绝、取消或过期，未执行',409)
            if b.context is None or b.context.project!=record['project_id'] or s.project!=record['project_id'] or s.scope_changed:
                self.invalidate(s,reason='项目已切换');raise ConsoleError('项目已切换，旧确认无效',409)
            if s.cancelled or datetime.now(timezone.utc)>=datetime.fromisoformat(record['expires_at']):
                self.invalidate(s,'EXPIRED','操作已取消或确认过期');raise ConsoleError('确认已取消或过期，未执行',409)
            if not b.approved:
                self.invalidate(s,'REJECTED','用户拒绝');s.timing.mark('confirmation_rejected','用户拒绝');s.timing.save();return {'acknowledged':True,'status':'REJECTED'}
            cfg=self.center.settings(s.persona,s.project)
            if any(record['permissions'].get(k) and not getattr(cfg,k) for k in ('page','selection','setting_context','references','style','manuscript')):
                self.invalidate(s,reason='上下文权限已收回');raise ConsoleError('权限已变化，请重新提出操作',409)
            name=record['action_type'];args=TOOLS[name].schema.model_validate(record['validated_parameters']).model_dump()
            if self.revision(s)!=record['expected_revision'] or name=='propose_chapter_revision' and any(getattr(b.context,k)!=getattr(s.context,k) for k in ('path','document_revision','selection','start','end')):
                self.invalidate(s,reason='目标版本已变化');raise ConsoleError('目标版本已变化，请重新检查差异',409)
            # Claim before scheduling. Duplicate approvals cannot create another Task.
            record.update(status='EXECUTING',approved_at=now());self.save();s.pending=None
            row=next(x for x in s.steps if x['id']==record['action_id']);row['status']='正在执行';s.confirming=True;s.deadline=time.monotonic()+60
            req=TaskRequest(type='custom_prompt',prompt='执行已确认的固定应用操作',options=TaskOptions(read_only=True,resume=False,timeout_seconds=60))
            s.execution_task=s.manager.prepared(req,'固定操作审批执行',True,'assistant-action-'+record['action_id'],execute=lambda emit,cancel:self.center.finish(s,lambda:self.execute(s,record,row,cancel)),provider='作者确认 / 应用 Dispatcher',skill='固定操作，不调用模型',application_actions=True)
            s.execution_task.private_text=True;s.manager.store.save(s.execution_task)
            return {'acknowledged':True,'status':'EXECUTING','action_id':record['action_id']}
    def execute(self,s,record,row,cancel):
        try:
            s.timing.mark('confirmation_approved','正在执行')
            if cancel():s.stop()
            # Re-check under the same mutation lease used by the existing Action Dispatcher.
            result=s.execute_action(record['action_type'],record['validated_parameters'],row,expected_revision=record['expected_revision'])
            with self.center.lock:record.update(status='SUCCEEDED',executed_at=now(),receipt={'ok':True,'id':result.get('id'),'proposal_id':result.get('proposal_id'),'status':result.get('status')});self.save()
            s.mcp_state='已确认操作收到应用执行回执';s.output='作者确认的固定操作已执行；没有再次调用模型规划。'
            return {'status':'completed','output':s.output}
        except Exception as error:
            from app.ai.credentials import scrub
            row.update(status='操作取消' if s.cancelled else '操作失败',error=scrub(str(error))[:400]);self.center.audit(s,row,False)
            s.output='操作已取消，未自动重试。' if s.cancelled else '已确认操作执行失败；请查看错误详情，未自动重试。'
            with self.center.lock:record.update(status='CANCELLED' if s.cancelled else 'FAILED',reason='执行失败；没有自动重试');self.save()
            return {'status':'interrupted' if s.cancelled else 'failed','error':row['error']}
        finally:
            s.confirming=False;s.timing.mark('request_complete','已取消' if s.cancelled else record['status']);s.timing.save()
