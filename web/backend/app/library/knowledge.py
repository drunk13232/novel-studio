"""Author-facing associations over existing files and the disposable project SQLite index.
Never imported by Writer ContextBuilder. No entity copies, Canon writes or inferred identities.
"""
import json,sqlite3,threading
from fastapi import APIRouter
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
from app.errors import ConsoleError
from app.library.storage import safe,read,write,digest,uid,now,database,checkpoint
from app.studio_tools import normalized,utf16_slice,utf16_index

STATUSES={'AUTHOR_CONFIRMED','COMMITTED','AI_PROPOSED','UNKNOWN','REFERENCE','PLANNED','BACKGROUND'}
LABELS={'character':'人物','entity':'设定','location':'地点','faction':'势力','item':'道具','term':'术语','event':'事件','chapter':'章节','clue':'伏笔','reference':'文献','asset':'图片'}
LOCATIONS={'continent','region','city','town','building','location','geography'}
FACTIONS={'country','government','army','company','sect','family','faction','secret-faction'}
class LinkRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_type:str;source_id:str;target_type:str;target_id:str
    relation_type:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=2000)
    status:Literal['AUTHOR_CONFIRMED','AI_PROPOSED','UNKNOWN']='AUTHOR_CONFIRMED'
    evidence:str=Field(default='',max_length=2000)
    chapter_id:str='';story_time:str='';etag:str
    confirm:bool=False
class AnchorRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    path:str;document_revision:str;start:int=Field(ge=0);end:int=Field(gt=0)
    selected_text:str=Field(min_length=1,max_length=2000)
    target_type:str;target_id:str;etag:str;confirm:Literal[True]

