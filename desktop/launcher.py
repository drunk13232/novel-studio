"""Novel Studio window + one owned loopback server. No novel data in the bundle."""
import argparse
import ctypes
import hashlib
import json
import logging
import os
import socket
import shutil
import subprocess
import sys
import threading
import time
import tempfile
import urllib.request
from http.client import HTTPConnection,HTTPException
from pathlib import Path
from ctypes import wintypes

def dispatch_worker():
    """Worker modes must not initialize desktop data, profiles or windows."""
    modes = {
        '--python-control-worker': 'app.automation.worker',
        '--world-logic-worker': 'app.world_logic.worker',
        '--assistant-mcp': 'app.assistant.mcp_server',
    }
    selected = [module for flag, module in modes.items() if flag in sys.argv]
    if not selected:
        return False
    if len(selected) != 1:
        raise SystemExit('Only one worker mode can be selected')
    if not getattr(sys, 'frozen', False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web/backend'))
    from importlib import import_module
    import_module(selected[0]).main()
    return True


if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    if dispatch_worker():
        raise SystemExit(0)

from native_i18n import native_text
TITLE='Novel Studio'
def default_data_directory():
    local = os.environ.get('LOCALAPPDATA')
    return (Path(local) if local else Path.home()/'AppData/Local')/'NovelStudio'

def json_object(path):
    try:
        value=json.loads(path.read_text(encoding='utf8'))
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError):return {}


def path_setting(value):
    return value if isinstance(value,str) and value.strip() and not any(ord(c)<32 for c in value) else None


def data_locations():
    """Keep local migration locators; ignore malformed persisted preferences."""
    executable=Path(sys.executable) if getattr(sys,'frozen',False) else Path(__file__)
    locations=json_object(executable.resolve().parent/'data-location.json')
    standard=default_data_directory()
    chosen=json_object(standard/'launcher-location.json').get('data')
    home=Path(path_setting(os.environ.get('NOVEL_STUDIO_HOME')) or path_setting(locations.get('data')) or path_setting(chosen) or standard).expanduser().resolve()
    preview=Path(path_setting(locations.get('preview_data')) or home.parent/'NovelStudioPreview').expanduser().resolve()
    return home,preview

DATA,PREVIEW_DATA=data_locations()
BUNDLE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
FROZEN=bool(getattr(sys,'frozen',False))
DEMO=False
def native(key):return native_text(key,DATA)
CONFIG_LOCK=threading.RLock()


def demo_source():
    return BUNDLE/'resources/demo-workspace' if FROZEN else BUNDLE/'desktop/preview-template'


def demo_workspace():
    """Copy only validated manifest entries, never a live/private workspace."""
    source=demo_source().resolve()
    manifest=json_object(source/'demo-manifest.json')
    entries=manifest.get('files')
    if not isinstance(entries,dict) or not entries:raise RuntimeError(native('invalidDemoManifest'))
    validated=[]
    for name,expected in entries.items():
        if not isinstance(name,str) or not isinstance(expected,str):raise RuntimeError(native('invalidDemoManifest'))
        relative=Path(name)
        path=source/relative
        if relative.is_absolute() or '..' in relative.parts or not path.resolve().is_relative_to(source) or any(p.is_symlink() for p in [path,*path.parents] if p.is_relative_to(source)):
            raise RuntimeError(native('invalidDemoPath'))
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise RuntimeError(native('demoHashMismatch')+name)
        validated.append((relative,path))
    target=DATA/'demo-workspace'
    if target.resolve().is_relative_to(BUNDLE.resolve()):raise RuntimeError(native('demoOutsideInstall'))
    if target.exists():
        if target.is_symlink() or not (target/'DEMO.txt').is_file() or (target/'DEMO.txt').read_text(encoding='utf8')!='Novel Studio original demo only\n':
            raise RuntimeError(native('demoMarkerMismatch'))
        (target/'web').mkdir(exist_ok=True)
        return valid_workspace(target,allow_demo=True)
    pending=DATA/'demo-workspace.pending'
    if pending.exists():raise RuntimeError(native('demoInitializationPending'))
    pending.mkdir()
    for relative,path in validated:
        destination=pending/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination)
    shutil.copyfile(source/'demo-manifest.json',pending/'demo-manifest.json')
    (pending/'web').mkdir(exist_ok=True)
    if not valid_workspace(pending,allow_demo=True):raise RuntimeError(native('demoIncomplete'))
    pending.rename(target)
    return valid_workspace(target,allow_demo=True)


