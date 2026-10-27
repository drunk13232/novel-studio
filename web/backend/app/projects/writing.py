"""Form-specific UI adapters over existing files, proposals, tasks and backups."""
import copy,json,uuid,hashlib,os
from pathlib import Path
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel,ConfigDict,Field
from app.errors import ConsoleError
from app.library.storage import safe,read,write,checkpoint,digest
from app.projects.service import write_yaml,now
from app.projects.writing_config import WritingConfig,writing,defaults,LABELS
from app.domain.planning import Scene,ChapterCard,PlanAction
from app.models.requests import TaskRequest,TaskOptions
from app.codex.adapter import CodexAdapter

CARD_FIELDS={'premise':'一句话故事','characters':'核心人物','desire':'人物欲望','conflict':'主要矛盾','opening':'故事起点',
 'change':'重要变化','ending':'结尾方向','motifs':'希望保留的意象','avoid':'不想出现的内容'}
STRUCTURE_FIELDS={'core':'故事核心','goal':'主角目标','conflict':'主要矛盾','start':'起始状态','turns':'重要转折',
 'middle':'中段变化','climax':'高潮','ending':'结局','arc':'人物弧'}
REFERENCES={'free':'自由写作','classic':'经典故事结构','change':'人物变化型','reveal':'悬疑揭示型',
 'slice':'日常切片型','open':'开放结尾型','nonlinear':'非线性叙事'}
GENRES=[('realism','现实主义人物故事','现实处境、人的选择和关系中的代价'),('mystery','悬疑短篇','线索、记忆、认知和揭示权限'),
 ('emotion','情感短篇','关系中的期待、行动与沉默'),('science','科幻短篇','一个假设怎样影响具体的人'),('fantasy','奇幻短篇','规则与人物选择的关系'),
 ('history','历史短篇','时代处境、职业和日常生活'),('slice','日常生活短篇','细节、情绪和观察'),('nonlinear','实验性或非线性短篇','视角、时间组织和读者理解'),('free','自由创作','作品自己的意图与语言')]
NOVELLAS=[('growth','人物成长','目标、选择与改变'),('social','社会现实','环境、关系与真实处境'),('investigation','悬疑调查','线索、认知与信息揭示'),
 ('history','历史故事','时代与人物行动'),('science','科幻故事','假设与现实后果'),('fantasy','奇幻冒险','规则、冒险代价与选择'),
 ('emotion','情感关系','关系的阶段变化'),('ensemble','群像叙事','多人物目标与因果联系'),('free','自由创作','作品自己的结构与节奏')]

def templates():
    return [{'id':form+'-'+key,'form':form,'title':title,'questions':[f'{focus}中，作者最想留下什么？','谁作出关键选择，或观察到关键变化？','哪些信息可以省略，让行动或细节承担？','结尾希望留下什么感受？'],
      'focus':[focus],'structure_hints':['可留白、调整顺序或不用传统冲突；没有必填节拍。'],
      'ai_directions':['完善创意','寻找冲突或变化','讨论不同结尾'],'review_focus':[focus,'叙事集中度' if form=='short' else '中段与章节因果','语言冗余']} for form,rows in [('short',GENRES),('novella',NOVELLAS)] for key,title,focus in rows]

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class StoryCard(Strict):
    fields:dict[str,str]=Field(default_factory=dict,max_length=9)
    structure:list[dict[str,str]]=Field(default_factory=list,max_length=30)
    scenes:list[Scene]=Field(default_factory=list,max_length=100)
    template:dict=Field(default_factory=dict)
    structure_reference:str=Field(default='free',max_length=100)
class CardSave(Strict):
    etag:str
    value:StoryCard
class SettingsSave(Strict):
    etag:str
    writing:WritingConfig
    confirm:Literal[True]
class Collection(Strict):
    entries:list[str]=Field(default_factory=list,max_length=500)
    introduction:str=Field(default='',max_length=20000)
    afterword:str=Field(default='',max_length=20000)
    description:str=Field(default='',max_length=4000)
    display_titles:dict[str,str]=Field(default_factory=dict,max_length=500)
class CollectionSave(Strict):
    etag:str
    value:Collection
class TemplateSave(Strict):
    etag:str
    title:str=Field(min_length=1,max_length=120)
    form:Literal['short','novella']
    content:dict