class Knowledge:
    def __init__(self,registry,tools,references):
        self.registry=registry;self.tools=tools;self.bible=tools.bible;self.references=references;self.lock=threading.RLock()
    def root(self,p):return self.registry.workspace(p).root
    def associations(self,p):
        path=safe(self.root(p),'bible/relations.json')
        return {'relations':self.bible.explicit_relations(p),'etag':digest(path.read_bytes()) if path.exists() else digest(b'')}
    def anchors(self,p,path=None):
        rows=[]
        for f in safe(self.root(p),'metadata/studio/entity-anchors').glob('*.json'):
            row=read(f)
            if path and row['path']!=path:continue
            doc=self.tools.doc(p,row['path']) if safe(self.root(p),row['path']).is_file() else None
            located=False
            if doc and doc['etag']==row['document_revision']:
                try:located=utf16_slice(normalized(doc),row['start'],row['end'])==row['anchor']['exact']
                except ConsoleError:pass
            rows.append({**row,'located':located,'etag':digest(f.read_bytes()),'location_status':'已定位' if located else '需要重新定位'})
        return rows
    def source_stamp(self,p):
        # Metadata only. Index queries never reread the manuscript corpus.
        root=self.root(p);f=safe(root,'project.yaml');stat=f.stat();rows=[('project.yaml',stat.st_mtime_ns,stat.st_size)]
        for directory in ['characters','bible','settings','state','outlines','chapters','assets/metadata','.research/library','metadata/studio/entity-anchors']:
            for f in safe(root,directory).rglob('*'):
                if f.is_file() and f.suffix in {'.yaml','.yml','.json','.txt','.md'}:
                    safe(root,f.relative_to(root).as_posix());s=f.stat();rows.append((f.relative_to(root).as_posix(),s.st_mtime_ns,s.st_size))
        for binding in self.references.bindings(p)['documents']:
            if binding['source_scope']=='public':
                for f in [self.references.path('public','documents',binding['id'])]:
                    if f.is_file():s=f.stat();rows.append(('public:'+binding['id'],s.st_mtime_ns,s.st_size))
        return digest(json.dumps(sorted(rows)).encode())
    def collect(self,p):
        ws=self.registry.workspace(p);nodes={};edges=[]
        def node(type,id,name,path='',summary='',status='UNKNOWN',**extra):
            if id:nodes[(type,str(id))]={'id':str(id),'type':type,'name':name or '未命名'+LABELS.get(type,'对象'),'path':path,'summary':str(summary or '')[:4000],'status':status,**extra}
        def edge(st,si,tt,ti,label,evidence,status='UNKNOWN',**extra):
            if (st,str(si)) in nodes and (tt,str(ti)) in nodes:
                edges.append({'id':extra.pop('id',None) or 'derived:'+digest(json.dumps([st,si,tt,ti,label,evidence],ensure_ascii=False).encode())[:24],'source_type':st,'source_id':str(si),'target_type':tt,'target_id':str(ti),'relation_type':label,'description':extra.pop('description',''),'status':status,'evidence':evidence,'created_by':extra.pop('created_by','SOURCE_RECORD'),'derived':extra.pop('derived',True),**extra})
        chars=self.tools.characters.list(p)
        for r in chars:
            c=r['canonical'];node('character',c['id'],c['name'],'characters/'+c['id']+'.yaml',c['identity'].get('summary') or c['identity'].get('occupation'),'AUTHOR_CONFIRMED',identity=c['identity'].get('occupation',''),appearance=c.get('appearance',{}),search_text=' '.join(c.get('aliases',[])))
        entities=self.bible.list(p)
        for e in entities:
            category=e['category'];kind='location' if category in LOCATIONS else 'faction' if category in FACTIONS else 'item' if category in {'item','weapon','equipment','resource'} else category if category in {'term','event','clue','plotline'} else 'entity'
            node('entity',e['id'],e['name'],'bible/entities/'+e['id']+'.json',e['summary'],'AUTHOR_CONFIRMED' if e['status'] in {'FORMAL','LOCKED'} else 'AI_PROPOSED' if e['source']=='AI_PROPOSED' or e['status']=='PENDING' else 'REFERENCE' if e['source']=='RESEARCH' else 'UNKNOWN',category=category,kind=kind,search_text=e.get('details','')+'\n'+json.dumps({'fields':e.get('fields',{}),'periods':e.get('periods',[])},ensure_ascii=False))
        # Read legacy world records in place; no conversion or overwrite.
        for f in safe(ws.root,'settings').glob('*.yaml'):
            data=ws.yaml_file('settings/'+f.name)
            if not isinstance(data,dict):continue
            for key,kind in [('locations','location'),('factions','faction'),('organizations','faction'),('items','item'),('terms','term')]:
                values=data.get(key,[])
                values=[{'id':id,**v} for id,v in values.items() if isinstance(v,dict)] if isinstance(values,dict) else values
                if isinstance(values,list):
                    for value in values:
                        if isinstance(value,dict) and value.get('id'):node(kind,value['id'],value.get('name') or value.get('title'),'settings/'+f.name,value.get('summary') or value.get('description'),'AUTHOR_CONFIRMED')
        for filename,kind,key in [('locations.yaml','location','locations'),('factions.yaml','faction','factions'),('items.yaml','item','items')]:
            path='state/'+filename
            if not safe(ws.root,path).exists():continue
            values=ws.yaml_file(path).get(key,{})
            if isinstance(values,dict):
                for id,value in values.items():
                    if isinstance(value,dict) and (kind,str(id)) not in nodes:node(kind,id,value.get('name') or value.get('title'),path,'；'.join(v.get('text','') for v in value.get('writer_view',[]) if v.get('visibility')=='PUBLIC'),'COMMITTED')
        chapters=self.registry.book_center.catalog(p)['chapters'];chapter_by_number={c['number']:c for c in chapters}
        ledger=ws.yaml_file('state/chapter-ledger.yaml').get('entries',[]);committed={r['chapter'] for r in ledger}
        for c in chapters:node('chapter',c['id'],c['title'] or '未命名章节',c.get('final') or c.get('draft') or '',c.get('purpose',''),'COMMITTED' if c['number'] in committed else 'PLANNED',number=c['number'])
        timeline=ws.yaml_file('state/timeline.yaml').get('events',[])
        if isinstance(timeline,dict):timeline=[{'id':id,**e} for id,e in timeline.items() if isinstance(e,dict)]
        for e in timeline:
            n=e.get('chapter');status='PLANNED' if e.get('type',e.get('event_type')) in {'PLANNED','PLAN'} else 'UNKNOWN' if e.get('type',e.get('event_type')) in {'AUTHOR','AUTHOR_METADATA','SYSTEM','METADATA'} else 'BACKGROUND' if n==0 else 'COMMITTED' if n in committed else 'UNKNOWN'
            node('event',e.get('id'),e.get('title') or e.get('name') or str(e.get('summary') or '未命名事件')[:32],'state/timeline.yaml',e.get('summary',''),status,story_time=e.get('story_time',''),number=n)
        clues=ws.yaml_file('state/foreshadowing.yaml') if safe(ws.root,'state/foreshadowing.yaml').exists() else {}
        values=clues.get('foreshadowing',clues.get('threads',clues.get('clues',{})))
        values=[{'id':id,**v} for id,v in values.items() if isinstance(v,dict)] if isinstance(values,dict) else values
        if isinstance(values,list):
            for e in values:
                if isinstance(e,dict):node('clue',e.get('id'),e.get('title') or e.get('name') or e.get('description') or e.get('id'),'state/foreshadowing.yaml',e.get('summary') or e.get('description'),'UNKNOWN')
        plot=ws.yaml_file('state/plot-threads.yaml') if safe(ws.root,'state/plot-threads.yaml').exists() else {}
        for id,value in plot.get('threads',plot.get('plot_threads',{})).items():
            if isinstance(value,dict):node('entity',id,value.get('title') or value.get('name') or id,'state/plot-threads.yaml',value.get('summary'),'UNKNOWN',kind='plotline')
        assets=[]
        for f in safe(ws.root,'assets/metadata').glob('asset_*.json'):
            a=read(f);assets.append(a);node('asset',a['id'],a['name'],'',a.get('notes',''),'REFERENCE',image=f'/api/projects/{p}/assets/{a["id"]}/file?thumbnail=true')
        refs=self.references.rows(p,'documents');refs=[(p,d) for d in refs if not d.get('trashed')]
        for b in self.references.bindings(p)['documents']:
            if b['source_scope']=='public':
                try:
                    d=self.references.source_document(p,'public',b['id'])
                    if not d.get('trashed'):refs.append(('public',d))
                except ConsoleError:pass
        for scope,d in refs:
            content=''
            if d.get('parse_status')=='READY' or d.get('status') in {'READY','PARTIAL'}:
                try:content='\n'.join(u.get('text','') for u in self.references.extracted(scope,d['id'])['units'])
                except ConsoleError:pass
            node('reference',d['id'],d.get('metadata',{}).get('title') or d.get('name'),'',d.get('metadata',{}).get('description',''),'REFERENCE',source_scope=scope,search_text=content)

        for r in chars:
            c=r['canonical']
            for target,rel in c['relationships']['initial'].items():edge('character',c['id'],'character',target,' / '.join(rel.get('type',[])) or '初始关系','characters/'+c['id']+'.yaml','BACKGROUND',description=rel.get('public_state',{}).get('description',''))
        relations=self.bible.relations(p,entities=entities)
        for r in self.tools.graph(p,entities=entities,relations=relations)['edges']:
            if r.get('source_kind')=='已提交关系记录':edge('character',r['source'],'character',r['target'],r['label'],'state/relationships.yaml','COMMITTED',id=r['id'],description=r['description'],undirected=True,number=r.get('chapter'),story_time=r.get('story_time'))
        for r in relations:
            row={**r};status=row.pop('status','UNKNOWN' if row.get('derived') else 'AUTHOR_CONFIRMED')
            source_type=row.pop('source_type');source_id=row.pop('source_id');target_type=row.pop('target_type');target_id=row.pop('target_id');label=row.pop('relation_type');evidence=row.pop('evidence','bible/relations.json' if not row.get('derived') else 'bible/entities/'+source_id+'.json')
            edge(source_type,source_id,target_type,target_id,label,evidence,status,**row)
        for e in timeline:
            eid=e.get('id');status=nodes.get(('event',str(eid)),{}).get('status','UNKNOWN');c=chapter_by_number.get(e.get('chapter'));evidence='state/timeline.yaml#'+str(eid)
            if c:edge('event',eid,'chapter',c['id'],'发生于章节',evidence,status,story_time=e.get('story_time',''))
            for cid in e.get('characters',[]):edge('event',eid,'character',cid,'涉及人物',evidence,status)
            for tid in e.get('plot_threads',[]):edge('event',eid,'entity',tid,'关联剧情线',evidence,status)
            loc=e.get('location');kind=next((t for t in ['entity','location'] if (t,str(loc)) in nodes),'location');edge('event',eid,kind,loc,'发生地点',evidence,status)
        if isinstance(values,list):
            for clue in values:
                if not isinstance(clue,dict):continue
                for key in ['introduced_chapter','resolved_chapter']:
                    n=clue.get(key);c=chapter_by_number.get(n)
                    if c and n in committed:edge('clue',clue.get('id'),'chapter',c['id'],'已提交引入' if key=='introduced_chapter' else '已提交回收','state/foreshadowing.yaml','COMMITTED')
        for c in self.tools.planning.rows(p,'chapter'):
            for tid in [x for group in c.get('plot_threads',{}).values() for x in group]:edge('chapter',c['id'],'entity',tid,'计划剧情线','outlines/chapters','PLANNED')
            for cid in [x for group in c.get('foreshadowing',{}).values() for x in group]:edge('chapter',c['id'],'clue',cid,'计划伏笔','outlines/chapters','PLANNED')
        for a in assets:
            for link in a.get('links',[]):edge('asset',a['id'],link['type'],link['id'],link['role'],'assets/metadata/'+a['id']+'.json','REFERENCE')
        for n in self.references.rows(p,'notes'):
            for link in n.get('links',[]):edge('reference',n['document_id'],link['type'],link['id'],'Reference Material','.research/library/notes/'+n['id']+'.json','REFERENCE',description=n.get('quote','')[:500])
        for anchor in self.anchors(p):edge('chapter',anchor['chapter_id'],anchor['target_type'],anchor['target_id'],'正文人工定位','metadata/studio/entity-anchors/'+anchor['id']+'.json','AUTHOR_CONFIRMED' if anchor['located'] else 'UNKNOWN',anchor_id=anchor['id'],located=anchor['located'])
        # Chapter-card references stay explicitly PLANNED regardless of final presence.
        for c in self.tools.planning.rows(p,'chapter'):
            cid=c['id']
            for character in set(c.get('characters',[])+([c.get('pov',{}).get('character')] if c.get('pov',{}).get('character') else [])):edge('chapter',cid,'character',character,'章节计划人物','outlines/chapters','PLANNED')
            location=c.get('location');kind=next((t for t in ['entity','location'] if (t,str(location)) in nodes),'location');edge('chapter',cid,kind,location,'章节计划地点','outlines/chapters','PLANNED')
        return list(nodes.values()),edges
    def schema(self,db):
        db.execute('CREATE TABLE IF NOT EXISTS knowledge_entities (type TEXT,id TEXT,payload TEXT,PRIMARY KEY(type,id))')
        db.execute('CREATE TABLE IF NOT EXISTS knowledge_links (id TEXT PRIMARY KEY,source_type TEXT,source_id TEXT,target_type TEXT,target_id TEXT,payload TEXT)')
        db.execute('CREATE INDEX IF NOT EXISTS knowledge_links_source ON knowledge_links(source_type,source_id)')
        db.execute('CREATE INDEX IF NOT EXISTS knowledge_links_target ON knowledge_links(target_type,target_id)')
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(type UNINDEXED,id UNINDEXED,name,summary,tokenize='trigram')")
        db.execute('CREATE TABLE IF NOT EXISTS knowledge_meta (key TEXT PRIMARY KEY,value TEXT)')
    def refresh(self,p,force=False):
        with self.lock:
            if force:
                path=safe(self.root(p),'storage/index.sqlite')
                if path.exists():
                    corrupt=False
                    try:
                        db=sqlite3.connect(path)
                        try:corrupt=db.execute('PRAGMA quick_check').fetchone()[0]!='ok'
                        finally:db.close()
                    except sqlite3.DatabaseError:corrupt=True
                    if corrupt:
                        folder=safe(self.root(p),'storage/corrupt-'+uid('index'));folder.mkdir(parents=True)
                        for suffix in ['', '-wal','-shm']:
                            f=path.with_name(path.name+suffix)
                            if f.exists():f.rename(folder/f.name)
            stamp=self.source_stamp(p)
            try:
                with database(self.root(p)) as db:
                    self.schema(db);previous=db.execute("SELECT value FROM knowledge_meta WHERE key='stamp'").fetchone()
                    if previous and previous[0]==stamp and not force:return
                    nodes,edges=self.collect(p)
                    if self.source_stamp(p)!=stamp:raise ConsoleError('索引期间资料发生变化，请重试刷新',409)
                    db.execute('DELETE FROM knowledge_entities');db.execute('DELETE FROM knowledge_links');db.execute('DELETE FROM knowledge_fts')
                    db.executemany('INSERT INTO knowledge_entities VALUES (?,?,?)',[(n['type'],n['id'],json.dumps({k:v for k,v in n.items() if k!='search_text'},ensure_ascii=False)) for n in nodes])
                    db.executemany('INSERT INTO knowledge_fts VALUES (?,?,?,?)',[(n['type'],n['id'],n['name'],n['summary']+'\n'+n.get('search_text','')) for n in nodes])
                    db.executemany('INSERT OR REPLACE INTO knowledge_links VALUES (?,?,?,?,?,?)',[(e['id'],e['source_type'],e['source_id'],e['target_type'],e['target_id'],json.dumps(e,ensure_ascii=False)) for e in edges])
                    db.execute("INSERT OR REPLACE INTO knowledge_meta VALUES ('stamp',?)",(stamp,))
            except sqlite3.DatabaseError as e:raise ConsoleError('关联索引不可用；原稿不受影响，请在数据中心重建索引或恢复索引文件',409) from e
    def view(self,p,q='',type='',id=None):
        self.refresh(p)
        with database(self.root(p)) as db:
            nodes=[json.loads(r[0]) for r in db.execute('SELECT payload FROM knowledge_entities ORDER BY type,id')]
            if q.strip():
                if len(q.strip())>=3:
                    matched={(r[0],r[1]) for r in db.execute('SELECT type,id FROM knowledge_fts WHERE knowledge_fts MATCH ? LIMIT 200',('"'+q.strip().replace('"','""')+'"',))}
                else:matched={(r[0],r[1]) for r in db.execute('SELECT type,id FROM knowledge_fts WHERE instr(lower(name),lower(?))>0 OR instr(lower(summary),lower(?))>0 LIMIT 200',(q,q))}
                nodes=[n for n in nodes if (n['type'],n['id']) in matched]
            if id:
                rows=db.execute('SELECT payload FROM knowledge_links WHERE (source_type=? AND source_id=?) OR (target_type=? AND target_id=?)',(type,id,type,id)).fetchall()
                entity=next((n for n in nodes if n['type']==type and n['id']==id),None)
                if not entity:raise ConsoleError('对象不属于当前小说或已经移除',404)
            else:rows=db.execute('SELECT payload FROM knowledge_links').fetchall();entity=None
            edges=[json.loads(r[0]) for r in rows]
        return {'entities':[n for n in nodes if not type or n['type']==type or n.get('kind')==type] if not id else nodes,'entity':entity,'relations':edges,'labels':LABELS,'associations':self.associations(p),'audience':'AUTHOR','writer_context':False,'refreshed_at':now()}
    def lookup(self,p,q,limit=40):
        """Bounded read from the existing FTS; no graph or manuscript replay."""
        self.refresh(p);q=q.strip()[:120];limit=max(1,min(limit,100))
        if not q:return []
        with database(self.root(p)) as db:
            if len(q)>=3:
                rows=db.execute('SELECT e.payload FROM knowledge_fts f JOIN knowledge_entities e ON e.type=f.type AND e.id=f.id WHERE knowledge_fts MATCH ? LIMIT ?',('"'+q.replace('"','""')+'"',limit)).fetchall()
            else:rows=db.execute('SELECT e.payload FROM knowledge_fts f JOIN knowledge_entities e ON e.type=f.type AND e.id=f.id WHERE instr(lower(f.name),lower(?))>0 OR instr(lower(f.summary),lower(?))>0 LIMIT ?',(q,q,limit)).fetchall()
        return [json.loads(r[0]) for r in rows]
    def link(self,p,b):
        ws=self.tools.writable(p)
        with self.lock,ws._save_lock:
            current=self.associations(p)
            if current['etag']!=b.etag:raise ConsoleError('关联记录已变化，请刷新',409)
            nodes=self.view(p)['entities'];ids={(n['type'],n['id']) for n in nodes}
            if (b.source_type,b.source_id) not in ids or (b.target_type,b.target_id) not in ids:raise ConsoleError('对象不属于当前小说或已经移除',422)
            if b.chapter_id and ('chapter',b.chapter_id) not in ids:raise ConsoleError('关联章节不属于当前小说',422)
            if b.status=='AUTHOR_CONFIRMED' and not b.confirm:raise ConsoleError('请明确确认关联；不会修改 Canon 或 State',409)
            row=b.model_dump(exclude={'etag','confirm'});row.update(id=uid('relation'),created_at=now(),created_by='AUTHOR' if b.status=='AUTHOR_CONFIRMED' else 'PROPOSAL',derived=False)
            checkpoint(ws.root,'bible/relations.json','PRE_RELATION');write(safe(ws.root,'bible/relations.json'),{'relations':[*current['relations'],row]});return row
    def unlink(self,p,id,etag):
        ws=self.tools.writable(p)
        with self.lock,ws._save_lock:
            current=self.associations(p)
            if current['etag']!=etag:raise ConsoleError('关联记录已变化，请刷新',409)
            if not any(r['id']==id for r in current['relations']):raise ConsoleError('仅可删除作者新增关联；来源数据需在原页面编辑',409)
            checkpoint(ws.root,'bible/relations.json','PRE_UNLINK');write(safe(ws.root,'bible/relations.json'),{'relations':[r for r in current['relations'] if r['id']!=id]});return {'removed':True,'entities_deleted':False}
    def anchor(self,p,b):
        ws=self.tools.writable(p)
        with self.lock,ws._save_lock:
            doc=self.tools.doc(p,b.path);text=normalized(doc)
            if doc['etag']!=b.document_revision or b.end<=b.start or utf16_slice(text,b.start,b.end)!=b.selected_text:raise ConsoleError('正文版本或选区已变化，请保存并重新选中',409)
            if not any(n['type']==b.target_type and n['id']==b.target_id for n in self.view(p)['entities']):raise ConsoleError('关联目标不属于当前小说',422)
            if any(a['located'] and a['start']==b.start and a['end']==b.end for a in self.anchors(p,b.path)):raise ConsoleError('该选区已有定位关联；请先解除旧关联，再选择正确对象',409)
            cid,_,_=self.tools.chapter(p,b.path);id=uid('anchor');index=len(text.encode('utf-16-le')[:b.start*2].decode('utf-16-le'))
            row={'id':id,'path':b.path,'chapter_id':cid,'document_revision':doc['etag'],'start':b.start,'end':b.end,'target_type':b.target_type,'target_id':b.target_id,'status':'AUTHOR_CONFIRMED','created_by':'AUTHOR','created_at':now(),'anchor':{'exact':b.selected_text,'prefix':text[max(0,index-32):index],'suffix':text[index+len(b.selected_text):index+len(b.selected_text)+32],'text_hash':digest(text.encode())}}
            # Existing explicit anchor revisions protect concurrent re-location.
            if b.etag:raise ConsoleError('新关联不需要旧版本；重新定位请先移除旧关联',409)
            write(safe(ws.root,'metadata/studio/entity-anchors/'+id+'.json'),row);return row

