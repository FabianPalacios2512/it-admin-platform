"""Asistente de GPO: razona, aclara y solo entonces propone crear."""
import json
import logging
import re
from typing import Any, Optional

from app.services.gpo_inspect import diagnose_gpo, looks_like_inquiry, mentioned_gpos
from app.services.llm_router import complete

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Arquitecto e Ingeniero Experto en GPO (Directivas de Grupo) de AdInfra F2 (dominio code.local, DC 192.168.20.100).
Hablas español como un profesional Senior de Infraestructura IT: eres directo, analítico, experto en Active Directory y no usas relleno de chatbot. Tienes memoria: si el usuario te responde una pregunta, integras esa respuesta en tu contexto y continúas desde ahí sin volver a preguntar lo mismo.

Tu trabajo NO es simplemente disparar un botón de crear. Es entender profundamente la necesidad del negocio, analizar si una GPO es la herramienta correcta, explicar la solución técnica y recolectar los parámetros faltantes mediante preguntas precisas. Solo propondrás la creación cuando tengas TODOS los datos confirmados.

CÓMO RAZONAR Y RESPONDER (siempre):
1. **Análisis de Viabilidad:** Explica brevemente si la petición se puede hacer con GPO (plantilla administrativa, registro, preferencia, script, etc.) y su impacto real en los equipos/usuarios. Demuestra tu experiencia.
2. **Memoria de Contexto:** Revisa el historial. Si el usuario ya te dio un dato (ej. una ruta, una letra de unidad, un tiempo), NO se lo vuelvas a preguntar. Asúmelo como confirmado.
3. **Preguntas Precisas:** Si faltan datos técnicos obligatorios para construir la GPO, haz preguntas. MÁXIMO 2 preguntas por turno, claras y enumeradas. (Ej: 1. ¿Cuál es la ruta UNC exacta? 2. ¿Deseas aplicar esto a todos o solo a un grupo/OU específico?).
4. **No asumas datos:** NO inventes rutas UNC, letras de unidad ni nombres de impresoras si no te los han dado explícitamente.
5. **Diagnóstico y Hechos:** Si te preguntan "qué hace la GPO X", lee los HECHOS DE DOMINIO que se te inyectarán. Si dicen "GPO VACÍA", informa al usuario que la política existe pero no tiene ninguna configuración por dentro.

CUÁNDO NO CREAR:
- Charlas casuales o saludos breves.
- Tareas de Office 365, Exchange, Redes, Hardware (indica que tu especialidad es el Directorio Activo y GPOs).

FORMATO ESTRICTO: Responde SIEMPRE y ÚNICAMENTE con este JSON:
{"reply":"Tu respuesta experta y conversacional aquí en formato texto o Markdown","proposal":null}

- Mantén `proposal: null` mientras estés diagnosticando, explicando o haciendo preguntas.
- SOLO cambia `proposal` a un objeto JSON válido cuando EL USUARIO HAYA CONFIRMADO todos los datos necesarios (rutas, letras, tiempo) y tú confirmes que la GPO es técnicamente viable.

Formato del objeto proposal cuando esté listo:
{"reply":"...","proposal":{"viable":true,"ready":true,"name":"GPO_USR_Mapeo_Unidad","template_type":"network_drive","summary":"Resumen técnico","params":{"letter":"Z:","path":"\\\\servidor\\\\share"},"target_ou":"","script":"","warnings":[]}}

Valores válidos para template_type: wallpaper|network_drive|screen_lock|printer|custom
Parámetros obligatorios (params): wallpaper {path}; network_drive {letter,path}; screen_lock {minutes}; printer {path}; custom {}

