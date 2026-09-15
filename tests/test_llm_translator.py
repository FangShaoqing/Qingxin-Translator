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


class TestLLMTranslateMode:
    """Test translate_mode (literal / paraphrase / polish)"""

    def _make_translator(self, mock_config, mode="literal"):
        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return "gpt-3.5-turbo"
            elif key == "translate_mode":
                return mode
            return default

        mock_config.get.side_effect = mock_get
        from core.llm_translator import LLMTranslator
        return LLMTranslator()

    def _get_system_prompt(self, translator, text="Hello", source="en", target="zh"):
        payload = translator._build_payload(text, source, target, stream=False)
        return payload["messages"][0]["content"]

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_literal_mode_prompt(self, mock_config):
        t = self._make_translator(mock_config, mode="literal")
        prompt = self._get_system_prompt(t)
        assert "Output ONLY the translated text" in prompt
        assert "free paraphrase" not in prompt
        assert "polishing" not in prompt

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_paraphrase_mode_prompt(self, mock_config):
        t = self._make_translator(mock_config, mode="paraphrase")
        prompt = self._get_system_prompt(t)
        assert "free paraphrase" in prompt

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_polish_mode_prompt(self, mock_config):
        t = self._make_translator(mock_config, mode="polish")
        prompt = self._get_system_prompt(t)
        assert "polishing" in prompt or "polished" in prompt

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_unknown_mode_falls_back_to_literal(self, mock_config):
        t = self._make_translator(mock_config, mode="unknown-mode")
        prompt = self._get_system_prompt(t)
        # 未知模式回退到默认模板
        assert "Output ONLY the translated text" in prompt


class TestLLMTokenParam:
    """Test token param name selection (mimo vs others)"""

    def _make_translator(self, mock_config, model):
        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return model
            return default

        mock_config.get.side_effect = mock_get
        from core.llm_translator import LLMTranslator
        return LLMTranslator()

    def _get_payload(self, translator):
        return translator._build_payload("Hello", "en", "zh", stream=False)

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_mimo_uses_max_completion_tokens(self, mock_config):
        t = self._make_translator(mock_config, "mimo-v2.5-pro")
        payload = self._get_payload(t)
        assert "max_completion_tokens" in payload
        assert "max_tokens" not in payload

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_deepseek_uses_max_tokens(self, mock_config):
        t = self._make_translator(mock_config, "deepseek-chat")
        payload = self._get_payload(t)
        assert "max_tokens" in payload
        assert "max_completion_tokens" not in payload

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_glm_uses_max_tokens(self, mock_config):
        t = self._make_translator(mock_config, "glm-4.7-flash")
        payload = self._get_payload(t)
        assert "max_tokens" in payload
        assert "max_completion_tokens" not in payload

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_thinking_param_always_present(self, mock_config):
        t = self._make_translator(mock_config, "deepseek-chat")
        payload = self._get_payload(t)
        assert "thinking" in payload
        assert payload["thinking"] == {"type": "disabled"}


class TestTestConnectionNoConfigMutation:
    """v0.3.14 回归：测试连接不得读写持久化配置

    历史缺陷：api.test_connection 先把测试参数 config.set()+config.save() 落盘、
    测完再恢复。期间并发读取会拿到脏值，恢复失败还会永久写坏用户配置。
    """

    CONFIG_MODEL = "MODEL-FROM-CONFIG"
    ARG_MODEL = "MODEL-FROM-ARG"

    def _make_translator(self, mock_config):
        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.deepseek.com/v1"
            elif key == "api_key":
                return "config-key"
            elif key == "api_model":
                return self.CONFIG_MODEL
            return default

        mock_config.get.side_effect = mock_get
        from core.llm_translator import LLMTranslator
        return LLMTranslator()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_explicit_model_reaches_request(self, mock_config):
        """显式传入的 model / key 必须落到请求上，而不是被配置值覆盖"""
        t = self._make_translator(mock_config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "你好"}}]}
        mock_response.text = "ok"

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch('core.llm_translator.httpx.Client', return_value=mock_client):
            ok, msg = t.test_connection(
                "https://api.deepseek.com/v1", "arg-key", self.ARG_MODEL)

        assert ok is True, msg
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["model"] == self.ARG_MODEL
        assert kwargs["headers"]["Authorization"] == "Bearer arg-key"

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_no_config_write_during_test(self, mock_config):
        """测试连接全程不得调用 config.set / config.save"""
        t = self._make_translator(mock_config)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "你好"}}]}
        mock_response.text = "ok"

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch('core.llm_translator.httpx.Client', return_value=mock_client):
            t.test_connection("https://api.deepseek.com/v1", "arg-key", self.ARG_MODEL)

        mock_config.set.assert_not_called()
        mock_config.save.assert_not_called()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_missing_url_or_key_reported(self, mock_config):
        """参数缺失时给出明确错误，且不触碰配置"""
        t = self._make_translator(mock_config)

        ok, msg = t.test_connection("", "", self.ARG_MODEL)
        assert ok is False
        assert "API URL or API Key is not configured" in msg
        mock_config.set.assert_not_called()
        mock_config.save.assert_not_called()


