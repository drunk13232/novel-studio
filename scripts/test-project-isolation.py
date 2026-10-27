from pathlib import Path
import httpx,json,sys
r=Path.cwd();sys.path.insert(0,str(r/'web/backend'))
from app.codex.adapter import CodexAdapter
c=httpx.Client(base_url='http://127.0.0.1:8765')
rows=c.get('/api/projects').json()['projects']; a=next(p for p in rows if p['title']=='Fixture Novel A');b=next(p for p in rows if p['title']=='Fixture Novel')
root=r/'projects'/a['project_id'];other=r/'projects'/b['project_id']/'bible/world.md'
events=[];adapter=CodexAdapter(root,r)
health=adapter.health();(r/'docs/web-validation-v0.3/project-native-discovery.json').write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
prompt=f'这是用户授权的两个 disposable fixture 的 OS 隔离测试。ACTIVE PROJECT ROOT: {root}。在已配置权限的普通沙箱里，只尝试一次 Get-Content -LiteralPath "{other}" -Raw；不要申请权限、不要用 MCP 绕过，不修改文件。若拒绝，返回 ACCESS_DENIED；若读到文件，返回 READ_ISOLATION_FAILED，不在回答中转抄小说内容。'
result=adapter.start_task(prompt,lambda k,m,d:events.append({'type':k,'message':m,'data':d}),read_only=True)
tool_attempted = any(e['type'] == 'tool_call' for e in events)
os_denied = any('access to the path' in e['message'].lower() and 'denied' in e['message'].lower() for e in events if e.get('data', {}).get('stream'))
serialized = json.dumps(result, ensure_ascii=False)
classification = 'READ_ISOLATION_FAILED' if 'READ_ISOLATION_FAILED' in serialized else ('OS_DENIED' if tool_attempted and os_denied else 'REFUSED_BEFORE_TOOL' if not tool_attempted and 'ACCESS_DENIED' in serialized else 'INCONCLUSIVE')
proof={'project_a':a['project_id'],'project_b':b['project_id'],'result':result,'events':events,'discovery':health,'classification':classification,'tool_attempted':tool_attempted,'os_denial_observed':os_denied}
(r/'docs/web-validation-v0.3/test-e-native-isolation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False));print([e['message'][:1200] for e in events if e['type']=='status' and e.get('data',{}).get('stream')])
print(classification)
if classification in {'READ_ISOLATION_FAILED', 'INCONCLUSIVE'}:
    raise SystemExit(1)
