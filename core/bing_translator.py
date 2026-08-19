"""
Qingxin Translator - Bing Translator Engine
Bing 免费翻译引擎（备用引擎）

使用微软翻译的边缘免费端点（无需 API Key）：
- 获取 token: GET https://edge.microsoft.com/translate/auth
- 翻译:      GET https://api-edge.cognitive.microsofttranslator.com/translate

注意：这是非官方免费端点，仅作为主 LLM 引擎失败时的备用方案。
"""

import threading
import time
from typing import Optional

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from core.translator import TranslatorEngine, TranslationEngine, TranslationResult
from core.logger import log


# 语言代码映射（微软 API 使用 RFC 3066 代码，与语言检测器基本一致）
# 检测器可能返回的代码与 Bing 需要的不完全一致，做一层映射
LANG_MAP = {
    "zh": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-tw": "zh-Hant",
    "en": "en",
    "ja": "ja",
    "ko": "ko",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "ru": "ru",
    "it": "it",
    "pt": "pt",
    "ar": "ar",
}


class BingTranslator(TranslatorEngine):
    """
    Bing 免费翻译引擎（备用）
    仅支持非流式翻译
    """

    AUTH_URL = "https://edge.microsoft.com/translate/auth"
    TRANSLATE_URL = "https://api-edge.cognitive.microsofttranslator.com/translate"

    def __init__(self):
        self._available = HTTPX_AVAILABLE
        self._token: Optional[str] = None
        self._token_expire_at: float = 0.0
        self._token_lock = threading.Lock()
        self._client: Optional[httpx.Client] = None

    @property
    def engine_name(self) -> str:
        return "bing"

    @property
    def engine_type(self) -> TranslationEngine:
        return TranslationEngine.ONLINE

    def _get_client(self) -> httpx.Client:
        """获取或创建 HTTP 客户端"""
        if self._client is None or self._client.is_closed:
            from core.proxy_manager import get_proxy_url
            proxy = get_proxy_url()
            self._client = httpx.Client(
                timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
                proxy=proxy
            )
        return self._client

    def _get_token(self) -> Optional[str]:
        """获取/刷新认证 token（约 10 分钟有效，缓存 8 分钟）"""
        now = time.time()
        if self._token and now < self._token_expire_at:
            return self._token

        with self._token_lock:
            # 双重检查
            if self._token and now < self._token_expire_at:
                return self._token

            try:
                client = self._get_client()
                resp = client.get(self.AUTH_URL)
                if resp.status_code != 200:
                    log.warning(f"Bing auth failed: HTTP {resp.status_code}")
                    return None
                token = resp.text.strip()
                if not token:
                    log.warning("Bing auth returned empty token")
                    return None
                self._token = token
                self._token_expire_at = now + 8 * 60  # 8 分钟缓存
                log.info("Bing auth token refreshed")
                return token
            except Exception as e:
                log.warning(f"Bing auth error: {e}")
                return None

    def _map_lang(self, lang: str) -> str:
        """映射语言代码到 Bing 格式"""
        return LANG_MAP.get(lang, lang)

    def is_available(self) -> bool:
        """Bing 引擎始终可用（无需配置）"""
        return self._available

    def detect_language(self, text: str) -> str:
        """检测语言（复用全局语言检测器）"""
        from core.language_detector import language_detector
        return language_detector.detect(text)

    def translate(self, text: str, source_lang: str, target_lang: str,
                  is_mixed: bool = False) -> TranslationResult:
        """翻译文本（非流式）"""
        if not self._available:
            return self._create_error_result(text, source_lang, target_lang, "httpx is not installed")

        if not text or not text.strip():
            return self._create_error_result(text, source_lang, target_lang, "Empty text")

        # 自动检测源语言
        if source_lang == "auto":
            source_lang = self.detect_language(text)

        # 相同语言直接返回
        if source_lang == target_lang and not is_mixed:
            return TranslationResult(
                source_text=text, translated_text=text,
                source_lang=source_lang, target_lang=target_lang,
                engine=self.engine_name, success=True
            )

        try:
            translated_text = self._call_api(text, source_lang, target_lang)
            return TranslationResult(
                source_text=text, translated_text=translated_text,
                source_lang=source_lang, target_lang=target_lang,
                engine=self.engine_name, success=True
            )
        except Exception as e:
            return self._create_error_result(text, source_lang, target_lang, str(e))

    def _call_api(self, text: str, source_lang: str, target_lang: str) -> str:
        """调用 Bing 翻译 API"""
        token = self._get_token()
        if not token:
            raise ValueError("无法获取 Bing 翻译授权 token")

        from_lang = self._map_lang(source_lang)
        to_lang = self._map_lang(target_lang)

        url = f"{self.TRANSLATE_URL}?api-version=3.0&from={from_lang}&to={to_lang}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        body = [{"Text": text}]

        log.info(f"Bing translate: {source_lang} -> {target_lang} (len={len(text)})")

        client = self._get_client()
        resp = client.post(url, headers=headers, json=body)

        if resp.status_code != 200:
            raise ValueError(f"Bing API error (HTTP {resp.status_code}): {resp.text[:200]}")

        result = resp.json()
        try:
            translated_text = result[0]["translations"][0]["text"]
        except (IndexError, KeyError, TypeError) as e:
            raise ValueError(f"Bing API 返回格式异常: {e}")

        if not translated_text.strip():
            raise ValueError("Bing 返回空译文")

        log.info(f"Bing translate OK: '{translated_text[:50]}...'")
        return translated_text

    def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            self._client.close()


# 全局实例
bing_translator = BingTranslator()
