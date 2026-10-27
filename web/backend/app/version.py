"""Release identity shared with the packager; no user data is read."""
import json,sys
from pathlib import Path
def release_info():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[3]))
    path=base/'resources/version.json' if getattr(sys,'frozen',False) else base/'desktop/version.json'
    try:
        value=json.loads(path.read_text(encoding='utf8'))
        if not isinstance(value,dict) or not all(isinstance(value.get(k),str) for k in ('version','release_date','runtime_validation')) or not isinstance(value.get('changes'),list) or not all(isinstance(x,str) for x in value['changes']):raise ValueError('Invalid release metadata')
        return {k:value[k] for k in ('version','release_date','changes','runtime_validation')}
    except (OSError,ValueError,KeyError):
        return {'version':'UNKNOWN','release_date':'UNKNOWN','changes':[],'runtime_validation':'UNKNOWN'}
