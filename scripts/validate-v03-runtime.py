from pathlib import Path
import httpx,json,time,hashlib
r=Path.cwd();out=r/'docs/web-validation-v0.3'
c=httpx.Client(base_url='http://127.0.0.1:8765',timeout=30)
for _ in range(30):
 if c.get('/api/health').json().get('codex'):break
 time.sleep(1)
c.headers['X-Novel-Request']=c.get('/api/session').json()['request_token']
rows=c.get('/api/projects').json()['projects'];a=next(p for p in rows if p['title']=='Fixture Novel A');b=next(p for p in rows if p['title']=='Fixture Novel')
def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
def run(prompt):
 p=c.post('/api/projects/'+a['project_id']+'/tasks',json={'type':'custom_prompt','prompt':prompt,'options':{'read_only':True,'resume':False}});p.raise_for_status();return p.json()
def await_task(task):
 for _ in range(240):
  t=c.get('/api/projects/'+a['project_id']+'/tasks/'+task['id']).json()
  if t['status'] in ['SUCCEEDED','FAILED','CANCELLED']:return t
  time.sleep(1)
 raise RuntimeError('test timeout')
# Restore external conflict fixture to the pre-conflict world before extra tests.
f=json.loads((out/'test-f-external-change.json').read_text(encoding='utf8'))
print('conflict evidence keys',list(f),flush=True)
bpath='/api/projects/'+b['project_id']+'/files/content';world=c.get(bpath,params={'path':'bible/world.md'}).json()
if 'EXTERNAL_FIXTURE_CHANGE' in world['content']:
 orig=f['before']['content']
 c.put(bpath,json={'path':'bible/world.md','content':orig,'etag':world['etag']}).raise_for_status()
def snapshot(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
before=snapshot(r/'projects'/b['project_id'])
t=await_task(run('只读本项目 project.yaml 和 state/current-story-state.yaml，报告当前 project ID、标题和章号。使用普通沙箱读取，禁止读取其他小说或 engine 根目录旧小说。不要写文件。'))
assert t['status']=='SUCCEEDED',t
logs=c.get('/api/projects/'+a['project_id']+'/tasks/'+t['id']+'/log').json()
assert before==snapshot(r/'projects'/b['project_id'])
save('test-e-api-project-task.json',{'project_a':a['project_id'],'project_b':b['project_id'],'task':t,'events':logs,'b_files_unchanged':True})
print('A readonly task',t['id'],t['status'],flush=True)
t=run('这是 disposable fixture 的取消验收。只用普通沙箱执行 Start-Sleep -Seconds 30，随后返回 WAIT_COMPLETED。不读取其他项目，不写文件，不申请额外权限。')
for _ in range(120):
 row=c.get('/api/projects/'+a['project_id']+'/tasks/'+t['id']).json();logs=c.get('/api/projects/'+a['project_id']+'/tasks/'+t['id']+'/log').json()
 if row.get('turn_id') and any(e['type']=='tool_call' for e in logs):break
 if row['status'] in ['FAILED','SUCCEEDED','CANCELLED']:raise RuntimeError(row)
 time.sleep(1)
assert row.get('turn_id')
c.post('/api/projects/'+a['project_id']+'/tasks/'+t['id']+'/cancel',json={}).raise_for_status()
final=await_task(t);assert final['status']=='CANCELLED',final
save('regression-active-turn-cancel.json',{'before_cancel':row,'final':final,'events':c.get('/api/projects/'+a['project_id']+'/tasks/'+t['id']+'/log').json()})
print('Real Turn cancel',final['turn_id'],final['status'],flush=True)
