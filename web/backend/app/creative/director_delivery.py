"""Local delivery checks and recovery metadata over existing Director candidates.
No generated facts, model calls, manuscript writes or alternative task authority.
"""
import copy,re
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.errors import ConsoleError
from app.library.storage import read,write,digest,now
from app.studio_tools import normalized,utf16_slice,text_hash
from app.studio import body_counts

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class SceneIntent(Strict):
    entry_state:str=Field(default='',max_length=500)
    exit_state:str=Field(default='',max_length=500)
    objective:str=Field(default='',max_length=500)
    obstacle:str=Field(default='',max_length=500)
    choice:str=Field(default='',max_length=500)
    consequence:str=Field(default='',max_length=500)
class DeliveryUpdate(Strict):
    etag:str=Field(pattern=r'^[0-9a-f]{64}$')
    path:str|None=Field(default=None,max_length=300)
    candidate_id:str|None=Field(default=None,pattern=r'^[0-9a-f]{32}$')
    target_han:int|None=Field(default=None,ge=0,le=10000000)
    reason:str=Field(default='',max_length=500)

def failure(error):
    text=str(error).lower()
    code='REQUEST_FAILED';action='REVIEW_AND_RESUME'
    for match,kind,next_action in [(['workspace routing','models: request timed out','连接超时','模型目录'],'CONNECTION','CHECK_CONNECTION'),(['memory allocation','out of memory','内存分配'],'MEMORY','RELEASE_MEMORY'),(['上下文','固定资料超过预算','预留'],'CONTEXT_BUDGET','REVIEW_CONTEXT'),(['轮次','调用轮次','时间限制','时间或调用','尝试上限'],'TASK_BUDGET','REVIEW_LIMITS'),(['原文已变化','选区已变化','context changed','来源','正文已变化'],'SOURCE_CHANGED','REVIEW_SOURCES'),(['未返回正文','正文为空'],'NO_PROSE','REVIEW_RESULT'),(['超时','timed out','timeout'],'TIMEOUT','CHECK_RECEIPT'),(['已取消','已被新指令','interrupted'],'CANCELLED','MANUAL_RESUME')]:
        if any(s in text for s in match):code=kind;action=next_action;break
    return {'code':code,'next_action':action,'automatic_retry':False,'provider_fallback':False}

def task_delivery(row,candidate=None):
    counts=body_counts(row.get('draft',''));minimum=row.get('goal_han')
    matches=bool(candidate and candidate.get('candidate')==row.get('draft',''))
    adopted=bool(matches and candidate.get('status')=='ACCEPTED' and candidate.get('accepted_text',candidate.get('candidate'))==row.get('draft',''))
    pending=[{'index':i,'step_id':s.get('step_id'),'title':s['title']} for i,s in enumerate(row['plan']['steps']) if s['enabled'] and i not in row['completed']]
    return {'counts':counts,'goal_han':minimum,'length_state':'NOT_SET' if not minimum else 'REACHED' if counts['han']>=minimum else 'BELOW_TARGET','text_produced':bool(row.get('draft','').strip()),'steps_complete':not pending,'remaining_steps':pending,'candidate_staged':matches,'candidate_matches_current_draft':matches,'candidate_status':candidate.get('status') if candidate else None,'author_adopted':adopted,'literary_review':'NOT_PROVEN_BY_COMPLETION','source_validation':'AT_PREFLIGHT_AND_STAGE','candidate_only':True}

def recovery(row):
    return {'failure':row.get('failure'),'checkpoint':copy.deepcopy(row.get('resume_checkpoint')),'attempts_used':row['calls'],'attempts_remaining':max(0,row['limits']['max_calls']-row['calls']),'seconds_remaining':None if row.get('timing_unknown') else max(0,round(row['limits']['seconds']-row['seconds_used'],1)),'budget_confirmation_required':bool(row.get('timing_unknown')),'retained_han':body_counts(row.get('draft',''))['han'],'can_resume':not row.get('active_task') and row['status']!='TERMINATED' and any(s['enabled'] and i not in row['completed'] for i,s in enumerate(row['plan']['steps'])),'automatic_resume':False}

def checkpoint(row,index,reason):
    step=row['plan']['steps'][index] if index is not None and index<len(row['plan']['steps']) else {}
    return {'step_id':step.get('step_id'),'step_index':index,'retained_characters':len(row.get('draft','')),'retained_sha256':text_hash(row.get('draft','')),'source_revision':row['revision'],'completed_steps':list(row['completed']),'reason':reason,'at':now()}

def selected_text(candidate,view):
    draft=view.get('draft')
    if draft is not None:return draft['text']
    variants=candidate.get('variants') or [{'candidate':candidate['candidate']}]
    return variants[view['variant']]['candidate']

def selected_view(service,p,candidate):
    return service.tools.draft_view(p,candidate['id'],variant=(candidate.get('author_draft') or {}).get('active_variant',0))

def selection_hash(candidate,view):
    import json
    return digest(json.dumps({k:candidate.get(k) for k in ['id','path','document_revision','start','end','selected_text','status']}|{'text':selected_text(candidate,view),'variant':view['variant']},ensure_ascii=False,sort_keys=True).encode())

def _path(service,p):return service.tools.local(p,'director-delivery.json')
def _base(service,p):
    service.tools.writable(p)
    default=(service.tools.registry.get(p).get('writing') or {}).get('target_characters') or 0
    path=_path(service,p);record=read(path,{'version':1,'target_han':int(default),'selected':{},'goal_versions':[]})
    return record,digest(path.read_bytes()) if path.exists() else digest(b'EMPTY_DIRECTOR_DELIVERY')

