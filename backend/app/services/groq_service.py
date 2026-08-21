"""Cliente Groq con rotación automática de API keys (rate limit / auth)."""
import logging
import threading
from typing import Optional

import httpx

from app.core.config import env_settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODELS = (
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.1-8b-instant",
)

_lock = threading.Lock()
_key_index = 0


def _clean_key(value: Optional[str]) -> str:
    return (value or "").strip().strip('"').strip("'")


def get_groq_keys() -> list[str]:
    raw = [
        env_settings.GROQ_API_KEY,
        env_settings.GROQ_API_KEY_1,
        env_settings.GROQ_API_KEY_2,
        env_settings.GROQ_API_KEY_3,
        env_settings.GROQ_API_KEY_4,
        env_settings.GROQ_API_KEY_5,
        env_settings.GROQ_API_KEY_6,
        env_settings.GROQ_API_KEY_7,
        env_settings.GROQ_API_KEY_8,
        env_settings.GROQ_API_KEY_9,
        env_settings.GROQ_API_KEY_10,
        env_settings.GROQ_API_KEY_11,
        env_settings.GROQ_API_KEY_12,
        env_settings.GROQ_API_KEY_13,
        env_settings.GROQ_API_KEY_14,
    ]
    keys = []
    seen = set()
    for item in raw:
        key = _clean_key(item)
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _is_rotatable(status_code: int, body: str) -> bool:
    if status_code in (401, 403, 429):
        return True
    text = (body or "").lower()
    markers = (
        "rate_limit",
        "rate limit",
        "tokens per minute",
        "tpm",
        "quota",
        "limit exceeded",
        "too many requests",
        "invalid api key",
        "unauthorized",
    )
    return any(m in text for m in markers)


def chat_completions(
    messages: list[dict],
    *,
    temperature: float = 0.3,
    max_tokens: int = 700,
    models: tuple[str, ...] = DEFAULT_MODELS,
    json_mode: bool = False,
) -> str:
    keys = get_groq_keys()
    if not keys:
        raise RuntimeError("No hay API keys de Groq configuradas en el .env")

    global _key_index
    last_error = "Error desconocido de Groq"

    with _lock:
        start = _key_index % len(keys)

    for offset in range(len(keys)):
        idx = (start + offset) % len(keys)
        key = keys[idx]
        for model in models:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}
                with httpx.Client(timeout=45.0) as client:
                    res = client.post(
                        GROQ_URL,
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if res.status_code == 200:
                    with _lock:
                        _key_index = idx
                    data = res.json()
                    return (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""

                body = res.text[:500]
                last_error = f"Groq HTTP {res.status_code}"
                if res.status_code in (400, 404) and (
                    "model" in body.lower() or "not found" in body.lower() or "does not exist" in body.lower()
                ):
                    logger.warning("Modelo Groq no disponible: %s", model)
                    continue
                if _is_rotatable(res.status_code, body):
                    logger.warning("Groq key #%s modelo %s agotada/invalida. Rotando.", idx + 1, model)
                    break
                logger.warning("Groq HTTP %s en key #%s modelo %s. Rotando.", res.status_code, idx + 1, model)
                break
            except httpx.TimeoutException:
                last_error = "Timeout consultando Groq"
                logger.warning("Timeout Groq key #%s. Rotando.", idx + 1)
                break
            except RuntimeError:
                raise
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Error Groq key #%s: %s", idx + 1, exc)
                break

    raise RuntimeError(f"Todas las API keys de Groq fallaron. Último error: {last_error}")
