"""
Qingxin Translator - Secret Manager
API Key 加密存储（Windows DPAPI）

用 ctypes 调 crypt32.dll 的 CryptProtectData / CryptUnprotectData：
- 加密结果绑定当前 Windows 用户 + 机器
- 不引入 pywin32 依赖
- 备份恢复后跨机器无法解密 → 由调用方提示重新输入
"""

import base64
import ctypes
import ctypes.wintypes as wintypes
from typing import Optional

from core.logger import log

# CryptProtectData 标志
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.c_void_p)]


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    """构造 DATA_BLOB（pbData 指向字节缓冲区）"""
    buf = ctypes.create_string_buffer(data, len(data))
    blob = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.c_void_p))
    return blob


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    """从 DATA_BLOB 读取字节"""
    if blob.cbData == 0 or not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _free_blob(blob: DATA_BLOB):
    """释放 DPAPI 分配的缓冲区（LocalFree）"""
    if blob.pbData:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree(ctypes.cast(blob.pbData, ctypes.c_void_p))


def encrypt(plain_text: str) -> str:
    """用 DPAPI 加密文本，返回 base64 字符串（空输入返回空）"""
    if not plain_text:
        return ""
    try:
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPCWSTR,
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL

        data_in = _blob_from_bytes(plain_text.encode("utf-8"))
        data_out = DATA_BLOB()
        ok = crypt32.CryptProtectData(
            ctypes.byref(data_in),
            None, None, None, None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out),
        )
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        result = base64.b64encode(_bytes_from_blob(data_out)).decode("ascii")
        _free_blob(data_out)
        return result
    except Exception as e:
        log.error(f"DPAPI encrypt failed: {e}")
        return ""


def decrypt(encoded: str) -> Optional[str]:
    """解密 DPAPI base64 字符串；失败返回 None（如跨机器无法解密）"""
    if not encoded:
        return None
    try:
        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DATA_BLOB),
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(DATA_BLOB),
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL

        raw = base64.b64decode(encoded)
        data_in = _blob_from_bytes(raw)
        data_out = DATA_BLOB()
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None, None, None, None,
            CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(data_out),
        )
        if not ok:
            raise ctypes.WinError(ctypes.get_last_error())
        result = _bytes_from_blob(data_out).decode("utf-8", errors="ignore")
        _free_blob(data_out)
        return result
    except Exception as e:
        log.warning(f"DPAPI decrypt failed: {e}")
        return None
