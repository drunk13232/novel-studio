"""Native .research/<topic>/FINDINGS.md store, scoped to one novel."""
import hashlib
import re
import threading
import uuid
from datetime import date
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
import yaml
from pydantic import BaseModel, ConfigDict, Field
from app.atomic import replace
from app.errors import ConsoleError
from app.workspace.service import sha

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ResearchWrite(Strict):
    content: str = Field(max_length=200000)
    etag: str = Field(min_length=64, max_length=64)

class ResearchAction(Strict):
    etag: str = Field(min_length=64, max_length=64)
    confirm: bool = False

class ResearchOutput(Strict):
    markdown: str
    summary: str

class SpecialistRequest(Strict):
    type: str
    chapter: int | None = Field(default=None, ge=1, le=99999)
    chapter_id: str | None = None
    character_id: str | None = None
    topic_id: str | None = None
    topic: str = Field(default='', max_length=300)
    instruction: str = Field(default='', max_length=12000)
    prompt: str | None = Field(default=None, max_length=12000)
    depth: Literal['quick', 'deep'] = 'quick'
    category: Literal['reality', 'source_canon'] = 'reality'
    research_ids: list[str] = Field(default_factory=list, max_length=5)
    names: list[str] = Field(default_factory=list, max_length=12)
    options: dict = Field(default_factory=dict)

