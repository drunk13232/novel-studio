"""Reproducible, opt-in writing comparison using existing Novel Studio services.

No real works are opened. Creates only an isolated copy of the public preview
fixture. Inference requires --run-ai; grading additionally requires --judge.
Codex uses the existing login; no API key or global configuration is copied.
"""
import argparse,asyncio,hashlib,json,os,random,shutil,sys,threading,time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 {'id':'dialogue','methods':['context','scene','character'],'mode':'director','han':700,'start':'何霁把待签的移交表放在修复台上。林葭正在揭一张受潮信封的衬纸，镊子停在半空。窗外最后一班渡轮已经鸣过笛。',
  'goal':'续写一场约700汉字的移交争执。何霁要林葭在闭馆前签署责任移交，林葭要求先核对一只缺失的木匣。两人都保护工作但不愿把担心的事说破。只写争执，不达成和解、不签字、不离开房间；停在门外有人敲门，两人尚未开门。可以创造当下对白、动作和非关键现场细节。'},
 {'id':'suspense','methods':['context','scene','continuity'],'mode':'quick','han':700,'start':'旧钟停在十七点二十分。何霁数了数柜门上的封条，四张，一张没少。林葭把台灯往里挪了一寸。',
  'goal':'续写约700汉字。两人核对封条发现右下角印泥颜色与其他三张略有不同，但目前不知道原因或责任人。何霁只能根据可见证据行动，林葭也没有额外秘密知识。保留多种解释，让疑点改变检查方法。只到两人决定保存封条照片，暂不开柜、不找出真凶、不揭晓木匣去向。允许合理的现场动作，不新增重大历史或特殊能力。'},
 {'id':'value_conflict','methods':['scene','character','writing'],'mode':'quick','han':800,'start':'仓房只剩一组能用的蓄电池。左边的门通向临时病房，右边的门后停着最后一辆转运车。何霁把电池提到两扇门之间。',
  'goal':'续写约800汉字的价值冲突。病房供电与车辆转运都需要这组电池，但目前只有一组，两人不能同时满足两边。何霁倾向先核实危险，林葭要尽快让患者离开漏雨的病房。两人有分量的理由通过物件、选择、受阻和代价出现，不要求哲学说教或结论正确。停在两人去核查患者名单之前，未作最终分配。不要借新电池、外援、超能力或未交代的重大过去消除当前难题。'},
 {'id':'style','methods':['style','character','writing'],'mode':'quick','han':700,'start':'雨沿着信箱的铰链往下滴。何霁收好钥匙，发现林葭还站在屋檐外。她手里那张回执没有折起来。',
  'goal':'续写约700汉字。两人已知道一封普通退信迟了三天，收件人已经搬走；只讨论明天如何查地址，不增加死亡、亲属、旧情或重大过去。遵循已给文风，保留句长变化、听觉、停顿和少量有功能的修辞。不同对白服务各自当前目的，留住未说透的理解，不在结尾复述情绪或宣讲道理。停在两人把回执装进干燥信封。'},
 {'id':'continuous_chapter','methods':['context','scene','character','style'],'mode':'quick','han':3000,'start':'临时邮局的卷帘门升到一半，何霁弯腰进去。林葭已经把三张待核对的清单铺在台上。',
  'goal':'续写一个约3000汉字的连续章节，按以下三个场景自然衔接：一，何霁和林葭在清晨核对清单，对一只登记在册但未找到的木匣发生争执，双方未签移交表；二，两人去仓房核查，发现架位旁有新鲜水痕，只能确定近期漏雨，不能推断责任人；三，两人回到修复台，商定先拍照、登记未核项目并暂缓移交，但木匣去向仍未知。只写这三场，不进入次日、不揭真相、不让人物关系突然亲密。允许当下对白和动作，保留两人的不同策略、利益和克制文风。思想通过取舍及责任压力呈现，不另写哲理总结。'}]

def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def sha(value):return hashlib.sha256(value.encode('utf8')).hexdigest()

