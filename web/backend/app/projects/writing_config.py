"""Optional writing preferences; absent legacy fields are read as long fiction."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

Form = Literal['short','novella','novel','anthology','undecided']
LABELS = {'short':'短篇','novella':'中篇','novel':'长篇','anthology':'短篇合集','undecided':'暂不确定'}

class WritingConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    form: Form = 'novel'
    target_characters: int | None = Field(default=None,ge=0)
    structure_mode: Literal['free','scenes','chapters'] = 'chapters'
    planning_depth: Literal['minimal','standard','detailed'] = 'standard'
    interview_depth: Literal['quick','standard','deep'] = 'standard'
    auto_suggestions: bool = False
    template_id: str = Field(default='free',max_length=100)
    structure_reference: str = Field(default='free',max_length=100)
    body_id: str | None = Field(default=None,pattern=r'^story_[0-9a-f]{32}$')

def defaults(form='novel'):
    return WritingConfig(form=form,structure_mode='free' if form in {'short','anthology','undecided'} else 'chapters',
        planning_depth='minimal' if form in {'short','anthology','undecided'} else 'standard',
        interview_depth='quick' if form in {'short','anthology','undecided'} else 'standard').model_dump()

def writing(manifest):
    value=manifest.get('writing')
    return WritingConfig.model_validate(value).model_dump() if value else defaults()

def story_row(ws,manifest,include_text_counts=True):
    """One stable manuscript document, without inventing a Chapter 1."""
    cfg=writing(manifest)
    if not cfg['body_id']:return None
    files=[f for f in ws.list_files() if f['path'].startswith('chapters/story/') and
           (f['name'] in {'draft.txt','final.txt'} or f['name'].startswith('manual-') and f['name'].endswith('.txt'))]
    revisions=sorted([f for f in files if f['name'].startswith('manual-')],key=lambda f:f['modified_at'],reverse=True)
    final=next((f for f in files if f['name']=='final.txt'),None)
    draft=next((f for f in files if f['name']=='draft.txt'),None)
    candidates=[*revisions,*([draft] if draft else []),*([final] if final else [])]
    chosen=max(candidates,key=lambda f:(f['modified_at'],f==final)) if candidates else None
    from app.studio import body_counts
    return {'id':cfg['body_id'],'card_id':cfg['body_id'],'card_id':cfg['body_id'],'number':0,'order':0,'title':manifest['title'],
        'kind':'story','volume':None,'volume_id':None,'path':chosen['path'] if chosen else None,
        'draft':draft['path'] if draft else None,'final':final['path'] if final else None,
        'final_path':final['path'] if final else None,'status':'FINAL' if final and chosen==final else 'DRAFT',
        'missing_title':False,'modified_at':chosen['modified_at'] if chosen else None,
        'versions':[{'path':f['path'],'label':'正式稿' if f==final else '修订稿' if f in revisions else '草稿'} for f in [*revisions,*([final] if final else []),*([draft] if draft else [])]],
        **body_counts(ws.content(chosen['path'])['content'] if chosen and include_text_counts else '',strip_header=False)}
