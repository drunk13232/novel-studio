"""Build a standard NSIS installer from a verified existing release only."""
from __future__ import annotations
import argparse,hashlib,json,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BS=chr(92)
NL=chr(10)
DQ=chr(34)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()

def nsis_source_path(path):
    """Use Win32's extended namespace for long absolute compiler input paths.

    Only build-time source paths change; installed names and payload hashes do not.
    """
    value=str(Path(path).resolve())
    if os.name!='nt' or len(value)<240 or value.startswith(BS*2+'?'+BS):return value
    if value.startswith(BS*2):return BS*2+'?'+BS+'UNC'+BS+value[2:]
    return BS*2+'?'+BS+value

def quote(value):
    value=str(value)
    if any(ord(c)<32 for c in value):raise ValueError('Unsafe build value')
    return value.replace('$','$$').replace(DQ,'$'+BS+DQ)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--makensis',required=True,type=Path)
    parser.add_argument('--data-default',type=Path)
    parser.add_argument('--output-name')
    args=parser.parse_args()
    version=json.loads((ROOT/'desktop/version.json').read_text(encoding='utf-8'))['version']
    release=(ROOT/'release'/('v'+version)).resolve();app=release/'NovelStudio'
    manifest=json.loads((app/'RELEASE-MANIFEST.json').read_text(encoding='utf-8'))
    if manifest['release']['version']!=version:raise ValueError('Release mismatch')
    files=[]
    for name,expected in sorted(manifest['files'].items()):
        p=app/name
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(app.resolve()) or digest(p)!=expected:raise ValueError('Release manifest mismatch: '+name)
        if name in {'data-location.json','_internal/resources/preview.txt'}:continue
        files.append((name,p))
    files.append(('ORIGIN-RELEASE-MANIFEST.json',app/'RELEASE-MANIFEST.json'))
    tool=args.makensis.resolve()
    if not tool.is_file():raise ValueError('Missing verified NSIS compiler')
    notice=tool.parent/'COPYING'
    if not notice.is_file():raise ValueError('Missing NSIS license notice')
    files.append(('INSTALLER-THIRD-PARTY-NOTICES.txt',notice))
    filename=args.output_name or f'NovelStudio-{version}-Setup.exe'
    if Path(filename).name!=filename or not filename.endswith('.exe'):raise ValueError('Unsafe output name')
    output=release/filename
    if output.exists():raise ValueError('Installer already exists; preserve it or select a new output name')
    build=ROOT/'desktop/build/installer'/version;build.mkdir(parents=True,exist_ok=True)
    default=str(args.data_default) if args.data_default else '$LOCALAPPDATA'+BS+'NovelStudio'
    if args.data_default and (not args.data_default.is_absolute() or len(default)>440):raise ValueError('Invalid default data directory')
    pre=[f'!define APP_VERSION "{quote(version)}"',f'!define SETUP_OUTPUT "{quote(output)}"',f'!define DEFAULT_DATA_DIRECTORY "{quote(default) if args.data_default else default}"',f'!define PAYLOAD_KB {sum(p.stat().st_size for _,p in files)//1024}', f'!define MAX_INSTALL_ROOT_LENGTH {253-max(len(n.encode("utf-16-le"))//2 for n,_ in files)}', '!macro InstallVerifiedPayload']
    parent=None
    for name,p in files:
        folder=Path(name).parent.as_posix().replace('/',BS)
        folder='' if folder=='.' else BS+folder
        if folder!=parent:
            pre.append(f' SetOutPath "$INSTDIR{quote(folder)}"');parent=folder
        pre.append(f' File "/oname={quote(Path(name).name)}" "{quote(nsis_source_path(p))}"')
    pre+=['!macroend','!macro UninstallVerifiedPayload']
    for name,_ in files:pre.append(' Delete "$INSTDIR'+BS+quote(name.replace('/',BS))+'"')
    dirs={parent.as_posix().replace('/',BS) for n,_ in files for parent in Path(n).parents if str(parent)!='.'}
    for folder in sorted(dirs,key=lambda x:(x.count(BS),len(x)),reverse=True):pre.append(' RMDir "$INSTDIR'+BS+quote(folder)+'"')
    pre.append('!macroend')
    include=build/'payload.nsh';include.write_text(NL.join(pre)+NL,encoding='utf-8-sig')
    result=subprocess.run([str(tool),'/V3','/NOCONFIG',f'/DBUILD_INCLUDE={include}',str(ROOT/'desktop/installer.nsi')],cwd=ROOT)
    if result.returncode:raise SystemExit(result.returncode)
    record={'version':version,'installer':output.name,'sha256':digest(output),'bytes':output.stat().st_size,'source_manifest_sha256':digest(app/'RELEASE-MANIFEST.json'),'application_exe_sha256':digest(app/'NovelStudio.exe'),'compiler_sha256':digest(tool),'payload_files':len(files),'max_install_root_length':253-max(len(n.encode('utf-16-le'))//2 for n,_ in files),'preview_auto_mode':False,'author_data_included':False,'personal_data_default':bool(args.data_default),'no_auto_launch':True,'uninstall':'fixed owned file list; no recursive application or data-folder removal'}
    (release/(output.stem+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    (release/(output.stem+'.sha256')).write_text(record['sha256']+'  '+output.name+NL,encoding='utf-8')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
