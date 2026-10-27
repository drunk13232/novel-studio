"""Explicit original-fiction fixture; never seed a personal project.
Synthetic author records exercise retrieval and temporal projection, not real AI
semantic State validation. CLI refuses an existing non-fixture workspace.
"""
import copy,json,os,sys,time,argparse,shutil,uuid,asyncio
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def seed(s,p,root,count=40):
    """Author fixture, hash-bound ledgers and inverse patches, not AI semantics."""
    from app.creative.state_view import read_state
    from app.tasks.router import core_workflow
    w=core_workflow(s.registry.engine);ws=s.registry.workspace(p);state=read_state(ws,s.registry.engine)
    a,b=[v['canonical']['id'] for v in s.tools.characters.list(p)]
    state['chapter-ledger.yaml']['entries']=[]
    state['items.yaml']['items']={'TEST_WEAPON':{'name':'隔离练习用剑','holder':a,'location':None,'status':'完好','writer_view':[]}}
    state['knowledge-state.yaml']['facts']={};state['timeline.yaml']['events']={}
    state['current-story-state.yaml']['project']['story_date']='2041-10-01T00:00:00+08:00'
    current=copy.deepcopy(state)
    for n in range(1,count+1):
        date=f'2041-10-{(n-1)//24+1:02}T{(n-1)%24:02}:00:00+08:00'
        path=f'chapters/chapter-{n}/draft.txt';f=root/path;f.parent.mkdir(exist_ok=True);body=f'第{n}章隔离原文。江予核对练习用剑。周栖说：“这只是我的猜测。”'
        if n==12:body+='练习用剑损坏，不能使用。'
        if n==25:body+='这是一段倒叙：江予回忆十月一日的交接，并未提前知道暗号。'
        if n==37:body+='练习用剑已经修复。'
        if n==40:body+='周栖接过练习用剑。'
        f.write_text(body,'utf8');sha=__import__('hashlib').sha256(f.read_bytes()).hexdigest();ops=[]
        if n in (12,37,40):
            before=copy.deepcopy(current['items.yaml']['items']['TEST_WEAPON']);after=copy.deepcopy(before)
            after['status']='损坏' if n==12 else '修复' if n==37 else '可用';after['holder']=b if n==40 else a
            ops=[{'file':'items.yaml','pointer':'/items/TEST_WEAPON','before':before,'after':after,'evidence':body}];current['items.yaml']['items']['TEST_WEAPON']=after
        ops.append({'file':'current-story-state.yaml','pointer':'/project/story_date','before':current['current-story-state.yaml']['project']['story_date'],'after':date,'evidence':body})
        current['current-story-state.yaml']['project']['story_date']=date
        proposal={'proposal_id':f'isolated-{n}','final':{'chapter':n,'body_path':path,'body_sha256':sha},'extraction':{'operations':ops},'author_state_time':{'value':date,'basis':'ISOLATED_AUTHOR_FIXTURE_NOT_REAL_AI'}}
        w.y.write(root/f'state/proposed/isolated-{n}.yaml',proposal)
        current['chapter-ledger.yaml']['entries'].append({'chapter':n,'body_sha256':sha,'proposal_id':proposal['proposal_id'],'proposal_sha256':w.digest(proposal),'committed_at':date,'revision':n})
    current['current-story-state.yaml']['project']['current_chapter']=count
    for path,value in current.items():w.y.write(root/'state'/path,value)
    return w,current,a,b

