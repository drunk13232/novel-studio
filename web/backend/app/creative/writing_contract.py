"""Small, source-bound writing briefs; no planner, reviewer or story authority.

Only the already approved Writer packet and installed method material enter a
brief. Signals are author review aids, never automatic assertions about Canon.
"""
import json,re
from app.studio_tools import text_hash,utf16_index
from .director_skills import load,METHODS

VERSION='writing-quality-3'
FACT_BOUNDARIES={
 'established':'遵守提供的已确认事实、人物关系、能力与可用知识；计划、猜测和前文叙述的权威不同。',
 'free_now':'可以创造服务当前场景的对白、动作、感官细节和合理反应；无需把每个新细节都视为设定错误。',
 'author_decision':'重大既往经历、新亲属或身份、新能力、改变主线的历史与持久关系变化，先交作者决定；缺证据不等于绝对错误。',
 'disclosure':'读者可见信息不自动成为人物知识。尊重作者授权的全知或限知叙述，但只使用安全包实际授权的信息；未来计划不成为已经发生的事实。'}
ACTIONS={
 'context':['按当前任务、硬事实与知识、邻近正文、远处结构的顺序使用资料；缺失资料保持未知。','区分观察、转述、怀疑、误信和计划，不把摘要升级为事实。'],
 'research':['外部资料只作作者选择的参考；不把真实历史、原作资料或模型推断写成小说既定过去。'],
 'scene':['围绕当前冲突组织行动与后果，在明确的离场条件停止；不替作者完成后续场景。','终点未解决不等于过程停滞：让现场选择、阻力、策略或可核对的小发现改变局面，不循环同一问答凑长度；不强制固定钩子或圆满结尾。'],
 'character':['依据当前利益、知识、关系和说话对象选择词语、句长、隐瞒或试探；允许人物在压力下变化。','让关键回应改变下一步策略；不为每句对白机械附加表情、动作或心理解释。'],
 'writing':['具体细节服务人物、情节或氛围；保留有功能的抒情、比喻、心理和留白。','段落结束后只在有新行动、认识或后果时继续，不为显得完整重复解释。'],
 'style':['以实际文风档案和附近原文为准：叙事距离、节奏、情绪呈现、修辞、留白与声音分别保持。','修订先保留叙事功能和声音，不能以压缩或统一漂亮措辞代替作者文风。'],
 'continuity':['核对当前能观察、知道、到达和使用的内容；不从未来揭示或计划反推现在。','新鲜的现场细节可以写；影响因果的重大新过去保留为作者待确认方案。'],
 'revision':['只修改授权选区，保留人物声音、事实、结果和未选中文本；不顺手重写整章。'],
 'review':['具体定位可核实的原文；区分确定冲突、条件风险、信息不足和文学意见，不强行找错。']}
INPUT_KINDS={
 'context':{'knowledge','state','plan','current','chapter','world'},'scene':{'plan','current','thread','clue'},
 'character':{'character','relationship','knowledge','current'},'style':{'style','current','chapter'},
 'continuity':{'event','state','item','knowledge','world'},'research':{'reference'},
 'writing':{'current','style','plan'},'revision':{'current','style','character'},'review':{'current'}}

def source_priority(source):
    id=source['id'];kind=source['kind']
    if id.startswith('contract:hard:'):return 0
    if kind=='knowledge':return 1
    if kind in {'plan','current'}:return 2
    if kind=='style':return 3
    if kind in {'character','relationship','state'}:return 4
    if kind=='chapter':return 5
    if kind=='creative_material':return 6
    return 7

def compile_methods(engine,keys,packet):
    _,proof=load(engine,keys)
    capsules=[]
    for key in keys:
        sources=[{'sha256':s['sha256'],'name':PathName(s['source'])} for s in proof if s['id']==key]
        inputs=[s['id'] for s in packet.get('sources',[]) if s.get('kind') in INPUT_KINDS.get(key,set())]
        capsules.append({'id':key,'name':METHODS[key][0],'source_hashes':sources,'input_source_ids':inputs,
                         'input_status':'AVAILABLE' if inputs else 'PARTIAL_OR_NOT_APPLICABLE',
                         'actions':ACTIONS.get(key,[]),'basis':'COMPACT_APPLICATION_OF_LOADED_METHOD_NOT_AGENT_PERMISSION'})
    return capsules,proof

