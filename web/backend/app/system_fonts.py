"""Local desktop font names from Windows GDI; no files or network access."""
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def installed_fonts():
    if os.name != 'nt' or not os.environ.get('NOVEL_DESKTOP'):
        return {'status':'UNAVAILABLE','families':[],'message':'字体检测仅在 Windows 桌面版提供；浏览器继续使用系统回退。'}
    try:
        import ctypes
        from ctypes import wintypes as w
        class LOGFONT(ctypes.Structure):
            _fields_=[(n,w.LONG) for n in ('height','width','escapement','orientation','weight')]+[(n,w.BYTE) for n in ('italic','underline','strikeout','charset','outprecision','clipprecision','quality','pitch')]+[('face',w.WCHAR*32)]
        class ENUMLOGFONT(ctypes.Structure):
            _fields_=[('font',LOGFONT),('full',w.WCHAR*64),('style',w.WCHAR*32),('script',w.WCHAR*32)]
        callback_type=ctypes.WINFUNCTYPE(ctypes.c_int,ctypes.POINTER(ENUMLOGFONT),ctypes.c_void_p,w.DWORD,ctypes.c_ssize_t)
        names=set()
        @callback_type
        def collect(font,metrics,kind,param):
            for name in (font.contents.font.face,font.contents.full):
                name=name.strip()
                if name and not name.startswith('@') and len(name)<=120:names.add(name)
            return 1 if len(names)<2048 else 0
        gdi=ctypes.WinDLL('gdi32',use_last_error=True)
        gdi.CreateCompatibleDC.argtypes=[w.HDC];gdi.CreateCompatibleDC.restype=w.HDC
        gdi.DeleteDC.argtypes=[w.HDC];gdi.DeleteDC.restype=w.BOOL
        gdi.EnumFontFamiliesExW.argtypes=[w.HDC,ctypes.POINTER(LOGFONT),callback_type,ctypes.c_ssize_t,w.DWORD]
        gdi.EnumFontFamiliesExW.restype=ctypes.c_int
        dc=gdi.CreateCompatibleDC(None)
        if not dc:raise OSError('GDI unavailable')
        try:
            query=LOGFONT();query.charset=1  # DEFAULT_CHARSET; enumerate all families.
            gdi.EnumFontFamiliesExW(dc,ctypes.byref(query),collect,0,0)
        finally:gdi.DeleteDC(dc)
        if not names:raise OSError('No enumerated fonts')
        return {'status':'AVAILABLE','families':sorted(names,key=str.casefold),'message':'由 Windows 返回的本机字体名称；具体汉字仍可能使用后备字形。'}
    except Exception:
        return {'status':'UNAVAILABLE','families':[],'message':'本机字体检测暂不可用；当前字体仍由系统回退，不影响写作。'}
