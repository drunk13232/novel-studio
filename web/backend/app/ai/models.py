"""Typed, non-sensitive AI preferences. Unknown capabilities stay unknown."""
from pydantic import BaseModel, ConfigDict, Field,field_validator
from typing import Literal

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class Parameters(Strict):
    temperature:float|None=Field(default=None,ge=0,le=2)
    top_p:float|None=Field(default=None,ge=0,le=1)
    max_output_tokens:int|None=Field(default=None,ge=1,le=1000000)
    reasoning_effort:Literal['none','minimal','low','medium','high','xhigh','max','ultra']|None=None
    thinking:Literal['enabled','disabled']|None=None
    stop:list[str]|None=Field(default=None,max_length=4)
    frequency_penalty:float|None=Field(default=None,ge=-2,le=2)
    presence_penalty:float|None=Field(default=None,ge=-2,le=2)
    seed:int|None=Field(default=None,ge=0,le=2147483647)
    top_k:int|None=Field(default=None,ge=1,le=1000)
    streaming:bool=True
    timeout:int=Field(default=120,ge=5,le=1800)
    @field_validator('stop')
    @classmethod
    def bounded_stop(cls,value):
        if value is not None and any(not s or len(s)>500 for s in value):raise ValueError('停止序列需为 1～500 字符')
        return value

class Model(Strict):
    id:str=Field(min_length=1,max_length=160,pattern=r'^[^\s\x00-\x1f]+$')
    display_name:str=Field(default='',max_length=120)
    protocol:Literal['chat','responses']='chat'
    context_length:int|None=Field(default=None,ge=1)
    output_limit:int|None=Field(default=None,ge=1)
    capabilities:dict[str,bool|None]=Field(default_factory=lambda:{k:None for k in ['streaming','structured','tools','vision','reasoning','temperature','top_p']})
    reasoning_levels:list[str]=Field(default_factory=list,max_length=12)
    capability_source:Literal['UNKNOWN','USER','OFFICIAL_METADATA','OFFICIAL_DOCS','TESTED']='UNKNOWN'
    capability_note:str=Field(default='',max_length=1000)
    parameter_rules:dict[str,dict]=Field(default_factory=dict,max_length=15)
    favorite:bool=False
    chat_token_parameter:Literal['max_tokens','max_completion_tokens']|None=None
    input_price:float|None=Field(default=None,ge=0)
    output_price:float|None=Field(default=None,ge=0)
    currency:str=Field(default='USD',pattern=r'^[A-Z]{3}$')
    parameters:Parameters=Field(default_factory=Parameters)
    @field_validator('reasoning_levels')
    @classmethod
    def levels(cls,value):
        if set(value)-{'none','minimal','low','medium','high','xhigh','max','ultra'} or len(value)!=len(set(value)):raise ValueError('无效或重复的推理档位')
        return value
    @field_validator('parameter_rules')
    @classmethod
    def rules(cls,value):
        allowed={'temperature','top_p','top_k','frequency_penalty','presence_penalty','seed','stop'}
        if set(value)-allowed or any(set(v)-{'minimum','maximum','disabled_when_thinking'} for v in value.values()):raise ValueError('参数规则仅允许受支持字段的范围与思考限制')
        for v in value.values():
            if any(k in v and not isinstance(v[k],(int,float)) for k in ['minimum','maximum']):raise ValueError('参数范围必须是数值')
        return value

class Provider(Strict):
    provider_id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,100}$')
    display_name:str=Field(min_length=1,max_length=100)
    provider_type:str=Field(default='custom',max_length=40)
    protocol:Literal['chat','responses']='chat'
    base_url:str=Field(min_length=1,max_length=500)
    credential_reference:str|None=None
    auth_header:Literal['Authorization','X-API-Key','Api-Key']='Authorization'
    available_models:list[Model]=Field(default_factory=list,max_length=2000)
    default_model:str|None=None
    enabled:bool=True
    timeout:int=Field(default=120,ge=5,le=1800)
    retry_policy:Literal['none']='none'
    connection_status:str='UNVERIFIED'

