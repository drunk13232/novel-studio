"""Filesystem registry and explicitly reviewed foundation commits. No database."""
import copy
from functools import lru_cache
import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml
from app.errors import ConsoleError
from app.atomic import replace
from app.workspace.service import WorkspaceService, sha
from app.projects.models import Idea, Proposal

ID = re.compile(r'novel_[0-9a-f]{32}')
DRAFT_ID = re.compile(r'draft_[0-9a-f]{32}')

def now(): return datetime.now(timezone.utc).isoformat()

def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.pending-'+uuid.uuid4().hex)
    temporary.write_text(yaml.safe_dump(data,allow_unicode=True,sort_keys=False),encoding='utf-8')
    replace(temporary,path)

@lru_cache(maxsize=32)
def committed_chapters(content):
    value=WorkspaceService.parse_yaml(content)
    if not isinstance(value,dict):
        from app.errors import WorkspaceError
        raise WorkspaceError('state/chapter-ledger.yaml 必须是 YAML 映射',422)
    return frozenset(str(e.get('chapter')) for e in value.get('entries',[]))

class NovelWorkspace(WorkspaceService):
    def resolve(self, relative, *, allow_reviews=False):
        if relative == 'project.yaml':
            path = self.root / relative
            if path.is_symlink() or path.is_junction(): raise ConsoleError('Manifest 链接被拒绝',403)
            return path
        return super().resolve(relative,allow_reviews=allow_reviews)

    def list_files(self, *, include_reviews=False):
        rows = super().list_files(include_reviews=include_reviews)
        if (self.root/'project.yaml').is_file():
            c=self.content('project.yaml'); rows.append({k:c[k] for k in ['path','size','modified_at','editable']}|{'name':'project.yaml'})
        return rows

    def content(self, relative, *, allow_reviews=False):
        result=super().content(relative,allow_reviews=allow_reviews)
        if relative=='project.yaml' or self.protected_body(relative): result['editable']=False
        return result

    def protected_body(self, relative):
        if not relative.startswith('chapters/'): return False
        name=Path(relative).stem.lower()
        if name=='final' or name.endswith('-final'): return True
        match=re.match(r'chapters/chapter-(\d+)/',relative)
        if match and not name.startswith('manual-'):
            try:content=self.content('state/chapter-ledger.yaml')['content']
            except ConsoleError as error:
                if error.status==404:return False
                raise
            # Large ledgers are parsed without retaining their text in the cache.
            chapters=committed_chapters(content) if len(content)<=65536 else committed_chapters.__wrapped__(content)
            return match[1] in chapters
        return False

    def save(self,relative,content,etag):
        if relative=='project.yaml': raise ConsoleError('Manifest 通过项目设置修改；可在外部人工编辑 YAML',403)
        if self.protected_body(relative): raise ConsoleError('正式稿及已提交章节受保护；请先创建独立修订稿',409)
        if relative.startswith('characters/'):
            from app.domain.characters import normalize,validate_card
            card=normalize(self.parse_yaml(content));validate_card(card,Path(relative).stem)
        return super().save(relative,content,etag)

def validate_locks(proposal, idea):
    if proposal['user_locked'] != idea['locked_constraints'] or proposal['lock_verdict']!='PASS':
        raise ConsoleError('USER LOCKED 审查 FAIL：'+proposal.get('lock_reason','锁定事实不匹配'),409)
    fields={'protagonist':json.dumps(proposal['protagonist_concept'],ensure_ascii=False),
            'era':proposal['world_concept'],'ending':proposal['macro_structure']['ending_direction']}
    for key,rule in idea['locked_constraints'].items():
        if rule and rule not in fields[key]: raise ConsoleError('锁定原文必须保留在对应方案区域：'+key,409)
    # Fail closed on an explicit contradictory gender assignment, not arbitrary word occurrence.
    rule=idea['locked_constraints'].get('protagonist','')
    identity=proposal['protagonist_concept']['identity']
    if '女性' in rule and re.search(r'(?:主角|主人公|性别|身份)[^。\n]{0,8}(?:为|是|：|:)\s*(?:男性|男生|男人)',identity):
        raise ConsoleError('主角性别违反 USER LOCKED',409)

