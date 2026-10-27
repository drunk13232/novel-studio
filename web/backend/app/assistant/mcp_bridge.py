"""Ephemeral authenticated loopback bridge. All policy stays in Session.call."""
import hashlib,json,secrets,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from app.errors import ConsoleError
from app.assistant.actions import TOOLS
# One schema/dispatcher for UI, both personas, Python and Codex. Permissions and
# confirmation remain enforced by Session.call, including Python plans (Level 2).
MCP_ACTIONS=tuple(TOOLS)
class Bridge:
    def __init__(self,session):
        self.session=session;self.token=secrets.token_urlsafe(32);self.lock=threading.Lock();self.calls={};self.closed=False
        bridge=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def answer(self,status,value):
                data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers()
                try:self.wfile.write(data)
                except (OSError,ConnectionError):pass
            def authorized(self):
                return not bridge.closed and not self.headers.get('Origin') and secrets.compare_digest(self.headers.get('X-Novel-MCP',''),bridge.token)
            def do_GET(self):
                if not self.authorized():return self.answer(403,{'error':'bridge access denied'})
                if self.path=='/context':
                    try:bridge.session.check();return self.answer(200,{'session_id':bridge.session.id})
                    except Exception:return self.answer(409,{'error':'session ended'})
                if self.path!='/tools':return self.answer(404,{})
                try:
                    bridge.session.check();bridge.session.timing.mark('mcp_server_initialized');bridge.session.mcp_state='工具已发现'
                    self.answer(200,{'tools':[d for d in bridge.session.center.actions.definitions() if d['name'] in MCP_ACTIONS]})
                except Exception:return self.answer(409,{'error':'session ended'})
            def do_POST(self):
                if not self.authorized():return self.answer(403,{'error':'bridge access denied'})
                if self.path!='/call':return self.answer(404,{})
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if size<1 or size>20000:raise ValueError('invalid body size')
                    body=json.loads(self.rfile.read(size));name=body['name'];cid=body['call_id'];args=body['arguments']
                    if set(body)!={'name','call_id','arguments','session_id'} or name not in MCP_ACTIONS or not isinstance(cid,str) or not 1<=len(cid)<=80:raise ValueError('unregistered call')
                    signature=hashlib.sha256(json.dumps([name,args],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                    with bridge.lock:
                        bridge.session.check()
                        if body['session_id']!=bridge.session.id:raise ConsoleError('旧会话操作已撤销',409)
                        bridge.session.timing.mark('mcp_tool_start','正在调用工具',tool=name)
                        if bridge.session.scope_changed:raise ConsoleError('项目已切换，本会话工具已撤销',409)
                        if cid in bridge.calls:
                            old,value=bridge.calls[cid]
                            if old!=signature:raise ValueError('replayed call differs')
                        else:
                            bridge.session.mcp_state='正在执行应用操作'
                            value=bridge.session.call(name,args);bridge.calls[cid]=(signature,value)
                        self.answer(200,value)
                except Exception:return self.answer(403,{'ok':False,'error':{'message':'MCP 参数、权限或会话校验失败；未重试写入'}})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,name='NovelMCPBridge',daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def bind(self,session):
        with self.lock:
            self.session=session;self.calls={}
    def close(self):
        self.closed=True;self.token='';self.server.shutdown();self.server.server_close();self.thread.join(2)
