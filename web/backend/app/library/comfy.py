"""ComfyUI's public API. No inference, remote key store or global interrupt."""
import copy
import json
import re
import threading
import time
from abc import ABC,abstractmethod
from urllib.parse import urlsplit,urlencode
import httpx
import websocket
from app.errors import ConsoleError
from .storage import safe,read,write,uid,now,write_guard,digest
from .assets import MAX_BYTES

PARAMETERS={'positive','negative','seed','width','height','steps','cfg','model','reference'}
TASK_TYPES=['人物头像','人物半身','人物全身','人物设定图','角色表情','服装变体','年龄变化','地点插画','建筑概念图','道具设定图','生物设定图','章节插画','小说封面','自由生图']
TERMINAL={'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}

class ImageProvider(ABC):
    @abstractmethod
    def status(self):...
    @abstractmethod
    def submit(self,graph,client_id):...
    @abstractmethod
    def history(self,prompt_id):...
    @abstractmethod
    def output(self,file):...

def validate_url(url,confirmed=False):
    parsed=urlsplit(url)
    if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConsoleError('ComfyUI 地址须为不含凭证和查询参数的 HTTP(S) 地址',422)
    if parsed.hostname not in {'localhost','127.0.0.1','::1'} and not confirmed:
        raise ConsoleError('远程服务会接收提示词和参考图，请明确确认此地址',409)
    return url.rstrip('/')

class ComfyUIProvider(ImageProvider):
    def __init__(self,config):
        self.url=validate_url(config.get('url','http://127.0.0.1:8188'),config.get('remote_confirmed',False))
        self.client=httpx.Client(timeout=15,trust_env=False,follow_redirects=False)
    def request(self,method,path,**kwargs):
        r=self.client.request(method,self.url+path,**kwargs)
        if r.status_code>=300:raise ConsoleError('ComfyUI '+str(r.status_code)+': '+r.text[:1600],422)
        return r.json()
    def status(self):
        try:return {'connected':True,'stats':self.request('GET','/system_stats'),'queue':self.request('GET','/queue'),'url':self.url}
        except (httpx.HTTPError,ConsoleError,ValueError) as e:return {'connected':False,'url':self.url,'message':'ComfyUI 未连接','error':str(e)[:500]}
    def object_info(self):return self.request('GET','/object_info')
    def submit(self,graph,client_id):return self.request('POST','/prompt',json={'prompt':graph,'client_id':client_id})
    def history(self,prompt_id):return self.request('GET','/history/'+prompt_id).get(prompt_id)
    def queue(self):return self.request('GET','/queue')
    def cancel_pending(self,prompt_id):
        # Only delete a server queue entry whose ID was returned for our own job.
        if any(len(r)>1 and r[1]==prompt_id for r in self.queue().get('queue_pending',[])):
            self.request('POST','/queue',json={'delete':[prompt_id]});return True
        return False
    def upload(self,path):
        with path.open('rb') as f:
            row=self.request('POST','/upload/image',files={'image':('novel-'+uid('ref')+path.suffix,f,'application/octet-stream')},data={'overwrite':'false','type':'input'})
        return (row.get('subfolder','').strip('/')+'/' if row.get('subfolder') else '')+row['name']
    def output(self,file):
        # Server filename is only a query value, never a local destination.
        with self.client.stream('GET',self.url+'/view',params={k:str(file.get(k,'')) for k in ['filename','subfolder','type']}) as response:
            response.raise_for_status();data=bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data)>MAX_BYTES:raise ConsoleError('ComfyUI 输出超过图片上限',413)
            return bytes(data)
    def socket(self,client_id):
        url=('wss' if self.url.startswith('https:') else 'ws')+self.url[self.url.index(':'):]
        return websocket.create_connection(url+'/ws?'+urlencode({'clientId':client_id}),timeout=1,http_no_proxy=['localhost','127.0.0.1','::1'])
    def close(self):self.client.close()

