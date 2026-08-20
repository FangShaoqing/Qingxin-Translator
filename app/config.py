"""
Qingxin Translator - Configuration Manager
配置管理模块
"""

import json
from pathlib import Path
from typing import Any, Optional

from app.constants import CONFIG_FILE, DATA_DIR, _EXE_DIR

# 默认配置（包含开箱即用的 API 配置）
DEFAULT_CONFIG = {
    # 翻译引擎
    "engine": "online",
    "api_url": "https://llm-x3zqff59a3xftxwa.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
    "api_key": "sk-ws-H.EPIPEXE.EZD5.MEUCIDXYK6Py0iVmOh0aZRcPeiCJnc6xBICVv6Pc8vph4W47AiEAkrPSqjwsrvkluCXrgmbGckK5PHACCg72P3CkgY3-0_Q",
    "api_model": "deepseek-v4-flash-0731",
    
    # 语言设置
    "source_lang": "auto",
    "target_lang": "zh",
    
    # 行为设置
    "auto_copy": False,          # 翻译后自动复制译文
    "minimize_to_tray": True,    # 关闭时最小化到托盘
    "launch_at_startup": True,   # 开机自启
    
    # 性能设置
    "disable_thinking": True,    # 禁用模型思考模式（加速响应）
    "use_streaming": True,       # 使用流式传输（实时显示）
    "debounce_ms": 300,          # 输入防抖延迟（毫秒）
    
    # 翻译设置
    "translate_mode": "literal", # 译文质量：literal直译 / paraphrase意译 / polish润色
    
    # 界面设置
    "theme": "light",            # "light" / "dark"
    "font_size": 14,
    "font_family": "Source Han Sans",
    
    # 窗口位置（None = 使用屏幕居中）
    "window_x": None,            # 上次窗口 X 坐标
    "window_y": None,            # 上次窗口 Y 坐标
    "window_width": 520,         # 上次窗口宽度
    "window_height": 200,        # 上次窗口高度
    "window_on_top": False,      # 窗口置顶（用户意愿，托盘菜单/图钉切换）
    
    # 快捷键
    "hotkey": "Ctrl+Alt+S",
    
    # 划词翻译
    "selection_translate_hotkey": "Ctrl+Alt+X",  # 划词翻译快捷键
    "selection_display_mode": "bubble",          # 划词翻译结果展示：bubble气泡 / window窗口
    "selection_hover_button": True,              # 拖选文本后显示悬浮翻译按钮
    "clipboard_auto_translate": False,           # 复制文本后自动翻译（剪贴板监听）
}


class Config:
    """
    配置管理器
    支持读取、写入、监听配置变化
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[Path] = None):
        if self._initialized:
            return
        
        self.config_path = config_path or CONFIG_FILE
        self.data: dict = DEFAULT_CONFIG.copy()
        self._listeners: list = []
        
        # 确保数据目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.load()
        self._initialized = True
    
    def load(self) -> None:
        """从文件加载配置，优先读取用户目录，否则复制预置配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # 合并配置（保留默认值）
                    self.data.update(saved_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config: {e}")
        else:
            # 用户配置不存在：从安装目录的预置配置复制到用户目录
            # （避免安装到 Program Files 后直接读写无权限的 {app}\data）
            try:
                from app.constants import PRESET_CONFIG_FILE
                if PRESET_CONFIG_FILE.exists() and PRESET_CONFIG_FILE != self.config_path:
                    with open(PRESET_CONFIG_FILE, "r", encoding="utf-8") as f:
                        saved_config = json.load(f)
                        self.data.update(saved_config)
                        print(f"Loaded preset config from: {PRESET_CONFIG_FILE}")
                    # 复制到用户目录，确保后续保存可写
                    try:
                        self.save()
                        print(f"Preset config copied to: {self.config_path}")
                    except Exception:
                        pass
            except (json.JSONDecodeError, IOError, ImportError):
                pass
        
        # 纠正无效的 engine 值
        valid_engines = {"online"}
        if self.data.get("engine") not in valid_engines:
            self.data["engine"] = "online"
        
        # 兼容迁移：旧版明文 api_key → 加密存储
        self._migrate_api_key()
    
    def _migrate_api_key(self):
        """旧版明文 api_key 自动迁移为加密存储（api_key_enc）"""
        try:
            plain = self.data.get("api_key", "")
            # 加密字段存在则无需迁移（优先使用加密值）
            if self.data.get("api_key_enc"):
                # 清理残留明文
                if plain:
                    self.data["api_key"] = ""
                return
            if plain:
                from core.secret import encrypt
                enc = encrypt(plain)
                if enc:
                    self.data["api_key_enc"] = enc
                    self.data["api_key"] = ""
                    try:
                        self.save()
                        print("API key migrated to encrypted storage")
                    except Exception:
                        pass
        except Exception as e:
            print(f"Warning: API key migration failed: {e}")
    
    def save(self) -> None:
        """保存配置到文件（api_key 加密存储）"""
        try:
            # 保存前把明文 api_key 加密，磁盘上不保留明文
            plain = self.data.get("api_key", "")
            if plain:
                from core.secret import encrypt
                enc = encrypt(plain)
                if enc:
                    self.data["api_key_enc"] = enc
                    self.data["api_key"] = ""
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            self._notify_listeners()
        except IOError as e:
            print(f"Warning: Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（api_key 解密返回明文）"""
        if key == "api_key":
            # 优先明文（未加密场景），否则解密 api_key_enc
            plain = self.data.get("api_key", "")
            if plain:
                return plain
            enc = self.data.get("api_key_enc", "")
            if enc:
                from core.secret import decrypt
                dec = decrypt(enc)
                if dec is not None:
                    return dec
                return ""  # 跨机器无法解密 → 返回空，提示重新输入
            return default
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值（api_key 保存时加密）"""
        self.data[key] = value
        self.save()
    
    def update(self, updates: dict) -> None:
        """批量更新配置"""
        self.data.update(updates)
        self.save()
    
    def reset(self) -> None:
        """重置为默认配置"""
        self.data = DEFAULT_CONFIG.copy()
        self.save()
    
    def add_listener(self, callback) -> None:
        """添加配置变化监听器"""
        if callback not in self._listeners:
            self._listeners.append(callback)
    
    def remove_listener(self, callback) -> None:
        """移除配置变化监听器"""
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        """通知所有监听器"""
        for listener in self._listeners:
            try:
                listener(self.data)
            except Exception as e:
                print(f"Warning: Config listener error: {e}")
    
    def to_dict(self) -> dict:
        """导出配置为字典"""
        return self.data.copy()
    
    def __repr__(self) -> str:
        return f"Config({self.config_path})"


# 全局配置实例
config = Config()
