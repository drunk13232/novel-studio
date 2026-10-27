"""Local, rough narrative signals over explicitly selected manuscript versions.

This is not a sentiment model or literary score. Only author metadata is written;
plans and missing signal evidence never become demonstrated narrative emotion.
"""
import json, re, time
from app.errors import ConsoleError
from app.library.storage import digest, now, safe, checkpoint
from app.projects.writing_config import writing
from app.studio_tools import normalized, utf16_index

METHOD='lexical-dialogue-signals-1'
MAX_RUN_CHARACTERS=20_000_000
MAX_RUN_SECONDS=45
LEXICONS={
 'conflict':['危险','威胁','追赶','逃跑','枪声','鲜血','死亡','争吵','崩溃','惊恐','搏斗','杀死','爆炸','冲突','danger','threat','escape','fight','attack','scream','blood','explosion'],
 'calm':['平静','安静','宁静','轻声','休息','微笑','从容','calm','quiet','gentle','peaceful'],
 'positive':['喜悦','快乐','欣喜','温暖','希望','幸福','庆幸','微笑','happy','joy','hope','delight'],
 'negative':['悲伤','恐惧','绝望','愤怒','痛苦','失落','哭泣','惊恐','sad','fear','despair','anger','grief']}
PATTERNS={key:re.compile('|'.join(r'\b'+re.escape(word)+r'\b' if word.isascii() else re.escape(word) for word in words),re.I) for key,words in LEXICONS.items()}


def fingerprint(value):
    return digest(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())


def signals(text, offset=0, whole=None):
    """Small transparent lexicons + existing dialogue measurement, no classifier."""
    from .text_statistics import quoted,HAN
    whole=text if whole is None else whole
    matches={key:list(pattern.finditer(text)) for key,pattern in PATTERNS.items()}
    counts={key:len(values) for key,values in matches.items()}
    spans,_=quoted(text);total=len(HAN.findall(text));dialogue=round(sum(len(HAN.findall(text[a:b])) for a,b in spans)/max(1,total),4)
    marker_count=sum(counts.values())
    if not marker_count and not dialogue:
        return {'tension':None,'emotion':None,'counts':counts,'dialogue_ratio':dialogue,'evidence':[],'status':'INSUFFICIENT_SIGNALS'}
    density=1000/max(100,len(text))
    tension=round(min(10,max(0,counts['conflict']*density*.9 + dialogue*2 - counts['calm']*density*.25)),2)
    emotion=round(5+5*(counts['positive']-counts['negative'])/(counts['positive']+counts['negative']+2),2) if counts['positive']+counts['negative'] else None
    candidates=[*[(match,'conflict') for match in matches['conflict']],*[(match,'emotion') for match in matches['negative']+matches['positive']],*[(match,'calm') for match in matches['calm']]]
    evidence=[];seen=set()
    for match,kind in candidates:
        start=max(0,offset+match.start()-35);end=min(len(whole),offset+match.end()+35)
        if (start,end) in seen:continue
        seen.add((start,end));evidence.append({'quote':whole[start:end],'kind':kind,'start':utf16_index(whole,start),'end':utf16_index(whole,end)})
        if len(evidence)>=3:break
    if not evidence and dialogue:
        match=re.search(r'[“「\"]([^”」\"\n]{1,200})[”」\"]',text)
        if match:
            start=offset+match.start();end=offset+match.end()
            evidence=[{'quote':whole[start:end],'kind':'dialogue','start':utf16_index(whole,start),'end':utf16_index(whole,end)}]
    if not evidence:return {'tension':None,'emotion':None,'counts':counts,'dialogue_ratio':dialogue,'evidence':[],'status':'INSUFFICIENT_SIGNALS'}
    return {'tension':tension,'emotion':emotion,'counts':counts,'dialogue_ratio':dialogue,'evidence':evidence,'status':'ROUGH_LOCAL_SIGNALS'}


def current_record(record,stamp,path,series_hash,legacy_hash):
    return bool(record and record.get('path')==path and record.get('stamp')==stamp and record.get('method')==METHOD and not record.get('retryable') and (record.get('series_spec_hash')==series_hash if record.get('series_spec_hash') else record.get('spec_hash')==legacy_hash))


