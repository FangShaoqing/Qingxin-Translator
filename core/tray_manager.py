"""
Qingxin Translator - System Tray Manager
系统托盘管理器
"""

import threading
from pathlib import Path
from typing import Callable, Optional

import pystray
from PIL import Image

from app.constants import APP_NAME, ICONS_DIR
from core.logger import log


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
        self._initialized = True
        self._started = False
    
    def start(self, on_show: Callable, on_quit: Callable) -> bool:
        """
        启动系统托盘图标
        
        Args:
            on_show: 显示窗口的回调
            on_quit: 退出应用的回调
        
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
            
            # 创建菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self._show_window, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._quit_app)
            )
            
            # 创建托盘图标
            self._icon = pystray.Icon(
                name=APP_NAME,
                icon=icon_image,
                title=APP_NAME,
                menu=menu
            )
            
            # 在新线程中运行（非 daemon 线程，确保托盘图标持续运行）
            self._thread = threading.Thread(target=self._run, daemon=False, name="TrayIconThread")
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
        """更新托盘图标提示文本"""
        if self._icon:
            try:
                self._icon.title = tooltip
            except Exception as e:
                log.warning(f"Failed to update tooltip: {e}")
    
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
