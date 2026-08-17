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


def _wait_modifiers_released(timeout=0.5):
    """等待所有修饰键松开（5ms 轮询）"""
    VKS = [0x11, 0x10, 0x12, 0x5B, 0x5C]
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not any(user32.GetAsyncKeyState(v) & 0x8000 for v in VKS):
            return
        time.sleep(0.005)
    time.sleep(0.01)


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

    # 等修饰键松开
    _wait_modifiers_released(0.5)

    # 清剪贴板（用 pyperclip，已验证可用）
    old_cb = None
    try:
        old_cb = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy("")

    # SendInput Ctrl+C
    arr = (INPUT * 4)(
        mk(VK_CONTROL, 0), mk(VK_C, 0),
        mk(VK_C, KEYEVENTF_KEYUP), mk(VK_CONTROL, KEYEVENTF_KEYUP),
    )
    user32.SendInput(4, arr, ctypes.sizeof(INPUT))

    # 等剪贴板有内容（最多 500ms，20ms 轮询）
    for _ in range(25):
        time.sleep(0.02)
        try:
            t = pyperclip.paste()
            if t and t.strip():
                return True
        except Exception:
            pass

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
