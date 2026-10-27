import hashlib
import json
import os
import re
import sqlite3
import uuid
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from app.errors import ConsoleError

def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return prefix+'_'+uuid.uuid4().hex
def digest(data): return hashlib.sha256(data).hexdigest()
def safe(root, relative):
    if not isinstance(relative,str) or not relative or any(c in relative for c in '\\:\x00'):
        raise ConsoleError('无效相对路径',403)
    parts=relative.split('/')
    if any(p in {'','.','..'} or p.endswith((' ','.')) or re.match(r'^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)',p,re.I) for p in parts):
        raise ConsoleError('路径越界或 Windows 保留文件名',403)
    p=root.joinpath(*parts)
    for q in [p,*p.parents]:
        if q==root: break
        if q.is_symlink() or q.is_junction(): raise ConsoleError('不允许链接目录或文件',403)
    if not p.resolve().is_relative_to(root.resolve()): raise ConsoleError('路径越界',403)
    return p

def read(path, default=None):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError,UnicodeError) as e: raise ConsoleError('文件损坏，请从历史恢复：'+path.name,422) from e

def write_bytes(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.pending-'+uuid.uuid4().hex)
    try:
        with temporary.open('xb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        from app.atomic import replace
        replace(temporary,path)
    finally: temporary.unlink(missing_ok=True)

def write(path,value): write_bytes(path,json.dumps(value,ensure_ascii=False,indent=2).encode('utf8'))

def checkpoint(root,relative,source='PRE_WRITE',note=''):
    path=safe(root,relative)
    if not path.is_file(): return None
    data=path.read_bytes();id=uid('revision')
    base=safe(root,'history/revisions/'+id)
    row={'id':id,'path':relative,'created_at':now(),'source':source,'note':note,'sha256':digest(data),'size':len(data),'blob':id+'/content'+path.suffix}
    write_bytes(base/('content'+path.suffix),data)
    write(base/'revision.json',row)
    return row

def checkpoint_before_replace(path):
    """Hook covers existing atomic YAML/JSON writers without migrating files."""
    path=Path(path)
    for root in path.parents:
        if re.fullmatch(r'novel_[0-9a-f]{32}',root.name) and root.parent.name=='projects':
            relative=path.relative_to(root).as_posix()
            if relative.split('/')[0] in {'chapters','characters','bible','settings','outlines','.research'} and path.suffix in {'.txt','.md','.yaml','.yml','.json'}:
                checkpoint(root,relative)
            break

def revisions(root,path=None):
    folder=safe(root,'history/revisions')
    rows=[read(safe(root,p.relative_to(root).as_posix())) for p in folder.glob('revision_*/revision.json')]
    return sorted([r for r in rows if not path or r['path']==path],key=lambda x:x['created_at'],reverse=True)

def revision_content(root,id):
    if not re.fullmatch(r'revision_[0-9a-f]{32}',id):raise ConsoleError('无效历史 ID',403)
    row=read(safe(root,'history/revisions/'+id+'/revision.json'))
    if not row:raise ConsoleError('历史不存在',404)
    data=safe(root,'history/revisions/'+row['blob']).read_bytes()
    if digest(data)!=row['sha256']:raise ConsoleError('历史校验失败',409)
    return row,data

def files(root):
    for directory,dirs,names in os.walk(root,followlinks=False):
        dirs[:]=[n for n in dirs if n not in {'.git','.codex','.agents','node_modules','__pycache__','.venv'}]
        for name in names:
            relative=(Path(directory)/name).relative_to(root).as_posix()
            yield relative,safe(root,relative)

@contextmanager
def database(root):
    path=safe(root,'storage/index.sqlite');path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path,timeout=10)
    try:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, type TEXT, name TEXT, path TEXT, content TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS refs (source_type TEXT, source_id TEXT, target_type TEXT, target_id TEXT, relation_type TEXT, description TEXT)')
        yield db
        db.commit()
    finally:db.close()

_index_lock=threading.RLock()
_index_signatures={}
def index_signature(root,relations=None):
    rows=[]
    for rel,p in files(root):
        if rel.split('/')[0] in {'chapters','characters','bible','assets','settings','outlines'} and p.suffix in {'.txt','.md','.yaml','.yml','.json'}:
            st=p.stat();rows.append((rel,st.st_mtime_ns,st.st_size))
    return digest(json.dumps([sorted(rows),relations],sort_keys=True,ensure_ascii=False).encode())

def rebuild(root,relations=None):
    import yaml
    rows=[];refs=[]
    for rel,p in files(root):
        if rel.startswith(('history/','trash/','storage/','art/jobs/')):continue
        if p.suffix not in {'.txt','.md','.yaml','.yml','.json'} or p.stat().st_size>2*1024*1024:continue
        if rel.split('/')[0] not in {'chapters','characters','bible','assets','settings','outlines'}:continue
        text=p.read_text(encoding='utf-8-sig');kind=rel.split('/')[0];name=p.stem;id=rel
        try:
            v=json.loads(text) if p.suffix=='.json' else yaml.safe_load(text) if p.suffix in {'.yaml','.yml'} else None
            if isinstance(v,dict):
                id=str(v.get('id',rel));name=str(v.get('name',v.get('title',name)))
                if rel=='bible/relations.json':refs=v.get('relations',[])
            elif kind=='chapters':name=text.splitlines()[0] if text.splitlines() else name
        except (ValueError,yaml.YAMLError):pass
        rows.append((id,kind,name,rel,text))
    if relations is not None:refs=relations
    with database(root) as db:
        db.execute('DELETE FROM documents');db.execute('DELETE FROM refs')
        db.executemany('INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?)',rows)
        for r in refs:db.execute('INSERT INTO refs VALUES (?,?,?,?,?,?)',tuple(r.get(k,'') for k in ['source_type','source_id','target_type','target_id','relation_type','description']))
    return {'documents':len(rows),'relations':len(refs),'rebuilt_at':now()}

def search(root,query,relations=None):
    # SQLite instr provides exact Unicode substring matching, not English FTS.
    key=str(root.resolve())
    with _index_lock:
        signature=index_signature(root,relations)
        if _index_signatures.get(key)!=signature or not safe(root,'storage/index.sqlite').exists():
            rebuild(root,relations)
            _index_signatures[key]=signature
    with database(root) as db:
        return [dict(zip(['id','type','name','path','excerpt'],r)) for r in db.execute('SELECT id,type,name,path,substr(content,max(1,instr(content,?)-60),240) FROM documents WHERE instr(lower(name),lower(?))>0 OR instr(lower(content),lower(?))>0 LIMIT 100',(query,query,query))]

@contextmanager
def write_guard(engine):
    from app.tasks.lease import acquire,release
    lease=acquire(engine,'studio-data.lock')
    try:yield
    finally:release(lease)