def atomic_config(path,value):
    with CONFIG_LOCK:
        path.parent.mkdir(parents=True,exist_ok=True)
        handle,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.pending',dir=path.parent)
        temp=Path(name)
        try:
            with os.fdopen(handle,'w',encoding='utf8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
            os.replace(temp,path)
        finally:temp.unlink(missing_ok=True)

def read_config():
    return json_object(DATA/'settings.json')


def message(text):ctypes.windll.user32.MessageBoxW(None,text,TITLE,0x40)


def valid_workspace(value,allow_demo=False):
    if not isinstance(value,(str,Path)) or not str(value).strip():return None
    try:
        supplied=Path(value).expanduser()
        if supplied.is_symlink():return None
        root=supplied.resolve()
        required=['projects','.agents/skills','scripts/novel_workflow.py','engine/templates/project','web']
        if not all((root/name).exists() for name in required):return None
        if root.is_relative_to(BUNDLE.resolve()):
            if FROZEN:return None
        if root.is_relative_to(DATA.resolve()):
            marker=root/'DEMO.txt'
            if not allow_demo or root not in {DATA/'demo-workspace',DATA/'demo-workspace.pending'} or not marker.is_file() or marker.read_text(encoding='utf8')!='Novel Studio original demo only\n':return None
        return root
    except (OSError,ValueError,TypeError):return None


def workspace_choice(requested=None):
    if requested is not None:
        root=valid_workspace(requested)
        if not root:raise RuntimeError(native('invalidRequestedWorkspace'))
        return root
    config=read_config()
    exe=Path(sys.executable if FROZEN else __file__).resolve()
    candidates=[config.get('workspace'),os.environ.get('NOVEL_WORKSPACE'),*exe.parents,DATA.parent/'novel-workspace']
    for value in candidates:
        root=valid_workspace(value)
        if root:return root
    import tkinter as tk
    from tkinter import filedialog
    window=tk.Tk();window.withdraw()
    path=filedialog.askdirectory(title=native('chooseExistingWorkspace'))
    window.destroy()
    root=valid_workspace(path)
    if not root:raise RuntimeError(native('noValidWorkspace'))
    return root


def first_setup(default):
    """Small native directory wizard; reuses the public demo, never migrates novels."""
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    window=tk.Tk();window.title(TITLE+native('firstLaunchSuffix'));window.geometry('720x430');window.minsize(620,390)
    panel=ttk.Frame(window,padding=24);panel.pack(fill='both',expand=True);panel.columnconfigure(0,weight=1)
    data=tk.StringVar(value=str(default));workspace=tk.StringVar();mode=tk.StringVar(value='existing')
    existing=next((p for p in [*Path(sys.executable if FROZEN else __file__).resolve().parents,default.parent/'novel-workspace'] if valid_workspace(p)),None)
    if existing:workspace.set(str(existing))
    else:mode.set('demo')
    ttk.Label(panel,text=native('welcome'),font=('Microsoft YaHei UI',16)).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
    ttk.Label(panel,text=native('separateDataNotice'),wraplength=620).grid(row=1,column=0,columnspan=2,sticky='w')
    ttk.Label(panel,text=native('personalDataDirectory')).grid(row=2,column=0,sticky='w',pady=(18,4))
    ttk.Entry(panel,textvariable=data).grid(row=3,column=0,sticky='ew')
    def choose(variable):
        selected=filedialog.askdirectory(parent=window,title=native('chooseDirectory'),mustexist=True)
        if selected:variable.set(selected)
    ttk.Button(panel,text=native('browseDirectory'),command=lambda:choose(data)).grid(row=3,column=1,padx=(10,0))
    ttk.Radiobutton(panel,text=native('openExistingWorkspace'),variable=mode,value='existing').grid(row=4,column=0,sticky='w',pady=(18,4))
    ttk.Entry(panel,textvariable=workspace).grid(row=5,column=0,sticky='ew')
    ttk.Button(panel,text=native('browseWorkspace'),command=lambda:choose(workspace)).grid(row=5,column=1,padx=(10,0))
    demo_available=(demo_source()/'demo-manifest.json').is_file()
    ttk.Radiobutton(panel,text=native('tryPublicDemo'),variable=mode,value='demo',state='normal' if demo_available else 'disabled').grid(row=6,column=0,columnspan=2,sticky='w',pady=(14,4))
    ttk.Label(panel,text=native('demoIsolationNotice'),wraplength=610).grid(row=7,column=0,columnspan=2,sticky='w')
    result=[]
    def accept():
        try:
            if not data.get().strip():raise ValueError(native('choosePersonalData'))
            destination=Path(data.get()).expanduser().resolve()
            install=Path(sys.executable).resolve().parent if FROZEN else BUNDLE
            if destination.is_relative_to(install) or destination.is_relative_to(BUNDLE):raise ValueError(native('dataInsideInstallRejected'))
            if destination.exists() and not destination.is_dir():raise ValueError(native('dataPathNotDirectory'))
            target=valid_workspace(workspace.get()) if mode.get()=='existing' else None
            if mode.get()=='existing' and not target:raise ValueError(native('chooseCompleteWorkspace'))
            if mode.get()=='demo' and not demo_available:raise ValueError(native('demoResourcesMissing'))
            if target and (destination.is_relative_to(target) or target.is_relative_to(destination)):raise ValueError(native('dataWorkspaceOverlap'))
            result.append((destination,str(target) if target else None,mode.get()=='demo'));window.destroy()
        except Exception as error:messagebox.showerror(TITLE,str(error),parent=window)
    actions=ttk.Frame(panel);actions.grid(row=8,column=0,columnspan=2,sticky='e',pady=(20,0))
    ttk.Button(actions,text=native('cancel'),command=window.destroy).pack(side='left',padx=8)
    ttk.Button(actions,text=native('begin'),command=accept).pack(side='left')
    window.mainloop()
    return result[0] if result else None


class SingleInstance:
    def __init__(self):
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype=wintypes.HANDLE
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        suffix='Preview-'+hashlib.sha256(str(DATA).casefold().encode()).hexdigest()[:16] if DEMO else 'V1-'+os.environ.get('USERNAME','user')
        self.handle=self.kernel.CreateMutexW(None,False,'Local\\NovelStudioDesktop'+suffix)
        if not self.handle:raise RuntimeError(native('instanceLockFailed'))
        self.existing=ctypes.get_last_error()==183
    def activate(self):
        user=ctypes.windll.user32
        user.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];user.FindWindowW.restype=wintypes.HWND
        user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int];user.SetForegroundWindow.argtypes=[wintypes.HWND]
        for _ in range(60):
            handle=user.FindWindowW(None,TITLE)
            if handle:user.ShowWindow(handle,9);user.SetForegroundWindow(handle);return
            time.sleep(.15)
        message(native('applicationStarting'))
    def close(self):self.kernel.CloseHandle(self.handle)


