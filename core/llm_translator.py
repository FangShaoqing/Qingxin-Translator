"""
Qingxin Translator - LLM Online Translation Engine
大模型在线翻译引擎
支持 OpenAI 兼容 API（如 ChatGPT、Deepseek、本地 Ollama 等）
"""

import json
import threading
from typing import Optional, Callable

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from core.translator import TranslatorEngine, TranslationEngine, TranslationResult
from core.language_detector import language_detector
from core.logger import log
from app.config import config


# 语言名称映射（用于提示词）
LANG_NAMES = {
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
    "it": "Italiano",
    "pt": "Português",
    "ar": "العربية",
}

# 翻译提示词（平衡速度和质量）
SYSTEM_PROMPT_TEMPLATE = """You are a professional translator. Translate text from {source} to {target}.

Rules:
1. Output ONLY the translated text, nothing else.
2. Preserve original meaning accurately.
3. Keep proper nouns, brand names, and game titles as-is or use their well-known translations.
4. No explanations, no quotes, no extra formatting."""

# 译文质量模式提示词
TRANSLATE_MODE_PROMPTS = {
    "literal": SYSTEM_PROMPT_TEMPLATE,
    "paraphrase": """You are a professional translator. Translate text from {source} to {target} using free paraphrase.

Rules:
1. Output ONLY the translated text, nothing else.
2. Faithfully convey the meaning, but express it in a natural way that a native {target} speaker would use.
3. Do not stick rigidly to the original sentence structure.
4. Keep proper nouns, brand names, and game titles as-is or use their well-known translations.
5. No explanations, no quotes, no extra formatting.""",
    "polish": """You are a professional translator and editor. Translate text from {source} to {target} with careful polishing.

Rules:
1. Output ONLY the polished translated text, nothing else.
2. Faithfully preserve the original meaning.
3. Elevate the language: refine word choice, improve flow and rhythm, make it elegant and readable.
4. Keep proper nouns, brand names, and game titles as-is or use their well-known translations.
5. No explanations, no quotes, no extra formatting.""",
}


