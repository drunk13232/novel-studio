"""Real loopback readiness, independent of user proxy or HTTPS configuration."""
import importlib.util,sys,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer


def test_desktop_readiness_uses_real_owned_loopback(monkeypatch):
    root=Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(root/'desktop'))
    spec=importlib.util.spec_from_file_location('readiness_launcher',root/'desktop/launcher.py')
    launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            assert self.path=='/api/session'
            self.send_response(200);self.end_headers();self.wfile.write(b'{}')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('HTTP_PROXY','http://127.0.0.1:9')
    monkeypatch.setenv('http_proxy','http://127.0.0.1:9')
    monkeypatch.setenv('NO_PROXY','')
    monkeypatch.setattr(launcher.urllib.request,'urlopen',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('Ambient opener must not be used')))
    try:assert launcher.backend_ready(server.server_port)
    finally:server.shutdown();server.server_close();thread.join(2)
