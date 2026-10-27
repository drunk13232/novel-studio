"""Bounded local observations in an existing frozen evaluation, never grades."""
import re
from app.errors import ConsoleError
from app.library.storage import safe,read,write,now
from .text_statistics import measure

def statistics(service,p,id):
    row=service.raw(p,id)
    if not service.current(p,row,True)['is_current']:raise ConsoleError('正文已变化，请为新版本建立审核后再做文风比较',409)
    file=safe(service.root(p),id+'/local-statistics.json');saved=read(file,{'snapshot':row['snapshot_sha256'],'chapters':[]})
    if saved['snapshot']!=row['snapshot_sha256']:raise ConsoleError('统计版本不匹配',409)
    done={c['source_id'] for c in saved['chapters']};total=0;count=0
    for src in row['source_manifest']:
        if src['source_id'] in done:continue
        if count>=20 or total>=300000:break
        count+=1;s=service.source(p,row,src['source_id']);body=s['body'];total+=len(body)
        data={'source_id':s['source_id'],'path':s['path'],'revision':s['revision'],'number':s['number'],'title':s['title']}
        if s.get('error') or len(body)>50000:data.update(status='UNVERIFIED',reason='UNREADABLE_OR_OVER_50000_CHARACTERS')
        else:
            v=measure(body);data.update(status='COMPLETE',summary={k:v[k] for k in ['han','sentences','mean_sentence_han','dialogue_ratio','mean_paragraph_han','unclosed_quote']},repeated_expressions=v['repeated_expressions'][:5],sentences=[m.group() for m in re.finditer(r'[^。！？!?\n]{6,100}[。！？!?]',body)][:160])
        saved['chapters'].append(data)
    done={c['source_id'] for c in saved['chapters']};saved.update(updated_at=now(),total_sources=row['source_count'],processed_sources=len(done),status='FULL_COVERAGE' if len(done)==row['source_count'] and all(c['status']=='COMPLETE' for c in saved['chapters']) else 'PARTIAL_COVERAGE',authority='DESCRIPTIVE_LOCAL_OBSERVATIONS_NOT_LITERARY_ERRORS')
    groups={}
    for c in saved['chapters']:
        for sentence in set(c.get('sentences',[])):groups.setdefault(sentence,[]).append({'source_id':c['source_id'],'path':c['path'],'revision':c['revision']})
    saved['cross_chapter_repetitions']=[{'quote':q,'sources':v[:20],'source_count':len(v)} for q,v in sorted(groups.items(),key=lambda kv:-len(kv[1])) if len(v)>1][:20]
    saved['repetition_scope']='EXACT_SENTENCES_FIRST_160_PER_CHAPTER_NOT_COMPLETE_SEMANTIC_ANALYSIS'
    import json
    if len(json.dumps(saved,ensure_ascii=False))>12000000:raise ConsoleError('统计记录达到安全大小上限；已保存批次保留，请缩小章节范围',413)
    if not service.current(p,row)['is_current']:raise ConsoleError('统计期间原文变化，未保存旧版本结果',409)
    write(file,saved)
    return {**saved,'chapters':[{k:v for k,v in c.items() if k!='sentences'} for c in saved['chapters']]}