def enrich(s,p,root,count):
    """Original authored test corpus, two volumes, explicit expected outcomes."""
    from app.creative.narrative_memory import temporal_state
    from app.creative.state_view import read_state
    from app.tasks.router import core_workflow
    from app.studio_tools import utf16_index,normalized
    from model import VIEW,FACT,RECEIPT,EVENT,RELATIONSHIP
    w=core_workflow(s.registry.engine);ws=s.registry.workspace(p);full=read_state(ws,s.registry.engine)
    state,_=temporal_state(ws,s.registry.engine,full,0);state['chapter-ledger.yaml']['entries']=[]
    state['current-story-state.yaml']['project'].update(current_chapter=0,story_date='2041-10-01T00:00:00+08:00')
    a,b=[v['canonical']['id'] for v in s.tools.characters.list(p)];location=state['current-story-state.yaml']['location']['current']
    first_card=w.y.read(next((root/'outlines/chapters').glob('chapter_*.yaml')));volume=w.y.read(next((root/'outlines/volumes').glob('volume_*.yaml')))
    vids=[volume['id'],'volume_'+uuid.uuid5(uuid.NAMESPACE_URL,'novel-studio-isolated-volume-2').hex]
    for i,vid in enumerate(vids):
        v=copy.deepcopy(volume);v.update(id=vid,number=i+1,title='隔离卷 · '+str(i+1),purpose='合成回归样本，不是真实小说');w.y.write(root/'outlines/volumes'/f'{vid}.yaml',v)
    texts={3:'江予在蓝灯罩内侧看见一道细裂纹。她只记下形状，没有推断是谁留下的。',6:'周栖怀疑红灯表示通航，又承认自己没有核对过说明。',7:'江予左手擦伤，缠好绷带后仍能走路，握笔却不稳。',10:'说明写得很清楚：红灯表示封航。江予独自读完，尚未告诉周栖。',12:'练习用剑的剑刃断裂了，江予把它封存，修复尚未开始。',18:'江予把说明交给周栖，周栖确认红灯表示封航，撤回此前的猜测。',19:'周栖把灯罩裂纹当成运输碰撞的痕迹；这只是他的解释，尚无独立证据。',20:'两人把钥匙分开保管，仍然合作，但不再替对方签收。',25:'这一节是倒叙。十月一日凌晨三点的江予尚未读过封航说明。她看见红灯，并不知道它的含义。',26:'旁白记述：江予拿起完好无损的练习用剑，直接完成了练习。这一章没有发生修复。',28:'江予左手伤口已经愈合，终于能自己握稳笔。',29:'江予曾坚持任何决定都要等齐证据，如今愿意先把人带到干燥处，再补全记录，但仍担心责任被抹去。',31:'江予证实灯罩裂纹的方向与运输碰撞不符，旧解释被撤回；她没有据此指认责任人。',32:'周栖说：“我早就知道完整暗号是潮声三叠。”叙述没有证明他的话；这句话应当保留为人物声称。',35:'封存记录再次确认，练习用剑仍未修复，无法投入练习。',37:'工匠当着江予的面修复练习用剑，并留下修复记录。',38:'完整暗号潮声三叠第一次写在公开说明上，江予与周栖同时读到。',39:'江予找到制作记录，裂纹来自旧灯罩的热应力；碰撞解释被重新解释，损坏原因得到局部回收。',40:'江予把修复后的练习用剑交给周栖。她不再把谨慎等同于永不行动，也不把一次让步当成原则已经解决。'}
    for n in range(1,count+1):
        raw=w.y.read(root/f'state/proposed/isolated-{n}.yaml');date=raw['author_state_time']['value'];path=f'chapters/chapter-{n}/draft.txt'
        passage=texts.get(n,'江予核对登记，周栖把未核项目留空。桌上的蓝灯还亮着，他们没有把沉默当作同意。')
        body=f'第{n}章 · 隔离长篇检索样本\n\n'+passage+'\n\n'+('窗外雨声渐密。江予把纸移到干燥处，问周栖是否愿意承担下一步的记录。周栖没有立刻答应，先指出她遗漏的一项条件。两人的目的相近，愿意承担的代价却不同。' if n%3 else '周栖翻过纸页。风从门缝里挤进来，吹动尚未干透的墨迹。江予没有重复刚才的问题，先把自己的名字填在应由自己负责的位置。')+'\n'
        (root/path).write_text(body,'utf8')
        for name in ['final.md','final.txt']:
            f=root/f'chapters/chapter-{n}'/name
            if f.exists():f.write_text(body,'utf8')
        cid=first_card['id'] if n==1 else 'chapter_'+uuid.uuid5(uuid.NAMESPACE_URL,'novel-studio-isolated-chapter-'+str(n)).hex
        card=copy.deepcopy(first_card);card.update(id=cid,number=n,order=n,title='隔离情节 '+str(n),status='DRAFTED',volume=vids[0 if n<=20 else 1],story_time='2041-10-01T03:00:00+08:00' if n==25 else date,temporal_mode='FLASHBACK' if n==25 else 'PRESENT',purpose='验证连续性，不是真实作品',chapter_goal=passage,notes=None)
        w.y.write(root/'outlines/chapters'/f'{cid}.yaml',card)
        ops=[]
        def change(file,pointer,after):
            keys=pointer[1:].split('/');cursor=state[file]
            for k in keys[:-1]:cursor=cursor[k]
            before=copy.deepcopy(cursor.get(keys[-1]));ops.append({'file':file,'pointer':pointer,'before':before,'after':copy.deepcopy(after),'evidence':passage});cursor[keys[-1]]=copy.deepcopy(after)
        view=lambda text:{**VIEW,'text':text,'visibility':'PUBLIC','known_by':[],'since_chapter':n,'story_time':date}
        event={**copy.deepcopy(EVENT),'id':'ISOLATED_E'+str(n),'chapter':n,'story_time':card['story_time'],'location':location,'characters':[a,b],'summary':passage,'writer_view':[view(passage)]}
        change('timeline.yaml','/events/'+event['id'],event)
        if n in (12,37,40):
            item=copy.deepcopy(state['items.yaml']['items']['TEST_WEAPON']);item.update(status='损坏' if n==12 else '修复' if n==37 else '可用',holder=b if n==40 else a,writer_view=[view('练习用剑'+('已损坏并封存。' if n==12 else '已经修复。' if n==37 else '已经交给周栖。'))]);change('items.yaml','/items/TEST_WEAPON',item)
        if n in (7,28):
            char=copy.deepcopy(state['characters/'+a+'.yaml']);char['status']['physical_condition']='左手擦伤' if n==7 else '左手伤口已愈合';char.update(last_updated_chapter=n,writer_view=[view(passage)])
            change('characters/'+a+'.yaml','/status',char['status']);change('characters/'+a+'.yaml','/writer_view',char['writer_view'])
        if n in (6,10,18):
            fact=copy.deepcopy(state['knowledge-state.yaml']['facts'].get('ISOLATED_SIGNAL',FACT));fact.update(canonical_truth='红灯表示封航。',introduced_chapter=6,public=False)
            receipt=lambda actor:{**RECEIPT,'character_id':actor,'acquired_chapter':n,'story_time':date,'source_event':event['id']}
            if n==6:fact['false_beliefs'][b]={'belief':'红灯表示通航。','acquired_chapter':6,'story_time':date,'source_event':event['id']}
            if n==10:fact['known_by'].append(receipt(a))
            if n==18:fact['known_by'].append(receipt(b));fact['false_beliefs'].pop(b,None)
            change('knowledge-state.yaml','/facts/ISOLATED_SIGNAL',fact)
        if n==38:
            fact=copy.deepcopy(FACT);fact.update(canonical_truth='完整暗号是潮声三叠。',introduced_chapter=38,public=False,known_by=[{**RECEIPT,'character_id':actor,'acquired_chapter':38,'story_time':date,'source_event':event['id']} for actor in [a,b]]);change('knowledge-state.yaml','/facts/ISOLATED_CODE',fact)
        if n==20:change('relationships.yaml','/relationships/ISOLATED_REL',{**copy.deepcopy(RELATIONSHIP),'characters':[a,b],'kind':'保留合作但分别签收','last_updated_chapter':n,'writer_view':[view(passage)]})
        change('current-story-state.yaml','/project/story_date',date)
        sha=__import__('hashlib').sha256((root/path).read_bytes()).hexdigest();v={'proposal_id':f'isolated-{n}','final':{'chapter':n,'body_path':path,'body_sha256':sha},'extraction':{'operations':ops},'author_state_time':{'value':date,'basis':'ISOLATED_AUTHOR_FIXTURE_NOT_SEMANTIC_AI'}}
        w.y.write(root/f'state/proposed/isolated-{n}.yaml',v);state['chapter-ledger.yaml']['entries'].append({'chapter':n,'body_sha256':sha,'proposal_id':v['proposal_id'],'proposal_sha256':w.digest(v),'committed_at':date,'revision':n})
    state['current-story-state.yaml'].update(revision=count);state['current-story-state.yaml']['project']['current_chapter']=count
    for path,value in state.items():w.y.write(root/'state'/path,value)
    from app.creative.literary_models import Save,CoreDetails,Event
    def evidence(n):
        path=f'chapters/chapter-{n}/draft.txt';doc=s.tools.doc(p,path);quote=texts[n];text=normalized(doc);a0=text.index(quote)
        return {'path':path,'revision':doc['etag'],'quote':quote,'start':utf16_index(text,a0),'end':utf16_index(text,a0+len(quote))}
    def save(details,text):
        return s.literary_core.save(p,Save(etag=s.workbench.entries(p)['etag'],text=text,details=CoreDetails(**details),confirm=True))
    if count>=40:
        result=save({'kind':'clue','title':'蓝灯罩裂纹','phase':'PLANNED'},'隔离样本中的跨卷伏笔，计划与正文证据分开。')
        clue=result.get('id') or result.get('record',{}).get('id')
        if not clue:clue=next(v['id'] for v in s.literary_core.index(p)['records'] if v['literary']['title']=='蓝灯罩裂纹')
        for n,phase in [(3,'PLACED'),(19,'MISDIRECTED'),(31,'PARTIAL'),(39,'RESOLVED')]:
            card=s.literary_core.card(p,clue);s.literary_core.event(p,clue,Event(etag=s.workbench.entries(p)['etag'],phase=phase,text=texts[n],evidence=[evidence(n)],confirm=True))
        for n,stance in [(10,'证据齐全前不下判断'),(29,'先保护人，同时保留记录'),(40,'承认行动和谨慎之间的矛盾仍未解决')]:
            save({'kind':'thought','title':'江予的选择 · '+str(n),'phase':'PLACED','positions':[{'character':a,'stance':stance,'experience':texts[n],'choice':'承认有限证据下的责任','cost':'需要承担判断的不确定性','change':'非线性变化，不等于数值成长'}],'evidence':[evidence(n)]},'隔离作者解释，不是客观思想结论。')
    return {'characters':[a,b],'chapters':count,'volumes':2,'expected_conflict_chapter':26,'attributed_claim_not_truth':32,'legal_flashback':25,'clue_nodes':[3,19,31,39],'fixture_authority':'SYNTHETIC_AUTHOR_RECORDS_NOT_AI_COMMIT_VALIDATION'}