def workflow(value):
    row=copy.deepcopy(value);graph=row.get('graph');mapping=row.get('mapping',{})
    if not isinstance(graph,dict) or not graph or len(graph)>1000 or 'nodes' in graph:raise ConsoleError('请导入 API 格式 JSON（节点 ID → class_type / inputs），不是画布格式',422)
    for id,node in graph.items():
        if not isinstance(id,str) or not isinstance(node,dict) or not isinstance(node.get('class_type'),str) or not isinstance(node.get('inputs'),dict):raise ConsoleError('无效 API 节点结构',422)
        for v in node['inputs'].values():
            if isinstance(v,list) and (len(v)!=2 or str(v[0]) not in graph or not isinstance(v[1],int) or v[1]<0):raise ConsoleError('节点连线引用无效',422)
    if not isinstance(mapping,dict) or set(mapping)-PARAMETERS:raise ConsoleError('工作流映射参数无效',422)
    for key,m in mapping.items():
        if not isinstance(m,dict) or set(m)!={'node','input'}:raise ConsoleError('映射需指定 node 与 input',422)
        node=graph.get(str(m['node']),{});inputs=node.get('inputs',{})
        if m['input'] not in inputs or isinstance(inputs[m['input']],(list,dict)):raise ConsoleError('映射必须指向节点现有的标量输入：'+key,422)
        actual=inputs[m['input']]
        if key in {'positive','negative','model','reference'} and not isinstance(actual,str):raise ConsoleError('文本映射必须对应文本输入：'+key,422)
        if key in {'seed','width','height','steps','cfg'} and (not isinstance(actual,(int,float)) or isinstance(actual,bool)):raise ConsoleError('数值映射必须对应数值输入：'+key,422)
    outputs=row.get('outputs',[])
    if not outputs or any(str(n) not in graph for n in outputs):raise ConsoleError('请指定工作流内真实输出节点',422)
    return {'id':row.get('id') or uid('workflow'),'name':str(row.get('name','未命名工作流'))[:200],'description':str(row.get('description',''))[:4000],'graph':graph,'mapping':mapping,'outputs':[str(n) for n in outputs],'updated_at':now()}

def compatible(row,objects,reference_pending=False):
    errors=[];models={}
    for id,node in row['graph'].items():
        info=objects.get(node['class_type'])
        if info is None:errors.append(f"缺少节点：{node['class_type']} ({id})");continue
        inputs={**info.get('input',{}).get('required',{}),**info.get('input',{}).get('optional',{})}
        for k,v in node['inputs'].items():
            if k not in inputs:errors.append(f'节点 {id} 不支持输入 {k}');continue
            spec=inputs[k]
            if spec and isinstance(spec[0],list) and not isinstance(v,list):
                models[id+'.'+k]=spec[0]
                reference=row['mapping'].get('reference')
                if v not in spec[0] and not (reference_pending and reference=={'node':id,'input':k}):errors.append(f'节点 {id} 的模型或枚举值不存在：{k} = {v}')
            elif spec and not isinstance(v,list):
                t=spec[0];limits=spec[1] if len(spec)>1 and isinstance(spec[1],dict) else {}
                valid=(isinstance(v,str) if t=='STRING' else isinstance(v,bool) if t=='BOOLEAN' else isinstance(v,int) and not isinstance(v,bool) if t=='INT' else isinstance(v,(int,float)) and not isinstance(v,bool) if t=='FLOAT' else True)
                if not valid:errors.append(f'节点 {id} 输入 {k} 类型应为 {t}')
                if isinstance(v,(int,float)) and (v<limits.get('min',v) or v>limits.get('max',v)):errors.append(f'节点 {id} 输入 {k} 超出节点声明范围')
        for k in info.get('input',{}).get('required',{}):
            if k not in node['inputs']:errors.append(f'节点 {id} 缺少必填输入 {k}')
    for id in row['outputs']:
        if not objects.get(row['graph'][id]['class_type'],{}).get('output_node'):errors.append('指定节点不是输出节点：'+id)
    return {'compatible':not errors,'errors':errors,'choices':models}

