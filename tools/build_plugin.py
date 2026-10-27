"""Build a local Novel Studio plugin using the same validator as the app.
Usage: python tools/build_plugin.py <plugin-folder> <new-output.zip>
"""
import hashlib,io,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'web/backend'))
from app.extensions.service import PluginHub,safe_name,MAX_TOTAL,MAX_ZIP

def build(source,target):
    source=Path(source).resolve();target=Path(target).resolve()
    if target.exists():raise SystemExit('Output already exists; choose a new filename')
    if target.is_relative_to(source):raise SystemExit('Place the ZIP outside the source folder')
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8-sig'))
    data={}
    for path in sorted(source.rglob('*')):
        if path.is_dir():continue
        if path.is_symlink() or not path.resolve().is_relative_to(source):raise SystemExit('Links are not supported')
        name=path.relative_to(source).as_posix();safe_name(name)
        if name!='manifest.json':data[name]=path.read_bytes()
    manifest['files']={name:hashlib.sha256(content).hexdigest() for name,content in data.items()}
    data['manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
    PluginHub.validate(manifest,data)
    if sum(map(len,data.values()))>MAX_TOTAL:raise SystemExit('Uncompressed package too large')
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in data.items():z.writestr(name,content)
    raw=out.getvalue()
    if len(raw)>MAX_ZIP:raise SystemExit('Compressed package too large')
    # Exercise the complete upload validator without creating an app or user files.
    PluginHub.parse(PluginHub.__new__(PluginHub),raw)
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    print(json.dumps({'file':str(target),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}))
if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit(__doc__)
    build(sys.argv[1],sys.argv[2])
