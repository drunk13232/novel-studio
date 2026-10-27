# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata, collect_all

root=Path(SPECPATH).parent
import sys
sys.path.insert(0,str(root/'web/backend'))
from app.companion import assert_public_resources
from app.live2d import assert_public_live2d
assert_public_resources(root/'web/frontend/public/companion')
assert_public_live2d(root/'web/frontend/public/live2d')
assert_public_resources(root/'web/frontend/dist/companion')
assert_public_live2d(root/'web/frontend/dist/live2d')
data=[(str(root/'web/frontend/dist'),'resources/frontend'),(str(root/'desktop/third-party'),'resources/third-party'),(str(root/'desktop/version.json'),'resources'),(str(root/'desktop/preview-template'),'resources/demo-workspace')]
import os,ssl
# Vendor CPython may load this public CA rejection policy in SSLContext.__new__.
# Keep its original bytes; do not disable TLS verification or its distrust rule.
ssl_policy=Path(ssl.__file__).with_name('codex-rejected-cas.pem')
if ssl_policy.is_file():data.append((str(ssl_policy),'.'))
from app.creative.director_skills import METHODS
for key,(_,relative) in METHODS.items():
    if key=='research':continue  # Installed optional research methods are not redistributed.
    data.append((str(root/relative),'resources/creative-methods/'+key))
solver_datas,solver_binaries,solver_hidden=collect_all('z3')
pint_datas,pint_binaries,pint_hidden=collect_all('pint')
ortools_datas,ortools_binaries,ortools_hidden=collect_all('ortools')
jieba_datas,jieba_binaries,jieba_hidden=collect_all('jieba')
wasm_datas,wasm_binaries,wasm_hidden=collect_all('wasmtime')
data+=jieba_datas+wasm_datas+copy_metadata('wasmtime')+[(str(root/'web/backend/app/automation/runtime'),'app/automation/runtime'),*[(str(f),'resources/python/'+str(f.parent.relative_to(root/'python'))) for f in (root/'python').rglob('*') if f.is_file() and f.suffix in {'.py','.typed'} and '__pycache__' not in f.parts]]
data+=solver_datas+pint_datas+ortools_datas+[(str(root/'web/backend/app/world_logic/resources'),'app/world_logic/resources')]
if os.environ.get('NOVEL_PREVIEW_BUILD')=='1':
    data += [(str(root/'desktop/preview.txt'),'resources')]
for dependency in ['jieba','openai-codex','pypdf','python-docx','charset-normalizer','python-multipart','lxml','comtypes','openai','keyring','httpx2','httpcore2','mcp','mcp-types','z3-solver','networkx','sympy','pint','jsonschema','mpmath','flexcache','flexparser','platformdirs','ortools','numpy','pandas','protobuf','absl-py','immutabledict','python-dateutil','six','tzdata']:
    data+=copy_metadata(dependency)
a=Analysis([str(root/'desktop/launcher.py')],pathex=[str(root/'web/backend')],
           binaries=solver_binaries+pint_binaries+ortools_binaries+wasm_binaries,datas=data,
           hiddenimports=jieba_hidden+solver_hidden+pint_hidden+ortools_hidden+wasm_hidden+['app.automation.worker','app.assistant.mcp_server','win32job','app.world_logic.worker','keyring.backends.Windows','win32ctypes.pywin32.win32cred']+collect_submodules('openai')+collect_submodules('httpx2')+collect_submodules('httpcore2')+collect_submodules('uvicorn')+collect_submodules('openai_codex')+collect_submodules('pypdf')+collect_submodules('docx')+collect_submodules('charset_normalizer')+collect_submodules('mcp',filter=lambda name:not name.startswith('mcp.cli'))+collect_submodules('mcp_types')+collect_submodules('comtypes',filter=lambda name:'.test' not in name),
           hookspath=[],runtime_hooks=[],excludes=['pytest','_pytest'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='NovelStudio',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False,
        contents_directory='_internal')
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='NovelStudio')
