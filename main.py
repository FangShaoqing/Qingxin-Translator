"""
Qingxin Translator - Main Entry Point (pywebview)
青欣翻译 - 程序入口
"""

import os
import sys
import threading
from pathlib import Path

# 区分打包环境与开发环境
if getattr(sys, 'frozen', False):
    # PyInstaller --onefile 打包后，资源在临时解压目录
    ROOT_DIR = Path(sys._MEIPASS)
else:
    ROOT_DIR = Path(__file__).parent

sys.path.insert(0, str(ROOT_DIR))

# 启动时自动设置代理
from core.proxy_manager import setup_proxy
proxy = setup_proxy()

# 初始化日志
from core.logger import log
log.info("=" * 50)
log.info("Qingxin Translator starting...")
log.info(f"Proxy: {proxy or 'None'}")

import webview
from api import api
from app.config import config
from app.constants import APP_NAME, APP_VERSION, ICONS_DIR
from models.database import init_db, close_db
from core.translator import translator_manager
from core.llm_translator import llm_translator

# 窗口可见状态追踪
_window_visible = True
_real_quit = False

# 主窗口引用（供后台线程使用主线程操作）
_main_window = None


def setup_app():
    """初始化应用"""
    log.info("Initializing application...")
    
    # 初始化数据库
    init_db()
    log.info("Database initialized")
    
    # 注册翻译引擎
    translator_manager.register_engine(llm_translator)
    
    # 注册 Bing 备用引擎（主引擎失败时降级使用）
    try:
        from core.bing_translator import bing_translator
        translator_manager.register_engine(bing_translator)
        log.info("Bing fallback engine registered")
    except Exception as e:
        log.warning(f"Failed to register Bing engine: {e}")
    
    # 打印可用引擎
    available = translator_manager.get_available_engines()
    log.info(f"Available translation engines: {available}")
    log.info(f"LLM available: {llm_translator.is_available()}")
    
    log.info(f"{APP_NAME} v{APP_VERSION} initialized")
    log.info(f"Config: {config.config_path}")


def cleanup_app():
    """清理应用资源"""
    log.info("Cleaning up...")
    
    # 停止系统托盘
    try:
        from core.tray_manager import tray_manager
        tray_manager.stop()
    except Exception as e:
        log.warning(f"Failed to stop tray: {e}")
    
    # 停止快捷键
    try:
        from core.hotkey_manager import hotkey_manager
        hotkey_manager.stop()
    except Exception as e:
        log.warning(f"Failed to stop hotkey: {e}")
    
    # 关闭 LLM 翻译器 HTTP 客户端
    try:
        from core.llm_translator import llm_translator
        llm_translator.close()
    except Exception as e:
        log.warning(f"Failed to close LLM translator: {e}")
    
    # 关闭数据库
    close_db()
    
    log.info(f"{APP_NAME} exited")


def _find_window_hwnd():
    """查找主窗口的 Win32 句柄"""
    import ctypes
    user32 = ctypes.windll.user32
    
    hwnd = user32.FindWindowW(None, APP_NAME)
    if hwnd:
        return hwnd
    
    # 备用：通过枚举窗口查找
    found = [0]
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    
    def enum_callback(hwnd_l, _):
        length = user32.GetWindowTextLengthW(hwnd_l)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd_l, buf, length + 1)
            if APP_NAME in buf.value:
                found[0] = hwnd_l
        return True
    
    user32.EnumWindows(WNDENUMPROC(enum_callback), 0)
    return found[0]


def _save_window_position(window) -> None:
    """保存主窗口位置和大小到配置（下次启动恢复）"""
    try:
        x = window.x
        y = window.y
        w = window.width
        h = window.height
        if x is None or y is None:
            return
        # 避免保存屏幕外位置（窗口可能被拖出屏幕边界）
        import ctypes
        user32 = ctypes.windll.user32
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        if x < -50 or y < -50 or x > screen_w or y > screen_h:
            return
        config.set("window_x", int(x))
        config.set("window_y", int(y))
        config.set("window_width", int(w))
        config.set("window_height", int(h))
        log.info(f"Window position saved: ({x}, {y}) {w}x{h}")
    except Exception as e:
        log.debug(f"Save window position failed: {e}")


