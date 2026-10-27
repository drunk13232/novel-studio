"""Executed by guest CPython WASI, never by the FastAPI interpreter."""
import json,sys,traceback
def main():
    data=json.loads(sys.stdin.readline(1000000))
    code=data['code']
    namespace={'__name__':'__main__','__file__':'<author-script>'}
    try:
        exec(compile(code,'<author-script>','exec'),namespace)
    except BaseException as error:
        if isinstance(error,SystemExit) and not error.code:return
        traceback.print_exc()
        raise SystemExit(1)
