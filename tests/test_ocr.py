"""
Tests for core.ocr module
"""

from unittest.mock import Mock, patch, PropertyMock

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ocr import WindowsOcr


class TestWindowsOcr:
    """Test WindowsOcr class"""

    def test_singleton(self):
        a = WindowsOcr()
        b = WindowsOcr()
        assert a is b

    def test_not_available_when_script_missing(self):
        ocr = WindowsOcr()
        # 重置缓存状态，模拟全新实例
        ocr._available = None
        # 指向不存在的脚本
        original_path = ocr._script_path
        ocr._script_path = Path("nonexistent.ps1")
        try:
            assert ocr._check_available() is False
        finally:
            ocr._script_path = original_path

    @patch('subprocess.run')
    def test_ocr_success_base64(self, mock_run):
        import base64
        text = "你好世界"
        b64 = base64.b64encode(text.encode("utf-8")).decode()

        mock_proc = Mock()
        mock_proc.stdout = f"__OCR_BASE64__:{b64}"
        mock_run.return_value = mock_proc

        ocr = WindowsOcr()
        ocr._available = True  # 重置缓存状态
        result = ocr.ocr_image(b"fake-image-bytes")
        assert result == "你好世界"

    @patch('subprocess.run')
    def test_ocr_empty(self, mock_run):
        mock_proc = Mock()
        mock_proc.stdout = "__OCR_EMPTY__"
        mock_run.return_value = mock_proc

        ocr = WindowsOcr()
        ocr._available = True
        result = ocr.ocr_image(b"fake-image-bytes")
        assert result == ""

    @patch('subprocess.run')
    def test_ocr_error(self, mock_run):
        import base64
        err_msg = "OCR engine failed"
        b64 = base64.b64encode(err_msg.encode("utf-8")).decode()

        mock_proc = Mock()
        mock_proc.stdout = f"__OCR_ERROR__:{b64}"
        mock_run.return_value = mock_proc

        ocr = WindowsOcr()
        ocr._available = True
        result = ocr.ocr_image(b"fake-image-bytes")
        assert result == ""

    @patch('subprocess.run')
    def test_ocr_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("powershell", 60)

        ocr = WindowsOcr()
        ocr._available = True
        result = ocr.ocr_image(b"fake-image-bytes")
        assert result == ""

    @patch('subprocess.run')
    def test_ocr_plain_text_fallback(self, mock_run):
        """兼容旧格式：直接输出纯文本"""
        mock_proc = Mock()
        mock_proc.stdout = "Hello World"
        mock_run.return_value = mock_proc

        ocr = WindowsOcr()
        ocr._available = True
        result = ocr.ocr_image(b"fake-image-bytes")
        assert result == "Hello World"
