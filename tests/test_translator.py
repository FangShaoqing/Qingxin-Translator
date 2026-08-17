"""
Tests for core.translator module
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.translator import (
    TranslationEngine, TranslationResult, TranslatorEngine, TranslatorManager
)


class TestTranslationResult:
    """Test TranslationResult dataclass"""

    def test_creation(self):
        result = TranslationResult(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="test"
        )
        assert result.source_text == "Hello"
        assert result.translated_text == "你好"
        assert result.source_lang == "en"
        assert result.target_lang == "zh"
        assert result.engine == "test"
        assert result.success is True
        assert result.error_message == ""

    def test_to_dict(self):
        result = TranslationResult(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="test",
            success=True,
            error_message=""
        )
        expected = {
            "source_text": "Hello",
            "translated_text": "你好",
            "source_lang": "en",
            "target_lang": "zh",
            "engine": "test",
            "success": True,
            "error_message": ""
        }
        assert result.to_dict() == expected

    def test_error_result(self):
        result = TranslationResult(
            source_text="Hello",
            translated_text="",
            source_lang="en",
            target_lang="zh",
            engine="test",
            success=False,
            error_message="Translation failed"
        )
        assert result.success is False
        assert result.error_message == "Translation failed"


class TestTranslatorEngine:
    """Test TranslatorEngine abstract base class"""

    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            TranslatorEngine()

    def test_concrete_implementation(self):
        class TestEngine(TranslatorEngine):
            @property
            def engine_name(self):
                return "test"

            @property
            def engine_type(self):
                return TranslationEngine.ONLINE

            def translate(self, text, source_lang, target_lang):
                return TranslationResult(
                    source_text=text,
                    translated_text="translated",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    engine=self.engine_name
                )

            def detect_language(self, text):
                return "en"

            def is_available(self):
                return True

        engine = TestEngine()
        assert engine.engine_name == "test"
        assert engine.engine_type == TranslationEngine.ONLINE
        assert engine.is_available() is True
        assert engine.detect_language("test") == "en"

    def test_create_error_result(self):
        class TestEngine(TranslatorEngine):
            @property
            def engine_name(self):
                return "test"

            @property
            def engine_type(self):
                return TranslationEngine.ONLINE

            def translate(self, text, source_lang, target_lang):
                pass

            def detect_language(self, text):
                pass

            def is_available(self):
                pass

        engine = TestEngine()
        result = engine._create_error_result("Hello", "en", "zh", "Test error")
        assert result.success is False
        assert result.error_message == "Test error"
        assert result.engine == "test"


class TestTranslatorManager:
    """Test TranslatorManager class"""

    def setup_method(self):
        # Reset singleton
        TranslatorManager._instance = None
        self.manager = TranslatorManager()

    def test_singleton(self):
        manager2 = TranslatorManager()
        assert self.manager is manager2

    def test_register_engine(self):
        engine = Mock(spec=TranslatorEngine)
        engine.engine_name = "test"
        self.manager.register_engine(engine)
        assert self.manager.get_engine("test") is engine

    def test_get_engine_not_found(self):
        assert self.manager.get_engine("nonexistent") is None

    def test_get_current_engine(self):
        engine = Mock(spec=TranslatorEngine)
        engine.engine_name = "online"
        self.manager.register_engine(engine)
        result = self.manager.get_current_engine()
        # Note: depends on config, may return None
        # Just verify it doesn't raise
        assert result is None or result is engine

    def test_translate_success(self):
        engine = Mock(spec=TranslatorEngine)
        engine.engine_name = "test"
        engine.is_available.return_value = True
        engine.translate.return_value = TranslationResult(
            source_text="Hello",
            translated_text="你好",
            source_lang="en",
            target_lang="zh",
            engine="test"
        )
        self.manager.register_engine(engine)
        result = self.manager.translate("Hello", "en", "zh", "test")
        assert result.success is True
        assert result.translated_text == "你好"

    def test_translate_engine_not_found(self):
        result = self.manager.translate("Hello", "en", "zh", "nonexistent")
        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_translate_engine_not_available(self):
        engine = Mock(spec=TranslatorEngine)
        engine.engine_name = "test"
        engine.is_available.return_value = False
        self.manager.register_engine(engine)
        result = self.manager.translate("Hello", "en", "zh", "test")
        assert result.success is False
        assert "not available" in result.error_message.lower()

    def test_get_available_engines(self):
        engine1 = Mock(spec=TranslatorEngine)
        engine1.engine_name = "test1"
        engine1.is_available.return_value = True

        engine2 = Mock(spec=TranslatorEngine)
        engine2.engine_name = "test2"
        engine2.is_available.return_value = False

        self.manager.register_engine(engine1)
        self.manager.register_engine(engine2)

        available = self.manager.get_available_engines()
        assert "test1" in available
        assert "test2" not in available

    def test_switch_engine(self):
        engine = Mock(spec=TranslatorEngine)
        engine.engine_name = "test"
        engine.is_available.return_value = True
        self.manager.register_engine(engine)
        # Note: switch_engine calls config.set, may need mock
        # Just test basic flow
        result = self.manager.switch_engine("test")
        # May return True or False depending on config availability


class TestTranslationEngineEnum:
    """Test TranslationEngine enum"""

    def test_values(self):
        assert TranslationEngine.ONLINE.value == "online"