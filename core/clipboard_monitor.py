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
        self._processing = False  # 翻译处理中标志（抑制连锁触发）

    def start(self, on_text: Callable) -> bool:
        """启动剪贴板监听

        启动时把当前剪贴板内容标记为"已处理"——开启功能后只有剪贴板
        【更新】为新内容才触发翻译，不会因旧内容立即触发一次。
        """
        try:
            if self._running:
                return True
            self._on_text = on_text
            self._running = True
            # 记录当前剪贴板内容（视为已处理）
            try:
                import pyperclip
                cur = pyperclip.paste()
                if cur and cur.strip():
                    self._last_hash = hashlib.md5(
                        cur.strip().encode("utf-8", errors="ignore")).hexdigest()
                    self._last_time = time.time()
            except Exception:
                pass
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

    def mark_handled(self, text: str):
        """标记某文本已被处理（auto-copy 写入剪贴板时调用，避免连锁触发）"""
        try:
            stripped = (text or "").strip()
            if stripped:
                self._last_hash = hashlib.md5(stripped.encode("utf-8", errors="ignore")).hexdigest()
                self._last_time = time.time()
        except Exception:
            pass

    def _run(self):
        try:
            import pyperclip
            while self._running:
                try:
                    # 翻译处理中：跳过检测（避免 auto-copy 译文触发连锁翻译）
                    if self._processing:
                        time.sleep(self._interval)
                        continue
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
            # 去重：同一内容只触发一次（剪贴板内容不变则不重复翻译）
            # 关键：不依赖时间窗——用户复制后剪贴板保持该内容，轮询不应再次触发；
            # 只有内容变化（用户复制了新文本）才触发
            h = hashlib.md5(stripped.encode("utf-8", errors="ignore")).hexdigest()
            if h == self._last_hash:
                return
            self._last_hash = h
            self._last_time = time.time()
            # 触发翻译（处理期间抑制检测，防止 auto-copy 连锁）
            if self._on_text:
                self._processing = True
                try:
                    self._on_text(stripped)
                except Exception as e:
                    log.error(f"Clipboard on_text callback failed: {e}")
                finally:
                    self._processing = False
        except Exception as e:
            log.debug(f"Clipboard check error: {e}")


# 全局实例
clipboard_monitor = ClipboardMonitor()
