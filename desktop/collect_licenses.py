"""Copy installed dependency notices only, never traverse novel projects."""
from pathlib import Path
import json,shutil,importlib.metadata,sys
root=Path(__file__).resolve().parents[1];out=root/'desktop/third-party';out.mkdir(exist_ok=True);rows=[]
modules=root/'web/frontend/node_modules'
for p in modules.glob('**/package.json'):
 if 'node_modules' not in p.parts or len(p.relative_to(modules).parts)>5:continue
 try:meta=json.loads(p.read_text('utf8'))
 except (ValueError,OSError):continue
 name=meta.get('name','');version=meta.get('version','');notices=[f for f in p.parent.iterdir() if f.is_file() and f.name.lower().startswith(('license','licence','copying','notice','copyright'))]
 if not name or not notices:continue
 folder=out/'javascript'/name.replace('/','_').replace('@','');folder.mkdir(parents=True,exist_ok=True)
 for f in notices:shutil.copy2(f,folder/f.name)
 rows.append({'name':name,'version':version,'license':meta.get('license','see included notices')})
for d in sorted(importlib.metadata.distributions(),key=lambda d:d.metadata.get('Name','').lower()):
 name=d.metadata.get('Name','unknown');folder=out/'python'/name;folder.mkdir(parents=True,exist_ok=True)
 for f in d.files or []:
  if Path(f).name.lower().startswith(('license','licence','copying','notice','copyright')):shutil.copy2(d.locate_file(f),folder/Path(f).name)
 rows.append({'name':name,'version':d.version,'license':d.metadata.get('License-Expression') or d.metadata.get('License','see included notices')})
for base in [Path(sys.base_prefix),Path(sys.base_prefix)/'Lib']:
 for name in ['LICENSE.txt','LICENSE']:
  if (base/name).is_file():
   folder=out/'python/CPython';folder.mkdir(exist_ok=True);shutil.copy2(base/name,folder/name)
guest=root/'web/backend/app/automation/runtime/LICENSE'
if guest.is_file():
 folder=out/'python/CPython-WASI';folder.mkdir(parents=True,exist_ok=True);shutil.copy2(guest,folder/'LICENSE')
 rows.append({'name':'CPython-WASI','version':'3.14.7','license':'PSF and included historical notices','source':'https://github.com/brettcannon/cpython-wasi-build/releases/tag/v3.14.7','archive_sha256':'2e064d3fb8172471d39d741348efa722349c40b96301f69968dff714999c584b'})
# Audited originals omitted from npm package roots; never invent copyright text.
supplemental=out/'SUPPLEMENTAL-NOTICES.json'
if supplemental.is_file():
 import hashlib
 for entry in json.loads(supplemental.read_text('utf8'))['entries']:
  source=root/entry['path']
  if not source.resolve().is_relative_to(out.resolve()) or source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest()!=entry['sha256']:raise RuntimeError('Supplemental notice integrity mismatch')
  installed=json.loads((modules/entry['name']/'package.json').read_text('utf8'))
  if installed['version']!=entry['version']:raise RuntimeError('Re-review supplemental notice for changed package version: '+entry['name'])
  rows=[row for row in rows if row['name']!=entry['name']]
  rows.append({key:entry[key] for key in ['name','version','license','source']})
# Some official distributions declare a license without shipping its text.
# Retain verified, corresponding-version upstream originals without relicensing.
python_supplemental=out/'PYTHON-SUPPLEMENTAL-NOTICES.json'
if python_supplemental.is_file():
 import hashlib
 for entry in json.loads(python_supplemental.read_text('utf8'))['entries']:
  if importlib.metadata.version(entry['name'])!=entry['version']:raise RuntimeError('Re-review Python supplemental notice for changed version: '+entry['name'])
  for notice in entry['files']:
   source=root/notice['path']
   if not source.resolve().is_relative_to(out.resolve()) or source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest()!=notice['sha256']:raise RuntimeError('Python supplemental notice integrity mismatch')
  for row in rows:
   if row['name'].lower().replace('_','-')==entry['name'].lower().replace('_','-'):row['source']=entry['source']
(out/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf8')
(out/'README.txt').write_text('Installed third-party notices for Novel Studio. JavaScript bundles include MIT/ISC/Apache-2.0 packages and their notices. SAPI5 is a Windows system interface; comtypes is MIT. External Pandoc 3.12.1 is NOT included in the release ZIP (GPL-2.0-or-later, https://pandoc.org). UI font selection uses system fonts. PDF standard fonts are redistributed from pinned pdfjs-dist with their notices; corresponding Liberation source is under font-source. Local art uses Lucide icons under ISC. PyInstaller bootloader redistribution uses its GPL exception. See individual files for complete terms.','utf8')
print('dependency notice entries:',len(rows))
