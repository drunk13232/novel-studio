"""Thin author UI bridge to the existing semantic Final / Memory Keeper / State engine.

No alternative state store, automatic fact mapping or model-authored commit. The
last step executes the reviewed, hash-bound proposal locally after a separate
explicit author confirmation; all original workflow gates are revalidated.
"""
import re
from pydantic import Field
from app.errors import ConsoleError
from app.library.storage import write,now
from app.models.requests import TaskRequest,TaskOptions
from app.tasks.router import core_workflow
from .writing import Strict

class Source(Strict):
    path:str=Field(min_length=1,max_length=300)
    revision:str=Field(pattern=r'^[0-9a-f]{64}$')
class Stage(Source):
    story_time:str=Field(default='',max_length=80)
    stage:str=Field(pattern=r'^(final|memory|validate)$')
    proposal_id:str|None=Field(default=None,pattern=r'^[A-Za-z0-9_-]{1,100}$')
class Commit(Source):
    proposal_id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,100}$')
    proposal_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    base_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirm:bool=False

def source(s,p,path,revision):
    ws=s.tools.writable(p);doc=s.tools.doc(p,path)
    if doc['etag']!=revision:raise ConsoleError('正文已变化，请保存并重新核对状态闭环',409)
    _,chapter,_=s.tools.chapter(p,path)
    if not chapter:raise ConsoleError('正式状态闭环需要有章号的章节；单篇仍可保存事实候选',409)
    return ws,chapter,core_workflow(s.registry.engine)

def proposal(s,p,path,revision,id):
    ws,n,w=source(s,p,path,revision)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',id or ''):raise ConsoleError('请选择本章的 Proposed Diff',422)
    try:value=w.y.read(ws.resolve('state/proposed/'+id+'.yaml'))
    except (OSError,ValueError):raise ConsoleError('Proposed Diff 不存在或文件无效，请重新选择候选',409) from None
    if value.get('proposal_id')!=id or value.get('final',{}).get('chapter')!=n or value.get('final',{}).get('body_path')!=path or value.get('final',{}).get('body_sha256')!=revision:
        raise ConsoleError('Proposed Diff 与当前章节正文不匹配',409)
    return ws,n,w,value

