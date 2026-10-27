from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.ai.controls import RequestControls

TaskType = Literal['world_logic_run','world_logic_design','writing_analysis','reference_analyze', 'creation_interview', 'chapter_plan', 'chapter_write', 'chapter_review', 'chapter_revise',
                   'context_build', 'continuity_check', 'character_check', 'contract_check',
                   'sepia_review', 'sepia_refactor', 'story_structure_review', 'scene_review',
                   'dialogue_review', 'pacing_review', 'memory_extract', 'state_validate',
                   'state_commit', 'custom_prompt', 'chapter_pipeline', 'final_check', 'story_architect',
                   'story_architect_refine','world_expand','character_create','character_refine','master_outline_generate','volume_outline_generate','character_consistency_check','character_difference_check','volume_outline_refine','chapter_skeleton_generate','chapter_cards_deepen','chapter_plan_refine','chapter_plan_review',
                   'story_continuity_check','story_knowledge_check','story_timeline_check','story_voice_check','story_context_build','story_links_check','story_doctor','story_names_check','research_topic','pov_review','voice_preserving_revision']


class TaskOptions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    read_only: bool = False
    resume: bool = True
    timeout_seconds: int = Field(default=600, ge=30, le=1800)
    proposal_path: str | None = Field(default=None, max_length=240)
    writing_report: str | None = Field(default=None,max_length=300)
    confirm_state_commit: bool = False
    confirm_pipeline: bool = False
    research_ids: list[str] = Field(default_factory=list,max_length=5)
    scene_id: str | None = Field(default=None,max_length=100)
    ai_controls:RequestControls|None=None


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: TaskType
    chapter: int | None = Field(default=None, ge=1, le=99999)
    prompt: str | None = Field(default=None, max_length=12000)
    options: TaskOptions = Field(default_factory=TaskOptions)

    @model_validator(mode='after')
    def validate_task(self) -> 'TaskRequest':
        if self.type in {'world_logic_run','world_logic_design','writing_analysis','creation_interview','reference_analyze'}:
            if self.chapter is not None:raise ValueError('创作访谈不生成章节')
        elif self.type == 'custom_prompt':
            if not self.prompt or not self.prompt.strip():
                raise ValueError('自定义任务需要自然语言指令')
        elif self.type not in ['state_validate', 'state_commit','story_architect','story_architect_refine','world_expand','character_create','character_refine','master_outline_generate','volume_outline_generate','character_consistency_check','character_difference_check','volume_outline_refine','chapter_skeleton_generate','chapter_cards_deepen','chapter_plan_refine','chapter_plan_review','research_topic','story_continuity_check','story_knowledge_check','story_timeline_check','story_voice_check','story_context_build','story_links_check','story_doctor','story_names_check'] and self.chapter is None:
            raise ValueError('请选择有效章号')
        if self.options.writing_report and self.type!='memory_extract':raise ValueError('事实候选仅可交给 Memory Keeper')
        if self.type == 'state_commit' and not self.options.confirm_state_commit:
            raise ValueError('State Commit 必须明确确认')
        if self.type == 'chapter_pipeline' and not self.options.confirm_pipeline:
            raise ValueError('完整章节流程必须明确确认；State Commit 不在其中')
        if self.type != 'state_commit' and self.options.confirm_state_commit:
            raise ValueError('其他任务不能附带 State Commit 授权')
        return self


class FileWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(min_length=1, max_length=300)
    content: str = Field(max_length=2 * 1024 * 1024)
    etag: str = Field(min_length=64, max_length=64)
