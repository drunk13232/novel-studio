"""Official SDK text-only adapter; no filesystem, tools, redirects or paid retries."""
import ipaddress,socket,threading,time
from urllib.parse import urlsplit,urlunsplit
import httpx2
from openai import OpenAI,APIStatusError,APITimeoutError,APIConnectionError
from app.errors import ConsoleError
from app.ai.credentials import scrub

ERRORS={401:'认证失败：请更新 API Key。',403:'该密钥没有此服务或模型权限。',404:'模型或接口不存在：检查 Base URL、协议和 Model ID。',429:'请求频率或配额受限：检查余额与限流后手动重试。'}
def normalize_url(value):
    try:u=urlsplit(value.strip());port=u.port
    except ValueError:raise ConsoleError('API 地址格式错误',422) from None
    if u.scheme not in {'https','http'} or not u.hostname or u.username or u.password or u.query or u.fragment or '\\' in value:raise ConsoleError('API 地址须为不含凭据、查询参数的 HTTP(S) 服务根地址',422)
    path=u.path.rstrip('/')
    if any(part in path.lower() for part in ['/chat/completions','/responses','/models']):raise ConsoleError('请填写服务根地址，例如 https://服务商/v1，不是请求接口路径',422)
    while '/v1/v1' in path:path=path.replace('/v1/v1','/v1')
    if not path:path='/v1'
    host=u.hostname.lower()
    try:local=ipaddress.ip_address(host).is_loopback
    except ValueError:local=host=='localhost'
    if u.scheme=='http' and not local:raise ConsoleError('远端 API 必须使用 HTTPS；HTTP 只允许本机回环服务',422)
    if port in {8765,8876,8878,5173}:raise ConsoleError('不能把 Novel Studio 自身或前端端口设为 AI 服务',422)
    return urlunsplit((u.scheme,u.netloc.lower(),path,'',''))

def endpoint(value):
    url=normalize_url(value);u=urlsplit(url)
    try:addresses={row[4][0] for row in socket.getaddrinfo(u.hostname,u.port or (443 if u.scheme=='https' else 80),type=socket.SOCK_STREAM)}
    except OSError:raise ConsoleError('无法解析服务地址；请检查网络或本地服务是否启动',502) from None
    loopback=all(ipaddress.ip_address(ip).is_loopback for ip in addresses)
    try:explicit_local=ipaddress.ip_address(u.hostname).is_loopback
    except ValueError:explicit_local=u.hostname=='localhost'
    if loopback!=explicit_local:raise ConsoleError('DNS 解析范围与配置地址不一致，已拒绝请求',403)
    if not addresses or not loopback and any(not ipaddress.ip_address(ip).is_global for ip in addresses):raise ConsoleError('此地址指向受保护的内网或系统服务，已拒绝发送凭据',403)
    return url,u,sorted(addresses)[0],loopback

def client(provider,key,timeout):
    url,u,ip,local=endpoint(provider.base_url)
    def pin(request):
        if request.url.host!=u.hostname or request.url.port!=(u.port or (443 if u.scheme=='https' else 80)):raise ConsoleError('请求目标变化，已阻止凭据发送',403)
        if provider.auth_header!='Authorization':request.headers.pop('Authorization',None)
        request.headers['Host']=u.netloc
        request.extensions['sni_hostname']=u.hostname
        request.url=request.url.copy_with(host=ip)
    transport=httpx2.Client(timeout=timeout,follow_redirects=False,trust_env=False,event_hooks={'request':[pin]})
    headers={}
    # Custom authentication is allowlisted; the ordinary Bearer header is removed.
    if provider.auth_header!='Authorization':
        headers[provider.auth_header]=key or ''
        headers['Authorization']=''
    return OpenAI(api_key=key or 'local-no-key',base_url=url,timeout=timeout,max_retries=0,http_client=transport,default_headers=headers)

