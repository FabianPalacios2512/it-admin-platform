"""Cliente Gemini (Flash / Flash-Lite) con rotación de keys y modelos."""
import logging
import threading
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import env_settings

logger = logging.getLogger(__name__)

# Flash-lite primero (a petición del usuario), otros como respaldo.
DEFAULT_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-exp-1206",
)

_lock = threading.Lock()
_key_index = 0


def _clean_key(value: Optional[str]) -> str:
    return (value or "").strip().strip('"').strip("'")


def get_gemini_keys() -> list[str]:
    raw = [
        env_settings.GEMINI_API_KEY,
        env_settings.GEMINI_API_KEY_1,
        env_settings.GEMINI_API_KEY_2,
        env_settings.GEMINI_API_KEY_3,
        env_settings.GEMINI_API_KEY_4,
        env_settings.GEMINI_API_KEY_5,
    ]
    keys: list[str] = []
    seen: set[str] = set()
    for item in raw:
        key = _clean_key(item)
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def _err_text(exc: Exception) -> str:
    return str(exc).lower()


def _rotate_key(exc: Exception) -> bool:
    text = _err_text(exc)
    markers = (
        "429",
        "401",
        "403",
        "resource_exhausted",
        "quota",
        "rate limit",
        "too many requests",
        "api_key",
        "invalid api key",
        "permission_denied",
        "unauthorized",
    )
    return any(m in text for m in markers)


def _next_model(exc: Exception) -> bool:
    text = _err_text(exc)
    markers = (
        "404",
        "not found",
        "not_found",
        "not supported",
        "unknown model",
        "invalid model",
        "is not found",
    )
    return any(m in text for m in markers)


def _system_and_contents(messages: list[dict]) -> tuple[str, list]:
    system_parts: list[str] = []
    contents: list = []
    for item in messages:
        role = item.get("role")
        text = (item.get("content") or "").strip()
        if not text:
            continue
        if role == "system":
            system_parts.append(text)
            continue
        gemini_role = "user" if role == "user" else "model"
        if contents and contents[-1].role == gemini_role:
            prev = contents[-1].parts[0].text if contents[-1].parts else ""
            contents[-1] = types.Content(
                role=gemini_role,
                parts=[types.Part(text=f"{prev}\n\n{text}".strip())],
            )
        else:
            contents.append(
                types.Content(role=gemini_role, parts=[types.Part(text=text)])
            )
    if contents and contents[0].role != "user":
        contents.insert(0, types.Content(role="user", parts=[types.Part(text="Continúa.")]))
    return "\n\n".join(system_parts), contents


def chat_completions(
    messages: list[dict],
    *,
    temperature: float = 0.35,
    max_tokens: int = 1800,
    models: tuple[str, ...] = DEFAULT_MODELS,
    json_mode: bool = False,
) -> str:
    keys = get_gemini_keys()
    if not keys:
        raise RuntimeError("No hay API keys de Gemini configuradas")

    global _key_index
    last_error = "Error desconocido de Gemini"
    system, contents = _system_and_contents(messages)
    if not contents:
        raise ValueError("El mensaje está vacío")

    with _lock:
        start = _key_index % len(keys)

    for offset in range(len(keys)):
        idx = (start + offset) % len(keys)
        key = keys[idx]
        client = genai.Client(api_key=key)
        for model in models:
            try:
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    system_instruction=system or None,
                    response_mime_type="application/json" if json_mode else None,
                )
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                text = (getattr(response, "text", None) or "").strip()
                if not text:
                    last_error = f"Gemini {model} respondió vacío"
                    logger.warning("%s. Probando siguiente modelo.", last_error)
                    continue
                with _lock:
                    _key_index = idx
                logger.info("Gemini OK con modelo %s (key #%s)", model, idx + 1)
                return text
            except Exception as exc:
                last_error = str(exc)
                if _next_model(exc):
                    logger.warning("Modelo Gemini no disponible: %s (%s)", model, exc)
                    continue
                if _rotate_key(exc):
                    logger.warning("Gemini key #%s modelo %s agotada/inválida. Rotando.", idx + 1, model)
                    break
                logger.warning("Error Gemini key #%s modelo %s: %s", idx + 1, model, exc)
                break

    raise RuntimeError(f"Todas las API keys de Gemini fallaron. Último error: {last_error}")