class ImageStudio:
    def __init__(self,registry,bible,assets,config_path):
        self.registry=registry;self.bible=bible;self.assets=assets;self.config_path=config_path
        self.stop=threading.Event();self.wake=threading.Event();self.thread=None;self.worker_lease=None
    def config(self):return read(self.config_path,{'url':'http://127.0.0.1:8188','remote_confirmed':False})
    def configure(self,value):
        url=validate_url(value.get('url',''),value.get('confirm_remote') is True)
        row={'url':url,'remote_confirmed':value.get('confirm_remote') is True};write(self.config_path,row);return row
    def provider(self):return ComfyUIProvider(self.config())
    def root(self,p):return self.registry.workspace(p).root
    def rows(self,p,kind):return sorted([read(safe(self.root(p),f'art/{kind}/'+x.name)) for x in safe(self.root(p),'art/'+kind).glob('*.json')],key=lambda x:x.get('created_at',x.get('updated_at','')),reverse=True)
    def get(self,p,kind,id):
        if not re.fullmatch(r'(?:workflow|style|job)_[0-9a-f]{32}',id):raise ConsoleError('无效图像记录 ID',403)
        r=read(safe(self.root(p),f'art/{kind}/{id}.json'))
        if not r:raise ConsoleError('图像记录不存在',404)
        return r
    def put_workflow(self,p,value):
        row=workflow(value)
        if not re.fullmatch(r'workflow_[0-9a-f]{32}',row['id']):raise ConsoleError('无效工作流 ID',422)
        write(safe(self.root(p),'art/workflows/'+row['id']+'.json'),row);return row
    def put_style(self,p,value):
        row={k:value.get(k,v) for k,v in {'id':uid('style'),'name':'新风格','description':'','positive':'','negative':'','workflow_id':'','width':512,'height':512,'references':[],'parameters':{}}.items()}
        if not re.fullmatch(r'style_[0-9a-f]{32}',row['id']):raise ConsoleError('无效风格 ID',422)
        if row['workflow_id']:self.get(p,'workflows',row['workflow_id'])
        for id in row['references']:self.assets.get(p,id)
        if not isinstance(row['parameters'],dict) or set(row['parameters'])-(PARAMETERS-{'reference'}):raise ConsoleError('风格自定义参数无效',422)
        row['updated_at']=now();write(safe(self.root(p),'art/styles/'+row['id']+'.json'),row);return row
    def enqueue(self,p,value):
        if not self.worker_lease:raise ConsoleError('另一 Novel Studio 窗口管理图像队列，请在该窗口生成',409)
        if value.get('confirm') is not True:raise ConsoleError('请确认提示词后提交',409)
        w=self.get(p,'workflows',str(value.get('workflow_id','')));params=copy.deepcopy(value.get('parameters',{}))
        if set(params)-set(w['mapping']):raise ConsoleError('当前 Workflow 不支持这些参数',422)
        graph=copy.deepcopy(w['graph'])
        for k,v in params.items():
            if k=='reference':continue
            m=w['mapping'][k]
            if k in {'seed','width','height','steps'} and (not isinstance(v,int) or isinstance(v,bool) or v<0):raise ConsoleError('整数参数无效：'+k,422)
            if k in {'width','height'} and not 64<=v<=2048:raise ConsoleError('尺寸限 64～2048，6 GB 建议 512',422)
            if k=='steps' and not 1<=v<=150:raise ConsoleError('步数限 1～150',422)
            if k=='cfg' and (not isinstance(v,(int,float)) or not 0<=v<=30):raise ConsoleError('CFG 参数无效',422)
            if k in {'positive','negative','model'} and not isinstance(v,str):raise ConsoleError('文本参数无效',422)
            graph[str(m['node'])]['inputs'][m['input']]=v
        for node in graph.values():
            if isinstance(node['inputs'].get('batch_size'),list):raise ConsoleError('工作流 Batch 由连线控制。请在 ComfyUI 中改为明确的 batch_size=1 再导入',422)
            if isinstance(node['inputs'].get('batch_size'),(int,float)):node['inputs']['batch_size']=1
        ref=params.get('reference')
        if ref:self.assets.path(p,ref)
        for link in value.get('links',[]):self.bible.check_target(p,link['type'],link['id'])
        with_provider=self.provider()
        try:
            check=compatible({**w,'graph':graph},with_provider.object_info(),bool(ref))
            if not check['compatible']:raise ConsoleError('；'.join(check['errors']),409)
        except httpx.HTTPError as e:raise ConsoleError('ComfyUI 未连接，请启动后重试',503) from e
        finally:with_provider.close()
        quantity=value.get('quantity',1)
        if not isinstance(quantity,int) or not 1<=quantity<=8:raise ConsoleError('单次队列数量限 1～8，每任务 Batch 1',422)
        rows=[]
        for _ in range(quantity):
            row={'id':uid('job'),'name':str(value.get('name','自由生图'))[:200],'project_id':p,'created_at':now(),'started_at':None,'finished_at':None,'status':'QUEUED','progress':None,'error':None,'cancel_requested':False,'workflow':w,'graph':graph,'parameters':params,'links':value.get('links',[]),'style':value.get('style'),'assets':[],'prompt_id':None,'provider':self.config()}
            write(safe(self.root(p),'art/jobs/'+row['id']+'.json'),row);rows.append(row)
        self.wake.set()
        return rows
    def cancel(self,p,id):
        row=self.get(p,'jobs',id)
        if row['status'] in TERMINAL:return row
        row['cancel_requested']=True
        if row['status']=='QUEUED':row.update(status='CANCELLED',finished_at=now())
        write(safe(self.root(p),'art/jobs/'+id+'.json'),row);return row
    def persist(self,p,row,blocking=True):
        while True:
            try:
                with write_guard(self.registry.engine):
                    current=self.get(p,'jobs',row['id']);row['cancel_requested']=current.get('cancel_requested',False)
                    write(safe(self.root(p),'art/jobs/'+row['id']+'.json'),row)
                return
            except ConsoleError as e:
                if e.status!=409 or not blocking: return
                if self.stop.wait(.1):return
    def start(self):
        from app.tasks.lease import acquire
        try:self.worker_lease=acquire(self.registry.engine,'studio-image-worker.lock')
        except ConsoleError:return
        self.thread=threading.Thread(target=self.run,daemon=True,name='novel-image-queue');self.thread.start()
    def close(self):
        from app.tasks.lease import release
        self.stop.set();self.wake.set()
        if self.thread:self.thread.join()
        release(self.worker_lease);self.worker_lease=None
    def run(self):
        # Recovery preserves server prompt IDs. Never silently resubmit an interrupted job.
        initial=True
        while not self.stop.is_set():
            self.wake.clear()
            self.registry.scan()
            for p in list(self.registry.rows):
                try:
                    for row in reversed(self.rows(p,'jobs')):
                        if initial and row['status']=='RUNNING':row.update(status='INTERRUPTED',error='上次应用退出时生成尚未完成；未自动重复提交',finished_at=now());self.persist(p,row)
                        if row['status']=='QUEUED' and not self.stop.is_set():self.execute(p,row)
                except Exception:continue # A damaged project's record does not stop other local work.
            initial=False;self.wake.wait(30)
    def execute(self,p,row):
        provider=ComfyUIProvider(row['provider']);ws=None
        row.update(status='RUNNING',started_at=now());self.persist(p,row)
        try:
            if row['cancel_requested']:
                row['status']='CANCELLED';return
            client_id=uid('client');ws=provider.socket(client_id) # Connect before enqueue, as in official example.
            graph=copy.deepcopy(row['graph']);ref=row['parameters'].get('reference')
            if ref:
                m=row['workflow']['mapping']['reference'];graph[str(m['node'])]['inputs'][m['input']]=provider.upload(self.assets.path(p,ref))
            row['submitted_graph']=graph
            submitted=provider.submit(graph,client_id);row['prompt_id']=submitted['prompt_id'];self.persist(p,row)
            start=time.monotonic();last_history=0;history=None
            while not self.stop.is_set():
                current=self.get(p,'jobs',row['id']);row['cancel_requested']=current['cancel_requested']
                if row['cancel_requested'] and provider.cancel_pending(row['prompt_id']):row['status']='CANCELLED';break
                if time.monotonic()-start>3600:raise ConsoleError('等待生成超过 60 分钟；保留服务器任务 ID，未全局中断',504)
                try:
                    msg=ws.recv()
                    event=json.loads(msg) if isinstance(msg,str) else {}
                    data=event.get('data',{})
                    if data.get('prompt_id')==row['prompt_id']:
                        if event.get('type')=='execution_error':raise ConsoleError('ComfyUI 执行失败：'+str(data.get('exception_message','')),422)
                        if event.get('type')=='progress':row['progress']={'value':data.get('value'),'max':data.get('max')};self.persist(p,row,False)
                except websocket.WebSocketTimeoutException:pass
                except (websocket.WebSocketConnectionClosedException,OSError):self.stop.wait(1)
                if time.monotonic()-last_history>=2:
                    history=provider.history(row['prompt_id']);last_history=time.monotonic()
                    if history and (history.get('status',{}).get('completed') or history.get('outputs') or history.get('status',{}).get('status_str')=='error'):break
            if self.stop.is_set():row['status']='INTERRUPTED'
            elif row['cancel_requested']:row['status']='CANCELLED'
            elif history:
                if history.get('status',{}).get('status_str')=='error':raise ConsoleError('ComfyUI 任务失败：'+str(history.get('status',{}).get('messages',[]))[:1800],422)
                outputs=[f for n,out in history.get('outputs',{}).items() if n in row['workflow']['outputs'] for f in out.get('images',[])]
                if not outputs:raise ConsoleError('工作流所选输出节点没有返回图片',422)
                for output in outputs:
                    data=provider.output(output)
                    while not self.stop.is_set():
                        try:
                            with write_guard(self.registry.engine):
                                if self.get(p,'jobs',row['id']).get('cancel_requested'):row['cancel_requested']=True;break
                                asset=self.assets.import_image(p,data,row['name'],{'job_id':row['id'],'workflow':row['workflow'],'submitted_graph':graph,'parameters':row['parameters'],'reference':ref,'style':row['style'],'created_at':now(),'server_output':output})
                                if row['links']:asset=self.assets.update(p,asset['id'],{'links':row['links']},asset['etag'])
                                row['assets'].append(asset['id'])
                            break
                        except ConsoleError as e:
                            if e.status!=409:raise
                            self.stop.wait(.2)
                row['status']='CANCELLED' if row['cancel_requested'] else 'INTERRUPTED' if self.stop.is_set() else 'SUCCEEDED'
        except Exception as e:row.update(status='FAILED',error=str(e)[:2500])
        finally:
            row['finished_at']=now();self.persist(p,row)
            if ws:ws.close()
            provider.close()
