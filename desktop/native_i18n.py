"""Native labels share the offline frontend catalogs and existing UI preference.
No credentials, content, global Codex configuration or user font files are read.
"""
import ctypes,hashlib,json,os,sys
from pathlib import Path
SUPPORTED={"zh-CN","zh-TW","en","ja","ko","es","fr","de","ru","pt-BR","pt-PT","it","nl","pl","uk","tr","id","vi","th","ms","hi","bn","ur","ar","fa","he"}

def object_file(path):
    try:
        data=json.loads(path.read_text(encoding='utf8'))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}

def current_language(data,workspace=None):
    workspace=workspace or os.environ.get('NOVEL_WORKSPACE') or object_file(data/'settings.json').get('workspace')
    if workspace:
        namespace=hashlib.sha256(str(Path(workspace).resolve()).casefold().encode()).hexdigest()[:20]
        pref=object_file(Path(os.environ.get('NOVEL_STUDIO_DATA',data/'workspaces'))/namespace/'preferences.json')
        if pref.get('ui_language') in SUPPORTED:return pref['ui_language']
    try:
        buffer=ctypes.create_unicode_buffer(85);ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer,85);raw=buffer.value
        if raw in SUPPORTED:return raw
        if raw.startswith(('zh-TW','zh-HK','zh-Hant')):return 'zh-TW'
        if raw.startswith('zh'):return 'zh-CN'
        if raw.startswith('pt'):return 'pt-BR' if raw.startswith('pt-BR') else 'pt-PT'
        if raw.split('-')[0] in SUPPORTED:return raw.split('-')[0]
    except (OSError,AttributeError):pass
    return 'zh-CN'

def native_text(key,data,workspace=None):
    language=current_language(data,workspace)
    bundle=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
    root=bundle/'resources/frontend/locales' if getattr(sys,'frozen',False) else bundle/'web/frontend/public/locales'
    for code in dict.fromkeys([language,'en','zh-CN']):
        value=object_file(root/code/'desktop.json').get(key)
        if isinstance(value,str) and value:return value
    return 'Novel Studio'
