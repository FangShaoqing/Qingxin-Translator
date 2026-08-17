"""
Qingxin Translator - Language Detector
语言检测模块
"""

from typing import Optional

try:
    from langdetect import detect, detect_langs
    from langdetect.lang_detect_exception import LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


# 语言代码映射（langdetect -> 标准代码）
LANG_MAP = {
    "zh-cn": "zh",
    "zh-tw": "zh",
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "ru": "ru",
    "it": "it",
    "pt": "pt",
    "ar": "ar",
}

# 语言名称映射
LANG_NAMES = {
    "auto": "自动识别",
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
    "it": "Italiano",
    "pt": "Português",
    "ar": "العربية",
}


class LanguageDetector:
    """
    语言检测器
    支持自动检测文本语言
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
        
        self._available = LANGDETECT_AVAILABLE
        self._initialized = True
    
    @property
    def is_available(self) -> bool:
        """检测器是否可用"""
        return self._available
    
    def detect(self, text: str) -> str:
        """
        检测文本语言
        
        Args:
            text: 待检测文本
            
        Returns:
            str: 语言代码（如 "zh", "en"）
                 检测失败返回 "unknown"
        """
        if not text or not text.strip():
            return "unknown"
        
        # 短文本使用简单检测（langdetect对短文本不准）
        if len(text.strip()) < 20:
            return self._simple_detect(text)
        
        if not self._available:
            return self._simple_detect(text)
        
        try:
            # 使用langdetect检测
            lang_code = detect(text)
            
            # 标准化语言代码
            return LANG_MAP.get(lang_code.lower(), lang_code.lower())
        except LangDetectException:
            # 检测失败，使用简单检测
            return self._simple_detect(text)
    
    def detect_with_confidence(self, text: str) -> list[dict]:
        """
        检测文本语言（带置信度）
        
        Args:
            text: 待检测文本
            
        Returns:
            list[dict]: 语言检测结果列表，每项包含 "lang" 和 "confidence"
        """
        if not self._available or not text or not text.strip():
            return []
        
        try:
            results = detect_langs(text)
            return [
                {
                    "lang": LANG_MAP.get(r.lang.lower(), r.lang.lower()),
                    "confidence": round(r.prob, 4)
                }
                for r in results
            ]
        except LangDetectException:
            return []
    
    def _simple_detect(self, text: str) -> str:
        """
        简单语言检测（基于字符范围）
        当langdetect不可用时使用
        
        Args:
            text: 待检测文本
            
        Returns:
            str: 语言代码
        """
        if not text:
            return "unknown"
        
        # 统计中文字符数量
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        
        # 统计日文字符数量（平假名 + 片假名）
        japanese_count = sum(1 for c in text if '\u3040' <= c <= '\u30ff')
        
        # 统计韩文字符数量
        korean_count = sum(1 for c in text if '\uac00' <= c <= '\ud7af')
        
        total_chars = len(text)
        
        if total_chars == 0:
            return "unknown"
        
        # 计算比例
        chinese_ratio = chinese_count / total_chars
        japanese_ratio = japanese_count / total_chars
        korean_ratio = korean_count / total_chars
        
        # 判断语言
        if chinese_ratio > 0.3:
            return "zh"
        elif japanese_ratio > 0.1:
            return "ja"
        elif korean_ratio > 0.1:
            return "ko"
        else:
            # 默认为英文
            return "en"
    
    @staticmethod
    def get_language_name(lang_code: str) -> str:
        """
        获取语言名称
        
        Args:
            lang_code: 语言代码
            
        Returns:
            str: 语言名称
        """
        return LANG_NAMES.get(lang_code, lang_code)
    
    @staticmethod
    def get_supported_languages() -> dict[str, str]:
        """获取支持的语言列表"""
        return LANG_NAMES.copy()


# 全局语言检测器实例
language_detector = LanguageDetector()
