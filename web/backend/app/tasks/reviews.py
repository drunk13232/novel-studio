"""Persist author-side review and expose only typed safe revision directions."""
import uuid
from app.domain.tasks import ReviewReport
from app.errors import ConsoleError
from app.projects.foundation import schema
from app.tasks.router import core_workflow

REVIEW_TASKS={'chapter_review','continuity_check','character_check','contract_check','sepia_review',
              'story_structure_review','scene_review','dialogue_review','pacing_review'}


def prepare(manager,request,prompt,scope):
    ws=manager.workspace
    row=ws.chapter(request.chapter)
    source=row.get('draft') or row.get('final')
    body=ws.content(source)
    w=core_workflow(manager.engine)
    prompt+='\n只返回指定 ReviewReport JSON。paragraph 使用正文 splitlines 的 1 基行号。'
    def complete(output):
        report=ReviewReport.model_validate_json(output).model_dump()
        if ws.content(source)['etag']!=body['etag']:raise ConsoleError('正文已变化，审稿报告已拒绝',409)
        for issue in report['issues']:
            if issue['severity'].upper() in ['HARD','ERROR','FAIL'] or issue['code'] in ['KNOWLEDGE_LEAK','UNSUPPORTED_POV']:
                issue['priority']='MUST FIX'
        if any(i['priority']=='MUST FIX' for i in report['issues']):report['verdict']='FAIL'
        report.update(audience='CHECKER',body_sha256=body['etag'],source_path=source,report_only=True)
        path=f'reviews/chapter-{request.chapter}/review-{request.type}-{uuid.uuid4().hex}.yaml'
        w.y.write(ws.resolve(path,allow_reviews=True),report)
        # Full chapter review owns the combined feedback. A style specialist must
        # not replace it and accidentally erase outstanding Canon/POV problems.
        if request.type=='chapter_review':
            w.y.write(ws.resolve(f'reviews/chapter-{request.chapter}/revision-feedback.yaml',allow_reviews=True),report)
        return {**report,'saved_path':path}
    return manager.prepared(request,prompt,True,scope,schema(ReviewReport),complete,target=source)
