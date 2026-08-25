"""
Qingxin Translator - Selection Translator
划词翻译模块

智能方案：
1. 按快捷键时，先模拟 Ctrl+C 自动复制选中文本
2. 成功则直接翻译，失败则提示用户手动复制
"""

import time
import ctypes
from ctypes import wintypes
from typing import Optional, Callable

from core.logger import log

user32 = ctypes.windll.user32


def _wait_modifiers_released(timeout=1.0) -> bool:
    """等待所有修饰键松开（5ms 轮询）。

    返回 True=已全部松开（并额外稳定等待 60ms，让目标应用菜单栏/焦点状态
    稳定后再注入）；False=超时仍按住（调用方应放弃注入——此时 SendInput
    注入 Ctrl+C 会被仍按住的 Alt/Ctrl 修饰，导致复制失败）。
    """
    VKS = [0x11, 0x10, 0x12, 0x5B, 0x5C]
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(user32.GetAsyncKeyState(v) & 0x8000 for v in VKS):
            time.sleep(0.06)  # 松开后稳定等待（菜单栏动画/焦点恢复）
            return True
        time.sleep(0.005)
    return False


_uia_auto = None  # comtypes UIAutomation 单例（复用，避免每次 COM 初始化开销）


def uia_get_selection() -> Optional[str]:
    """UI Automation 直接读取前台焦点元素选中文本（不注入按键）。

    对支持 UIA 文本模式的应用有效（记事本/Word/浏览器等）；不支持时
    （如 IDEA 未启用 Java Access Bridge）快速失败返回 None。
    使用 comtypes 生成的 UIAutomationClient 接口（vtable 由 comtypes 处理）。
    """
    global _uia_auto
    try:
        import comtypes.client
        from comtypes.gen.UIAutomationClient import (
            CUIAutomation, IUIAutomationTextPattern, UIA_TextPatternId)
        if _uia_auto is None:
            _uia_auto = comtypes.client.CreateObject(CUIAutomation)
        auto = _uia_auto
        focused = auto.GetFocusedElement()
        if not focused:
            return None
        pat = focused.GetCurrentPattern(UIA_TextPatternId)
        if not pat:
            return None
        try:
            text_pat = pat.QueryInterface(IUIAutomationTextPattern)
        except Exception:
            return None
        arr = text_pat.GetSelection()
        if not arr or arr.Length == 0:
            return None
        r = arr.GetElement(0)
        text = r.GetText(-1)
        return text or None
    except Exception:
        return None


def wait_user_copy(timeout=8.0) -> Optional[str]:
    """等待用户手动 Ctrl+C（目标应用对注入免疫时的兜底）。

    返回复制的文本（剪贴板变化且非空）；超时返回 None。
    """
    try:
        import pyperclip
        base = ""
        try:
            base = pyperclip.paste() or ""
        except Exception:
            pass
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.2)
            try:
                t = pyperclip.paste()
                if t and t.strip() and t != base:
                    return t.strip()
            except Exception:
                pass
        return None
    except Exception:
        return None


