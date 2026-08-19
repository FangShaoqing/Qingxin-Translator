"""
Qingxin Translator - Windows OCR Engine
使用 Windows 10/11 自带 OCR（Windows.Media.Ocr）识别图片中的文字

零依赖方案：通过 PowerShell 调用系统 WinRT OCR，无需额外模型或 Python 包。
"""

import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

from core.logger import log


class WindowsOcr:
    """Windows 自带 OCR 引擎（线程安全）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._available = None  # 懒检测
        self._lock = threading.Lock()
        self._script_path = Path(__file__).parent / "ocr.ps1"
        self._initialized = True

    def _check_available(self) -> bool:
        """检查 OCR 脚本是否存在"""
        if self._available is not None:
            return self._available
        self._available = self._script_path.exists()
        if not self._available:
            log.warning(f"OCR script not found: {self._script_path}")
        return self._available

    def ocr_image(self, image_bytes: bytes) -> str:
        """
        识别图片中的文字

        Args:
            image_bytes: 图片原始字节（PNG/JPEG 等）

        Returns:
            str: 识别出的文本（可能为空）
        """
        if not self._check_available():
            return ""

        with self._lock:
            try:
                # 写入临时图片文件
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(image_bytes)
                    tmp_path = tmp.name

                try:
                    # 调用 PowerShell 执行 OCR
                    cmd = [
                        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", str(self._script_path),
                        "-ImagePath", tmp_path
                    ]
                    proc = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=60,
                        encoding="utf-8",
                        errors="replace"
                    )

                    output = proc.stdout.strip()

                    # 解析 base64 输出（避免编码问题）
                    if output.startswith("__OCR_BASE64__:"):
                        import base64
                        b64_data = output[len("__OCR_BASE64__:"):].strip()
                        text = base64.b64decode(b64_data).decode("utf-8", errors="replace").strip()
                        log.info(f"OCR result ({len(text)} chars): '{text[:100]}...'")
                        return text
                    if output.startswith("__OCR_ERROR__:"):
                        import base64
                        b64_data = output[len("__OCR_ERROR__:"):].strip()
                        err_msg = base64.b64decode(b64_data).decode("utf-8", errors="replace")
                        log.warning(f"OCR error: {err_msg}")
                        return ""
                    if "__OCR_EMPTY__" in output:
                        log.info("OCR: no text recognized")
                        return ""

                    # 兼容旧格式（纯文本）
                    if output:
                        log.info(f"OCR result ({len(output)} chars): '{output[:100]}...'")
                        return output
                    return ""

                finally:
                    # 清理临时文件
                    try:
                        Path(tmp_path).unlink(missing_ok=True)
                    except Exception:
                        pass

            except subprocess.TimeoutExpired:
                log.error("OCR timed out")
                return ""
            except Exception as e:
                log.error(f"OCR failed: {e}", exc_info=True)
                return ""


# 全局实例
ocr_engine = WindowsOcr()
