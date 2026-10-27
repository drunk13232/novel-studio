"""Writer-only execution: filtered bytes, fresh thread, no author filesystem."""
import hashlib
import json
import uuid
import os
from pathlib import Path
from app.errors import ConsoleError
from app.tasks.router import core_workflow
from app.codex.adapter import CodexAdapter
from app.atomic import replace
from app.integrations.stack import resources

WRITER_TASKS = {'chapter_write', 'chapter_revise', 'sepia_refactor', 'voice_preserving_revision'}
POLICY = '''只使用给定 Writer View 与安全修订指令；缺少必需信息返回 NEEDS_CONTEXT。
写作通过行动后果、人物诉求、错误判断、现实阻力与环境细节传递信息。
材料只保留影响当前选择的差异；专业对白只回答人物此刻需要解决的问题。
保留原有声音。MUST FIX 必修；SHOULD FIX 仅高置信；SUGGESTION 保留；STYLE ONLY 默认不改。
Sepia Optional；仅明确选定 sepia_refactor 时做局部语言修改。不得自动统一句式或声音。
只返回正文或修订候选文本；不访问外部文件，不调用其他角色或插件，不更新状态。
'''


def prepare(manager, request):
    w = core_workflow(manager.engine)
    from knowledge_isolation import require_safe_review, revision_feedback, assert_no_hidden, hidden_texts
    ws = manager.workspace
    row = ws.chapter(request.chapter)
    if not row['plan']:
        raise ConsoleError('需要本章生产计划和 Writer Safety Review',409)
    plan = w.y.read(ws.resolve(row['plan']))
    # No unreviewed manual context file is trusted. Rebuild from current authority.
    packet = w.context(ws.root, plan, request.options.scene_id)
    review_path=f'reviews/chapter-{request.chapter}/writer-safety.yaml'
    if not ws.resolve(review_path,allow_reviews=True).is_file():
        raise ConsoleError('需要本次 Writer Safety Review，请先运行 Context Build',409)
    review = w.y.read(ws.resolve(review_path,allow_reviews=True))
    require_safe_review(packet,review)
    state = w.load_state(ws.root)
    allowed = {f['fact_id'] for f in packet['pov_knowledge']['known']+packet['pov_knowledge']['scene_disclosures']}
    hidden = hidden_texts(state,plan,allowed)
    source = row['draft'] or row['final']
    revision = request.type != 'chapter_write'
    payload = {'writer_view':packet, 'operation':request.type}
    selected_skill = ''
    if request.type=='voice_preserving_revision':
        selected_skill,_=resources(manager.engine,'novel',['style-fidelity.md','cognition-layers-and-language.md'])
    elif request.type=='sepia_refactor':
        base=Path(os.environ['USERPROFILE'])/'.codex/plugins/cache/sepia/sepia/0.12.3/skills'
        selected_skill='\n\n'.join((base/name/'SKILL.md').read_text(encoding='utf-8-sig') for name in ['sepia','sepia-refactor'])
    if request.options.scene_id:
        payload['scope']='仅当前场景；输出独立场景候选，不视为整章 Draft 或 Final。'
    source_hash = None
    if revision:
        if not source: raise ConsoleError('修订需要现有正文',409)
        source_row = ws.content(source)
        raw = source_row['content']
        source_hash = source_row['etag']
        feedback_path=ws.resolve(f'reviews/chapter-{request.chapter}/revision-feedback.yaml',allow_reviews=True)
        if not feedback_path.is_file():raise ConsoleError('需要绑定当前正文的合并审稿反馈，请先运行 Chapter Review',409)
        feedback = w.y.read(feedback_path)
        if feedback.get('body_sha256') != source_hash:
            raise ConsoleError('修订反馈与正文不匹配',409)
        payload['revision'] = revision_feedback(feedback,raw)
        assert_no_hidden(payload,hidden)
    elif row['draft'] or row['final']:
        raise ConsoleError('本章已有正文；请使用修订候选入口',409)
    # Research and free-form reviewer/user instructions are author inputs. They
    # must be approved in the packet, never concatenated to the Writer prompt.
    if request.options.research_ids or request.prompt:
        raise ConsoleError('Writer 的附加要求/资料请先纳入并审查安全 Context，不能直接拼接作者输入',409)
    capsule = manager.engine/'web/writer-runs'/ws.root.name/uuid.uuid4().hex
    capsule.mkdir(parents=True)
    (capsule/'AGENTS.md').write_text(POLICY,encoding='utf8')
    skill = capsule/'.agents/skills/novel-safe-writer/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('---\nname: novel-safe-writer\ndescription: 在隔离安全包内写作或修订单章。\n---\n'+POLICY,encoding='utf8')
    prompt=POLICY+'\n定向技能参考（通用技法，事实只取 Writer View）：\n'+selected_skill+'\nINPUT JSON:\n'+json.dumps(payload,ensure_ascii=False)
    (capsule/'input.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf8')
    adapter = CodexAdapter(capsule,manager.engine,role='WRITER')
    def complete(output):
        # Revalidate authority and target before publishing a result.
        if w.context(ws.root,w.y.read(ws.resolve(row['plan'])),request.options.scene_id) != packet:
            raise ConsoleError('写作期间 Context 已变化，输出不应用',409)
        if source and ws.content(source)['etag']!=source_hash:
            raise ConsoleError('写作期间原稿已变化，输出不应用',409)
        if not output.strip() or 'NEEDS_CONTEXT' in output:
            raise ConsoleError('Writer 请求补充安全 Context，未保存正文',409)
        assert_no_hidden(output,hidden)
        target=f'reviews/chapter-{request.chapter}/revision-candidate-{uuid.uuid4().hex}.txt' if revision else f'chapters/chapter-{request.chapter}/draft.txt'
        if request.options.scene_id:
            target=f'reviews/chapter-{request.chapter}/scene-candidate-{uuid.uuid4().hex}.txt'
        path=ws.resolve(target,allow_reviews=True)
        if path.exists(): raise ConsoleError('目标已存在，输出不覆盖',409)
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.pending')
        temp.write_text(output,encoding='utf8');replace(temp,path)
        return {'saved_path':target,'audience':'WRITER','revision_candidate':revision,
                'requires_final_check':True,'context_sha256':packet['packet_sha256']}
    return manager.prepared(request,prompt,True,f'writer-chapter-{request.chapter}',complete=complete,
                            target=source,adapter=adapter)