class TestModelOverrideAndFallback:
    """v0.3.14 回归：model 可显式覆盖，且回退值必须被 DeepSeek 端点认识"""

    def _make_translator(self, mock_config, config_model):
        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.deepseek.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return config_model
            return default

        mock_config.get.side_effect = mock_get
        from core.llm_translator import LLMTranslator
        return LLMTranslator()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_build_payload_honours_model_override(self, mock_config):
        t = self._make_translator(mock_config, "MODEL-FROM-CONFIG")
        payload = t._build_payload("Hello", "en", "zh", stream=False, model="override-model")
        assert payload["model"] == "override-model"

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_empty_model_falls_back_to_deepseek(self, mock_config):
        """空模型时回退到 deepseek-flash，而不是端点不认识的 mimo-v2.5-pro"""
        t = self._make_translator(mock_config, "")
        payload = t._build_payload("Hello", "en", "zh", stream=False)
        assert payload["model"] == "deepseek-flash"

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_api_url_override(self, mock_config):
        t = self._make_translator(mock_config, "deepseek-flash")
        assert t._build_api_url("https://example.com/v1") == \
            "https://example.com/v1/chat/completions"
        assert t._build_api_url() == "https://api.deepseek.com/v1/chat/completions"


class TestLLMURLBuilding:
    """Test API URL building logic"""

    @patch('core.llm_translator.config')
    def test_url_with_chat_completions_unchanged(self, mock_config):
        mock_config.get.return_value = "https://api.example.com/v1/chat/completions"
        from core.llm_translator import LLMTranslator
        t = LLMTranslator()
        assert t._build_api_url() == "https://api.example.com/v1/chat/completions"

    @patch('core.llm_translator.config')
    def test_url_ending_with_v1(self, mock_config):
        mock_config.get.return_value = "https://api.example.com/v1"
        from core.llm_translator import LLMTranslator
        t = LLMTranslator()
        assert t._build_api_url() == "https://api.example.com/v1/chat/completions"

    @patch('core.llm_translator.config')
    def test_url_base(self, mock_config):
        mock_config.get.return_value = "https://api.example.com"
        from core.llm_translator import LLMTranslator
        t = LLMTranslator()
        assert t._build_api_url() == "https://api.example.com/v1/chat/completions"

    @patch('core.llm_translator.config')
    def test_url_with_trailing_slash(self, mock_config):
        mock_config.get.return_value = "https://api.example.com/v1/"
        from core.llm_translator import LLMTranslator
        t = LLMTranslator()
        assert t._build_api_url() == "https://api.example.com/v1/chat/completions"


class TestLLMRetry:
    """Test retry logic"""

    def _make_translator(self, mock_config):
        def mock_get(key, default=""):
            if key == "api_url":
                return "https://api.openai.com/v1"
            elif key == "api_key":
                return "test-key"
            elif key == "api_model":
                return "gpt-3.5-turbo"
            return default

        mock_config.get.side_effect = mock_get
        from core.llm_translator import LLMTranslator
        return LLMTranslator()

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    def test_retryable_status_detection(self, mock_config):
        t = self._make_translator(mock_config)
        assert t._is_retryable_error(ValueError("API error (429): rate limited")) is True
        assert t._is_retryable_error(ValueError("API error (500): oops")) is True
        assert t._is_retryable_error(ValueError("API error (503): busy")) is True
        assert t._is_retryable_error(ValueError("API error (401): unauthorized")) is False
        assert t._is_retryable_error(ValueError("API error (400): bad request")) is False

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    @patch('core.llm_translator.LLMTranslator._get_client')
    @patch('core.llm_translator.LLMTranslator._wait_before_retry')
    def test_retry_on_500_then_success(self, mock_wait, mock_client, mock_config):
        t = self._make_translator(mock_config)

        # 让 _get_client() 返回 mock_client 本身
        mock_client.return_value = mock_client

        # 第一次 500，第二次 200
        err_response = Mock()
        err_response.status_code = 500
        err_response.json.return_value = {"error": {"message": "server error"}}
        err_response.text = "server error"

        ok_response = Mock()
        ok_response.status_code = 200
        ok_response.json.return_value = {"choices": [{"message": {"content": "你好"}}]}

        mock_client.post.side_effect = [err_response, ok_response]

        result = t._call_api("Hello", "en", "zh")
        assert result == "你好"
        assert mock_wait.call_count == 1  # 重试了一次

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    @patch('core.llm_translator.LLMTranslator._get_client')
    @patch('core.llm_translator.LLMTranslator._wait_before_retry')
    def test_no_retry_on_401(self, mock_wait, mock_client, mock_config):
        t = self._make_translator(mock_config)

        # 让 _get_client() 返回 mock_client 本身
        mock_client.return_value = mock_client

        err_response = Mock()
        err_response.status_code = 401
        err_response.json.return_value = {"error": {"message": "unauthorized"}}
        err_response.text = "unauthorized"

        mock_client.post.return_value = err_response

        import pytest
        with pytest.raises(ValueError):
            t._call_api("Hello", "en", "zh")
        assert mock_wait.call_count == 0  # 不重试