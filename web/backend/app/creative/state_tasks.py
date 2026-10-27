"""Data-only stage adapter over existing Skills, TaskManager and state mechanics.
The model returns evidence-bound review/extraction data. Only the application
writes reports/proposals; State Commit stays in the original local engine.
"""
import json,copy
from typing import Literal
from pydantic import Field,create_model
from app.errors import ConsoleError
from app.models.requests import TaskRequest,TaskOptions
from app.tasks.router import core_workflow
from app.projects.foundation import schema
from app.library.storage import digest,write,now
from app.studio_tools import normalized
from .writing import Strict
from .tasks import adapter,metadata

class Finding(Strict):
    source:Literal['BODY','INPUT']='BODY'
    priority:Literal['MUST FIX','SHOULD FIX','SUGGESTION','STYLE ONLY']
    message:str=Field(max_length=1000)
    evidence:str=Field(default='',max_length=1200)
class Semantic(Strict):
    kind:Literal['contract','continuity','character','scene_plot','style']
    result:Literal['PASS','FAIL','INCONCLUSIVE']
    reviewed_rules:list[str]=Field(min_length=1,max_length=12)
    findings:list[Finding]=Field(default_factory=list,max_length=12)
class Finals(Strict):reviews:list[Semantic]=Field(min_length=5,max_length=5)
class Evidence(Strict):
    text:str=Field(max_length=1200)
    evidence:str=Field(min_length=1,max_length=1600)
class Operation(Strict):
    file:str=Field(max_length=200)
    pointer:str=Field(max_length=300)
    before_json:str=Field(max_length=22000)
    after_json:str=Field(max_length=22000)
    evidence:str=Field(min_length=1,max_length=1600)
class DiffReview(Strict):
    result:Literal['PASS','FAIL','INCONCLUSIVE']
    verified_operations:list[str]=Field(max_length=80)
    extraction_complete:bool
    findings:list[Finding]=Field(default_factory=list,max_length=15)

SKILLS={'final':['novel-contract-checker','novel-continuity-checker','novel-character-checker','novel-plot-checker','novel-style-reviewer'],
        'memory':['novel-memory-keeper'],'validate':['novel-state-commit']}

