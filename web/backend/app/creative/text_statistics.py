"""Bounded, deterministic Chinese manuscript measurements within ReviewCenter.
Jieba is loaded on demand. No readability score, literary verdict or speaker guess.
"""
import json,re,threading
from collections import Counter,defaultdict
from functools import lru_cache
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.library.storage import safe,read,write,uid,now
from app.studio_tools import normalized,text_hash,utf16_index
HAN=re.compile(r'[\u3400-\u9fff\U00020000-\U0002fa1f]')
STOP=set('我们 你们 他们 她们 自己 这个 那个 一个 什么 怎么 已经 没有 不是 还是 但是 因为 所以 然后 时候 这里 那里 可以 不能 就是 一下 一些 一样 只是 这样 那样'.split())
SEGMENT_LOCK=threading.RLock()
@lru_cache(maxsize=1)
def tokenizer():
    import jieba
    result=jieba.Tokenizer();result.initialize();return result
class Request(BaseModel):
    model_config=ConfigDict(extra='forbid')
    path:str=Field(min_length=1,max_length=300)
    related_paths:list[str]=Field(default_factory=list,max_length=20)
    compare_id:str|None=Field(default=None,max_length=80)

def location(body,start,end):return {'start':utf16_index(body,start),'end':utf16_index(body,end),'line':body.count('\n',0,start)+1,'exact':body[start:end],'prefix':body[max(0,start-24):start],'suffix':body[end:end+24]}
def quoted(body):
    stack=[];spans=[];pairs={'“':'”','「':'」','『':'』'}
    for i,c in enumerate(body):
        if c in pairs:stack.append((pairs[c],i))
        elif c=='"':
            if stack and stack[-1][0]=='"':
                _,a=stack.pop()
                if not stack:spans.append((a+1,i))
            elif not stack:stack.append(('"',i))
        elif stack and c==stack[-1][0]:
            _,a=stack.pop()
            if not stack:spans.append((a+1,i))
    return spans,bool(stack)

