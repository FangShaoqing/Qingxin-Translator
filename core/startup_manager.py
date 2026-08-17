"""
Qingxin Translator - Startup Manager
开机自启管理
"""

import sys
import winreg
from pathlib import Path

from app.config import config
from app.constants import APP_NAME


# 注册表路径
REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_KEY = APP_NAME.replace(" ", "_")


def is_launch_at_startup() -> bool:
    """
    检查是否设置了开机自启
    
    Returns:
        bool: 是否开机自启
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_READ
        )
        
        try:
            value, _ = winreg.QueryValueEx(key, APP_KEY)
            return bool(value)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def set_launch_at_startup(enable: bool) -> bool:
    """
    设置开机自启
    
    Args:
        enable: 是否启用
        
    Returns:
        bool: 是否设置成功
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REGISTRY_PATH,
            0,
            winreg.KEY_WRITE
        )
        
        if enable:
            # 获取可执行文件路径
            if getattr(sys, 'frozen', False):
                # 打包后的exe
                exe_path = sys.executable
            else:
                # 开发环境，创建启动脚本
                exe_path = sys.executable
                script_path = Path(__file__).parent.parent / "main.py"
                exe_path = f'"{exe_path}" "{script_path}"'
            
            winreg.SetValueEx(key, APP_KEY, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_KEY)
            except FileNotFoundError:
                pass
        
        winreg.CloseKey(key)
        
        # 更新配置
        config.set("launch_at_startup", enable)
        
        return True
    except Exception as e:
        print(f"Failed to set launch at startup: {e}")
        return False


def toggle_launch_at_startup() -> bool:
    """
    切换开机自启状态
    
    Returns:
        bool: 切换后的状态
    """
    current = is_launch_at_startup()
    new_state = not current
    set_launch_at_startup(new_state)
    return new_state
