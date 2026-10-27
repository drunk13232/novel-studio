"""Explicit project instruction delivery with byte provenance and role isolation."""
import hashlib
import json
from pathlib import Path


def digest(text):
    return hashlib.sha256(text.encode('utf8')).hexdigest()


def bundle(workspace, engine, role='AUTHOR', capsule=False):
    sources = []
    paths = [engine/'AGENTS.md']
    if workspace != engine:
        paths.append(workspace/'AGENTS.md')
    # Writer workspaces contain only a generated, generic AGENTS and curated skill.
    if role == 'WRITER' or capsule:
        paths = [workspace/'AGENTS.md']
    blocks = []
    for path in paths:
        if not path.is_file():
            if path == engine/'AGENTS.md' or role == 'WRITER' or capsule:
                raise ValueError('缺少执行指令：'+str(path))
            continue
        content = path.read_text(encoding='utf-8-sig')
        sources.append({'path':str(path), 'sha256':digest(content), 'kind':'AGENTS'})
        blocks.append(f'# AGENTS.md instructions for {path.parent}\n{content}')
    skill_root = workspace/'.agents/skills' if role == 'WRITER' or capsule else engine/'.agents/skills'
    for path in sorted(skill_root.glob('*/SKILL.md')):
        content = path.read_text(encoding='utf-8-sig')
        sources.append({'path':str(path), 'sha256':digest(content), 'kind':'SKILL'})
    text = '\n\n'.join(blocks)
    return text, {'version':'0.6','workspace':str(workspace),'role':role,'instruction_scope':'capsule' if capsule else 'project',
                  'instructions_sha256':digest(text),'sources':sources}


def verify_thread_owner(record, workspace, role, thread_id):
    if record != {'workspace':str(workspace.resolve()),'role':role,'thread_id':thread_id}:
        raise ValueError('线程身份与当前项目/角色不匹配；拒绝恢复旧线程')
