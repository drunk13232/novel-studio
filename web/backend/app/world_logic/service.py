"""Project-scoped experiment versions/reports; no Canon/State mutation methods."""
import copy, hashlib, json, os, re, subprocess, sys, threading, time
from pathlib import Path
from typing import Literal
import yaml
from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from app.errors import ConsoleError
from app.library.storage import safe, read, write, now, uid, digest
from app.models.requests import TaskRequest, TaskOptions
from app.projects.foundation import schema as ai_schema
from .models import validate, schema, Save, Freeze, Run, Design, Proposal, Strict, AIProposal, Acceptance, Experiment

def fingerprint(value):return digest(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8'))
def acceptance_fingerprint(definition):
    return fingerprint([Acceptance.model_validate(r).model_dump() for r in definition['acceptance_rules']])

def identity(value,prefix):
    if not re.fullmatch(prefix+r'_[0-9a-f]{32}',value or ''):raise ConsoleError('实验或报告 ID 无效',403)
    return value

def parse(text):
    if len(text.encode())>160000:raise ConsoleError('实验导入超过 160 KB',413)
    try:
        if any(isinstance(t,(yaml.tokens.AliasToken,yaml.tokens.AnchorToken,yaml.tokens.TagToken)) for t in yaml.scan(text)):raise ValueError('导入不允许 YAML 标签、锚点或别名')
        value=yaml.safe_load(text)
        def depth(v,n=0):
            if n>16:raise ValueError('实验结构过深')
            if isinstance(v,dict):
                for k,x in v.items():
                    if not isinstance(k,str):raise ValueError('键必须为字符串')
                    depth(x,n+1)
            if isinstance(v,list):
                if len(v)>200:raise ValueError('数组过大')
                for x in v:depth(x,n+1)
        depth(value);return validate(value)
    except ConsoleError:raise
    except Exception as e:raise ConsoleError('实验导入无效：'+str(e)[:300],422) from e

def bounded_experiment_context(definition,sources):
    if definition is None:return None
    result=copy.deepcopy(definition);allowed={x['type']+':'+x['target_id'] for x in sources}
    result['source_references']=[x for x in result['source_references'] if x['type']+':'+x['target_id'] in allowed]
    keep={x['id'] for x in result['source_references']}
    for group in ['inputs','constraints','acceptance_rules','dependencies','events']:
        for x in result.get(group,[]):x['source_ids']=[id for id in x['source_ids'] if id in keep]
    return result

class Scenario(Strict):
    version:int=Field(ge=1)
    changes:dict[str,float|bool|None]=Field(default_factory=dict,max_length=48)
    note:str=Field(min_length=1,max_length=1000)
    name:str=Field(default='',max_length=200)
class Counterexample(Strict):
    finding:int=Field(ge=0,le=7)
    version:int=Field(ge=1)
    confirm:Literal[True]
class RecordChoice(Strict):
    finding:int=Field(ge=0,le=7)
    kind:Literal['inspiration','world_proposal']
    target_id:str=Field(default='',max_length=100)
    confirm:Literal[True]
class CompareMany(Strict):
    baseline:str=Field(pattern=r'^run_[0-9a-f]{32}$')
    scenarios:list[str]=Field(min_length=1,max_length=2)
class Import(Strict):text:str=Field(max_length=160000)
class Adopt(Strict):
    experiment_id:str|None=None
    etag:str=Field(default='',max_length=64)
    confirm:bool=False
class ManualReview(Strict):
    rule_id:str=Field(pattern=r'^[A-Za-z][A-Za-z0-9_]{0,47}$')
    status:Literal['PASS','FAIL']
    note:str=Field(min_length=1,max_length=1500)
    definition_fingerprint:str=Field(pattern=r'^[0-9a-f]{64}$')
    acceptance_fingerprint:str=Field(pattern=r'^[0-9a-f]{64}$')
    rule_fingerprint:str=Field(pattern=r'^[0-9a-f]{64}$')
    review_revision:str=Field(pattern=r'^[0-9a-f]{64}$')
    confirm:Literal[True]

class WorldLogic:
    def __init__(self,registry,knowledge,manager,ai_center):
        self.registry=registry;self.knowledge=knowledge;self.manager=manager;self.ai_center=ai_center;self.lock=threading.RLock()
        self.resources=Path(__file__).parent/'resources'
    def root(self,p):return safe(self.registry.workspace(p).root,'metadata/world-logic')
    def path(self,p,id):return safe(self.root(p),'experiments/'+identity(id,'exp')+'.json')
    def templates(self):return [read(f) for f in sorted((self.resources/'templates').glob('*.json'))]
    def list(self,p):
        rows=[self.get(p,f.stem) for f in self.root(p).joinpath('experiments').glob('exp_*.json')]
        return sorted(rows,key=lambda r:r['updated_at'],reverse=True)
    def get(self,p,id):
        path=self.path(p,id);v=read(path)
        if not v:raise ConsoleError('实验不存在',404)
        return {**v,'etag':digest(path.read_bytes())}
    def save(self,p,definition,etag=''):
        d=validate(definition);id=d['experiment_id'];path=self.path(p,id)
        with self.lock:
            old=self.get(p,id) if path.exists() else None
            if old and old['etag']!=etag:raise ConsoleError('实验已被更新；请保留编辑并重新加载比较',409)
            if not old and etag:raise ConsoleError('实验已不存在',409)
            if old and old['definition']==d:return old
            value={'id':id,'definition':d,'status':'DRAFT','created_at':old['created_at'] if old else now(),'updated_at':now(),'latest_version':old['latest_version'] if old else 0}
            write(path,value)
            return self.get(p,id)
    def source_nodes(self,p):
        nodes,_=self.knowledge.collect(p)
        return [n for n in nodes if n['type'] in ['entity','character','event','chapter','clue','reference']]
    def sources(self,p):return [{'key':n['type']+':'+n['id'],'id':n['id'],'type':n['type'],'name':n['name'],'basis':n['status']} for n in self.source_nodes(p)][:1000]
    def source(self,p,key):
        if re.fullmatch(r'entity:entity_[0-9a-f]{32}',key):
            entity=self.knowledge.bible.get(p,key.split(':',1)[1])
            node={'type':'entity','id':entity['id'],'name':entity['name'],'summary':entity['summary'],'category':entity['category'],'path':'bible/entities/'+entity['id']+'.json','status':'AUTHOR_CONFIRMED' if entity['status'] in {'FORMAL','LOCKED'} else 'UNKNOWN'}
        else:node=next((n for n in self.source_nodes(p) if n['type']+':'+n['id']==key),None)
        if not node:raise ConsoleError('来源不存在或不属于当前小说',403)
        basis=node['status'] if node['status'] in ['AUTHOR_CONFIRMED','COMMITTED','REFERENCE'] else 'UNKNOWN'
        value={'id':'source_'+hashlib.sha256(key.encode()).hexdigest()[:16],'type':node['type'],'target_id':node['id'],'name':node['name'],'basis':basis,'excerpt':node.get('summary','')[:2000]}
        if node['type']=='entity' and re.fullmatch(r'entity_[0-9a-f]{32}',node['id']):
            entity=self.knowledge.bible.get(p,node['id'])
            categories={c['id']:c for c in self.knowledge.bible.categories(p)}
            fields={f['id']:f['name'] for f in categories.get(entity['category'],{}).get('fields',[])}
            facts=[]
            for key,item in entity.get('fields',{}).items():
                if isinstance(item,(str,int,float,bool)) or item is None:
                    if any(token in key.lower() for token in ['api_key','access_token','password','credential']):continue
                    facts.append({'id':key[:80],'name':str(fields.get(key,key))[:100],'value':item[:240] if isinstance(item,str) else item,'unit':''})
                if len(facts)>=32:break
            value['facts']=facts
        # Hash the selected, bounded view, not all novel/author secrets.
        extra={k:node[k] for k in ['story_time','number','location','category','chapter'] if node.get(k) is not None}
        if extra:value['excerpt']=(value['excerpt']+'\n来源元数据：'+json.dumps(extra,ensure_ascii=False))[:2000]
        evidence={'selected_view':value}
        path=str(node.get('path','')).split('#')[0]
        if path:
            f=safe(self.registry.workspace(p).root,path)
            if f.is_file():evidence['source_file_hash']=digest(f.read_bytes())
        value['sha256']=fingerprint(evidence)
        return value
    def stamp_sources(self,p,d):
        result=copy.deepcopy(d)
        for i,s in enumerate(result['source_references']):
            if s['type']=='manual':s['sha256']=fingerprint({k:v for k,v in s.items() if k!='sha256'});continue
            current=self.source(p,s['type']+':'+s['target_id']);current['id']=s['id'];result['source_references'][i]=current
        return result
    def freeze(self,p,id,b):
        with self.lock:
            row=self.get(p,id)
            if row['etag']!=b.etag:raise ConsoleError('实验已变化；不能确认旧版本',409)
            d=self.stamp_sources(p,row['definition']);version=row['latest_version']+1
            v={'schema_version':'1.0','id':id,'version':version,'definition':d,'fingerprint':fingerprint(d),'acceptance_fingerprint':fingerprint(d['acceptance_rules']),'confirmed_at':now(),'reason':b.reason,'project_id':p}
            path=safe(self.root(p),f'versions/{id}/v{version}.json')
            if path.exists():raise ConsoleError('冻结版本已存在，不覆盖',409)
            write(path,v);row.pop('etag');row.update(status='CONFIRMED',latest_version=version,definition=d,updated_at=now());write(self.path(p,id),row)
            return {**self.get(p,id),'frozen':v}
    def version(self,p,id,number):
        identity(id,'exp')
        if not isinstance(number,int) or not 1<=number<=100000:raise ConsoleError('版本号无效',422)
        v=read(safe(self.root(p),f'versions/{id}/v{number}.json'))
        if not v:raise ConsoleError('确认版本不存在，请先锁定验收标准',409)
        if fingerprint(v['definition'])!=v['fingerprint'] or fingerprint(v['definition']['acceptance_rules'])!=v['acceptance_fingerprint']:raise ConsoleError('冻结版本完整性检查失败；请勿修改旧版本',409)
        # Restored snapshots remain usable without executing their old tasks.
        return v
    def reports(self,p,id=None):
        if id:identity(id,'exp')
        rows=[read(f) for f in safe(self.root(p),'reports').glob('run_*.json')]
        return [self.reviewed(p,r) for r in sorted([r for r in rows if not id or r['experiment_id']==id],key=lambda r:r['created_at'],reverse=True)[:200]]
    def report(self,p,id):
        r=read(safe(self.root(p),'reports/'+identity(id,'run')+'.json'))
        if not r:raise ConsoleError('实验报告不存在',404)
        changed=[]
        for s in r['definition']['source_references']:
            if s['type']=='manual':continue
            try:
                if self.source(p,s['type']+':'+s['target_id'])['sha256']!=s['sha256']:changed.append(s['id'])
            except ConsoleError:changed.append(s['id'])
        explanations=[{'id':v['id'],'created_at':v['created_at'],'status':v['status'],'value':v['value']} for f in safe(self.root(p),'proposals').glob('proposal_*.json') if (v:=read(f)).get('report_id')==id and v.get('project_id')==p]
        return {**self.reviewed(p,r),'ai_explanations':explanations,'source_changes':changed,'source_notice':'当前来源已变化，建议新版本重新执行。' if changed else ''}
    def reviewed(self,p,r):
        """Author review is an overlay; immutable solver reports are never rewritten."""
        from .engine import status_of
        result=copy.deepcopy(r);d=r['definition']
        rules={x['id']:x for x in d['acceptance_rules'] if not x['automatic'] or x['type']=='QUALITATIVE'}
        journal_path=safe(self.root(p),'manual-reviews/'+identity(r['id'],'run')+'.json')
        journal=read(journal_path,[])
        result['review_revision']=digest(journal_path.read_bytes() if journal_path.exists() else b'')
        current=self.get(p,r['experiment_id'])
        stale=current['status']!='CONFIRMED' or current['latest_version']!=r['definition_version'] or fingerprint(current['definition'])!=r['definition_fingerprint']
        automatic=[x for x in result.get('acceptance_results',[]) if x['id'] not in rules]
        result['mathematical_status']=status_of(automatic) if automatic else 'NOT RUN'
        manual=[]
        for id,rule in rules.items():
            bound=fingerprint(rule)
            decisions=[x for x in journal if x.get('actor')=='AUTHOR' and x.get('rule_id')==id and x.get('definition_fingerprint')==r['definition_fingerprint'] and x.get('acceptance_fingerprint')==r['acceptance_fingerprint'] and x.get('rule_fingerprint')==bound]
            decision=decisions[-1] if decisions and not stale else None
            manual.append({'id':id,'name':rule['name'],'status':decision['status'] if decision else 'NOT RUN','manual':True,'rule_fingerprint':bound,'basis':rule['basis'],'source_ids':rule['source_ids'],'stale':stale,'review':decision,'detail':decision['note'] if decision else '规则或实验已变化，需锁定新版本后重新审核。' if stale else '等待作者人工验收；AI 意见不代替批准。'})
        result['acceptance_results']=[*automatic,*manual]
        if r.get('finished_at'):
            status=status_of(result['acceptance_results'])
            if r.get('status')=='ERROR':status='ERROR'
            elif r.get('status')=='FAIL':status='FAIL'
            if any(not a['accepted'] for a in d['assumptions']) and status=='PASS':status='INCONCLUSIVE'
            result['status']=status
        result['manual_pending']=sum(x['status']=='NOT RUN' for x in manual)
        result['manual_reviews']=journal
        result['unverified']=[x['name'] for x in result['acceptance_results'] if x['status'] in {'NOT RUN','INCONCLUSIVE'}]
        return result

    def manual_review(self,p,id,b):
        with self.lock:
            r=self.report(p,id)
            if not r.get('finished_at') or r.get('cancelled'):raise ConsoleError('请先完成本次实验，再进行人工验收',409)
            if r['definition_fingerprint']!=b.definition_fingerprint or r['acceptance_fingerprint']!=b.acceptance_fingerprint or r['review_revision']!=b.review_revision:raise ConsoleError('报告或人工审核记录已变化，请重新查看',409)
            rule=next((x for x in r['acceptance_results'] if x['id']==b.rule_id and x.get('manual')),None)
            if not rule or rule['stale'] or rule['rule_fingerprint']!=b.rule_fingerprint:raise ConsoleError('人工规则已失效；请锁定当前实验版本并重新执行',409)
            row={**b.model_dump(exclude={'confirm','review_revision'}),'id':uid('review'),'actor':'AUTHOR','at':now(),'report_id':id,'definition_version':r['definition_version'],'project_id':p}
            path=safe(self.root(p),'manual-reviews/'+id+'.json');journal=read(path,[])
            if len(journal)>=500:raise ConsoleError('本报告人工审核记录已达上限，请保存新版本实验',413)
            write(path,[*journal,row])
            return self.report(p,id)

    def run(self,p,id,b):
        frozen=self.version(p,id,b.version)
        if b.fingerprint!=frozen['fingerprint']:raise ConsoleError('执行请求与确认的实验版本不一致',409)
        manager=self.manager(p);rid=uid('run');created=now();definition=copy.deepcopy(frozen['definition']);path=safe(self.root(p),'reports/'+rid+'.json')
        base={'schema_version':'1.0','id':rid,'experiment_id':id,'definition_version':b.version,'definition_fingerprint':frozen['fingerprint'],'acceptance_fingerprint':frozen['acceptance_fingerprint'],'created_at':created,'definition':definition,'status':'NOT RUN','ai_explanations':[]}
        write(path,base)
        def execute(emit,cancelled):
            emit('status','正在运行本地求解器；仅读取已确认的实验快照',{'experiment_id':id,'version':b.version})
            command=[sys.executable,'--world-logic-worker'] if getattr(sys,'frozen',False) else [sys.executable,'-m','app.world_logic.worker']
            env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ['KEY','TOKEN','SECRET','CODEX','NOVEL_MCP'])}
            env['PYTHONPATH']=str(Path(__file__).resolve().parents[2]);env['PYTHONDONTWRITEBYTECODE']='1'
            env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
            process=None;budget=None;started=time.monotonic();result=None
            try:
                process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=str(Path(__file__).resolve().parents[2]),env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                from .budget import Budget
                budget=Budget(process)
                payload=json.dumps(definition,ensure_ascii=False,allow_nan=False).encode('utf8')
                first=True
                while True:
                    if cancelled():
                        if budget:budget.close()
                        process.kill();process.communicate();result={'status':'NOT RUN','cancelled':True,'error':'作者已取消；没有修改任何正式设定。'};break
                    if time.monotonic()-started>b.timeout_seconds:
                        if budget:budget.close()
                        process.kill();process.communicate();result={'status':'INCONCLUSIVE','error':'本地求解超过运行时限，未确认数学结论。'};break
                    try:
                        out,err=process.communicate(payload if first else None,timeout=.15)
                        if len(out)>1000000:raise ValueError('求解结果超过 1 MB')
                        if process.returncode:raise ValueError('求解器子进程启动或运行失败，代码 '+str(process.returncode))
                        result=json.loads(out);break
                    except subprocess.TimeoutExpired:first=False
                if result.get('status') not in ['PASS','FAIL','INCONCLUSIVE','ERROR','NOT RUN']:raise ValueError('求解器结果格式不合法')
            except Exception as e:result={'status':'ERROR','error':str(e)[:400]}
            finally:
                if process and process.poll() is None:
                    if budget:budget.close()
                    process.kill();process.communicate()
                if budget:budget.close()
            report={**base,**result,'finished_at':now(),'task_id':task.id,'total_seconds':round(time.monotonic()-started,4)}
            with self.lock:write(path,report)
            task.result={'report_id':rid,'status':report['status'],'experiment_id':id}
            emit('status','实验结果：'+report['status'],{'report_id':rid,'result_status':report['status']})
            return {'status':'interrupted' if cancelled() else 'failed' if report['status']=='ERROR' else 'completed','output':json.dumps({'report_id':rid,'status':report['status'],'experiment_id':id},ensure_ascii=False),'error':report.get('error')}
        req=TaskRequest(type='world_logic_run',prompt='执行已确认本地实验',options=TaskOptions(read_only=True,resume=False,timeout_seconds=b.timeout_seconds+30))
        task=manager.prepared(req,'',True,'world-logic-'+id,complete=lambda t:json.loads(t),execute=execute,provider='本地世界逻辑求解器',target=id,skill='声明式规则；无文件工作流',application_actions=True)
        base['task_id']=task.id;write(path,base)
        task.result={'report_id':rid,'status':'NOT RUN','experiment_id':id};manager.store.save(task)
        return {**task.public(),'report_id':rid}
    def scenario(self,p,id,b):
        baseline=self.version(p,id,b.version);d=copy.deepcopy(baseline['definition']);d.update(experiment_id=uid('exp'),name=d['name']+' · 反事实',experiment_type='counterfactual',baseline_id=id,baseline_version=b.version,baseline_fingerprint=baseline['fingerprint'],baseline_acceptance_fingerprint=acceptance_fingerprint(baseline['definition']),scenario_note=b.note,sensitivity=None)
        if b.name:d['name']=b.name
        inputs={v['id']:v for v in d['inputs']}
        for name,value in b.changes.items():
            if name not in inputs or inputs[name]['role']!='input':raise ConsoleError('只能修改已声明的固定输入',422)
            inputs[name]['value']=value;inputs[name]['note']='反事实参数：'+b.note;inputs[name]['basis']='SCENARIO'
        return self.save(p,d)
    def compare(self,p,a,b):
        left=self.report(p,a);right=self.report(p,b);ld=left['definition'];rd=right['definition']
        lv={v['id']:v for v in ld['inputs']};rv={v['id']:v for v in rd['inputs']}
        changed=[{'id':k,'before':lv.get(k),'after':rv.get(k)} for k in sorted(lv.keys()|rv.keys()) if lv.get(k)!=rv.get(k)]
        rules_changed=acceptance_fingerprint(ld)!=acceptance_fingerprint(rd)
        linked=rd.get('baseline_id')==left['experiment_id'] and rd.get('baseline_version')==left['definition_version']
        preserved=False
        if linked:
            frozen=self.version(p,left['experiment_id'],left['definition_version'])
            preserved=frozen['fingerprint']==left['definition_fingerprint'] and rd.get('baseline_fingerprint') in ['',frozen['fingerprint']]
        influence=left.get('model_influence',{}).get('affected_outputs',{})
        causal={n['id']:n.get('affected',[]) for n in left.get('dependency_graph',{}).get('nodes',[])}
        paths=[{'variable':v['id'],'formula_outputs':influence.get(v['id'],[]),'declared_causal_dependents':causal.get(v['id'],[]),'basis':'DECLARED_FORMULA_AND_CAUSAL_EDGES_ONLY; no invented quantitative effect'} for v in changed]
        return {'left':a,'right':b,'left_status':left['status'],'right_status':right['status'],'inputs_changed':changed,'rules_changed':rules_changed,'constraints_changed':ld['constraints']!=rd['constraints'],
            'left_outputs':left.get('outputs',[]),'right_outputs':right.get('outputs',[]),'baseline_preserved':preserved,'linked_baseline':linked,'shared_acceptance_fingerprint':acceptance_fingerprint(ld) if not rules_changed else None,
            'comparable':not rules_changed and ld['constraints']==rd['constraints'] and ld['outputs']==rd['outputs'],'influence_paths':paths,
            'limitations':['只有显式公式提供数量影响；普通关联不等于因果。','验收标准变化时不能把两个结果当作同一标准的优劣排名。']}
    def compare_many(self,p,b):
        baseline=self.report(p,b.baseline)
        comparisons=[self.compare(p,b.baseline,id) for id in b.scenarios]
        return {'baseline':baseline['id'],'baseline_status':baseline['status'],'scenarios':comparisons,'same_locked_acceptance':all(not r['rules_changed'] for r in comparisons),'baseline_preserved':all(r['baseline_preserved'] for r in comparisons)}
    def mapping(self,p,id):
        row=self.get(p,id);d=row['definition'];sources={s['id']:s for s in d['source_references']}
        return {'id':id,'etag':row['etag'],'version':row['latest_version'],'confirmed':row['status']=='CONFIRMED','rules':[{'id':v['id'],'natural_language':v.get('meaning') or v.get('basis') or v['name'],'expression':v.get('expression') or v.get('target',''),'condition':v.get('condition',''),'source_ids':v.get('source_ids',[]),'sources':[sources[s] for s in v.get('source_ids',[]) if s in sources]} for v in [*d['constraints'],*d['acceptance_rules']]],'inputs':d['inputs'],'notice':'形式化映射需作者检查；它不是新的 HARD Canon。'}
    def counterexample(self,p,pid,b):
        proposal=self.proposal(p,pid);findings=proposal['value']['findings']
        if b.finding>=len(findings):raise ConsoleError('反例候选不存在',404)
        if proposal['status']=='REJECTED':raise ConsoleError('该建议已拒绝，不执行迟到反例操作',409)
        target=proposal.get('accepted_id') or proposal.get('experiment_id')
        if not target:raise ConsoleError('请先采用并确认一个实验基线，再将反例转为独立实验',409)
        finding=findings[b.finding];changes={v['variable']:v['value'] for v in finding.get('counterexample_inputs',[])}
        if not changes:raise ConsoleError('该意见尚无可执行参数；它仍是定性意见或信息缺口',409)
        result=self.scenario(p,target,Scenario(version=b.version,changes=changes,note=('AI 反例候选，尚未数学验证：'+finding['condition'])[:1000],name=(finding['title']+' · 反例草稿')[:200]))
        return {**result,'proposal_id':pid,'finding_index':b.finding,'executed':False,'needs_author_freeze':True}
    def design(self,p,b):
        self.registry.get(p);manager=self.manager(p);sources=[self.source(p,k) for k in b.source_ids]
        row=self.get(p,b.experiment_id) if b.experiment_id else None
        report=self.report(p,b.report_id) if b.report_id else None
        if report and row and report['experiment_id']!=row['id']:raise ConsoleError('报告不属于当前实验',403)
        # No broad Author Context: only specifically selected sources and experiment snapshot.
        report_context=None
        if report and b.mode in ['explain','rebuttal']:
            report_context={k:copy.deepcopy(v) for k,v in report.items() if k not in ['ai_explanations','source_changes']}
            report_context['definition']=bounded_experiment_context(report['definition'],sources)
        selected={'sources':sources,'selected_text':b.selected_text,'experiment':bounded_experiment_context(row['definition'],sources) if row else None,'actual_report':report_context}
        prompt=('你是世界逻辑实验设计助手，只返回 Proposal，不执行求解、不写文件，不改变 Canon/State/Final。只使用下列明确选取内容。'
          '未知参数保留 null，最多问三个必要问题，问题提供作者回答、可选假设、保持未知或演示参数路径。不得编造人口、财政、工业、剧情事实。'
          '严格区分作者确认、已提交事实、计划、参考和假设。未接受假设 accepted=false。'
          '已有验收条件是冻结的；修改仅提出新版本，失败后不能暗改阈值。不得声称模型意见是数学证明。'
          '对抗/推倒重建模式仅给有来源的可能问题、形式化条件、缺口和建议，不能删除或重建正式设定。'
          '报告解释只引用实际输入和 acceptance_results，不能生成新模拟数据。已有实验的对抗/反驳/解释模式令 experiment=null，只给 findings 和可检查参数；验收修改须单独 acceptance 模式。'
          '表达式仅 + - * / **、比较、and/or/not、abs/sqrt/min/max；变量英文标识，单位 Pint 英文。expression 只含表达式，不写变量赋值、单位或自然语言。输出例：id=travel_time, expression=distance/speed, unit=hour；验收 expression=travel_time <= available_time；condition 无条件时为空字符串。禁止使用单等号赋值和 Unicode 比较符号。'
          'solver 仅 z3/graph/formula/schedule；schedule 使用声明的有限资源与整数时间刻度；Z3 除法分母仅常量，事件图用 dependencies；没有可靠社会模型时只提出方案与局限。'
          '对抗强度只控制寻找遗漏/反例的范围，绝不改变数学阈值。探索：找缺失条件；严格：逐条核对；极限：挑战脆弱前提、边界和明确依赖链。'
          '同一基础模型扮演挑战和复核角色不是独立科学证据。SAT 仅形式化可行；UNSAT 仅当前集合冲突；Unsat Core 未证明最小。'
          '发现可量化反例时，用 counterexample_inputs 列出作者尚需确认的参数变量与数值；不要声称已运行。用 rule_ids 关联既有规则。'
          '反驳与补充必须复核已声明的架空规则和缺失前提。社会意见只标 QUALITATIVE/CONDITIONAL_RISK，不做确定历史预测。'
          '\n对抗强度：'+b.strength+'\n任务模式：'+b.mode+'\n作者要求：'+b.instruction+'\n精简实验设计 Schema：'+json.dumps(AIProposal.model_json_schema(),ensure_ascii=False)+'\n已选资料：'+json.dumps(selected,ensure_ascii=False)+'\n精简输出，初次只设计一两个关键公式与验收条件。assumptions 是自然语言字符串；不要返回完整应用元数据。')
        pid=uid('proposal');capsule=safe(self.root(p),'ai-capsules/'+pid);capsule.mkdir(parents=True,exist_ok=True)
        (capsule/'AGENTS.md').write_text('只设计、评论本次给定实验。禁止文件修改、Shell、MCP、联网、读取其他小说和作者秘密。后端保存 Proposal，数学求解交给受控求解器。\n',encoding='utf8')
        from app.codex.adapter import CodexAdapter
        adapter=CodexAdapter(capsule,self.registry.engine,role='CHECKER' if b.mode in ['adversarial','explain','rebuild','rebuttal'] else 'AUTHOR',capsule=True,reasoning_effort='low')
        def complete(text):
            try:value=AIProposal.model_validate_json(text).model_dump()
            except Exception:raise ConsoleError('模型返回的实验方案结构无效，未执行、未修改设定；请缩小范围或更换模型后手动重试',422) from None
            validation_error=None
            if row and b.mode in ['adversarial','rebuild','explain','rebuttal']:
                # A challenge cannot silently introduce a new acceptance contract.
                # Parameter counterexamples remain separate author-confirmed scenarios.
                value['experiment']=None
            if value['experiment']:
                e=value['experiment']
                for variable in e['inputs']:variable['basis']='AI_PROPOSED'
                for rule in e['acceptance_rules']:rule['origin']='AI_PROPOSED';e['experiment_id']=row['id'] if row else uid('exp')
                e['assumptions']=[{'id':'hypothesis_'+str(i),'text':t,'origin':'AI_PROPOSED','accepted':False} for i,t in enumerate(e['assumptions'])]
                e['source_references']=sources
                for group in ['inputs','constraints','dependencies']:
                    for v in e[group]:
                        v['source_ids']=v.get('source_ids',[])
                        if any(id not in {s['id'] for s in sources} for id in v['source_ids']):raise ConsoleError('AI 引用了未选择的依据',422)
                try:value['experiment']=validate(e)
                except ConsoleError as error:
                    value['experiment']=Experiment.model_validate(e).model_dump();validation_error=str(error)
            valid_sources={x['id'] for x in sources}
            for finding in value['findings']:
                if any(id not in valid_sources for id in finding['evidence_source_ids']):raise ConsoleError('反例引用了未选择的依据',422)
                context=value['experiment'] or (row['definition'] if row else None)
                if finding['counterexample_inputs']:
                    declared={v['id'] for v in context['inputs']} if context else set()
                    if any(v['variable'] not in declared for v in finding['counterexample_inputs']):raise ConsoleError('反例参数不属于当前实验',422)
                if context and any(id not in {r['id'] for r in [*context['constraints'],*context['acceptance_rules']]} for id in finding['rule_ids']):raise ConsoleError('反例规则标识无法解析',422)
            if row and b.mode in ['explain','rebuttal'] and value['experiment'] and acceptance_fingerprint(value['experiment'])!=acceptance_fingerprint(row['definition']):raise ConsoleError('结果解释不能改变已锁定验收；请另建验收建议版本',409)
            value=Proposal.model_validate(value).model_dump()
            if value['experiment']:
                value['experiment']['experiment_id']=row['id'] if row else uid('exp')
                # Sources are stamped by application, not accepted on the model's claim.
                refs=value['experiment']['source_references']
                for s in refs:
                    if s['type']!='manual':
                        current=next((x for x in sources if x['type']==s['type'] and x['target_id']==s['target_id']),None)
                        if not current:raise ConsoleError('AI 引用了未授权来源，Proposal 未接受',422)
                        old_id=s['id'];s.update(current);s['id']=old_id
                for assumption in value['experiment']['assumptions']:
                    assumption['origin']='AI_PROPOSED';assumption['accepted']=False
                if len(value['experiment']['assumptions'])>=32:value['experiment']['assumptions']=value['experiment']['assumptions'][:31]
                value['experiment']['assumptions'].append({'id':'ai_review','text':'本方案的输入数值和自然语言到形式化规则均为 AI 候选，作者需逐项检查后接受，不属于新增 Canon。','origin':'AI_PROPOSED','accepted':False})
                try:validate(value['experiment'])
                except ConsoleError as error:validation_error=str(error)
            result={'id':pid,'project_id':p,'mode':b.mode,'created_at':now(),'status':'PROPOSED','value':value,'base_etag':row['etag'] if row else '', 'experiment_id':row['id'] if row else None,'source_ids':b.source_ids,'model':b.model or '当前任务模型','canon_changed':False,'strength':b.strength,'process_stages':['selected_sources','challenge_proposal','await_author_formalization','local_solver_after_freeze','author_judgment'],'evidence_status':'AI_OPINION_NOT_SOLVER_PROOF','validation_error':validation_error}
            from app.creative.tasks import metadata
            result['ai_metadata']=metadata(task.adapter)
            write(safe(self.root(p),'proposals/'+pid+'.json'),result)
            if report and b.mode in ['explain','rebuttal']:
                # New sidecar only; original deterministic report stays immutable.
                result['report_id']=report['id'];write(safe(self.root(p),'proposals/'+pid+'.json'),result)
            return result
        req=TaskRequest(type='world_logic_design',prompt='世界逻辑实验设计（仅发送明确选取的资料）',options=TaskOptions(read_only=True,resume=False,timeout_seconds=240))
        task=manager.prepared(req,prompt,True,'world-logic-ai-'+pid,output_schema=ai_schema(AIProposal),complete=complete,adapter=adapter,provider='Codex',target=row['id'] if row else None,ai_task='world_explain' if b.mode in ['explain','rebuttal'] else 'world_challenge' if b.mode in ['adversarial','rebuild'] else 'world_design',ai_model=b.model,application_actions=True)
        task.private_text=True;manager.store.save(task)
        return task.public()
    def proposal(self,p,id):
        r=read(safe(self.root(p),'proposals/'+identity(id,'proposal')+'.json'))
        if not r or r['project_id']!=p:raise ConsoleError('实验 Proposal 不存在',404)
        return r
    def adopt(self,p,id,b):
        with self.lock:
            proposal=self.proposal(p,id)
            if not b.confirm:raise ConsoleError('请明确接受实验设计稿；此操作不执行求解',422)
            if proposal['status']=='REJECTED':raise ConsoleError('该建议已经拒绝，不能继续采用',409)
            if proposal['status']=='ACCEPTED':return self.get(p,proposal['accepted_id'])
            d=proposal['value']['experiment']
            if not d:raise ConsoleError('本建议尚无完整可编辑实验；请先补充必要参数',409)
            if proposal['experiment_id']:
                if b.experiment_id!=proposal['experiment_id'] or b.etag!=proposal['base_etag']:raise ConsoleError('AI 方案目标或版本已改变，请先人工比较',409)
            result=self.save(p,d,b.etag)
            proposal.update(status='ACCEPTED',accepted_id=result['id'],accepted_at=now());write(safe(self.root(p),'proposals/'+id+'.json'),proposal)
            return result

