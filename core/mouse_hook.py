"""
Qingxin Translator - Mouse Selection Hook
全局鼠标钩子：检测"拖选"动作（左键按下 → 移动超过阈值 → 松开），
用于弹出选区悬浮翻译按钮。

- WH_MOUSE_LL 低级鼠标钩子，独立线程运行
- 检测阈值：按下与松开距离 > 10px 视为拖选
- 回调 on_select(x, y)：松开时鼠标位置（屏幕坐标）
"""

import ctypes
import threading
from ctypes import wintypes
from typing import Callable, Optional

from core.logger import log

# Windows 常量
WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_MOUSEMOVE = 0x0200

# 钩子事件结构
class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

# 回调函数类型
HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong,          # LRESULT (64 位)
    ctypes.c_int,               # nCode
    wintypes.WPARAM,            # wParam
    wintypes.LPARAM,            # lParam
)


class MouseSelectionHook:
    """全局鼠标拖选检测钩子"""

    def __init__(self):
        self._hook = None
        self._thread: Optional[threading.Thread] = None
        self._on_select: Optional[Callable] = None
        self._running = False

        self._pressed = False
        self._press_x = 0
        self._press_y = 0

        # 回调对象必须保持引用（否则被 GC 后钩子崩溃）
        self._callback = HOOKPROC(self._hook_proc)

    def _hook_proc(self, n_code, w_param, l_param):
        if n_code >= 0:
            try:
                if w_param == WM_LBUTTONDOWN:
                    data = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    self._pressed = True
                    self._press_x = data.pt.x
                    self._press_y = data.pt.y
                elif w_param == WM_MOUSEMOVE:
                    pass  # 可扩展：按下期间检测移动
                elif w_param == WM_LBUTTONUP:
                    if self._pressed:
                        data = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                        dx = data.pt.x - self._press_x
                        dy = data.pt.y - self._press_y
                        dist = (dx * dx + dy * dy) ** 0.5
                        self._pressed = False
                        # 拖选阈值：移动距离 > 10px 视为选中操作
                        if dist > 10:
                            if self._on_select:
                                try:
                                    self._on_select(data.pt.x, data.pt.y)
                                except Exception as e:
                                    log.error(f"Mouse select callback failed: {e}")
            except Exception as e:
                log.debug(f"Mouse hook proc error: {e}")
        # 继续传递（不阻塞系统）；lParam 是指针值，须用 c_void_p 包装避免 64 位溢出
        return ctypes.windll.user32.CallNextHookEx(
            self._hook, n_code, w_param, ctypes.c_void_p(l_param)
        )

    def start(self, on_select: Callable) -> bool:
        """启动鼠标钩子（在独立线程中运行消息循环）"""
        try:
            if self._running:
                return True
            self._on_select = on_select
            self._running = True

            # 一次性声明类型（HHOOK 是 64 位指针；lParam 用 c_void_p 避免溢出）。
            # 注意：这些钩子函数 pywebview 不使用，声明 argtypes 不影响其内部调用。
            user32 = ctypes.windll.user32
            user32.SetWindowsHookExW.restype = ctypes.c_void_p
            user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC,
                                                 ctypes.c_void_p, ctypes.c_uint]
            user32.CallNextHookEx.restype = ctypes.c_longlong
            user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                              wintypes.WPARAM, ctypes.c_void_p]
            user32.UnhookWindowsHookEx.restype = ctypes.c_bool
            user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]

            def _run():
                try:
                    user32 = ctypes.windll.user32
                    kernel32 = ctypes.windll.kernel32
                    # WH_MOUSE_LL 钩子：hMod 必须有效；GetModuleHandleW(None) 返回 exe 模块句柄
                    hmod = kernel32.GetModuleHandleW(None)
                    self._hook = user32.SetWindowsHookExW(
                        WH_MOUSE_LL, self._callback, hmod, 0
                    )
                    if not self._hook:
                        # 兜底：传 NULL 模块句柄（LL 钩子允许）
                        log.warning("SetWindowsHookExW with module handle failed, retrying with NULL")
                        self._hook = user32.SetWindowsHookExW(
                            WH_MOUSE_LL, self._callback, None, 0
                        )
                    if not self._hook:
                        log.error("SetWindowsHookExW failed (both attempts)")
                        self._running = False
                        return
                    log.info("Mouse selection hook installed")
                    # 消息循环（钩子需要）
                    msg = wintypes.MSG()
                    while self._running:
                        r = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
                        if r == 0:      # WM_QUIT
                            break
                        if r == -1:
                            log.error("GetMessage failed")
                            break
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                except Exception as e:
                    log.error(f"Mouse hook thread error: {e}")
                finally:
                    self._running = False

            self._thread = threading.Thread(target=_run, daemon=True, name="MouseHookThread")
            self._thread.start()
            return True
        except Exception as e:
            log.error(f"Mouse hook start failed: {e}")
            return False

    def stop(self):
        """停止鼠标钩子"""
        try:
            self._running = False
            if self._hook:
                # 向钩子线程发 WM_QUIT 退出消息循环
                user32 = ctypes.windll.user32
                user32.PostThreadMessageW(
                    ctypes.windll.kernel32.GetCurrentThreadId(), 0x0012, 0, 0
                )
                user32.UnhookWindowsHookEx(self._hook)
                self._hook = None
            log.info("Mouse selection hook stopped")
        except Exception as e:
            log.error(f"Mouse hook stop failed: {e}")


# 全局实例
mouse_selection_hook = MouseSelectionHook()
