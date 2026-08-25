"""
Qingxin Translator - Constants
应用常量定义
"""

import os
import sys
from pathlib import Path

# ==================== 路径常量 ====================
APP_NAME = "Qingxin Translator"
APP_NAME_CN = "青欣翻译"
APP_VERSION = "0.3.7"

# 区分打包环境与开发环境
# 打包后：sys._MEIPASS 指向临时解压目录（只读资源在这里）
# 开发时：使用项目根目录
if getattr(sys, 'frozen', False):
    # PyInstaller --onefile 打包后的临时解压目录（只读）
    _BUNDLE_DIR = Path(sys._MEIPASS)
    # exe 所在目录（安装目录，Program Files 下无写权限，仅作只读资源来源）
    _EXE_DIR = Path(sys.executable).parent
    # 用户数据目录（%APPDATA% 可写，避免安装到 Program Files 后配置保存失败）
    _DATA_BASE = Path(os.environ.get('APPDATA', str(Path.home()))) / "Qingxin Translator"
else:
    _BUNDLE_DIR = Path(__file__).parent.parent
    _EXE_DIR = Path(__file__).parent.parent
    _DATA_BASE = _EXE_DIR

# 项目根目录（兼容旧代码引用）
ROOT_DIR = _BUNDLE_DIR

# 数据目录（可写：打包后为 %APPDATA%\Qingxin Translator\data，开发时为项目目录）
DATA_DIR = _DATA_BASE / "data"
CONFIG_FILE = DATA_DIR / "config.json"
DATABASE_FILE = DATA_DIR / "history.db"

# 预置配置目录（打包后为安装目录 data，仅首次启动作种子）
PRESET_CONFIG_FILE = _EXE_DIR / "data" / "config.json"

# 资源目录（只读，打包在 exe 内部）
RESOURCES_DIR = _BUNDLE_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
FONTS_DIR = RESOURCES_DIR / "fonts"
STYLES_DIR = RESOURCES_DIR / "styles"

# ==================== 翻译引擎 ====================
ENGINE_ONLINE = "online"

# 支持的语言
LANGUAGES = {
    "auto": "自动识别",
    "zh": "中文",
    "en": "English",
}

# ==================== 主题 ====================
THEME_LIGHT = "light"
THEME_DARK = "dark"

# ==================== 配色方案（macOS风格） ====================
class Colors:
    """应用配色方案"""
    # 主色调
    PRIMARY = "#FADADE"  # 樱花粉
    PRIMARY_HOVER = "#F0C4C8"
    PRIMARY_PRESSED = "#E8B0B5"
    
    # 背景色
    BACKGROUND = "#FFFFFF"
    BACKGROUND_SECONDARY = "#F5F5F5"
    
    # 文字色
    TEXT_PRIMARY = "#333333"
    TEXT_SECONDARY = "#666666"
    TEXT_TERTIARY = "#999999"
    
    # 边框色
    BORDER = "#E8E8E8"
    BORDER_FOCUS = "#FADADE"
    
    # 状态色
    SUCCESS = "#52C41A"
    WARNING = "#FAAD14"
    ERROR = "#FF4D4F"
    INFO = "#1890FF"

# ==================== 字体 ====================
class Fonts:
    """字体配置"""
    CHINESE = "Source Han Sans"
    CHINESE_FALLBACK = "Microsoft YaHei"
    ENGLISH = "Inter"
    MONOSPACE = "JetBrains Mono"
    
    SIZE_SMALL = 12
    SIZE_NORMAL = 14
    SIZE_LARGE = 16

# ==================== 窗口尺寸 ====================
class WindowSize:
    """窗口尺寸配置"""
    # 主窗口
    MAIN_WIDTH = 800
    MAIN_HEIGHT = 600
    
    # 翻译弹窗
    POPUP_MIN_WIDTH = 300
    POPUP_MIN_HEIGHT = 150
    POPUP_MAX_WIDTH = 500
    POPUP_MAX_HEIGHT = 400
    
    # 快捷翻译输入框
    QUICK_WIDTH = 400
    QUICK_HEIGHT = 80
    
    # 圆角
    BORDER_RADIUS = 12
    BORDER_RADIUS_SMALL = 8

# ==================== 动画 ====================
class Animation:
    """动画配置"""
    POPUP_DURATION = 200  # 弹窗动画时长（毫秒）
    FADE_DURATION = 150   # 淡入淡出时长（毫秒）