def arguments():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--output',type=Path,required=True)
 p.add_argument('--run-ai',action='store_true',help='Explicitly send only these original fixture texts to the current Codex login.')
 p.add_argument('--judge',action='store_true',help='Run the existing literary evaluator on anonymous candidate text; same-model opinions are not independent evidence.')
 p.add_argument('--resume',action='store_true',help='Resume the same frozen fixture, preserving all existing attempts.')
 p.add_argument('--seed',type=int,default=213)
 p.add_argument('--cases',nargs='+',choices=[c['id'] for c in CASES],default=[c['id'] for c in CASES])
 return p.parse_args()

def setup(args):
 out=args.output.resolve();real_data=Path(os.environ.get('NOVEL_STUDIO_DATA',str(ROOT.parent/'NovelStudio Data'))).resolve()
 if out==real_data or real_data in out.parents or out==ROOT or out==ROOT/'projects' or ROOT/'projects' in out.parents:
  raise ValueError('Benchmark output must be separate from real application data and novels.')
 marker=out/'run.json'
 if out.exists() and any(out.iterdir()) and not (args.resume and marker.is_file()):raise ValueError('Use an empty output directory, or --resume for this benchmark marker.')
 out.mkdir(parents=True,exist_ok=True)
 fixture=out/'workspace'
 if not fixture.exists():shutil.copytree(ROOT/'desktop/preview-template',fixture)
 os.environ.update(NOVEL_WORKSPACE=str(fixture),NOVEL_STUDIO_DATA=str(out/'data'),NOVEL_STATIC_DIR=str(out/'no-static'),NOVEL_PORT='8913')
 sys.path.insert(0,str(ROOT/'web/backend'))
 from app.main import create_app
 from app.config import Settings
 app=create_app(Settings(workspace=fixture));director=app.state.creative_director
 project=next((fixture/'projects').glob('novel_*')).name;pr=fixture/'projects'/project
 if not marker.exists():
  import yaml
  characters=director.tools.characters.list(project)
  for i,entry in enumerate(characters[:2]):
   c=entry['canonical'];c['name']='何霁' if i==0 else '林葭';c['aliases']=[]
   c['identity']['summary']='临时邮局负责人，重证据；与林葭只是同事。' if i==0 else '档案修复师，保护工作完整性；与何霁只是同事。'
   c['speech'].update(tone='克制，短问句，先核对事实' if i==0 else '习惯反问，借具体工序表达异议',sentence_style='按当前处境变化，不使用固定口头禅')
   c['secrets']['author_only']=[]
   (pr/'characters'/f"{c['id']}.yaml").write_text(yaml.safe_dump(c,allow_unicode=True,sort_keys=False),encoding='utf8')
  # Bind the existing confirmed demo profile; do not create another profile store.
  profile=director.writing.references.bindings(project)['profiles'][0]['id']
  record={'version':'writing-comparison-1','created_at':datetime.now(timezone.utc).isoformat(),'seed':args.seed,'project_id':project,'profile_id':profile,'cases':{},'calls':[],
   'conditions':{'writer_model':'CURRENT_CODEX_LOGIN_VERIFIED_PER_CALL','reasoning_effort':'low','inputs':'same safe source objects and author goal in each pair','output_budget':'same Director limits; Codex session does not expose a strict output-token cap','prompt_budget':'recorded, not exactly equal because methods add input','paid_api_calls':False,'all_attempts_retained':True,'judge_blind_to_arm':True,'human_review':'NOT_RUN','same_model_judging_is_independent':False}}
  save(marker,record)
 return out,app,director,project,pr

