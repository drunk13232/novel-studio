import os,time

def replace(source,target):
    """Windows scanners/readers may briefly hold the existing target open."""
    from app.library.storage import checkpoint_before_replace
    checkpoint_before_replace(target)
    for attempt in range(6):
        try:os.replace(source,target);return
        except PermissionError:
            if os.name!='nt' or attempt==5:raise
            time.sleep(0.01*(2**attempt))