def measure(body,names=()):
    original=body
    # Match the existing editor's chapter-title boundary while retaining exact
    # original code-point / UTF-16 locations and line numbers for every finding.
    title=re.match(r'^(?:#{1,6}\s+[^\n]+|第[一二三四五六七八九十百千零〇\d]+章[^\n]*)(?:\n+|$)',body)
    excluded=title.end() if title else 0
    if excluded:body=''.join('\n' if c=='\n' else ' ' for c in body[:excluded])+body[excluded:]
    paragraphs=[m for m in re.finditer(r'[^\n]+',body) if m[0].strip()]
    sentences=[m for m in re.finditer(r'[^。！？!?\n]+[。！？!?]*',body) if HAN.search(m[0]) or re.search(r'\w',m[0])]
    spans,unclosed=quoted(body);total=len(HAN.findall(body));dialogue=sum(len(HAN.findall(body[a:b])) for a,b in spans)
    lengths=[len(HAN.findall(m[0])) for m in sentences]
    para_rows=[]
    for i,m in enumerate(paragraphs):
        inside=sum(len(HAN.findall(body[max(a,m.start()):min(b,m.end())])) for a,b in spans if a<m.end() and b>m.start())
        para_rows.append({'paragraph':i+1,'han':len(HAN.findall(m[0])),'dialogue_han':inside,'location':location(original,m.start(),m.end())})
    counts=Counter();positions=defaultdict(list);phrases=defaultdict(list)
    with SEGMENT_LOCK:tokens=list(tokenizer().tokenize(body,HMM=False))
    for word,a,b in tokens:
        word=word.strip()
        if len(word)<2 or word in STOP or not HAN.search(word):continue
        counts[word]+=1
        if len(positions[word])<12:positions[word].append(location(original,a,b))
    # Adjacent exact 4-10 Chinese-character expressions, paragraph confined.
    # A bounded sliding window surfaces repetition, not semantic equivalence.
    for m in paragraphs:
        for run in re.finditer(r'[\u3400-\u9fff]{4,}',m[0]):
            text=run[0]
            for width in (4,6,8,10):
                for i in range(0,max(0,len(text)-width+1)):
                    phrase=text[i:i+width]
                    if len(phrases[phrase])<20:phrases[phrase].append(m.start()+run.start()+i)
    repeated=[];accepted=[]
    for phrase,ps in sorted(phrases.items(),key=lambda x:(-len(x[1]),-len(x[0]),x[0])):
        if len(ps)<3:continue
        if any(phrase in longer and len(ps)==n for longer,n in accepted):continue
        accepted.append((phrase,len(ps)));repeated.append({'text':phrase,'count':len(ps),'count_capped':len(ps)==20,'locations':[location(original,a,a+len(phrase)) for a in ps[:8]]})
        if len(repeated)>=20:break
    starts=defaultdict(list)
    for m in sentences:
        stripped=re.sub(r'^[\s“”「」『』"，,]+','',m[0]);prefix=stripped[:3]
        if len(prefix)==3 and HAN.fullmatch(prefix[0]) and HAN.fullmatch(prefix[-1]):
            a=m.start()+m[0].find(stripped);starts[prefix].append(location(original,a,a+3))
    characters=[]
    for name,ids in names:
        found=[location(original,m.start(),m.end()) for m in re.finditer(re.escape(name),body)]
        if found:characters.append({'name':name,'ids':ids,'count':len(found),'ambiguous':len(ids)>1,'locations':found[:12],'interpretation':'NAME_MENTION_NOT_SCENE_PRESENCE'})
    separators=list(re.finditer(r'(?m)^\s*(?:\*\s*\*\s*\*|---+|#{1,4}\s+[^\n]+)\s*$',body));scene_starts=[0]+[m.end() for m in separators];scene_ends=[m.start() for m in separators]+[len(body)]
    scenes=[{'index':i+1,'han':len(HAN.findall(body[a:b])),'location':location(original,a,b)} for i,(a,b) in enumerate(zip(scene_starts,scene_ends)) if body[a:b].strip()]
    bins=[('1–10',1,10),('11–20',11,20),('21–40',21,40),('41–60',41,60),('61+',61,10**9)]
    return {'han':total,'characters':len(original)-excluded,'chapter_heading_excluded':bool(excluded),'paragraphs':len(paragraphs),'sentences':len(sentences),'mean_sentence_han':round(sum(lengths)/max(1,len(lengths)),2),'mean_paragraph_han':round(total/max(1,len(paragraphs)),2),'sentence_bins':[{'label':label,'count':sum(lo<=n<=hi for n in lengths)} for label,lo,hi in bins],'dialogue_han':dialogue,'dialogue_ratio':round(dialogue/max(1,total),4),'unclosed_quote':unclosed,'paragraph_distribution':para_rows[:1000],'sentence_distribution':[{'index':i+1,'han':lengths[i],'location':location(original,m.start(),m.end())} for i,m in enumerate(sentences[:1000])],'repeated_words':[{'text':w,'count':n,'locations':positions[w]} for w,n in counts.most_common(40) if n>=3],'repeated_expressions':repeated,'repeated_starts':[{'text':w,'count':len(ls),'locations':ls[:10]} for w,ls in sorted(starts.items(),key=lambda x:-len(x[1])) if len(ls)>=3][:15],'character_mentions':characters,'scenes':scenes,'scene_basis':'EXPLICIT_SEPARATORS' if separators else 'WHOLE_DOCUMENT_NO_SCENE_BOUNDARIES','distribution_capped':len(paragraphs)>1000 or len(sentences)>1000}

