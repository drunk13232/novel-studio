"""Package only the allowlisted PyInstaller output; never traverse the workspace."""
from pathlib import Path
import argparse
import hashlib
import zipfile
import json
import shutil

project=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--release-root',default=str(project/('release/v'+json.loads((project/'desktop/version.json').read_text('utf8'))['version'])))
parser.add_argument('--preview',action='store_true');parser.add_argument('--output-name',default=None,help='New candidate ZIP filename, preserving previous candidates');args=parser.parse_args()
root=Path(args.release_root).resolve()
assert root.is_relative_to((project/'release').resolve())
source=root/'NovelStudio'
assert (source/'NovelStudio.exe').is_file()
import sys
sys.path.insert(0,str(project/'web/backend'))
from app.companion import assert_public_resources
from app.live2d import assert_public_live2d
assert_public_resources(project/'web/frontend/public/companion')
assert_public_live2d(project/'web/frontend/public/live2d')
assert_public_resources(source/'_internal/resources/frontend/companion')
assert_public_live2d(source/'_internal/resources/frontend/live2d')
# Only our four curated UTF-8 guides; never copy project AGENTS or runtime files.
guide_root=project/'desktop/developer-guide'
for name in ('AGENTS.md','AI-DEVELOPMENT.md','ARCHITECTURE.md','DEVELOPMENT.md'):
    origin=guide_root/name
    destination=source/name
    assert origin.is_file() and not origin.is_symlink() and origin.resolve().is_relative_to(guide_root.resolve())
    assert origin.stat().st_size<=128*1024
    origin.read_text(encoding='utf8')
    assert not destination.is_symlink() and destination.resolve().is_relative_to(source.resolve())
    shutil.copyfile(origin,destination)
forbidden={'node_modules','.git','.codex','.agents','projects','chapters','state','canon',
           '.pytest_cache','__pycache__','auth.json','.env','reference-library','.research','reference-runs','reference-tasks'}
paths=sorted(p for p in source.rglob('*') if p.is_file() and p.relative_to(source).as_posix()!='RELEASE-MANIFEST.json')
demo=source/'_internal/resources/demo-workspace'
demo_files=json.loads((demo/'demo-manifest.json').read_text(encoding='utf8'))['files'] if (demo/'demo-manifest.json').is_file() else {}
for p in paths:
    assert not p.is_symlink() and p.resolve().is_relative_to(source.resolve())
    if demo_files and p.is_relative_to(demo):
        name=p.relative_to(demo).as_posix()
        assert name=='demo-manifest.json' or (name in demo_files and hashlib.sha256(p.read_bytes()).hexdigest()==demo_files[name]),p
        assert not {'.codex','auth.json','.env'}.intersection(p.relative_to(demo).parts),p
    else:assert not forbidden.intersection(p.relative_to(source).parts),p
    assert not p.name.endswith(('.pyc','.log')),p
release=json.loads((project/'desktop/version.json').read_text('utf8'))
manifest={'release':release,'files':{p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
(source/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
paths=sorted(p for p in source.rglob('*') if p.is_file())
filename=args.output_name or ('NovelStudio-Windows-Preview.zip' if args.preview else 'NovelStudio-Windows.zip')
if Path(filename).name!=filename or not filename.endswith('.zip') or '\\' in filename or ':' in filename:raise SystemExit('Unsafe ZIP filename')
target=root/filename
if args.output_name and target.exists():raise SystemExit('Named candidate already exists; previous candidates are preserved')
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in paths:z.write(p,Path('NovelStudio')/p.relative_to(source))
with zipfile.ZipFile(target) as z:assert z.testzip() is None
print('ZIP:',target,'files:',len(paths),'bytes:',target.stat().st_size)
print('EXE SHA256:',hashlib.sha256((source/'NovelStudio.exe').read_bytes()).hexdigest())
