"""
Tests for core.bing_translator module
"""

import pytest
from unittest.mock import Mock, patch


class TestBingTranslator:
    """Test BingTranslator class"""

    def _make_translator(self, mock_available=True):
        from core.bing_translator import BingTranslator
        t = BingTranslator()
        t._available = mock_available
        return t

    def test_engine_properties(self):
        from core.bing_translator import BingTranslator
        from core.translator import TranslationEngine
        t = BingTranslator()
        assert t.engine_name == "bing"
        assert t.engine_type == TranslationEngine.ONLINE

    @patch('core.bing_translator.HTTPX_AVAILABLE', False)
    def test_not_available_when_httpx_missing(self):
        from core.bing_translator import BingTranslator
        t = BingTranslator()
        assert t.is_available() is False

    @patch('core.bing_translator.HTTPX_AVAILABLE', True)
    def test_available_when_httpx_present(self):
        from core.bing_translator import BingTranslator
        t = BingTranslator()
        assert t.is_available() is True

    def test_translate_empty_text(self):
        t = self._make_translator()
        result = t.translate("", "en", "zh")
        assert result.success is False
        assert "empty" in result.error_message.lower()

    def test_translate_same_language(self):
        t = self._make_translator()
        result = t.translate("Hello", "en", "en")
        assert result.success is True
        assert result.translated_text == "Hello"

    @patch('core.bing_translator.BingTranslator._call_api')
    def test_translate_success(self, mock_call):
        t = self._make_translator()
        mock_call.return_value = "你好"
        result = t.translate("Hello", "en", "zh")
        assert result.success is True
        assert result.translated_text == "你好"
        assert result.engine == "bing"

    @patch('core.bing_translator.BingTranslator._call_api')
    def test_translate_api_error(self, mock_call):
        t = self._make_translator()
        mock_call.side_effect = ValueError("Bing API error (HTTP 429)")
        result = t.translate("Hello", "en", "zh")
        assert result.success is False
        assert "429" in result.error_message

    @patch('core.bing_translator.BingTranslator._get_token')
    def test_call_api_auth_failure(self, mock_token):
        t = self._make_translator()
        mock_token.return_value = None
        with pytest.raises(ValueError):
            t._call_api("Hello", "en", "zh")

    @patch('core.bing_translator.BingTranslator._get_token')
    @patch('core.bing_translator.BingTranslator._get_client')
    def test_call_api_success(self, mock_client, mock_token):
        t = self._make_translator()
        mock_token.return_value = "test-token"
        mock_client.return_value = mock_client  # _get_client() 返回自身

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"translations": [{"text": "你好"}]}]

        mock_client.post.return_value = mock_response

        result = t._call_api("Hello", "en", "zh")
        assert result == "你好"

    @patch('core.bing_translator.BingTranslator._get_token')
    @patch('core.bing_translator.BingTranslator._get_client')
    def test_call_api_http_error(self, mock_client, mock_token):
        t = self._make_translator()
        mock_token.return_value = "test-token"
        mock_client.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "forbidden"

        mock_client.post.return_value = mock_response

        with pytest.raises(ValueError):
            t._call_api("Hello", "en", "zh")

    @patch('core.bing_translator.BingTranslator._get_token')
    @patch('core.bing_translator.BingTranslator._get_client')
    def test_call_api_malformed_response(self, mock_client, mock_token):
        t = self._make_translator()
        mock_token.return_value = "test-token"
        mock_client.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"unexpected": "shape"}]

        mock_client.post.return_value = mock_response

        with pytest.raises(ValueError):
            t._call_api("Hello", "en", "zh")

    def test_lang_mapping(self):
        t = self._make_translator()
        assert t._map_lang("zh") == "zh-Hans"
        assert t._map_lang("zh-cn") == "zh-Hans"
        assert t._map_lang("zh-tw") == "zh-Hant"
        assert t._map_lang("en") == "en"
        # 未知语言原样返回
        assert t._map_lang("xx") == "xx"

    def test_token_caching(self):
        """token 在缓存期内不重复请求"""
        t = self._make_translator()
        with patch.object(t, '_get_client') as mock_client:
            mock_client.return_value = mock_client
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.text = "token-1"
            mock_client.get.return_value = mock_resp

            token1 = t._get_token()
            token2 = t._get_token()
            assert token1 == "token-1"
            assert token2 == "token-1"
            assert mock_client.get.call_count == 1  # 只请求了一次
