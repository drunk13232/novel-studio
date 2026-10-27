import hashlib
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
import yaml
from app.errors import WorkspaceError

ROOTS = {'state', 'settings', 'outlines', 'chapters', 'docs', 'bible', 'characters', 'metadata'}
EXTENSIONS = {'.md', '.yaml', '.yml', '.json', '.txt'}
SKIP_DIRS = {'vendor', 'runtime', 'node_modules', '__pycache__', '.venv', 'dist'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def modified(stat: os.stat_result) -> str:
    return datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()


class WorkspaceService:
    def __init__(self, root: Path, max_bytes: int = 2 * 1024 * 1024) -> None:
        self.root = root.resolve()
        self.max_bytes = max_bytes
        # Local acceptance holds this lock across revision checks and save().
        self._save_lock = threading.RLock()

    def resolve(self, relative: str, *, allow_reviews: bool = False) -> Path:
        if (not relative or '\\' in relative or ':' in relative or '\x00' in relative
                or relative.startswith('/') or any(p in ['', '.', '..'] for p in relative.split('/'))):
            raise WorkspaceError('路径必须是工作区内的安全相对路径', 403)
        parts = PurePosixPath(relative).parts
        if parts[0] not in ROOTS | ({'reviews'} if allow_reviews else set()):
            raise WorkspaceError('文件不在网页允许范围', 403)
        if any(p.startswith('.') or p in SKIP_DIRS for p in parts):
            raise WorkspaceError('不允许访问隐藏目录、源码依赖或运行日志', 403)
        if Path(parts[-1]).suffix.lower() not in EXTENSIONS:
            raise WorkspaceError('不支持此文件类型', 403)
        candidate = self.root.joinpath(*parts)
        for ancestor in [candidate, *candidate.parents]:
            if ancestor == self.root:
                break
            if ancestor.is_symlink() or ancestor.is_junction():
                raise WorkspaceError('不允许通过 symlink/junction 访问文件', 403)
        if not candidate.resolve().is_relative_to(self.root):
            raise WorkspaceError('文件路径越出工作区', 403)
        return candidate

    def list_files(self, *, include_reviews: bool = False) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        for name in sorted(ROOTS | ({'reviews'} if include_reviews else set())):
            folder = self.root / name
            if not folder.is_dir() or folder.is_symlink() or folder.is_junction():
                continue
            for directory, dirs, filenames in os.walk(folder, followlinks=False):
                dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d not in SKIP_DIRS
                                  and not (Path(directory) / d).is_symlink() and not (Path(directory) / d).is_junction())
                for filename in filenames:
                    relative = (Path(directory) / filename).relative_to(self.root).as_posix()
                    try:
                        path = self.resolve(relative, allow_reviews=include_reviews)
                        if path.is_file():
                            stat = path.stat()
                            files.append({'path': relative, 'name': filename, 'size': stat.st_size,
                                          'modified_at': modified(stat), 'editable': name != 'reviews'})
                    except (WorkspaceError, OSError):
                        continue
        return sorted(files, key=lambda row: row['path'])

    def content(self, relative: str, *, allow_reviews: bool = False) -> dict[str, Any]:
        path = self.resolve(relative, allow_reviews=allow_reviews)
        if not path.is_file():
            raise WorkspaceError('文件尚未生成', 404)
        if path.stat().st_size > self.max_bytes:
            raise WorkspaceError('文件超过 2 MiB 编辑上限', 413)
        data = path.read_bytes()
        if len(data) > self.max_bytes:
            raise WorkspaceError('文件超过编辑上限', 413)
        try:
            content = data.decode('utf-8-sig')
        except UnicodeDecodeError as error:
            raise WorkspaceError('编辑器只支持 UTF-8 文件，不会擅自转换编码', 422) from error
        newlines = re.findall(r'\r\n|\r|\n', content)
        line_ending = 'CRLF' if newlines and all(n == '\r\n' for n in newlines) else 'LF'
        if any(n == '\r' for n in newlines) or len(set(newlines)) > 1:
            line_ending = 'MIXED'
        return {'path': relative, 'content': content, 'etag': sha(data), 'size': len(data),
                'modified_at': modified(path.stat()), 'bom': data.startswith(b'\xef\xbb\xbf'),
                'line_ending': line_ending, 'editable': relative.split('/')[0] != 'reviews'}

    def save(self, relative: str, content: str, etag: str) -> dict[str, Any]:
        path = self.resolve(relative)
        if path.suffix.lower() == '.json':
            try:
                json.loads(content)
            except (ValueError, RecursionError) as error:
                raise WorkspaceError('JSON 语法错误：' + str(error), 422) from error
        if path.suffix.lower() in ['.yaml', '.yml']:
            self.parse_yaml(content)
        with self._save_lock:
            original = self.content(relative)
            if original['etag'] != etag:
                raise WorkspaceError('文件已被其他程序修改，请 Reload 后合并自己的修改', 409)
            data = content.encode('utf-8-sig' if original['bom'] else 'utf-8')
            if len(data) > self.max_bytes:
                raise WorkspaceError('文件超过编辑上限', 413)
            if original['line_ending'] == 'MIXED' and content != original['content']:
                raise WorkspaceError('混合换行文件请先在外部编辑器处理；网页不会自动统一格式', 422)
            self.resolve(relative)
            temporary = path.with_name(path.name + '.web-save-' + uuid.uuid4().hex)
            try:
                with temporary.open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                if sha(path.read_bytes()) != etag:
                    raise WorkspaceError('保存期间文件发生外部修改，请重新加载', 409)
                self.resolve(relative)
                from app.atomic import replace
                replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
            from app.writing_metrics import notify_saved
            notify_saved(self.root,relative,original['content'],content)
        return self.content(relative)

    @staticmethod
    def parse_yaml(content: str) -> Any:
        try:
            for token in yaml.scan(content):
                if isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)):
                    raise WorkspaceError('网页状态解析不接受 YAML anchor/alias', 422)
            return yaml.safe_load(content)
        except (yaml.YAMLError, RecursionError) as error:
            raise WorkspaceError('YAML 语法错误：' + str(error), 422) from error

    def yaml_file(self, relative: str) -> dict[str, Any]:
        try:
            value = self.parse_yaml(self.content(relative)['content'])
        except WorkspaceError as error:
            if error.status == 404:
                return {}
            raise
        if not isinstance(value, dict):
            raise WorkspaceError(relative + ' 必须是 YAML 映射', 422)
        return value

    def status(self, file_rows=None) -> dict[str, Any]:
        file_rows = self.list_files() if file_rows is None else file_rows
        current = self.yaml_file('state/current-story-state.yaml')
        project = current.get('project') or {}
        pov = current.get('pov') or {}
        threads = (self.yaml_file('state/plot-threads.yaml').get('threads') or {})
        foreshadow = (self.yaml_file('state/foreshadowing.yaml').get('foreshadowing') or {})
        ledger = self.yaml_file('state/chapter-ledger.yaml')
        if not all(isinstance(v, dict) for v in [project, pov, threads, foreshadow, current.get('location') or {}]):
            raise WorkspaceError('状态字段必须是 YAML 映射', 422)
        if not isinstance(ledger.get('entries', []), list) or any(not isinstance(e, dict) for e in ledger.get('entries', [])):
            raise WorkspaceError('chapter-ledger entries 必须是对象列表', 422)
        if any(not isinstance(row, dict) for row in [*threads.values(), *foreshadow.values()]):
            raise WorkspaceError('剧情线/伏笔记录必须是 YAML 映射', 422)
        committed = {e.get('proposal_id') for e in ledger.get('entries', [])}
        pending = [f['path'] for f in file_rows if f['path'].startswith('state/proposed/')
                   and f['path'].endswith('.yaml') and not f['path'].endswith(('.review.yaml', '.validation.yaml'))
                   and Path(f['path']).stem not in committed]
        return {'title': project.get('title'), 'genre': project.get('genre'), 'volume': project.get('current_volume'),
                'chapter': project.get('current_chapter'), 'pov': pov.get('current_character'),
                'location': (current.get('location') or {}).get('current'), 'story_time': project.get('story_date'),
                'open_foreshadowing': sum(1 for row in foreshadow.values() if row.get('status') not in ['RESOLVED', 'ABANDONED']),
                'active_threads': sum(1 for row in threads.values() if row.get('status') in ['OPEN', 'ACTIVE']),
                'pending_diffs': pending, 'warnings': current.get('warnings') or [],
                'last_commit': ledger.get('last_commit'),
                'recent_files': sorted(file_rows, key=lambda f: f['modified_at'], reverse=True)[:8],
                'recent_chapters': self.chapters()[-5:][::-1]}

    def chapters(self, file_rows=None) -> list[dict[str, Any]]:
        chapters: dict[int, dict[str, Any]] = {}
        for item in self.list_files(include_reviews=True) if file_rows is None else file_rows:
            path = item['path']
            match = re.match(r'chapters/(?:chapter[-_])?(\d+)(?:[._/-]|$)', path)
            number = int(match[1]) if match else None
            if number is None:
                match = re.match(r'(?:outlines|reviews|state/proposed)/(?:chapter[-_])?(\d+)(?:[._/-]|$)', path)
                number = int(match[1]) if match else None
            if number is None or number == 0:
                continue
            row = chapters.setdefault(number, {'id': str(number), 'number': number, 'title': None, 'files': [],
                                               'plan': None, 'draft': None, 'final': None, 'review': None, 'state_diff': None})
            row['files'].append(item)
            basename = Path(path).stem.lower()
            if path.startswith('state/proposed/') and not path.endswith(('.validation.yaml', '.review.yaml')):
                row['state_diff'] = path
            elif path.startswith('reviews/') or 'review' in basename:
                row['review'] = row['review'] or path
            elif 'plan' in basename or path.startswith('outlines/'):
                row['plan'] = path
            elif basename == 'final' or basename.endswith('-final'):
                row['final'] = path
            elif path.startswith('chapters/'):
                row['draft'] = row['draft'] or path
                if re.fullmatch(r'(?:chapter[-_])?\d+', basename):
                    row['final'] = path
            if path.endswith('.md') and path.startswith('chapters/') and row['title'] is None:
                try:
                    heading = re.search(r'^#\s+(.+)', self.content(path)['content'], re.MULTILINE)
                    row['title'] = heading[1] if heading else None
                except WorkspaceError:
                    pass
        return [chapters[n] for n in sorted(chapters)]

    def chapter(self, number: int) -> dict[str, Any]:
        return next((row for row in self.chapters() if row['number'] == number),
                    {'id': str(number), 'number': number, 'title': None, 'files': [], 'plan': None,
                     'draft': None, 'final': None, 'review': None, 'state_diff': None})

    def snapshot(self) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for row in self.list_files(include_reviews=True):
            try:
                snapshot[row['path']] = sha(self.resolve(row['path'], allow_reviews=True).read_bytes())
            except OSError:
                continue
        return snapshot

    def changes(self, before: dict[str, str]) -> list[dict[str, str]]:
        after = self.snapshot()
        return [{'path': path, 'change': 'ADDED' if path not in before else 'DELETED' if path not in after else 'MODIFIED'}
                for path in sorted(before.keys() | after.keys()) if before.get(path) != after.get(path)]