def failure(error):
    if isinstance(error,ConsoleError):return str(error)
    if isinstance(error,APITimeoutError):return '请求超时；上游是否已执行未知，请检查服务商记录后手动重试。'
    if isinstance(error,APIConnectionError):return '网络连接中断或本地模型未启动；检查地址、服务和网络。'
    if isinstance(error,APIStatusError):
        code=error.status_code
        return ERRORS.get(code,'服务端错误，请稍后手动重试。' if code>=500 else '接口拒绝请求：检查参数支持情况、协议或服务响应。')+f' [HTTP {code}]'
    return '流式输出或返回格式异常；诊断类型：'+type(error).__name__

def failure_kind(error):
    """Stable diagnostics without returning upstream bodies or credentials."""
    if isinstance(error,APITimeoutError):return 'TIMEOUT'
    if isinstance(error,APIConnectionError):return 'UNREACHABLE'
    if isinstance(error,APIStatusError):
        code=error.status_code
        if code==401:return 'AUTH_FAILED'
        if code==403:return 'PERMISSION_DENIED'
        if code==404:return 'MODEL_OR_ENDPOINT_NOT_FOUND'
        if code==429:return 'RATE_OR_QUOTA_LIMIT'
        if code>=500:return 'SERVER_ERROR'
        body=getattr(error,'body',{})
        text=str(body).lower()
        if code in {400,422} and any(k in text for k in ['unsupported','unknown parameter','unrecognized','not supported','not_support','required parameter','max_tokens','max_completion_tokens','max_output_tokens']):return 'UNSUPPORTED_PARAMETER'
        return 'REQUEST_REJECTED'
    if isinstance(error,ConsoleError):
        text=str(error)
        if '尚未配置' in text and '输出长度参数' in text:return 'PARAMETER_MAPPING_REQUIRED'
        if '不支持' in text and ('参数' in text or 'temperature' in text or 'top_p' in text):return 'UNSUPPORTED_PARAMETER'
        if '截断' in text:return 'TRUNCATED'
        if '解析服务地址' in text:return 'UNREACHABLE'
        if any(k in text for k in ['返回','流式','服务没有','服务返回']):return 'INVALID_RESPONSE'
        return 'LOCAL_CONFIGURATION'
    return 'INVALID_RESPONSE'