def _try_send_ctrl_c() -> bool:
    """等修饰键松开 → 清剪贴板 → SendInput Ctrl+C → 等剪贴板变化"""
    import pyperclip

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_C = 0x43

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_uint), ("time", ctypes.c_uint),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", ctypes.c_long), ("dy", ctypes.c_long),
            ("mouseData", ctypes.c_uint), ("dwFlags", ctypes.c_uint),
            ("time", ctypes.c_uint), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
        ]
    class U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_uint), ("union", U)]

    def mk(vk, flags=0):
        i = INPUT()
        i.type = INPUT_KEYBOARD
        i.union.ki.wVk = vk
        i.union.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        i.union.ki.dwFlags = flags
        return i

    # 等修饰键松开（超时 0.8s）；用户长按快捷键时不注入（修饰键仍在按下
    # 会污染注入的 Ctrl+C，Alt 还会激活目标应用菜单栏致复制失败）
    if not _wait_modifiers_released(0.8):
        log.debug("Ctrl+C injection skipped: modifiers still pressed")
        return False
    # 主键（X）通常与修饰键同时松开；仅当仍按下时等待
    # （快速检测主键状态，避免固定 sleep 延迟）
    for _ in range(10):
        if not (user32.GetAsyncKeyState(0x58) & 0x8000):  # VK_X
            break
        time.sleep(0.01)

    # 记录剪贴板旧内容
    old_cb = None
    try:
        old_cb = pyperclip.paste()
    except Exception:
        pass

    # 清剪贴板
    try:
        pyperclip.copy("")
    except Exception:
        pass

    # SendInput Ctrl+C（注意：不要注入 Alt 键击，会激活目标应用菜单栏/取消选中）
    arr = (INPUT * 4)(
        mk(VK_CONTROL, 0), mk(VK_C, 0),
        mk(VK_C, KEYEVENTF_KEYUP), mk(VK_CONTROL, KEYEVENTF_KEYUP),
    )
    user32.SendInput(4, arr, ctypes.sizeof(INPUT))

    # 等剪贴板有内容（最多 1000ms，20ms 轮询）
    for _ in range(50):
        time.sleep(0.02)
        try:
            t = pyperclip.paste()
            if t and t.strip():
                return True
        except Exception:
            pass

    # 失败：Ctrl+C 已注入但剪贴板 1s 内无内容。记录前台窗口信息以便定位
    # （无选区 / 目标应用对注入免疫如浏览器沙箱 / 管理员窗口 UIPI 拦截）
    try:
        hwnd = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        exe_path = ""
        try:
            # 用局部 WinDLL + 显式签名（禁止改全局 ctypes.windll 的函数签名）
            k32 = ctypes.WinDLL('kernel32')
            k32.OpenProcess.restype = ctypes.c_void_p
            k32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
            k32.QueryFullProcessImageNameW.restype = ctypes.c_int
            k32.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p, ctypes.c_uint, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint)]
            k32.CloseHandle.argtypes = [ctypes.c_void_p]
            h = k32.OpenProcess(0x0400 | 0x0010, False, pid.value)  # QUERY_LIMITED|VM_READ
            if h:
                buf = ctypes.create_unicode_buffer(1024)
                sz = ctypes.c_uint(1024)
                if k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(sz)):
                    exe_path = buf.value
                k32.CloseHandle(h)
        except Exception:
            pass
        log.warning(f"Ctrl+C injected but clipboard empty: fg_hwnd={hwnd} pid={pid.value} "
                    f"title={title.value!r} exe={exe_path}")
    except Exception as e:
        log.debug(f"foreground window probe failed: {e}")
    # 失败，恢复
    if old_cb:
        try:
            pyperclip.copy(old_cb)
        except Exception:
            pass
    return False


class SelectionTranslator:
    _instance = None

    def __new__(cls, *a, **kw):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._translate_callback = None
        self._initialized = True
        log.info("SelectionTranslator initialized")

    def set_translate_callback(self, cb):
        self._translate_callback = cb

    def get_selected_text(self) -> Optional[str]:
        log.info("Selection: auto-copy...")
        # 1) UIA 直读选中文本（不注入按键——对 IDEA 等 Java 应用/浏览器
        #    SendInput 注入无效，UIA 在支持的应用上最可靠）
        try:
            t = uia_get_selection()
            if t:
                log.info(f"Selection: got via UIA ({len(t)} chars)")
                return t.strip()
        except Exception:
            pass
        # 2) SendInput Ctrl+C（注入）
        if _try_send_ctrl_c():
            import pyperclip
            text = pyperclip.paste()
            if text and text.strip():
                return text.strip()
        log.info("Selection: auto-copy failed")
        return None

    def probe_selection(self) -> Optional[str]:
        """探测当前是否有选中文本（复制到剪贴板后【恢复原剪贴板内容】）

        用于悬浮按钮显示前的判断：拖选文本才有内容，空白拖动/拖动窗口无内容。
        探测完成后剪贴板恢复原样，不干扰用户剪贴板。
        """
        try:
            import pyperclip
            old_cb = None
            try:
                old_cb = pyperclip.paste()
            except Exception:
                pass
            if _try_send_ctrl_c():
                text = pyperclip.paste()
                # 恢复原剪贴板内容（探测完不保留选区）
                try:
                    if old_cb:
                        pyperclip.copy(old_cb)
                    else:
                        pyperclip.copy("")
                except Exception:
                    pass
                if text and text.strip():
                    return text.strip()
            else:
                # 复制失败：恢复剪贴板（_try_send_ctrl_c 失败时会自己恢复，这里兜底）
                try:
                    if old_cb:
                        pyperclip.copy(old_cb)
                except Exception:
                    pass
            return None
        except Exception as e:
            log.debug(f"probe_selection error: {e}")
            return None

    def trigger_selection_translate(self) -> Optional[dict]:
        log.info("Selection translate triggered")
        text = self.get_selected_text()
        if not text:
            return {"success": False, "error": "自动复制未生效，请先 Ctrl+C 复制，再按快捷键"}
        log.info(f"Translating: '{text[:50]}...' (len={len(text)})")
        if self._translate_callback:
            try:
                return self._translate_callback(text)
            except Exception as e:
                log.error(f"Translation error: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "翻译回调未设置"}

    def start_hook(self):
        log.info("SelectionTranslator: ready")

    def stop_hook(self):
        pass

    @property
    def is_available(self):
        return self._translate_callback is not None


selection_translator = SelectionTranslator()