class DraftStore:
    def __init__(self,engine):
        self.engine=engine
        self.rows={}
        self.lock=threading.RLock()
        root=engine/'web/runtime/wizard-drafts';root.mkdir(parents=True,exist_ok=True)
        legacy=engine/'web/.runtime/drafts'
        if legacy.is_dir() and not legacy.is_symlink() and not legacy.is_junction():
            for old in legacy.iterdir():
                if DRAFT_ID.fullmatch(old.name) and not (root/old.name).exists() and not (root/(old.name+'.discarded.json')).exists():
                    if old.is_symlink() or old.is_junction():raise ConsoleError('旧草稿链接被拒绝',403)
                    shutil.copytree(old,root/old.name)

    def create(self,idea):
        id='draft_'+uuid.uuid4().hex
        row={'id':id,'version':1,'input':idea.model_dump(),'proposal':None,'accepted':False,'committed_project_id':None,'wizard_step':1,'updated_at':now(),'proposal_revision':0}
        self.rows[id]=row
        self.path(id).mkdir(parents=True)
        self.persist(row)
        return copy.deepcopy(row)

    def path(self,id):
        if not DRAFT_ID.fullmatch(id): raise ConsoleError('无效草稿 ID',403)
        root=self.engine/'web/runtime/wizard-drafts'
        p=root/id
        if any(q.is_symlink() or q.is_junction() for q in [self.engine/'web',root.parent,root,p]): raise ConsoleError('草稿链接被拒绝',403)
        return p

    def get(self,id):
        self.path(id)
        if id not in self.rows:
            p=self.path(id)/'draft.json'
            if not p.is_file(): raise ConsoleError('草稿不存在',404)
            self.rows[id]=json.loads(p.read_text(encoding='utf8'))
        return copy.deepcopy(self.rows[id])

    def persist(self,row):
        p=self.path(row['id'])/'draft.json'
        t=p.with_suffix('.tmp');t.write_text(json.dumps(row,ensure_ascii=False,indent=2),encoding='utf8');os.replace(t,p)

    def list(self):
        rows=[]
        for p in (self.engine/'web/runtime/wizard-drafts').iterdir():
            if not DRAFT_ID.fullmatch(p.name):continue
            row=self.get(p.name)
            if not row.get('committed_project_id'):rows.append(row)
        return sorted(rows,key=lambda x:x.get('updated_at',''),reverse=True)

    def discard(self,id,version):
        with self.lock:
            row=self.get(id)
            if row['version']!=version or row.get('committed_project_id'):raise ConsoleError('草稿已更新或已正式创建',409)
            from app.tasks.storage import atomic_json
            p=self.path(id)
            atomic_json(p.parent/(id+'.discarded.json'),{'id':id,'discarded_at':now()})
            # Only disposable Wizard data. Formal projects have no delete route.
            if not p.resolve().is_relative_to(p.parent.resolve()):raise ConsoleError('草稿路径越界',403)
            shutil.rmtree(p);self.rows.pop(id,None)
            old=self.engine/'web/.runtime/drafts'/id
            if old.exists():
                if old.is_symlink() or old.is_junction():raise ConsoleError('旧草稿链接被拒绝',403)
                shutil.rmtree(old)
            return {'discarded':True,'id':id}

    def update(self,id,version,**changes):
        with self.lock:
            row=self.get(id)
            if row['version']!=version or row['committed_project_id']: raise ConsoleError('草稿已更新或已创建项目，请刷新',409)
            if 'input' in changes and changes['input']!=row['input']:changes.update(proposal=None,accepted=False)
            if changes.get('proposal') is not None:
                p=Proposal.model_validate(changes['proposal']).model_dump();validate_locks(p,row['input']);changes['proposal']=p
            if changes.get('proposal') is not None and changes['proposal']!=row.get('proposal'):row['proposal_revision']=row.get('proposal_revision',0)+1
            row.update(changes);row['version']+=1;row['updated_at']=now();self.rows[id]=row;self.persist(row)
            return copy.deepcopy(row)