class LLMTranslator(TranslatorEngine):
    """
    大模型在线翻译引擎
    支持 OpenAI 兼容 API（流式 + 非流式）
    """
    
    def __init__(self):
        self._available = HTTPX_AVAILABLE
        self._client: Optional[httpx.Client] = None
        self._client_lock = threading.Lock()
    
    @property
    def engine_name(self) -> str:
        return "online"
    
    @property
    def engine_type(self) -> TranslationEngine:
        return TranslationEngine.ONLINE
    
    def _get_client(self) -> httpx.Client:
        """获取或创建复用的 HTTP 客户端（连接池）"""
        if self._client is None or self._client.is_closed:
            with self._client_lock:
                if self._client is None or self._client.is_closed:
                    from core.proxy_manager import get_proxy_url
                    proxy = get_proxy_url()
                    self._client = httpx.Client(
                        timeout=httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0),
                        proxy=proxy,
                        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
                    )
        return self._client
    
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        if not self._available:
            return False
        
        api_url = config.get("api_url", "")
        api_key = config.get("api_key", "")
        
        return bool(api_url and api_key)
    
    def detect_language(self, text: str) -> str:
        """检测语言"""
        return language_detector.detect(text)
    
    def _build_api_url(self) -> str:
        """构建 API URL"""
        api_url = config.get("api_url", "").strip().rstrip("/")
        
        if api_url.endswith("/chat/completions"):
            return api_url
        
        if api_url.endswith("/v1"):
            return api_url + "/chat/completions"
        
        return api_url + "/v1/chat/completions"
    
    def _build_payload(self, text: str, source_lang: str, target_lang: str, stream: bool = False, is_mixed: bool = False) -> dict:
        """构建请求 payload（兼容 MiMo API）"""
        source_name = LANG_NAMES.get(source_lang, source_lang)
        target_name = LANG_NAMES.get(target_lang, target_lang)
        
        if is_mixed and target_lang == "en":
            # 中英混合 → 英文
            system_prompt = "You are a translator. Output ONLY the translated text."
            user_prompt = (
                "[MIXED MODE] The following text contains both Chinese and English. "
                "You MUST translate ALL Chinese characters into English. "
                "Keep English words like pyperclip, import, SendInput exactly as they are. "
                "Do NOT output any Chinese characters in your response.\n\n"
                f"Text: {text}"
            )
            log.info(f"LLM: using MIXED prompt, user_prompt={user_prompt[:100]}")
        elif is_mixed and target_lang == "zh":
            # 中英混合 → 中文
            system_prompt = "You are a translator. 只输出译文。"
            user_prompt = (
                "The following text contains both Chinese and English. "
                "将所有英文部分翻译成中文。中文部分保持不变。"
                "不要把中文翻译成英文。\n\n"
                f"{text}"
            )
        else:
            # 根据译文质量模式选择 system prompt（直译/意译/润色）
            mode = config.get("translate_mode", "literal")
            mode_prompt = TRANSLATE_MODE_PROMPTS.get(mode, SYSTEM_PROMPT_TEMPLATE)
            system_prompt = mode_prompt.format(source=source_name, target=target_name)
            user_prompt = f"Translate the following {source_name} text to {target_name}:\n{text}"
            log.info(f"LLM: translate_mode={mode}")
        
        model = config.get("api_model") or "mimo-v2.5-pro"
        
        # 根据模型选择正确的 token 参数名
        # MiMo: max_completion_tokens | DeepSeek/GLM/其他: max_tokens
        token_key = "max_completion_tokens" if "mimo" in model.lower() else "max_tokens"
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            token_key: 1024,
            "stream": stream,
            "thinking": {"type": "disabled"},
        }
        
        return payload
    
    def translate(self, text: str, source_lang: str, target_lang: str, is_mixed: bool = False) -> TranslationResult:
        """
        翻译文本（非流式，兼容旧接口）
        """
        if not self._available:
            return self._create_error_result(text, source_lang, target_lang, "httpx is not installed")
        
        if not self.is_available():
            return self._create_error_result(text, source_lang, target_lang, "API URL or API Key is not configured")
        
        if not text or not text.strip():
            return self._create_error_result(text, source_lang, target_lang, "Empty text")
        
        if source_lang == "auto":
            source_lang = self.detect_language(text)
        
        if source_lang == target_lang and not is_mixed:
            return TranslationResult(
                source_text=text, translated_text=text,
                source_lang=source_lang, target_lang=target_lang,
                engine=self.engine_name, success=True
            )
        
        try:
            translated_text = self._call_api(text, source_lang, target_lang, is_mixed=is_mixed)
            return TranslationResult(
                source_text=text, translated_text=translated_text,
                source_lang=source_lang, target_lang=target_lang,
                engine=self.engine_name, success=True
            )
        except Exception as e:
            error_msg = str(e)
            # 网络错误提供更友好的提示
            if any(kw in error_msg.lower() for kw in ('getaddrinfo', 'connect', 'timeout', 'connection')):
                error_msg = "网络连接失败，请检查网络或代理设置"
                # 关闭失效的客户端，下次重新创建
                self._reset_client()
            return self._create_error_result(text, source_lang, target_lang, error_msg)
    
    def translate_stream(self, text: str, source_lang: str, target_lang: str,
                         on_chunk: Callable[[str], None]) -> TranslationResult:
        """
        流式翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言代码
            target_lang: 目标语言代码
            on_chunk: 回调函数，每收到一个文本片段就调用
            
        Returns:
            TranslationResult: 翻译结果
        """
        log.info(f"translate_stream called: source={source_lang}, target={target_lang}, text='{text[:30]}...'")
        
        if not self._available:
            return self._create_error_result(text, source_lang, target_lang, "httpx is not installed")
        
        if not self.is_available():
            return self._create_error_result(text, source_lang, target_lang, "API URL or API Key is not configured")
        
        if not text or not text.strip():
            return self._create_error_result(text, source_lang, target_lang, "Empty text")
        
        if source_lang == "auto":
            source_lang = self.detect_language(text)
            log.info(f"Re-detected language from 'auto' to: {source_lang}")
        
        if source_lang == target_lang:
            log.info(f"Source and target are same ({source_lang}), returning original text")
            on_chunk(text)
            return TranslationResult(
                source_text=text, translated_text=text,
                source_lang=source_lang, target_lang=target_lang,
                engine=self.engine_name, success=True
            )
        
        try:
            translated_text = self._call_api_stream(text, source_lang, target_lang, on_chunk)
            return TranslationResult(
                source_text=text, translated_text=translated_text,
                source_lang=source_lang, target_lang=target_lang,
                engine=self.engine_name, success=True
            )
        except Exception as e:
            error_msg = str(e)
            if any(kw in error_msg.lower() for kw in ('getaddrinfo', 'connect', 'timeout', 'connection')):
                error_msg = "网络连接失败，请检查网络或代理设置"
                self._reset_client()
            return self._create_error_result(text, source_lang, target_lang, error_msg)
    
    # ========== 重试机制 ==========
    
    # 可重试的 HTTP 状态码（429 限流、5xx 服务端错误）
    RETRYABLE_STATUS = {429, 500, 502, 503, 504}
    # 最大尝试次数（1 次原始 + 2 次重试）
    MAX_ATTEMPTS = 3
    # 重试退避基数（秒），每次重试等待 base * 2^attempt
    RETRY_BACKOFF_BASE = 1.0
    
    def _is_retryable_error(self, e: Exception) -> bool:
        """判断错误是否值得重试"""
        # 网络层错误
        if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout,
                          httpx.ReadTimeout, httpx.ReadError,
                          httpx.PoolTimeout, httpx.RemoteProtocolError)):
            return True
        
        # HTTP 状态码错误
        if isinstance(e, httpx.HTTPStatusError):
            return e.response.status_code in self.RETRYABLE_STATUS
        
        # API 业务错误（通过 ValueError 抛出，携带状态码）
        if isinstance(e, ValueError):
            msg = str(e)
            for code in self.RETRYABLE_STATUS:
                if f"({code})" in msg:
                    return True
        
        return False
    
    def _wait_before_retry(self, attempt: int):
        """指数退避等待"""
        import time
        wait = self.RETRY_BACKOFF_BASE * (2 ** attempt)
        log.info(f"Retrying in {wait:.1f}s... (attempt {attempt + 1}/{self.MAX_ATTEMPTS})")
        time.sleep(wait)
    
    def _call_api(self, text: str, source_lang: str, target_lang: str, is_mixed: bool = False) -> str:
        """调用 LLM API（非流式，带重试）"""
        api_url = self._build_api_url()
        api_key = config.get("api_key", "")
        payload = self._build_payload(text, source_lang, target_lang, stream=False, is_mixed=is_mixed)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        log.info(f"Calling API: {api_url} (model: {payload['model']})")
        log.info(f"Request payload keys: {list(payload.keys())}")
        
        last_error: Exception = None
        for attempt in range(self.MAX_ATTEMPTS):
            try:
                client = self._get_client()
                response = client.post(api_url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    # 从响应体提取 API 错误信息
                    api_err = ""
                    try:
                        err_body = response.json()
                        api_err = err_body.get("error", {}).get("message", "")
                    except Exception:
                        api_err = response.text[:200]
                    
                    error_msg = api_err or f"HTTP {response.status_code}"
                    last_error = ValueError(f"API error ({response.status_code}): {error_msg}")
                    
                    if response.status_code in self.RETRYABLE_STATUS and attempt < self.MAX_ATTEMPTS - 1:
                        self._wait_before_retry(attempt)
                        continue
                    raise last_error
                
                result = response.json()
                log.debug(f"API response: {result}")
                
                # 安全解析响应
                choices = result.get("choices", [])
                if not choices:
                    error_msg = result.get("error", {}).get("message", "Empty response from API")
                    raise ValueError(f"API returned no choices: {error_msg}")
                
                message = choices[0].get("message", {})
                translated_text = message.get("content", "").strip()
                
                if not translated_text:
                    raise ValueError("API returned empty translation")
                
                log.info(f"Translation OK: '{translated_text[:50]}...'")
                return translated_text
                
            except (httpx.ConnectError, httpx.ConnectTimeout,
                    httpx.ReadTimeout, httpx.ReadError,
                    httpx.PoolTimeout, httpx.RemoteProtocolError) as e:
                last_error = e
                log.warning(f"Network error (attempt {attempt + 1}/{self.MAX_ATTEMPTS}): {e}")
                if attempt < self.MAX_ATTEMPTS - 1:
                    self._wait_before_retry(attempt)
                    continue
                # 网络错误时重置客户端，下次请求重新建立连接
                self._reset_client()
        
        raise last_error
    
    def _call_api_stream(self, text: str, source_lang: str, target_lang: str,
                         on_chunk: Callable[[str], None]) -> str:
        """调用 LLM API（流式，带重试）
        
        重试策略：仅在尚未收到任何内容时重试（避免重复输出）。
        已收到部分内容后中断 → 直接抛错，不重试。
        """
        api_url = self._build_api_url()
        api_key = config.get("api_key", "")
        payload = self._build_payload(text, source_lang, target_lang, stream=True)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        log.info(f"Calling API (stream): {api_url} (model: {payload['model']})")
        
        last_error: Exception = None
        
        for attempt in range(self.MAX_ATTEMPTS):
            full_text = []
            received_any = False
            
            try:
                with httpx.Client(timeout=httpx.Timeout(connect=5.0, read=60.0, write=5.0, pool=5.0)) as client:
                    with client.stream("POST", api_url, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            err_text = response.read().decode("utf-8", errors="replace")
                            api_err = ""
                            try:
                                import json as _json
                                err_body = _json.loads(err_text)
                                api_err = err_body.get("error", {}).get("message", "")
                            except Exception:
                                api_err = err_text[:200]
                            
                            error_msg = api_err or f"HTTP {response.status_code}"
                            last_error = ValueError(f"API error ({response.status_code}): {error_msg}")
                            
                            if response.status_code in self.RETRYABLE_STATUS and attempt < self.MAX_ATTEMPTS - 1:
                                self._wait_before_retry(attempt)
                                continue
                            raise last_error
                        
                        for line in response.iter_lines():
                            if not line:
                                continue
                            
                            # 跳过 SSE 前缀
                            if line.startswith("data: "):
                                line = line[6:]
                            
                            if line.strip() == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(line)
                                log.debug(f"Stream chunk: {chunk}")
                                
                                # 安全解析 choices
                                choices = chunk.get("choices", [])
                                if not choices:
                                    # 检查是否有错误信息
                                    error = chunk.get("error")
                                    if error:
                                        raise ValueError(f"Stream error: {error.get('message', 'Unknown error')}")
                                    continue
                                
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    full_text.append(content)
                                    received_any = True
                                    on_chunk(content)
                            except json.JSONDecodeError:
                                continue
                
                result = "".join(full_text).strip()
                
                if not result:
                    raise ValueError("Stream returned empty translation")
                
                log.info(f"Stream translation OK: '{result[:50]}...'")
                return result
                
            except (httpx.ConnectError, httpx.ConnectTimeout,
                    httpx.ReadTimeout, httpx.ReadError,
                    httpx.PoolTimeout, httpx.RemoteProtocolError) as e:
                last_error = e
                # 已收到内容则不再重试（避免重复输出）
                if received_any:
                    log.warning(f"Stream interrupted after receiving content: {e}")
                    raise e
                log.warning(f"Stream network error (attempt {attempt + 1}/{self.MAX_ATTEMPTS}): {e}")
                if attempt < self.MAX_ATTEMPTS - 1:
                    self._wait_before_retry(attempt)
                    continue
                self._reset_client()
            except ValueError as e:
                last_error = e
                # 流式业务错误：未收到内容且可重试状态码 → 重试
                if not received_any and self._is_retryable_error(e) and attempt < self.MAX_ATTEMPTS - 1:
                    self._wait_before_retry(attempt)
                    continue
                raise e
        
        raise last_error
    
    def test_connection(self) -> tuple[bool, str]:
        """测试 API 连接（使用短超时）"""
        log.info("Testing LLM connection...")
        
        if not self._available:
            return False, "httpx is not installed"
        
        if not self.is_available():
            return False, "API URL or API Key is not configured"
        
        try:
            # 使用短超时发送测试请求
            api_url = self._build_api_url()
            api_key = config.get("api_key", "")
            payload = self._build_payload("Hello", "en", "zh", stream=False)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            log.info(f"Test connection: url={api_url}, model={payload.get('model')}, keys={list(payload.keys())}")
            
            with httpx.Client(timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)) as client:
                response = client.post(api_url, headers=headers, json=payload)
                
                log.info(f"Test response: status={response.status_code}, body={str(response.text)[:300]}")
                
                if response.status_code != 200:
                    api_err = ""
                    try:
                        err_body = response.json()
                        api_err = err_body.get("error", {}).get("message", "")
                    except Exception:
                        api_err = response.text[:200]
                    if api_err:
                        return False, f"API error ({response.status_code}): {api_err}"
                    return False, f"HTTP {response.status_code}"
                
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    return True, "Connection successful"
                return False, "API returned empty response"
                
        except Exception as e:
            error_msg = str(e)
            log.error(f"Test connection failed: {error_msg}")
            if any(kw in error_msg.lower() for kw in ('getaddrinfo', 'connect', 'timeout', 'connection')):
                return False, "网络连接失败，请检查网络或代理设置"
            return False, error_msg
    
    def close(self):
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            self._client.close()
    
    def _reset_client(self):
        """重置 HTTP 客户端（网络错误后调用，下次请求重新创建）"""
        with self._client_lock:
            if self._client and not self._client.is_closed:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = None


# 全局实例
llm_translator = LLMTranslator()
