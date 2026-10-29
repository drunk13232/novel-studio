"""Refresh an explicit reviewed source list; never copy the parent Git workspace."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--developer-zip',required=True);args=p.parse_args()
 archive=Path(args.developer_zip).resolve()
 if not archive.is_relative_to(ROOT/'release') or not archive.is_file():raise SystemExit('Use a retained developer ZIP under release/')
 old=json.loads((ROOT/'docs/oss/PUBLIC-ALLOWLIST.json').read_text('utf8'))
 with zipfile.ZipFile(archive) as z:
  if z.testzip():raise SystemExit('Developer ZIP CRC failed')
  developer=json.loads(z.read('novel-studio-source/SOURCE-MANIFEST.json'))
  for name,expected in developer['files'].items():
   if hashlib.sha256(z.read('novel-studio-source/'+name)).hexdigest()!=expected:raise SystemExit('Developer ZIP hash mismatch')
 chosen=set(developer['files'])
 # Old reviewed non-code installation/licensing resources remain; obsolete audit
 # snapshots are not republished as current evidence.
 for row in old['files']:
  name=row['path']
  if name.startswith('docs/oss/'):continue  # Current public OSS documents are explicitly selected below.
  if (ROOT/name).is_file():chosen.add(name)
 for folder in ['web/backend/app','web/backend/tests','web/frontend/src','web/frontend/scripts','scripts','python','schemas','engine/templates','templates']:
  for file in (ROOT/folder).rglob('*'):
   if file.is_file() and file.suffix in {'.py','.ps1','.json','.ts','.tsx','.css','.mjs','.js','.yaml','.yml','.md','.typed'} and not {'__pycache__','private-checks','private-assets','source-backup'}.intersection(file.relative_to(ROOT).parts):chosen.add(file.relative_to(ROOT).as_posix())
 extras=['README.md','README_EN.md','INSTALL.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md','THIRD_PARTY_NOTICES.md','docs/DEVELOPMENT.md','docs/WINDOWS-BUILD.md','desktop/export_public_source.py','tools/oss/build_public_allowlist.py','tools/oss/scan_public_candidate.py','docs/workbench-experience/DELIVERY-2.24.9.md','docs/workbench-experience/DELIVERY-2.24.10.md','docs/workbench-experience/DELIVERY-2.24.11.md','docs/workbench-experience/DELIVERY-2.24.12.md','docs/workbench-experience/DELIVERY-2.24.13.md','docs/oss/CHANGELOG-SOURCES.json','docs/oss/DEPENDENCIES.md','docs/oss/INSTALL-VERIFICATION.md','docs/oss/PREPUBLICATION.md','docs/oss/CANDIDATE-AUDIT.md','docs/oss/RELEASE-NOTES.md','docs/oss/RELEASE-NOTES-TEMPLATE.md','docs/oss/RELEASE-PAGE-NOTES.md','docs/oss/public-overrides/test_global_replace.py','desktop/third-party/font-source/liberation-fonts-1.07.4.tar.gz']
 chosen.update(extras)
 chosen.update(['LICENSE','NOTICE','COPYRIGHT','COPYRIGHT-CONFIRMATION.md','docs/oss/FONTS.md','docs/oss/FONT-PROVENANCE.json','docs/oss/SCREENSHOTS.md','docs/oss/SCREENSHOT-PROVENANCE.json','docs/oss/EXTERNAL-SKILLS.md','docs/oss/screenshots/bookshelf.png','docs/oss/screenshots/editor.png','desktop/INSTALLER.md','desktop/build_installer.py','licenses/installer/NSIS-3.13.txt'])
 for folder in ['.github','licenses','desktop/third-party']:
  chosen.update(file.relative_to(ROOT).as_posix() for file in (ROOT/folder).rglob('*') if file.is_file())
 # Include the complete pre-reviewed runtime lock, not a partial stdlib tree.
 runtime_base=ROOT/'web/backend/app/automation/runtime'
 runtime_lock=json.loads((ROOT/'docs/character-control/RUNTIME-LOCK.json').read_text('utf8'))
 for relative,expected in runtime_lock['files'].items():
  file=runtime_base/relative
  if not file.resolve().is_relative_to(runtime_base.resolve()) or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:raise SystemExit('Pinned runtime resource mismatch: '+relative)
  chosen.add(file.relative_to(ROOT).as_posix())
 chosen.discard('COPYRIGHT-CONFIRMATION.candidate.md')
 chosen.discard('NOTICE.candidate')
 chosen.discard('docs/oss/LICENSE-OPTIONS.md')
 chosen={name for name in chosen if '.candidate' not in name and not name.startswith('docs/oss/public-overrides/')}
 chosen.discard('scripts/check_v06.py')  # Owner-approved exclusion; private original retained.
 chosen.update(['docs/oss/public-overrides/test_global_replace.py','docs/oss/public-overrides/check-global-replace.mjs'])  # Portable re-export requires the reviewed override sources.
 chosen.discard('SOURCE-MANIFEST.json');chosen.discard('SOURCE-README.md');chosen.discard('projects/.gitkeep');chosen.discard('docs/oss/PUBLIC-ALLOWLIST.json')
 chosen={name for name in chosen if not name.startswith('web/frontend/public/pdf/')}
 exclusions={'.git','.codex','.venv','node_modules','private-checks','private-assets','private-audit','source-backup','__pycache__','logs'}
 rows=[]
 for name in sorted(chosen):
  rel=PurePosixPath(name)
  if rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or exclusions.intersection(rel.parts):raise SystemExit('Unsafe candidate path: '+name)
  if rel.parts[0] in {'projects','chapters','state','settings','outlines','reviews','release'}:raise SystemExit('Author data excluded: '+name)
  source_name={'desktop/data-location.json':'desktop/data-location.public.json','web/backend/tests/test_global_replace.py':'docs/oss/public-overrides/test_global_replace.py','web/frontend/scripts/check-global-replace.mjs':'docs/oss/public-overrides/check-global-replace.mjs'}.get(name,name)
  file=ROOT/source_name
  if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(ROOT):raise SystemExit('Missing/unsafe source: '+source_name)
  if any(parent.is_symlink() for parent in file.parents if parent.is_relative_to(ROOT)):raise SystemExit('Symlink parent: '+source_name)
  content=file.read_bytes();row={'path':name,'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)}
  if source_name!=name:row['source_path']=source_name
  rows.append(row)
 manifest={'version':json.loads((ROOT/'desktop/version.json').read_text('utf8'))['version']+' Preview','license':'Apache-2.0','copyright':'Copyright 2026 drunk13232','intended_repository':'drunk13232/novel-studio','history_included':False,'publication_ready':False,'source':'current retained developer manifest + scoped application/tests/helpers + reviewed public docs and notices; no Git history','public_overrides':'Only portable locator and owner-approved synthetic test names; original tests/business data unchanged. Upstream terms remain; no private Git history is exported.','files':rows,'excluded_categories':['user works and private project IDs','credentials and user-level Codex settings','private character models/voices and plugin caches','developer environments and runtime/audit logs','parent Git objects and old release archives','generated PDF assets rebuilt from pinned npm package','old audit snapshots not current acceptance']}
 (ROOT/'docs/oss/PUBLIC-ALLOWLIST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
 print(json.dumps({'version':manifest['version'],'files':len(rows),'bytes':sum(x['bytes'] for x in rows),'history_included':False,'publication_ready':False},indent=2))
if __name__=='__main__':main()