def validate_template(value):
    allowed={'id','title','form','questions','focus','structure_hints','ai_directions','review_focus'}
    if not isinstance(value,dict) or set(value)-allowed or value.get('form') not in {'short','novella'}:raise ConsoleError('模板配置只允许构思问题与关注点',422)
    if not isinstance(value.get('id'),str) or not isinstance(value.get('title'),str):raise ConsoleError('模板标识与名称无效',422)
    for key in allowed-{'id','title','form'}:
        rows=value.get(key,[])
        if not isinstance(rows,list) or len(rows)>100 or any(not isinstance(v,str) or len(v)>4000 for v in rows):raise ConsoleError('模板问题格式无效',422)
    return value
class Analysis(Strict):
    action:Literal['idea','directions','conflict','choice','ending','fit','focus','compress','review','motivation','pov','causality','redundancy','reader','middle','arc','chapters','merge','structure','sepia']='review'
    instruction:str=Field(default='',max_length=6000)
    paths:list[str]=Field(default_factory=list,max_length=200)
    manuscript_budget:int=Field(default=30000,ge=1000,le=50000)
    depth:Literal['quick','standard','deep']='standard'
    excerpt:dict|None=None
class ChapterSave(Strict):
    title:str=Field(default='',max_length=180)
    card:dict=Field(default_factory=dict)
    etags:dict[str,str]=Field(default_factory=dict)
    confirm:Literal[True]
class Finalize(Strict):
    path:str
    etag:str
    final_etag:str|None=None
    confirm:Literal[True]