def knowledge_routes(service):
    router=APIRouter(prefix='/api/projects/{p}/knowledge')
    @router.get('')
    def view(p:str,q:str='',type:str=''):return service.view(p,q[:200],type)
    @router.get('/entity')
    def entity(p:str,type:str,id:str):return service.view(p,type=type,id=id)
    @router.post('/reindex')
    def reindex(p:str):service.refresh(p,True);return {'rebuilt':True}
    @router.post('/relations')
    def link(p:str,b:LinkRequest):return service.link(p,b)
    @router.delete('/relations/{id}')
    def unlink(p:str,id:str,etag:str):return service.unlink(p,id,etag)
    @router.get('/anchors')
    def anchors(p:str,path:str):service.tools.doc(p,path);return service.anchors(p,path)
    @router.post('/anchors')
    def anchor(p:str,b:AnchorRequest):return service.anchor(p,b)
    @router.delete('/anchors/{id}')
    def unanchor(p:str,id:str,etag:str):
        ws=service.tools.writable(p)
        with service.lock,ws._save_lock:
            rows=service.anchors(p);row=next((r for r in rows if r['id']==id),None)
            if not row or row['etag']!=etag:raise ConsoleError('定位关联已变化，请刷新',409)
            f=safe(ws.root,'metadata/studio/entity-anchors/'+id+'.json');checkpoint(ws.root,f.relative_to(ws.root).as_posix(),'PRE_UNLINK');f.unlink();return {'removed':True}
    return router
