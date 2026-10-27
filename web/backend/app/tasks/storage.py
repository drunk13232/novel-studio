"""Atomic task metadata and append-only event evidence. No database."""
import json
import os
import re
import uuid
from pathlib import Path
from app.errors import ConsoleError
from app.atomic import replace


def process_alive(pid):
    if not isinstance(pid,int) or pid<=0:return False
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x00100000,False,pid)
        if not handle:return ctypes.get_last_error()==5
        try:return kernel.WaitForSingleObject(handle,0)==258
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0);return True
    except OSError:return False


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.pending-' + uuid.uuid4().hex)
    with temp.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    replace(temp, path)


class TaskStore:
    def __init__(self, engine):
        self.root = engine / 'web/runtime/tasks'
        self.root.mkdir(parents=True, exist_ok=True)
        self.path('0' * 32)

    def path(self, id):
        if not re.fullmatch(r'[0-9a-f]{32}', id):
            raise ConsoleError('无效任务 ID', 404)
        p = self.root / id
        for part in [p, self.root, self.root.parent, self.root.parent.parent]:
            if part.is_symlink() or part.is_junction():
                raise ConsoleError('任务存储链接被拒绝', 403)
        return p

    def save(self, task):
        row = task.public()
        row.update(request=task.request.model_dump(), workspace=str(task.workspace),
                   event_sequence=task.event_sequence, target=task.target,owner_pid=os.getpid())
        if task.private_text:
            row['prompt']='[未保存私人输入]';row['request']['prompt']='普通 API 文本建议（未保存输入）'
            row['result']=({'id':task.result.get('id'),'summary':'实验 Proposal 在项目实验资料中单独保存；任务日志不重复私人资料'} if task.request.type=='world_logic_design' else {'summary':'结果仅在本次会话可见；默认不保存完整对话'}) if task.result else None
            row['result_summary']='[未保存私人结果]'
        atomic_json(self.path(task.id) / 'task.json', row)
        if task.result is not None:
            atomic_json(self.path(task.id) / 'result.json', row['result'])

    def append(self, task, event):
        if task.private_text and event['type'] in {'llm_delta','message','reasoning_summary'}:event={**event,'message':'[未保存正文片段]','data':{}}
        p = self.path(task.id) / 'events.jsonl'; p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_symlink() or p.is_junction(): raise ConsoleError('事件链接被拒绝', 403)
        with p.open('a', encoding='utf8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
            stream.flush()

    def rows(self, workspace=None):
        rows=[]
        for folder in self.root.iterdir():
            if not re.fullmatch(r'[0-9a-f]{32}', folder.name): continue
            p=self.path(folder.name)/'task.json'
            if p.is_symlink(): raise ConsoleError('任务元数据链接被拒绝',403)
            try:
                row=json.loads(p.read_text(encoding='utf8'))
                if row['id']!=folder.name: continue
                if workspace is None or row.get('workspace')==str(workspace): rows.append(row)
            except (OSError,ValueError,KeyError): continue
        return sorted(rows,key=lambda x:x['created_at'])

    def recover(self):
        from app.tasks.manager import now
        for row in self.rows():
            if row['status'] not in {'RUNNING','QUEUED'}: continue
            # Another development/desktop backend may still own this task.
            # Legacy rows have no process evidence: retain them, never guess.
            owner=row.get('owner_pid')
            if owner is None or process_alive(owner):continue
            row.update(status='INTERRUPTED',reason='backend_restart',error='后端重启，任务已中断；未自动恢复执行',finished_at=now())
            row['event_sequence']=row.get('event_sequence',0)+1
            event={'id':row['event_sequence'],'task_id':row['id'],'type':'task_interrupted','timestamp':now(),'message':row['error'],'data':{'status':'INTERRUPTED','reason':'backend_restart'}}
            with (self.path(row['id'])/'events.jsonl').open('a',encoding='utf8') as f: f.write(json.dumps(event,ensure_ascii=False)+'\n')
            atomic_json(self.path(row['id'])/'task.json',row)

    def page(self, id, before=None, limit=200):
        """Reverse read only needed tail; retain complete disk evidence."""
        limit=max(1,min(limit,500)); p=self.path(id)/'events.jsonl'
        if not p.exists(): return {'events':[],'has_more':False,'next_before':None}
        if p.is_symlink(): raise ConsoleError('事件链接被拒绝',403)
        rows=[]; buffered=b''; more=False; byte_count=0
        with p.open('rb') as f:
            pos=f.seek(0,2)
            while pos>0:
                length=min(65536,pos);pos-=length;f.seek(pos)
                pieces=(f.read(length)+buffered).split(b'\n');buffered=pieces.pop(0)
                if pos==0: pieces.insert(0,buffered);buffered=b''
                for line in reversed(pieces):
                    if not line: continue
                    try: event=json.loads(line)
                    except ValueError: continue # incomplete crash tail retained on disk
                    if before is not None and event['id']>=before: continue
                    if len(rows)>=limit or byte_count>512*1024: more=True;break
                    event['message']=event.get('message','')[:12000]
                    # Structured RPC data may be large; full original remains on disk.
                    if len(json.dumps(event.get('data',{})))>12000: event['data']={'summary':'大事件数据保存在完整磁盘日志'}
                    byte_count+=len(json.dumps(event,ensure_ascii=False).encode('utf8'));rows.append(event)
                if more:break
        rows.reverse()
        return {'events':rows,'has_more':more,'next_before':rows[0]['id'] if more and rows else None}