class ResearchLibrary:
    def __init__(self, registry):
        self.registry = registry
        self.lock = threading.RLock()

    def path(self, project, topic=None):
        root = self.registry.workspace(project).root
        path = root / '.research'
        if topic:
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', topic): raise ConsoleError('无效研究主题 ID', 422)
            path = path / topic / 'FINDINGS.md'
        for part in [path, *path.parents]:
            if part == root: break
            if part.is_symlink() or part.is_junction(): raise ConsoleError('Research 链接被拒绝', 403)
        if not path.resolve().is_relative_to(root): raise ConsoleError('Research 路径越界', 403)
        return path

    @staticmethod
    def parse(content):
        match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)', content, re.S)
        if not match: raise ConsoleError('Research Markdown 需要 YAML frontmatter', 422)
        try: meta = yaml.safe_load(match[1])
        except yaml.YAMLError as error: raise ConsoleError('Research frontmatter 无效', 422) from error
        if not isinstance(meta, dict): raise ConsoleError('Research frontmatter 必须为对象', 422)
        if not isinstance(meta.get('topic'),str) or not isinstance(meta.get('title',meta.get('topic')),str):
            raise ConsoleError('Research topic / title 必须为文字',422)
        if meta.get('status') not in ['active', 'superseded']: raise ConsoleError('status 应为 active / superseded', 422)
        if meta.get('depth') not in ['quick', 'deep']: raise ConsoleError('depth 应为 quick / deep', 422)
        if meta.get('category', 'reality') not in ['reality', 'source_canon']: raise ConsoleError('无效研究分类', 422)
        for key in ['created', 'last_verified']:
            try: date.fromisoformat(str(meta[key]))
            except (ValueError, KeyError): raise ConsoleError('Research 日期无效：' + key, 422)
        sources = meta.get('sources') or []
        if not isinstance(sources, list): raise ConsoleError('sources 必须为列表', 422)
        for source in sources:
            if not isinstance(source, dict): raise ConsoleError('来源需包含 url / fetched', 422)
            url = urlsplit(str(source.get('url', '')))
            if url.scheme not in ['https', 'http'] or not url.hostname or url.username or url.password:
                raise ConsoleError('Research 来源 URL 无效', 422)
            try: date.fromisoformat(str(source['fetched']))
            except (ValueError, KeyError): raise ConsoleError('来源需要 fetched 日期', 422)
        for heading in ['Summary', 'Findings', 'Strongest objection', 'Open questions', 'Timeline']:
            if not re.search(r'^## '+re.escape(heading)+r'\s*$', match[2], re.M):
                raise ConsoleError('Research 缺少章节：' + heading, 422)
        return meta, match[2]

    def get(self, project, topic):
        path = self.path(project, topic)
        if not path.is_file(): raise ConsoleError('研究主题不存在', 404)
        if path.stat().st_size > 200000: raise ConsoleError('研究主题超过编辑上限', 413)
        data = path.read_bytes(); content = data.decode('utf-8-sig')
        meta, body = self.parse(content)
        if meta.get('topic') != topic: raise ConsoleError('Research topic 与目录不匹配', 422)
        summary = re.search(r'^## Summary\s*\n(.*?)(?=^## |\Z)', body, re.M | re.S)
        return {'id': topic, 'title': meta.get('title', topic), 'category': meta.get('category', 'reality'),
                'status': meta['status'], 'depth': meta['depth'], 'updated_at': str(meta['last_verified']),
                'summary': summary[1].strip() if summary else '', 'sources': meta.get('sources') or [],
                'content': content, 'etag': sha(data), 'path': f'.research/{topic}/FINDINGS.md',
                'modified_at': path.stat().st_mtime}

    def list(self, project, query='', archived=False):
        root = self.path(project); rows, errors = [], []
        if root.is_dir():
            for folder in root.iterdir():
                if folder.is_dir() and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,79}', folder.name):
                    try: row = self.get(project, folder.name)
                    except ConsoleError as error: errors.append({'id': folder.name, 'error': str(error)}); continue
                    if not archived and row['status'] != 'active': continue
                    if query.lower() not in (row['title']+' '+row['summary']+' '+row['id']).lower(): continue
                    rows.append({k:v for k,v in row.items() if k not in ['content']})
        return {'topics': sorted(rows, key=lambda row: row['modified_at'], reverse=True), 'errors': errors,
                'index': self.index_text(rows), 'reference_only': True}

    @staticmethod
    def index_text(rows):
        clean = lambda text: str(text).replace('|', '/').replace('\n', ' ').replace('\r', ' ')
        return '# Research index\n\nREFERENCE MATERIAL — Research ≠ Canon\n\n| Topic | Path | Last verified | One-liner |\n|---|---|---|---|\n' + ''.join(
            f'| {clean(r["title"])} | {r["id"]}/FINDINGS.md | {r["updated_at"]} | {clean(r["summary"][:200])} |\n' for r in rows if r['status']=='active')

    @staticmethod
    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name+'.pending-'+uuid.uuid4().hex)
        temp.write_text(content, encoding='utf-8'); replace(temp, path)

    def save(self, project, topic, content, etag=None):
        with self.registry.lock, self.lock:
            if self.registry.get(project)['status']['phase']=='ARCHIVED': raise ConsoleError('归档小说只读', 409)
            path = self.path(project, topic); meta, _ = self.parse(content)
            index = self.path(project) / 'INDEX.md'
            if index.is_symlink() or index.is_junction(): raise ConsoleError('Research Index 链接被拒绝', 403)
            if meta.get('topic') != topic: raise ConsoleError('研究主题 ID 不可修改', 422)
            current = sha(path.read_bytes()) if path.is_file() else None
            if current != etag: raise ConsoleError('研究资料已被修改，请重新加载', 409)
            if path.is_file():
                # Preserve history outside Canon and preserve prior evidence on refresh.
                archive = path.parent / 'history' / (uuid.uuid4().hex+'.md')
                for part in [archive.parent, archive]:
                    if part.is_symlink() or part.is_junction(): raise ConsoleError('Research 历史链接被拒绝', 403)
                self.write(archive, path.read_text(encoding='utf-8-sig'))
            self.write(path, content)
            self.write(index, self.list(project)['index'])
            return self.get(project, topic)

    def archive(self, project, topic, body):
        if not body.confirm: raise ConsoleError('请确认归档研究主题', 422)
        value = self.get(project, topic); meta, text = self.parse(value['content'])
        meta['status'] = 'superseded'
        content = '---\n'+yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)+'---\n'+text
        return self.save(project, topic, content, body.etag)

    def reference(self, project, ids, budget=10000):
        parts=[]
        for topic in ids:
            row=self.get(project, topic)
            if row['status']!='active': raise ConsoleError('归档研究不可自动引用',409)
            parts.append(f'REFERENCE MATERIAL — Research ≠ Canon\n{row["path"]}\n{row["content"][:budget]}')
            budget -= min(len(row['content']), budget)
            if budget<=0: break
        return '\n\n'.join(parts)
