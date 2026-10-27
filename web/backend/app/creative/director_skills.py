"""On-demand method sources; no skill installation, script execution or new agents."""
from pathlib import Path
import sys
from functools import lru_cache
from app.library.storage import digest
from app.errors import ConsoleError

METHODS={
 'world':('世界规则、地理与势力设计','.novelforge/references/phases/02-worldbuilding.md'),
 'research':('资料研究与事实边界','.agents/skills/novel-context-builder/SKILL.md'),
 'context':('长篇上下文与知识边界','.agents/skills/novel-context-builder/SKILL.md'),
 'scene':('场景导演','.novelforge/references/agents/playwright.md'),
 'character':('人物塑造与对白','.agents/skills/novel-character-checker/SKILL.md'),
 'writing':('中文小说叙事','.novelforge/references/agents/literary-renderer.md'),
 'style':('文风保持','.agents/skills/novel-style-reviewer/SKILL.md'),
 'continuity':('情节连续性','.agents/skills/novel-continuity-checker/SKILL.md'),
 'revision':('最小必要修订','.agents/skills/novel-editor/SKILL.md'),
 'review':('文学与剧情评审','.novelforge/references/agents/quality-inspector.md')}
def paths(engine,key):
    if key not in METHODS:raise ConsoleError('未知专业方法',422)
    if key=='research':return [Path.home()/'.codex/plugins/cache/research-skill/research-codex/0.4.2/skills/research/SKILL.md']
    primary=engine/METHODS[key][1]
    if not primary.is_file():
        primary=(Path(getattr(sys,'_MEIPASS',''))/'resources/creative-methods'/key/Path(METHODS[key][1]).name if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[4]/METHODS[key][1])
    result=[primary]
    home=Path.home()/'.codex/plugins/cache'
    if key in {'scene','character'}:
        name='sw-scene-craft' if key=='scene' else 'sw-dialogue'
        path=home/'screenwriting-skills/screenwriting/2.0.0/skills'/name/'SKILL.md'
        if path.is_file():result.append(path)
    return result

def catalog(engine):
    return [{'id':key,'name':label,'available':all(p.is_file() for p in paths(engine,key)),
             'sources':[p.name if p.name!='SKILL.md' else p.parent.name for p in paths(engine,key)]}
            for key,(label,_) in METHODS.items()]

@lru_cache(maxsize=48)
def _body(path,mtime_ns,size):
    data=Path(path).read_bytes()
    return data.decode('utf-8-sig'),digest(data)

def load(engine,keys):
    if len(keys)>4 or len(set(keys))!=len(keys):raise ConsoleError('一次最多选择四种专业方法',422)
    blocks=[];proof=[]
    for key in keys:
        for p in paths(engine,key):
            if not p.is_file():raise ConsoleError('专业方法资源未安装：'+METHODS[key][0],409)
            if p.stat().st_size>35000:raise ConsoleError('专业方法过大，请缩小范围',413)
            stat=p.stat();body,sha=_body(str(p),stat.st_mtime_ns,stat.st_size);blocks.append('METHOD '+key+' / '+p.parent.name+'\n'+body)
            proof.append({'id':key,'name':METHODS[key][0],'source':str(p),'sha256':sha,'delivered_characters':len(body)})
    if sum(map(len,blocks))>50000:raise ConsoleError('专业方法总量过大，请减少选择',413)
    return '\n\n'.join(blocks),proof
