"""Curated developer source archive; never package a live novel workspace."""
from pathlib import Path
import argparse,hashlib,json,re,zipfile
root=Path(__file__).resolve().parents[1]
version=json.loads((root/'desktop/version.json').read_text('utf8'))
parser=argparse.ArgumentParser()
parser.add_argument('--release-root',default=str(root/('release/v'+version['version'])))
args=parser.parse_args();destination=Path(args.release_root).resolve()
if not destination.is_relative_to(root/'release'):raise RuntimeError('Source output must stay in release')
destination.mkdir(parents=True,exist_ok=True)
target=destination/'NovelStudio-Developer.zip'
if target.exists():raise RuntimeError('Developer package exists; keep the previous archive')
import sys
sys.path.insert(0,str(root/'web/backend'))
from app.companion import assert_public_resources
from app.live2d import assert_public_live2d
assert_public_resources(root/'web/frontend/public/companion')
assert_public_live2d(root/'web/frontend/public/live2d')
files={}
OFFLINE_TYPING_SOUND='web/frontend/public/sounds/typewriter-soft.wav'
excluded={'.git','.codex','.venv','node_modules','__pycache__','.pytest_cache','dist','build','runtime','logs','source-backup','private-checks','private-assets'}
allowed_suffix={'.py','.ps1','.tsx','.ts','.css','.json','.md','.txt','.html','.mjs','.js','.yaml','.yml','.toml','.svg','.spec','.nsi','.map','.bcmap','.wasm','.ttf','.pfb'}
sensitive=re.compile(r'(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?i:api[_-]?key|access[_-]?token)\s*[:=]\s*["\'][A-Za-z0-9_-]{30,}["\']')
def add(path,archive=None,upstream=False):
    path=root/path if isinstance(path,str) else path
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):raise RuntimeError('Unsafe source path')
    name=archive or path.relative_to(root).as_posix()
    if path.stat().st_size>16*1024*1024 and not (upstream and path.name=='python.wasm' and path.stat().st_size<40*1024*1024):raise RuntimeError('Unexpected large source file: '+name)
    content=path.read_bytes()
    binary=path.relative_to(root).as_posix()==OFFLINE_TYPING_SOUND or (path.is_relative_to(root/'web/frontend/src/assets/study') and path.suffix=='.webp') or (path.is_relative_to(root/'web/frontend/public/themes') and path.suffix=='.webp') or (path.is_relative_to(root/'docs/visual-renaissance/art-source') and path.suffix=='.png') or (path.is_relative_to(root/'desktop/third-party/font-source') and path.suffix=='.gz') or path.suffix in {'.wasm','.bcmap','.ttf','.pfb'} or (path.is_relative_to(root/'desktop/preview-template') and path.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.pdf','.docx'})
    if not binary:
        try:text=content.decode('utf8')
        except UnicodeDecodeError:raise RuntimeError('Non UTF-8 source: '+name)
        if sensitive.search(text) or (re.search(r'novel_[a-f0-9]{32}',text) and not path.is_relative_to(root/'desktop/preview-template')):raise RuntimeError('Private content marker in source: '+name)
        if not upstream and re.search(r'[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+',text):raise RuntimeError('Personal path in source: '+name)
    files[name]=content
def tree(base):
    base=root/base
    for p in sorted(base.rglob('*')):
        if not p.is_file():continue
        if excluded.intersection(p.relative_to(base).parts) or p.suffix=='.pyc' or p.name.endswith(('.log','.tsbuildinfo')):continue
        if p.suffix in allowed_suffix or p.name.startswith(('LICENSE','NOTICE')) or p.name in {'.gitkeep','.gitignore','.cursorrules'}:add(p)
for base in ('web/frontend/src','web/frontend/public','web/frontend/scripts','web/backend/app','engine/templates','templates','engine/genres','schemas','.agents/skills','.novelforge','desktop/developer-guide','desktop/third-party','python'):tree(base)
# Only the explicit, hash-checked original 2.12.2 art set is redistributed.
art_base=root/'web/frontend/src/assets/study'
art_manifest=json.loads((art_base/'manifest.json').read_text('utf8'))
for asset in art_manifest['assets']:
    art=art_base/asset['file']
    if not art.resolve().is_relative_to(art_base.resolve()) or hashlib.sha256(art.read_bytes()).hexdigest()!=asset['sha256']:raise RuntimeError('Visual asset manifest mismatch')
    if art.suffix=='.webp':add(art)
theme_base=root/'web/frontend/public/themes'
theme_manifest=json.loads((theme_base/'manifest.json').read_text('utf8'))
for asset in theme_manifest['assets']:
    art=theme_base/asset['file']
    if not art.resolve().is_relative_to(theme_base.resolve()) or hashlib.sha256(art.read_bytes()).hexdigest()!=asset['sha256']:raise RuntimeError('Theme art manifest mismatch')
    if art.suffix=='.webp':add(art)
    if asset.get('source_sha256'):
        original=root/asset['source']
        if not original.resolve().is_relative_to((root/'docs/visual-renaissance/art-source').resolve()) or hashlib.sha256(original.read_bytes()).hexdigest()!=asset['source_sha256']:raise RuntimeError('Theme original art mismatch')
        add(original)
# One original offline sound; do not broadly admit private audio assets.
sound_manifest=json.loads((root/'web/frontend/public/sounds/manifest.json').read_text('utf8'))
sound= root/OFFLINE_TYPING_SOUND
entry=sound_manifest['assets'][0]
blob=sound.read_bytes()
if entry['file']!='typewriter-soft.wav' or len(blob)>4096 or blob[:4]!=b'RIFF' or blob[8:12]!=b'WAVE' or hashlib.sha256(blob).hexdigest()!=entry['sha256']:raise RuntimeError('Offline typing sound manifest mismatch')
add(OFFLINE_TYPING_SOUND)
for name in ('AGENTS.md','install-web.ps1','start-web.ps1','stop-web.ps1','web/frontend/package.json','web/frontend/package-lock.json','web/frontend/index.html','web/frontend/tsconfig.json','web/frontend/vite.config.ts','web/backend/requirements.txt','desktop/requirements.txt','desktop/launcher.py','desktop/NovelStudio.spec','desktop/build.ps1','desktop/package_zip.py','desktop/package_source.py','desktop/collect_licenses.py','desktop/version.json','desktop/README.txt','desktop/PREVIEW-DEMO-GUIDE.md','desktop/preview.txt','desktop/data-location.public.json','scripts/model.py','scripts/yaml_io.py','scripts/knowledge_isolation.py','scripts/novel_workflow.py','scripts/novel.ps1'):add(name)
demo=root/'desktop/preview-template';demo_manifest=json.loads((demo/'demo-manifest.json').read_text('utf8'))
for name,expected in demo_manifest['files'].items():
    p=demo/name
    if not p.resolve().is_relative_to(demo.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:raise RuntimeError('Public demo changed: '+name)
    add(p)
add(demo/'demo-manifest.json')
add('desktop/data-location.public.json','desktop/data-location.json')
add('web/backend/tests/test_world_logic.py')
add('web/backend/tests/test_creative_boundaries.py')
add('web/backend/tests/test_writing_assist.py')
add('web/backend/tests/test_candidate_drafts.py')
add('web/backend/tests/test_candidate_line_endings.py')
add('web/backend/tests/test_mcp_chapter_drafts.py')
add('docs/ai-writing/README.md')
add('web/backend/tests/test_autonomous_workflows.py')
add('docs/autonomous-enhancement/README.md')
add('web/backend/tests/test_codex_preflight.py')
font_source=root/'desktop/third-party/font-source/liberation-fonts-1.07.4.tar.gz'
if hashlib.sha256(font_source.read_bytes()).hexdigest()!='ad98b7498dc2992f7f0868f79b65ce4a720a3acdb63ab3f1f1cb6881117a5406':raise RuntimeError('Font source integrity mismatch')
add(font_source)
add('docs/daily-reliability/README.md')
for guide in ['README.md','README_EN.md','INSTALL.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','THIRD_PARTY_NOTICES.md','docs/DEVELOPMENT.md','docs/WINDOWS-BUILD.md','docs/daily-reliability/DELIVERY.md']:add(guide)
add('web/backend/tests/test_creative_director.py')
add('web/backend/tests/test_director_console.py')
add('web/backend/tests/test_director_freedom.py')
add('web/backend/tests/test_director_reliability.py')
add('web/backend/tests/test_director_review_basis.py')
add('web/backend/tests/test_codex_probe_concurrency.py')
add('docs/creative-director/DELIVERY-2.24.2.md')
add('docs/creative-director/DELIVERY-2.24.1.md')
add('docs/creative-director/README.md')
add('docs/ai-writing-quality/README.md')
add('scripts/writing_quality_experiment.py')
add('scripts/long_form_fixture.py')
add('docs/long-form/README.md')
add('web/backend/tests/test_long_form.py')
add('web/backend/tests/test_world_studio.py')
add('docs/worldbuilding-studio/README.md')
add('docs/worldbuilding-studio/TEMPLATE-FORMAT.md')
add('docs/worldbuilding-studio/TECHNICAL-SELECTION.md')
add('docs/worldbuilding-studio/PUBLIC-REVIEW.json')
add('docs/ai-controls/README.md')
add('docs/experience-optimization/README.md')
for name in ('README.md','TECHNICAL-DECISIONS.md','ASSETS.md','generation.json','PUBLIC-REVIEW.json'):add('docs/visual-renaissance/'+name)
for name in ('README.md','PUBLIC-REVIEW.json'):add('docs/product-evolution/'+name)
for name in ('README.md','PUBLIC-REVIEW.json'):add('docs/soft-ui/'+name)
for name in ('README.md','PUBLIC-REVIEW.json'):add('docs/interaction-freedom/'+name)
add('web/backend/tests/test_interaction_freedom.py')
add('web/backend/tests/test_python_control.py')
add('python/novel_studio_api/py.typed')
add('desktop/fetch_python_runtime.py')
for name in ('README.md','manifest.schema.json'):add('docs/plugin-hub/'+name)
tree('docs/plugin-hub/examples')
add('tools/build_plugin.py')
add('docs/ui-polish/README.md')
add('docs/art-refinement/README.md')
add('docs/model-control/README.md')
add('docs/writing-dashboard/README.md')
add('docs/daily-writing-tools/README.md')
for name in ('README.md','DELIVERY.md','HARDENING.md','ANNUAL-RITUAL-PRINT.md','CHAPTER-VERSIONS.md'):add('docs/creative-tools/'+name)
add('docs/creative-insights/README.md')
add('docs/creative-insights/DELIVERY-2.22.2.md')
add('web/backend/tests/test_creative_insights_backup.py')
add('docs/creative-insights/HARDENING-20261025.md')
add('scripts/sample-narrative-curves.py')
for name in ('test_creative_maps_audio.py','test_creative_insights.py','test_chapter_versions.py','test_writing_annual_ritual.py','test_print_preview.py'):add('web/backend/tests/'+name)

add('docs/daily-writing-tools/USABILITY-REPORT.md')
add('docs/daily-writing-tools/FINAL-ROUND-REPORT.md')
add('docs/writing-tools/global-replacement.md')
add('THIRD_PARTY_NOTICES.md')
for legal in ('LICENSE','NOTICE','COPYRIGHT'):add(legal)
add('.gitattributes')
# Reuse the owner's previously reviewed public-only fixture, without editing
# the private development original. Hashes freeze that specific decision.
public_fixture=root/'docs/oss/public-overrides/test_global_replace.py'
if hashlib.sha256(public_fixture.read_bytes()).hexdigest()!='6b44df79e034f84a1e0c183259a33250a59a03627a579c210aebce8c093618c8':raise RuntimeError('Reviewed public fixture changed; review before redistribution')
original_fixture=root/'web/backend/tests/test_global_replace.py'
if hashlib.sha256(original_fixture.read_bytes()).hexdigest() not in {'a88f774539443fdd661b174c654d0ca80fdd60499111479460afc4462da4b866','6b44df79e034f84a1e0c183259a33250a59a03627a579c210aebce8c093618c8'}:raise RuntimeError('Test changed after public fixture review')
add(public_fixture)
add(public_fixture,archive='web/backend/tests/test_global_replace.py')
public_ui_fixture=root/'docs/oss/public-overrides/check-global-replace.mjs'
if hashlib.sha256(public_ui_fixture.read_bytes()).hexdigest()!='35761656fbd1c44955caca1fae0563cbf9a57a64bc2c4d7f2c851e35ca57aed7':raise RuntimeError('Reviewed public UI fixture changed; review before redistribution')
if hashlib.sha256((root/'web/frontend/scripts/check-global-replace.mjs').read_bytes()).hexdigest() not in {'43455c2ceaab5e19fcae9e729de9f9f01ea59a262e1bf3a6484c1a827cf0d98a','35761656fbd1c44955caca1fae0563cbf9a57a64bc2c4d7f2c851e35ca57aed7'}:raise RuntimeError('UI test changed after public fixture review')
add(public_ui_fixture)
add(public_ui_fixture,archive='web/frontend/scripts/check-global-replace.mjs')
for name in ('test_focus_summary.py','test_clue_board.py','test_daily_writing_tools_api.py'):add('web/backend/tests/'+name)
add('web/backend/tests/test_writing_dashboard.py')
add('web/backend/tests/test_writing_dashboard_api.py')
add('web/backend/tests/test_desktop_readiness.py')
add('web/backend/tests/test_desktop_exit.py')
add('web/backend/tests/test_plugin_hub.py')
for name in ('README.md','PYTHON-API.md','ACTION-API.md','ACTION-CATALOG.json','TECHNICAL-DECISIONS.md','RUNTIME-LOCK.json','PUBLIC-REVIEW.json'):add('docs/character-control/'+name)
add('web/backend/tests/test_appearance.py')
add('docs/ai-controls/TECHNICAL-SELECTION.md')
add('docs/ai-controls/PUBLIC-REVIEW.json')
add('web/backend/tests/test_ai_controls.py')
add('docs/world-model/README.md')
add('docs/world-model/RULES-AND-EVIDENCE.md')
add('docs/world-model/PUBLIC-REVIEW.json')
add('web/backend/tests/test_world_model.py')
add('web/backend/tests/test_creative_spaces.py')
add('docs/creative-workspace/README.md')
add('web/backend/tests/test_professional_writing.py')
add('docs/professional-writing/README.md')
add('web/backend/tests/test_writing_quality.py')
add('web/backend/tests/fixtures/writing-quality-gold.json')
add('docs/writing-quality/README.md')
add('docs/writing-quality/TECHNICAL-SELECTION.md')
add('web/backend/tests/test_lightweight.py')
add('docs/lightweight/README.md')
add('docs/visual-upgrade/README.md')
add('docs/visual-upgrade/PORTRAITS.md')
add('web/backend/tests/test_companion.py')
add('web/backend/tests/test_live2d.py')
add('web/backend/tests/test_embodied_assistant.py')
add('web/backend/tests/test_assistant_daily_use.py')
add('docs/live2d/DAILY-STABILITY.md')
add('docs/live2d/README.md')
add('docs/live2d/TECHNICAL-SELECTION.md')
add('docs/live2d/DYNAMIC-COMPANION.md')
add('docs/input-focus/README.md')
for name in ('README.md','TECHNICAL-DECISIONS.md','AI-SAFETY.md','UPGRADE-REPORT.md','character-card.example.json'):add('docs/goal-upgrade/'+name)
add('desktop/native_i18n.py')
add('web/frontend/i18next.config.ts')
for name in ('docs/i18n/TRANSLATING.md','docs/i18n/TERMINOLOGY.md','docs/i18n/TECHNICAL-SELECTION.md','docs/i18n/LANGUAGE-STATUS.md'):add(name)
for name in ('docs/world-logic/README.md', 'docs/world-logic/EXPERIMENT-FORMAT.md', 'docs/world-logic/RULE-SPECIFICATION.md', 'docs/world-logic/ACCEPTANCE-GUIDE.md', 'docs/world-logic/SOLVER-ADAPTER-GUIDE.md', 'docs/world-logic/TEMPLATE-AUTHORING.md', 'docs/world-logic/SECURITY-MODEL.md', 'docs/world-logic/VERSIONING.md', 'docs/world-logic/TECHNICAL-SELECTION.md', 'docs/world-logic/examples/adapter.json', 'docs/world-logic/examples/custom-constraint.json', 'docs/world-logic/examples/event-order.json', 'docs/world-logic/examples/event-order.yaml', 'docs/world-logic/examples/minimal-report.json', 'docs/world-logic/examples/physics-units.json', 'docs/world-logic/examples/resources.json', 'docs/world-logic/examples/travel.json'):add(name)
# Verified upstream CPython examples are retained byte-for-byte, not local identities.
runtime=root/'web/backend/app/automation/runtime'
lock=json.loads((root/'docs/character-control/RUNTIME-LOCK.json').read_text('utf8'))
for name,expected in lock['files'].items():
    source=runtime/name
    if not source.resolve().is_relative_to(runtime.resolve()) or hashlib.sha256(source.read_bytes()).hexdigest()!=expected:raise RuntimeError('Pinned runtime source mismatch')
    add(source,upstream=True)
add('docs/character-control/RUNTIME-LOCK.json')
font_source=root/'desktop/third-party/font-source/liberation-fonts-1.07.4.tar.gz'
if hashlib.sha256(font_source.read_bytes()).hexdigest()!='ad98b7498dc2992f7f0868f79b65ce4a720a3acdb63ab3f1f1cb6881117a5406':raise RuntimeError('Font source integrity mismatch')
add(font_source)
add('docs/daily-reliability/README.md')
for guide in ['README.md','README_EN.md','INSTALL.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','THIRD_PARTY_NOTICES.md','docs/DEVELOPMENT.md','docs/WINDOWS-BUILD.md','docs/daily-reliability/DELIVERY.md']:add(guide)
for guide in ('README.md','DELIVERY.md','world-first.example.json'):add('docs/custom-workflows/'+guide)
add('web/backend/tests/test_custom_workflows.py')
add('web/backend/tests/test_workflow_backup.py')
add('web/backend/tests/test_creative_maps_audio.py')
add('docs/world-first/README.md')
add('docs/world-first/DELIVERY.md')
add('web/backend/tests/test_world_first.py')
add('web/backend/tests/test_projects.py')
add('desktop/installer.nsi')
add('desktop/build_installer.py')
add('desktop/INSTALLER.md')
add('licenses/installer/NSIS-3.13.txt')
add('web/backend/tests/test_planning_center.py')
add('web/backend/tests/test_cache_maintenance.py')
readme="""# Novel Studio Developer Source
对应版本："""+version['version']+"""
此包是白名单源码，不含用户 projects、Canon、State、文献、图片、备份、凭据或运行历史。
桌面公开演示模板中的示例 State/章节仅属于原创演示。
先读 desktop/developer-guide/AI-DEVELOPMENT.md、ARCHITECTURE.md、DEVELOPMENT.md。
源码根 AGENTS.md 保留项目知识隔离与作品保护规则。
安装与启动前由用户指定源码、个人数据、作品与隔离开发目录。
原创软件按根 LICENSE 的 Apache-2.0 授权；版权署名 drunk13232。第三方组件和用户作品保持各自权利。
其他用户级 Plugins、Codex 登录、Story CLI、ComfyUI 不包含在此包；缺少时如实显示未配置。
不要对真实作品运行测试；当前版本的检查范围与限制见发行说明。
"""
files['SOURCE-README.md']=readme.encode()
files['projects/.gitkeep']=b''
add('web/backend/tests/test_workflow_reliability.py')
add('docs/workflow-reliability/README.md')
add('web/backend/tests/test_core_reliability.py')
add('docs/core-reliability/README.md')
add('web/backend/tests/test_literary_core.py')
add('web/backend/tests/test_literary_evaluation.py')
add('docs/evaluation/README.md')
add('docs/evaluation/DESIGN.md')
add('docs/visual-design/README.md')
add('docs/visual-design/DESIGN-SYSTEM.md')
add('docs/visual-design/ASSETS.md')
add('docs/literary-core/README.md')
add('docs/literary-core/DESIGN.md')
add('docs/workbench-experience/README.md')
add('docs/workbench-experience/DELIVERY-2.24.3.md')
add('docs/workbench-experience/DELIVERY-2.24.4.md')
add('docs/workbench-experience/DELIVERY-2.24.5.md')
add('docs/workbench-experience/DELIVERY-2.24.6.md')
add('docs/workbench-experience/DELIVERY-2.24.7.md')
add('docs/workbench-experience/DELIVERY-2.24.8.md')
add('docs/workbench-experience/DELIVERY-2.24.9.md')
add('docs/workbench-experience/DELIVERY-2.24.10.md')
add('docs/workbench-experience/DELIVERY-2.24.11.md')
add('docs/workbench-experience/DELIVERY-2.24.12.md')
add('docs/workbench-experience/DELIVERY-2.24.13.md')
add('docs/workbench-experience/DELIVERY-2.24.14.md')
add('docs/workbench-experience/DELIVERY-2.24.15.md')
add('docs/workbench-experience/DELIVERY-2.24.16.md')
add('docs/workbench-experience/DELIVERY-2.24.17.md')
add('docs/workbench-experience/DELIVERY-2.24.18.md')
add('docs/workbench-experience/DELIVERY-2.24.19.md')
add('docs/workbench-experience/DELIVERY-2.24.20.md')
add('docs/workbench-experience/DELIVERY-2.24.21.md')
add('docs/workbench-experience/DELIVERY-2.24.22.md')
add('docs/workbench-experience/DELIVERY-2.24.23.md')
files['.gitignore']='# Developer snapshot: local works, credentials and runtime evidence are private.\n/projects/*\n!/projects/.gitkeep\n**/private-checks/\n**/private-assets/\n/release/\n/web/.runtime/\n/web/runtime/\n/web/frontend/node_modules/\n/web/frontend/dist/\n/web/backend/.venv/\n/.codex/\n**/__pycache__/\n**/.pytest_cache/\n.env\n.env.*\n!.env.example\n*.log\n*.dmp\n*.sqlite\n*.sqlite3\n'.encode('utf8')
manifest={'release':version,'files':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(files.items())}}
files['SOURCE-MANIFEST.json']=json.dumps(manifest,ensure_ascii=False,indent=2).encode()
with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for name,content in sorted(files.items()):archive.writestr('novel-studio-source/'+name,content)
print('DEVELOPER ZIP:',target,'files:',len(files),'bytes:',target.stat().st_size)