class Bridge:
    def __init__(self,app,config):
        self._app=app;self._config=config;self._window=None;self._ready=False;self._allow_close=False;self._restart=None;self._selected=None;self._exit_thread=None;self._exit_guard=threading.Lock()
    def ready(self):self._ready=True
    def request_exit(self):
        if not self._exit_guard.acquire(blocking=False):
            return {'ok':False,'error':native('exitAlreadyPreparing')}
        try:
            if self._allow_close:return {'ok':True}
            if self._app.state.active_tasks():return {'ok':False,'error':native('codexTasksActive')}
            try:self._app.state.data_center.scheduled(exit=True)
            except Exception as error:return {'ok':False,'error':native('backupIncomplete')+'\n'+str(error)}
            # Work may have started while an exit backup was being prepared.
            if self._app.state.active_tasks():return {'ok':False,'error':native('codexTasksActive')}
            self._allow_close=True
            # Finish the actual JS-API reply worker before disposing its WebView.
            caller=threading.current_thread()
            def close_after_reply():
                if caller is not threading.main_thread():caller.join()
                self._window.destroy()
            try:
                self._exit_thread=threading.Thread(target=close_after_reply,name='NovelStudioWindowClose',daemon=False)
                self._exit_thread.start()
            except Exception:
                self._allow_close=False;self._exit_thread=None
                logging.exception('Owned desktop close worker could not start')
                return {'ok':False,'error':native('exitCloseFailed')}
            return {'ok':True}
        finally:self._exit_guard.release()
    def open_project_folder(self,project):
        try:
            path=self._app.state.registry.workspace(project).root
            os.startfile(str(path));return {'ok':True}
        except Exception as error:return {'error':str(error)}
    def choose_backup_directory(self):
        import webview
        result=self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return {'path':result[0]} if result else {}
    def choose_export_directory(self):
        return self.choose_backup_directory()
    def choose_workspace(self):
        if DEMO:return {'error':native('demoCannotOpenPrivate')}
        import webview
        result=self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not result:return {}
        root=valid_workspace(result[0])
        if not root:return {'error':native('invalidWorkspaceUnchanged')}
        self._selected=str(root)
        return {'path':self._selected}
    def switch_workspace(self,path):
        if path!=self._selected:return {'ok':False,'error':native('useWorkspacePicker')}
        if self._app.state.active_tasks():return {'ok':False,'error':native('stopTasksFirst')}
        root=valid_workspace(path)
        if not root:return {'ok':False,'error':native('workspaceNoLongerValid')}
        self._config['workspace']=str(root);atomic_config(DATA/'settings.json',self._config)
        self._restart=str(root)
        return self.request_exit()
    def closing(self):
        if self._allow_close:return True
        if not self._ready:
            return not bool(self._app.state.active_tasks())
        # Never block the UI thread waiting for JavaScript to answer.
        def notify():
            try:
                mounted=self._window.evaluate_js("Boolean(document.querySelector('#root')?.firstElementChild)")
                if not mounted and not self._app.state.active_tasks():
                    self._allow_close=True;self._window.destroy();return
                self._window.evaluate_js("window.dispatchEvent(new Event('novel-close-request'))")
            except Exception:logging.exception('Could not display close prompt')
        threading.Thread(target=notify,daemon=True).start()
        return False