def prepare(s,p,path,revision,stage,proposal_id=None,writing_report=None,story_time=''):
    ws=s.tools.writable(p);w=core_workflow(s.registry.engine);doc=s.tools.doc(p,path);_,n,card=s.tools.chapter(p,path)
    if doc['etag']!=revision:raise ConsoleError('正文已经变化，请刷新后重试',409)
    state=w.load_state(ws.root)
    if any(e['chapter']==n for e in state['chapter-ledger.yaml']['entries']):raise ConsoleError('本章已提交，不覆盖历史 Final / Memory，请使用独立修订流程',409)
    base=w.digest(state);authority=w.authority_digest(ws.root)
    if stage=='memory':
        try:anchor=w.timestamp(story_time)
        except (ValueError,TypeError):raise ConsoleError('Memory 需要作者明确填写带时区的本章结束状态时间；不会从大纲猜测',409) from None
        prior=state['current-story-state.yaml']['project'].get('story_date')
        if prior and anchor<w.timestamp(prior):raise ConsoleError('结束状态时间不能早于当前基线；回忆事件另行标时',409)
    from model import MEMORY_KEYS,SCHEMAS
    body=normalized(doc);plan=card or {}
    packet=w.role_context(ws.root,plan,'CHECKER',body=body)
    data={'project_id':p,'chapter':n,'source_path':path,'source_revision':revision,'checker_view':packet}
    if stage!='final':
        final=w.y.read(ws.resolve(f'reviews/chapter-{n}/final.yaml',allow_reviews=True));w.verify_final(ws.root,final)
        if final['body_path']!=path or final['body_sha256']!=revision:raise ConsoleError('Final witness 不是当前版本',409)
        data['final']=final
    methods=[];proof=[]
    for key in SKILLS[stage]:
        f=s.registry.engine/'.agents/skills'/key/'SKILL.md'
        if not f.is_file():raise ConsoleError('缺少已有项目 Skill：'+key,409)
        text=f.read_text('utf-8-sig');methods.append(key+'\n'+text);proof.append({'id':key,'sha256':digest(f.read_bytes()),'delivered_characters':len(text)})
    if writing_report:data['author_reviewed_observations']=json.loads(ws.content(writing_report,allow_reviews=True)['content'])
    if stage=='final':
        output=Finals;instructions='Perform the five actual semantic reviews of this exact complete BODY against the supplied Checker view. Review contract, continuity/knowledge/POV, character, scene/plot and style separately. Return precisely one result per kind. Missing essential evidence is INCONCLUSIVE, not PASS. MUST FIX blocks. Optional style preferences do not force rewriting. Report genuine findings and concrete checked rules; do not manufacture PASS. No manuscript revision.'
    elif stage=='memory':
        data['author_state_time']={'value':story_time,'basis':'EXPLICIT_AUTHOR_END_STATE_ANCHOR_NOT_INFERRED_FROM_OUTLINE'}
        output=create_model('MemoryCandidates',__base__=Strict,**{k:(list[Evidence],Field(default_factory=list,max_length=40)) for k in MEMORY_KEYS},operations=(list[Operation],Field(max_length=80)))
        data['state_schemas']=SCHEMAS['$defs'];data['memory_categories']=MEMORY_KEYS
        instructions='Use the actual Memory Keeper method to extract consequential, complete state changes from semantic Final BODY only. Plans, scenarios and discussion are not facts. Attributed claims and beliefs never grant objective truth. Every category entry and operation needs exact BODY evidence. Only actual changes. Empty categories are valid. Output all categories. Operations use existing state filenames, simple JSON pointers, exact before-values and after-values serialized as JSON strings. No whole-document replacement. Append lists at index equal to their length; never copy a whole timeline to append one event. All new events have stable IDs, chapter and explicit timezone story_time. Do not infer calendar dates from the outline. Use the explicit author_state_time as the author-confirmed end/as-of anchor, not a claim of exact event timing. Preserve uncertainty of intra-chapter event times. Conservative acquired/view times must not grant knowledge before it is established. Advance current-story-state.yaml /project/story_date to that anchor when needed. No invented future meeting dates. New knowledge needs introduced_chapter, acquired_chapter, source_event, story_time and synchronized character knowledge projection. Update item holder/inventory consistently, actual location and physical condition, relationship and source-visible writer_view entries; replace superseded current views without manufacturing historical facts. PUBLIC/CHARACTER views need known_by, since_chapter, story_time. Preserve old unrelated facts. Do not modify Canon, existing canonical_truth, revision or current_chapter. Use schema-complete records. Do not claim future meetings already occurred. You generate only a Proposed candidate; author approval and separate semantic Diff review are still required.'
    else:
        value=w.y.read(ws.resolve('state/proposed/'+proposal_id+'.yaml'));w.candidate(ws.root,value)
        data['proposal']=value
        data['operation_targets']=[o['file']+o['pointer'] for o in value['extraction']['operations']]
        instructions='Perform actual SEMANTIC_DIFF_REVIEW: compare every operation and all extraction categories with exact Final BODY, current State and character knowledge receipts. Check completeness of consequential changes, actual occurrence versus claim, plan or inference, synchronization, times and sources, inventory/holder consistency, preserving existing facts and Writer views. verified_operations must copy the exact supplied operation_targets strings, in original order, after actual review. No inserted spaces or separators. A character utterance alone does not require promotion to true character knowledge; preserve source UNKNOWN when acquisition is not established, while checking the claim and observable action are recorded. Preserve established injuries unless positive healing evidence replaces them. PASS only if every operation is correct and extraction_complete is true. Report missing or unsupported changes instead of approving automatically. Do not change the proposal or weaken rules.'
        output=DiffReview
    prompt='Use only supplied project data and method source text. No tools, filesystem access, shell, scripts, network, subagents or State commits. Return schema JSON in Chinese. '+instructions+' Every finding evidence must be an exact contiguous quote with no ellipsis or paraphrase. Use source BODY for manuscript quotations, INPUT for supplied State, Canon or plan quotations. Empty evidence is allowed only for an unanchored suggestion, never a factual conflict.\nMETHODS:\n'+'\n\n'.join(methods)+'\nINPUT:\n'+json.dumps(data,ensure_ascii=False)
    if len(prompt)>160000:raise ConsoleError('当前完整语义资料超过安全文本上限；请使用现有工程流程，不会截断后假称完整审核',413)
    a=adapter(s.center,p,'fact_extract',prompt,'codex',role='CHECKER')
    def complete(raw):
        result=output.model_validate_json(raw).model_dump()
        with s.tools.lock,s.lock,ws._save_lock:
            if s.tools.doc(p,path)['etag']!=revision or w.digest(w.load_state(ws.root))!=base or w.authority_digest(ws.root)!=authority:raise ConsoleError('正文、设定或 State 在任务期间变化，结果未写入，请重新核对',409)
            reviewer='MODEL '+str(metadata(a).get('backend','UNKNOWN'))+' / '+str(metadata(a).get('observed_model') or metadata(a).get('model','UNKNOWN'))
            if stage=='final':
                write(ws.resolve(f'reviews/chapter-{n}/semantic-final-candidates.json',allow_reviews=True),{'result':result,'source_revision':revision,'skill_proof':proof,'ai_metadata':metadata(a),'at':now(),'status':'UNVERIFIED_UNTIL_EVIDENCE_CHECK'})
                if {r['kind'] for r in result['reviews']}!=set(w.REVIEW_KINDS):raise ConsoleError('未完整返回五类语义审查',422)
                reviews={};passed=True
                for r in result['reviews']:
                    valid=r['result']=='PASS' and not any(f['priority']=='MUST FIX' for f in r['findings']);passed=passed and valid
                    for f in r['findings']:
                        evidence_source=body if f['source']=='BODY' else json.dumps(data,ensure_ascii=False)
                        if f['evidence'] and f['evidence'] not in evidence_source:raise ConsoleError('语义审查引用不存在的正文，结果未确认',422)
                    rel=f'reviews/chapter-{n}/final-{r["kind"]}.yaml';reviews[r['kind']]=rel
                    w.y.write(ws.resolve(rel,allow_reviews=True),{**r,'result':'PASS' if valid else r['result'] if r['result']!='PASS' else 'FAIL','coverage':'SEMANTIC_REVIEW','reviewer':reviewer,'body_sha256':revision,'reviewed_rules':r['reviewed_rules'],'findings_resolved':valid,'skill_proof':proof,'ai_metadata':metadata(a)})
                if not passed:raise ConsoleError('语义 Final 未通过；已保存实际分级报告，请先处理阻塞项',409)
                witness=w.final_witness(ws.root,path,n,reviews);w.y.write(ws.resolve(f'reviews/chapter-{n}/final.yaml',allow_reviews=True),witness)
                return {'stage':stage,'result':'PASS','witness':f'reviews/chapter-{n}/final.yaml','skill_proof':proof,'ai_metadata':metadata(a)}
            if stage=='memory':
                def decode(value):
                    try:return json.loads(value,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('non-finite JSON')))
                    except (ValueError,TypeError):raise ConsoleError('Memory 候选包含无效 JSON 值，未生成 Diff',422) from None
                observations={k:result[k] for k in MEMORY_KEYS};observations['operations']=[{'file':o['file'],'pointer':o['pointer'],'before':decode(o['before_json']),'after':decode(o['after_json']),'evidence':o['evidence']} for o in result['operations']]
                extraction=w.extract(ws.root,final,observations)
                from uuid import uuid4
                id=f'chapter-{n}-'+uuid4().hex[:12];v=w.propose(ws.root,final,extraction,id)
                v['author_state_time']={'value':story_time,'basis':'EXPLICIT_AUTHOR_END_STATE_ANCHOR','source_revision':revision};w.y.write(ws.resolve('state/proposed/'+id+'.yaml'),v)
                w.y.write(ws.resolve(f'reviews/chapter-{n}/memory-{id}.yaml',allow_reviews=True),extraction)
                try:
                    updated=w.candidate(ws.root,v)
                    if updated['current-story-state.yaml']['project']['story_date']!=story_time:raise ValueError('结束状态时间未与作者确认的锚点同步')
                except (ValueError,KeyError,IndexError,TypeError) as e:raise ConsoleError('已保留 Memory / Proposed，但结构校验未通过：'+str(e)[:600],409) from None
                return {'stage':stage,'result':'PROPOSED','proposal_id':id,'operations':len(observations['operations']),'skill_proof':proof,'ai_metadata':metadata(a),'state_commit_required':True}
            if w.digest(w.y.read(ws.resolve('state/proposed/'+proposal_id+'.yaml')))!=w.digest(value):raise ConsoleError('Proposed 在审查期间变化，未确认旧版本',409)
            targets=[o['file']+o['pointer'] for o in value['extraction']['operations']]
            ok=result['result']=='PASS' and result['extraction_complete'] and result['verified_operations']==targets and not any(f['priority']=='MUST FIX' for f in result['findings'])
            rel='state/proposed/'+proposal_id+'.review.yaml'
            w.y.write(ws.resolve(rel),{**result,'result':'PASS' if ok else 'FAIL','coverage':'SEMANTIC_DIFF_REVIEW','reviewer':reviewer,'proposal_sha256':w.digest(value),'skill_proof':proof,'ai_metadata':metadata(a)})
            if not ok:raise ConsoleError('语义 Diff 审查未通过；保留候选与实际报告，未提交状态',409)
            receipt=w.validate_proposal(ws.root,value)
            return {'stage':stage,'result':receipt['result'],'proposal_id':proposal_id,'skill_proof':proof,'ai_metadata':metadata(a)}
    request=TaskRequest(type={'final':'final_check','memory':'memory_extract','validate':'state_validate'}[stage],chapter=n,options=TaskOptions(read_only=True,resume=False,timeout_seconds=600))
    task=s.manager(p).prepared(request,prompt,True,'state-'+str(n)+'-'+stage,schema(output),complete,adapter=a,application_actions=True,target=path)
    task.private_text=True
    return task
