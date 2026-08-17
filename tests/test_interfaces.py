"""
Tests for translation interfaces
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTranslationInterface:
    """Test translation interface"""

    def test_translator_manager_translate_success(self):
        from core.translator import TranslatorManager, TranslationResult

        TranslatorManager._instance = None
        manager = TranslatorManager()

        engine = Mock()
        engine.engine_name = "test"
        engine.is_available.return_value = True
        engine.translate.return_value = TranslationResult(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="test",
            success=True
        )
        manager.register_engine(engine)

        result = manager.translate("Hello", "en", "zh", "test")
        assert result.success is True
        assert result.translated_text == "你好"

    def test_translator_manager_translate_engine_not_found(self):
        from core.translator import TranslatorManager

        TranslatorManager._instance = None
        manager = TranslatorManager()

        result = manager.translate("Hello", "en", "zh", "nonexistent")
        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_translator_manager_translate_engine_not_available(self):
        from core.translator import TranslatorManager

        TranslatorManager._instance = None
        manager = TranslatorManager()

        engine = Mock()
        engine.engine_name = "test"
        engine.is_available.return_value = False
        manager.register_engine(engine)

        result = manager.translate("Hello", "en", "zh", "test")
        assert result.success is False
        assert "not available" in result.error_message.lower()


class TestLLMTranslatorInterface:
    """Test LLM translator interface"""

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_llm_translator_engine_name(self, mock_config):
        from core.llm_translator import LLMTranslator

        mock_config.get.return_value = ""
        translator = LLMTranslator()
        assert translator.engine_name == "online"

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_llm_translator_is_available(self, mock_config):
        from core.llm_translator import LLMTranslator

        mock_config.get.side_effect = lambda key, default=None: {
            "api_url": "https://api.example.com",
            "api_key": "test-key"
        }.get(key, default)
        
        translator = LLMTranslator()
        assert translator.is_available() is True
