"""Explicit isolated UI fixture; never opens the real data directory."""
from pathlib import Path
import argparse,json,os,shutil,sys
R=Path(__file__).resolve().parents[3]
a=argparse.ArgumentParser();a.add_argument('--fixture',type=Path,required=True);a.add_argument('--port',type=int,default=8945);args=a.parse_args();D=args.fixture.resolve()
if not D.is_relative_to(R/'desktop/build') or D==R/'desktop/build' or D.is_symlink():raise SystemExit('Use a dedicated owned desktop/build directory')
if not 1024<=args.port<=65535:raise SystemExit('Unprivileged loopback port required')
D.mkdir(parents=True,exist_ok=True);W=D/'workspace'
if not W.exists():shutil.copytree(R/'desktop/preview-template',W)
if W.is_symlink() or W.is_junction():raise SystemExit('Unsafe fixture workspace')
os.environ.update(NOVEL_WORKSPACE=str(W),NOVEL_STUDIO_HOME=str(D/'home'),NOVEL_STUDIO_DATA=str(D/'data/workspaces'),CODEX_HOME=str(D/'empty-codex'),NOVEL_DEMO='1')
sys.path.insert(0,str(R/'web/backend'));sys.path.insert(0,str(R/'scripts'))
from app.main import create_app
from app.config import Settings
app=create_app(Settings(workspace=W,port=args.port,static_dir=R/'web/frontend/dist'))
p=next((W/'projects').glob('novel_*')).name
(D/'fixture.json').write_text(json.dumps({'project':p,'url':'http://127.0.0.1:'+str(args.port),'real_data_used':False}),'utf8')
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=args.port,log_level='warning')
