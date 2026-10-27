"""Fetch the pinned CPython WASI runtime; TLS and SHA-256 remain mandatory."""
from pathlib import Path,PurePosixPath
import hashlib,json,shutil,tempfile,urllib.request,zipfile

ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/brettcannon/cpython-wasi-build/releases/download/v3.14.7/python-3.14.7-wasi_sdk-24.zip'
SHA256='2e064d3fb8172471d39d741348efa722349c40b96301f69968dff714999c584b'
TARGET=ROOT/'web/backend/app/automation/runtime'

def verify(folder):
    lock=json.loads((ROOT/'docs/character-control/RUNTIME-LOCK.json').read_text('utf8'))
    files=lock['files']
    for name,expected in files.items():
        path=folder/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError('Runtime integrity mismatch: '+name)
    return len(files)

def main():
    if TARGET.exists():
        print('Verified existing runtime:',verify(TARGET),'files');return
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='novel-python-') as temp:
        archive=Path(temp)/'python.zip'
        request=urllib.request.Request(URL,headers={'User-Agent':'NovelStudio-Runtime-Installer/2.20'})
        with urllib.request.urlopen(request,timeout=90) as source,archive.open('wb') as out:
            if source.geturl().split(':',1)[0]!='https':raise RuntimeError('HTTPS required')
            size=0
            while block:=source.read(1024*1024):
                size+=len(block)
                if size>20000000:raise RuntimeError('Runtime archive exceeds expected size')
                out.write(block)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise RuntimeError('Downloaded runtime checksum mismatch')
        stage=Path(temp)/'runtime';stage.mkdir()
        with zipfile.ZipFile(archive) as z:
            if z.testzip():raise RuntimeError('Runtime ZIP is damaged')
            if sum(f.file_size for f in z.infolist())>60000000:raise RuntimeError('Runtime archive expansion too large')
            for entry in z.infolist():
                name=PurePosixPath(entry.filename)
                if name.is_absolute() or '..' in name.parts or ':' in entry.filename or '\\' in entry.filename or (entry.external_attr>>16)&0o170000==0o120000:raise RuntimeError('Unsafe runtime archive entry')
            z.extractall(stage)
        source=stage
        if not (source/'python.wasm').exists():
            matches=list(stage.rglob('python.wasm'))
            if len(matches)!=1:raise RuntimeError('Unexpected runtime layout')
            source=matches[0].parent
        verify(source)
        shutil.copytree(source,TARGET)
    print('Installed verified CPython 3.14.7 WASI runtime')

if __name__=='__main__':main()
