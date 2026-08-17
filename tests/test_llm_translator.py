"""
Tests for core.llm_translator module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestLLMTranslator:
    """Test LLMTranslator class"""

    @patch('core.llm_translator.HTTPX_AVAILABLE', False)
    def test_not_available_when_httpx_missing(self):
        from core.llm_translator import LLMTranslator
        translator = LLMTranslator()
        assert translator.is_available() is False

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_not_available_when_config_missing(self, mock_config):
        from core.llm_translator import LLMTranslator

        mock_config.get.return_value = ""
        translator = LLMTranslator()
        assert translator.is_available() is False

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_available_when_config_present(self, mock_config):
        from core.llm_translator import LLMTranslator

        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            return default

        mock_config.get.side_effect = mock_get
        translator = LLMTranslator()
        assert translator.is_available() is True

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_translate_success(self, mock_config):
        from core.llm_translator import LLMTranslator

        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return "gpt-3.5-turbo"
            return default

        mock_config.get.side_effect = mock_get

        # Mock httpx client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "你好"}}]
        }
        mock_response.raise_for_status = Mock()

        with patch('core.llm_translator.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client

            translator = LLMTranslator()
            result = translator.translate("Hello", "en", "zh")
            assert result.success is True
            assert result.translated_text == "你好"

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_translate_not_available(self, mock_config):
        from core.llm_translator import LLMTranslator

        mock_config.get.return_value = ""
        translator = LLMTranslator()
        result = translator.translate("Hello", "en", "zh")
        assert result.success is False
        assert "not configured" in result.error_message.lower()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_translate_empty_text(self, mock_config):
        from core.llm_translator import LLMTranslator

        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            return default

        mock_config.get.side_effect = mock_get
        translator = LLMTranslator()
        result = translator.translate("", "en", "zh")
        assert result.success is False
        assert "empty" in result.error_message.lower()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_translate_same_language(self, mock_config):
        from core.llm_translator import LLMTranslator

        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            return default

        mock_config.get.side_effect = mock_get
        translator = LLMTranslator()
        result = translator.translate("Hello", "en", "en")
        assert result.success is True
        assert result.translated_text == "Hello"

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_test_connection_success(self, mock_config):
        from core.llm_translator import LLMTranslator

        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return "gpt-3.5-turbo"
            return default

        mock_config.get.side_effect = mock_get

        # Mock successful translation
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "你好"}}]
        }
        mock_response.raise_for_status = Mock()

        with patch('core.llm_translator.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.post.return_value = mock_response
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client

            translator = LLMTranslator()
            success, message = translator.test_connection()
            assert success is True
            assert "successful" in message.lower()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_test_connection_failure(self, mock_config):
        from core.llm_translator import LLMTranslator

        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return "gpt-3.5-turbo"
            return default

        mock_config.get.side_effect = mock_get

        # Mock failed translation
        with patch('core.llm_translator.httpx.Client') as mock_client_class:
            mock_client = Mock()
            mock_client.post.side_effect = Exception("Connection failed")
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=False)
            mock_client_class.return_value = mock_client

            translator = LLMTranslator()
            success, message = translator.test_connection()
            assert success is False
            # 网络错误会被转换为中文友好提示
            assert "失败" in message or "connection" in message.lower()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_engine_properties(self, mock_config):
        from core.llm_translator import LLMTranslator
        from core.translator import TranslationEngine

        translator = LLMTranslator()
        assert translator.engine_name == "online"
        assert translator.engine_type == TranslationEngine.ONLINE