class Writing:
    def __init__(self,registry,planning,characters,proposals,foundation,tools,books,data_center,manager):
        self.registry=registry;self.planning=planning;self.characters=characters;self.proposals=proposals
        self.foundation=foundation;self.tools=tools;self.books=books;self.data=data_center;self.manager=manager
    def writable(self,p):return self.characters.writable(p)
    def card(self,p):
        ws=self.registry.workspace(p);path=ws.resolve('outlines/story-card.json')
        m=self.registry.get(p);value=read(path,{'fields':{'premise':m['creative_direction'].get('premise') or ''}})
        return {'value':StoryCard.model_validate(value).model_dump(),'etag':digest(path.read_bytes()) if path.exists() else digest(b'')}
    def validate_card(self,value):
        value=StoryCard.model_validate(value).model_dump()
        if set(value['fields'])-set(CARD_FIELDS):raise ConsoleError('未知构思卡字段',422)
        if any(len(v)>12000 for v in value['fields'].values()):raise ConsoleError('构思字段超过上限',422)
        if value['structure_reference'] not in REFERENCES:raise ConsoleError('未知结构参考',422)
        if any(set(r)-{'id','label','text'} or len(r.get('text',''))>12000 for r in value['structure']):raise ConsoleError('结构条目格式无效',422)
        ids=[r['id'] for r in value['scenes']]
        if len(ids)!=len(set(ids)):raise ConsoleError('场景 ID 重复',422)
        return value
    def save_card(self,p,b):
        ws=self.writable(p)
        with self.registry.lock,ws._save_lock:
            if self.card(p)['etag']!=b.etag:raise ConsoleError('构思卡已变化，请刷新',409)
            value=self.validate_card(b.value);path=ws.resolve('outlines/story-card.json')
            checkpoint(ws.root,'outlines/story-card.json','PRE_STORY_CARD');write(path,value)
            return self.card(p)
    def finalize(self,p,b):
        from app.library.storage import write_bytes
        from .writing_config import story_row
        ws=self.writable(p)
        with self.registry.lock,ws._save_lock:
            row=story_row(ws,self.registry.get(p))
            if not row or b.path not in {v['path'] for v in row['versions']} or b.path.endswith('/final.txt'):raise ConsoleError('请选择已有单篇草稿定稿',422)
            source=ws.content(b.path);target=ws.resolve('chapters/story/final.txt')
            if source['etag']!=b.etag or (digest(target.read_bytes()) if target.exists() else None)!=b.final_etag:raise ConsoleError('正文版本已变化，请刷新后确认',409)
            if not source['content'].strip():raise ConsoleError('空白正文不能定稿',422)
            checkpoint(ws.root,'chapters/story/final.txt','PRE_AUTHOR_FINAL','作者明确确认单篇定稿前保留版本')
            write_bytes(target,ws.resolve(b.path).read_bytes())
            write(ws.resolve('metadata/story-final.json'),{'source':b.path,'source_etag':b.etag,'final_etag':digest(target.read_bytes()),'at':now(),'method':'AUTHOR_CONFIRMED','state_commit':False})
            return {'saved':True,'path':'chapters/story/final.txt','state_commit':False}
    def collection(self,p):
        ws=self.registry.workspace(p);path=ws.resolve('metadata/anthology.json')
        value=Collection.model_validate(read(path,{})).model_dump();rows=[]
        for id in value['entries']:
            try:
                m=self.registry.get(id)
                rows.append({'id':id,'title':m['title'],'available':True,'form':writing(m)['form']})
            except ConsoleError:rows.append({'id':id,'title':'不可用篇目','available':False})
        return {'value':value,'rows':rows,'etag':digest(path.read_bytes()) if path.exists() else digest(b'')}
    def save_collection(self,p,b):
        ws=self.writable(p)
        if writing(self.registry.get(p))['form']!='anthology':raise ConsoleError('当前作品不是合集',422)
        with self.registry.lock,ws._save_lock:
            if self.collection(p)['etag']!=b.etag:raise ConsoleError('合集已变化，请刷新',409)
            entries=b.value.entries
            if len(entries)!=len(set(entries)) or p in entries:raise ConsoleError('篇目重复或自引用',422)
            for id in entries:
                if writing(self.registry.get(id))['form']!='short':raise ConsoleError('合集只能引用已有短篇',422)
            if set(b.value.display_titles)-set(entries) or any(len(v)>180 for v in b.value.display_titles.values()):raise ConsoleError('展示标题必须属于合集篇目且不超过 180 字符',422)
            checkpoint(ws.root,'metadata/anthology.json','PRE_COLLECTION')
            write(ws.resolve('metadata/anthology.json'),b.value.model_dump());return self.collection(p)
    def settings(self,p,b):
        ws=self.writable(p)
        with self.registry.lock,ws._save_lock:
            if ws.content('project.yaml')['etag']!=b.etag:raise ConsoleError('作品设置已变化，请刷新',409)
            m=self.registry.get(p);old=writing(m);new=b.writing.model_dump()
            new['body_id']=old['body_id'] # Stable document identity never changes with display mode.
            snapshot=None;differences=[]
            if old['form']!=new['form']:
                snapshot=self.data.backup(p,images=True,note='PRE_FORM_CHANGE')
                if self.planning.rows(p,'volume'):differences.append('保留全部卷纲；新模式可隐藏卷视图，未移动正文。')
                if ws.chapters():differences.append('保留全部章节与稳定 ID；不会自动合并成单篇。')
                if old['body_id']:differences.append('保留单篇正文与稳定 ID；扩展章节需要作者主动添加。')
                if new['form']=='anthology':differences.append('原有正文保留，合集导出仅使用作者选定的篇目引用。')
                if new['form']=='novel' and any(not c['volume'] for c in self.planning.rows(p,'chapter')):differences.append('原章节尚未关联卷；完整长篇规划需要作者手动关联，正文仍可打开。')
                if new['form'] in {'short','undecided'} and not new['body_id'] and not ws.chapters():
                    new['body_id']='story_'+uuid.uuid4().hex
                    ws.resolve('chapters/story/draft.txt').parent.mkdir(parents=True,exist_ok=True)
                    ws.resolve('chapters/story/draft.txt').write_text('',encoding='utf8')
            checkpoint(ws.root,'project.yaml','PRE_WRITING_SETTINGS')
            m['writing']=new;m['status']['updated_at']=now();write_yaml(ws.resolve('project.yaml'),m)
            if snapshot:write(ws.resolve('metadata/mode-changes/'+uuid.uuid4().hex+'.json'),{'from':old,'to':new,'backup_id':snapshot['id'],'differences':differences,'at':now()})
            return {'writing':new,'snapshot':snapshot,'differences':differences,'etag':ws.content('project.yaml')['etag']}
    def view(self,p):
        m=self.registry.get(p);ws=self.registry.workspace(p)
        custom=self.template_catalog();catalog=self.books.catalog(p)
        overview={'description':m.get('creative_direction',{}).get('premise',''),'written':sum(bool(c['final'] or c['draft']) for c in catalog['chapters']),'final':sum(bool(c['final']) for c in catalog['chapters']),'han':sum(c['han'] for c in catalog['chapters'])}
        return {'title':m['title'],'writing':writing(m),'label':LABELS[writing(m)['form']],'overview':overview,'manifest_etag':ws.content('project.yaml')['etag'],
            'card':self.card(p),'field_labels':CARD_FIELDS,'structure_fields':STRUCTURE_FIELDS,'references':REFERENCES,
            'templates':templates()+custom['items'],'template_etag':custom['etag'],'collection':self.collection(p),
            'chapters':self.planning.board(p),'characters':[{'id':c['canonical']['id'],'name':c['canonical']['name']} for c in self.characters.list(p)],
            'manuscripts':[{'id':c['id'],'title':c['title'],'path':c['final'] or c['draft']} for c in self.books.catalog(p)['chapters'] if c['final'] or c['draft']],
            'mode_history':[read(f) for f in ws.resolve('metadata/mode-changes/index.json').parent.glob('*.json')]}
    def template_catalog(self):
        path=self.tools.config/'writing-templates.json';items=read(path,[])
        return {'items':items,'etag':digest(path.read_bytes()) if path.exists() else digest(b'')}
    def save_template(self,b):
        with self.registry.lock:
            rows=self.template_catalog()
            if rows['etag']!=b.etag:raise ConsoleError('模板库已变化，请刷新',409)
            if len(json.dumps(b.content,ensure_ascii=False))>20000:raise ConsoleError('模板过大',422)
            item={**b.content,'id':'template_'+uuid.uuid4().hex,'title':b.title,'form':b.form}
            validate_template(item)
            if len(rows['items'])>=500:raise ConsoleError('个人模板已达到本版上限',422)
            write(self.tools.config/'writing-templates.json',[*rows['items'],item]);return self.template_catalog()
    def chapter(self,p,b):
        self.writable(p);cfg=writing(self.registry.get(p))
        if cfg['form'] not in {'short','novella','undecided'}:raise ConsoleError('请使用原长篇规划入口',422)
        existing=self.planning.rows(p,'chapter');value=copy.deepcopy(b.card)
        if not value.get('id'):
            number=max([c['number'] for c in existing]+[c['number'] for c in self.registry.workspace(p).chapters()]+[0])+1
            value=ChapterCard(id='chapter_'+uuid.uuid4().hex,number=number,
                order=number,title=b.title,volume='').model_dump()|value
        card=ChapterCard.model_validate(value).model_dump()
        result=self.planning.action(p,PlanAction(action='save' if any(c['id']==card['id'] for c in existing) else 'add',volume_id=card['volume'],chapter_id=card['id'],card=card,etags=b.etags,confirm=True)) if any(c['id']==card['id'] for c in existing) else None
        if result:return result
        from app.domain.planning import dump
        path=self.planning.path(card['id'],'chapter');ops=[{'path':path,'action':'write','content':dump(card)}]
        return self.proposals.stage(p,'chapter_light',ops,'作者填写的精简章节规划',[],self.planning.bases(p),lambda ops:self.planning.validate(p,ops))
    def skill_sources(self,action):
        home=Path(os.environ.get('USERPROFILE',Path.home()))/'.codex';paths=[]
        if action=='reader':
            paths=[home/'skills/beta-reader-panel/SKILL.md',home/'plugins/cache/novel-writing-stack/story-skills/0.22.1/skills/reader-panel/SKILL.md']
            paths=[p for p in paths if p.is_file()][:1]
        elif action=='sepia':paths=[p for p in (home/'plugins/cache/sepia').glob('*/*/skills/sepia-review/SKILL.md') if p.is_file()]
        elif action in {'review','middle','arc','merge'}:paths=[home/'skills/developmental-editor/SKILL.md']
        else:
            name='sw-premise-theme' if action in {'idea','directions','fit','compress'} else 'sw-character-conflict' if action in {'choice','motivation'} else 'sw-story-structure' if action=='structure' else 'sw-scene-craft'
            paths=[p for p in (self.registry.engine/'docs/vendor/screenwriting-skills').rglob('SKILL.md') if p.parent.name==name][:1]
            if not paths:paths=[p for p in (home/'plugins/cache/screenwriting-skills').glob(f'*/ */skills/{name}/SKILL.md'.replace(' ','')) if p.is_file()][:1]
            if action in {'pov','redundancy','causality'}:paths.append(home/'skills/novel-writing/SKILL.md')
        paths=[p for p in paths if p.is_file()]
        if not paths:raise ConsoleError('对应现成 Skill 未安装；可继续手动创作',409)
        return '\n'.join(p.read_text(encoding='utf-8-sig') for p in paths),[{'path':str(p),'sha256':digest(p.read_bytes())} for p in paths]
    def analyze(self,p,b):
        ws=self.registry.workspace(p);m=self.registry.get(p);cfg=writing(m);skill,proof=self.skill_sources(b.action)
        if cfg['form']=='anthology':raise ConsoleError('请打开原短篇进行分析；合集只管理篇目引用',422)
        reader=b.action=='reader';planning=b.action in {'idea','directions','conflict','choice','ending','fit','focus','compress','structure'}
        audience='READER' if reader else 'AUTHOR' if planning else 'CHECKER'
        catalog=self.books.catalog(p);rows=catalog['chapters']
        paths=b.paths or [c['final'] or c['draft'] for c in rows if c['final'] or c['draft']]
        # The native document adapter validates every path, including manual
        # revisions. It cannot resolve Author files or another project's body.
        manuscript=[]
        for path in paths:
            doc=self.tools.doc(p,path)
            manuscript.append({'path':path,'text':doc['content'],'revision':doc['etag']})
        coverage='全文' if not b.paths else '作者选定范围';size=sum(len(r['text']) for r in manuscript)
        if not planning and not any(r['text'].strip() for r in manuscript):raise ConsoleError('正文仍为空；请手动写作后再发起审稿或读者反馈',422)
        if b.excerpt:
            from app.studio_tools import utf16_slice
            e=b.excerpt
            if set(e)!={'path','revision','start','end'} or e['path'] not in paths:raise ConsoleError('选段范围格式无效',422)
            source=next(r for r in manuscript if r['path']==e['path'])
            if source['revision']!=e['revision']:raise ConsoleError('正文已变化，请重新选择范围',409)
            if type(e['start']) is not int or type(e['end']) is not int or not 0<=e['start']<e['end']<=len(source['text'].encode('utf-16-le'))//2:raise ConsoleError('选段范围无效',422)
            manuscript=[{**source,'text':utf16_slice(source['text'],e['start'],e['end'])}]
            size=len(manuscript[0]['text']);coverage='作者选定正文片段，未覆盖全文'
        package={'form':cfg['form'],'title':m['title'],'genre':m['genre']['primary'],'manuscript':manuscript}
        if size>b.manuscript_budget:
            if reader:raise ConsoleError('全文超出本次预算，请选择较小阅读范围；不截断后冒充整体反馈',413)
            # Reuse the established Builder for bounded chapter knowledge, never raw future outline in a Writer prompt.
            from app.tasks.router import core_workflow
            wf=core_workflow(self.registry.engine);packs=[]
            for path in paths:
                _,n,_=self.tools.chapter(p,path);row=ws.chapter(n)
                if row['plan']:packs.append(wf.context(ws.root,wf.y.read(ws.resolve(row['plan']))))
            if not packs:raise ConsoleError('全文超过预算且没有可用 Context Builder 包，请选择正文范围再分析',413)
            package['manuscript']=[];package['context_builder']=packs[:3]
            if len(json.dumps(package,ensure_ascii=False))>b.manuscript_budget:raise ConsoleError('所选上下文仍超过预算，请缩小范围',413)
            coverage='Context Builder 选择性上下文，未覆盖全文'
        if not reader:
            package['story_card']=self.card(p)['value']
            package['canon']=ws.yaml_file('settings/canon-contract.yaml')
            if audience=='CHECKER':
                package['knowledge']=ws.yaml_file('state/knowledge-state.yaml')
                package['characters']=[{'canon':r['canonical'],'current':r['runtime']} for r in self.characters.list(p)]
                package['state']={name:ws.yaml_file('state/'+name+'.yaml') for name in ['current-story-state','timeline','relationships','plot-threads','foreshadowing']}
            refs=getattr(self.registry,'references',None)
            if refs:
                package['style']=[v.get('directives',{}) for row in refs.bindings(p)['profiles'] if (v:=refs.selected_profile(p,row['id'])) and v.get('status')=='USER_CONFIRMED'][:3]
        max_prompt=120000
        if len(json.dumps(package,ensure_ascii=False))+len(skill)>max_prompt:raise ConsoleError('完整请求超过安全预算，请缩小正文范围',413)
        policy=('你仅使用提供的数据和真实 Skill 做构思/诊断，禁止读取其他文件、网络、创建Agent、写正文或修改任何文件。'
            '不把大纲、怀疑、计划或作者秘密当作已发生事实。允许开放结尾、无反转、无成长或无传统冲突，先判断作者意图。'
            '按作品篇幅调整关注点，不能擅自改变 form。输出JSON，message给具体证据和建议；suggestions仅是构思候选字段，不是小说正文。'
            'MUST FIX仅确凿Canon/POV/知识/连续性错误；SHOULD FIX为高置信度因果/动机；一般建议SUGGESTION，风格STYLE ONLY不强制。'
            '缺少来源或超出本次覆盖的内容不得断言通过/违反 Canon；指出资料边界。不猜测未知人物、事实或中文对白归属。'
            '读者模拟只代表AI反馈，不声称独立真人认可。Checker报告是作者资料，禁止原样转给Writer；修订应经已有安全选段流程。')
        capsule=safe(self.tools.config,'writing-runs/'+p+'/'+uuid.uuid4().hex);capsule.mkdir(parents=True)
        (capsule/'AGENTS.md').write_text(policy,encoding='utf8')
        prompt=policy+'\n真实Skill:\n'+skill+'\n受控资料:'+json.dumps(package,ensure_ascii=False)+'\n操作:'+b.action+'\n覆盖:'+coverage+'\n深度:'+b.depth+'\n作者要求:'+b.instruction
        output={'type':'object','properties':{'message':{'type':'string'},'suggestions':{'type':'object','properties':{k:{'type':'string'} for k in CARD_FIELDS},'required':list(CARD_FIELDS),'additionalProperties':False}},'required':['message','suggestions'],'additionalProperties':False}
        def complete(text):
            result=json.loads(text)
            if not isinstance(result.get('message'),str):raise ConsoleError('审稿返回格式无效',422)
            if not planning:result['suggestions']={}
            report={**result,'audience':audience,'coverage':coverage,'skill_sources':proof,'report_only':True,'summary':result['message'],'independent_reader':False,'verdict':'SUGGESTIONS','revisions':{r['path']:r['revision'] for r in manuscript}}
            write(ws.resolve('reviews/writing/'+uuid.uuid4().hex+'.json',allow_reviews=True),report)
            return report
        return self.manager(p).prepared(TaskRequest(type='writing_analysis',options=TaskOptions(read_only=True,resume=False)),prompt,True,'writing-'+uuid.uuid4().hex,output,complete,provider='Codex',skill=proof[0]['path'],adapter=CodexAdapter(capsule,self.registry.engine,role='CHECKER' if reader else audience,capsule=True))

