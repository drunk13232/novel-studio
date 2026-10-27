"""World model views coordinate Bible, reference notes, FTS and World Logic Lab.

No second database, temporal replay engine, task manager or solver lives here.
"""
import copy,json,re,time
from fastapi import APIRouter,Request
from pydantic import Field
from typing import Literal
from app.errors import ConsoleError
from .bible import Strict,Entity
from .storage import safe,read,digest,uid,revisions,revision_content,now
from .world_rules import is_rule,card,fragment,historical,interval,RELATIONS

class SaveEntity(Strict):
    entity:Entity
    etag:str|None=None
    confirm:bool=False
class RuleLink(Strict):
    target_id:str
    relation:Literal['RULE_REQUIRES','RULE_ASSOCIATED','RULE_CONDITIONAL','RULE_AI_POSSIBLE','RULE_OVERRIDES']
    etag:str
    confirm:Literal[True]
class Evidence(Strict):
    etag:str
    kind:Literal['reference_note','manuscript']='reference_note'
    note_id:str=Field(default='',max_length=80)
    path:str=Field(default='',max_length=300)
    revision:str=Field(default='',max_length=64)
    quote:str=Field(default='',max_length=6000)
    purpose:str=Field(default='',max_length=1000)
    confirm:Literal[True]
class Prepare(Strict):
    rule_ids:list[str]=Field(min_length=1,max_length=8)
    scope_ids:list[str]=Field(default_factory=list,max_length=20)
    story_time:str=Field(default='',max_length=80)
    calendar:str=Field(default='iso',max_length=80)
    accepted_conditions:list[str]=Field(default_factory=list,max_length=16)
    solver:Literal['z3','formula']='z3'
class SaveExperiment(Prepare):
    mapping_hash:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirm:Literal[True]

