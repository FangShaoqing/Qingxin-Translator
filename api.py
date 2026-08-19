"""
Qingxin Translator - Python/JS API Bridge
pywebview API 桥接模块
"""

import json
from pathlib import Path
from typing import Optional, List

import webview
from app.config import config
from app.constants import APP_NAME, APP_VERSION
from core.logger import log
from core.translator import translator_manager
from core.llm_translator import llm_translator
from core.language_detector import language_detector
from models.database import init_db, close_db
from models.history import History


class Api:
    """Python与JS通信的API类"""
    
    def __init__(self):
        self._window = None
        self._bubble_window = None
        self._hotkey_manager = None
        self._bubble_timer = None
        self._bubble_visible = False  # 自维护气泡可见状态
        self._bubble_pos = None       # 热键触发瞬间记录的鼠标位置 (x, y)
        self._bubble_transparent = False  # 气泡窗口不透明（真透明在 WebView2 不可靠，渲染成黑底）
    
    def _capture_mouse_pos(self):
        """记录当前鼠标位置（热键触发瞬间调用，供翻译完成后定位气泡）"""
        try:
            import ctypes
            from ctypes import wintypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            self._bubble_pos = (pt.x, pt.y)
            log.info(f"Mouse position captured: {self._bubble_pos}")
        except Exception as e:
            log.debug(f"Capture mouse pos failed: {e}")
            self._bubble_pos = None
        
    def set_window(self, window):
        """设置pywebview窗口引用"""
        self._window = window
    
    def set_bubble_window(self, window):
        """设置划词翻译气泡窗口引用"""
        self._bubble_window = window
    
    # ========== 划词翻译气泡 ==========
    
    def _safe_js(self, code: str):
        """向气泡窗口安全推送 JS（失败静默）"""
        if not self._bubble_window:
            return
        try:
            self._bubble_window.evaluate_js(code)
        except Exception as e:
            log.debug(f"Bubble evaluate_js failed: {e}")
    
    def _find_bubble_hwnd(self):
        """查找气泡窗口的 Win32 句柄"""
        try:
            # 优先：window.native.Handle（pywebview 后端设置的本地窗口对象，最可靠）
            try:
                native = getattr(self._bubble_window, 'native', None)
                if native is not None:
                    handle = getattr(native, 'Handle', None)
                    if handle is not None:
                        try:
                            hwnd = handle.ToInt64()
                        except Exception:
                            hwnd = int(handle)
                        if hwnd and hwnd > 0:
                            return hwnd
            except Exception as e:
                log.debug(f"Bubble native handle failed: {e}")
            
            # 其次：从 pywebview 窗口对象的 GUI 句柄获取
            try:
                gui = getattr(self._bubble_window, 'gui', None)
                if gui is not None:
                    handle = getattr(gui, 'Handle', None)
                    if handle is not None:
                        try:
                            hwnd = handle.ToInt64()
                        except Exception:
                            hwnd = int(handle)
                        if hwnd and hwnd > 0:
                            return hwnd
            except Exception as e:
                log.debug(f"Bubble gui handle failed: {e}")
            
            # 兜底：按窗口标题查找（包含匹配）
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            
            hwnd = user32.FindWindowW(None, "QingxinBubble")
            if hwnd:
                return hwnd
            
            # 备用：枚举窗口查找（兼容旧标题"翻译气泡"）
            found = [0]
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
            
            def enum_callback(hwnd_l, _):
                length = user32.GetWindowTextLengthW(hwnd_l)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd_l, buf, length + 1)
                    if "QingxinBubble" in buf.value or "翻译气泡" in buf.value:
                        found[0] = hwnd_l
                return True
            
            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
            return found[0]
        except Exception:
            return 0
    
    def _win32_show_bubble(self, x: int, y: int) -> bool:
        """用 Win32 API 显示并移动气泡窗口"""
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = self._find_bubble_hwnd()
            if not hwnd:
                log.warning("Bubble hwnd not found")
                return False
            
            SW_SHOW = 5
            SW_RESTORE = 9
            HWND_TOPMOST = -1
            
            # 强制窗口不透明（仅非透明窗口需要；透明窗口依赖 per-pixel alpha，不能强制）
            if not self._bubble_transparent:
                try:
                    GWL_EXSTYLE = -20
                    WS_EX_LAYERED = 0x00080000
                    LWA_ALPHA = 0x00000002
                    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                    if ex_style & WS_EX_LAYERED:
                        # 设置 alpha=255（完全不透明）
                        user32.SetLayeredWindowAttributes(hwnd, 0, 255, LWA_ALPHA)
                        log.info("Bubble alpha forced to opaque")
                except Exception as e:
                    log.debug(f"Bubble alpha fix failed: {e}")
            
            # 移除任务栏图标（WS_EX_TOOLWINDOW），只显示在屏幕上
            try:
                GWL_EXSTYLE = -20
                WS_EX_TOOLWINDOW = 0x00000080
                current = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current | WS_EX_TOOLWINDOW)
            except Exception:
                pass
            
            user32.ShowWindow(hwnd, SW_SHOW)
            user32.ShowWindow(hwnd, SW_RESTORE)
            
            # 置顶（SetWindowPos 只做置顶，不移动）
            # 注意：不要声明 argtypes——ctypes.windll 是全局共享的，
            # pywebview 内部 SetWindowPos(handle, None, x, y, None, None, flags) 依赖默认的 None→NULL 转换
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002)  # NOSIZE|NOMOVE
            
            # 移动窗口：读取当前尺寸（JS 已 resize 后的值），避免显示时闪大气泡
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w <= 0 or h <= 0:
                w, h = 120, 60
            
            moved = user32.MoveWindow(hwnd, x, y, w, h, True)
            log.info(f"Bubble moved to ({x}, {y}) size={w}x{h}, ok={moved}")
            return True
        except Exception as e:
            log.debug(f"Win32 bubble show failed: {e}")
            return False
    
    def _win32_hide_bubble(self) -> bool:
        """用 Win32 API 隐藏气泡窗口"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = self._find_bubble_hwnd()
            if not hwnd:
                return False
            SW_HIDE = 0
            user32.ShowWindow(hwnd, SW_HIDE)
            return True
        except Exception as e:
            log.debug(f"Win32 bubble hide failed: {e}")
            return False
    
    def resize_bubble(self, width: int, height: int) -> None:
        """按内容自适应调整气泡窗口尺寸（保持当前位置）"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = self._find_bubble_hwnd()
            if not hwnd:
                log.warning(f"resize_bubble: hwnd not found (w={width}, h={height})")
                return
            # 读取当前位置
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            # 调整尺寸（保持左上角不变）
            ok = user32.MoveWindow(hwnd, rect.left, rect.top, width, height, True)
            # 验证实际尺寸（MoveWindow 后立即读回）
            rect2 = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect2))
            actual_w = rect2.right - rect2.left
            actual_h = rect2.bottom - rect2.top
            log.info(f"Bubble resize: target={width}x{height}, actual={actual_w}x{actual_h}, pos=({rect.left},{rect.top}), ok={ok}")
        except Exception as e:
            log.error(f"Bubble resize failed: {e}")

    def show_bubble(self, source_text: str, translation: str) -> None:
        """在鼠标附近显示翻译气泡，5 秒后自动隐藏；气泡不可用时降级到主窗口显示"""
        if not self._bubble_window:
            log.warning("Bubble window not available, falling back to main window")
            self._fallback_show_main(source_text, translation)
            return
        
        # 取消之前的自动隐藏定时器
        if self._bubble_timer:
            self._bubble_timer.cancel()
            self._bubble_timer = None
        
        # 推送内容到气泡
        import json as _json
        safe_source = _json.dumps(source_text)
        safe_translation = _json.dumps(translation)
        self._safe_js(
            f"window.__setBubbleContent && window.__setBubbleContent({safe_source}, {safe_translation})"
        )
        
        # 等待 JS 端 fitBubbleHeight 完成 resize（异步 api 调用需要时间），
        # 让气泡以正确尺寸显示，避免"先小后大"的跳变
        import time as _time
        _time.sleep(0.15)
        
        # 定位到鼠标位置（优先使用热键触发瞬间记录的位置）
        try:
            import ctypes
            from ctypes import wintypes
            
            if self._bubble_pos:
                # 使用触发时记录的位置（用户选中文本时的鼠标位置）
                pt_x, pt_y = self._bubble_pos
                self._bubble_pos = None  # 用完即清
            else:
                # 兜底：获取当前鼠标位置
                class POINT(ctypes.Structure):
                    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
                pt = POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                pt_x, pt_y = pt.x, pt.y
            
            # 气泡窗口初始尺寸（JS 自适应后由 resize_bubble 修正）
            width = 120
            height = 60
            
            # 屏幕尺寸
            screen_w = ctypes.windll.user32.GetSystemMetrics(0)
            screen_h = ctypes.windll.user32.GetSystemMetrics(1)
            
            # 默认放在鼠标右下（偏移 16px），超界则翻转到左侧/上方
            x = pt_x + 16
            y = pt_y + 16
            if x + width > screen_w:
                x = pt_x - width - 16
            if y + height > screen_h:
                y = pt_y - height - 16
            x = max(0, x)
            y = max(0, y)
            
            # 用 Win32 显示 + 定位（最可靠，不依赖 pywebview 事件）
            if not self._win32_show_bubble(x, y):
                # 兜底：pywebview 方法
                try:
                    self._bubble_window.show()
                    self._bubble_window.restore()
                    self._bubble_window.move(x, y)
                except Exception as e:
                    log.debug(f"pywebview bubble show fallback failed: {e}")
            
            # 验证气泡是否真的显示了（句柄存在且可见）
            import ctypes as _ctypes
            user32_ = _ctypes.windll.user32
            bubble_hwnd = self._find_bubble_hwnd()
            if not bubble_hwnd or not user32_.IsWindowVisible(bubble_hwnd):
                log.warning("Bubble failed to show, falling back to main window")
                self._fallback_show_main(source_text, translation)
                return
            
            # 检查气泡窗口是否真的可见（透明窗口跳过 alpha 检查——per-pixel alpha 读取值不可靠）
            if not self._bubble_transparent:
                try:
                    import ctypes as _ct
                    GWL_EXSTYLE = -20
                    WS_EX_LAYERED = 0x00080000
                    LWA_ALPHA = 0x00000002
                    ex_style = user32_.GetWindowLongW(bubble_hwnd, GWL_EXSTYLE)
                    if ex_style & WS_EX_LAYERED:
                        # 读取 alpha 值
                        alpha = _ct.c_ubyte(0)
                        user32_.GetLayeredWindowAttributes(bubble_hwnd, None, _ct.byref(alpha), None)
                        if alpha.value == 0:
                            log.warning("Bubble is transparent (alpha=0), forcing opaque")
                            user32_.SetLayeredWindowAttributes(bubble_hwnd, 0, 255, LWA_ALPHA)
                            # 强制后再次检查
                            user32_.GetLayeredWindowAttributes(bubble_hwnd, None, _ct.byref(alpha), None)
                            if alpha.value == 0:
                                log.warning("Bubble still transparent, falling back to main window")
                                self._fallback_show_main(source_text, translation)
                                return
                except Exception as e:
                    log.debug(f"Bubble transparency check failed: {e}")
            
            self._bubble_visible = True
            log.info(f"Bubble shown at ({x}, {y})")
            
            # 显示后延迟重新推送内容（窗口隐藏时 WebView2 可能未就绪，evaluate_js 会失败）
            # 二次推送确保内容可见，避免空气泡
            def _re_push():
                try:
                    self._safe_js(
                        f"window.__setBubbleContent && window.__setBubbleContent({safe_source}, {safe_translation})"
                    )
                    # 验证内容已设置（读取气泡页面返回值）
                    log.info("Bubble content re-pushed after show")
                    
                    # 诊断：验证气泡页面是否真实渲染（查询 DOM 内容 + 窗口矩形）
                    try:
                        import ctypes as _ct2
                        u32 = _ct2.windll.user32
                        # 窗口矩形（确认在屏幕内）
                        class RECT(_ct2.Structure):
                            _fields_ = [("left", _ct2.c_long), ("top", _ct2.c_long),
                                        ("right", _ct2.c_long), ("bottom", _ct2.c_long)]
                        rect = RECT()
                        h = self._find_bubble_hwnd()
                        if h:
                            u32.GetWindowRect(h, _ct2.byref(rect))
                            screen_w = u32.GetSystemMetrics(0)
                            screen_h = u32.GetSystemMetrics(1)
                            log.info(f"Bubble rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom}), screen: {screen_w}x{screen_h}")
                        # 页面渲染状态
                        self._safe_js(
                            "console.log('Bubble DOM check:', "
                            "document.getElementById('bubble-translation').textContent)"
                        )
                    except Exception as e:
                        log.debug(f"Bubble diagnostic failed: {e}")
                except Exception as e:
                    log.debug(f"Bubble re-push failed: {e}")
            import threading as _threading
            _threading.Timer(0.3, _re_push).start()
            
        except Exception as e:
            log.debug(f"Bubble positioning failed: {e}")
            self._fallback_show_main(source_text, translation)
            return
        
        # 5 秒后自动隐藏
        import threading
        self._bubble_timer = threading.Timer(5.0, self.hide_bubble)
        self._bubble_timer.daemon = True
        self._bubble_timer.start()
        
        log.info(f"Bubble shown: '{source_text[:30]}...' -> '{translation[:30]}...'")
    
    def bubble_interacting(self, active: bool) -> None:
        """
        气泡交互状态（由气泡页面 JS 调用）
        - 鼠标悬停/选中内容时：暂停自动隐藏
        - 鼠标移开：恢复自动隐藏计时
        """
        try:
            if active:
                # 鼠标在气泡上，取消自动隐藏定时器（气泡保持显示）
                if self._bubble_timer:
                    self._bubble_timer.cancel()
                    self._bubble_timer = None
                log.debug("Bubble: mouse entered, auto-hide paused")
            else:
                # 鼠标移开，重新启动自动隐藏
                if self._bubble_visible and not self._bubble_timer:
                    import threading
                    self._bubble_timer = threading.Timer(3.0, self.hide_bubble)
                    self._bubble_timer.daemon = True
                    self._bubble_timer.start()
                log.debug("Bubble: mouse left, auto-hide resumed")
        except Exception as e:
            log.debug(f"Bubble interacting error: {e}")
    
    def show_bubble_error(self, message: str) -> None:
        """在气泡中显示错误信息"""
        if not self._bubble_window:
            return
        import json as _json
        safe_msg = _json.dumps(message)
        self._safe_js(f"window.__setBubbleError && window.__setBubbleError({safe_msg})")
        
        # 显示（保持在当前位置，或居中屏幕）
        try:
            import ctypes
            from ctypes import wintypes
            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            if not self._win32_show_bubble(pt.x + 16, pt.y + 16):
                try:
                    self._bubble_window.show()
                    self._bubble_window.restore()
                except Exception:
                    pass
            self._bubble_visible = True
        except Exception:
            pass
        
        import threading
        if self._bubble_timer:
            self._bubble_timer.cancel()
        self._bubble_timer = threading.Timer(4.0, self.hide_bubble)
        self._bubble_timer.daemon = True
        self._bubble_timer.start()
    
    def _fallback_show_main(self, source_text: str, translation: str) -> None:
        """降级方案：气泡不可用时，显示主窗口并推送结果"""
        log.info("Fallback: showing main window with result")
        try:
            # 显示主窗口
            if self._window:
                try:
                    self._window.show()
                    self._window.restore()
                except Exception:
                    pass
                # 同步主窗口状态
                try:
                    import main as main_module
                    main_module._window_visible = True
                except Exception:
                    pass
                # 推送结果到主窗口
                self._push_selection_result(source_text, translation)
        except Exception as e:
            log.error(f"Fallback show main failed: {e}")
    
    def hide_bubble(self) -> None:
        """隐藏气泡窗口"""
        if self._bubble_timer:
            self._bubble_timer.cancel()
            self._bubble_timer = None
        
        # 用自维护状态判断，避免依赖 window.hidden（该属性不会随 show/hide 更新）
        if not self._bubble_visible:
            # 仍然尝试 Win32 隐藏（保险）
            self._win32_hide_bubble()
            return
        
        # Win32 隐藏（最可靠）
        hidden = self._win32_hide_bubble()
        if not hidden:
            # 兜底：pywebview 方法
            try:
                self._bubble_window.hide()
            except Exception as e:
                log.debug(f"pywebview bubble hide fallback failed: {e}")
        
        self._bubble_visible = False
        log.info("Bubble hidden")
    
    def get_app_info(self) -> dict:
        """获取应用信息"""
        import sys
        # 仅开发环境（未打包）标记，用于显示诊断功能
        is_dev = not getattr(sys, 'frozen', False)
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "is_dev": is_dev
        }
    
    def open_log_file(self) -> dict:
        """
        打开日志文件（仅开发环境可用，用于反馈 BUG）
        正式打包版本返回失败，不暴露此功能
        """
        import sys
        if getattr(sys, 'frozen', False):
            return {"success": False, "error": "开发环境专用功能"}
        
        try:
            import os
            from core.logger import log
            log_file = log.get_log_file()
            if os.path.exists(str(log_file)):
                os.startfile(str(log_file))  # 用默认文本编辑器打开
                return {"success": True}
            return {"success": False, "error": "日志文件不存在"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def translate(self, text: str) -> dict:
        """翻译文本（流式显示）"""
        if not text or not text.strip():
            return {"success": False, "error": "请输入要翻译的文本"}
        
        log.info(f"Translate request: '{text[:50]}...' (len={len(text)})")
        
        try:
            # 检测语言
            lang = language_detector.detect(text)
            log.info(f"Detected language: '{lang}' for text: '{text}'")
            
            # 确定目标语言（中英互译）
            if lang == "zh":
                target_lang = "en"
            else:
                target_lang = "zh"
            
            log.info(f"Translation direction: {lang} -> {target_lang}")
            
            # 使用流式翻译，实时推送到前端
            from core.llm_translator import llm_translator
            
            accumulated_text = []
            
            def on_chunk(chunk: str):
                accumulated_text.append(chunk)
                # 通过 evaluate_js 实时推送片段到前端
                safe_chunk = chunk.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "")
                try:
                    if self._window:
                        self._window.evaluate_js(
                            f"window.__onTranslateChunk && window.__onTranslateChunk('{safe_chunk}')"
                        )
                except Exception:
                    pass  # 推送失败不影响翻译
            
            result = llm_translator.translate_stream(text, lang, target_lang, on_chunk)
            
            if result.success:
                log.info(f"Translation success: '{result.translated_text[:50]}...'")
                
                # 通知前端流式传输完成
                try:
                    if self._window:
                        self._window.evaluate_js("window.__onTranslateDone && window.__onTranslateDone()")
                except Exception:
                    pass
                
                # 自动复制译文（如果开启）
                self._auto_copy_result(result.translated_text)
                
                # 保存到历史记录
                History.add(
                    source_text=text,
                    translated_text=result.translated_text,
                    source_lang=result.source_lang,
                    target_lang=result.target_lang,
                    engine=result.engine
                )
                
                return {
                    "success": True,
                    "translation": result.translated_text,
                    "source_lang": result.source_lang,
                    "target_lang": result.target_lang
                }
            else:
                # 主引擎失败 → 降级到 Bing 备用引擎
                # 仅当流式未推送任何内容时才降级（避免与已输出内容冲突）
                if not accumulated_text:
                    log.warning(f"LLM stream failed, falling back to Bing: {result.error_message}")
                    fallback = self._translate_with_fallback(text, lang, target_lang)
                    if fallback.get("success"):
                        # 推送 Bing 结果到前端（整段）
                        bing_text = fallback.get("translation", "")
                        try:
                            if self._window:
                                self._window.evaluate_js(
                                    f"window.__onTranslateChunk && window.__onTranslateChunk({json.dumps(bing_text)})"
                                )
                                self._window.evaluate_js("window.__onTranslateDone && window.__onTranslateDone()")
                        except Exception:
                            pass
                        
                        # 自动复制译文（如果开启）
                        self._auto_copy_result(bing_text)
                        
                        # 保存到历史记录（标记为 bing 引擎）
                        History.add(
                            source_text=text,
                            translated_text=bing_text,
                            source_lang=fallback.get("source_lang", lang),
                            target_lang=fallback.get("target_lang", target_lang),
                            engine="bing"
                        )
                        return fallback
                
                # 通知前端翻译失败
                try:
                    if self._window:
                        safe_err = result.error_message.replace("\\", "\\\\").replace("'", "\\'")
                        self._window.evaluate_js(
                            f"window.__onTranslateError && window.__onTranslateError('{safe_err}')"
                        )
                except Exception:
                    pass
                return {"success": False, "error": result.error_message}
                
        except Exception as e:
            log.error(f"Translation failed: {e}", exc_info=True)
            
            # 尝试 Bing 兜底（流式路径异常时）
            try:
                lang2 = language_detector.detect(text)
                target2 = "en" if lang2 == "zh" else "zh"
                fallback = self._translate_with_fallback(text, lang2, target2)
                if fallback.get("success"):
                    try:
                        if self._window:
                            self._window.evaluate_js(
                                f"window.__onTranslateChunk && window.__onTranslateChunk({json.dumps(fallback.get('translation', ''))})"
                            )
                            self._window.evaluate_js("window.__onTranslateDone && window.__onTranslateDone()")
                    except Exception:
                        pass
                    return fallback
            except Exception:
                pass
            
            # 通知前端翻译失败
            try:
                if self._window:
                    safe_err = str(e).replace("\\", "\\\\").replace("'", "\\'")
                    self._window.evaluate_js(
                        f"window.__onTranslateError && window.__onTranslateError('{safe_err}')"
                    )
            except Exception:
                pass
            
            return {"success": False, "error": str(e)}
    
    def _auto_copy_result(self, translation: str) -> None:
        """翻译成功后自动复制译文（auto_copy 开启时）"""
        try:
            if not config.get("auto_copy", False):
                return
            if not translation:
                return
            import pyperclip
            pyperclip.copy(translation)
            log.info(f"Translation auto-copied: '{translation[:50]}...'")
        except Exception as e:
            log.debug(f"Auto copy failed: {e}")
    
    def _translate_with_fallback(self, text: str, source_lang: str, target_lang: str,
                                 is_mixed: bool = False) -> dict:
        """
        使用 Bing 备用引擎翻译（主引擎失败时调用）
        
        Returns:
            dict: 与 translate 返回格式一致
        """
        try:
            from core.bing_translator import bing_translator
            result = bing_translator.translate(text, source_lang, target_lang, is_mixed=is_mixed)
            if result.success:
                log.info(f"Bing fallback success: '{result.translated_text[:50]}...'")
                return {
                    "success": True,
                    "translation": result.translated_text,
                    "source_lang": result.source_lang,
                    "target_lang": result.target_lang,
                    "engine": "bing"
                }
            log.warning(f"Bing fallback failed: {result.error_message}")
            return {"success": False, "error": result.error_message}
        except Exception as e:
            log.error(f"Bing fallback error: {e}")
            return {"success": False, "error": str(e)}
    
    # ========== 图片翻译（OCR） ==========
    
    def ocr_image(self, image_base64: str) -> dict:
        """
        识别图片中的文字（Windows 自带 OCR）
        
        Args:
            image_base64: 图片的 base64 数据（不含 data: 前缀）
            
        Returns:
            dict: {"success": bool, "text": str, "error": str}
        """
        try:
            import base64
            
            if not image_base64:
                return {"success": False, "error": "图片数据为空"}
            
            # 解码 base64
            image_bytes = base64.b64decode(image_base64)
            if not image_bytes:
                return {"success": False, "error": "图片数据无效"}
            
            log.info(f"OCR request: {len(image_bytes)} bytes")
            
            from core.ocr import ocr_engine
            text = ocr_engine.ocr_image(image_bytes)
            
            if not text:
                return {"success": False, "error": "未识别到文字，请换一张更清晰的图片"}
            
            return {"success": True, "text": text}
            
        except Exception as e:
            log.error(f"OCR error: {e}", exc_info=True)
            return {"success": False, "error": f"OCR 识别失败: {e}"}
    
    def translate_image(self, image_base64: str) -> dict:
        """
        图片翻译：OCR 识别 → 自动翻译
        
        Args:
            image_base64: 图片的 base64 数据（不含 data: 前缀）
            
        Returns:
            dict: 翻译结果（含识别文本）
        """
        try:
            ocr_result = self.ocr_image(image_base64)
            if not ocr_result.get("success"):
                return ocr_result
            
            text = ocr_result.get("text", "")
            
            # 复用主翻译流程
            result = self.translate(text)
            if result.get("success"):
                result["source_text"] = text
            return result
            
        except Exception as e:
            log.error(f"translate_image error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def get_history(self, keyword: Optional[str] = None) -> List[dict]:
        """获取翻译历史"""
        try:
            if keyword:
                records = History.search(keyword)
            else:
                records = History.get_recent()
            
            return [record.to_dict() for record in records]
        except Exception as e:
            return []
    
    def clear_history(self) -> dict:
        """清空历史记录"""
        try:
            History.clear_all()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_history(self, record_id: int) -> dict:
        """删除单条历史记录"""
        try:
            History.delete_by_id(record_id)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_settings(self) -> dict:
        """获取设置"""
        return config.to_dict()
    
    def set_startup(self, enable: bool) -> dict:
        """设置开机自启动（操作 Windows 注册表 + 更新配置）"""
        try:
            from core.startup_manager import set_launch_at_startup
            success = set_launch_at_startup(enable)
            if success:
                log.info(f"Launch at startup set to: {enable}")
                return {"success": True}
            else:
                return {"success": False, "error": "设置开机自启失败"}
        except Exception as e:
            log.error(f"set_startup error: {e}")
            return {"success": False, "error": str(e)}
    
    def save_settings(self, settings: dict) -> dict:
        """保存设置"""
        try:
            # engine 固定为 online
            settings["engine"] = "online"
            
            # 检查快捷键是否变化
            old_hotkey = config.get("hotkey", "")
            old_sel_hotkey = config.get("selection_translate_hotkey", "")
            
            for key, value in settings.items():
                # 跳过空字符串值，避免覆盖已保存的配置
                if value == "" and key in ("api_url", "api_key", "api_model"):
                    continue
                config.set(key, value)
            config.save()
            
            # 只在快捷键实际变化时重新注册
            new_hotkey = config.get("hotkey", "")
            new_sel_hotkey = config.get("selection_translate_hotkey", "")
            if new_hotkey != old_hotkey or new_sel_hotkey != old_sel_hotkey:
                import threading
                threading.Thread(target=self._update_hotkey, args=(new_hotkey, new_sel_hotkey), daemon=True).start()
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _update_hotkey(self, hotkey: str, selection_hotkey: str = ""):
        """更新全局快捷键"""
        try:
            from core.hotkey_manager import hotkey_manager
            hotkey_manager.stop()
            
            if hotkey:
                try:
                    import main as main_module
                    hotkey_manager.start(hotkey, main_module._toggle_window)
                except ImportError:
                    hotkey_manager.start(hotkey, self._toggle_window)
            
            if selection_hotkey:
                try:
                    import main as main_module
                    hotkey_manager.register(selection_hotkey, main_module._trigger_selection_translate)
                except ImportError:
                    hotkey_manager.register(selection_hotkey, self._trigger_selection_translate_local)
                    
            log.info(f"Hotkeys updated: main={hotkey}, selection={selection_hotkey}")
        except Exception as e:
            log.error(f"Failed to update hotkey: {e}")
    
    def _toggle_window(self):
        """切换窗口显示/隐藏（备用方案，当无法使用 main._toggle_window 时使用）"""
        try:
            window = self._window or (webview.windows[0] if webview.windows else None)
            if not window:
                return
            
            if window.hidden:
                # 显示窗口
                window.show()
                window.restore()
                # 更新 main 模块状态
                try:
                    import main as main_module
                    main_module._window_visible = True
                except ImportError:
                    pass
                log.info("Toggle: window shown")
            else:
                # 隐藏窗口
                minimize_to_tray = config.get("minimize_to_tray", True)
                if minimize_to_tray:
                    window.hide()
                    try:
                        import main as main_module
                        main_module._window_visible = False
                    except ImportError:
                        pass
                    log.info("Toggle: window hidden to tray")
                else:
                    window.minimize()
                    log.info("Toggle: window minimized")
        except Exception as e:
            log.error(f"Toggle window error: {e}")
    
    def _trigger_selection_translate_local(self):
        """划词翻译（备用方案）"""
        self.translate_selection()
    
    def test_connection(self, api_url: str, api_key: str, model: str) -> dict:
        """测试API连接"""
        try:
            # 验证参数
            if not api_url or not api_key or not model:
                return {"success": False, "error": "请填写完整的API配置"}
            
            # 临时更新配置进行测试
            original_url = config.get("api_url")
            original_key = config.get("api_key")
            original_model = config.get("api_model")
            
            config.set("api_url", api_url)
            config.set("api_key", api_key)
            config.set("api_model", model)
            config.save()
            
            # 调用LLM翻译器测试
            success, message = llm_translator.test_connection()
            
            # 恢复原始配置
            config.set("api_url", original_url)
            config.set("api_key", original_key)
            config.set("api_model", original_model)
            config.save()
            
            return {"success": success, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_models(self, api_url: str, api_key: str) -> dict:
        """获取可用模型列表"""
        try:
            import httpx
            
            # 构建API URL
            url = api_url.rstrip("/")
            if not url.endswith("/v1/models"):
                if url.endswith("/v1"):
                    url = url + "/models"
                else:
                    url = url + "/v1/models"
            
            # 获取代理
            from core.proxy_manager import get_proxy_url
            proxy = get_proxy_url()
            
            # 发送请求
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            with httpx.Client(timeout=10.0, proxy=proxy) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                models = result.get("data", [])
                
                return {
                    "success": True,
                    "models": [{"id": m.get("id", "")} for m in models]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def minimize_window(self) -> None:
        """最小化窗口"""
        if self._window:
            self._window.minimize()
    
    def set_on_top(self, on_top: bool) -> None:
        """
        设置窗口是否置顶。
        
        pywebview 的 window.on_top 在 GUI 线程中执行 SetWindowPos，
        但从 JS API 线程直接赋值会死锁。
        解决方案：在独立线程中延迟一小段时间再赋值，
        让 JS API 调用先返回，避免死锁。
        """
        if not self._window:
            return
        
        def _apply():
            try:
                # 短暂延迟，让当前 JS API 调用先返回
                import time
                time.sleep(0.05)
                self._window.on_top = on_top
                log.info(f"Window on_top={on_top}")
            except Exception as e:
                log.warning(f"set_on_top failed: {e}")
                # fallback: Win32 API
                try:
                    import ctypes
                    u32 = ctypes.windll.user32
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    HWND_TOPMOST = -1
                    HWND_NOTOPMOST = -2
                    hwnd = u32.FindWindowW(None, APP_NAME)
                    if hwnd:
                        flag = HWND_TOPMOST if on_top else HWND_NOTOPMOST
                        u32.SetWindowPos(hwnd, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                        log.info(f"Window on_top={on_top} via Win32 (hwnd={hwnd:#x})")
                except Exception as e2:
                    log.warning(f"Win32 fallback failed: {e2}")
        
        import threading
        threading.Thread(target=_apply, daemon=True).start()
    
    def close_window(self) -> None:
        """关闭窗口（根据设置决定是否最小化到托盘）"""
        minimize_to_tray = config.get("minimize_to_tray", True)
        log.info(f"close_window called, minimize_to_tray={minimize_to_tray}")
        if minimize_to_tray and self._window:
            self._window.hide()
            # 更新 main 模块的窗口状态
            try:
                import main as main_module
                main_module._window_visible = False
            except ImportError:
                pass
            log.info("Window hidden to system tray")
        elif self._window:
            log.info("Destroying window")
            self._window.destroy()
    
    def resize(self, width: int, height: int) -> None:
        """调整窗口大小"""
        if self._window:
            self._window.resize(width, height)
    
    def get_position(self) -> dict:
        """获取窗口位置"""
        if self._window:
            try:
                return {"x": self._window.x, "y": self._window.y}
            except Exception:
                return {"x": 0, "y": 0}
        return {"x": 0, "y": 0}
    
    def move_window(self, x: int, y: int) -> None:
        """移动窗口到指定位置"""
        if self._window:
            try:
                self._window.move(x, y)
            except Exception as e:
                log.error(f"Move window error: {e}")
    
    def move_relative(self, dx: int, dy: int) -> None:
        """相对移动窗口（基于当前位置偏移）"""
        if self._window:
            try:
                x = self._window.x
                y = self._window.y
                self._window.move(x + dx, y + dy)
            except Exception as e:
                log.error(f"Move relative error: {e}")

    # ========== 划词翻译 ==========
    
    def translate_selection(self) -> dict:
        """
        划词翻译（备用方法，从热键管理器调用）
        """
        try:
            # 热键触发瞬间记录鼠标位置（供翻译完成后定位气泡）
            self._capture_mouse_pos()
            
            from core.selection_translator import selection_translator
            selection_translator.set_translate_callback(self._do_translate)
            
            # 先获取选中文本（自动复制）
            text = selection_translator.get_selected_text()
            if not text:
                self._show_selection_error("自动复制未生效，请先 Ctrl+C 复制，再按快捷键")
                return {"success": False, "error": "自动复制未生效"}
            
            # 立即显示"翻译中..."（气泡/窗口），翻译完成后更新内容
            self._show_selection_loading(text)
            
            result = self._do_translate(text)
            
            if result and result.get("success"):
                self._update_selection_result(text, result.get("translation", ""))
            elif result and not result.get("success"):
                self._show_selection_error(result.get("error", "划词翻译失败"))
            
            return result
        except Exception as e:
            log.error(f"translate_selection error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def translate_selection_callback(self, text: str) -> dict:
        """
        划词翻译回调（从键盘钩子调用）
        翻译文本 → 按配置显示结果（气泡或窗口）
        
        Args:
            text: 要翻译的文本
            
        Returns:
            dict: 翻译结果
        """
        try:
            # 回调触发时记录鼠标位置（供翻译完成后定位气泡）
            self._capture_mouse_pos()
            
            if not text or not text.strip():
                self._show_selection_error("未获取到选中文本")
                return {"success": False, "error": "未获取到选中文本"}
            
            # 立即显示"翻译中..."（气泡/窗口），翻译完成后更新内容
            self._show_selection_loading(text)
            
            result = self._do_translate(text)
            
            if result and result.get("success"):
                self._update_selection_result(text, result.get("translation", ""))
            elif result and not result.get("success"):
                self._show_selection_error(result.get("error", "划词翻译失败"))
            
            return result
        except Exception as e:
            log.error(f"translate_selection_callback error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _show_selection_loading(self, source_text: str) -> None:
        """立即显示"翻译中..."（气泡或窗口），提升响应速度"""
        display_mode = config.get("selection_display_mode", "bubble")
        if display_mode == "window":
            self._fallback_show_main(source_text, "翻译中...")
        else:
            self.show_bubble(source_text, "翻译中...")
            # loading 状态不自动隐藏（翻译可能超过 5 秒），等结果更新后再计时
            if self._bubble_timer:
                self._bubble_timer.cancel()
                self._bubble_timer = None
    
    def _update_selection_result(self, source_text: str, translation: str) -> None:
        """翻译完成后更新显示内容（气泡或窗口）"""
        display_mode = config.get("selection_display_mode", "bubble")
        if display_mode == "window":
            # 更新主窗口译文区内容
            self._push_selection_result(source_text, translation)
        else:
            # 更新气泡内容（不重新定位，保持当前位置）
            import json as _json
            safe_source = _json.dumps(source_text)
            safe_translation = _json.dumps(translation)
            self._safe_js(
                f"window.__setBubbleContent && window.__setBubbleContent({safe_source}, {safe_translation})"
            )
            # 重置自动隐藏定时器（翻译耗时可能超过 loading 的 5 秒）
            if self._bubble_timer:
                self._bubble_timer.cancel()
            import threading
            self._bubble_timer = threading.Timer(5.0, self.hide_bubble)
            self._bubble_timer.daemon = True
            self._bubble_timer.start()
            log.info("Bubble content updated with final result")
    
    def _show_selection_result(self, source_text: str, translation: str) -> None:
        """按配置的划词翻译窗口样式显示结果"""
        display_mode = config.get("selection_display_mode", "bubble")
        if display_mode == "window":
            log.info("Selection result shown in main window (mode=window)")
            self._fallback_show_main(source_text, translation)
        else:
            self.show_bubble(source_text, translation)
    
    def _show_selection_error(self, message: str) -> None:
        """按配置的划词翻译窗口样式显示错误"""
        display_mode = config.get("selection_display_mode", "bubble")
        if display_mode == "window":
            # 窗口模式：错误显示在主窗口（通过 toast 无法直接调用，显示在译文区）
            log.info(f"Selection error in main window mode: {message}")
            try:
                if self._window:
                    self._window.show()
                    self._window.restore()
                    import main as main_module
                    main_module._window_visible = True
                    # 显示错误到译文区
                    safe_err = str(message).replace("\\", "\\\\").replace("'", "\\'")
                    self._window.evaluate_js(
                        f"window.__onTranslateError && window.__onTranslateError('{safe_err}')"
                    )
            except Exception as e:
                log.debug(f"Window mode error display failed: {e}")
        else:
            self.show_bubble_error(message)
    
    def _do_translate(self, text: str) -> dict:
        """
        执行翻译（内部方法，供 selection_translator 回调使用）
        
        Args:
            text: 待翻译文本
            
        Returns:
            dict: 翻译结果
        """
        try:
            # 检测语言
            lang = language_detector.detect(text)
            
            # 直接用字符比例判断（langdetect 对短文本/混合文本不可靠）
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            has_english = any('a' <= c.lower() <= 'z' for c in text)
            is_mixed = has_chinese and has_english
            
            chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            english_count = sum(1 for c in text if 'a' <= c.lower() <= 'z')
            
            log.info(f"Selection translate - detected='{lang}', zh_chars={chinese_count}, en_chars={english_count}, mixed={is_mixed}")
            
            if is_mixed:
                # 中英混合：统一翻译为英文
                target_lang = "en"
            elif lang in ("zh", "zh-cn", "zh-tw"):
                target_lang = "en"
            else:
                target_lang = "zh"
            
            log.info(f"Selection translate direction: {lang} -> {target_lang} (mixed={is_mixed})")
            
            # 调用翻译引擎（非流式，一次性返回）
            result = llm_translator.translate(text, lang, target_lang, is_mixed=is_mixed)
            
            if result.success:
                log.info(f"Selection translate success: '{result.translated_text[:50]}...'")
                
                # 自动复制译文（如果开启）
                self._auto_copy_result(result.translated_text)
                
                # 保存到历史记录
                History.add(
                    source_text=text,
                    translated_text=result.translated_text,
                    source_lang=result.source_lang,
                    target_lang=result.target_lang,
                    engine=result.engine
                )
                
                return {
                    "success": True,
                    "translation": result.translated_text,
                    "source_text": text,
                    "source_lang": result.source_lang,
                    "target_lang": result.target_lang
                }
            else:
                # 主引擎失败 → 降级到 Bing 备用引擎
                log.warning(f"Selection translate failed, falling back to Bing: {result.error_message}")
                fallback = self._translate_with_fallback(text, lang, target_lang, is_mixed=is_mixed)
                if fallback.get("success"):
                    bing_text = fallback.get("translation", "")
                    # 自动复制译文（如果开启）
                    self._auto_copy_result(bing_text)
                    # 保存到历史记录（标记为 bing 引擎）
                    History.add(
                        source_text=text,
                        translated_text=bing_text,
                        source_lang=fallback.get("source_lang", lang),
                        target_lang=fallback.get("target_lang", target_lang),
                        engine="bing"
                    )
                    return {
                        "success": True,
                        "translation": bing_text,
                        "source_text": text,
                        "source_lang": fallback.get("source_lang", lang),
                        "target_lang": fallback.get("target_lang", target_lang),
                        "engine": "bing"
                    }
                log.error(f"Selection translate failed: {result.error_message}")
                return {"success": False, "error": result.error_message}
                
        except Exception as e:
            log.error(f"_do_translate error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _show_window_for_selection(self):
        """显示主窗口（划词翻译时调用），强制置顶"""
        try:
            if self._window:
                log.info("Showing window for selection translate...")
                self._window.show()
                self._window.restore()
                
                # 用 Win32 API 强制置顶（从 pywebview 线程调用，有正确的上下文）
                try:
                    import ctypes
                    u32 = ctypes.windll.user32
                    SW_RESTORE = 9
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    HWND_TOPMOST = -1
                    
                    hwnd = u32.FindWindowW(None, APP_NAME)
                    if hwnd:
                        u32.ShowWindow(hwnd, SW_RESTORE)
                        u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                        u32.SetForegroundWindow(hwnd)
                        log.info(f"Window set topmost (hwnd={hwnd:#x})")
                except Exception as e:
                    log.debug(f"Win32 topmost failed: {e}")
                
                log.info("Window shown and restored for selection translate")
            else:
                log.warning("_show_window_for_selection: no window available")
        except Exception as e:
            log.error(f"Failed to show window: {e}", exc_info=True)
    
    def _push_selection_result(self, source_text: str, translation: str):
        """
        将划词翻译结果推送到前端

        通过 evaluate_js 调用前端的 __onSelectionTranslate 回调
        """
        if not self._window:
            log.warning("_push_selection_result: no window available")
            return
        
        try:
            # 使用 JSON 安全序列化，避免 JS 注入问题
            import json as _json
            safe_source = _json.dumps(source_text)
            safe_translation = _json.dumps(translation)
            
            js_code = f"window.__onSelectionTranslate && window.__onSelectionTranslate({safe_source}, {safe_translation});"
            
            log.info(f"Pushing selection result via evaluate_js: source={source_text[:30]}..., translation={translation[:30]}...")
            self._window.evaluate_js(js_code)
            log.info("Selection translate result pushed to frontend successfully")
            
        except Exception as e:
            log.error(f"Failed to push selection result to frontend: {e}", exc_info=True)

    # ========== 更新 ==========
    
    def check_update(self) -> dict:
        """
        检查 GitHub 上是否有新版本
        Returns: {"has_update": bool, "version": str, "download_url": str, "notes": str}
        """
        try:
            import httpx
            from core.proxy_manager import get_proxy_url
            from app.constants import APP_VERSION, APP_NAME_CN
            import re
            
            proxy = get_proxy_url()
            repo = "FangShaoqing/Qingxin-Translator"
            
            with httpx.Client(timeout=10.0, proxy=proxy) as client:
                resp = client.get(
                    f"https://api.github.com/repos/{repo}/releases/latest",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )
                
                if resp.status_code == 404:
                    return {"has_update": False, "error": "no_releases"}
                
                resp.raise_for_status()
                release = resp.json()
            
            remote_version = release.get("tag_name", "").lstrip("v")
            if not remote_version:
                return {"has_update": False, "error": "no_version"}
            
            # 版本比较（简单的 x.y.z 比较）
            def parse_ver(v):
                return [int(x) for x in re.split(r'[^0-9]', v) if x]
            
            local = parse_ver(APP_VERSION)
            remote = parse_ver(remote_version)
            
            if remote <= local:
                return {"has_update": False}
            
            # 查找安装程序下载链接
            download_url = ""
            for asset in release.get("assets", []):
                name = asset.get("name", "")
                if name.endswith(".exe") and "Setup" in name:
                    download_url = asset.get("browser_download_url", "")
                    break
            
            # 通用下载链接（如果没找到 Setup.exe）
            if not download_url:
                download_url = release.get("html_url", "")
            
            notes = release.get("body", "")[:500]
            
            log.info(f"Update available: v{APP_VERSION} -> v{remote_version}")
            
            return {
                "has_update": True,
                "version": remote_version,
                "download_url": download_url,
                "notes": notes
            }
            
        except Exception as e:
            log.error(f"check_update failed: {e}")
            return {"has_update": False, "error": str(e)}
    
    def open_download_page(self, url: str) -> dict:
        """在浏览器中打开下载页面"""
        try:
            import webbrowser
            webbrowser.open(url)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


# 全局API实例
api = Api()