def project_delivery(service,p):
    record,etag=_base(service,p);rows=[];present=set();manuscript_total=0;selected_total=0;total=0;invalid=[]
    chapters=service.tools.registry.studio_workspace(p)['chapters'];paths={c.get('path') for c in chapters};selections={};mapped=set()
    for key,entry in record['selected'].items():
        destination=key
        if key not in paths:
            try:
                adopted=service.tools.candidate(p,entry['id'])
                if adopted.get('status')=='ACCEPTED' and adopted.get('saved_path') in paths:destination=adopted['saved_path'];mapped.add(key)
            except ConsoleError:pass
        if destination not in selections:selections[destination]=(key,entry)
    for chapter in chapters:
        path=chapter.get('path')
        if not path:continue
        present.add(path);selection_key,entry=selections.get(path,(path,None));row={'path':path,'number':chapter.get('number'),'title':chapter.get('title'),'chapter_id':chapter.get('card_id'),'candidate_id':entry.get('id') if entry else None,'basis':'MANUSCRIPT','selection_path':selection_key}
        try:
            doc=service.tools.doc(p,path);original=normalized(doc);count=body_counts(original)['han'];row['manuscript_han']=count;manuscript_total+=count
            if entry:
                candidate=service.tools.candidate(p,entry['id'])
                if candidate['path']!=path and not (candidate.get('status')=='ACCEPTED' and candidate.get('saved_path')==path):raise ConsoleError('候选章节不匹配',409)
                if candidate['status']=='ACCEPTED':row['basis']='ADOPTED_MANUSCRIPT'
                else:
                    if candidate['status']!='PROPOSED' or candidate['document_revision']!=doc['etag']:raise ConsoleError('候选来源已变化或已经处理',409)
                    view=selected_view(service,p,candidate)
                    if selection_hash(candidate,view)!=entry['fingerprint']:raise ConsoleError('所选候选已被编辑，请重新选择当前版本',409)
                    if utf16_slice(original,candidate['start'],candidate['end'])!=candidate['selected_text']:raise ConsoleError('候选选区已变化',409)
                    value=original.encode('utf-16-le');result=value[:candidate['start']*2].decode('utf-16-le')+selected_text(candidate,view)+value[candidate['end']*2:].decode('utf-16-le')
                    if candidate['start']==candidate['end']==0 and original.strip() and body_counts(original)['characters']==0:row['format_warning']='INSERTION_BEFORE_CHAPTER_HEADER'
                    count=body_counts(result)['han'];selected_total+=count;row['basis']='SELECTED_UNADOPTED_CANDIDATE'
            row['delivery_han']=count;total+=count
        except (ConsoleError,KeyError,ValueError) as error:row.update(basis='NEEDS_REVIEW',error=str(error)[:250],delivery_han=None);invalid.append(path)
        rows.append(row)
    for path in record['selected']:
        if path not in present and path not in mapped:invalid.append(path)
    target=record['target_han'];format_warnings=[{'path':r['path'],'code':r['format_warning']} for r in rows if r.get('format_warning')];state='PARTIAL_COVERAGE' if invalid else 'NEEDS_FORMAT_REVIEW' if format_warnings else 'NOT_SET' if not target else 'DRAFT_TARGET_REACHED' if total>=target else 'BELOW_TARGET'
    return {'etag':etag,'project_id':p,'target_han':target,'manuscript_han':manuscript_total,'selected_candidate_han':selected_total,'delivery_han':total,'remaining_han':max(0,target-total),'state':state,'invalid_paths':invalid,'format_warnings':format_warnings,'orphaned_selections':[{'path':path,'candidate_id':record['selected'][path]['id']} for path in record['selected'] if path not in present and path not in mapped],'chapters':rows,'goal_versions':record['goal_versions'],'statistics_changed':False,'canon_changed':False,'author_adoption_required':True,'literary_quality':'NOT_PROVEN_BY_LENGTH'}

def update_delivery(service,p,body):
    with service.lock:
        record,etag=_base(service,p)
        if body.etag!=etag:raise ConsoleError('交付检查已更新，请刷新后重试',409)
        if body.target_han is not None and body.target_han!=record['target_han']:
            if not body.reason.strip():raise ConsoleError('修改目标需填写作者说明，不能在失败后自动放宽标准',422)
            record['goal_versions']=(record['goal_versions']+[{'target_han':record['target_han'],'at':now(),'reason':body.reason}])[-30:];record['target_han']=body.target_han
        if body.path:
            paths={c.get('path') for c in service.tools.registry.studio_workspace(p)['chapters']}
            if body.path not in paths and not (not body.candidate_id and body.path in record['selected']):raise ConsoleError('请选择当前作品的实际章节路径',409)
            if body.candidate_id:
                candidate=service.tools.candidate(p,body.candidate_id);doc=service.tools.doc(p,body.path)
                if candidate['path']!=body.path or candidate['status']!='PROPOSED' or candidate['document_revision']!=doc['etag']:raise ConsoleError('候选不属于此章节、已处理或源版本变化',409)
                view=selected_view(service,p,candidate)
                record['selected'][body.path]={'id':body.candidate_id,'fingerprint':selection_hash(candidate,view),'at':now()}
            else:record['selected'].pop(body.path,None)
        write(_path(service,p),record);return project_delivery(service,p)
