"""
Qingxin Translator - Translator Engine Abstraction
翻译引擎抽象层
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from app.config import config


class TranslationEngine(Enum):
    """翻译引擎类型"""
    ONLINE = "online"


@dataclass
class TranslationResult:
    """
    翻译结果数据类
    """
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    engine: str
    success: bool = True
    error_message: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "source_text": self.source_text,
            "translated_text": self.translated_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "engine": self.engine,
            "success": self.success,
            "error_message": self.error_message,
        }


class TranslatorEngine(ABC):
    """
    翻译引擎抽象基类
    所有翻译引擎都需要继承此类并实现抽象方法
    """
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """引擎名称"""
        pass
    
    @property
    @abstractmethod
    def engine_type(self) -> TranslationEngine:
        """引擎类型"""
        pass
    
    @abstractmethod
    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（"auto"表示自动检测）
            target_lang: 目标语言代码
            
        Returns:
            TranslationResult: 翻译结果
        """
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 待检测文本
            
        Returns:
            str: 语言代码
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查引擎是否可用
        
        Returns:
            bool: 引擎是否可用
        """
        pass
    
    def _create_error_result(self, source_text: str, source_lang: str, 
                             target_lang: str, error_message: str) -> TranslationResult:
        """
        创建错误结果
        
        Args:
            source_text: 原文
            source_lang: 源语言
            target_lang: 目标语言
            error_message: 错误信息
            
        Returns:
            TranslationResult: 错误结果
        """
        return TranslationResult(
            source_text=source_text,
            translated_text="",
            source_lang=source_lang,
            target_lang=target_lang,
            engine=self.engine_name,
            success=False,
            error_message=error_message
        )


class TranslatorManager:
    """
    翻译管理器
    统一调度翻译引擎
    """
    
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
        
        self._engines: dict[str, TranslatorEngine] = {}
        self._initialized = True
    
    def register_engine(self, engine: TranslatorEngine) -> None:
        """
        注册翻译引擎
        
        Args:
            engine: 翻译引擎实例
        """
        self._engines[engine.engine_name] = engine
    
    def get_engine(self, engine_name: Optional[str] = None) -> Optional[TranslatorEngine]:
        """
        获取翻译引擎
        
        Args:
            engine_name: 引擎名称，None则使用配置中的引擎
            
        Returns:
            TranslatorEngine: 翻译引擎实例
        """
        if engine_name is None:
            engine_name = config.get("engine", "online")
        
        return self._engines.get(engine_name)
    
    def get_current_engine(self) -> Optional[TranslatorEngine]:
        """获取当前配置的翻译引擎"""
        return self.get_engine()
    
    def translate(self, text: str, source_lang: str = "auto", 
                  target_lang: str = "zh", engine_name: Optional[str] = None) -> TranslationResult:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码（"auto"表示自动检测）
            target_lang: 目标语言代码
            engine_name: 引擎名称，None则使用配置中的引擎
            
        Returns:
            TranslationResult: 翻译结果
        """
        engine = self.get_engine(engine_name)
        
        if engine is None:
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=engine_name or "unknown",
                success=False,
                error_message=f"Translation engine not found: {engine_name}"
            )
        
        if not engine.is_available():
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=engine.engine_name,
                success=False,
                error_message=f"Translation engine not available: {engine.engine_name}"
            )
        
        return engine.translate(text, source_lang, target_lang)
    
    def detect_language(self, text: str, engine_name: Optional[str] = None) -> str:
        """
        检测文本语言
        
        Args:
            text: 待检测文本
            engine_name: 引擎名称（可选）
            
        Returns:
            str: 语言代码
        """
        # 优先使用指定的引擎
        if engine_name:
            engine = self.get_engine(engine_name)
            if engine and engine.is_available():
                return engine.detect_language(text)
        
        # 使用全局语言检测器
        from core.language_detector import language_detector
        return language_detector.detect(text)
    
    def get_available_engines(self) -> list[str]:
        """获取所有可用的引擎名称"""
        return [name for name, engine in self._engines.items() if engine.is_available()]
    
    def switch_engine(self, engine_name: str) -> bool:
        """
        切换当前翻译引擎
        
        Args:
            engine_name: 引擎名称
            
        Returns:
            bool: 是否切换成功
        """
        if engine_name in self._engines and self._engines[engine_name].is_available():
            config.set("engine", engine_name)
            return True
        return False


# 全局翻译管理器实例
translator_manager = TranslatorManager()
