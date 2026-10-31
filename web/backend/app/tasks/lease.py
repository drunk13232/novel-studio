"""One OS-held task lease shared by desktop and development backends."""
import os
from app.errors import ConsoleError


def acquire(engine,name='codex-task.lock'):
    path=engine/'web/.runtime'/name
    path.parent.mkdir(parents=True,exist_ok=True)
    stream=path.open('a+b')
    try:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return stream
    except OSError as error:
        stream.close()
        raise ConsoleError('工作区正有另一项保存或任务进行中，请等待结束后重试。',409,code='WORKSPACE_BUSY') from error


def release(stream):
    if stream is None:return
    try:
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_UN)
    finally:stream.close()
