"""
DAR-22 · OpenRouter Client with Model Fallbacks and Quota Protection.

Acceptance criteria (from DAR-22):
  ✓ Call OpenRouter chat completions with primary model and ranked fallback list
  ✓ 429, timeout, and auth errors map to clear user-facing messages
  ✓ The API key never appears in logs or responses
"""

from __future__ import annotations

import os
import json
import time
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("openrouter")

# Shortlisted free models per plan section 5 and ADR-0003
DEFAULT_MODELS = [
    "nvidia/nemotron-3.5-super-vl:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-7b-instruct:free",
    "openrouter/free",  # router fallback
]


@dataclass
class CompletionResponse:
    content: str
    model_used: str
    latency_ms: float
    usage: dict


class OpenRouterError(Exception):
    def __init__(self, message: str, user_facing_message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.user_facing_message = user_facing_message
        self.status_code = status_code


class OpenRouterClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        models: Optional[list[str]] = None,
        timeout: float = 20.0,
        max_tokens: int = 800,
        temperature: float = 0.2,
    ):
        # API key comes strictly from parameter or environment
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.models = models or DEFAULT_MODELS
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

    def _sanitize(self, text: str) -> str:
        """Strip API key from any debug or error message."""
        if self._api_key and self._api_key in text:
            return text.replace(self._api_key, "[REDACTED_API_KEY]")
        return text

    def generate(self, system_prompt: str, user_prompt: str) -> CompletionResponse:
        """Attempt completion using primary model, cascading to fallbacks on 429/5xx/timeout."""
        if not self._api_key:
            raise OpenRouterError(
                message="OPENROUTER_API_KEY is not set",
                user_facing_message="Chat service is temporarily offline: API key not configured.",
                status_code=500
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        last_error = None

        for model in self.models:
            start_time = time.monotonic()
            logger.info("Calling OpenRouter with model: %s", model)

            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
            }

            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/dar-project/dar-chatbot",
                    "X-Title": "DAR AI Property Assistant",
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    latency = round((time.monotonic() - start_time) * 1000, 2)
                    raw_data = resp.read()
                    data = json.loads(raw_data.decode("utf-8"))

                    model_used = data.get("model", model)
                    choices = data.get("choices", [])
                    if not choices:
                        raise ValueError("No choices in completion response")

                    reply = choices[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})

                    logger.info("OpenRouter model %s succeeded in %.2fms", model_used, latency)
                    return CompletionResponse(
                        content=reply,
                        model_used=model_used,
                        latency_ms=latency,
                        usage=usage,
                    )

            except urllib.error.HTTPError as e:
                latency = round((time.monotonic() - start_time) * 1000, 2)
                err_body = e.read().decode("utf-8", errors="ignore") if hasattr(e, "read") else ""
                clean_err = self._sanitize(err_body)
                logger.warning("Model %s returned HTTP %d: %s", model, e.code, clean_err)

                if e.code == 401 or e.code == 403:
                    raise OpenRouterError(
                        message=f"Authentication error: {clean_err}",
                        user_facing_message="Authentication failed with the AI service provider. Please verify server API keys.",
                        status_code=502
                    )
                elif e.code == 429:
                    last_error = OpenRouterError(
                        message=f"Rate limit exceeded on {model}: {clean_err}",
                        user_facing_message="The free AI service quota is currently busy. Please wait a moment and try again.",
                        status_code=429
                    )
                    # Cascade to next fallback model
                    continue
                else:
                    last_error = OpenRouterError(
                        message=f"HTTP {e.code} on {model}: {clean_err}",
                        user_facing_message="The upstream AI provider encountered an error. Trying fallback...",
                        status_code=502
                    )
                    continue

            except Exception as e:
                clean_msg = self._sanitize(str(e))
                logger.warning("Model %s failed with error: %s", model, clean_msg)
                last_error = OpenRouterError(
                    message=clean_msg,
                    user_facing_message="AI request timed out. Please try again.",
                    status_code=504
                )
                continue

        # If all fallbacks failed
        if last_error:
            raise last_error

        raise OpenRouterError(
            message="All candidate models failed",
            user_facing_message="All AI service models are currently busy or unavailable. Please try again shortly.",
            status_code=503
        )