def proposal_index(s,p,ws,w):
    """Derived in-memory metadata only; the commit path always re-reads and validates."""
    with s.lock:
        caches=getattr(s,'_state_proposal_index',{})
        key=str(ws.root.resolve());old=caches.get(key,{});current={}
        for f in (ws.root/'state/proposed').glob('*.yaml'):
            if f.name.endswith(('.review.yaml','.validation.yaml')):continue
            try:
                f=ws.resolve('state/proposed/'+f.name)
                stat=f.stat();stamp=(stat.st_mtime_ns,stat.st_size)
                cached=old.get(f.name)
                if cached and cached[0]==stamp:meta=cached[1]
                else:
                    v=w.y.read(f);final=v.get('final',{}) if isinstance(v,dict) else {}
                    id=v.get('proposal_id','') if isinstance(v,dict) else ''
                    meta=None
                    if isinstance(final,dict) and isinstance(id,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',id) and f.stem==id and v.get('project_id',p)==p:
                        meta={'id':id,'chapter':final.get('chapter'),'path':final.get('body_path'),'sha':w.digest(v)}
                current[f.name]=(stamp,meta)
            except (ValueError,OSError,KeyError,TypeError):continue
        caches.pop(key,None);caches[key]=current
        while len(caches)>4:caches.pop(next(iter(caches)))
        s._state_proposal_index=caches
        return [v for _,v in current.values() if v]

def status(s,p,path,revision,page=0,page_size=20,filter='all',snapshot=''):
    if filter not in {'all','pending','committed'} or not 0<=page<=100000 or not 1<=page_size<=50:raise ConsoleError('候选分页参数无效',422)
    ws,n,w=source(s,p,path,revision);state=w.load_state(ws.root)
    entries=state['chapter-ledger.yaml']['entries'];rows=[];final={'present':False,'valid':False}
    f=ws.resolve(f'reviews/chapter-{n}/final.yaml',allow_reviews=True)
    if f.is_file():
        final['present']=True
        try:
            v=w.y.read(f);w.verify_final(ws.root,v,check_state=not any(e['chapter']==n for e in entries))
            if v['body_path']!=path or v['body_sha256']!=revision:raise ValueError('Final witness 不是当前正文版本')
            final.update(valid=True,body_path=v['body_path'],body_sha256=v['body_sha256'])
        except (ValueError,KeyError,OSError,TypeError,IndexError) as e:final['reason']=str(e)[:400]
    committed_by={(e['proposal_id'],e['proposal_sha256']):e for e in entries}
    candidates=[]
    for meta in proposal_index(s,p,ws,w):
        if meta['chapter']!=n or meta['path']!=path:continue
        committed=committed_by.get((meta['id'],meta['sha']))
        if filter=='pending' and committed or filter=='committed' and not committed:continue
        candidates.append({**meta,'committed':committed})
    candidates.sort(key=lambda r:r['id'])
    token=w.digest([(r['id'],r['sha'],bool(r['committed'])) for r in candidates])
    if snapshot and snapshot!=token:raise ConsoleError('候选列表已变化，请刷新后重新分页',409)
    total=len(candidates)
    for meta in candidates[page*page_size:(page+1)*page_size]:
        id=meta['id'];sha=meta['sha'];committed=meta['committed']
        v=w.y.read(ws.resolve('state/proposed/'+id+'.yaml'))
        if w.digest(v)!=sha:raise ConsoleError('候选已变化，请刷新列表',409)
        row={'id':id,'proposal_sha256':sha,'base_sha256':v.get('base_sha256'),'operations':v.get('extraction',{}).get('operations',[]),'committed':committed,'valid':False,'source_current':v['final'].get('body_sha256')==revision,'author_state_time':v.get('author_state_time')}
        if not committed:
            try:
                w.candidate(ws.root,v);review=w.verify_diff_review(ws.root,v)
                receipt=w.y.read(ws.resolve('state/proposed/'+id+'.validation.yaml'))
                if receipt!={'result':'PASS','proposal_sha256':sha,'base_sha256':v['base_sha256'],'candidate_sha256':w.digest(w.candidate(ws.root,v)),'final_sha256':w.digest(v['final']),'diff_review':review}:raise ValueError('Validation receipt 缺失或过期')
                row['valid']=True
            except (ValueError,KeyError,OSError,TypeError,IndexError) as e:row['reason']=str(e)[:400]
        rows.append(row)
    return {'project_id':p,'path':path,'revision':revision,'chapter':n,'current_chapter':state['current-story-state.yaml']['project']['current_chapter'],'current_story_time':state['current-story-state.yaml']['project'].get('story_date'),'final':final,'proposals':rows,'pagination':{'page':page,'page_size':page_size,'total':total,'has_more':(page+1)*page_size<total,'filter':filter,'snapshot':token},'state_sha256':w.digest(state),'semantic_review_required':True,'tasks':[t.public() for t in list(s.manager(p).tasks.values()) if t.request.chapter==n and t.request.type in {'final_check','memory_extract','state_validate'}][-8:]}

def start(s,p,b):
    ws,n,w=source(s,p,b.path,b.revision)
    if any(e['chapter']==n for e in w.load_state(ws.root)['chapter-ledger.yaml']['entries']):raise ConsoleError('本章已提交；历史 Final 和 Memory 保持不变，请使用独立修订流程',409)
    opts=TaskOptions(read_only=False,resume=False,timeout_seconds=600)
    if b.stage!='final':
        try:
            final=w.y.read(ws.resolve(f'reviews/chapter-{n}/final.yaml',allow_reviews=True));w.verify_final(ws.root,final)
        except (ValueError,KeyError,OSError,TypeError,IndexError) as e:raise ConsoleError('请先完成当前版本的语义 Final：'+str(e),409) from None
        if final['body_path']!=b.path or final['body_sha256']!=b.revision:raise ConsoleError('Final witness 不是当前正文版本',409)
    if b.stage=='validate':
        proposal(s,p,b.path,b.revision,b.proposal_id);opts.proposal_path='state/proposed/'+b.proposal_id+'.yaml'
    from .state_tasks import prepare
    return prepare(s,p,b.path,b.revision,b.stage,b.proposal_id,story_time=b.story_time).public()


def commit(s,p,b):
    if not b.confirm:raise ConsoleError('State Commit 必须独立、明确确认当前 Diff',409)
    ws=s.tools.writable(p)
    with s.tools.lock,s.lock,ws._save_lock:
        ws,n,w,v=proposal(s,p,b.path,b.revision,b.proposal_id)
        if w.digest(v)!=b.proposal_sha256 or v['base_sha256']!=b.base_sha256:raise ConsoleError('确认对象已变化，请重新查看 Diff',409)
        try:
            receipt=w.y.read(ws.resolve('state/proposed/'+b.proposal_id+'.validation.yaml'))
            result=w.commit(ws.root,v,receipt)
        except (ValueError,KeyError,OSError,TypeError,IndexError) as e:raise ConsoleError('State Commit 未执行或已回滚：'+str(e),409) from None
        write(ws.resolve(f'reviews/chapter-{n}/author-state-commit-{b.proposal_id}.json',allow_reviews=True),{'at':now(),'project_id':p,'chapter':n,'proposal_id':b.proposal_id,'proposal_sha256':b.proposal_sha256,'base_sha256':b.base_sha256,'confirmation':'EXPLICIT_AUTHOR_CONFIRMATION','result':result})
        return {**result,'workflow':status(s,p,b.path,b.revision)}

def install_routes(router,s):
    @router.get('/state-workflow')
    def get(p:str,path:str,revision:str,page:int=0,page_size:int=20,filter:str='all',snapshot:str=''):return status(s,p,path,revision,page,page_size,filter,snapshot)
    @router.post('/state-workflow/stage')
    async def stage(p:str,b:Stage):return start(s,p,b)
    @router.post('/state-workflow/commit')
    def confirm_commit(p:str,b:Commit):return commit(s,p,b)
