"""Local, opt-in plugin contributions over existing Actions and WASI Control."""
import ast,hashlib,io,json,re,stat,threading,time,uuid,zipfile
from pathlib import Path,PurePosixPath
from app.errors import ConsoleError
from app.library.storage import now,read
from app.tasks.storage import atomic_json
from app.assistant.actions import TOOLS
from app.ai.credentials import scrub
from .models import Manifest
MAX_ZIP=1024*1024
MAX_TOTAL=2*1024*1024
MAX_FILE=256*1024

def digest(data):return hashlib.sha256(data).hexdigest()
def safe_name(name):
    p=PurePosixPath(name)
    if len(name)>160 or len(p.parts)>4 or str(p)!=name or not name or '\\' in name or ':' in name or p.is_absolute() or any(not re.fullmatch(r'[A-Za-z0-9_.-]+',part) or part in {'.','..'} or part.startswith('.') or part.rstrip(' .')!=part or part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))} for part in p.parts):raise ConsoleError('插件包含不安全的文件路径',422)
    if p.suffix.lower() not in {'.json','.py','.md','.txt','.yaml','.yml'}:raise ConsoleError('插件文件类型尚未支持；不自动加载可执行程序或网页脚本',422)
    return name

class PluginHub:
    def __init__(self,app,root):
        self.app=app;self.root=Path(root)/'plugins';self.lock=threading.RLock();self.staged={}
        self.path=self.root/'registry.json';self.rows={};self.blocked=''
        try:
            if self.root.is_symlink() or self.path.is_symlink():raise ValueError('Linked plugin directory')
            if self.path.exists():
                if self.path.stat().st_size>2*1024*1024:raise ValueError('Registry too large')
                self.rows=json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(self.rows,dict) or len(self.rows)>300:raise ValueError('Invalid registry')
                for row in self.rows.values():Manifest.model_validate(row['manifest'])
        except (OSError,ValueError,KeyError,TypeError):
            self.rows={};self.blocked='插件配置损坏或目录被替换。插件已隔离，普通写作仍可使用；请保留原文件并联系维护者。'
    def guard(self):
        if self.blocked:raise ConsoleError(self.blocked,409)
    def save(self):
        self.guard();atomic_json(self.path,self.rows)
    def folder(self,id,revision):
        self.guard()
        if not re.fullmatch(r'[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*',id) or not re.fullmatch(r'[a-f0-9]{64}',revision):raise ConsoleError('插件标识无效',422)
        p=self.root/'packages'/id/revision
        if any(x.is_symlink() for x in (self.root,self.root/'packages',p.parent,p)):raise ConsoleError('插件目录被替换，已拒绝读取',409)
        return p
    @staticmethod
    def validate(manifest,contents):
        m=Manifest.model_validate(manifest)
        for content in contents.values():
            if re.search(rb'sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',content):raise ConsoleError('插件包含疑似密钥，请移除并使用原有安全凭据配置',422)
        from app.version import release_info
        if tuple(map(int,m.min_app_version.split('.')))>tuple(map(int,release_info()['version'].split('.'))):raise ConsoleError('插件需要更新版本的 Novel Studio',409)
        if set(contents)!={'manifest.json',*m.files}:raise ConsoleError('插件包文件与 manifest 文件清单不一致',422)
        for name,sha in m.files.items():
            safe_name(name)
            if not re.fullmatch(r'[a-f0-9]{64}',sha) or digest(contents[name])!=sha:raise ConsoleError('插件文件校验失败',422)
        if any(name not in TOOLS or name in {'run_python_plan','open_project'} for name in m.actions):raise ConsoleError('插件请求了未知、递归执行或跨作品操作',422)
        for command in m.commands:
            if command.kind=='action' and command.action not in m.actions:raise ConsoleError('命令动作没有在权限清单中声明',422)
            if command.kind=='python':
                if command.script not in m.files or not command.script.endswith('.py'):raise ConsoleError('缺少声明的 Python 脚本',422)
                if len(contents[command.script])>64000:raise ConsoleError('Python 脚本超过 64000 字节',422)
                try:ast.parse(contents[command.script].decode('utf-8-sig'))
                except (SyntaxError,ValueError):raise ConsoleError('插件 Python 语法无效',422)
        for resource in m.resources:
            if resource.file not in m.files or resource.file.endswith('.py'):raise ConsoleError('资源文件未声明或类型不支持',422)
            if resource.kind=='experiment':
                from app.world_logic.models import validate
                validate(json.loads(contents[resource.file]))
        return m
    def parse(self,raw):
        if len(raw)>MAX_ZIP:raise ConsoleError('插件压缩包最多 1 MiB',413)
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                entries=z.infolist()
                if len(entries)>64 or sum(i.file_size for i in entries)>MAX_TOTAL:raise ConsoleError('插件文件数量或解压大小超过限制',413)
                data={};case=set()
                for item in entries:
                    if item.is_dir():continue
                    name=safe_name(item.filename)
                    if name.casefold() in case or item.flag_bits&1 or stat.S_ISLNK(item.external_attr>>16) or item.file_size>MAX_FILE or item.file_size>max(item.compress_size,1)*100:raise ConsoleError('插件含重复文件、链接、加密文件或异常压缩内容',422)
                    case.add(name.casefold());content=z.read(item)
                    if len(content)>MAX_FILE:raise ConsoleError('插件文件过大',413)
                    content.decode('utf-8-sig');data[name]=content
            if 'manifest.json' not in data:raise ConsoleError('压缩包根目录缺少 manifest.json',422)
            m=self.validate(json.loads(data['manifest.json']),data)
            return m,data,digest(raw)
        except ConsoleError:raise
        except (ValueError,UnicodeError,zipfile.BadZipFile,KeyError,RuntimeError,OSError):raise ConsoleError('无法解析插件包，请检查 UTF-8、清单与校验值',422)
    def public(self,row):
        m=row['manifest'];return {**row,'permissions':[{'action':n,'description':TOOLS[n].description,'level':TOOLS[n].level} for n in m['actions'] if n in TOOLS],'runtime':'CPython WASI / controlled Actions','trusted':False}
    def list(self):
        with self.lock:return [self.public(dict(v)) for v in self.rows.values() if v.get('installed')]
    def preview(self,raw):
        self.guard()
        m,files,revision=self.parse(raw)
        with self.lock:
            self.staged={k:v for k,v in self.staged.items() if v['expires']>time.monotonic()}
            if len(self.staged)>=8:raise ConsoleError('待安装预览过多，请稍后重试',429)
            token=uuid.uuid4().hex;previous=self.rows.get(m.id)
            row={'manifest':m.model_dump(),'revision':revision,'enabled':False,'installed':True,'config':{v.id:v.default for v in m.settings}}
            self.staged[token]={'row':row,'files':files,'expires':time.monotonic()+600,'previous':previous.get('revision') if previous and previous.get('installed') else None}
            return {**self.public(row),'token':token,'previous_revision':self.staged[token]['previous'],'update':bool(self.staged[token]['previous']),'notice':'安装不执行代码；安装或更新后默认禁用。启用和运行均由作者主动触发。'}
    def install(self,b):
        self.guard()
        with self.lock:
            staged=self.staged.get(b.token)
            if not staged or staged['expires']<time.monotonic():raise ConsoleError('安装预览已过期，请重新选择文件',409)
            row=staged['row'];id=row['manifest']['id'];old=self.rows.get(id)
            if old is None and len(self.rows)>=100:raise ConsoleError('本机插件记录已达 100 个，请先整理',429)
            current=old['revision'] if old and old.get('installed') else None
            if current!=staged['previous'] or b.expected_revision!=current:raise ConsoleError('已安装插件已变化，请重新预览更新',409)
            folder=self.folder(id,row['revision']);folder.mkdir(parents=True,exist_ok=True)
            for name,content in staged['files'].items():
                dest=folder/name
                if any(x.is_symlink() for x in [dest,*dest.parents] if x.is_relative_to(folder)):raise ConsoleError('插件目标文件是链接',409)
                dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(content)
            row.update(installed_at=now());self.rows[id]=row;self.save();self.staged.pop(b.token,None)
            result=self.public(row)
        self.cancel(id)
        return result
    def get(self,id,revision=None,enabled=False):
        self.guard()
        row=self.rows.get(id)
        if not row or not row.get('installed'):raise ConsoleError('插件未安装',404)
        if revision is not None and row['revision']!=revision:raise ConsoleError('插件已更新，请刷新后再操作',409)
        if enabled and not row['enabled']:raise ConsoleError('插件已禁用',409)
        return row
    def cancel(self,id):
        for s in tuple(self.app.state.assistant.sessions.values()):
            if getattr(s,'plugin_source',{}).get('id')==id and not s.cancelled:
                s.stop()
                task=s.execution_task or s.task
                if task and task.status not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'} and self.app.state.automation.loop:
                    import asyncio
                    asyncio.run_coroutine_threadsafe(s.manager.cancel(task.id),self.app.state.automation.loop)
    def toggle(self,id,b):
        with self.lock:
            row=self.get(id,b.revision)
            if b.enabled:self.contents(row) # Do not enable damaged installations.
            row['enabled']=b.enabled;self.save();result=self.public(row)
        if not b.enabled:self.cancel(id)
        return result
    def configure(self,id,b):
        with self.lock:
            row=self.get(id,b.revision);m=Manifest.model_validate(row['manifest']);options={v.id:v for v in m.settings}
            if set(b.values)!=set(options):raise ConsoleError('配置字段与插件声明不一致',422)
            try:
                for key,value in b.values.items():
                    options[key].check(value)
                    if isinstance(value,str) and scrub(value)!=value:raise ValueError('Credentials are not plugin settings')
            except ValueError:raise ConsoleError('插件配置无效；请检查范围，不要填写密钥或令牌',422)
            row['config']=b.values;self.save();result=self.public(row)
        self.cancel(id)
        return result
    def uninstall(self,id,revision):
        with self.lock:
            row=self.get(id,revision);row.update(installed=False,enabled=False);self.save()
        self.cancel(id)
        return {'uninstalled':True,'recoverable':True,'notice':'已停用并移出插件列表，原包保留在本机，重新导入可恢复。'}
    def contents(self,row):
        folder=self.folder(row['manifest']['id'],row['revision']);data={}
        for name in ['manifest.json',*row['manifest']['files']]:
            safe_name(name);p=folder/name
            if any(x.is_symlink() for x in [p,*p.parents] if x.is_relative_to(folder)) or not p.is_file() or p.stat().st_size>MAX_FILE:raise ConsoleError('插件文件缺失或被替换',409)
            data[name]=p.read_bytes()
        self.validate(row['manifest'],data)
        # The stored declaration is also integrity bound to the installed manifest.
        if Manifest.model_validate(json.loads(data['manifest.json'])).model_dump()!=row['manifest']:raise ConsoleError('插件清单已变化，请重新导入',409)
        return data
    def check_session(self,s):
        with self.lock:
            row=self.get(s.plugin_source['id'],s.plugin_source['revision'],enabled=True)
            if digest(json.dumps(row['config'],sort_keys=True).encode())!=s.plugin_source['config_revision']:raise ConsoleError('插件配置已变化，请重新运行',409)
    def prepare(self,id,command,revision):
        with self.lock:
            row=self.get(id,revision,True);files=self.contents(row);m=Manifest.model_validate(row['manifest'])
            c=next((v for v in m.commands if v.id==command),None)
            if not c:raise ConsoleError('插件命令不存在',404)
            if c.kind=='entry':return {'kind':'entry','target':c.target.model_dump(),'title':c.title}
            if c.kind=='action':
                def expand(value):
                    if isinstance(value,str) and re.fullmatch(r'\$\{[a-z][a-z0-9_]*\}',value):
                        key=value[2:-1]
                        if key not in row['config']:raise ConsoleError('缺少命令配置：'+key,422)
                        return row['config'][key]
                    if isinstance(value,dict):return {k:expand(v) for k,v in value.items()}
                    if isinstance(value,list):return [expand(v) for v in value]
                    return value
                args=expand(c.arguments);TOOLS[c.action].schema.model_validate(args)
                code='from novel_studio_api import Studio\nimport json\nprint(Studio.connect().call('+repr(c.action)+', **json.loads('+repr(json.dumps(args,ensure_ascii=False))+')))\n'
            else:code='import json\nPLUGIN_CONFIG=json.loads('+repr(json.dumps(row['config'],ensure_ascii=False))+')\n'+files[c.script].decode('utf-8-sig')
            return {'kind':c.kind,'code':code,'title':m.name+' · '+c.title,'actions':m.actions,'source':{'id':id,'revision':row['revision'],'command':c.id,'config_revision':digest(json.dumps(row['config'],sort_keys=True).encode())}}
    def export(self,id):
        with self.lock:
            row=self.get(id);data=self.contents(row);out=io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                for name,content in data.items():z.writestr(name,content)
            return out.getvalue() # No user config, history, grants or private project data.
