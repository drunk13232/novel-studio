"""Read-only local portraits. Never exposes a user-selected filesystem path."""
import hashlib,json,re,stat
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import FileResponse
from PIL import Image
from app.errors import ConsoleError

SKINS=('yoshino','rem')
FILENAME=re.compile(r'^[A-Za-z0-9_-]{1,80}\.(?:png|webp|jpg|jpeg)$')
MIME={'PNG':'image/png','WEBP':'image/webp','JPEG':'image/jpeg'}
PUBLIC_FILES={'manifest.json','README.txt'}

def safe_local(path,root):
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):return False
    for part in [path,*path.parents]:
        if part==root.parent:break
        if getattr(part.lstat(),'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT or part.is_symlink():return False
    return True

def local_manifest(root):
    path=root/'manifest.json'
    try:
        if not safe_local(path,root) or path.stat().st_size>4096:return {}
        value=json.loads(path.read_text('utf-8-sig'))
        return value if isinstance(value,dict) and value.get('schema_version')==1 else {}
    except (OSError,ValueError):return {}

def portrait(root,skin):
    name=local_manifest(root).get(skin)
    if not isinstance(name,str) or not FILENAME.fullmatch(name):return None
    path=root/name
    try:
        if not safe_local(path,root) or not 0<path.stat().st_size<=8*1024*1024:return None
        with Image.open(path) as image:
            if image.format not in MIME or image.width*image.height>6_000_000:return None
            expected={'.png':'PNG','.webp':'WEBP','.jpg':'JPEG','.jpeg':'JPEG'}[path.suffix]
            if image.format!=expected:return None
            kind=MIME[image.format];image.verify()
        revision=hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        return path,kind,revision
    except (OSError,ValueError,Image.DecompressionBombError):return None

def assert_public_resources(root):
    """A public build must not accidentally distribute local companion artwork."""
    if not root.is_dir():raise RuntimeError('Missing public companion resource slots')
    if set(p.name for p in root.iterdir())!=PUBLIC_FILES:raise RuntimeError('Personal companion resources must stay outside public builds')
    if local_manifest(root)!={'schema_version':1,'yoshino':None,'rem':None}:raise RuntimeError('Public companion manifest must contain empty portrait slots')
    for name in PUBLIC_FILES:
        if not safe_local(root/name,root):raise RuntimeError('Unsafe public companion resource')

def companion_routes(personal,bundled):
    router=APIRouter()
    def find(skin):
        for root,source in [(personal,'personal'),(bundled,'bundled')]:
            item=portrait(root,skin)
            if item:return item,source
        return None,None
    @router.get('/api/studio/companion/manifest')
    def manifest():
        rows={}
        for skin in SKINS:
            item,source=find(skin)
            rows[skin]={'status':'ready' if item else 'missing','source':source,
                        'url':f'/api/studio/companion/{skin}?v={item[2]}' if item else None}
        return {'schema_version':1,'assets':rows}
    @router.get('/api/studio/companion/{skin}')
    def image(skin:str):
        if skin not in SKINS:raise ConsoleError('未知陪伴角色',404)
        item,_=find(skin)
        if not item:raise ConsoleError('尚未添加可用的本地立绘',404)
        return FileResponse(item[0],media_type=item[1])
    return router
