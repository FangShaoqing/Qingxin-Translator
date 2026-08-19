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
    
    # 快捷键
    "hotkey": "Ctrl+Alt+S",
    
    # 划词翻译
    "selection_translate_hotkey": "Ctrl+Alt+X",  # 划词翻译快捷键
    "selection_display_mode": "bubble",          # 划词翻译结果展示：bubble气泡 / window窗口
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
        """从文件加载配置，优先读取用户目录，否则加载预置配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                    # 合并配置（保留默认值）
                    self.data.update(saved_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load config: {e}")
        else:
            # 用户配置不存在，尝试加载预置配置（exe 旁边的 data/config.json）
            preset_config = _EXE_DIR / "data" / "config.json"
            if preset_config.exists() and preset_config != self.config_path:
                try:
                    with open(preset_config, "r", encoding="utf-8") as f:
                        saved_config = json.load(f)
                        self.data.update(saved_config)
                        print(f"Loaded preset config from: {preset_config}")
                except (json.JSONDecodeError, IOError):
                    pass
        
        # 纠正无效的 engine 值
        valid_engines = {"online"}
        if self.data.get("engine") not in valid_engines:
            self.data["engine"] = "online"
    
    def save(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            self._notify_listeners()
        except IOError as e:
            print(f"Warning: Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
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