def writing_routes(service):
    r=APIRouter(prefix='/api')
    @r.get('/projects/{p}/writing')
    def view(p:str):return service.view(p)
    @r.put('/projects/{p}/writing/settings')
    def settings(p:str,b:SettingsSave):return service.settings(p,b)
    @r.put('/projects/{p}/writing/card')
    def card(p:str,b:CardSave):return service.save_card(p,b)
    @r.get('/projects/{p}/writing/card')
    def read_card(p:str):return {**service.card(p),'labels':CARD_FIELDS}
    @r.put('/projects/{p}/writing/collection')
    def collection(p:str,b:CollectionSave):return service.save_collection(p,b)
    @r.post('/projects/{p}/writing/chapter')
    def chapter(p:str,b:ChapterSave):return service.chapter(p,b)
    @r.post('/projects/{p}/writing/finalize')
    def finalize(p:str,b:Finalize):return service.finalize(p,b)
    @r.post('/projects/{p}/writing/analyze')
    async def analyze(p:str,b:Analysis):return service.analyze(p,b).public()
    @r.get('/writing/templates')
    def template_catalog():
        custom=service.template_catalog();return {**custom,'items':templates()+custom['items']}
    @r.post('/writing/templates')
    def save_template(b:TemplateSave):return service.save_template(b)
    return r
