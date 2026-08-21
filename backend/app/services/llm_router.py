"""Enruta el chat de GPO: Gemini Flash/Lite primero, Groq si falla."""
import logging

from app.services import gemini_service, groq_service

logger = logging.getLogger(__name__)


def complete(
    messages: list[dict],
    *,
    temperature: float = 0.35,
    max_tokens: int = 1800,
    json_mode: bool = False,
) -> str:
    gemini_error = None
    if gemini_service.get_gemini_keys():
        try:
            return gemini_service.chat_completions(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except Exception as exc:
            gemini_error = exc
            logger.warning("Gemini no disponible, usando Groq: %s", exc)
    else:
        logger.info("Sin keys de Gemini; usando Groq")

    try:
        return groq_service.chat_completions(
            messages,
            temperature=temperature,
            max_tokens=min(max_tokens, 1200),
            json_mode=json_mode,
        )
    except Exception as groq_error:
        if json_mode:
            try:
                return groq_service.chat_completions(
                    messages,
                    temperature=temperature,
                    max_tokens=min(max_tokens, 1200),
                    json_mode=False,
                )
            except Exception:
                pass
        if gemini_error:
            raise RuntimeError(
                f"Gemini y Groq fallaron. Gemini: {gemini_error}. Groq: {groq_error}"
            ) from groq_error
        raise