async def exercise(args,s,p,root,output):
    from app.creative.evaluation_models import Request,Create,Run
    from app.creative.evaluation_rubrics import defaults
    from app.creative.narrative_memory import Query,inspect,temporal_state
    from app.creative.state_view import read_state
    from app.library.storage import write
    ev=s.literary_core.reviews.evaluation if hasattr(s.literary_core.reviews,'evaluation') else None
    if ev is None:
        from app.creative.evaluation import Evaluation
        ev=Evaluation(s.literary_core.reviews,s.literary_core)
    a,b=[v['canonical']['id'] for v in s.tools.characters.list(p)];measurements={}
    for name,cut,at in [('cold',30,''),('warm',30,''),('flashback',40,'2041-10-01T03:00:00+08:00')]:
        started=time.monotonic();r=inspect(s,p,Query(through_chapter=cut,story_time=at,character_id=a,queries=['断裂','修复']))
        measurements[name]={'seconds':round(time.monotonic()-started,4),'audit':r['audit'],'items':r['items'],'knowledge':r['knowledge'],'evidence_chapters':sorted({int(h['number']) for h in r['evidence']})}
    structure=inspect(s,p,Query(through_chapter=40,character_id=a,include_structure=True))
    write(output/'local-checks.json',{'kind':'LOCAL_DETERMINISTIC_NOT_REAL_AI','measurements':measurements,'structure_records':len(structure['structure'].get('records',[]))})
    print('LOCAL',json.dumps({k:v['seconds'] for k,v in measurements.items()}),flush=True)
    if not args.run_ai:return
    record=output/'editorial-job.json'
    if args.resume and record.is_file() and not args.new_evaluation:job=ev.get(p,json.loads(record.read_text('utf8'))['id'])
    else:
        rubric=defaults()[0]['rubric'];rubric['name']='隔离长篇总编辑：结构、人物与知识证据';rubric['dimensions']=[v for v in rubric['dimensions'] if v['id'] in ['character','structure','logic','thought']]
        request=Request(scope='book',purpose='editorial',rubric=rubric,model='codex',editorial_methods=['continuity','review'],editorial_goal='阅读全部目标文本，检查跨章连续性和结构。每个短章节最多保留一条有价值的发现；没有问题可以为空。综合时归纳两至三项根本问题，引用可核实证据。区分人物声称与旁白事实，尊重明确的倒叙。不要因是测试样本就编造缺陷。',editorial_lens='用于核对长篇证据与编辑流程，保留开放思想；不要求固定三幕或积极成长。')
        preview=ev.preview(p,request);write(output/'editorial-preview.json',preview)
        job=ev.create(p,Create(request=request,preview_hash=preview['preview_hash'],confirm=True))
        if record.is_file():shutil.copy2(record,output/('previous-'+json.loads(record.read_text('utf8'))['id']+'.json'))
        write(record,{'id':job['id']})
    for i in range(4):
        job=ev.get(p,job['id'])
        if job['status']=='COMPLETED':break
        task=ev.run(p,job['id'],Run(etag=job['etag'],calls=args.calls,seconds=600,confirm=True,retry_incomplete=args.resume))
        print('BATCH',i+1,task['id'],flush=True)
        await s.manager(p).get(task['id']).runner
        job=ev.get(p,job['id']);write(output/'editorial-result.json',job)
        print('COVERAGE',job['status'],job['models'][0]['coverage'],flush=True)
        if job['status']=='CANCELLED':break
        if s.manager(p).get(task['id']).status=='FAILED':raise RuntimeError(s.manager(p).get(task['id']).error)
    write(output/'editorial-result.json',ev.get(p,job['id']))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--chapters',type=int,default=40);parser.add_argument('--run-ai',action='store_true');parser.add_argument('--resume',action='store_true');parser.add_argument('--new-evaluation',action='store_true');parser.add_argument('--calls',type=int,default=20);args=parser.parse_args()
    if not 40<=args.chapters<=500 or not 1<=args.calls<=20:raise SystemExit('bounded fixture: 40–500 chapters, 1–20 calls per explicit batch')
    output=Path(args.output).resolve();workspace=output/'workspace'
    if output.exists() and not args.resume:raise SystemExit('refusing to overwrite; choose a new isolated output')
    if args.resume and not (output/'fixture.json').is_file():raise SystemExit('only a recorded isolated fixture can be resumed')
    output.mkdir(parents=True,exist_ok=True)
    if not workspace.exists():shutil.copytree(ROOT/'desktop/preview-template',workspace)
    os.environ.update(NOVEL_WORKSPACE=str(workspace),NOVEL_STUDIO_DATA=str(output/'data/workspaces'))
    sys.path.insert(0,str(ROOT/'web/backend'))
    from app.config import Settings
    from app.main import create_app
    from app.library.storage import write
    app=create_app(Settings(workspace=workspace));s=app.state.writing_assist;p=next((workspace/'projects').glob('novel_*')).name;root=workspace/'projects'/p
    if not args.resume:seed(s,p,root,args.chapters);write(output/'fixture.json',enrich(s,p,root,args.chapters))
    asyncio.run(exercise(args,s,p,root,output))

if __name__=='__main__':main()
