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
        self._hotkey_manager = None
        
    def set_window(self, window):
        """设置pywebview窗口引用"""
        self._window = window
    
    def get_app_info(self) -> dict:
        """获取应用信息"""
        return {
            "name": APP_NAME,
            "version": APP_VERSION
        }
    
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
            from core.selection_translator import selection_translator
            selection_translator.set_translate_callback(self._do_translate)
            result = selection_translator.trigger_selection_translate()
            
            if result and result.get("success"):
                self._show_window_for_selection()
                self._push_selection_result(result.get("source_text", ""), result.get("translation", ""))
            
            return result
        except Exception as e:
            log.error(f"translate_selection error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def translate_selection_callback(self, text: str) -> dict:
        """
        划词翻译回调（从键盘钩子调用）
        翻译文本 → 显示窗口 → 推送结果到前端
        
        Args:
            text: 要翻译的文本
            
        Returns:
            dict: 翻译结果
        """
        try:
            result = self._do_translate(text)
            
            if result and result.get("success"):
                translation = result.get("translation", "")
                source_text = result.get("source_text", "")
                
                # 显示主窗口
                self._show_window_for_selection()
                
                # 通过 evaluate_js 将翻译结果推送到前端
                self._push_selection_result(source_text, translation)
            
            return result
        except Exception as e:
            log.error(f"translate_selection_callback error: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
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


# 全局API实例
api = Api()
