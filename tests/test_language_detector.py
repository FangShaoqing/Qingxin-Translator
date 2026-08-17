"""
Tests for core.language_detector module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestLanguageDetector:
    """Test LanguageDetector class"""

    def test_singleton(self):
        from core.language_detector import LanguageDetector
        detector1 = LanguageDetector()
        detector2 = LanguageDetector()
        assert detector1 is detector2

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_simple_detect_chinese(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        result = detector.detect("你好世界")
        assert result == "zh"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_simple_detect_english(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        result = detector.detect("Hello world")
        assert result == "en"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_simple_detect_japanese(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        result = detector.detect("こんにちは")
        assert result == "ja"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_simple_detect_korean(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        result = detector.detect("안녕하세요")
        assert result == "ko"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_empty_text(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        result = detector.detect("")
        assert result == "unknown"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_whitespace_only(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        result = detector.detect("   ")
        assert result == "unknown"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('core.language_detector.detect')
    def test_langdetect_success(self, mock_detect):
        from core.language_detector import LanguageDetector
        mock_detect.return_value = "zh-cn"
        detector = LanguageDetector()
        result = detector.detect("这是一个测试文本，用于测试语言检测功能")
        assert result == "zh"

    @patch('core.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('core.language_detector.detect')
    def test_langdetect_failure_fallback(self, mock_detect):
        from core.language_detector import LanguageDetector
        from core.language_detector import LangDetectException
        mock_detect.side_effect = LangDetectException("Detection failed", "test")
        detector = LanguageDetector()
        result = detector.detect("Hello world test")
        assert result in ["en", "unknown"]

    @patch('core.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('core.language_detector.detect_langs')
    def test_detect_with_confidence(self, mock_detect_langs):
        from core.language_detector import LanguageDetector

        mock_result = Mock()
        mock_result.lang = "zh-cn"
        mock_result.prob = 0.95
        mock_detect_langs.return_value = [mock_result]

        detector = LanguageDetector()
        detector._available = True
        results = detector.detect_with_confidence("这是一个测试文本用于检测语言")
        assert len(results) == 1
        assert results[0]["lang"] == "zh"
        assert results[0]["confidence"] == 0.95

    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_detect_with_confidence_not_available(self):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        detector._available = False
        results = detector.detect_with_confidence("test")
        assert results == []

    def test_get_language_name(self):
        from core.language_detector import LanguageDetector
        assert LanguageDetector.get_language_name("zh") == "中文"
        assert LanguageDetector.get_language_name("en") == "English"
        assert LanguageDetector.get_language_name("unknown") == "unknown"

    def test_get_supported_languages(self):
        from core.language_detector import LanguageDetector
        languages = LanguageDetector.get_supported_languages()
        assert "zh" in languages
        assert "en" in languages
        assert "auto" in languages

    @patch('core.language_detector.LANGDETECT_AVAILABLE', True)
    @patch('core.language_detector.detect')
    def test_short_text_uses_simple_detect(self, mock_detect):
        from core.language_detector import LanguageDetector
        detector = LanguageDetector()
        # Short text (< 20 chars) should use simple detection
        result = detector.detect("Hello")
        # Should not call langdetect for short text
        mock_detect.assert_not_called()
        assert result == "en"