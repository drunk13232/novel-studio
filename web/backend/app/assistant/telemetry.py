"""Small request timeline; monotonic durations and no prompt/tool parameters."""
import time,uuid
from app.library.storage import now,read
from app.tasks.storage import atomic_json
class Timeline:
    def __init__(self,session,request_id=None,client_ms=0):
        self.session=session;self.id=request_id or uuid.uuid4().hex;self.started=time.monotonic();self.events=[];self.finished=None
        self.mark('backend_received','正在准备',client_ms=round(client_ms,1))
    def mark(self,event,status='ok',**values):
        row={'event':event,'elapsed_ms':round((time.monotonic()-self.started)*1000,1),'status':status}
        if event=='request_complete':self.finished=time.monotonic()
        if event=='confirmation_approved':self.finished=None
        row.update({k:v for k,v in values.items() if k in {'duration_ms','client_ms','reused','tool','code'}})
        with self.session.cv:self.events.append(row)
        return row
    def view(self):return {'request_id':self.id,'elapsed_ms':round(((self.finished or time.monotonic())-self.started)*1000,1),'events':list(self.events)}
    def save(self):
        s=self.session
        with s.center.lock:
            path=s.center.root/'assistant-timings.json'
            rows=read(path,[]);rows=[r for r in rows if r.get('request_id')!=self.id]
            atomic_json(path,[{'request_id':self.id,'session':s.id[:12],'project':(s.project or '')[-12:],'at':now(),'events':self.events},*rows][:500])