def public_definition(definition,private=False):
    d=copy.deepcopy(definition)
    if private:return d
    import ast
    mapping={v['id']:'variable_'+str(i+1) for i,v in enumerate(d['inputs'])}
    mapping.update({v['id']:'output_'+str(i+1) for i,v in enumerate(d['outputs'])})
    class Rename(ast.NodeTransformer):
        def visit_Name(self,node):return ast.copy_location(ast.Name(id=mapping.get(node.id,node.id),ctx=node.ctx),node)
        def visit_Call(self,node):
            node.args=[self.visit(x) for x in node.args];return node
    def expression(text):return ast.unparse(Rename().visit(ast.parse(text,mode='eval'))) if text else ''
    for group,label,prefix in [('inputs','变量','variable'),('outputs','计算结果','output'),('constraints','约束','constraint'),('acceptance_rules','验收','rule')]:
        for i,v in enumerate(d[group]):
            v['id']=mapping.get(v['id'],prefix+'_'+str(i+1));v['name']=label+str(i+1)
            if 'expression' in v:v['expression']=expression(v['expression'])
            if 'condition' in v:v['condition']=expression(v['condition'])
            if 'target' in v:v['target']=mapping.get(v['target'],v['target'])
    event_ids={id:'event_'+str(i+1) for i,id in enumerate(sorted({id for e in d['dependencies'] for id in [e['before'],e['after']]}|{e['id'] for e in d.get('events',[])}))}
    for i,e in enumerate(d['dependencies']):e.update(id='dependency_'+str(i+1),before=event_ids[e['before']],after=event_ids[e['after']])
    for i,event in enumerate(d.get('events',[])):
        event['id']=event_ids.get(event['id'],'event_'+str(i+1));event.update(name='事件'+str(i+1),time='',earliest='',latest='',coordinate=None,narrative_order=None,basis='UNKNOWN',source_ids=[],clock='gregorian' if event['clock']=='gregorian' else 'fictional_clock')
    for edge in d['dependencies']:
        if edge.get('condition'):edge['condition']=expression(edge['condition'])
    if d.get('schedule'):
        config=d['schedule'];resources={r['id']:'resource_'+str(i+1) for i,r in enumerate(config['resources'])};operations={o['id']:'operation_'+str(i+1) for i,o in enumerate(config['operations'])}
        for i,r in enumerate(config['resources']):r.update(id=resources[r['id']],name='资源'+str(i+1),capacity=expression(r['capacity']),source_ids=[])
        for i,o in enumerate(config['operations']):o.update(id=operations[o['id']],name='作业'+str(i+1),duration=expression(o['duration']),demand=expression(o['demand']),resource=resources[o['resource']],predecessors=[operations[id] for id in o['predecessors']],release=0,deadline=None,source_ids=[])
        config['horizon']=48
    if d['sensitivity']:d['sensitivity']['variable']=mapping[d['sensitivity']['variable']]
    d['name']='共享实验模板';d['seed']=None
    d['source_references']=[];d['description']='分享模板：未包含原作品的私有参数、来源或设定。';d['scenario_note']='';d['baseline_id']='';d['baseline_version']=None;d['baseline_fingerprint']='';d['baseline_acceptance_fingerprint']=''
    d['assumptions']=[];d['limitations']=['请由使用者重新填写输入、确认前提与验收依据。'];d['steps']=[]
    for v in d['inputs']:v.update(value=None,note='',source_ids=[],minimum=None,maximum=None,basis='UNKNOWN')
    for v in [*d['constraints'],*d['acceptance_rules'],*d['dependencies']]:
        v['source_ids']=[]
        for key in ['meaning','basis','applicability']:
            if key in v:v[key]=''
    return d

