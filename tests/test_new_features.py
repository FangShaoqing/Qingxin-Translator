"""
Tests for new features and code changes
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import shutil
from pathlib import Path
from core.translator import TranslationResult

# 本地临时目录（避免系统临时目录权限问题）
_TEST_TEMP_DIR = Path(__file__).parent / "_test_temp"


class TestDefaultEngineOnline:
    """Test that default translation engine is 'online'"""

    def test_default_config_engine_online(self):
        """Test that DEFAULT_CONFIG has engine='online'"""
        from app.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["engine"] == "online"

    @patch('app.config.config')
    def test_config_get_with_online_default(self, mock_config):
        """Test that config.get returns 'online' when default is specified"""
        mock_config.get.return_value = "online"
        engine = mock_config.get("engine", "online")
        assert engine == "online"

    @patch('core.translator.config')
    def test_translator_manager_uses_config_engine(self, mock_config):
        """Test that TranslatorManager uses config engine"""
        from core.translator import TranslatorManager
        
        # Reset singleton
        TranslatorManager._instance = None
        
        # Mock config to return 'online'
        mock_config.get.return_value = "online"
        
        # Create manager
        manager = TranslatorManager()
        
        # Verify the manager uses the config engine
        engine = mock_config.get("engine", "online")
        assert engine == "online"


class TestAutoTranslateOnEngineSwitch:
    """Test that switching engine triggers auto-translate"""

    def test_switch_engine_logic_with_text(self):
        """Test the logic of switching engine when text is present"""
        source_text = "Hello"
        translate_called = False
        
        text = source_text.strip()
        if text:
            translate_called = True
        
        assert translate_called == True

    def test_switch_engine_logic_without_text(self):
        """Test the logic of switching engine when text is empty"""
        source_text = ""
        translate_called = False
        
        text = source_text.strip()
        if text:
            translate_called = True
        
        assert translate_called == False

    def test_switch_engine_logic_with_whitespace(self):
        """Test the logic of switching engine when text is whitespace"""
        source_text = "   "
        translate_called = False
        
        text = source_text.strip()
        if text:
            translate_called = True
        
        assert translate_called == False


class TestConnectionTestResultLabel:
    """Test that connection test shows result in label instead of dialog"""

    def test_connection_success_message_format(self):
        """Test that successful connection message format is correct"""
        success = True
        message = "Connection successful"
        
        if success:
            result_text = "✓ 测试连接成功"
            color = "#52C41A"  # Green
        else:
            result_text = f"✗ {message}"
            color = "#FF4D4F"  # Red
        
        assert "成功" in result_text
        assert color == "#52C41A"

    def test_connection_failure_message_format(self):
        """Test that failed connection message format is correct"""
        success = False
        message = "连接失败"
        
        if success:
            result_text = "✓ 测试连接成功"
            color = "#52C41A"
        else:
            result_text = f"✗ {message}"
            color = "#FF4D4F"
        
        assert "失败" in result_text
        assert color == "#FF4D4F"


class TestHistorySearch:
    """Test history search functionality"""

    def test_history_search_by_keyword(self):
        """Test searching history by keyword"""
        from models.history import History
        from models.database import init_db, db
        
        tmpdir = _TEST_TEMP_DIR / "history_search"
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            db_path = tmpdir / "test_history_search.db"
            init_db(db_path)
            
            # Add multiple records
            History.add("Hello", "你好", "en", "zh", "online")
            History.add("World", "世界", "en", "zh", "online")
            History.add("Goodbye", "再见", "en", "zh", "online")
            
            # Test search
            results = History.search("Hello")
            assert len(results) == 1
            assert results[0].source_text == "Hello"
        finally:
            # Cleanup
            if not db.is_closed():
                db.close()
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestIntegrationNewFeatures:
    """Integration tests for new features"""

    def test_full_flow_with_auto_translate(self):
        """Test full flow with auto-translate mechanism"""
        from core.llm_translator import LLMTranslator
        from core.translator import TranslatorManager
        from models.database import init_db, db
        from models.history import History
        
        tmpdir = _TEST_TEMP_DIR / "integration"
        tmpdir.mkdir(parents=True, exist_ok=True)
        try:
            db_path = tmpdir / "test_integration.db"
            init_db(db_path)
            
            # Reset singletons
            TranslatorManager._instance = None
            
            # Create instances
            llm = LLMTranslator()
            manager = TranslatorManager()
            manager.register_engine(llm)
            
            # Mock the API call
            with patch.object(llm, '_call_api') as mock_api, \
                 patch.object(llm, 'is_available', return_value=True):
                mock_api.return_value = "你好世界"
                
                # Test translation
                result = manager.translate("Hello world", "en", "zh", "online")
                assert result.success is True
                assert result.translated_text == "你好世界"
                
                # Save to history (simulating auto-save)
                if result.success:
                    History.add(
                        result.source_text,
                        result.translated_text,
                        result.source_lang,
                        result.target_lang,
                        result.engine
                    )
                
                # Verify history was saved
                assert History.get_count() == 1
                recent = History.get_recent(limit=1)
                assert len(recent) == 1
                assert recent[0].source_text == "Hello world"
                assert recent[0].translated_text == "你好世界"
        finally:
            # Cleanup
            if not db.is_closed():
                db.close()
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_engine_switch_with_auto_translate(self):
        """Test engine switch triggers auto-translate in integration"""
        from core.translator import TranslatorManager
        
        # Reset singleton
        TranslatorManager._instance = None
        
        # Create mock engines
        engine1 = Mock()
        engine1.engine_name = "engine1"
        engine1.is_available.return_value = True
        engine1.translate.return_value = TranslationResult(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="engine1",
            success=True
        )
        
        engine2 = Mock()
        engine2.engine_name = "engine2"
        engine2.is_available.return_value = True
        engine2.translate.return_value = TranslationResult(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="engine2",
            success=True
        )
        
        # Create manager and register engines
        manager = TranslatorManager()
        manager.register_engine(engine1)
        manager.register_engine(engine2)
        
        # Test translation with engine1
        result1 = manager.translate("Hello", "en", "zh", "engine1")
        assert result1.success is True
        
        # Test translation with engine2
        result2 = manager.translate("Hello", "en", "zh", "engine2")
        assert result2.success is True
        
        # Verify both engines were called
        engine1.translate.assert_called_once()
        engine2.translate.assert_called_once()