class WorldModel:
    def __init__(self,studio,knowledge,references):
        self.studio=studio;self.bible=studio.bible;self.knowledge=knowledge;self.references=references;self.lab=studio.world

    def index(self,p):
        entities=self.bible.list(p)
        return {'rules':[{k:e.get(k) for k in ['id','name','summary','status','source','version','etag','category','valid_from','valid_to','fields','writer_view']} for e in entities if is_rule(e)],
                'entities':[{'id':e['id'],'name':e['name'],'status':e['status'],'category':e['category'],'periods':len(e.get('periods',[]))} for e in entities],
                'relations':self.bible.relations(p),'characters':[t for t in self.bible.targets(p) if t['type']=='character'],'relation_types':RELATIONS,'audience':'AUTHOR','writer_context':False}

    def save(self,p,b):
        return self.bible.save(p,b.entity.model_dump(),b.etag,b.confirm)

    def link(self,p,id,b):
        source=self.bible.get(p,id);self.bible.get(p,b.target_id)
        if not is_rule(source):raise ConsoleError('来源不是规则卡',422)
        from .knowledge import LinkRequest
        return self.knowledge.link(p,LinkRequest(source_type='entity',source_id=id,target_type='entity',target_id=b.target_id,relation_type=b.relation,description=RELATIONS[b.relation],status='AI_PROPOSED' if b.relation=='RULE_AI_POSSIBLE' else 'AUTHOR_CONFIRMED',etag=b.etag,confirm=True))

    def evidence(self,p,id):
        e=self.bible.get(p,id);rows=[];checked={}
        for ref in e.get('source_references',[]):
            if ref.get('kind')=='reference_note':
                try:
                    n=self.references.get(p,'notes',ref['note_id']);d=self.references.source_document(p,n['source_scope'],n['document_id']);state=self.references.citation_status(p,n,checked)
                    rows.append({'name':n.get('citation',{}).get('title') or d['metadata']['title'],'kind':'reference_note','note_id':n['id'],'quote':n['quote'],'location':n['location'],'purpose':ref.get('purpose',''),'current':'CURRENT' if state['status']=='VERIFIED' else state['status'],'evidence_status':state,'target_type':'reference','target_id':d['id'],'source_scope':n['source_scope'],'basis':'REFERENCE_NOT_CANON'})
                except (ConsoleError,KeyError):rows.append({'name':'原文引用不可用','current':'MISSING','kind':'reference_note'})
            elif ref.get('kind')=='manuscript':
                current='MISSING'
                try:
                    doc=self.studio.writing.tools.doc(p,ref['path'])
                    from app.studio_tools import normalized
                    current='CURRENT' if doc['etag']==ref['revision'] and ref['quote'] in normalized(doc) else 'STALE'
                except ConsoleError:pass
                rows.append({**ref,'name':ref['path'],'current':current,'target_type':'chapter','target_id':ref.get('chapter_id',''),'basis':'TEXT_NOT_OBJECTIVE_WORLD_FACT'})
        return {'entity':e['id'],'sources':rows,'note':'原文存在不等于小说事实成立；正式设定仍由作者确认。'}

    def attach(self,p,id,b):
        e=self.bible.get(p,id)
        if e['etag']!=b.etag:raise ConsoleError('设定已变化，未附加旧引用',409)
        if b.kind=='reference_note':
            n=self.references.get(p,'notes',b.note_id)
            if self.references.citation_status(p,n)['status']!='VERIFIED':raise ConsoleError('引用未通过版本与精确位置检查，请在文献阅读器重新核对',409)
            ref={'kind':'reference_note','note_id':n['id'],'purpose':b.purpose,'basis':'REFERENCE_NOT_CANON'}
        else:
            doc=self.studio.writing.tools.doc(p,b.path)
            from app.studio_tools import normalized
            if not b.path.startswith('chapters/') or doc['etag']!=b.revision or not b.quote or normalized(doc).count(b.quote)!=1:raise ConsoleError('正文选段版本不符或位置存在歧义，请保存并缩小唯一选段',409)
            chapter=self.studio.writing.tools.chapter(p,b.path)[0]
            ref={'kind':'manuscript','path':b.path,'revision':b.revision,'quote':b.quote,'chapter_id':chapter,'purpose':b.purpose,'basis':'TEXT_NOT_OBJECTIVE_WORLD_FACT'}
        if ref not in e['source_references']:e['source_references'].append(ref)
        etag=e.pop('etag');saved=self.bible.save(p,e,etag,True)
        if b.kind=='reference_note':
            link={'type':'entity','id':id}
            if link not in n['links']:
                n['links'].append(link);self.references.put(p,'notes',n,n['etag'])
        return saved

    def notes(self,p):
        rows=[];checked={}
        for n in sorted(self.references.rows(p,'notes'),key=lambda n:n.get('created_at',''),reverse=True)[:100]:
            state=self.references.citation_status(p,n,checked)
            rows.append({'id':n['id'],'title':n.get('citation',{}).get('title') or n['document_id'],'quote':n['quote'],'location':n['location'],'status':state['status'],'document_id':n['document_id'],'source_scope':n['source_scope']})
        return rows

    def memory(self,p,q='',id='',at='',calendar='iso',include_proposals=False):
        started=time.monotonic();warnings=[]
        if len(q)>120:raise ConsoleError('查询最多 120 字',422)
        if not at and re.search(r'年前|年后|以前|之后|当时|第.{1,8}章',q):return {'status':'NEEDS_BOUNDARY','facts':[],'drafts':[],'warnings':['请指定故事时间或使用人物章节知识查询；不由当前状态猜测过去。'],'seconds':time.monotonic()-started}
        if id:entities=[self.bible.get(p,id)]
        else:
            nodes=self.knowledge.lookup(p,q,40)
            if not nodes and len(q)>4:
                import jieba
                terms=list(dict.fromkeys(v for v in jieba.cut_for_search(q) if 2<=len(v)<=20 and v not in {'之前','有没有','什么','哪些','我们','这个','当前','设定','规则'}))[-4:]
                nodes=[]
                for term in terms:nodes.extend(self.knowledge.lookup(p,term,10))
            ids=list(dict.fromkeys(n['id'] for n in nodes if n['type']=='entity' and re.fullmatch(r'entity_[0-9a-f]{32}',n['id'])))[:40]
            entities=[]
            for key in ids:
                try:entities.append(self.bible.get(p,key))
                except ConsoleError:pass
        facts=[];drafts=[]
        for e in entities:
            base={'id':e['id'],'name':e['name'],'revision':e['etag'],'version':e['version'],'source':e['source'],'status':e['status']}
            if e['status'] not in {'FORMAL','LOCKED'}:
                if include_proposals:drafts.append({**base,'summary':e['summary'],'basis':'UNCONFIRMED_NOT_WORLD_FACT'})
                continue
            if at:
                projection=historical(e,at,calendar)
                facts.append({**base,'historical':projection,'basis':projection.get('basis','UNKNOWN'),'summary':projection.get('period',{}).get('description','')})
            else:facts.append({**base,'summary':e['summary'],'fields':e['fields'],'field_labels':{f['id']:f['name'] for f in (e.get('template_snapshot') or {}).get('fields',[])},'basis':'AUTHOR_CONFIRMED_CURRENT_EDIT_NOT_PAST_STATE','periods_available':len(e.get('periods',[])),'rule':card(e) if is_rule(e) else None})
        if include_proposals and q.strip() and not id:
            for path in sorted(safe(self.bible.root(p),'bible/designs').glob('design_*.json'),key=lambda f:f.stat().st_mtime_ns,reverse=True)[:30]:
                d=read(path)
                for e in d.get('result',{}).get('entries',[]):
                    if e['key'] not in d.get('adoptions',{}) and q in e['name']+' '+e['summary']:drafts.append({'id':d['id']+':'+e['key'],'name':e['name'],'summary':e['summary'],'basis':'AI_DESIGN_NOT_ADOPTED','design_id':d['id']})
            warnings.append('未采用设计稿仅检查最近 30 稿，不代表全部 AI 历史覆盖。')
        return {'status':'FOUND' if facts or drafts else 'NOT_FOUND','facts':facts,'drafts':drafts,'warnings':warnings,'seconds':time.monotonic()-started,'audience':'AUTHOR','writer_context':False,'story_time':at or 'CURRENT_EDIT_ONLY','calendar':calendar,'no_current_state_backfill':True,'coverage':{'mode':'EXPLICIT_ENTITY' if id else 'BOUNDED_RETRIEVAL','entity_limit':1 if id else 40,'complete_world_read':False}}

    def impact(self,p,id):
        import networkx as nx
        self.bible.get(p,id);relations=self.bible.relations(p);graph=nx.DiGraph();ordinary=[];conditional=[];possible=[];priority=[]
        for r in relations:
            src,dst=r['source_id'],r['target_id'];kind=r.get('relation_type','')
            if kind=='RULE_REQUIRES' and r.get('status')=='AUTHOR_CONFIRMED':graph.add_edge(dst,src)
            elif id in {src,dst}:
                (conditional if kind=='RULE_CONDITIONAL' else possible if kind=='RULE_AI_POSSIBLE' or r.get('status')=='AI_PROPOSED' else priority if kind=='RULE_OVERRIDES' else ordinary).append(r)
        impacted=sorted(nx.descendants(graph,id)) if id in graph else []
        names={e['id']:e['name'] for e in self.bible.list(p)}
        experiments=[]
        for row in self.lab.list(p):
            if any(s.get('type')=='entity' and s.get('target_id')==id for s in row['definition']['source_references']):experiments.append({'id':row['id'],'name':row['definition']['name'],'version':row['latest_version']})
        return {'actual_dependents':[{'id':k,'name':names.get(k,'未解析对象'),'path':nx.shortest_path(graph,id,k)} for k in impacted],'ordinary_links':ordinary,'conditional':conditional,'ai_possible':possible,'explicit_priorities':priority,'experiments_to_recheck':experiments,'warning':'依赖路径是作者记录的模型关系；不等于已经发生的政治、经济后果。'}

    def prepare(self,p,b):
        if len(set(b.rule_ids))!=len(b.rule_ids):raise ConsoleError('规则重复',422)
        entities=[self.bible.get(p,id) for id in b.rule_ids];known={t['id'] for t in self.bible.targets(p)}
        if set(b.scope_ids)-known:raise ConsoleError('推演对象不属于当前作品',403)
        from app.world_logic.models import validate
        from app.world_logic.service import fingerprint
        d={'schema_version':'1.0','experiment_id':'exp_'+'0'*32,'name':'世界规则验证','description':'作者确认的规则映射；只检查明确的有限数学条件。','experiment_type':'world_rules','solver':b.solver,'inputs':[],'constraints':[],'outputs':[],'acceptance_rules':[],'source_references':[],'assumptions':[],'limitations':['SAT 只表示当前形式化条件存在满足解；UNSAT 不直接证明文学设定错误。']}
        mapping=[];variables={};outputs={};unknown=[];eligible={}
        for e in entities:
            if not is_rule(e) or e['status'] not in {'FORMAL','LOCKED'}:raise ConsoleError('请选择本作品已确认规则；AI 草案不是事实',409)
            r=card(e);scope='MATCH'
            if r['rule_scope']=='SCENARIO':scope='UNKNOWN'
            if r['rule_scope']=='ENTITY' and not set(r['scope_ids'])&set(b.scope_ids):scope='UNKNOWN'
            if e.get('valid_from') or e.get('valid_to'):
                time_scope=interval(e.get('valid_from',''),e.get('valid_to',''),b.story_time,r['calendar']) if r['calendar']==b.calendar else 'UNKNOWN'
                # Matching time cannot erase a mismatched entity or sandbox scope.
                if time_scope=='OUTSIDE' or scope=='MATCH':scope=time_scope
            if r['rule_scope']=='PERIOD' and not (e.get('valid_from') or e.get('valid_to')):scope='UNKNOWN'
            eligible[e['id']]=scope
        import networkx as nx
        priorities=nx.DiGraph((r['source_id'],r['target_id']) for r in self.bible.explicit_relations(p) if r.get('relation_type')=='RULE_OVERRIDES' and r.get('status')=='AUTHOR_CONFIRMED' and r['source_id'] in b.rule_ids and r['target_id'] in b.rule_ids and eligible.get(r['source_id'])=='MATCH' and eligible.get(r['target_id'])=='MATCH')
        cyclic=not nx.is_directed_acyclic_graph(priorities)
        if cyclic:unknown.append('作者指定的优先关系存在循环，不以创建时间替代裁决')
        for i,e in enumerate(entities):
            r=card(e);sid='rule_source_'+str(i+1);prefix='r'+str(i+1)+'_'
            d['source_references'].append({'id':sid,'type':'entity','target_id':e['id'],'name':e['name'],'basis':'AUTHOR_CONFIRMED','sha256':e['etag'],'excerpt':e['summary'][:2000]})
            item={'id':e['id'],'name':e['name'],'revision':e['etag'],'strength':r['rule_strength'],'scope_status':eligible[e['id']],'natural_rule':e['summary'],'conditions':r['conditions'],'exceptions':r['exceptions'],'constraints':[]};mapping.append(item)
            overridden=not cyclic and e['id'] in priorities and priorities.in_degree(e['id'])>0
            if overridden:item['status']='EXPLICITLY_OVERRIDDEN';continue
            if eligible[e['id']]=='OUTSIDE':item['status']='OUTSIDE_PERIOD';continue
            if r['rule_strength']=='SOFT':
                item['status']='QUALITATIVE_NOT_HARD';d['acceptance_rules'].append({'id':prefix+'qualitative','name':e['name'],'type':'QUALITATIVE','basis':'软规则需要作者判断，不能当作绝对数学约束。','automatic':False,'source_ids':[sid]});continue
            if eligible[e['id']]!='MATCH':unknown.append(e['name']+'：适用范围或时间不足')
            if (r['conditions'] or r['exceptions']) and e['id'] not in b.accepted_conditions:unknown.append(e['name']+'：尚未由作者核对生效条件与例外')
            if r['confidence']!='AUTHOR_CONFIRMED':unknown.append(e['name']+'：关键前提仍为条件假设或未知')
            if e.get('periods'):
                item['status']='HISTORICAL_MODEL_UNAVAILABLE'
                unknown.append(e['name']+'：含历史时期；当前数学字段不能替代历史模型。请为目标时期明确建立并确认对应的规则版本。')
                continue
            f=fragment(r['formal_model'])
            if not f:unknown.append(e['name']+'：尚无已映射的数学模型');item['status']='NO_FORMAL_MODEL';continue
            if f['solver']!=b.solver:raise ConsoleError('所选规则的求解器不同，请分成独立实验',422)
            for v in f['inputs']:
                normalized={k:x for k,x in v.items() if k!='source_ids'}
                if v['id'] in variables and variables[v['id']][0]!=normalized:raise ConsoleError('同名变量定义不一致：'+v['id']+'；请作者明确统一参数，不能自动合并',409)
                if v['id'] not in variables:
                    actual={**v,'source_ids':[sid]};variables[v['id']]=(normalized,actual);d['inputs'].append(actual)
                elif sid not in variables[v['id']][1]['source_ids']:variables[v['id']][1]['source_ids'].append(sid)
            for v in f['outputs']:
                normalized={k:x for k,x in v.items() if k!='source_ids'}
                if v['id'] in outputs and outputs[v['id']]!=normalized:raise ConsoleError('输出名称重复且公式不同，请修改后再组合',409)
                if v['id'] not in outputs:outputs[v['id']]=normalized;d['outputs'].append(copy.deepcopy(v))
            for group in ['constraints','acceptance_rules','assumptions']:
                for v in f[group]:
                    actual={**v,'id':prefix+v['id']}
                    if group!='assumptions':actual['source_ids']=[sid]
                    if group=='constraints':item['constraints'].append({'id':actual['id'],'expression':v['expression'],'meaning':v.get('meaning',''),'source_id':sid})
                    d[group].append(actual)
            item['status']='MAPPED_NOT_RUN'
        if not d['constraints'] and not d['outputs'] and not d['acceptance_rules']:unknown.append('本次范围没有适用的形式化规则，未验证世界整体合理性')
        for i,text in enumerate(unknown):d['assumptions'].append({'id':'unknown_'+str(i),'text':text,'accepted':False,'origin':'UNKNOWN'})
        d=validate(d);proof={'definition':d,'mapping':mapping,'choice':b.model_dump(),'unknown':unknown};proof['mapping_hash']=fingerprint(proof)
        return proof

    def experiment(self,p,b):
        prepared=self.prepare(p,Prepare(**b.model_dump(exclude={'mapping_hash','confirm'})))
        if prepared['mapping_hash']!=b.mapping_hash:raise ConsoleError('规则或映射已变化，请重新预览；未保存旧实验',409)
        d=prepared['definition'];d['experiment_id']=uid('exp')
        return self.lab.save(p,d)

