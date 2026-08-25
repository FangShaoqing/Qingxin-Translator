"""
Qingxin Translator - Selection Translator
划词翻译模块

智能方案：
1. 按快捷键时，先模拟 Ctrl+C 自动复制选中文本
2. 成功则直接翻译，失败则提示用户手动复制
"""

import time
import ctypes
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

    # 失败：Ctrl+C 已注入但剪贴板 1s 内无内容（无选区/目标应用对注入免疫如浏览器沙箱）
    log.debug("Ctrl+C injected but clipboard empty (1s) - no selection or app immune to injection")
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
