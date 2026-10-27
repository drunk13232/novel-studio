import hashlib
import json
import os
from pathlib import Path
from app.errors import ConsoleError

PRIORITY = '用户明确要求 > HARD Canon > State / Knowledge > Character Canon > Plot Intent > POV > Scene Quality > Style > AI 味'
STORY_COMMANDS = {'continuity', 'knowledge', 'context', 'timeline', 'voices', 'links', 'doctor', 'names'}

def installations(engine):
    home = Path(os.environ['USERPROFILE']) / '.codex'
    return {
        'story': home / 'plugins/cache/novel-writing-stack/story-skills/0.22.1',
        'research': home / 'plugins/cache/research-skill/research-codex/0.4.2/skills/research',
        'novel': home / 'skills/novel-writing',
    }

def resources(engine, provider, references=()):
    root = installations(engine)[provider]
    if provider == 'story': root = root / 'skills/story-maintenance'
    paths = [root / 'SKILL.md', *(root / 'references' / name for name in references)]
    contents, proof = [], []
    for path in paths:
        if not path.is_file(): raise ConsoleError('未安装的写作入口：' + str(path), 409)
        data = path.read_bytes()
        contents.append(f'实际 Skill 源文 {path}:\n{data.decode("utf-8-sig")}')
        proof.append({'path': str(path), 'sha256': hashlib.sha256(data).hexdigest()})
    return '\n\n'.join(contents), proof

def catalog(engine):
    paths = installations(engine)
    return {'priority': PRIORITY, 'providers': [
        {'name': 'Story Skills', 'version': '0.22.1', 'entry': 'story-skills:story-maintenance',
         'installed': (paths['story'] / 'skills/story-maintenance/SKILL.md').is_file(),
         'path': str(paths['story']), 'commands': sorted(STORY_COMMANDS), 'role': 'Deterministic Story Validator'},
        {'name': 'Research Skill', 'version': '0.4.2', 'entry': 'research-codex:research',
         'installed': (paths['research'] / 'SKILL.md').is_file(), 'path': str(paths['research']), 'role': 'Project Research Library'},
        {'name': 'novel-writing', 'version': 'commit 838729695148008d42c01bd7c3c0c1a5c15de830', 'entry': 'novel-writing',
         'installed': (paths['novel'] / 'SKILL.md').is_file(), 'path': str(paths['novel']), 'role': 'POV / Dialogue / Voice Reviewer'},
    ]}