Bajo ninguna circunstancia incluyas texto fuera de la estructura JSON. No menciones que eres una IA.
"""

REQUIRED_PARAMS = {
    "wallpaper": ("path",),
    "network_drive": ("path", "letter"),
    "printer": ("path",),
    "screen_lock": ("minutes",),
    "custom": (),
}

PLACEHOLDER_MARKERS = (
    r"\\server\share",
    r"\\servidor\share",
    r"\\ejemplo",
    r"\\printserver",
    "printername",
    "wallpaper.jpg",
)

CONFIRM_WORDS = (
    "sí", "si", "dale", "ok", "okay", "listo", "correcto", "confirmo",
    "así es", "asi es", "adelante", "hazlo", "crea", "crear", "de acuerdo",
    "perfecto", "exacto", "esa ruta", "esa letra", "para todos",
)

UNC_RE = re.compile(r"\\\\[^\s\"'`]+")
LETTER_RE = re.compile(r"\b([A-Za-z]):(?:\b|$)")
MINUTES_RE = re.compile(r"\b(\d{1,3})\s*(?:min|minuto)", re.I)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    fence = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        raw = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            return None
        raw = text[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_envelope(text: str) -> tuple[str, Optional[dict]]:
    parsed = _extract_json(text)
    if isinstance(parsed, dict) and "reply" in parsed:
        return str(parsed.get("reply") or "").strip(), parsed.get("proposal")
    if isinstance(parsed, dict) and "proposal" in parsed:
        reply = (text[: text.find("{")].strip() if "{" in text else text).strip()
        return reply, parsed.get("proposal")
    return (text or "").strip(), None


def _infer_proposal(history: list[dict], proposal: Optional[dict]) -> Optional[dict]:
    user_turns = sum(1 for m in history if m.get("role") == "user")
    blob = " ".join(m["content"] for m in history if m.get("role") == "user")
    unc_match = UNC_RE.search(blob.replace("/", "\\"))
    letter_match = LETTER_RE.search(blob)
    minutes_match = MINUTES_RE.search(blob)
    unc = unc_match.group(0).rstrip(".,;)") if unc_match else ""
    letter = f"{letter_match.group(1).upper()}:" if letter_match else ""
    minutes = minutes_match.group(1) if minutes_match else ""

    if proposal:
        params = dict(proposal.get("params") or {})
        if unc and not params.get("path"):
            params["path"] = unc
        if letter and not params.get("letter"):
            params["letter"] = letter
        if minutes and not params.get("minutes"):
            params["minutes"] = minutes
        proposal["params"] = params
        return proposal

    if user_turns < 2 or not _user_confirmed(history):
        return None
    if unc and letter:
        return {
            "viable": True,
            "ready": True,
            "name": "GPO_USR_Mapeo_Unidad",
            "template_type": "network_drive",
            "summary": f"Mapear {unc} como unidad {letter} para los usuarios.",
            "params": {"path": unc, "letter": letter},
            "target_ou": "",
            "script": "",
            "warnings": [],
            "missing": [],
        }
    if unc and unc.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        return {
            "viable": True,
            "ready": True,
            "name": "GPO_USR_Fondo_Pantalla",
            "template_type": "wallpaper",
            "summary": f"Aplicar el fondo {unc} a los usuarios.",
            "params": {"path": unc},
            "target_ou": "",
            "script": "",
            "warnings": [],
            "missing": [],
        }
    return None


def _normalize_proposal(raw: Any) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    proposal = raw.get("proposal") if "proposal" in raw else raw
    if not isinstance(proposal, dict):
        return None
    if proposal.get("viable") is False and not proposal.get("template_type") and not proposal.get("params"):
        return None
    template = (proposal.get("template_type") or "custom").strip().lower()
    if template not in {"wallpaper", "network_drive", "screen_lock", "printer", "custom"}:
        template = "custom"
    warnings = proposal.get("warnings") or []
    if isinstance(warnings, str):
        warnings = [warnings]
    params = proposal.get("params") if isinstance(proposal.get("params"), dict) else {}
    letter = str(params.get("letter") or "").strip().upper()
    if letter and not letter.endswith(":"):
        letter = f"{letter}:"
        params = {**params, "letter": letter}
    return {
        "viable": bool(proposal.get("viable", True)),
        "ready": bool(proposal.get("ready", False)),
        "name": (proposal.get("name") or "").strip(),
        "template_type": template,
        "summary": (proposal.get("summary") or "").strip(),
        "params": params,
        "target_ou": (proposal.get("target_ou") or "").strip(),
        "script": (proposal.get("script") or "").strip(),
        "warnings": [str(w) for w in warnings if str(w).strip()],
        "missing": [],
    }


def _looks_placeholder(path: str) -> bool:
    p = (path or "").lower().replace("/", "\\")
    return any(m in p for m in PLACEHOLDER_MARKERS)


def _user_confirmed(history: list[dict]) -> bool:
    last = (history[-1].get("content") or "").lower()
    return any(word in last for word in CONFIRM_WORDS)


def _finalize_proposal(proposal: Optional[dict], history: list[dict]) -> Optional[dict]:
    if not proposal:
        return None
    user_turns = sum(1 for m in history if m.get("role") == "user")
    template = proposal.get("template_type") or "custom"
    params = dict(proposal.get("params") or {})
    required = REQUIRED_PARAMS.get(template, ())
    missing = [key for key in required if not str(params.get(key) or "").strip()]

    path = str(params.get("path") or "").strip()
    if path and _looks_placeholder(path):
        params["path"] = ""
        if "path" in required and "path" not in missing:
            missing.append("path")
        proposal["warnings"] = list(proposal.get("warnings") or [])
        proposal["warnings"].append("La ruta era un ejemplo; hay que confirmar el UNC real.")
        path = ""

    ready = bool(proposal.get("ready"))
    if not proposal.get("viable"):
        ready = False
    if user_turns < 2:
        ready = False
    if missing:
        ready = False
    if path and _looks_placeholder(path):
        ready = False

    proposal["params"] = params
    proposal["missing"] = missing
    proposal["ready"] = ready and not missing
    if not proposal.get("name") and proposal["ready"]:
        proposal["name"] = _default_name(template)
    return proposal


def _default_name(template: str) -> str:
    return {
        "wallpaper": "GPO_USR_Fondo_Pantalla",
        "network_drive": "GPO_USR_Mapeo_Unidad",
        "screen_lock": "GPO_USR_Bloqueo_Pantalla",
        "printer": "GPO_USR_Impresora",
        "custom": "GPO_Custom",
    }.get(template, "GPO_Custom")


def _compact(obj: dict) -> str:
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return text[:3500]


async def chat(messages: list[dict], existing_gpos: Optional[list[str]] = None) -> dict:
    history = []
    for item in messages[-12:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            history.append({"role": role, "content": content})
    if not history:
        raise ValueError("El mensaje está vacío")

    gpo_names = existing_gpos or []
    last_user = history[-1]["content"]
    last_l = last_user.lower().strip(" !.?,¿¡")
    is_small_talk = len(last_l) < 48 and last_l in {
        "hola", "buenas", "hey", "hi", "hello", "buenos dias", "buenos días",
        "que tal", "qué tal", "hola como estas", "hola cómo estás", "hola como estas?",
    }

    scan_text = " ".join(m["content"] for m in history[-4:] if m["role"] == "user")
    targets = mentioned_gpos(scan_text, gpo_names)
    facts = None
    if not is_small_talk and (targets or looks_like_inquiry(last_user)):
        if not targets:
            targets = mentioned_gpos(scan_text, gpo_names)
        if targets:
            try:
                facts = diagnose_gpo(targets[0], with_settings=True)
            except Exception as exc:
                logger.warning("Diagnóstico GPO falló: %s", exc)
                facts = {"error": str(exc), "name": targets[0]}
                
    # Detectar si el usuario pregunta por OUs, departamentos o recomendaciones de OUs
    ou_tree = None
    if not is_small_talk and re.search(r"\b(ou|ous|unidad organizativa|departamento|estructura|arbol|árbol|recomienda|donde)\b", scan_text, re.IGNORECASE):
        try:
            from app.services.ad_service import get_organizational_units
            ous = get_organizational_units()
            # Mapear solo los campos clave para no saturar el contexto
            ou_tree = [{"name": o.get("name"), "dn": o.get("dn")} for o in ous]
        except Exception as e:
            logger.warning("No se pudo obtener el árbol de OUs para el agente: %s", e)

    names_line = ", ".join(gpo_names[:50]) if gpo_names else "(sin listado)"
    context_parts = [
        "GPOs del dominio (nombres): " + names_line,
        "Turno del usuario en esta conversación: "
        + str(sum(1 for m in history if m["role"] == "user"))
        + ". Si es el primero y pide crear algo, proposal debe ser null: explica y pregunta.",
    ]
    if facts:
        context_parts.append("HECHOS DE DOMINIO (consulta real de GPO, no inventar):\n" + _compact(facts))
    
    if ou_tree:
        context_parts.append("ÁRBOL DE OUS ACTUAL DEL DOMINIO (Usa esto para responder qué OUs existen o recomendar dónde aplicarla):\n" + _compact(ou_tree))

    llm_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "\n".join(context_parts)},
        *history,
    ]

    text = complete(
        llm_messages,
        temperature=0.45 if is_small_talk else 0.3,
        max_tokens=1800,
        json_mode=not is_small_talk,
    )
    if is_small_talk:
        reply, raw_proposal = _parse_envelope(text)
        return {"reply": reply or text, "proposal": None}

    reply, raw_proposal = _parse_envelope(text)
    inferred = _infer_proposal(history, _normalize_proposal(raw_proposal))
    proposal = _finalize_proposal(inferred, history)
    return {
        "reply": reply or "Listo. ¿Confirmas los datos para crear la GPO?",
        "proposal": proposal,
    }