async def main(args):
 out,app,s,p,pr=setup(args);manifest=json.loads((out/'run.json').read_text(encoding='utf8'))
 from app.creative.director import Create,Control,Limits
 from app.creative.writing import ContextChoice,Approval
 from app.creative.tasks import metadata
 from app.creative.text_statistics import measure
 from app.studio_tools import normalized,utf16_index
 rng=random.Random(args.seed)
 selected=[c for c in CASES if c['id'] in args.cases]
 for ci,case in enumerate(selected):
  order=['plain','enhanced'] if ci%2==0 else ['enhanced','plain']
  labels=['X','Y'];rng.shuffle(labels);mapping=dict(zip(['plain','enhanced'],labels));folder=out/case['id'];folder.mkdir(exist_ok=True)
  entry=manifest['cases'].get(case['id'])
  if not entry:
   target=f'chapters/chapter-{90+ci}/draft.txt';f=pr/target;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(case['start']+'\n',encoding='utf8')
   d=s.tools.doc(p,target);actor=s.tools.characters.list(p)[0]['canonical']['id']
   ctx=s.writing.preview(p,ContextChoice(path=target,revision=d['etag'],pov=actor,profile_ids=[manifest['profile_id']],previous_paths=[],budget=18000))
   s.writing.approve(p,ctx['id'],Approval(context_hash=ctx['context_hash'],confirm=True))
   row=s.create(p,Create(path=target,revision=d['etag'],context_id=ctx['id'],goal=case['goal'],mode=case['mode'],executor='codex',skills=case['methods'],start=utf16_index(case['start']+'\n',len(case['start']+'\n')),end=utf16_index(case['start']+'\n',len(case['start']+'\n')),limits=Limits(max_calls=4,seconds=600,output_characters=16000,output_tokens=6000)))
   entry={'director_id':row['id'],'source_path':target,'context_id':ctx['id'],'goal':case['goal'],'target_han':case['han'],'order':order,'labels':mapping,'outputs':{},'attempts':[],'fixture_hash':sha(json.dumps(case,ensure_ascii=False,sort_keys=True))}
   manifest['cases'][case['id']]=entry;save(out/'run.json',manifest);save(folder/'context.json',ctx)
  elif entry['fixture_hash']!=sha(json.dumps(case,ensure_ascii=False,sort_keys=True)):raise ValueError('Fixture changed. Start another run; do not overwrite this comparison.')
  if not args.run_ai:continue
  row=s.get(p,entry['director_id']);ctx=s.context(p,row)
  for arm in entry['order']:
   if entry['outputs'].get(arm,{}).get('status')=='completed':continue
   begin=time.monotonic();attempt={'arm':arm,'started_at':datetime.now(timezone.utc).isoformat()};entry['attempts'].append(attempt);save(out/'run.json',manifest)
   try:
    if arm=='enhanced':
     if row['mode']=='director' and not row['plan'].get('methods'):
      task=await s.control(p,row['id'],Control(etag=row['etag'],action='plan'))
      await s.manager(p).get(task['active_task']).runner;row=s.get(p,row['id']);save(folder/'director-plan.json',row)
      if row['status']!='PLAN_REVIEW':raise RuntimeError(row.get('last_error') or 'Director plan was not produced')
     prompt=s.writer_prompt(row,ctx,0);(folder/(arm+'-prompt.txt')).write_text(prompt,encoding='utf8')
     task=await s.control(p,row['id'],Control(etag=row['etag'],action='run',confirm_plan=True,continue_important=True))
     await s.manager(p).get(task['active_task']).runner;row=s.get(p,row['id']);save(folder/'director-result.json',row)
     result={'status':'completed' if row['status']=='CANDIDATE' else 'failed','output':row['draft'],'error':row.get('last_error'),'ai_metadata':row['usage'][-1] if row['usage'] else {}}
    else:
     basic={'goal':case['goal'],'materials':[dict(x) for x in ctx['packet']['sources']],'pov':ctx['packet'].get('pov'),'current_text':case['start'],'length_han':case['han']}
     prompt='按目标和所给资料续写小说，只返回新的正文，不重复已有开场。\n'+json.dumps(basic,ensure_ascii=False,separators=(',',':'))
     (folder/(arm+'-prompt.txt')).write_text(prompt,encoding='utf8');a=s.executor(p,row,prompt,120)
     partial=[];timer=threading.Timer(120,a.close);timer.daemon=True;timer.start()
     def emit(kind,text,data=None):
      if kind in {'message','llm_delta'}:partial.append((data or {}).get('delta',text))
     try:result=await asyncio.to_thread(a.start_task,prompt,emit,read_only=True,allow_web=False)
     finally:timer.cancel();a.close()
     result['ai_metadata']=metadata(a)
     if not result.get('output') and partial:result['output']=''.join(partial)
    result.update(seconds=round(time.monotonic()-begin,3),prompt_characters=len(prompt),prompt_sha256=sha(prompt),output_sha256=sha(result.get('output','')))
    output=result.get('output','');(folder/(arm+'.txt')).write_text(output,encoding='utf8');save(folder/(arm+'-result.json'),result)
    if output:save(folder/(arm+'-statistics.json'),measure(output))
    entry['outputs'][arm]={k:v for k,v in result.items() if k!='output'}
    # Only original isolated fixture chapters become score inputs, never real works.
    slot=120+ci*2+(0 if entry['labels'][arm]=='X' else 1);path=f'chapters/chapter-{slot}/draft.txt';file=pr/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(output,encoding='utf8')
    entry['outputs'][arm]['evaluation_path']=path
    attempt.update(status=result['status'],seconds=result['seconds'])
    print(json.dumps({'case':case['id'],'arm':arm,'status':result['status'],'seconds':result['seconds'],'characters':len(output),'model':result['ai_metadata'].get('observed_model') or result['ai_metadata'].get('model')},ensure_ascii=False),flush=True)
   except Exception as error:
    attempt.update(status='failed',error=str(error)[:1500]);print(json.dumps({'case':case['id'],'arm':arm,'error':str(error)[:300]},ensure_ascii=False),flush=True)
   save(out/'run.json',manifest)
  if args.judge:await judge(out,app,p,pr,case,entry,manifest)
 save(out/'run.json',manifest)