def markdown(report,private=False):
    rows=['# 世界逻辑实验报告','',report['definition']['name'] if private else '共享实验报告','','结论：'+report['status'],'','当前结果只覆盖本次输入、假设和验收条件，不能证明世界观整体合理。','',f"实验版本 {report['definition_version']} · 验收指纹 {report['acceptance_fingerprint']}",'','## 实际验收','']
    for i,r in enumerate(report.get('acceptance_results',[])):rows.append('- '+(r['name'] if private else '验收'+str(i+1))+'：'+r['status']+(' — '+r.get('detail','') if private else ''))
    rows+=['','## 运算输出','']
    for i,v in enumerate(report.get('outputs',[])):rows.append('- '+(v['name'] if private else '计算结果'+str(i+1))+'：'+str(v.get('value','未知'))+' '+v.get('unit',''))
    rows+=['','## 局限','']+['- '+v for v in (report.get('limitations',[]) if private else ['仅适用于本次确认的数学前提；数值输出仍可能属于私人资料。'])]
    if private:rows+=['','## 本次输入与假设','','```json',json.dumps(report['definition'],ensure_ascii=False,indent=2),'```']
    else:rows+=['','导出未包含原作品来源文本和输入快照。运算输出仍可能属于私人资料，请分享前检查。']
    return '\n'.join(rows)

