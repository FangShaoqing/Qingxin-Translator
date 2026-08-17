"""
Qingxin Translator - UIA Text Selector
通过 Windows UI Automation 获取当前选中的文本（备用方案）
"""

import ctypes
import ctypes.wintypes
from typing import Optional

from core.logger import log


def get_selected_text_uia() -> Optional[str]:
    """通过 UIA 获取选中文本（备用方案，当前未使用）"""
    log.info("UIA: not implemented (clipboard method is primary)")
    return None


if __name__ == "__main__":
    text = get_selected_text_uia()
    print(f"Selected text: {text!r}" if text else "No text selected")
