"""
Integration tests for complete translation flow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTranslationFlow:
    """Test complete translation flow"""

    @patch('core.llm_translator.HTTPX_AVAILABLE', True)
    @patch('core.llm_translator.config')
    @patch('core.language_detector.LANGDETECT_AVAILABLE', False)
    def test_online_translation_flow(self, mock_config):
        """Test online translation with LLM"""
        from core.llm_translator import LLMTranslator
        from core.language_detector import LanguageDetector
        from core.translator import TranslatorManager

        # Reset singletons
        TranslatorManager._instance = None
        LanguageDetector._instance = None

        # Setup config mock
        mock_config.get.side_effect = lambda key, default=None: {
            "api_url": "https://api.example.com",
            "api_key": "test-key",
            "api_model": "gpt-3.5-turbo",
            "engine": "online"
        }.get(key, default)

        # Create instances
        llm = LLMTranslator()
        manager = TranslatorManager()
        manager.register_engine(llm)

        # Mock the API call
        with patch.object(llm, '_call_api') as mock_api:
            mock_api.return_value = "你好世界"
            
            # Test translation
            result = manager.translate("Hello world", "en", "zh", "online")
            assert result.success is True
            assert result.translated_text == "你好世界"
            assert result.engine == "online"


class TestHistoryFlow:
    """Test history management flow"""

    def test_history_add_and_retrieve(self):
        """Test adding and retrieving history"""
        from models.history import History
        from models.database import init_db

        # Initialize database
        init_db()

        # Add history record
        record = History.add(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="online"
        )

        assert record is not None
        assert record.source_text == "Hello"
        assert record.translated_text == "你好"

        # Retrieve recent records
        recent = History.get_recent()
        assert len(recent) > 0

        # Clean up
        History.delete_by_id(record.id)


class TestSettingsFlow:
    """Test settings management flow"""

    def test_settings_save_and_load(self):
        """Test saving and loading settings"""
        from app.config import Config
        from pathlib import Path
        import tempfile
        import json

        # 保存原始单例状态
        original_instance = Config._instance
        original_initialized = Config._instance._initialized if Config._instance else False

        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
            json.dump({"engine": "online"}, f)

        try:
            # 重置单例，使用临时路径
            Config._instance = None
            config = Config(temp_path)

            # 保存设置
            config.set("api_url", "https://api.example.com")
            config.save()

            # 重新加载并验证
            config.load()
            assert config.get("api_url") == "https://api.example.com"
        finally:
            # 恢复原始单例
            Config._instance = original_instance
            if original_instance:
                original_instance._initialized = original_initialized
            temp_path.unlink()