def browser_fallback(url,app):
    import tkinter as tk
    from tkinter import messagebox
    import webbrowser
    window=tk.Tk();window.title(TITLE);window.geometry('470x210');window.resizable(False,False)
    tk.Label(window,text=native('browserOpened'),font=('Microsoft YaHei',14)).pack(pady=(24,12))
    tk.Label(window,text=native('browserManager'),font=('Microsoft YaHei',10)).pack()
    tk.Button(window,text=native('openWritingPage'),command=lambda:webbrowser.open(url)).pack(pady=10)
    def close():
        if app.state.active_tasks():messagebox.showinfo(TITLE,native('activeTasks'));return
        if messagebox.askokcancel(TITLE,native('confirmExit')):
            try:app.state.data_center.scheduled(exit=True)
            except Exception as error:messagebox.showerror(TITLE,native('backupIncomplete')+'\n'+str(error));return
            window.destroy()
    tk.Button(window,text=native('safeExit'),command=close).pack();window.protocol('WM_DELETE_WINDOW',close)
    webbrowser.open(url);window.mainloop()


def backend_ready(port):
    """Probe only the owned loopback server; no proxy, redirects or TLS setup."""
    connection=HTTPConnection('127.0.0.1',port,timeout=.5)
    try:
        connection.request('GET','/api/session')
        response=connection.getresponse()
        return response.status==200
    finally:
        connection.close()


