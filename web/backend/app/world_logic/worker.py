"""JSON stdin/stdout only; no filesystem/database/business access."""
import json, sys, os, traceback

def main():
    if sys.platform=='win32' and (sys.stdin is None or sys.stdout is None):
        import msvcrt,win32api
        if sys.stdin is None:sys.stdin=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_INPUT_HANDLE),os.O_RDONLY),'r',encoding='utf8')
        if sys.stdout is None:sys.stdout=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE),os.O_WRONLY),'w',encoding='utf8')
    if sys.stderr is None:sys.stderr=open(os.devnull,'w')
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    try:
        data=sys.stdin.buffer.read(160001)
        if len(data)>160000:raise ValueError('实验定义过大')
        from .engine import run
        result=run(json.loads(data))
    except Exception as e:result={'status':'ERROR','error':str(e)[:500],'error_type':type(e).__name__,'diagnostic':[{'module':os.path.basename(f.filename),'line':f.lineno,'function':f.name} for f in traceback.extract_tb(e.__traceback__)[-5:]]}
    blob=json.dumps(result,ensure_ascii=False,allow_nan=False).encode('utf8')
    if len(blob)>1000000:blob=b'{"status":"ERROR","error":"Result exceeds 1 MB limit"}'
    sys.stdout.buffer.write(blob);sys.stdout.buffer.flush()
if __name__=='__main__':main()
