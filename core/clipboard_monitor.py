"""
Qingxin Translator - Clipboard Monitor
剪贴板监听：复制文本后自动触发翻译（"复制即翻译"）

- 后台线程每 500ms 轮询剪贴板内容（哈希对比）
- 检测到文本变化且距上次复制 > 2s → 回调翻译
- 过滤：纯数字/短文本(<2字符)/纯空白/URL/重复内容
"""

import hashlib
import re
import threading
import time
from typing import Callable, Optional

from core.logger import log

# 过滤规则：URL / 纯数字 / 纯空白
_URL_RE = re.compile(r'^https?://\S+$', re.IGNORECASE)
_NUM_RE = re.compile(r'^[\d\s.,%+-]+$')


class ClipboardMonitor:
    """剪贴板监听器"""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._on_text: Optional[Callable] = None
        self._last_hash = None
        self._last_time = 0.0
        self._interval = 0.5      # 轮询间隔（秒）
        self._min_gap = 2.0       # 两次触发最小间隔（秒）
        self._last_text = ""

    def start(self, on_text: Callable) -> bool:
        """启动剪贴板监听"""
        try:
            if self._running:
                return True
            self._on_text = on_text
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True, name="ClipboardMonitor")
            self._thread.start()
            log.info("Clipboard monitor started")
            return True
        except Exception as e:
            log.error(f"Clipboard monitor start failed: {e}")
            return False

    def stop(self):
        """停止剪贴板监听"""
        try:
            self._running = False
            log.info("Clipboard monitor stopped")
        except Exception as e:
            log.error(f"Clipboard monitor stop failed: {e}")

    def _run(self):
        try:
            import pyperclip
            while self._running:
                try:
                    text = pyperclip.paste()
                    if text and text.strip():
                        self._check_text(text)
                except Exception:
                    pass  # 剪贴板被占用等瞬时错误，静默跳过
                time.sleep(self._interval)
        except Exception as e:
            log.error(f"Clipboard monitor thread error: {e}")
        finally:
            self._running = False

    def _check_text(self, text: str):
        """检查剪贴板文本是否应触发翻译"""
        try:
            stripped = text.strip()
            # 过滤：太短
            if len(stripped) < 2:
                return
            # 过滤：纯数字 / URL / 纯空白
            if _NUM_RE.match(stripped) or _URL_RE.match(stripped):
                return
            # 过滤：重复内容（哈希相同且间隔 < 最小间隔）
            h = hashlib.md5(stripped.encode("utf-8", errors="ignore")).hexdigest()
            now = time.time()
            if h == self._last_hash and now - self._last_time < self._min_gap:
                return
            self._last_hash = h
            self._last_time = now
            # 触发翻译
            if self._on_text:
                try:
                    self._on_text(stripped)
                except Exception as e:
                    log.error(f"Clipboard on_text callback failed: {e}")
        except Exception as e:
            log.debug(f"Clipboard check error: {e}")


# 全局实例
clipboard_monitor = ClipboardMonitor()
