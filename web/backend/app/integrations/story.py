"""Translate authoritative data into disposable native Story Skills input.

The projection is an audit cache, never an alternate Canon or State store.
Only allowlisted read commands run against it. No story doctor --fix.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
import yaml
from app.errors import ConsoleError
from app.integrations.stack import installations, STORY_COMMANDS
from app.integrations.story_projection import cast_projection

def native_id(value):
    value=str(value)
    return re.sub('[^a-z0-9-]', '-', value.lower()).strip('-')[:60]+'-'+hashlib.sha256(value.encode()).hexdigest()[:8]

def pov_id(value):
    return value.get('character') if isinstance(value,dict) else value if isinstance(value,str) else None

class StoryValidator:
    def __init__(self, engine, registry, characters, planning, projection_base=None):
        self.engine=engine;self.registry=registry;self.characters=characters;self.planning=planning
        self.cli=installations(engine)['story']/'skills/story-maintenance/scripts/story.js'
        self.node=shutil.which('node')
        self.projection_base=projection_base or engine/'web/.runtime/story-audits'

    def command(self, args, cwd, emit, cancelled):
        if not self.node or not self.cli.is_file(): raise ConsoleError('Story Skills / Node 入口不可用',409)
        emit('tool_call','Story Skills: '+' '.join(args),{'provider':'Story Skills','skill':'story-maintenance'})
        with subprocess.Popen([self.node,str(self.cli),*args,'--json'],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,encoding='utf8',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0) as process:
            started=time.monotonic()
            while True:
                if cancelled() or time.monotonic()-started>60:
                    process.kill();process.communicate()
                    raise ConsoleError('Story Skills 已中断或超时',409)
                try: output,error=process.communicate(timeout=.25);break
                except subprocess.TimeoutExpired: continue
            try: result=json.loads(output)
            except ValueError: raise ConsoleError('Story Skills 未返回有效 JSON：'+error[:500],409)
            if not isinstance(result,dict) or result.get('apiVersion') is None:
                raise ConsoleError('Story Skills 返回接口格式不兼容',409)
            if result.get('writes') and args[0] in STORY_COMMANDS:
                raise ConsoleError('只读审计命令意外写入了缓存，结果已拒绝',409)
            return result

    @staticmethod
    def markdown(path, meta, body=''):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---\n\n'+body,encoding='utf8')

    def project(self, project, request, emit, cancelled):
        ws=self.registry.workspace(project)
        root=self.projection_base/project/uuid.uuid4().hex
        for part in [root,*root.parents]:
            if part==self.engine: break
            if part.is_symlink() or part.is_junction(): raise ConsoleError('审计缓存链接被拒绝',403)
        root.parent.mkdir(parents=True,exist_ok=True)
        title=self.registry.get(project)['title']
        self.command(['init',title,'--dir',str(root)],self.engine,emit,cancelled)
        self.markdown(root/'story.md',{'title':title,'schema-version':2,'status':'in-progress','pov':'third-person-limited','tense':'past','language':'zh'},'# Audit projection\n\nDerived from current project only; read-only second opinion.')
        cards=self.characters.list(project)
        current=ws.yaml_file('state/current-story-state.yaml')
        facts=ws.yaml_file('state/knowledge-state.yaml').get('facts',{})
        locations=ws.yaml_file('state/locations.yaml').get('locations',{})
        state_chars=[];knowledge=[]
        for row in cards:
            card=row['canonical']; runtime=row.get('runtime') or row.get('state') or {}
            # CharacterService returns runtime_state; read the canonical State path directly.
            path='state/characters/'+card['id']+'.yaml'
            if (ws.root/path).is_file(): runtime=ws.yaml_file(path)
            status=runtime.get('status') or {}
            meta={'id':native_id(card['id']),'name':card['name'] or card['id'],
                  'role':{'PROTAGONIST':'protagonist','ANTAGONIST':'antagonist','SUPPORTING':'supporting'}.get(card.get('role'),'minor'),
                  'status':'deceased' if status.get('alive') is False else 'alive' if status.get('alive') is True else 'unknown',
                  'aliases':card.get('aliases',[])}
            self.markdown(root/'characters'/f'{meta["id"]}.md',meta,'# '+meta['name']+'\n\n## Voice & Speech Patterns\n'+json.dumps(card.get('speech',{}),ensure_ascii=False))
            state_chars.append({'character':meta['id'],'location':native_id(status['location']) if status.get('location') else '',
                                'physical':str(status.get('physical_condition') or ''),'emotional':str(status.get('mental_condition') or '')})
        for id,location in locations.items():
            self.markdown(root/'worldbuilding/locations'/f'{native_id(id)}.md',{'id':native_id(id),'name':location.get('name') or id,'type':'location'},'')
        chapter_map={}; selected=None; projections={}; number_map={}
        rows=ws.chapters()
        planned=self.planning.rows(project,'chapter')
        volumes={v['id']:v['number'] for v in self.planning.rows(project,'volume')}
        ordered=sorted(planned,key=lambda c:(volumes.get(c['volume'],0),c['order']))
        # Stable cards are mapped in book order; duplicate display numbers do not become IDs.
        for index, card in enumerate(ordered,1):
            chapter_map[card['id']]='chapter-'+str(index).zfill(3)
            if card['id']==request.chapter_id:selected=chapter_map[card['id']]
        if not ordered:
            ordered=[{'id':'legacy-'+str(row['number']),'number':row['number'],'title':row.get('title'),'pov':{},'characters':[],'scenes':[],'story_time':None,'location':None} for row in rows]
            chapter_map={c['id']:'chapter-'+str(c['number']).zfill(3) for c in ordered}
        for index,card in enumerate(ordered,1):
            id=chapter_map[card['id']]
            # Legacy manuscript paths are global numbered chapters. Avoid ambiguous mappings across volumes.
            same_number=[c for c in ordered if c['number']==card['number']]
            row=next((r for r in rows if r['number']==card['number']),{}) if len(same_number)==1 else {}
            source=row.get('final') or row.get('draft');body=ws.content(source)['content'] if source else ''
            plan=ws.yaml_file(row['plan']) if row.get('plan') else {}
            if len(same_number)==1:number_map[card['number']]=id
            cast=cast_projection(card,body,cards)
            projections[id]=cast
            pov=pov_id(card.get('pov')) or pov_id(plan.get('pov'))
            setting=plan.get('setting') or {}
            location=card.get('location') or setting.get('location')
            moment=card.get('story_time') or setting.get('story_time')
            cast['chapter_time']={'value':moment,'source':'PLAN','scene_times':'UNKNOWN_UNLESS_EXPLICIT'}
            meta={'id':id,'title':card.get('title') or 'Chapter '+str(index),'number':index,'status':'final' if row.get('final') else 'draft' if source else 'outline',
                  'pov':native_id(pov) if pov else '', 'characters':[native_id(c) for c in cast['on_page']],
                  'mentions':[native_id(c) for c in cast['mentions']],
                  'locations':[native_id(location)] if location else []}
            if pov and meta['pov'] not in meta['characters']:meta['characters'].append(meta['pov'])
            if moment and re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',moment):meta.update(date=moment[:10],time=moment[11:16])
            if card.get('temporal_mode')=='FLASHBACK':meta['time-skip']='flashback'
            self.markdown(root/'chapters'/f'{id}.md',meta,'# '+meta['title']+'\n\n## Outline\nAudit projection only; planned changes have no fact authority.\n\n---\n\n'+body)
            for scene in card.get('scenes',[]):
                sid=native_id(scene['id'])
                sm={'id':sid,'title':scene.get('purpose') or sid,'chapter':id,'scene':scene['order'],'status':meta['status'],
                    'pov':native_id(pov_id(scene['pov'])) if pov_id(scene.get('pov')) else meta['pov'],
                    'characters':[native_id(c) for c in scene.get('characters',[]) if c not in cast['remote_explicit']],
                    'location':native_id(scene['location']) if scene.get('location') else ''}
                # A chapter start is not the timestamp of every scene. Copying it
                # invented simultaneous travel. Unknown scene times stay absent.
                scene_time=scene.get('story_time')
                if scene_time and re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',str(scene_time)):
                    sm.update(date=str(scene_time)[:10],time=str(scene_time)[11:16])
                if card.get('temporal_mode')=='FLASHBACK':sm['flashback-to']=id
                self.markdown(root/'scenes'/f'{sid}.md',sm,'')
            if request.chapter and card['number']==request.chapter and len(same_number)==1:selected=id
        for fact_id,fact in facts.items():
            for receipt in fact.get('known_by',[]):
                if not isinstance(receipt,dict):continue
                character=receipt.get('character_id');number=receipt.get('acquired_chapter')
                if type(number) is not int or number>current.get('project',{}).get('current_chapter',0):continue
                if not character or not any(r['canonical']['id']==character for r in cards):continue
                entry={'character':native_id(character),'knows':str(fact.get('canonical_truth') or ''),'fact':native_id(fact_id)}
                learned=number_map.get(number) if isinstance(number,int) and number>0 else None
                if learned and (root/'chapters'/f'{learned}.md').is_file():entry['learned-in']=learned
                elif isinstance(number,int) and number>0: continue  # Missing historical witness is not pre-story knowledge.
                knowledge.append(entry)
        objects=[]
        for item_id,item in ws.yaml_file('state/items.yaml').get('items',{}).items():
            if not isinstance(item,dict):continue
            aid=native_id(item_id)
            self.markdown(root/'worldbuilding/artifacts'/f'{aid}.md',{'id':aid,'name':item.get('name') or item_id,'type':'prop'},'')
            status=str(item.get('status') or 'unknown').lower()
            objects.append({'artifact':aid,'owner':native_id(item['holder']) if item.get('holder') else '',
                            'location':native_id(item['location']) if item.get('location') else '',
                            'status':status if status in ['active','lost','destroyed','hidden','transferred','unknown'] else 'unknown'})
        self.markdown(root/'continuity/state.md',{'type':'continuity-state','current-chapter':current.get('project',{}).get('current_chapter',0),
                       'character-state':state_chars,'knowledge-state':knowledge,'object-state':objects},'# Derived committed facts\n')
        self.command(['reindex',str(root)],root,emit,cancelled)
        self.command(['wordcount',str(root),'--write'],root,emit,cancelled)
        committed_timeline=ws.yaml_file('state/timeline.yaml').get('events',[]) if (ws.root/'state/timeline.yaml').is_file() else []
        (root/'adapter-evidence.json').write_text(json.dumps({'version':'0.6','chapters':projections,'committed_timeline':committed_timeline,
            'knowledge_source':'COMMITTED_RECEIPTS_ONLY','scene_times':'EXPLICIT_ONLY',
            'native_characters':'ON_PAGE_INCLUDING_REMOTE','physical_cast':'PLAN_ASSERTION_NOT_PROSE_FACT',
            'semantic_coverage':'LIMITED'},ensure_ascii=False,indent=2),encoding='utf8')
        return root, selected, chapter_map

    def run(self, project, request, command, emit, cancelled):
        if command not in STORY_COMMANDS: raise ConsoleError('未开放的 Story 命令',403)
        root,selected,mapping=self.project(project,request,emit,cancelled)
        args=[command,str(root)]
        if command in ['context','knowledge']:
            if not selected:raise ConsoleError('请选择已存在的当前章节',422)
            args=['context',selected,'--budget','3000'] if command=='context' else ['knowledge',native_id(request.character_id),'--at',selected]
        elif command=='names':
            if not request.names:raise ConsoleError('请输入候选名字',422)
            if any(not name.strip() or name.startswith('-') or '\n' in name or '\r' in name for name in request.names):
                raise ConsoleError('候选名字不能作为 CLI 参数',422)
            args=['names',*request.names]
        result=self.command(args,root,emit,cancelled)
        issues=[{'severity':r.get('severity','WARN').upper(),'message':r.get('message',''),
                 'evidence':[str(r.get('file','')),str(r.get('code',''))]} for r in result.get('diagnostics',[])]
        issues.append({'severity':'WARN','message':'此为数据投影的第二意见：自由文本伤势/道具因果、完整知识凭证、错误信念及中文对白归属仍由本地 Checker / POV 审稿负责。','evidence':['docs/reviewer-routing.md']})
        if command=='context':
            issues.append({'severity':'WARN','message':'辅助 Context 不提供给 Writer；Writer 继续使用 novel-context-builder 的过滤包。','evidence':['REFERENCE / SECOND OPINION']})
        return {'verdict':'FAIL' if any(i['severity']=='ERROR' for i in issues) else 'WARN',
                'summary':'Story Skills '+command+' 已返回原生结果；未修改 Canon / State。','issues':issues,
                'report_only':True,'provider':'Story Skills','skill':'story-maintenance','native':result,
                'stable_id_mapping':mapping,'projection':str(root),'author_only':command in ['context','knowledge'],
                'adapter_evidence':json.loads((root/'adapter-evidence.json').read_text(encoding='utf8')),
                'native_attribution_authoritative':False,'semantic_coverage':'DETERMINISTIC_PROJECTION_ONLY'}