class LLMProviderAdapter:
    def __init__(self,provider,model,key,record,task_type,project,parameters=None,role='AUTHOR'):
        self.provider=provider;self.model=model;self.key=key;self.record=record;self.task_type=task_type;self.project=project
        self.params=parameters or model.parameters;self.role=role
        self.cancelled=threading.Event();self.stream=None;self.client=None
        self.metadata={'backend':'llm','provider_id':provider.provider_id,'provider_name':provider.display_name,'model':model.id,'protocol':model.protocol,'task_type':task_type}
    def close(self):
        self.cancelled.set()
        try:
            if self.stream:self.stream.close()
        except Exception:pass
        try:
            if self.client:self.client.close()
        except Exception:pass
    interrupt=close
    def start_task(self,prompt,emit,**kwargs):
        started=time.monotonic();usage=None;output='';error=None;status='failed';error_category=None;phase='configuration';truncated=False;stream_finished=False
        first_output_ms=None
        if getattr(self,'prepare_controlled_prompt',None):prompt=self.prepare_controlled_prompt(prompt,kwargs.get('output_schema'))
        if kwargs.get('output_schema'):prompt+='\n仅返回以下 Schema 对应的 JSON，不使用 Markdown：\n'+__import__('json').dumps(kwargs['output_schema'],ensure_ascii=False)
        try:
            if self.cancelled.is_set():return {'status':'interrupted','output':''}
            p=self.params;m=self.model;cap=m.capabilities
            from app.ai.parameters import request_arguments
            args=request_arguments(self.provider,m,p)
            stream=args['stream']
            self.metadata['used_streaming']=stream
            if p.streaming and cap.get('streaming') is False:emit('warning','此模型不支持流式，使用已配置的非流式模式',{'parameter':'streaming'})
            self.metadata.update(request_model=m.id,effective_parameters={k:v for k,v in args.items() if k!='model'})
            emit('ai_request','本轮模型与真实参数已固定',self.metadata)
            phase='connection';self.client=client(self.provider,self.key,min(p.timeout,self.provider.timeout))
            phase='request'
            if m.protocol=='responses':
                args.update(input=prompt,store=False)
                response=self.client.responses.create(**args)
            else:
                args['messages']=[{'role':'user','content':prompt}]
                # Unknown servers may reject stream_options; request it only with confirmed streaming.
                if stream and cap.get('streaming') is True:args['stream_options']={'include_usage':True}
                response=self.client.chat.completions.create(**args)
            def append(text):
                nonlocal output,first_output_ms
                if self.cancelled.is_set():return
                if text and first_output_ms is None:first_output_ms=round((time.monotonic()-started)*1000,1)
                output+=text
                if len(output)>2000000:raise ConsoleError('输出超过本机安全限制，请降低输出规模',422)
                emit('llm_delta',scrub(text),{'delta':scrub(text),'model':m.id,'provider':self.provider.display_name})
            self.metadata['observed_model']=getattr(response,'model',None) if not stream else None
            if stream:
                self.stream=response
                for chunk in response:
                    observed=getattr(chunk,'model',None)
                    if observed:self.metadata['observed_model']=observed
                    if self.cancelled.is_set():break
                    if m.protocol=='responses':
                        if chunk.type=='response.output_text.delta':append(chunk.delta)
                        elif chunk.type in {'response.completed','response.incomplete'}:
                            self.metadata['observed_model']=getattr(chunk.response,'model',None)
                            usage=chunk.response.usage;stream_finished=True
                            truncated=chunk.type=='response.incomplete'
                        elif chunk.type in {'response.failed','error'}:raise ConsoleError('服务返回流式错误，未保存为成功结果',502)
                    else:
                        if chunk.usage:usage=chunk.usage
                        for choice in chunk.choices:
                            if choice.delta.content:append(choice.delta.content)
                            if choice.finish_reason:stream_finished=True
                            if choice.finish_reason=='length':truncated=True
                            elif choice.finish_reason not in {None,'stop'}:raise ConsoleError('服务拒绝或未返回完整文本，结果未采纳',502)
                self.stream.close()
                if not self.cancelled.is_set() and not stream_finished:raise ConsoleError('流式连接提前结束，未收到完整结束状态，请手动检查',502)
            elif m.protocol=='responses':
                append(response.output_text);usage=response.usage;truncated=response.status=='incomplete'
                if response.status=='failed':raise ConsoleError('服务返回失败状态',502)
            else:
                append(response.choices[0].message.content or '');usage=response.usage;truncated=response.choices[0].finish_reason=='length'
            if self.cancelled.is_set():status='interrupted'
            elif truncated:raise ConsoleError('内容被截断；请提高已支持的输出上限或缩小任务。未自动采纳结果。',422)
            elif not output.strip():raise ConsoleError('服务没有返回有效文本',502)
            else:status='completed'
        except Exception as exc:
            if self.cancelled.is_set():status='interrupted'
            else:error=failure(exc);error_category=failure_kind(exc)
        finally:
            if self.client:
                try:self.client.close()
                except Exception:pass
            tokens=usage.model_dump() if usage else {}
            self.metadata.update(usage=tokens or None,first_output_ms=first_output_ms,duration_ms=round((time.monotonic()-started)*1000,1),status=status)
            inp=tokens.get('input_tokens',tokens.get('prompt_tokens'));out=tokens.get('output_tokens',tokens.get('completion_tokens'))
            self.metadata['cost_estimate']=(inp*self.model.input_price+out*self.model.output_price)/1000000 if inp is not None and out is not None and self.model.input_price is not None and self.model.output_price is not None else None
            self.metadata['currency']=self.model.currency
            self.record(self.provider,self.model,self.project,self.task_type,status,time.monotonic()-started,tokens,error)
        return {'status':status,'output':output, 'error':error,'error_category':error_category,'stage':'completed' if status=='completed' else phase,'ai_metadata':self.metadata}
