import ctypes
import sys
from ctypes import HRESULT, Structure, c_uint, sizeof, byref
from ctypes.wintypes import HWND

ULONGLONG = ctypes.c_uint64

FLASHW_STOP = 0
FLASHW_CAPTION = 1
FLASHW_TRAY = 2
FLASHW_ALL = 3       # 同時閃爍標題列和工作列
FLASHW_TIMER = 4
FLASHW_TIMERNOFG = 12 

class FLASHWINFO(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("hwnd", HWND),
        ("dwFlags", c_uint),
        ("uCount", c_uint),    # 閃爍次數
        ("dwTimeout", c_uint)  # 閃爍速度 (毫秒, 0代表預設值)
    ]


if sys.platform == 'win32':
    from comtypes import IUnknown, GUID, COMMETHOD
    import comtypes.client as cc

    # 1. 介面定義 (手動定義，不依賴系統註冊表)
    # -----------------------------------------------------
    
    # ITaskbarList (基類)
    class ITaskbarList(IUnknown):
        _iid_ = GUID("{56FDF342-FD6D-11d0-958A-006097C9A090}")
        _methods_ = [
            COMMETHOD([], HRESULT, 'HrInit'),
            COMMETHOD([], HRESULT, 'AddTab', (['in'], HWND, 'hwnd')),
            COMMETHOD([], HRESULT, 'DeleteTab', (['in'], HWND, 'hwnd')),
            COMMETHOD([], HRESULT, 'ActivateTab', (['in'], HWND, 'hwnd')),
            COMMETHOD([], HRESULT, 'SetActiveAlt', (['in'], HWND, 'hwnd')),
        ]

    # ITaskbarList2 (繼承 ITaskbarList)
    class ITaskbarList2(ITaskbarList):
        _iid_ = GUID("{602D4995-B13A-429b-A66E-1935E44F4317}")
        _methods_ = [
            COMMETHOD([], HRESULT, 'MarkFullscreenWindow', (['in'], HWND, 'hwnd'), (['in'], ctypes.c_int, 'fFullscreen')),
        ]

    # ITaskbarList3 (繼承 ITaskbarList2) - 這才是我們主要用的
    class ITaskbarList3(ITaskbarList2):
        _iid_ = GUID("{ea1afb91-9e28-4b86-90e9-9e9f8a5eefaf}")
        _methods_ = [
            # SetProgressValue 是 ITaskbarList3 的第一個方法 (總順序第9個)
            COMMETHOD([], HRESULT, 'SetProgressValue', 
                      (['in'], HWND, 'hwnd'), 
                      (['in'], ULONGLONG, 'ullCompleted'), 
                      (['in'], ULONGLONG, 'ullTotal')),
            COMMETHOD([], HRESULT, 'SetProgressState', 
                      (['in'], HWND, 'hwnd'), 
                      (['in'], ctypes.c_int, 'tbpFlags')),
        ]
else:
    # 非 Windows 系統定義空類別以免報錯
    class ITaskbarList3: pass

class WindowsTaskbar:
    def __init__(self):
        self.hwnd = 0
        self.taskbar = None
        if sys.platform == 'win32':
            try:
                # 2. 建立物件的同時，指定我們上面手寫的介面 (interface=ITaskbarList3)
                # CLSID_TaskbarList = {56FDF344-FD6D-11d0-958A-006097C9A090}
                self.taskbar = cc.CreateObject(
                    "{56FDF344-FD6D-11d0-958A-006097C9A090}", 
                    interface=ITaskbarList3
                )
                self.taskbar.HrInit()
            except Exception as e:
                print(f"Taskbar init failed: {e}")
                self.taskbar = None

    def set_window_handle(self, window_title):
        """透過視窗標題抓取視窗 ID (HWND)"""
        if sys.platform == 'win32':
            # 需要等視窗完全建立後才能抓到，FindWindowW 需要完整的標題
            self.hwnd = ctypes.windll.user32.FindWindowW(None, window_title)

    def set_progress(self, current, total):
        """設定進度條數值 (綠色)"""
        if self.taskbar and self.hwnd:
            self.taskbar.SetProgressValue(self.hwnd, int(current), int(total))
            self.taskbar.SetProgressState(self.hwnd, 2) # 2 = Normal (Green)

    def set_state_error(self):
        """設定為錯誤狀態 (紅色)"""
        if self.taskbar and self.hwnd:
            self.taskbar.SetProgressState(self.hwnd, 4) # 4 = Error (Red)

    def set_state_indeterminate(self):
        """設定為不知確切進度狀態 (來回跑)"""
        if self.taskbar and self.hwnd:
            self.taskbar.SetProgressState(self.hwnd, 1) # 1 = Indeterminate

    def reset_progress(self):
        """清除進度條"""
        if self.taskbar and self.hwnd:
            self.taskbar.SetProgressState(self.hwnd, 0) # 0 = NoProgress
    
    def flash_window(self, count=5):
        """
        讓工作列圖示閃爍
        count: 閃爍次數
        """
        if sys.platform == 'win32' and self.hwnd:
            fwi = FLASHWINFO()
            fwi.cbSize = sizeof(FLASHWINFO)
            fwi.hwnd = self.hwnd
            fwi.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
            fwi.uCount = count
            fwi.dwTimeout = 0 # 使用系統預設閃爍速度
            
            # 呼叫 user32.dll 的 FlashWindowEx
            ctypes.windll.user32.FlashWindowEx(byref(fwi))