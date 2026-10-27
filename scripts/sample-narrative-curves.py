"""One isolated 500-chapter local sample, not a UI or inference benchmark."""
import argparse,hashlib,json,os,shutil,sys,tempfile,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];EVIDENCE=ROOT/'docs/creative-insights/private-checks';EVIDENCE.mkdir(parents=True,exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--output');args=parser.parse_args()
OUTPUT=Path(args.output).resolve() if args.output else EVIDENCE/'curve-500.json'
assert OUTPUT.is_relative_to(EVIDENCE.resolve()) and OUTPUT.suffix=='.json'
if OUTPUT.exists():raise RuntimeError('Keep previous sample evidence; choose a new output path')
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'web/backend'))
with tempfile.TemporaryDirectory(prefix='curve-500-',dir=EVIDENCE) as directory:
    isolated=Path(directory).resolve();assert isolated.is_relative_to(EVIDENCE.resolve())
    workspace=isolated/'workspace';shutil.copytree(ROOT/'desktop/preview-template',workspace)
    os.environ['NOVEL_WORKSPACE']=str(workspace);os.environ['NOVEL_STUDIO_DATA']=str(isolated/'data/workspaces')
    from app.main import create_app
    from app.config import Settings
    from app.domain.planning import ChapterCard,dump
    from app.creative.insight_models import CurveAnalyze
    application=create_app(Settings(workspace=workspace));service=application.state.creative_insights
    tools=application.state.studio_tools;project=next((workspace/'projects').glob('novel_*')).name;root=workspace/'projects'/project
    volume='';plans=root/'outlines/chapters';plans.mkdir(parents=True,exist_ok=True)
    import yaml
    existing={row['number']:(file,row['id']) for file in plans.glob('*.yaml') for row in [yaml.safe_load(file.read_text(encoding='utf8'))]}
    assert all(number<=500 for number in existing),'Fixture has more chapters than this bounded sample.'
    paragraph='小岚听见远处枪声，危险正在靠近。她感到恐惧，仍保留一点希望。雨水落在空荡的台阶。'
    text='\n'.join([paragraph]*36)
    for number in range(1,501):
        card=ChapterCard(id=existing.get(number,(None,'chapter_'+uuid.uuid4().hex))[1],number=number,order=number,volume=volume,title='合成性能章'+str(number))
        (plans/(card.id+'.yaml')).write_text(dump(card.model_dump()),encoding='utf8')
        file=root/f'chapters/chapter-{number}/draft.txt';file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf8')
    def protected():
        return {str(file.relative_to(root)):hashlib.sha256(file.read_bytes()).hexdigest() for folder in ['chapters','state','settings','characters','bible'] for file in (root/folder).rglob('*') if file.is_file()}
    before=protected();counts={'body_reads':0};ws=tools.registry.workspace(project);original=ws.content
    def measured(path,*args,**kwargs):
        if path.startswith('chapters/'):counts['body_reads']+=1
        return original(path,*args,**kwargs)
    ws.content=measured
    started=time.perf_counter();first=service.curve.analyze(project,CurveAnalyze(whole_book=True));first_seconds=time.perf_counter()-started;first_reads=counts['body_reads']
    started=time.perf_counter();cached=service.curve.analyze(project,CurveAnalyze(whole_book=True));cached_seconds=time.perf_counter()-started;cached_reads=counts['body_reads']-first_reads
    started=time.perf_counter();opened=service.curve.index(project);read_seconds=time.perf_counter()-started
    assert len(first['chapters'])==500 and len(first['points'])==500;assert before==protected()
    result={'scope':'LOCAL_SERVICE_SAMPLE_NOT_DESKTOP_OR_BROWSER','chapters':500,'characters_per_chapter':len(text),'points':len(first['points']),'pipeline':'actual BookCenter catalog + StudioTools + PlotMatrix + NarrativeCurve','first_analyze_seconds':round(first_seconds,3),'cached_analyze_seconds':round(cached_seconds,3),'cached_index_seconds':round(read_seconds,3),'first_workspace_chapter_reads':first_reads,'cached_workspace_chapter_reads':cached_reads,'read_counter_scope':'all Workspace.content chapters/ calls, including existing PlotMatrix heading metadata reads','source_files_unchanged':True,'external_ai_calls':0}
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(result,ensure_ascii=False,indent=2))