class NarrativeCurve:
    def __init__(self,tools,matrix):self.tools=tools;self.matrix=matrix
    def catalog(self,p):
        if writing(self.tools.registry.get(p))['form']=='anthology':return [],'ANTHOLOGY_SELECT_MEMBER'
        try:catalog=self.tools.registry.book_center.catalog(p,include_auxiliary=False,include_text_counts=False)
        except ConsoleError as error:
            if error.status==409:return [],'AMBIGUOUS_CHAPTER_NUMBERS'
            raise
        return [{**{k:chapter.get(k) for k in ['id','number','title','volume','kind']},'position':index,'path':chapter.get('final') or chapter.get('path') or chapter.get('draft') or ''} for index,chapter in enumerate(catalog['chapters'])],None
    def stamp(self,p,path):
        if not path:return None
        file=safe(self.tools.root(p),path)
        if not file.is_file():return None
        value=file.stat();return [value.st_mtime_ns,value.st_ctime_ns,value.st_size]
    def specs(self,p):
        board=self.matrix.series(p) if hasattr(self.matrix,'series') else self.matrix.get(p)
        characters=[{'id':'character:'+id,'name':name,'kind':'character','character_id':id} for id,name in board['characters'].items()]
        tracks=[{'id':'track:'+track['id'],'name':track['name'],'kind':'track','track':track} for track in board['tracks']+board['derived_tracks']]
        return board,[{'id':'book','name':'book','kind':'book'},*characters,*tracks]
    def index(self,p):
        chapters,note=self.catalog(p);_,specs=self.specs(p);pref=self.tools.preference(p,'narrative-curve');value=pref['value'];cache=value.get('points',{});overrides=value.get('overrides',{});points=[]
        active=set(value.get('series',['book']))|{'book'};active_hash=fingerprint([spec for spec in specs if spec['id'] in active]);spec_hashes={spec['id']:fingerprint(spec) for spec in specs};flat_count=value.get('flat_count',3);flat_threshold=value.get('flat_threshold',3)
        for spec in specs:
            if spec['id'] not in active:continue
            for chapter in chapters:
                key=chapter['id']+'|'+spec['id'];record=cache.get(key,{})
                current=current_record(record,self.stamp(p,chapter['path']),chapter['path'],spec_hashes[spec['id']],active_hash)
                override=overrides.get(key,{})
                override_current=bool(chapter['path'] and override and override.get('revision','')==record.get('revision','') and current)
                tension=record.get('tension') if current else None;emotion=record.get('emotion') if current else None
                if override_current:
                    if override.get('tension') is not None:tension=override['tension']
                    if override.get('emotion') is not None:emotion=override['emotion']
                evidence=[{**item,'path':chapter['path'],'document_revision':record.get('revision',''),'current':current} for item in record.get('evidence',[])]
                points.append({'chapter_id':chapter['id'],'series_id':spec['id'],'tension':tension,'emotion':emotion,'local_tension':record.get('tension'),'local_emotion':record.get('emotion'),'status':record.get('status','NOT_ANALYZED') if current or record.get('retryable') else 'SOURCE_CHANGED' if record else 'NOT_ANALYZED','revision':record.get('revision',''),'source_current':current,'override':override or None,'override_current':override_current,'evidence':evidence,'counts':record.get('counts',{}),'dialogue_ratio':record.get('dialogue_ratio')})
        spans=[];by_id={chapter['id']:chapter for chapter in chapters}
        for spec in specs:
            if spec['id'] not in active:continue
            pending=[]
            for point in [point for point in points if point['series_id']==spec['id']]:
                chapter=by_id[point['chapter_id']]
                qualifies=point['tension'] is not None and point['tension']<flat_threshold
                if pending and chapter['position']!=pending[-1]['position']+1:
                    if len(pending)>=flat_count:spans.append({'series_id':spec['id'],'chapter_ids':[c['id'] for c in pending]})
                    pending=[]
                if qualifies:pending.append(chapter)
                else:
                    if len(pending)>=flat_count:spans.append({'series_id':spec['id'],'chapter_ids':[c['id'] for c in pending]})
                    pending=[]
            if len(pending)>=flat_count:spans.append({'series_id':spec['id'],'chapter_ids':[c['id'] for c in pending]})
        book_points=[point for point in points if point['series_id']=='book']
        coverage={'chapters':len(chapters),'known_tension':sum(point['tension'] is not None for point in book_points),'unknown_tension':sum(point['tension'] is None for point in book_points)}
        return {'coverage':coverage,'etag':pref['etag'],'chapters':chapters,'series':[{k:v for k,v in spec.items() if k!='track'} for spec in specs],'active_series':[spec['id'] for spec in specs if spec['id'] in active],'points':points,'flat_spans':spans,'flat_count':flat_count,'flat_threshold':flat_threshold,'method':METHOD,'limitations':['LEXICAL_CUES_NOT_SEMANTIC_EMOTION','DIALOGUE_DENSITY_NOT_CONFLICT_PROOF','FLATNESS_NOT_LITERARY_ERROR'],'availability_note':note,'last_run':value.get('last_run'),'canon_changed':False}
    def analyze(self,p,b):
        ws=self.tools.writable(p)
        with self.tools.lock,ws._save_lock:
            chapters,note=self.catalog(p)
            if note:raise ConsoleError('合集请进入具体篇目；章号歧义请先整理目录',422)
            if len(b.chapter_ids)!=len(set(b.chapter_ids)):raise ConsoleError('分析章节不能重复',422)
            chosen=chapters if b.whole_book else [c for c in chapters if c['id'] in b.chapter_ids]
            if not b.whole_book and len(chosen)!=len(b.chapter_ids) or not chosen:raise ConsoleError('请选择当前作品的章节',422)
            if len(chosen)>1000:raise ConsoleError('本次最多分析 1000 章，请缩小选定范围',413)
            _,specs=self.specs(p);selected={'book',*['character:'+id for id in b.character_ids],*['track:'+id for id in b.track_ids]}
            if selected-{spec['id'] for spec in specs}:raise ConsoleError('角色或剧情线不属于当前作品',422)
            specs=[spec for spec in specs if spec['id'] in selected]
            if len(chosen)*len(specs)>6000:raise ConsoleError('本次曲线点过多，请减少叠加线或按卷分析',413)
            pref=self.tools.preference(p,'narrative-curve');value=pref['value'];cache=value.setdefault('points',{});spec_hash=fingerprint(specs);spec_hashes={spec['id']:fingerprint(spec) for spec in specs}
            started=time.monotonic();input_characters=0;stopped_reason='';processed=[];unprocessed=[]
            for chapter in chosen:
                stamp=self.stamp(p,chapter['path'])
                if all(current_record(cache.get(chapter['id']+'|'+spec['id'],{}),stamp,chapter['path'],spec_hashes[spec['id']],spec_hash) for spec in specs):
                    processed.append(chapter['id']);continue
                revision='';body='';status='UNWRITTEN'
                if time.monotonic()-started>=MAX_RUN_SECONDS:stopped_reason='RUN_TIME_BUDGET_REACHED'
                if stopped_reason:status=stopped_reason
                elif chapter['path']:
                    try:
                        # The catalog already validated this project's stable chapter ID and
                        # generated manuscript path. Reuse Workspace.content's bounded,
                        # safe read rather than re-scan every chapter card via doc().
                        doc=ws.content(chapter['path']);revision=doc['etag'];body=normalized(doc)
                        if input_characters+len(body)>MAX_RUN_CHARACTERS:stopped_reason='RUN_INPUT_BUDGET_REACHED';status=stopped_reason;body=''
                        else:input_characters+=len(body);status='EMPTY_MANUSCRIPT' if not body.strip() else 'TOO_LARGE' if len(body)>200000 else ''
                    except (ConsoleError,OSError,UnicodeError):status='UNREADABLE_MANUSCRIPT'
                for spec in specs:
                    point={'tension':None,'emotion':None,'evidence':[],'counts':{},'dialogue_ratio':None,'status':status}
                    if not status:
                        from app.book_center import prose
                        content=prose(body);content_offset=len(body)-len(content)
                        if spec['kind']=='book':point=signals(content,content_offset,body)
                        elif spec['kind']=='character':
                            mentions=[match for match in re.finditer(re.escape(spec['name']),body) if match.start()>=content_offset][:20]
                            observations=[]
                            for mention in mentions:
                                start=max(content_offset,mention.start()-150);end=min(len(body),mention.end()+150);observations.append(signals(body[start:end],start,body))
                            scored=[row for row in observations if row['tension'] is not None]
                            if scored:point={**max(scored,key=lambda row:row['tension']),'status':'CHARACTER_LOCAL_CONTEXT_NOT_INNER_STATE'}
                            else:point['status']='NO_CHARACTER_SIGNAL'
                        else:
                            milestone=next((m for m in spec['track'].get('milestones',[]) if m['chapter_id']==chapter['id']),None)
                            if not milestone:point['status']='NO_TRACK_MILESTONE'
                            elif milestone.get('basis')!='TEXT_OBSERVATION':point['status']='PLANNED_NOT_MEASURED'
                            elif milestone.get('source_path')!=chapter['path'] or milestone.get('revision')!=revision or not milestone.get('quote') or milestone['quote'] not in body:point['status']='TRACK_EVIDENCE_CHANGED'
                            else:point=signals(milestone['quote'],body.index(milestone['quote']),body)
                    cache[chapter['id']+'|'+spec['id']]={**point,'path':chapter['path'],'stamp':stamp,'revision':revision,'spec_hash':spec_hash,'series_spec_hash':spec_hashes[spec['id']],'method':METHOD,'analyzed_at':now(),'retryable':bool(stopped_reason)}
                (unprocessed if stopped_reason else processed).append(chapter['id'])
            value['last_run']={'status':'INCONCLUSIVE' if unprocessed else 'COMPLETE_SELECTED_SCOPE','selected_chapter_ids':[c['id'] for c in chosen],'processed_chapter_ids':processed,'unprocessed_chapter_ids':unprocessed,'reason':stopped_reason or None,'input_characters':input_characters,'max_input_characters':MAX_RUN_CHARACTERS,'max_seconds':MAX_RUN_SECONDS,'elapsed_seconds':round(time.monotonic()-started,3)}
            value.update(version=1,series=[spec['id'] for spec in specs],updated_at=now())
            self.tools.put_pref(p,'narrative-curve',value,pref['etag'])
            return self.index(p)
    def override(self,p,b):
        ws=self.tools.writable(p)
        with self.tools.lock,ws._save_lock:
            state=self.index(p);key=b.chapter_id+'|'+b.series_id
            if state['etag']!=b.etag:raise ConsoleError('曲线标注已变化，请刷新后保存',409)
            if not any(c['id']==b.chapter_id for c in state['chapters']) or not any(s['id']==b.series_id for s in state['series']):raise ConsoleError('曲线对象不属于当前作品',422)
            point=next((point for point in state['points'] if point['chapter_id']==b.chapter_id and point['series_id']==b.series_id),{})
            chapter=next(c for c in state['chapters'] if c['id']==b.chapter_id)
            if (not chapter['path'] or not point.get('source_current')) and not b.clear:raise ConsoleError('请先本地分析以绑定当前正文版本，再保存作者标注',409)
            pref=self.tools.preference(p,'narrative-curve');value=pref['value'];overrides=value.setdefault('overrides',{})
            if b.clear:overrides.pop(key,None)
            else:overrides[key]={'tension':b.tension,'emotion':b.emotion,'note':b.note,'revision':point.get('revision',''),'basis':'AUTHOR_JUDGMENT_NOT_CANON','updated_at':now()}
            checkpoint(ws.root,'metadata/studio/narrative-curve.json','PRE_CURVE_ANNOTATION')
            self.tools.put_pref(p,'narrative-curve',value,pref['etag']);return self.index(p)
    def settings(self,p,b):
        ws=self.tools.writable(p)
        with self.tools.lock,ws._save_lock:
            pref=self.tools.preference(p,'narrative-curve')
            if pref['etag']!=b.etag:raise ConsoleError('曲线设置已变化，请刷新',409)
            self.tools.put_pref(p,'narrative-curve',{**pref['value'],'flat_count':b.flat_count,'flat_threshold':b.flat_threshold},b.etag)
            return self.index(p)
