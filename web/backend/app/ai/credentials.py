"""Explicit Windows vault, never use keyring's plaintext/plugin fallbacks."""
import threading,uuid
from app.errors import ConsoleError

SECRET_VALUES=set()
SECRET_LOCK=threading.RLock()
def register(value):
    if value:
        with SECRET_LOCK:SECRET_VALUES.add(value)
def scrub(text):
    with SECRET_LOCK:
        for value in SECRET_VALUES:text=text.replace(value,'[REDACTED]')
    return text

class Credentials:
    def __init__(self,namespace):
        self.service='NovelStudio.AI.'+namespace
        self.session={};self.backend=None;self.reason='系统凭据存储不可用；可明确选择仅本次会话密钥'
        try:
            import os
            if os.name=='nt':
                from keyring.backends.Windows import WinVaultKeyring
                self.backend=WinVaultKeyring()
                if self.backend.priority<=0:self.backend=None
        except Exception:pass
    def put(self,reference,key,session_only=False):
        register(key)
        if session_only:self.session[reference]=key;return 'SESSION'
        if not self.backend:raise ConsoleError(self.reason,503)
        try:self.backend.set_password(self.service,reference,key)
        except Exception:raise ConsoleError(self.reason,503) from None
        self.session.pop(reference,None);return 'WINDOWS_CREDENTIAL_MANAGER'
    def get(self,reference):
        if not reference:return None
        key=self.session.get(reference)
        if not key and self.backend:
            try:key=self.backend.get_password(self.service,reference)
            except Exception:raise ConsoleError(self.reason,503) from None
        register(key);return key
    def delete(self,reference):
        self.session.pop(reference,None)
        if self.backend:
            try:
                if self.backend.get_password(self.service,reference) is not None:self.backend.delete_password(self.service,reference)
            except Exception:raise ConsoleError('删除系统凭据失败；配置未删除，请重试',503) from None
    def status(self,reference):
        try:configured=bool(self.get(reference))
        except ConsoleError:configured=False
        return {'configured':configured,'mode':'SESSION' if reference in self.session else 'WINDOWS_CREDENTIAL_MANAGER' if configured else 'NONE','available':self.backend is not None}
