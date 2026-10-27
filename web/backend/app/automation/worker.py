"""Host-owned WASI worker. Untrusted Python runs only inside WebAssembly."""
import json,os,sys,threading
from pathlib import Path

def streams():
    if sys.platform=='win32' and (sys.stdin is None or sys.stdout is None):
        import msvcrt,win32api
        if sys.stdin is None:sys.stdin=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_INPUT_HANDLE),os.O_RDONLY),'r',encoding='utf-8')
        if sys.stdout is None:sys.stdout=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE),os.O_WRONLY),'w',encoding='utf-8')
        if sys.stderr is None:sys.stderr=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_ERROR_HANDLE),os.O_WRONLY),'w',encoding='utf-8')

def main():
    streams()
    import wasmtime
    runtime=Path(__file__).with_name('runtime')
    sdk=Path(sys._MEIPASS)/'resources/python' if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[4]/'python'
    config=wasmtime.Config();config.consume_fuel=True;config.epoch_interruption=True
    engine=wasmtime.Engine(config);store=wasmtime.Store(engine)
    store.set_fuel(20000000000);store.set_limits(memory_size=268435456,table_elements=100000,instances=2,memories=2,tables=2)
    store.set_epoch_deadline(1)
    timer=threading.Timer(210,engine.increment_epoch);timer.daemon=True;timer.start()
    wasi=wasmtime.WasiConfig()
    wasi.argv=['python','-B','-u','-c','import sys;sys.path.insert(0,"/sdk");from novel_studio_api._bootstrap import main;main()']
    wasi.env=[('PYTHONHOME','/runtime'),('PYTHONIOENCODING','utf-8')]
    wasi.preopen_dir(str(runtime),'/runtime',False);wasi.preopen_dir(str(sdk),'/sdk',False)
    wasi.inherit_stdin()
    def stdout(data):sys.stdout.buffer.write(data);sys.stdout.buffer.flush();return len(data)
    def stderr(data):sys.stderr.buffer.write(data);sys.stderr.buffer.flush();return len(data)
    wasi.stdout_custom=stdout;wasi.stderr_custom=stderr;store.set_wasi(wasi)
    linker=wasmtime.Linker(engine);linker.define_wasi()
    try:
        module=wasmtime.Module.from_file(engine,str(runtime/'python.wasm'))
        instance=linker.instantiate(store,module)
        instance.exports(store)['_start'](store)
    except wasmtime.ExitTrap as error:
        if error.code:raise SystemExit(error.code)
    finally:timer.cancel()

if __name__=='__main__':main()