def _toggle_window():
    """
    切换窗口显示/隐藏（从快捷键调用）
    - 窗口隐藏时：显示窗口并置顶
    - 窗口可见时：隐藏窗口到托盘
    """
    global _window_visible
    try:
        window = webview.windows[0] if webview.windows else None
        if not window:
            log.warning("No window available for toggle")
            return
        
        # 用 Win32 检测窗口实际可见性（状态最可靠，避免 _window_visible 漂移）
        hwnd = _find_window_hwnd()
        if hwnd:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # IsWindowVisible 检测实际可见性 + 非最小化状态
                actually_visible = bool(user32.IsWindowVisible(hwnd)) and not user32.IsIconic(hwnd)
                if actually_visible != _window_visible:
                    log.info(f"Window state resynced: _window_visible {_window_visible} -> {actually_visible}")
                    _window_visible = actually_visible
            except Exception:
                pass
        
        # 判断窗口是否隐藏（以实际可见性为准）
        is_hidden = not _window_visible
        
        if is_hidden:
            # ---- 显示窗口 ----
            log.info("Toggle: showing window...")
            
            # pywebview 方法
            try:
                window.show()
                window.restore()
            except Exception:
                pass
            
            # Win32 API 强制置顶
            try:
                import ctypes
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                
                hwnd = _find_window_hwnd()
                if hwnd:
                    SW_RESTORE = 9
                    SW_SHOW = 5
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    HWND_TOPMOST = ctypes.c_void_p(-1)
                    HWND_NOTOPMOST = ctypes.c_void_p(-2)

                    user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.ShowWindow(hwnd, SW_SHOW)
                    # 临时置顶（拿前台用），稍后按用户意愿恢复
                    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

                    # 强制窗口置顶 + 前台（多级保障）
                    try:
                        # 1) 总是先做 Alt 键击解锁（模拟"最近有输入"，允许 SetForegroundWindow）
                        user32.keybd_event(0x12, 0, 0, 0)          # Alt down
                        user32.keybd_event(0x12, 0, 0x0002, 0)     # Alt up
                        
                        # 2) AttachThreadInput：必须 attach【当前调用线程】与【前台线程】
                        #    （SetForegroundWindow 检查的是调用线程与前台线程的连接）
                        fg = user32.GetForegroundWindow()
                        fg_tid = user32.GetWindowThreadProcessId(fg, None)
                        my_tid = kernel32.GetCurrentThreadId()  # 当前调用（热键回调）线程
                        attached = False
                        if fg and fg_tid != my_tid and fg_tid != 0:
                            attached = user32.AttachThreadInput(my_tid, fg_tid, True)
                        
                        # 3) 设置前台 + 置顶
                        ok = user32.SetForegroundWindow(hwnd)
                        user32.BringWindowToTop(hwnd)
                        
                        if attached:
                            user32.AttachThreadInput(my_tid, fg_tid, False)
                        
                        # 4) 验证是否真的成为前台窗口，失败则再重试一次
                        if not ok or user32.GetForegroundWindow() != hwnd:
                            user32.keybd_event(0x12, 0, 0, 0)
                            user32.keybd_event(0x12, 0, 0x0002, 0)
                            ok2 = user32.SetForegroundWindow(hwnd)
                            user32.BringWindowToTop(hwnd)
                            log.info(f"SetForegroundWindow retry: ok={ok2}, fg={user32.GetForegroundWindow()==hwnd}")
                        else:
                            log.info(f"SetForegroundWindow ok (my_tid={my_tid}, fg_tid={fg_tid})")
                    except Exception as e:
                        log.debug(f"Foreground set failed: {e}")
                        user32.BringWindowToTop(hwnd)

                    # 闪烁任务栏
                    class FLASHWINFO(ctypes.Structure):
                        _fields_ = [
                            ("cbSize", ctypes.wintypes.UINT),
                            ("hwnd", ctypes.wintypes.HWND),
                            ("dwFlags", ctypes.wintypes.DWORD),
                            ("uCount", ctypes.wintypes.UINT),
                            ("dwTimeout", ctypes.wintypes.DWORD),
                        ]
                    fw = FLASHWINFO()
                    fw.cbSize = ctypes.sizeof(FLASHWINFO)
                    fw.hwnd = hwnd
                    fw.dwFlags = 0x3 | 0x0C
                    fw.uCount = 3
                    fw.dwTimeout = 0
                    user32.FlashWindowEx(ctypes.byref(fw))

                    log.info(f"Window forced to front (hwnd={hwnd:#x})")
                else:
                    log.warning("Could not find window handle")
            except Exception as e:
                log.debug(f"Win32 show failed: {e}")
            
            # 延迟一次置顶（窗口完全显示后再补一次，配合正确的线程 attach）
            try:
                import threading
                hwnd2 = _find_window_hwnd()
                if hwnd2:
                    def _re_topmost():
                        try:
                            import ctypes
                            user32_ = ctypes.windll.user32
                            SWP_NOMOVE = 0x0002
                            SWP_NOSIZE = 0x0001
                            # 临时置顶拿前台
                            user32_.SetWindowPos(hwnd2, ctypes.c_void_p(-1), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                            # 延迟置顶后再尝试一次前台
                            fg2 = user32_.GetForegroundWindow()
                            fg2_tid = user32_.GetWindowThreadProcessId(fg2, None)
                            t2_tid = user32_.GetWindowThreadProcessId(hwnd2, None)
                            if fg2_tid != t2_tid:
                                user32_.AttachThreadInput(t2_tid, fg2_tid, True)
                            user32_.SetForegroundWindow(hwnd2)
                            if fg2_tid != t2_tid:
                                user32_.AttachThreadInput(t2_tid, fg2_tid, False)
                            # 按用户意愿恢复置顶（未开启则取消，避免复选框恒勾选）
                            if not bool(config.get("window_on_top", False)):
                                user32_.SetWindowPos(hwnd2, ctypes.c_void_p(-2), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                            log.info(f"Window re-topmost (hwnd={hwnd2:#x})")
                        except Exception:
                            pass
                    threading.Timer(0.3, _re_topmost).start()
            except Exception:
                pass
            
            _window_visible = True
        
        else:
            # ---- 隐藏窗口 ----
            log.info("Toggle: hiding window to tray...")
            
            # 保存窗口位置（下次启动恢复）
            _save_window_position(window)
            
            minimize_to_tray = config.get("minimize_to_tray", True)
            if minimize_to_tray:
                try:
                    window.hide()
                except Exception:
                    pass
                _window_visible = False
                log.info("Window hidden to system tray")
            else:
                # 不启用托盘时最小化窗口
                try:
                    window.minimize()
                except Exception:
                    pass
                _window_visible = False
                log.info("Window minimized")
    
    except Exception as e:
        log.error(f"Toggle window error: {e}")


def _show_window():
    """
    显示窗口（从托盘左键/菜单调用）
    强制前台+置顶（与热键唤起一致），确保在第三方 Dock 环境下也能可靠唤起
    """
    global _window_visible
    try:
        window = webview.windows[0] if webview.windows else None
        if not window:
            log.warning("No window available to show")
            return
        
        log.info("Showing window from tray...")
        window.show()
        window.restore()
        _window_visible = True
        _force_window_foreground()
        log.info("Window shown and restored")
    except Exception as e:
        log.error(f"Show window error: {e}")


def _force_window_foreground():
    """强制主窗口置顶+前台（Alt 解锁 + AttachThreadInput + 验证重试）

    注意：置顶是【临时】的——拿完前台后按用户意愿（config.window_on_top）恢复，
    否则每次唤起窗口都会永久置顶，导致托盘菜单"窗口置顶"复选框永远勾选。
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = _find_window_hwnd()
        if not hwnd:
            return
        SW_RESTORE = 9
        SW_SHOW = 5
        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        HWND_TOPMOST = ctypes.c_void_p(-1)  # 64 位指针值
        HWND_NOTOPMOST = ctypes.c_void_p(-2)

        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.ShowWindow(hwnd, SW_SHOW)
        # 临时置顶，确保拿到前台
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

        # 强制前台（多级保障）：Alt 键击解锁 + attach 当前线程
        import threading
        kernel32 = ctypes.windll.kernel32
        try:
            # 1) Alt 键击解锁（模拟"最近有输入"）
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 0x0002, 0)
            # 2) AttachThreadInput 当前调用线程与前台线程
            fg = user32.GetForegroundWindow()
            fg_tid = user32.GetWindowThreadProcessId(fg, None)
            my_tid = kernel32.GetCurrentThreadId()
            attached = False
            if fg and fg_tid != my_tid and fg_tid != 0:
                attached = user32.AttachThreadInput(my_tid, fg_tid, True)
            # 3) 设置前台
            ok = user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            if attached:
                user32.AttachThreadInput(my_tid, fg_tid, False)
            # 4) 验证，失败重试一次
            if not ok or user32.GetForegroundWindow() != hwnd:
                user32.keybd_event(0x12, 0, 0, 0)
                user32.keybd_event(0x12, 0, 0x0002, 0)
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception as e:
            log.debug(f"Foreground set failed: {e}")
            user32.BringWindowToTop(hwnd)

        # 按用户意愿恢复置顶状态（未开启置顶则取消 topmost，避免复选框恒勾选）
        try:
            want_top = bool(config.get("window_on_top", False))
            if not want_top:
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        except Exception as e:
            log.debug(f"Restore topmost failed: {e}")

        # 延迟 0.3s 补一次前台（窗口完全显示后）
        try:
            def _re_topmost():
                try:
                    user32_ = ctypes.windll.user32
                    SWP_NOMOVE = 0x0002
                    SWP_NOSIZE = 0x0001
                    # 临时置顶拿前台
                    user32_.SetWindowPos(hwnd, ctypes.c_void_p(-1), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                    user32_.SetForegroundWindow(hwnd)
                    # 按用户意愿恢复
                    if not bool(config.get("window_on_top", False)):
                        user32_.SetWindowPos(hwnd, ctypes.c_void_p(-2), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                    log.info(f"Window re-topmost (hwnd={hwnd:#x})")
                except Exception:
                    pass
            threading.Timer(0.3, _re_topmost).start()
        except Exception:
            pass
        log.info(f"Window forced to front (hwnd={hwnd:#x})")
    except Exception as e:
        log.debug(f"Win32 show failed: {e}")


def _quit_app():
    """
    真正退出应用（从托盘调用）
    """
    global _real_quit
    log.info("Real quit requested from tray")
    _real_quit = True
    
    # 保存窗口位置（退出前）
    try:
        window = webview.windows[0] if webview.windows else None
        if window:
            _save_window_position(window)
    except Exception:
        pass
    
    # 检查待安装更新（"稍后安装"：退出时静默执行安装程序覆盖原程序）
    try:
        from core.update_manager import run_pending_install
        run_pending_install()
    except Exception:
        pass
    
    # 先停止托盘和快捷键
    try:
        from core.tray_manager import tray_manager
        tray_manager.stop()
    except Exception:
        pass
    
    try:
        from core.hotkey_manager import hotkey_manager
        hotkey_manager.stop()
    except Exception:
        pass
    
    # 停止鼠标拖选钩子
    try:
        from core.mouse_hook import mouse_selection_hook
        mouse_selection_hook.stop()
    except Exception:
        pass
    
    # 停止剪贴板监听
    try:
        from core.clipboard_monitor import clipboard_monitor
        clipboard_monitor.stop()
    except Exception:
        pass
    
    # 销毁所有窗口（pywebview 需全部窗口关闭后才退出事件循环）
    # 注意：必须先销毁气泡和托盘菜单窗口，否则事件循环永不退出
    try:
        from api import api as api_instance
        if api_instance._bubble_window:
            try:
                api_instance._bubble_window.destroy()
                log.info("Bubble window destroyed")
            except Exception as e:
                log.warning(f"Bubble destroy failed: {e}")
        if api_instance._tray_menu_window:
            try:
                api_instance._tray_menu_window.destroy()
                log.info("Tray menu window destroyed")
            except Exception as e:
                log.warning(f"Tray menu destroy failed: {e}")
        if api_instance._tray_tooltip_window:
            try:
                api_instance._tray_tooltip_window.destroy()
                log.info("Tray tooltip window destroyed")
            except Exception as e:
                log.warning(f"Tray tooltip destroy failed: {e}")
        if api_instance._hover_btn_window:
            try:
                api_instance._hover_btn_window.destroy()
                log.info("Hover button window destroyed")
            except Exception as e:
                log.warning(f"Hover button destroy failed: {e}")
    except Exception:
        pass
    
    # 销毁主窗口（触发 pywebview 退出循环）
    try:
        window = webview.windows[0] if webview.windows else None
        if window:
            window.destroy()
    except Exception as e:
        log.error(f"Quit app error: {e}")


def _trigger_selection_translate():
    """
    触发划词翻译（从热键管理器调用）
    读取剪贴板 → 翻译 → 显示窗口并推送结果
    """
    log.info("Selection translate hotkey triggered")
    try:
        from api import api
        result = api.translate_selection()
        if result and not result.get("success"):
            log.warning(f"Selection translate failed: {result.get('error', 'unknown')}")
    except Exception as e:
        log.error(f"Selection translate error: {e}", exc_info=True)


def _setup_hotkey(window):
    """设置全局快捷键"""
    try:
        from core.hotkey_manager import hotkey_manager
        
        # 主窗口切换快捷键（使用旧的热键管理器）
        hotkey = config.get("hotkey", "")
        if hotkey:
            result = hotkey_manager.start(hotkey, _toggle_window)
            log.info(f"Window toggle hotkey registered: {hotkey} (result={result})")
        else:
            log.info("No window toggle hotkey configured")
        
        # 划词翻译快捷键（使用原热键管理器 + 剪贴板读取）
        selection_hotkey = config.get("selection_translate_hotkey", "")
        if selection_hotkey:
            try:
                from api import api
                from core.selection_translator import selection_translator
                selection_translator.set_translate_callback(api.translate_selection_callback)
                
                result = hotkey_manager.register(selection_hotkey, _trigger_selection_translate)
                log.info(f"Selection translate hotkey registered: {selection_hotkey} (result={result})")
            except Exception as e:
                log.error(f"Failed to register selection hotkey: {e}", exc_info=True)
        else:
            log.info("No selection translate hotkey configured")
        
        # 检查监听器状态
        log.info(f"Hotkey manager running: {hotkey_manager._running}")
        log.info(f"Registered hotkeys: {list(hotkey_manager._callbacks.keys())}")
            
    except Exception as e:
        log.error(f"Failed to setup hotkeys: {e}", exc_info=True)


def _on_tray_right_click(x: int, y: int):
    """
    托盘右键点击回调：显示自定义菜单（独立小窗口渲染，风格与应用一致）
    """
    try:
        from api import api as api_instance
        api_instance.show_tray_menu(x, y)
        log.info(f"Tray right-click at ({x}, {y}), custom menu requested")
    except Exception as e:
        log.error(f"Tray right-click failed: {e}")


def _on_tray_hover(x: int, y: int):
    """
    托盘图标鼠标悬停回调：显示自定义 tooltip（应用风格小卡片）
    """
    try:
        from api import api as api_instance
        mode = config.get("selection_display_mode", "bubble")
        mode_text = "气泡模式" if mode == "bubble" else "窗口模式"
        api_instance.show_tray_tooltip(x, y, mode_text)
    except Exception as e:
        log.debug(f"Tray hover failed: {e}")


def _setup_tray(window):
    """设置系统托盘"""
    try:
        from core.tray_manager import tray_manager
        minimize_to_tray = config.get("minimize_to_tray", True)
        if minimize_to_tray:
            tray_manager.start(
                on_show=_show_window,
                on_quit=_quit_app,
                on_right_click=_on_tray_right_click,
                on_hover=_on_tray_hover
            )
            # 设置初始托盘提示（显示当前划词模式）
            try:
                from api import api as api_instance
                api_instance._update_tray_tooltip()
            except Exception:
                pass
            log.info("System tray initialized")
        else:
            log.info("System tray disabled by config")
    except Exception as e:
        log.warning(f"Failed to setup system tray: {e}")


def _on_closing(window):
    """
    窗口关闭事件处理（处理 Alt+F4 或 OS 关闭按钮）
    """
    global _window_visible, _real_quit
    
    # 如果是真正的退出（托盘退出），允许关闭
    if _real_quit:
        log.info("Closing: real quit, allowing close")
        return True
    
    minimize_to_tray = config.get("minimize_to_tray", True)
    if minimize_to_tray:
        log.info("Closing: minimize to tray instead of quit")
        window.hide()
        _window_visible = False
        return False  # 阻止默认关闭行为
    
    log.info("Closing: allowing close")
    return True  # 允许关闭


def main():
    """主函数"""
    log.info("Starting main function...")
    
    # 初始化应用
    setup_app()
    
    # 获取窗口配置
    window_config = config.get("window", {})
    width = window_config.get("width", 520)
    height = window_config.get("height", 200)  # 初始高度，JS会动态调整
    min_width = window_config.get("min_width", 420)
    min_height = window_config.get("min_height", 120)
    
    # 读取上次保存的窗口位置（优先恢复，否则屏幕外创建等 loaded 后居中）
    saved_x = config.get("window_x")
    saved_y = config.get("window_y")
    saved_w = config.get("window_width")
    saved_h = config.get("window_height")
    
    # 创建主窗口 - 使用js_api参数传递API
    # 屏幕外创建（避免 WebView2 初始化时的白屏/黑屏闪烁），页面加载完成后移到上次位置或屏幕中央
    window = webview.create_window(
        title=APP_NAME,
        url=str(ROOT_DIR / "web" / "index.html"),
        width=saved_w if saved_w else width,
        height=saved_h if saved_h else height,
        min_size=(min_width, min_height),
        resizable=True,
        frameless=True,
        easy_drag=False,  # 禁用全局拖动，只允许标题栏拖动
        on_top=False,
        x=-10000,  # 屏幕外创建，加载完成后再显示（避免启动闪烁）
        y=-10000,
        background_color="#FFFFFF",
        js_api=api
    )
    
    # 页面加载完成后移到上次位置或屏幕中央（避免 WebView2 白/黑屏闪烁）
    def _on_main_loaded():
        try:
            import ctypes
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            win_w = window.width
            win_h = window.height
            
            # 优先恢复上次保存的位置
            if saved_x is not None and saved_y is not None:
                # 确保位置在屏幕内（防止显示器变更后窗口跑到屏幕外）
                sx = max(0, min(int(saved_x), screen_w - 100))
                sy = max(0, min(int(saved_y), screen_h - 100))
                window.move(sx, sy)
                log.info(f"Main window restored to ({sx}, {sy})")
            else:
                # 无保存位置：屏幕居中
                cx = max(0, (screen_w - win_w) // 2)
                cy = max(0, (screen_h - win_h) // 2)
                window.move(cx, cy)
                log.info(f"Main window moved to center ({cx}, {cy})")
        except Exception as e:
            log.debug(f"Position window failed: {e}")
    window.events.loaded += _on_main_loaded
    
    # 设置窗口引用
    api.set_window(window)
    
    # 创建划词翻译气泡窗口（无边框、置顶、白色无边框极简样式）
    # 注意：不用 hidden=True——hidden 窗口的 WebView2 可能不渲染页面（气泡是空窗口）
    # 注意：不用 transparent=True——WebView2+WinForms 的真透明不可靠（渲染成黑底）
    # 改为创建在屏幕外（-10000,-10000），页面正常加载，显示时再移到鼠标位置
    try:
        bubble = webview.create_window(
            title="QingxinBubble",
            url=str(ROOT_DIR / "web" / "bubble.html") + "?v=3",  # 版本号强制刷新 WebView2 缓存
            width=120,       # 初始小尺寸，避免显示时闪大气泡（JS 会自适应修正）
            height=60,
            min_size=(1, 1),   # 关键：取消默认最小尺寸(200x100)限制，否则内容自适应缩小时被钳制
            frameless=True,
            on_top=True,
            draggable=False,    # 禁用 pywebview 内置拖动（避免误调 window.move(None) 报错）
            easy_drag=False,    # 禁用全局拖动（默认 True，会导致按住气泡被拖动）
            text_select=True,   # 允许选中气泡内的文本（默认 False 禁选）
            x=-10000,       # 初始位置在屏幕外，用户不可见但页面正常加载
            y=-10000,
            background_color="#FFFFFF",
            js_api=api
        )
        api.set_bubble_window(bubble)
        
        # 气泡窗口禁止关闭，只能隐藏（避免引用失效）；退出时允许关闭
        def _on_bubble_closing():
            global _real_quit
            if _real_quit:
                log.info("Bubble closing allowed (real quit)")
                return True
            log.info("Bubble closing requested, hiding instead")
            try:
                bubble.hide()
            except Exception:
                pass
            return False
        bubble.events.closing += _on_bubble_closing
        log.info("Bubble window created (hidden)")
    except Exception as e:
        log.warning(f"Failed to create bubble window: {e}")
    
    # 创建自定义托盘菜单窗口（独立小窗口：主窗口隐藏到托盘时菜单仍可见）
    # 注意：与气泡相同——不用 hidden=True（WebView2 不渲染），屏幕外创建；min_size=(1,1) 防钳制
    try:
        tray_menu_win = webview.create_window(
            title="QingxinTrayMenu",
            url=str(ROOT_DIR / "web" / "tray_menu.html") + "?v=1",  # 版本号强制刷新 WebView2 缓存
            width=210,
            height=400,  # 初始高度留足余量（菜单全部项约 350px，防 JS 测量前内容被裁）
            min_size=(1, 1),
            frameless=True,
            on_top=True,
            draggable=False,
            easy_drag=False,
            text_select=False,
            x=-10000,
            y=-10000,
            background_color="#FFFFFF",
            js_api=api
        )
        api.set_tray_menu_window(tray_menu_win)
        # 创建后立即隐藏（Win32）：避免启动时窗口闪现/出现在任务栏
        try:
            api.hide_tray_menu()
        except Exception:
            pass
        
        # 菜单窗口禁止关闭，只能隐藏（避免引用失效）；退出时允许关闭
        def _on_tray_menu_closing():
            global _real_quit
            if _real_quit:
                log.info("Tray menu closing allowed (real quit)")
                return True
            log.info("Tray menu closing requested, hiding instead")
            try:
                tray_menu_win.hide()
            except Exception:
                pass
            return False
        tray_menu_win.events.closing += _on_tray_menu_closing
        log.info("Tray menu window created (hidden)")
    except Exception as e:
        log.warning(f"Failed to create tray menu window: {e}")
    
    # 创建自定义托盘 tooltip 窗口（应用风格小卡片，替代 Windows 原生气泡）
    try:
        tooltip_win = webview.create_window(
            title="QingxinTooltip",
            url=str(ROOT_DIR / "web" / "tray_tooltip.html") + "?v=1",
            width=160,
            height=32,
            min_size=(1, 1),
            frameless=True,
            on_top=True,
            draggable=False,
            easy_drag=False,
            text_select=False,
            x=-10000,
            y=-10000,
            background_color="#FFFFFF",
            js_api=api
        )
        api.set_tray_tooltip_window(tooltip_win)
        # 创建后立即隐藏（Win32）：避免启动时窗口闪现/出现在任务栏
        try:
            api.hide_tray_tooltip()
        except Exception:
            pass
        
        def _on_tooltip_closing():
            global _real_quit
            if _real_quit:
                return True
            try:
                tooltip_win.hide()
            except Exception:
                pass
            return False
        tooltip_win.events.closing += _on_tooltip_closing
        log.info("Tray tooltip window created (hidden)")
    except Exception as e:
        log.warning(f"Failed to create tray tooltip window: {e}")
    
    # 创建选区悬浮翻译按钮窗口（拖选文本后出现在选区旁，点击即翻译）
    try:
        hover_btn_win = webview.create_window(
            title="QingxinHoverBtn",
            url=str(ROOT_DIR / "web" / "hover_button.html") + "?v=1",
            width=70,
            height=30,
            min_size=(1, 1),
            frameless=True,
            on_top=True,
            draggable=False,
            easy_drag=False,
            text_select=False,
            x=-10000,
            y=-10000,
            background_color="#FFFFFF",
            js_api=api
        )
        api.set_hover_btn_window(hover_btn_win)
        # 创建后立即隐藏（Win32）
        try:
            api.hide_hover_btn()
        except Exception:
            pass
        
        def _on_hover_btn_closing():
            global _real_quit
            if _real_quit:
                return True
            try:
                hover_btn_win.hide()
            except Exception:
                pass
            return False
        hover_btn_win.events.closing += _on_hover_btn_closing
        log.info("Hover button window created (hidden)")
    except Exception as e:
        log.warning(f"Failed to create hover button window: {e}")
    
    # 注册窗口关闭事件（处理 Alt+F4 等 OS 级关闭）
    window.events.closing += _on_closing
    
    # 启动后的初始化函数
    def on_started():
        log.info("pywebview started, initializing components...")
        
        # 启动后立即隐藏辅助窗口（它们在屏幕外，但可能闪现/出现在任务栏）
        try:
            from api import api as api_instance
            api_instance.hide_bubble()
            api_instance.hide_tray_tooltip()
            api_instance.hide_tray_menu()
            api_instance.hide_hover_btn()
        except Exception:
            pass
        
        # 延迟初始化快捷键，确保 pywebview 完全启动
        import time
        time.sleep(1.0)
        
        # 再次确保辅助窗口隐藏（WebView2 完全就绪后）
        try:
            from api import api as api_instance
            api_instance.hide_bubble()
            api_instance.hide_tray_tooltip()
            api_instance.hide_tray_menu()
            api_instance.hide_hover_btn()
        except Exception:
            pass
        
        # 设置快捷键
        _setup_hotkey(window)
        
        # 设置系统托盘
        _setup_tray(window)
        
        # 启动鼠标拖选钩子（选区悬浮翻译按钮，配置开关控制）
        try:
            if config.get("selection_hover_button", True):
                from core.mouse_hook import mouse_selection_hook
                from api import api as api_instance
                mouse_selection_hook.start(on_select=api_instance.show_hover_btn)
                log.info("Mouse selection hook started (hover button)")
            else:
                log.info("Hover button disabled by config")
        except Exception as e:
            log.warning(f"Mouse selection hook failed: {e}")
        
        # 启动剪贴板监听（复制即翻译，配置开关控制，默认关闭）
        try:
            if config.get("clipboard_auto_translate", False):
                from core.clipboard_monitor import clipboard_monitor
                from api import api as api_instance
                clipboard_monitor.start(on_text=api_instance._on_clipboard_text)
                log.info("Clipboard monitor started (auto translate)")
            else:
                log.info("Clipboard monitor disabled by config")
        except Exception as e:
            log.warning(f"Clipboard monitor failed: {e}")
        
        log.info("All components initialized")
    
    # 运行应用
    log.info("Starting pywebview...")
    webview.start(
        debug=config.get("debug", False),
        func=on_started
    )
    
    # 清理
    cleanup_app()


if __name__ == "__main__":
    # 关键：把 __main__ 注册为 'main' 模块别名。
    # api.py 中 `import main as main_module` 依赖此别名拿到同一个模块对象；
    # 否则 main.py 会被二次加载（两个模块实例），_real_quit 等全局变量分裂，
    # 导致托盘退出时 closing 回调读到的 _real_quit 永远是 False、窗口无法关闭。
    sys.modules['main'] = sys.modules['__main__']
    main()
