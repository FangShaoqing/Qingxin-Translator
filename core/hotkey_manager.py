"""
Qingxin Translator - Hotkey Manager
全局快捷键管理器（GetAsyncKeyState 轮询方案）

不依赖消息循环、隐藏窗口或 COM，纯 ctypes 轮询按键状态。
"""

import ctypes
import threading
from typing import Callable, Dict, Optional, Set, FrozenSet

from core.logger import log

user32 = ctypes.WinDLL('user32', use_last_error=True)

# 虚拟键码
VK_MAP = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
    'z': 0x5A, '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33,
    '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38,
    '9': 0x39, 'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77, 'f9': 0x78,
    'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B, 'space': 0x20,
    'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B, 'escape': 0x1B,
}

# 修饰键 VK 码
MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C}  # Shift, Ctrl, Alt, LWin, RWin


class HotkeyManager:
    """全局快捷键管理器（GetAsyncKeyState 轮询）"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._hotkeys: Dict[int, tuple] = {}       # id -> (hotkey_str, frozenset of vks)
        self._callbacks: Dict[int, Callable] = {}
        self._hotkey_id_counter = 100
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._initialized = True

    def start(self, hotkey_str: str, callback: Callable) -> bool:
        hotkey_id = self._hotkey_id_counter
        self._hotkey_id_counter += 1
        return self._register_hotkey(hotkey_str, callback, hotkey_id)

    def register(self, hotkey_str: str, callback: Callable) -> Optional[int]:
        hotkey_id = self._hotkey_id_counter
        self._hotkey_id_counter += 1
        if self._register_hotkey(hotkey_str, callback, hotkey_id):
            return hotkey_id
        return None

    def unregister(self, hotkey_id: int) -> bool:
        if hotkey_id in self._callbacks:
            del self._callbacks[hotkey_id]
            self._hotkeys.pop(hotkey_id, None)
            log.info(f"Hotkey {hotkey_id} unregistered")
            if not self._callbacks:
                self._stop_listener()
            return True
        return False

    def stop(self):
        self._stop_listener()
        self._callbacks.clear()
        self._hotkeys.clear()
        log.info("Hotkey manager stopped")

    def _stop_listener(self):
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _register_hotkey(self, hotkey_str: str, callback: Callable, hotkey_id: int) -> bool:
        try:
            vks = self._parse_hotkey(hotkey_str)
            if vks is None:
                log.error(f"Failed to parse hotkey: {hotkey_str}")
                return False

            self._hotkeys[hotkey_id] = (hotkey_str, vks)
            self._callbacks[hotkey_id] = callback

            if not self._running:
                self._start_listener()

            log.info(f"Hotkey registered: {hotkey_str} (id={hotkey_id})")
            return True
        except Exception as e:
            log.error(f"Failed to register hotkey '{hotkey_str}': {e}")
            return False

    def _start_listener(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="HotkeyPoll")
        self._thread.start()
        log.info("Hotkey poll thread started")

    def _poll_loop(self):
        """轮询按键状态"""
        fired = set()  # 防止重复触发：已触发的热键 ID

        while self._running and not self._stop_event.is_set():
            try:
                for hotkey_id, (hotkey_str, vks) in list(self._hotkeys.items()):
                    if self._all_keys_pressed(vks):
                        if hotkey_id not in fired:
                            fired.add(hotkey_id)
                            cb = self._callbacks.get(hotkey_id)
                            if cb:
                                log.info(f"Hotkey triggered: {hotkey_str} (id={hotkey_id})")
                                threading.Thread(target=cb, daemon=True).start()
                    else:
                        fired.discard(hotkey_id)
            except Exception as e:
                log.error(f"Hotkey poll error: {e}")

            # 50ms 轮询间隔
            self._stop_event.wait(timeout=0.05)

    def _all_keys_pressed(self, vks: FrozenSet[int]) -> bool:
        """检查所有按键是否同时按下"""
        for vk in vks:
            if not (user32.GetAsyncKeyState(vk) & 0x8000):
                return False
        return True

    def _parse_hotkey(self, hotkey_str: str) -> Optional[FrozenSet[int]]:
        """解析快捷键为 VK 码集合"""
        try:
            parts = [p.strip().lower() for p in hotkey_str.split("+")]
            vks = set()

            for part in parts:
                if part in ('ctrl', 'control'):
                    vks.add(0x11)  # VK_CONTROL
                elif part == 'shift':
                    vks.add(0x10)  # VK_SHIFT
                elif part == 'alt':
                    vks.add(0x12)  # VK_MENU
                elif part in ('cmd', 'win'):
                    vks.add(0x5B)  # VK_LWIN
                elif part in VK_MAP:
                    vks.add(VK_MAP[part])
                elif len(part) == 1:
                    vks.add(ord(part.upper()))
                else:
                    log.error(f"Unknown key: {part}")
                    return None

            if not vks:
                log.error("No keys found")
                return None

            return frozenset(vks)
        except Exception as e:
            log.error(f"Parse hotkey error: {e}")
            return None


hotkey_manager = HotkeyManager()