async def judge(out,app,p,pr,case,entry,manifest):
 from app.creative.evaluation_models import Request,Create,Run,Selection
 from app.creative.evaluation_rubrics import defaults
 from app.studio_tools import utf16_index
 ev=app.state.literary_evaluation;blind=[]
 for arm in sorted(entry['outputs'],key=lambda k:entry['labels'][k]):
  item=entry['outputs'][arm]
  if item['status']!='completed':continue
  label=entry['labels'][arm];text=(out/case['id']/(arm+'.txt')).read_text(encoding='utf8');blind.append('## '+label+'\n\n'+text)
  if item.get('evaluation_complete'):continue
  doc=ev.tools.doc(p,item['evaluation_path']);rubric=defaults()[0]['rubric'];dims={'style','character','logic'}|({'thought','emotion'} if case['id']=='value_conflict' else {'clue'} if case['id']=='suspense' else {'structure'} if case['id']=='continuous_chapter' else set())
  rubric['dimensions']=[d for d in rubric['dimensions'] if d['id'] in dims];rubric['positioning']='原创局部写作对照。只按原文、人物与作者目标评价，不猜来源或生成方法。没有额外历史证据。作者目标：'+case['goal'];rubric['version']='comparison-213-1'
  req=Request(scope='selection',selection=Selection(path=item['evaluation_path'],revision=doc['etag'],start=0,end=utf16_index(text,len(text)),quote=text),rubric=rubric,model='codex')
  if not item.get('evaluation_id'):
   v=ev.create(p,Create(request=req,preview_hash=ev.preview(p,req)['preview_hash'],confirm=True));item['evaluation_id']=v['id'];save(out/'run.json',manifest)
  v=ev.get(p,item['evaluation_id']);task=ev.run(p,v['id'],Run(etag=v['etag'],calls=1,seconds=240,confirm=True,retry_incomplete=False));await ev.center.manager(p).get(task['id']).runner
  v=ev.get(p,v['id']);save(out/case['id']/(label+'-evaluation.json'),v);item['evaluation_complete']=v['status']=='COMPLETED'
  print(json.dumps({'case':case['id'],'blind_label':label,'evaluation':v['status'],'score':v['models'][0].get('weighted')},ensure_ascii=False),flush=True)
 (out/case['id']/'BLIND-REVIEW.md').write_text('# '+case['id']+'\n\n'+case['goal']+'\n\n'+'\n\n'.join(blind)+'\n\n人工盲评：尚未进行。请先记录偏好、引用和不确定性，再查看 run.json 中的方法映射。\n',encoding='utf8')
 save(out/'run.json',manifest)

if __name__=='__main__':
 args=arguments()
 try:asyncio.run(main(args))
 except KeyboardInterrupt:raise SystemExit('Stopped by user. Existing result files are retained.')