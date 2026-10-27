import io
import re
import warnings
from PIL import Image,ImageOps,UnidentifiedImageError
from app.errors import ConsoleError
from .storage import safe,read,write,write_bytes,uid,now,digest

MAX_BYTES=24*1024*1024
MAX_PIXELS=24_000_000
Image.MAX_IMAGE_PIXELS=MAX_PIXELS
CATEGORIES=['人物','地点','道具','生物','章节','封面','参考资料','未分类']

def decode(data):
    if len(data)>MAX_BYTES:raise ConsoleError('图片超过 24 MiB',413)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                format=image.format;size=image.size
                if format not in {'PNG','JPEG','WEBP'}:raise ConsoleError('只接受 PNG / JPG / WebP 内容',422)
                if size[0]*size[1]>MAX_PIXELS or max(size)>12000 or getattr(image,'n_frames',1)>1:raise ConsoleError('图片尺寸过大或含动画',422)
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                image.load();thumb=ImageOps.exif_transpose(image).convert('RGB');thumb.thumbnail((480,480))
                result=io.BytesIO();thumb.save(result,format='JPEG',quality=85)
        return format,size,result.getvalue()
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombWarning,Image.DecompressionBombError) as e:
        raise ConsoleError('图片解码或资源验证失败',422) from e

class Assets:
    def __init__(self,registry,bible):self.registry=registry;self.bible=bible
    def root(self,p):return self.registry.workspace(p).root
    def list(self,project):
        return sorted([self.get(project,p.stem) for p in safe(self.root(project),'assets/metadata').glob('asset_*.json')],key=lambda x:x['created_at'],reverse=True)
    def get(self,project,id):
        if not re.fullmatch(r'asset_[0-9a-f]{32}',id):raise ConsoleError('无效素材 ID',403)
        p=safe(self.root(project),'assets/metadata/'+id+'.json');row=read(p)
        if not row:raise ConsoleError('素材不存在',404)
        if not re.fullmatch(r'assets/(original|generated)/'+re.escape(id)+r'\.(png|jpg|webp)',row.get('file','')) or row.get('thumbnail')!='assets/thumbnails/'+id+'.jpg':raise ConsoleError('素材路径与稳定 ID 不匹配',422)
        return {**row,'etag':digest(p.read_bytes())}
    def import_image(self,project,data,name='图片',generated=None):
        format,size,thumb=decode(data);root=self.root(project);id=uid('asset')
        suffix={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[format]
        relative='assets/'+('generated/' if generated else 'original/')+id+suffix
        row={'id':id,'name':str(name)[:200],'category':'未分类','tags':[],'favorite':False,'notes':'','created_at':now(),'updated_at':now(),
             'file':relative,'thumbnail':'assets/thumbnails/'+id+'.jpg','width':size[0],'height':size[1],'format':format,'size':len(data),'sha256':digest(data),
             'links':[],'generation':generated}
        write_bytes(safe(root,relative),data);write_bytes(safe(root,row['thumbnail']),thumb)
        write(safe(root,'assets/metadata/'+id+'.json'),row)
        return self.get(project,id)
    def update(self,project,id,value,etag):
        row=self.get(project,id);root=self.root(project)
        if row.pop('etag')!=etag:raise ConsoleError('素材信息已变化，请刷新',409)
        if set(value)-{'name','category','tags','favorite','notes','links'}:raise ConsoleError('只允许编辑素材展示信息和关联',422)
        if value.get('category',row['category']) not in CATEGORIES:raise ConsoleError('无效素材分类',422)
        if not isinstance(value.get('tags',[]),list) or not all(isinstance(t,str) and len(t)<=100 for t in value.get('tags',[])):raise ConsoleError('无效标签',422)
        links=value.get('links',row['links'])
        if not isinstance(links,list) or len(links)>100:raise ConsoleError('关联数量无效',422)
        seen=set()
        for link in links:
            if set(link)!={'type','id','role'} or link['role'] not in {'PRIMARY','CANDIDATE','REFERENCE','DEPRECATED'}:raise ConsoleError('无效图片关联',422)
            self.bible.check_target(project,link['type'],link['id'])
            key=(link['type'],link['id'])
            if key in seen:raise ConsoleError('同一图片的关联对象重复',422)
            seen.add(key)
        for key in ['name','notes']:
            if key in value and (not isinstance(value[key],str) or len(value[key])>10000):raise ConsoleError('素材文字过长',422)
        for link in links:
            if link['role']=='PRIMARY':
                for other in self.list(project):
                    if other['id']==id:continue
                    changed=False
                    for old in other['links']:
                        if (old['type'],old['id'],old['role'])==(link['type'],link['id'],'PRIMARY'):old['role']='REFERENCE';changed=True
                    if changed:other.pop('etag');write(safe(root,'assets/metadata/'+other['id']+'.json'),other)
        row.update(value,updated_at=now());write(safe(root,'assets/metadata/'+id+'.json'),row)
        return self.get(project,id)
    def path(self,project,id,thumbnail=False):
        row=self.get(project,id);root=self.root(project);p=safe(root,row['thumbnail'] if thumbnail else row['file'])
        if not p.exists():
            if not thumbnail:raise ConsoleError('原图缺失（可能来自不含图片的轻量备份）',404)
            original=safe(root,row['file'])
            if not original.is_file():raise ConsoleError('素材原图缺失',404)
            # Read route returns original after cleanup; rebuilding thumbnails is explicit.
            return original
        return p