def routes(service):
    r=APIRouter(prefix='/api/projects/{p}/world-logic')
    @r.get('')
    def index(p:str):return {'experiments':service.list(p),'templates':service.templates(),'reports':[{k:v for k,v in x.items() if k in ['id','experiment_id','status','created_at','definition_version','total_seconds']} for x in service.reports(p)],'schema':schema()}
    @r.get('/sources')
    def sources(p:str):return service.sources(p)
    @r.get('/source')
    def source(p:str,key:str):return service.source(p,key)
    @r.get('/adapters')
    def adapters(p:str):
        service.registry.get(p)
        from .engine import ADAPTERS
        return {'adapters':ADAPTERS,'optional':[{'extension_id':'pymunk','enabled':False},{'extension_id':'mesa','enabled':False}], 'external_code_installation':False}
    @r.post('/validate')
    def check(p:str,b:Import):service.registry.get(p);return {'definition':parse(b.text),'valid':True}
    @r.post('/experiments')
    def save(p:str,b:Save):return service.save(p,b.definition.model_dump(),b.etag)
    @r.post('/import')
    def import_(p:str,b:Import):
        d=parse(b.text);d['experiment_id']=uid('exp');d['baseline_id']='';d['baseline_version']=None;d['baseline_fingerprint']='';d['baseline_acceptance_fingerprint']=''
        for s in d['source_references']:
            if s['type']!='manual':s.update(type='manual',target_id='',basis='UNKNOWN',sha256='')
        return service.save(p,d)
    @r.get('/experiments/{id}')
    def get(p:str,id:str):return service.get(p,id)
    @r.get('/experiments/{id}/versions')
    def versions(p:str,id:str):return [service.version(p,id,n) for n in range(1,service.get(p,id)['latest_version']+1)]
    @r.post('/experiments/{id}/freeze')
    def freeze(p:str,id:str,b:Freeze):return service.freeze(p,id,b)
    @r.post('/experiments/{id}/run',status_code=202)
    async def run(p:str,id:str,b:Run):return service.run(p,id,b)
    @r.post('/experiments/{id}/scenario')
    def scenario(p:str,id:str,b:Scenario):return service.scenario(p,id,b)
    @r.get('/reports/{id}')
    def report(p:str,id:str):return service.report(p,id)
    @r.post('/reports/{id}/manual-review')
    def manual_review(p:str,id:str,b:ManualReview):return service.manual_review(p,id,b)
    @r.get('/compare')
    def compare(p:str,left:str,right:str):return service.compare(p,left,right)
    @r.post('/design',status_code=202)
    async def design(p:str,b:Design):return service.design(p,b)
    @r.get('/proposals/{id}')
    def proposal(p:str,id:str):return service.proposal(p,id)
    @r.post('/proposals/{id}/accept')
    def accept(p:str,id:str,b:Adopt):return service.adopt(p,id,b)
    @r.get('/experiments/{id}/mapping')
    def mapping(p:str,id:str):return service.mapping(p,id)
    @r.post('/compare-many')
    def compare_many(p:str,b:CompareMany):return service.compare_many(p,b)
    @r.post('/proposals/{id}/counterexample')
    def counterexample(p:str,id:str,b:Counterexample):return service.counterexample(p,id,b)
    @r.post('/proposals/{id}/reject')
    def reject(p:str,id:str):
        with service.lock:
            v=service.proposal(p,id)
            if v['status']=='ACCEPTED':raise ConsoleError('已采用的实验草稿请在实验列表管理',409)
            v.update(status='REJECTED',rejected_at=now());write(safe(service.root(p),'proposals/'+id+'.json'),v)
        return {'id':id,'status':'REJECTED','canon_changed':False}
    @r.post('/proposals/{id}/record-choice')
    def record_choice(p:str,id:str,b:RecordChoice,request:Request):
        with service.lock:
            v=service.proposal(p,id);findings=v['value']['findings']
            if v['status']=='REJECTED':raise ConsoleError('已拒绝建议不再创建采用记录',409)
            operation=b.kind+':'+str(b.finding)+':'+b.target_id
            if operation in v.get('author_choices',{}):return v['author_choices'][operation]
            def recorded(result):
                v.setdefault('author_choices',{})[operation]=result;write(safe(service.root(p),'proposals/'+id+'.json'),v);return result
            if b.finding>=len(findings):raise ConsoleError('建议不存在',404)
            finding=findings[b.finding];text=(finding['title']+'\n条件：'+finding['condition']+'\n建议：'+finding['suggestion']+'\n代价/局限：'+finding.get('tradeoffs','')+'\n来源：World Logic AI Proposal '+id)[:5000]
            if b.kind=='inspiration':
                from app.author_workbench import Entry
                workbench=request.app.state.workbench;entry=workbench.entries(p)
                result=workbench.save_entry(p,Entry(etag=entry['etag'],kind='inspiration',text=text,source='AI_PROPOSED'))
                return recorded({'kind':'inspiration','id':result['notes'][-1]['id'],'canon_changed':False})
            from app.library.bible import Entity
            bible=request.app.state.studio_tools.bible;old=bible.get(p,b.target_id)
            if 'entity:'+b.target_id not in v['source_ids']:raise ConsoleError('只能为作者明确选取的设定建立候选',403)
            candidate={k:x for k,x in old.items() if k not in ['etag','id','version','created_at','updated_at']}
            candidate.update(name=old['name']+' · 推演候选',summary=text[:4000],source='AI_PROPOSED',status='PENDING',canon_level='REFERENCE',locked_fields=[])
            result=bible.save(p,Entity(**candidate).model_dump());return recorded({'kind':'world_proposal','id':result['id'],'status':result['status'],'original_unchanged':True,'canon_changed':False})
    @r.get('/experiments/{id}/export')
    def export(p:str,id:str,format:str='json',include_private:bool=False):
        d=public_definition(service.get(p,id)['definition'],include_private)
        body=yaml.safe_dump(d,allow_unicode=True,sort_keys=False) if format=='yaml' else json.dumps(d,ensure_ascii=False,indent=2)
        return Response(body,media_type='application/yaml' if format=='yaml' else 'application/json',headers={'Content-Disposition':f'attachment; filename="{id}.{format if format in ["json","yaml"] else "json"}"'})
    @r.get('/reports/{id}/export')
    def export_report(p:str,id:str,format:str='markdown',include_private:bool=False):
        v=service.report(p,id)
        if format=='json' and not include_private:
            v={k:x for k,x in v.items() if k not in ['definition','solver_result','dependency_graph','model_influence','calculation_trace','source_changes','ai_explanations','manual_reviews','review_revision']}
            v['acceptance_results']=[{'id':'rule_'+str(i+1),'name':'验收'+str(i+1),'status':row['status']} for i,row in enumerate(v.get('acceptance_results',[]))]
            v['outputs']=[{'id':'output_'+str(i+1),'name':'计算结果'+str(i+1),'value':row.get('value'),'unit':row.get('unit'),'status':row.get('status')} for i,row in enumerate(v.get('outputs',[]))]
            v['unverified']=['部分条件尚未确定；请查看私有原始报告'] if v.get('unverified') else []
            v['limitations']=['结果仅适用于本次确认的数学前提；输出数值仍可能属于私人资料。']
            if v.get('error'):v['error']='执行错误；详情请查看私有原始报告'
            v.pop('sensitivity',None)
            v['sharing_notice']='运算结果可能属于私人资料；已移除输入快照和设定引用。'
        return Response(json.dumps(v,ensure_ascii=False,indent=2) if format=='json' else markdown(v,include_private),media_type='application/json' if format=='json' else 'text/markdown',headers={'Content-Disposition':f'attachment; filename="{id}.{ "json" if format=="json" else "md"}"'})
    return r