def calculate(center,p,b):
    center.tools.writable(p);sources=[];names=defaultdict(list)
    for c in center.characters.list(p):
        name=c['canonical'].get('name')
        if name:names[name].append(c['canonical']['id'])
    for path in dict.fromkeys([b.path]+b.related_paths):
        doc=center.tools.doc(p,path);body=normalized(doc)
        if len(body)>100000:raise ConsoleError('单章统计上限 100000 字符，请缩小范围',413)
        sources.append({'path':path,'revision':doc['etag'],'body':body})
    if sum(len(x['body']) for x in sources)>300000:raise ConsoleError('本次统计超过 300000 字符，请分批比较',413)
    current=measure(sources[0]['body'],list(names.items()));trends=[]
    for src in sources:
        value=current if src is sources[0] else measure(src['body'],list(names.items()))
        _,number,_=center.tools.chapter(p,src['path'])
        trends.append({'path':src['path'],'revision':src['revision'],'chapter':number,'han':value['han'],'mean_sentence_han':value['mean_sentence_han'],'dialogue_ratio':value['dialogue_ratio'],'character_mentions':[{k:c[k] for k in ['name','count','ambiguous']} for c in value['character_mentions']]})
    id=uid('stats');row={'id':id,'project_id':p,'created_at':now(),'path':b.path,'source_revision':sources[0]['revision'],'sources':[{k:v for k,v in x.items() if k!='body'} for x in sources],'result':current,'chapter_comparison':trends,'method':{'version':'zh-local-2','chapter_heading':'EXCLUDED_USING_EDITOR_TITLE_BOUNDARY','segmentation':'jieba 0.42.1, HMM disabled','sentence_boundary':'Chinese 。！？ plus !? and newline; fragments retained','dialogue':'balanced quotation spans; not speaker attribution','basis':'DETERMINISTIC_MEASUREMENT_NOT_LITERARY_VERDICT','limitations':['Name mentions are not physical presence.','Quotes may include quoted documents, inner speech or hearsay.','Without explicit scene boundaries, document length is not a reliable scene count.','Repeated phrases may be deliberate; no automatic corrections.','No English readability formula or invented literary quality score.']}}
    if b.compare_id:
        if not re.fullmatch(r'stats_[0-9a-f]{32}',b.compare_id):raise ConsoleError('统计记录 ID 无效',422)
        old=read(safe(center.root(p),'statistics/'+b.compare_id+'.json'))
        if not old or old['project_id']!=p or old['path']!=b.path:raise ConsoleError('只比较同一作品同一正文的统计快照',409)
        if old.get('method',{}).get('version')!=row['method']['version']:raise ConsoleError('统计口径已更新，请先生成当前方法的基线快照，不混用旧口径比较',409)
        row['before_after']={'before_id':old['id'],'before_revision':old['source_revision'],'after_revision':row['source_revision'],'delta':{k:round(current[k]-old['result'][k],4) for k in ['han','sentences','paragraphs','mean_sentence_han','mean_paragraph_han','dialogue_ratio']}}
    # Check again before binding any evidence to the current source version.
    if any(center.tools.doc(p,x['path'])['etag']!=x['revision'] for x in sources):raise ConsoleError('统计期间正文变化，请重新计算',409)
    write(safe(center.root(p),'statistics/'+id+'.json'),row);return row

def history(center,p,path):
    center.tools.doc(p,path);result=[]
    for f in safe(center.root(p),'statistics').glob('stats_*.json'):
        row=read(f)
        if row.get('project_id')==p and row.get('path')==path:result.append({**{k:row[k] for k in ['id','created_at','source_revision']},'han':row['result']['han']})
    return sorted(result,key=lambda r:r['created_at'],reverse=True)[:30]

def snapshot(center,p,id):
    if not re.fullmatch(r'stats_[0-9a-f]{32}',id):raise ConsoleError('统计记录 ID 无效',422)
    row=read(safe(center.root(p),'statistics/'+id+'.json'))
    if not row or row.get('project_id')!=p:raise ConsoleError('统计记录不存在',404)
    row['source_current']=center.tools.doc(p,row['path'])['etag']==row['source_revision']
    return row