def main():
    global DATA,TITLE,DEMO
    args=argparse.ArgumentParser();args.add_argument('--workspace');args.add_argument('--browser',action='store_true');args.add_argument('--demo',action='store_true');args.add_argument('--demo-data');options=args.parse_args()
    DEMO=options.demo or (FROZEN and (BUNDLE/'resources/preview.txt').is_file() and not options.workspace)
    if options.demo_data and not DEMO:args.error('--demo-data requires demo mode')
    if not DEMO and not options.workspace and FROZEN:
        remembered=read_config()
        if remembered.get('demo'):DEMO=True
        elif not valid_workspace(remembered.get('workspace')):
            choice=first_setup(DATA)
            if not choice:return
            DATA,options.workspace,DEMO=choice
            if not os.environ.get('NOVEL_STUDIO_HOME'):
                atomic_config(default_data_directory()/'launcher-location.json',{'data':str(DATA)})
    if DEMO:
        DATA=Path(options.demo_data).expanduser().resolve() if options.demo_data else PREVIEW_DATA if options.demo or (BUNDLE/'resources/preview.txt').is_file() else DATA
        if DATA.is_relative_to(BUNDLE):raise RuntimeError(native('demoDataInsideInstall'))
        TITLE=native('demoTitle')
        os.environ['NOVEL_DEMO']='1'
    DATA.mkdir(parents=True,exist_ok=True)
    if sys.stdout is None:sys.stdout=open(os.devnull,'w')
    if sys.stderr is None:sys.stderr=open(os.devnull,'w')
    from logging.handlers import RotatingFileHandler
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(DATA/'launcher.log',maxBytes=2*1024*1024,backupCount=2,encoding='utf8')])
    instance=SingleInstance()
    if instance.existing:instance.activate();instance.close();return
    server=None;thread=None;bound=None;bridge=None
    try:
        workspace=demo_workspace() if DEMO else workspace_choice(options.workspace)
        if not workspace:raise RuntimeError(native('demoIncomplete'))
        if DEMO:
            namespace=hashlib.sha256(str(workspace.resolve()).casefold().encode()).hexdigest()[:20]
            public=DATA/'workspaces'/namespace/'reference-library'
            if not public.exists():
                public.parent.mkdir(parents=True,exist_ok=True)
                shutil.copytree(workspace/'demo-public/reference-library',public)
        config=read_config();config['workspace']=str(workspace);config['demo']=DEMO
        bound=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        if os.name=='nt':bound.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        try:bound.bind(('127.0.0.1',int(config.get('port',8876))))
        except OSError:bound.bind(('127.0.0.1',0))
        port=bound.getsockname()[1];bound.listen(128);config['port']=port
        atomic_config(DATA/'settings.json',config)
        static=BUNDLE/'resources/frontend' if FROZEN else BUNDLE/'web/frontend/dist'
        if not (static/'index.html').is_file():raise RuntimeError(native('frontendResourcesMissing'))
        os.environ.update(NOVEL_WORKSPACE=str(workspace),NOVEL_PORT=str(port),NOVEL_STATIC_DIR=str(static),NOVEL_STUDIO_DATA=str(DATA/'workspaces'),NOVEL_DESKTOP='1')
        if not FROZEN:sys.path.insert(0,str(BUNDLE/'web/backend'))
        # Imports occur only after real workspace and resources have been split.
        from app.main import app
        import uvicorn
        server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_config=None,access_log=False,timeout_graceful_shutdown=30))
        thread=threading.Thread(target=lambda:server.run(sockets=[bound]),name='NovelStudioBackend',daemon=False);thread.start()
        url=f'http://127.0.0.1:{port}/'
        for _ in range(150):
            if not thread.is_alive():raise RuntimeError(native('backendStartupFailed'))
            try:
                if backend_ready(port):break
            except (OSError,ValueError,HTTPException) as error:
                if _==0:logging.info('Local readiness pending: %s',type(error).__name__)
                time.sleep(.1)
        else:raise RuntimeError(native('backendReadyTimeout'))
        atomic_config(DATA/'instance.json',{'pid':os.getpid(),'port':port,'url':url,'workspace':str(workspace),'started_at':time.time()})
        logging.info('Ready pid=%s port=%s workspace=%s',os.getpid(),port,workspace)
        # Persistent WebView profiles must not reuse an older entry document
        # whose hashed asset names no longer exist after an onedir upgrade.
        url+='?build='+hashlib.sha256((static/'index.html').read_bytes()).hexdigest()[:16]
        if options.browser:browser_fallback(url,app)
        else:
            try:
                import webview
                webview.settings['ALLOW_FILE_URLS']=False
                webview.settings['ALLOW_DOWNLOADS']=True
                bridge=Bridge(app,config)
                window=webview.create_window(TITLE,url,js_api=bridge,width=1280,height=850,min_size=(820,460),background_color='#fbfaf7',text_select=True)
                bridge._window=window;window.events.closing+=bridge.closing
                webview.start(gui='edgechromium',private_mode=False,storage_path=str(DATA/'webview'),debug=False)
            except Exception:
                logging.exception('WebView2 unavailable; browser fallback')
                message(native('webviewUnavailable'))
                browser_fallback(url,app)
    except Exception as error:
        logging.exception('Launcher failed')
        message(native('startupFailed')+'\n'+str(error)+'\n\n'+native('logLocation')+': '+(native('demoLogLocation') if DEMO else str(DATA/'launcher.log')))
    finally:
        if server:server.should_exit=True
        if thread:
            thread.join()  # Graceful HTTP/file writes finish; never kill unrelated processes.
        if bridge and bridge._exit_thread:bridge._exit_thread.join()
        if bound:bound.close()
        try:
            record=json.loads((DATA/'instance.json').read_text(encoding='utf8'))
            if record.get('pid')==os.getpid():(DATA/'instance.json').unlink()
        except (OSError,ValueError):pass
        instance.close()
        logging.info('Novel Studio stopped cleanly')
        if bridge and bridge._restart:
            command=[sys.executable]+([] if FROZEN else [str(Path(__file__).resolve())])+['--workspace',bridge._restart]
            subprocess.Popen(command,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)

if __name__=='__main__':
    main()
