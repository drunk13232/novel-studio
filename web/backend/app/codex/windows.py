"""Windowed-host subprocess policy for the existing official SDK.

The SDK 0.160.1 stdio launcher has no creationflags option. A module-local
subprocess facade adds CREATE_NO_WINDOW while retaining the official client,
binary, arguments, configuration and pipe ownership. No installed file is edited.
"""
import os
import subprocess


def hide_sdk_console():
    if os.name!='nt' or not os.environ.get('NOVEL_DESKTOP'):return
    import openai_codex.client as sdk
    class HiddenProcess:
        def __getattr__(self,name):return getattr(subprocess,name)
        def Popen(self,*args,**kwargs):
            kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
            return subprocess.Popen(*args,**kwargs)
    sdk.subprocess=HiddenProcess()