def routes(s):
    r=APIRouter(prefix='/api/projects/{p}/world-model')
    @r.get('')
    def index(p:str):return s.index(p)
    @r.post('/entities')
    def save(p:str,b:SaveEntity):return s.save(p,b)
    @r.get('/entities/{id}')
    def entity(p:str,id:str):return s.bible.get(p,id)
    @r.get('/notes')
    def notes(p:str):return s.notes(p)
    @r.get('/entities/{id}/evidence')
    def evidence(p:str,id:str):return s.evidence(p,id)
    @r.post('/entities/{id}/evidence')
    def attach(p:str,id:str,b:Evidence):return s.attach(p,id,b)
    @r.post('/entities/{id}/links')
    def link(p:str,id:str,b:RuleLink):return s.link(p,id,b)
    @r.get('/entities/{id}/impact')
    def impact(p:str,id:str):return s.impact(p,id)
    @r.get('/memory')
    def memory(p:str,q:str='',id:str='',at:str='',calendar:str='iso',include_proposals:bool=False):
        with s.studio.guard():return s.memory(p,q,id,at,calendar,include_proposals)
    @r.post('/prepare')
    def prepare(p:str,b:Prepare):return s.prepare(p,b)
    @r.post('/experiments')
    def experiment(p:str,b:SaveExperiment):return s.experiment(p,b)
    return r