TASKS={'experiments':'世界逻辑实验设计','interview':'新建小说访谈','brainstorm':'故事构思','character':'人物设定','world':'世界观补充','outline':'大纲辅助','expand':'文本扩写','polish':'文本润色','dialogue':'对白优化','style':'文风分析','research':'文献问答','review':'普通审稿','workflow':'复杂章节工作流','files':'文件与 State 操作'}
TASKS.update({'roleplay':'角色扮演','roleplay_memory':'场景记忆整理','behavior':'人物行为与情景分析',
 'world_design':'世界实验设计','world_challenge':'世界逻辑对抗','world_explain':'实验结果复核',
 'review_structure':'文学结构与因果评审','review_character':'人物与知识边界评审',
 'review_language':'对白与语言评审','review_reader':'读者体验评审'})
TASKS.update({'scene_design':'AI 场景导演','cowrite':'选区协写','fact_extract':'章节事实候选'})
TASKS['assistant']='软件助手'
TASK_ALIASES={'scene_design':'outline','cowrite':'polish','fact_extract':'review','roleplay':'brainstorm','roleplay_memory':'roleplay','behavior':'review',
 'world_design':'experiments','world_challenge':'experiments','world_explain':'experiments',
 'review_structure':'review','review_character':'review','review_language':'review','review_reader':'review'}
TASK_ALIASES['assistant']='brainstorm'
AGENT_ONLY={'workflow','files'}
PRESETS=[
 {'provider_type':'openai','display_name':'OpenAI API','protocol':'responses','base_url':'https://api.openai.com/v1'},
 {'provider_type':'siliconflow','display_name':'硅基流动','protocol':'chat','base_url':'https://api.siliconflow.cn/v1'},
 {'provider_type':'deepseek','display_name':'DeepSeek API','protocol':'chat','base_url':'https://api.deepseek.com/v1'},
 {'provider_type':'lmstudio','display_name':'LM Studio 本地服务','protocol':'chat','base_url':'http://127.0.0.1:1234/v1'},
 {'provider_type':'ollama','display_name':'Ollama 本地服务','protocol':'chat','base_url':'http://127.0.0.1:11434/v1'},
 {'provider_type':'custom','display_name':'自定义 OpenAI 兼容 API','protocol':'chat','base_url':'https://example.com/v1'}]

class Preferences(Strict):
    providers:list[Provider]=Field(default_factory=list,max_length=100)
    default:str='codex'
    routes:dict[str,str]=Field(default_factory=dict,max_length=64)
    projects:dict[str,dict[str,str]]=Field(default_factory=dict,max_length=2000)
    budgets:dict[str,float]=Field(default_factory=dict,max_length=3)
    budget_currency:str=Field(default='USD',pattern=r'^[A-Z]{3}$')
    budget_policy:Literal['notify','block']='notify'
    save_history:bool=False
    help_seen:bool=False
    controls:dict[str,dict]=Field(default_factory=dict,max_length=4000)
    control_presets:dict[str,dict]=Field(default_factory=dict,max_length=80)
    codex_models:list[dict]=Field(default_factory=list,max_length=200)

class Secret(Strict):
    key:str=Field(min_length=1,max_length=4096)
    session_only:bool=False

class Run(Strict):
    task:str=Field(default='brainstorm')
    text:str=Field(default='',max_length=16000)
    instruction:str=Field(min_length=1,max_length=2000)
    model:str|None=None
    parameters:Parameters|None=None

class Test(Strict):
    model:str=Field(min_length=1,max_length=160)
    confirm_cost:bool=False

class Confirm(Strict):
    token:str=Field(max_length=100)

class SettingsUpdate(Strict):
    default:str='codex'
    routes:dict[str,str]=Field(default_factory=dict,max_length=64)
    projects:dict[str,dict[str,str]]=Field(default_factory=dict,max_length=2000)
    budgets:dict[str,float]=Field(default_factory=dict,max_length=3)
    budget_currency:str=Field(default='USD',pattern=r'^[A-Z]{3}$')
    budget_policy:Literal['notify','block']='notify'
    save_history:bool=False
    help_seen:bool=True
