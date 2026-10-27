from pathlib import Path
import sys,json
sys.path.insert(0,str(Path('web/backend').resolve()))
from app.codex.adapter import CodexAdapter
from app.projects.service import DraftStore
from app.projects.models import Idea
r=Path.cwd(); ds=DraftStore(r); d=ds.create(Idea(title='Fixture Discovery',premise='A discovers B.'))
a=CodexAdapter(ds.path(d['id']),r)
health=a.health(); (r/'docs/web-validation-v0.3/native-discovery.json').write_text(json.dumps(health,ensure_ascii=False,indent=2),encoding='utf8')
events=[]
res=a.start_task('只返回 ISOLATION_PROFILE_READY，不执行工具，不写任何文件。',lambda k,m,data:events.append({'type':k,'message':m,'data':data}),read_only=True)
(r/'docs/web-validation-v0.3/profile-probe.json').write_text(json.dumps({'draft_id':d['id'],'result':res,'events':events},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'discovery':health,'result':res},ensure_ascii=False))
