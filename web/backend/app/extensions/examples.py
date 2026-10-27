"""Auditable public samples; generated from fixed data, never user files."""
import io,json,zipfile,hashlib
from .models import Manifest
from app.errors import ConsoleError

def package(name):
    base={'schema_version':'novel-studio-plugin/1','id':'example.'+name,'name':'','version':'1.0.0','min_app_version':'2.20.0','description':'','author':'Novel Studio examples','license':'Local demonstration; project license pending','actions':[],'commands':[],'settings':[],'resources':[],'files':{}}
    files={}
    if name=='writing-shortcuts':
        base.update(name='写作快捷操作 / Writing shortcuts',description='调整字号、切换专注和打开章节；仅调用原有界面 Action。',actions=['set_editor_font_size','toggle_focus_mode','open_chapter'],settings=[{'id':'font_size','label':'正文大小 / Font size','type':'integer','default':18,'minimum':14,'maximum':32},{'id':'chapter','label':'章节号 / Chapter','type':'integer','default':1,'minimum':1,'maximum':99999}],commands=[{'id':'font','title':'应用插件字号','kind':'action','action':'set_editor_font_size','arguments':{'size':'${font_size}'}},{'id':'focus','title':'切换专注模式','kind':'action','action':'toggle_focus_mode'},{'id':'chapter','title':'打开指定章节','kind':'action','action':'open_chapter','arguments':{'number':'${chapter}'}}])
    elif name=='chapter-summary':
        base.update(name='章节目录速览 / Chapter summary',description='真实 Python 汇总当前作品目录，不读取正文，不调用模型。',actions=['get_active_project','list_chapters'],commands=[{'id':'summarize','title':'生成目录速览','kind':'python','script':'scripts/summary.py'}])
        files['scripts/summary.py']=b'from novel_studio_api import Studio\nimport json\nstudio=Studio.connect()\nproject=studio.projects.current()\nchapters=studio.chapters.list(limit=100)\nprint(json.dumps({"project":project,"chapters":chapters},ensure_ascii=False,indent=2))\n'
    elif name=='integration-entries':
        base.update(name='创作接入入口 / Integration entries',description='集中打开已有 AI 接口、模型分配和世界逻辑实验室。',commands=[{'id':'providers','title':'配置 AI Provider','kind':'entry','target':{'type':'settings','value':'api'}},{'id':'routing','title':'配置任务模型','kind':'entry','target':{'type':'settings','value':'models'}},{'id':'lab','title':'打开世界逻辑实验室','kind':'entry','target':{'type':'page','value':'worldlogic'}}])
    else:raise ConsoleError('示例插件不存在',404)
    files['README.md']=('Novel Studio plugin example\n\nImport, inspect permissions, install, enable, then run a command explicitly. No install hooks, credentials or startup tasks.\n').encode()
    base['files']={key:hashlib.sha256(value).hexdigest() for key,value in files.items()}
    base=Manifest.model_validate(base).model_dump();files['manifest.json']=json.dumps(base,ensure_ascii=False,indent=2).encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for key,value in files.items():z.writestr(key,value)
    return out.getvalue()