class ProjectRegistry:
    def __init__(self,engine):
        self.engine=engine.resolve();self.root=self.engine/'projects';self.root.mkdir(exist_ok=True)
        if self.root.is_symlink() or self.root.is_junction(): raise ConsoleError('projects 根目录不能为链接',403)
        self.lock=threading.RLock();self.workspaces={};self.scan()

    def scan(self):
        rows={};errors=[]
        for p in self.root.iterdir():
            if not p.is_dir() or not ID.fullmatch(p.name): continue
            try:
                if p.is_symlink() or p.is_junction() or (p/'project.yaml').is_symlink(): raise ValueError('链接目录')
                value=WorkspaceService.parse_yaml((p/'project.yaml').read_text(encoding='utf-8-sig'))
                if not isinstance(value,dict) or value.get('id')!=p.name or not value.get('title') or value.get('status',{}).get('phase') not in ['IDEA','FOUNDATION','OUTLINING','WRITING','REVISION','COMPLETED','ARCHIVED']: raise ValueError('Manifest 不匹配')
                for key in ['genre','target','current','creative_direction','workflow','codex']:
                    if not isinstance(value.get(key),dict):raise ValueError('Manifest 缺少对象：'+key)
                if not isinstance(value['genre'].get('primary'),str) or not isinstance(value['status'].get('updated_at'),str):raise ValueError('Manifest 类型无效')
                rows[p.name]=value
            except (OSError,ValueError,ConsoleError,AttributeError) as e: errors.append({'id':p.name,'error':str(e)})
        self.rows=rows;self.errors=errors
        return rows

    def get(self,id):
        if not ID.fullmatch(id): raise ConsoleError('无效项目 ID',403)
        self.scan()
        if id not in self.rows: raise ConsoleError('项目不存在或 Manifest 无效',404)
        p=self.root/id
        if p.is_symlink() or p.is_junction() or not p.resolve().is_relative_to(self.root): raise ConsoleError('项目路径越界',403)
        return copy.deepcopy(self.rows[id])

    def workspace(self,id):
        self.get(id)
        if id not in self.workspaces: self.workspaces[id]=NovelWorkspace(self.root/id)
        return self.workspaces[id]

    def status(self,id,summary=False):
        manifest=self.get(id);ws=self.workspace(id);files=ws.list_files();result=ws.status(files)
        character_files=[f for f in files if f['path'].startswith('characters/') and f['path'].endswith('.yaml')]
        chars=[] if summary else [ws.yaml_file(f['path']) for f in character_files]
        bodies=[]
        for c in ws.chapters(files):
            if c['final'] or c['draft']: bodies.append(WorkspaceService.content(ws,c['final'] or c['draft'])['content'] if summary else ws.content(c['final'] or c['draft'])['content'])
        from .writing_config import story_row,writing
        single=story_row(ws,manifest)
        if single and single['path']:bodies.insert(0,ws.content(single['path'])['content'])
        body='\n'.join(bodies);canon=ws.yaml_file('settings/canon-contract.yaml')
        proposal=ws.yaml_file('metadata/story-proposal.yaml') if (ws.root/'metadata/story-proposal.yaml').exists() else {}
        result.update(project_id=id,title=manifest['title'],genre=manifest['genre']['primary'],phase=manifest['status']['phase'],manifest=manifest,
            stats={'chapters':len(bodies),'characters':len(character_files),'text_characters':len(re.sub(r'\s','',body)),'chinese_words':len(re.findall(r'[\u3400-\u9fff]',body))+len(re.findall(r'[A-Za-z0-9]+',body)),
                   'canon':sum(len(canon.get(k,[])) for k in ['hard','strong','soft','preferences']),'open_questions':len(proposal.get('open_questions',[]))},
            characters=chars,character_states={c['id']:ws.yaml_file('state/characters/'+c['id']+'.yaml') if (ws.root/'state/characters'/ (c['id']+'.yaml')).is_file() else {} for c in chars},volume_concepts=proposal.get('volume_concepts',[]),open_questions=proposal.get('open_questions',[]),
            world_initialized=(ws.root/'bible/world.md').is_file() and ws.content('bible/world.md')['content']!=(self.engine/'engine/templates/project/bible/world.md').read_text(encoding='utf8'),outline_initialized=(ws.root/'outlines/master-outline.md').is_file() and ws.content('outlines/master-outline.md')['content']!=(self.engine/'engine/templates/project/outlines/master-outline.md').read_text(encoding='utf8'),
            updated_at=max([f['modified_at'] for f in files]+[manifest['status']['updated_at']]),
            next_actions=['完善主角' if character_files else '创建核心人物','完善世界观','生成第一卷详细卷纲'])
        result['writing']=writing(manifest)
        if result['writing']['form']!='novel':result['next_actions']=['直接写作','可选故事构思','按需审稿']
        return result

    def list(self,archived=False):
        self.scan()
        return [self.status(id,summary=True) for id,m in sorted(self.rows.items()) if archived or m['status']['phase']!='ARCHIVED']

    def patch(self,id,etag,title=None,phase=None):
        with self.lock:
            m=self.get(id);p=self.root/id/'project.yaml'
            if sha(p.read_bytes())!=etag: raise ConsoleError('项目设置已变化，请刷新',409)
            if title is not None:m['title']=title
            if phase:m['status']['phase']=phase
            m['status']['updated_at']=now();write_yaml(p,m)
            return self.get(id)

    def create(self,drafts,request):
        with self.lock,drafts.lock:
            row=drafts.get(request.draft_id)
            if row['committed_project_id']: return self.get(row['committed_project_id'])
            if row['version']!=request.version: raise ConsoleError('草稿版本已变化',409)
            if getattr(self,'covers',None) and any(j['status'] in {'QUEUED','RUNNING'} for j in self.covers.images.rows(row['id'],'jobs')):raise ConsoleError('封面背景仍在生成；请等待完成或取消后再创建',409)
            if row['proposal'] and not request.accept_proposal: raise ConsoleError('必须明确接受当前 AI Proposal',409)
            idea=Idea.model_validate(row['input']).model_dump();proposal=row['proposal']
            if proposal:validate_locks(proposal,idea)
            if row.get('creation'):
                from .creation import reviewed_proposal
                # World-first creation has no story/placeholder protagonist proposal.
                proposal=None if row['creation'].get('focus')=='world' else reviewed_proposal(row)
                if (idea.get('writing') or {}).get('form') in {'short','undecided','anthology'}:
                    from .creation import session,confirmed
                    v=confirmed(session(row))
                    if not any(v.get(k) for k in ['protagonist','protagonist_name','world','long_direction']):proposal=None
            id='novel_'+uuid.uuid4().hex;p=self.root/id
            selected=row.get('creation',{}).get('references',{})
            if selected and getattr(self,'references',None):
                from app.library.storage import write,safe
                bindings={'documents':[],'profiles':[]}
                for kind,reference_ids in selected.items():
                    if kind not in bindings:continue
                    for reference_id in reference_ids:
                        ref=self.references.get('public',kind,reference_id)
                        if ref.get('trashed') or (kind=='profiles' and ref.get('status')!='USER_CONFIRMED'):raise ConsoleError('创建前参考资料已变化，请重新选择',409)
                        bindings[kind].append({'id':reference_id,'source_scope':'public','role':'main' if kind=='profiles' and not bindings[kind] else 'auxiliary','confirmed_at':now(),'purpose':'作者在新建向导中明确选择'})
                        if kind=='profiles':bindings[kind][-1]['profile_snapshot']={k:ref[k] for k in ['id','title','directives','sources','status']}
            staging=self.engine/'web/.runtime/create'/id
            if staging.exists(): raise ConsoleError('创建暂存冲突',409)
            shutil.copytree(self.engine/'engine/templates/project',staging)
            self.initialize(staging,id,idea,proposal)
            if row.get('creation'):
                from .creation import initialize_profile
                initialize_profile(staging,row)
            if idea.get('writing') and idea['writing']['form']!='novel':
                from .creation import session,confirmed
                from .writing import StoryCard
                v=confirmed(session(row)) if row.get('creation') else {'premise':idea['premise']}
                mapping={'premise':'premise','characters':'protagonist','desire':'goal','conflict':'conflict','opening':'opening','ending':'ending','motifs':'visual_motifs'}
                from app.library.storage import write,safe
                write(safe(staging,'outlines/story-card.json'),StoryCard(fields={k:v[s] for k,s in mapping.items() if v.get(s)}).model_dump())
            if getattr(self,'covers',None):self.covers.migrate(row['id'],staging,id)
            if selected:write(safe(staging,'.research/library/bindings.json'),bindings)
            # Windows scanners can briefly retain handles to freshly copied
            # template directories. Retry the same atomic rename; never fall
            # back to exposing a partially initialized destination.
            for attempt in range(5):
                try:
                    os.replace(staging,p);break
                except PermissionError:
                    if os.name!='nt' or attempt==4:raise
                    time.sleep(0.05*(2**attempt))
            row['committed_project_id']=id;row['accepted']=bool(proposal);drafts.rows[row['id']]=row;drafts.persist(row)
            self.scan();return self.get(id)

    def initialize(self,p,id,idea,proposal):
        def load(relative):return yaml.safe_load((p/relative).read_text(encoding='utf8'))
        m=load('project.yaml');m.update(id=id,title=idea['title'],slug=re.sub(r'[^a-z0-9-]','',idea['title'].lower().replace(' ','-'))[:60] or id,
            genre={'primary':idea['genre'],'secondary':idea['secondary']},language=idea['language'],
            target={k:idea[k] or None for k in ['total_words','estimated_chapters','estimated_volumes']},
            creative_direction={'premise':idea['premise'],'themes':proposal['themes'] if proposal else [],'tone':[idea['tone']] if idea['tone'] else [],'audience':None,'pacing':idea['pacing'] or None})
        m['status'].update(created_at=now(),updated_at=now());write_yaml(p/'project.yaml',m)
        if idea.get('writing'):
            from .writing_config import writing
            m['writing']=writing({'writing':idea['writing']})
            if m['writing']['form'] in {'short','undecided'}:
                m['writing']['body_id']='story_'+uuid.uuid4().hex
                body=p/'chapters/story/draft.txt';body.parent.mkdir(parents=True,exist_ok=True);body.write_text('',encoding='utf8')
            if m['writing']['form']!='novel':m['workflow'].update(auto_review=False,auto_memory_extract=False,auto_state_commit=False)
            write_yaml(p/'project.yaml',m)
        write_yaml(p/'metadata/user-input.yaml',idea)
        current=load('state/current-story-state.yaml');current['project'].update(title=m['title'],genre=idea['genre']);write_yaml(p/'state/current-story-state.yaml',current)
        canon=load('settings/canon-contract.yaml');sources={}
        for key,value in idea['locked_constraints'].items():
            if value:
                ruleid='user_'+key;canon['hard'].append({'id':ruleid,'statement':value,'check':'manual','writer_view':[]});sources[ruleid]={'source':'user','priority':'HARD','scope':key}
        if proposal:
            for key in ['premise','core_conflict','power_or_rule_system']:
                rid='proposal_'+key;canon['strong'].append({'id':rid,'statement':proposal[key],'check':'manual','writer_view':[]});sources[rid]={'source':'accepted_proposal','priority':'STRONG'}
        write_yaml(p/'settings/canon-contract.yaml',canon);write_yaml(p/'metadata/canon-sources.yaml',sources)
        style=load('settings/style-profile.yaml');style['pacing']=idea['pacing'] or None
        style['description_preferences']=[idea['style']] if idea['style'] else []
        for key,label in [('tone','整体基调'),('narrative','叙事倾向'),('romance','感情线比重')]:
            if idea[key]:style['description_preferences'].append(label+'：'+idea[key])
        write_yaml(p/'settings/style-profile.yaml',style)
        write_yaml(p/'metadata/style-input.yaml',{k:idea[k] for k in ['language','tone','pacing','narrative','romance','style']})
        if idea['genre']=='同人':write_yaml(p/'settings/source-canon.yaml',{'SOURCE CANON':idea['fanfiction'],'PROJECT CANON':'settings/canon-contract.yaml','AU CHANGES':idea['fanfiction'].get('major_changes','TBD')})
        if not proposal:return
        write_yaml(p/'metadata/story-proposal.yaml',proposal)
        (p/'bible/world.md').write_text('# 世界观\n\n'+''.join('## '+h+'\n'+v+'\n\n' for h,v in [('世界一句话',proposal['world_concept']),('时代与社会',idea['locked_constraints'].get('era','UNKNOWN')),('核心规则',proposal['power_or_rule_system']),('核心矛盾',proposal['core_conflict']),('已知区域','UNKNOWN'),('核心势力','\n'.join(proposal['major_factions']) or 'TBD'),('待探索区域','\n'.join(proposal['open_questions']) or 'TBD')]),encoding='utf8')
        char_template=yaml.safe_load((self.engine/'engine/templates/character.yaml').read_text(encoding='utf8'))
        for i,c in enumerate([proposal['protagonist_concept'],*proposal['major_character_roles']]):
            card=copy.deepcopy(char_template);cid='character_'+str(i+1).zfill(3)
            card.update({k:c[k] for k in ['name','identity','personality','core_desire','fear','story_function']});card.update(id=cid,role='PROTAGONIST' if i==0 else 'STRUCTURAL')
            card['arc']['direction']=c['arc'];card['canon']['locked']=[idea['locked_constraints']['protagonist']] if i==0 and idea['locked_constraints'].get('protagonist') else []
            write_yaml(p/f'characters/{cid}.yaml',card)
            state=yaml.safe_load((self.engine/'templates/state/character.yaml').read_text(encoding='utf8'));state.update(id=cid,name=c['name'])
            state['goals']['long_term']=[c['core_desire']];write_yaml(p/f'state/characters/{cid}.yaml',state)
        outline=[('故事承诺','\n'.join(proposal['reader_promises'])),('核心冲突',proposal['core_conflict']),('主角长期弧',proposal['protagonist_concept']['arc']),('主要关系弧','TBD'),('主线阶段',yaml.safe_dump(proposal['macro_structure'],allow_unicode=True,sort_keys=False)),('卷级规划',yaml.safe_dump(proposal['volume_concepts'],allow_unicode=True,sort_keys=False)),('重要转折',proposal['macro_structure']['escalation']),('中段变化',proposal['macro_structure']['midpoint']),('终局方向',proposal['macro_structure']['ending_direction']),('开放问题','\n'.join(proposal['open_questions']))]
        (p/'outlines/master-outline.md').write_text('# 总纲\n\n'+''.join('## '+h+'\n'+(v or 'TBD')+'\n\n' for h,v in outline),encoding='utf8')