def PathName(value):
    # Receipts show source names and hashes; no local user path in model input.
    return value.replace('\\','/').rstrip('/').split('/')[-2:]

def brief(row,packet,index,capsules,rewrite=False):
    step=row['plan']['steps'][index] if not rewrite else {'instruction':row['rewrite']['instruction']}
    sources=packet.get('sources',[])
    enabled=[i for i,s in enumerate(row['plan']['steps']) if s['enabled']]
    position={'current':index+1,'enabled_total':len(enabled),'remaining_after_current':sum(1 for i in enabled if i>index),'is_final_enabled_step':bool(enabled and index==enabled[-1]),'completed_indices':list(row['completed']),'boundary':'Only the current step is requested; do not close the full chapter while later steps remain.'}
    return {'version':VERSION,'goal':row['goal'],'current_step':step,'execution_position':position,
        'latest_author_directions':row.get('interventions',[])[-8:],
        'fact_boundaries':FACT_BOUNDARIES,
        'evidence_roles':[{'source_id':s['id'],'basis':s.get('basis','UNKNOWN'),'kind':s['kind']} for s in sources],
        'selected_methods':capsules,'director_applications':row['plan'].get('method_application',[]),
        'style_source_ids':[s['id'] for s in sources if s['kind']=='style'],
        'continuation':'只写选区替换，保留其他文字。' if rewrite else '从保留草稿末尾接写，不重复已完成的开场、对话或结尾。当前步骤结束立即停止。',
        'judgment':'方法为当前目标服务；作者未要求时，不补哲理总结、不强求和解或解释所有情绪。文学手法本身不被禁止。'}

def observations(output,packet):
    # Narrow temporal reference signals, not a word blacklist or semantic verdict.
    # Missing evidence means review, not FALSE. No automatic deletion or rejection.
    supplied='\n'.join(s.get('text','') for s in packet.get('sources',[]));rows=[]
    pattern=r'(?:[一二三四五六七八九十百\d]{1,5}年前|童年时|小时候|那年(?:春|夏|秋|冬|他|她))'
    for match in re.finditer(pattern,output):
        a=max(output.rfind('。',0,match.start()),output.rfind('\n',0,match.start()))+1
        ends=[v for v in (output.find('。',match.end()),output.find('\n',match.end())) if v>=0]
        b=min(ends)+1 if ends else min(len(output),match.end()+100)
        quote=output[a:b][:250]
        if quote and quote not in supplied and not any(x['quote']==quote for x in rows):
            rows.append({'code':'PAST_REFERENCE_REVIEW','quote':quote,'start':utf16_index(output,a),
             'end':utf16_index(output,a+len(quote)),'status':'NEEDS_CONTEXT_NOT_PROVEN_ERROR',
             'message':'此处涉及过去，所给资料未直接支持整句；可能合理，需结合作者设定复核，不自动改写。'})
        if len(rows)>=8:break
    repeated=[];seen={}
    for match in re.finditer(r'[^\n]+(?:\n(?!\s*\n)[^\n]+)*',output):
        text=match.group().strip();a=match.start()+len(match.group())-len(match.group().lstrip());b=a+len(text)
        if len(text)<80:continue
        if text in seen and len(repeated)<6:
            first=seen[text];repeated.append({'quote':text[:200],'first':{'start':utf16_index(output,first),'end':utf16_index(output,first+len(text))},'repeat':{'start':utf16_index(output,a),'end':utf16_index(output,b)},'status':'AUTHOR_REVIEW_NOT_AUTOMATIC_ERROR'})
        else:seen[text]=a
    return {'version':VERSION,'repeated_passage_signals':repeated,'past_reference_signals':rows,'semantic_review':'NOT_RUN',
            'basis':'DETERMINISTIC_POINTERS_NOT_FACT_OR_LITERARY_VERDICT','text_sha256':text_hash(output)}
