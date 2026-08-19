"""
Qingxin Translator - System Tray Manager
系统托盘管理器

自定义菜单方案：子类化 pystray 图标拦截右键点击，
不显示原生菜单，改为回调主窗口弹出自绘 HTML 菜单（与应用风格一致）。
"""

import threading
from pathlib import Path
from typing import Callable, Optional

import pystray
from PIL import Image

from app.constants import APP_NAME, ICONS_DIR
from core.logger import log


class _CustomMenuIcon(pystray.Icon):
    """
    自定义托盘图标：拦截右键点击，不显示原生菜单。
    通过 on_right_click 回调通知外部显示自定义菜单。
    通过 on_hover 回调通知外部显示自定义 tooltip（应用风格小卡片）。
    通过 on_show 回调处理左键单击（直接唤起窗口，不走 pystray 菜单逻辑）。
    """

    # Windows 消息常量（pystray 未定义的部分）
    WM_MOUSEMOVE = 0x0200

    def __init__(self, *args, on_right_click: Callable = None, on_hover: Callable = None,
                 on_show: Callable = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_right_click = on_right_click
        self._on_hover = on_hover
        self._on_show = on_show
        self._hover_pos = None

    def _on_notify(self, wparam, lparam):
        """覆盖原生菜单逻辑：左键直接唤起窗口，右键回调自定义菜单，悬停回调自定义 tooltip"""
        import pystray._util.win32 as win32
        from ctypes import wintypes
        import ctypes

        if lparam == win32.WM_LBUTTONUP:
            # 左键单击：直接调用显示窗口回调（不能调 self()——那是显示菜单用的，
            # menu=None 时无效，导致左键无法唤起窗口）
            if self._on_show:
                try:
                    self._on_show()
                except Exception as e:
                    log.error(f"Tray left-click show callback failed: {e}")
        elif lparam == win32.WM_RBUTTONUP:
            # 右键点击：回调显示自定义菜单
            try:
                point = wintypes.POINT()
                win32.GetCursorPos(ctypes.byref(point))
                if self._on_right_click:
                    self._on_right_click(point.x, point.y)
            except Exception as e:
                log.error(f"Tray right-click callback failed: {e}")
        elif lparam == self.WM_MOUSEMOVE:
            # 鼠标悬停/移动：回调显示自定义 tooltip（应用风格）
            # 节流：300ms 内不重复触发（WM_MOUSEMOVE 高频）
            import time as _time
            now = _time.time()
            if getattr(self, '_last_hover_ts', 0) and now - self._last_hover_ts < 0.3:
                return
            self._last_hover_ts = now
            try:
                point = wintypes.POINT()
                win32.GetCursorPos(ctypes.byref(point))
                # 位置未变化（静止悬停）也刷新，保证 tooltip 持续显示
                self._hover_pos = (point.x, point.y)
                if self._on_hover:
                    self._on_hover(point.x, point.y)
            except Exception as e:
                log.error(f"Tray hover callback failed: {e}")


class TrayManager:
    """系统托盘管理器"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._on_show: Optional[Callable] = None
        self._on_quit: Optional[Callable] = None
        self._on_right_click: Optional[Callable] = None
        self._on_hover: Optional[Callable] = None
        self._initialized = True
        self._started = False
    
    def start(self, on_show: Callable, on_quit: Callable,
              on_right_click: Callable = None, on_hover: Callable = None) -> bool:
        """
        启动系统托盘图标
        
        Args:
            on_show: 显示窗口的回调（左键单击）
            on_quit: 退出应用的回调
            on_right_click: 右键点击回调 (x, y) —— 用于显示自定义菜单
            on_hover: 鼠标悬停回调 (x, y) —— 用于显示自定义 tooltip
        
        Returns:
            bool: 是否启动成功
        """
        try:
            # 防止重复启动
            if self._started and self._icon is not None:
                log.warning("System tray already started, skipping")
                return True
            
            self._on_show = on_show
            self._on_quit = on_quit
            self._on_right_click = on_right_click
            self._on_hover = on_hover
            
            log.info("Loading tray icon...")
            
            # 加载图标
            icon_path = ICONS_DIR / "app_32.png"
            if not icon_path.exists():
                icon_path = ICONS_DIR / "icon_32.png"
            if not icon_path.exists():
                # 使用默认图标
                log.info("No tray icon file found, using default icon")
                icon_image = self._create_default_icon()
            else:
                log.info(f"Loading tray icon from: {icon_path}")
                icon_image = Image.open(icon_path)
                # 确保图标尺寸为 32x32
                if icon_image.size != (32, 32):
                    icon_image = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
            
            # 创建自定义托盘图标（无原生菜单，右键走回调；title 留空禁用 Windows 原生气泡，
            # tooltip 由自定义小窗口渲染，风格与应用一致）
            self._icon = _CustomMenuIcon(
                name=APP_NAME,
                icon=icon_image,
                title="",  # 空 title：不显示系统原生气泡提示
                menu=None,  # 禁用原生菜单
                on_right_click=on_right_click,
                on_hover=on_hover,
                on_show=on_show
            )
            
            # 在新线程中运行（daemon 线程，避免 pystray 卡住时阻塞进程退出）
            self._thread = threading.Thread(target=self._run, daemon=True, name="TrayIconThread")
            self._thread.start()
            
            self._started = True
            log.info("System tray started successfully")
            return True
            
        except Exception as e:
            log.error(f"Failed to start system tray: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _run(self):
        """运行托盘图标事件循环"""
        try:
            if self._icon:
                log.info("Tray icon event loop starting...")
                self._icon.run()
                log.info("Tray icon event loop ended")
        except Exception as e:
            log.error(f"Tray icon error: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        """停止系统托盘图标"""
        try:
            if self._icon:
                log.info("Stopping tray icon...")
                self._icon.stop()
                self._icon = None
                self._started = False
                log.info("System tray stopped")
            else:
                log.info("System tray was not running, nothing to stop")
        except Exception as e:
            log.error(f"Failed to stop system tray: {e}")
            import traceback
            traceback.print_exc()
    
    def update_tooltip(self, tooltip: str):
        """更新托盘提示文本

        原生气泡已禁用（title 为空），tooltip 由自定义小窗口渲染。
        此方法保留仅为兼容旧调用，不再设置系统气泡。
        """
        # 保留：设置 title 会重新启用 Windows 原生气泡，与自定义 tooltip 冲突
        pass
    
    def _show_window(self, icon=None, item=None):
        """显示窗口"""
        log.info("Tray: show window requested")
        if self._on_show:
            try:
                self._on_show()
            except Exception as e:
                log.error(f"Tray show window error: {e}")
        else:
            log.warning("Tray: on_show callback not set")
    
    def _quit_app(self, icon=None, item=None):
        """退出应用"""
        log.info("Tray: quit requested")
        if self._on_quit:
            try:
                self._on_quit()
            except Exception as e:
                log.error(f"Tray quit error: {e}")
        else:
            log.warning("Tray: on_quit callback not set")
        self.stop()
    
    def _create_default_icon(self) -> Image.Image:
        """创建默认图标"""
        # 创建一个简单的蓝色方块图标
        size = 32
        image = Image.new('RGBA', (size, size), (0, 120, 215, 255))
        return image


# 全局系统托盘管理器实例
tray_manager = TrayManager()
