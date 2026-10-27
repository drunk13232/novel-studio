"""Project-local reader personas and an explicit manifest over ReviewCenter tasks.

No additional AI engine, scoring system or autonomous queue. Each execution step
uses the existing public-reader review and TaskManager; confirmation freezes the
profile, manuscript versions, exact model configuration and call limit.
"""
import json,re,threading
from app.errors import ConsoleError
from app.library.storage import safe,read,write,uid,now,checkpoint,digest
from app.studio_tools import normalized
from app.ai.controls import estimate
from .narrative_curve import fingerprint
from .reviews import Start

TERMINAL={'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}

class ReaderPersonas:
    def __init__(self,reviews,curve):self.reviews=reviews;self.tools=reviews.tools;self.curve=curve;self.lock=threading.RLock()
    def root(self,p):return safe(self.reviews.root(p),'reader-panels')
    def path(self,p,id):
        if not re.fullmatch(r'panel_[0-9a-f]{32}',id or ''):raise ConsoleError('模拟读者批次 ID 无效',422)
        return safe(self.root(p),id+'.json')
    def raw(self,p,id):
        file=self.path(p,id);row=read(file)
        if not isinstance(row,dict) or row.get('project_id')!=p or row.get('id')!=id:raise ConsoleError('模拟读者批次不属于当前作品或记录已损坏',404)
        if any(not isinstance(row.get(key),list) for key in ['profiles','sources','cells']) or any(not isinstance(row.get(key),dict) for key in ['preview','model']) or not isinstance(row.get('chunks'),int):raise ConsoleError('模拟读者批次结构损坏，请从备份恢复',422)
        if any(not isinstance(cell,dict) or not {'id','status','chunk_index','persona_id','source_ids'}<=cell.keys() for cell in row['cells']):raise ConsoleError('模拟读者执行记录损坏，请从备份恢复',422)
        return row,digest(file.read_bytes())
    def put(self,p,row):row['updated_at']=now();write(self.path(p,row['id']),row)
    def index(self,p):
        chapters,note=self.curve.catalog(p);pref=self.tools.preference(p,'reader-personas');history=[];unavailable=[]
        with self.lock:
            candidates=[]
            for file in self.root(p).glob('panel_*.json'):
                try:candidates.append((self.path(p,file.stem).stat().st_mtime_ns,file))
                except (ConsoleError,OSError):unavailable.append({'id':file.stem,'code':'PANEL_UNAVAILABLE'})
            files=[file for _,file in sorted(candidates,key=lambda pair:pair[0],reverse=True)[:100]]
            for file in files:
                try:
                    row,_=self.raw(p,file.stem)
                    # Derive current status without rewriting every historical file.
                    row=self.sync(p,row,persist=False)
                    history.append({k:row.get(k) for k in ['id','created_at','updated_at','status','whole_book','calls_started','max_calls','preview']})
                except (ConsoleError,OSError,ValueError,TypeError,AttributeError,KeyError):
                    unavailable.append({'id':file.stem,'code':'PANEL_UNAVAILABLE'})
        return {'etag':pref['etag'],'profiles':pref['value'].get('profiles',[]),'chapters':chapters,'history':sorted(history,key=lambda row:row['created_at'],reverse=True)[:100],'history_issues':unavailable,'availability_note':note,'model_simulation_not_human_data':True,'canon_changed':False}
    def save(self,p,b):
        ws=self.tools.writable(p)
        with self.tools.lock,ws._save_lock:
            pref=self.tools.preference(p,'reader-personas')
            if pref['etag']!=b.etag:raise ConsoleError('画像已变化，请刷新后保存',409)
            profiles=pref['value'].get('profiles',[]);value=b.persona.model_dump();value['name']=value['name'].strip()
            if not value['name']:raise ConsoleError('请填写画像名称',422)
            if value['id']:
                index=next((i for i,row in enumerate(profiles) if row['id']==value['id']),None)
                if index is None:raise ConsoleError('画像不属于当前作品',404)
            else:
                if len(profiles)>=100:raise ConsoleError('单个作品最多保留 100 个画像，请先整理',413)
                value['id']=uid('reader');index=None
            value.update(updated_at=now(),fictional_profile=True)
            if index is None:profiles.append(value)
            else:profiles[index]=value
            checkpoint(ws.root,'metadata/studio/reader-personas.json','PRE_READER_PERSONA')
            self.tools.put_pref(p,'reader-personas',{'version':1,'profiles':profiles},b.etag)
            return self.index(p)
    def remove(self,p,id,b):
        ws=self.tools.writable(p)
        with self.tools.lock,ws._save_lock:
            pref=self.tools.preference(p,'reader-personas');profiles=pref['value'].get('profiles',[])
            if b.confirm is not True:raise ConsoleError('请确认移除画像',409)
            if pref['etag']!=b.etag:raise ConsoleError('画像已变化，请刷新',409)
            if not any(row['id']==id for row in profiles):raise ConsoleError('画像不属于当前作品',404)
            checkpoint(ws.root,'metadata/studio/reader-personas.json','PRE_READER_PERSONA_REMOVE')
            self.tools.put_pref(p,'reader-personas',{'version':1,'profiles':[row for row in profiles if row['id']!=id]},b.etag)
            return self.index(p)
    def model(self,p,ref):
        center=self.reviews.ai_center;controls=center.controls_for(p,'review_reader',model=ref);provider,model=center.choose(p,'review_reader',controls.model)
        if provider is None:return {'ref':controls.model or 'codex','label':'Codex / '+str(controls.model or 'default'),'signature':fingerprint(controls.model_dump()),'input_price':None,'output_price':None,'currency':None,'output_reserve':controls.parameters.get('max_output_tokens') or controls.context.output_reserve}
        config={'provider':provider.provider_id,'base_url':provider.base_url,'protocol':model.protocol,'id':model.id,'parameters':model.parameters.model_dump(),'controls':controls.model_dump(),'context_length':model.context_length,'output_limit':model.output_limit,'capabilities':model.capabilities}
        return {'ref':provider.provider_id+'::'+model.id,'label':provider.display_name+' / '+(model.display_name or model.id),'signature':fingerprint(config),'input_price':model.input_price,'output_price':model.output_price,'currency':model.currency,'output_reserve':controls.parameters.get('max_output_tokens') or model.parameters.max_output_tokens or controls.context.output_reserve}
    def prepare(self,p,b):
        ws=self.tools.writable(p);index=self.index(p)
        profiles=[row for row in index['profiles'] if row['id'] in b.persona_ids]
        if len(profiles)!=len(set(b.persona_ids)) or len(b.persona_ids)!=len(set(b.persona_ids)):raise ConsoleError('请选择当前作品中不同的读者画像',422)
        chosen=list(index['chapters']) if b.whole_book else [chapter for chapter in index['chapters'] if chapter['id'] in b.chapter_ids]
        if not chosen or not b.whole_book and len(chosen)!=len(set(b.chapter_ids)):raise ConsoleError('请选择当前作品的正文范围',422)
        if len(chosen)>1000:raise ConsoleError('本次最多 1000 章，请缩小范围',413)
        model=self.model(p,b.model);sources=[];chunks=[];pending=[];characters=0
        def flush():
            nonlocal pending,characters
            if pending:chunks.append(pending);pending=[];characters=0
        for chapter in chosen:
            source={**chapter,'revision':'','length':0,'error':None}
            try:
                if not chapter['path']:source['error']='UNWRITTEN_CHAPTER';sources.append(source);flush();continue
                doc=ws.content(chapter['path']);body=normalized(doc);source.update(revision=doc['etag'],length=len(body),input_upper=estimate(json.dumps(body,ensure_ascii=False)))
                if not body.strip():source['error']='EMPTY_MANUSCRIPT'
                elif len(body)>95000:source['error']='CHAPTER_TOO_LARGE_FOR_READER_REVIEW'
            except (ConsoleError,OSError,UnicodeError):source['error']='UNREADABLE_MANUSCRIPT'
            sources.append(source)
            if source['error']:flush();continue
            if pending and (len(pending)>=8 or characters+source['length']>95000 or source['number']!=pending[-1]['number']+1):flush()
            pending.append(source);characters+=source['length']
        flush()
        calls=len(chunks)*len(profiles)
        techniques,_=self.reviews.techniques('scene_review','reader')
        # Estimate the actual selected technique/profile bytes, not a generic
        # token count or an optimistic fixed allowance for Chinese skill text.
        fixed_allowance=estimate(techniques)+6000
        profile_allowance=sum(estimate(json.dumps(profile,ensure_ascii=False)) for profile in profiles)
        input_upper=sum(source.get('input_upper',0) for source in sources if not source['error'])*len(profiles)+calls*fixed_allowance+len(chunks)*profile_allowance
        output_upper=calls*int(model['output_reserve'] or 4096)
        cost=((input_upper*model['input_price']+output_upper*model['output_price'])/1000000) if model['input_price'] is not None and model['output_price'] is not None else None
        preview={'source_count':len(sources),'readable_count':sum(not source['error'] for source in sources),'characters':sum(source['length'] for source in sources),'requests':calls,'chunks':len(chunks),'profiles':len(profiles),'input_tokens_upper_estimate':input_upper,'output_tokens_reserve':output_upper,'cost_estimate':cost,'currency':model['currency'],'max_calls':b.max_calls,'blocked':[{'id':source['id'],'title':source['title'],'error':source['error']} for source in sources if source['error']],'can_approve':bool(calls and calls<=b.max_calls),'estimate_method':'SELECTED_TEXT_JSON_TECHNIQUE_PROFILE_UTF8_BYTE_UPPER_ESTIMATE_NOT_TOKENIZER','coverage':'PARTIAL_COVERAGE' if any(source['error'] for source in sources) else 'COMPLETE_SELECTED_TEXT','semantics':'INDEPENDENT_PUBLIC_READER_CHUNKS_NOT_A_HUMAN_SURVEY_OR_FULL_MEMORY'}
        frozen={'profiles':profiles,'sources':sources,'model':model,'max_calls':b.max_calls,'whole_book':b.whole_book,'preview':preview}
        id=uid('panel');cells=[]
        for chunk_index,chunk in enumerate(chunks):
            for profile in profiles:cells.append({'id':'cell_'+str(len(cells)),'chunk_index':chunk_index,'persona_id':profile['id'],'source_ids':[source['id'] for source in chunk],'status':'PENDING','task_id':None,'review_id':None,'attempts':0})
        row={'id':id,'project_id':p,'created_at':now(),'status':'PREVIEW','approved':False,'preview_hash':fingerprint(frozen),'model':model,'profiles':profiles,'sources':sources,'chunks':len(chunks),'cells':cells,'calls_started':0,'max_calls':b.max_calls,'whole_book':b.whole_book,'preview':preview,'canon_changed':False}
        self.put(p,row);return self.get(p,id)
    def saved_report(self,p,row,cell):
        """Recover only a durable, matching public-reader report, never model text."""
        try:
            report=read(self.reviews.path(p,cell.get('review_id')),None)
            expected={source['path']:source['revision'] for source in row['sources'] if source['id'] in cell['source_ids']}
            if not isinstance(report,dict) or report.get('id')!=cell.get('review_id') or report.get('project_id')!=p:return None
            if report.get('mode')!='reader' or report.get('reader_persona',{}).get('id')!=cell['persona_id']:return None
            if not expected or {source['path']:source['revision'] for source in report.get('sources',[])}!=expected:return None
            if not isinstance(report.get('report',{}).get('summary'),str):return None
            return report
        except (ConsoleError,OSError,ValueError,TypeError,AttributeError,KeyError):return None
    def sync(self,p,row,persist=True):
        changed=False;previous_status=row['status']
        for cell in row['cells']:
            if cell['status']!='RUNNING':continue
            missing=False;restart=False
            try:
                task=self.reviews.manager(p).get(cell['task_id']);status=task.public()['status']
                restart=status=='INTERRUPTED' and getattr(task,'reason',None)=='backend_restart'
            except ConsoleError:missing=True;status='INTERRUPTED'
            if status in TERMINAL:
                report=self.saved_report(p,row,cell) if status=='SUCCEEDED' or missing or restart else None
                if report:
                    cell['status']='COMPLETED';cell.pop('last_error',None)
                    if missing or restart:cell['recovered_from_report']=True
                elif status=='SUCCEEDED':cell.update(status='FAILED',last_error='REPORT_UNAVAILABLE')
                else:cell.update(status=status,last_error='TASK_MISSING_INTERRUPTED' if missing else 'TASK_'+status)
                changed=True
                if cell['status']!='COMPLETED':row['status']='PAUSED'
        if row['cells'] and all(cell['status']=='COMPLETED' for cell in row['cells']):row['status']='COMPLETED' if row['preview']['coverage']=='COMPLETE_SELECTED_TEXT' else 'PARTIAL_COVERAGE'
        elif any(cell['status']=='RUNNING' for cell in row['cells']):row['status']='RUNNING'
        elif row['approved'] and row['status']=='RUNNING':row['status']='PAUSED'
        if (changed or previous_status!=row['status']) and persist:self.put(p,row)
        return row
    def get(self,p,id,chunk=0):
        with self.lock:
            row,_=self.raw(p,id);row=self.sync(p,row);reports=[]
            if chunk<0 or chunk>=max(1,row['chunks']):raise ConsoleError('所选评阅分段不存在，请刷新批次',422)
            for cell in row['cells']:
                if cell['chunk_index']!=chunk or cell['status']!='COMPLETED':continue
                try:reports.append({'cell_id':cell['id'],'persona_id':cell['persona_id'],'report':self.reviews.get(p,cell['review_id'])})
                except (ConsoleError,OSError,ValueError,TypeError,AttributeError,KeyError):reports.append({'cell_id':cell['id'],'persona_id':cell['persona_id'],'error':'REPORT_UNAVAILABLE'})
            return {**row,'etag':digest(self.path(p,id).read_bytes()),'reports':reports,'display_chunk':chunk,'active_task':next((self.reviews.manager(p).get(cell['task_id']).public() for cell in row['cells'] if cell['status']=='RUNNING'),None),'model_simulation_not_human_data':True}
    def approve(self,p,id,b):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            row,etag=self.raw(p,id)
            if b.confirm is not True or b.etag!=etag or b.preview_hash!=row['preview_hash']:raise ConsoleError('范围、预算或批次版本已变化，请重新预览确认',409)
            if not row['preview']['can_approve']:raise ConsoleError('请求数超出本次预算或没有可读正文，请缩小范围',422)
            if row['approved']:return self.get(p,id)
            row.update(approved=True,status='READY',approved_at=now());self.put(p,row);return self.get(p,id)
    async def next(self,p,id,b):
        ws=self.tools.writable(p);task=None
        with self.lock,self.tools.lock,ws._save_lock:
            row,etag=self.raw(p,id);row=self.sync(p,row)
            if b.confirm is not True or b.etag!=digest(self.path(p,id).read_bytes()):raise ConsoleError('批次已变化，请刷新后继续',409)
            if not row['approved']:raise ConsoleError('请先确认本次正文范围、画像和预算',409)
            if any(cell['status']=='RUNNING' for cell in row['cells']):raise ConsoleError('当前评阅尚未结束，不重复启动',409)
            if row['calls_started']>=row['max_calls']:raise ConsoleError('本次请求预算已用完，请重新建立并确认批次',409)
            cell=next((cell for cell in row['cells'] if cell['status']=='PENDING'),None)
            if cell is None:return self.get(p,id)
            if self.model(p,row['model']['ref'])['signature']!=row['model']['signature']:raise ConsoleError('模型或参数已变化，请重新预览，不会跨服务商发送',409)
            sources=[source for source in row['sources'] if source['id'] in cell['source_ids']]
            current_catalog={chapter['id']:chapter['path'] for chapter in self.curve.catalog(p)[0]}
            if any(current_catalog.get(source['id'])!=source['path'] for source in sources):raise ConsoleError('选定章节或正式稿已变化，请重新预览',409)
            for source in sources:
                if ws.content(source['path'])['etag']!=source['revision']:raise ConsoleError('目标正文已变化，请重新预览；不读取未经确认的新版本',409)
            profile=next(profile for profile in row['profiles'] if profile['id']==cell['persona_id']);profile={key:value for key,value in profile.items() if key not in {'updated_at','fictional_profile'}}
            task=self.reviews.start(p,Start(path=sources[0]['path'],mode='reader',engine='ai',reader_paths=[source['path'] for source in sources],reader_source_versions={source['path']:source['revision'] for source in sources},source_revision=sources[0]['revision'],reader_focus=profile['focus'],reader_persona=profile,model=row['model']['ref'],criteria=['Return subjective reader reactions, any evidence-supported possible abandonment point and moving passage. Do not manufacture missing reactions or literary scores.']))
            cell.update(status='RUNNING',task_id=task['id'],review_id=task['review_id'],attempts=cell['attempts']+1);row.update(status='RUNNING',calls_started=row['calls_started']+1)
            try:self.put(p,row)
            except OSError:
                await self.reviews.manager(p).cancel(task['id'])
                raise ConsoleError('批次状态无法保存，已取消本次排队任务；请检查本地存储',503) from None
            return self.get(p,id)
    def retry(self,p,id,b):
        ws=self.tools.writable(p)
        with self.lock,self.tools.lock,ws._save_lock:
            row,etag=self.raw(p,id);row=self.sync(p,row)
            if b.confirm is not True or b.etag!=digest(self.path(p,id).read_bytes()):raise ConsoleError('批次状态已变化，请刷新',409)
            cell=next((cell for cell in row['cells'] if cell['id']==b.cell_id),None)
            if not cell or cell['status'] not in {'FAILED','CANCELLED','INTERRUPTED'}:raise ConsoleError('只可由作者重试失败或取消的项目',422)
            if row['calls_started']>=row['max_calls']:raise ConsoleError('已达到确认的调用预算，不能自动扩大',409)
            cell.update(status='PENDING',task_id=None,review_id=None);cell.pop('last_error',None);cell.pop('recovered_from_report',None);row['status']='READY';self.put(p,row);return self.get(p,id)
