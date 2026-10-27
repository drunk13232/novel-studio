"""OS resource ceilings for owned solver processes, never other applications."""
import os
class Budget:
    def __init__(self,process):
        self.handle=None
        if os.name!='nt':return
        import ctypes
        from ctypes import wintypes as w
        class IO(ctypes.Structure):_fields_=[(n,ctypes.c_ulonglong) for n in ['ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount']]
        class BASIC(ctypes.Structure):_fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
        class EXTENDED(ctypes.Structure):_fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        k=ctypes.WinDLL('kernel32',use_last_error=True);k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE;k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];k.CloseHandle.argtypes=[w.HANDLE]
        h=k.CreateJobObjectW(None,None)
        if not h:raise OSError('无法建立求解器资源限制')
        limits=EXTENDED();limits.BasicLimitInformation.LimitFlags=0x2000|0x100|0x200|0x8;limits.BasicLimitInformation.ActiveProcessLimit=2;limits.ProcessMemoryLimit=512*1024*1024;limits.JobMemoryLimit=512*1024*1024
        if not k.SetInformationJobObject(h,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(h,w.HANDLE(int(process._handle))):
            k.CloseHandle(h);raise OSError('无法应用求解器资源限制，已拒绝无限制运行')
        self.handle=h;self.kernel=k
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None
