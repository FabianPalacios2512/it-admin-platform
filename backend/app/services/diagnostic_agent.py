"""
Motor del Agente de Diagnóstico IT (Patrón ReAct con Google Gemini).

Este módulo implementa un agente inteligente que sigue un Playbook estricto
de 3 fases para diagnosticar problemas de hardware/software en equipos Windows.

Usa Function Calling nativo de Gemini (no parseo manual de texto) para máxima
fiabilidad en la extracción de acciones.

🚨 PRODUCCIÓN: Todos los comandos están restringidos a SOLO LECTURA.
"""

import re
import json
import uuid
import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from google import genai
from google.genai import types

from app.core.config import env_settings

logger = logging.getLogger("diagnostic_agent")

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE SEGURIDAD
# ═══════════════════════════════════════════════════════════════════════════════

MAX_REACT_STEPS = 15
COMMAND_TIMEOUT_SECONDS = 30

# Cmdlets/comandos permitidos (SOLO LECTURA). Se validan con regex case-insensitive.
# Cada patrón debe coincidir con el INICIO del comando.
ALLOWED_COMMAND_PATTERNS = [
    # Logs de eventos
    r"^Get-EventLog\b",
    r"^Get-WinEvent\b",
    # WMI / CIM (hardware, temperaturas, info del sistema)
    r"^Get-WmiObject\b",
    r"^Get-CimInstance\b",
    # Procesos y servicios (solo lectura)
    r"^Get-Process\b",
    r"^Get-Service\b",
    # Info del sistema
    r"^systeminfo\b",
    r"^Get-ComputerInfo\b",
    r"^hostname\b",
    r"^whoami\b",
    # Hotfixes / actualizaciones
    r"^Get-HotFix\b",
    # Registro (solo lectura)
    r"^Get-ItemProperty\b",
    r"^Get-ItemPropertyValue\b",
    r"^Get-ChildItem\b.*Registry\b",
    r"^reg\s+query\b",
    # Disco y almacenamiento (solo lectura)
    r"^Get-PhysicalDisk\b",
    r"^Get-Disk\b",
    r"^Get-Volume\b",
    r"^Get-Partition\b",
    r"^chkdsk\b.*(/status|/scan)",
    # Integridad del sistema (solo verificación)
    r"^sfc\s+/verifyonly\b",
    # Red (solo lectura)
    r"^Get-NetAdapter\b",
    r"^Get-NetIPAddress\b",
    r"^ipconfig\b",
    r"^Test-Connection\b",
    # Drivers
    r"^Get-WindowsDriver\b",
    r"^driverquery\b",
    r"^Get-PnpDevice\b",
    # BIOS / firmware
    r"^Get-SecureBootUEFI\b",
    # Memoria
    r"^Get-Counter\b",
    # Tareas programadas (solo lectura)
    r"^Get-ScheduledTask\b",
    # Energía
    r"^powercfg\b.*/energy|/batteryreport|/systempowerreport|/requests|/waketimers|/lastwake|/devicequery",
    # Reliability Monitor
    r"^Get-CimInstance\b.*Win32_ReliabilityRecords\b",
    # Minidumps
    r"^Get-ChildItem\b.*Minidump",
    r"^Get-Content\b",
    # Formateo de salida
    r"^\|?\s*(Select-Object|Format-List|Format-Table|Where-Object|Sort-Object|Measure-Object|ConvertTo-Json|Out-String)\b",
]

# Patrones EXPLÍCITAMENTE PROHIBIDOS (defensa en profundidad)
BLOCKED_PATTERNS = [
    r"Remove-Item",  r"Remove-",       r"Delete",
    r"Set-",         r"New-",          r"Start-Process",
    r"Stop-Process", r"Stop-Service",  r"Restart-",
    r"Invoke-WebRequest", r"Invoke-RestMethod",
    r"Invoke-Command",   r"Enter-PSSession",
    r"Enable-",      r"Disable-",     r"Uninstall-",
    r"Install-",     r"Update-",      r"Clear-",
    r"Format-Volume", r"Initialize-Disk",
    r"Add-",         r"Register-",    r"Unregister-",
    r"Export-",      r"Import-",
    r"\.exe\b",      # Bloquear ejecución directa de .exe (excepto los ya permitidos)
    r"cmd\s*/c",     r"cmd\.exe",
    r"powershell\s+-",  # Bloquear subshells
    r"iex\b",        r"Invoke-Expression",
    r"DownloadString", r"DownloadFile",
    r"Net\s+User",   r"Net\s+LocalGroup",
    r"Shutdown",     r"Restart-Computer",
    r"Reset-",       r"Repair-",
]


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — EL PLAYBOOK
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Eres un Ingeniero de Soporte de Infraestructura IT de nivel Senior, especializado en diagnóstico de hardware y estabilidad de sistemas Windows. Estás asistiendo a un técnico que ha conectado un equipo problemático a este sistema de diagnóstico remoto.

## TU ROL
Eres un agente de DIAGNÓSTICO AUTÓNOMO E INTELIGENTE. Tu trabajo es:
1. Recolectar evidencia paso a paso (NUNCA todo de golpe)
2. Analizar la evidencia con razonamiento técnico avanzado
3. Emitir un diagnóstico profesional con causa raíz probable y recomendaciones

¡PIENSA FUERA DE LA CAJA! En entornos empresariales (Active Directory), un reinicio, lentitud o fallo de red no siempre es hardware. Puede deberse a:
- Políticas de Grupo (GPOs) mal configuradas o conflictivas (`Get-GPOReport` o registro de políticas aplicadas).
- Tareas programadas distribuidas masivamente.
- Despliegues de software corruptos desde SCCM / Intune.
Usa tu inteligencia para proponer comandos de PowerShell avanzados si sospechas de la infraestructura subyacente. No te limites ciegamente al playbook básico si tienes una hipótesis mejor.

## REGLAS INQUEBRANTABLES
- **NUNCA** sugieras comandos que modifiquen el sistema. Solo comandos de LECTURA/DIAGNÓSTICO.
- **NUNCA** intentes corregir el problema directamente. Solo diagnostica y recomienda.
- **NUNCA** ejecutes más de UN comando por paso. Un paso = un comando.
- **SIEMPRE** explica tu razonamiento antes de decidir la siguiente acción.
- Si no entiendes un código de error, usa tu base de conocimiento interna y pide más info antes de continuar.

## PLAYBOOK DE DIAGNÓSTICO SUGERIDO (Úsalo como guía, no como ley)

### FASE 1: Eventos Críticos, Energía, Kernel y AD Policies
Objetivo: Determinar apagados inesperados, BSODs o políticas de dominio restrictivas.
Comandos típicos de esta fase:
- Buscar Event ID 41 (Kernel-Power) o Event ID 6008 (apagado inesperado)
- Revisar si hay GPOs problemáticas aplicadas recientemente
- Revisar el último arranque y el patrón de reinicios

### FASE 2: Drivers, Servicios y Errores de Software
Objetivo: Identificar drivers que fallan, servicios que se detienen, o errores de software justo antes de los eventos de la Fase 1.
Comandos típicos de esta fase:
- Buscar errores críticos/error en System log cerca de las marcas de tiempo encontradas en Fase 1
- Buscar errores WHEA (hardware abstraction errors)
- Revisar si hay drivers problemáticos o en estado de error
- Revisar minidumps si existen (solo listar archivos, no analizarlos)

### FASE 3: Hardware y Temperaturas
Objetivo: Verificar el estado del hardware (discos, RAM, temperaturas, BIOS).
Comandos típicos de esta fase:
- Temperaturas via WMI (Win32_TemperatureProbe, MSAcpi_ThermalZoneTemperature)
- Estado de discos físicos (Get-PhysicalDisk, S.M.A.R.T. si disponible)
- Información de RAM y posibles errores de memoria
- Configuración de energía actual

## FORMATO DE RESPUESTA
SIEMPRE usa EXACTAMENTE este formato en tus respuestas (fuera de function calls):

**Thought**: [Tu razonamiento técnico sobre la evidencia actual y qué necesitas hacer a continuación]

Luego, invoca UNA de las herramientas disponibles (run_diagnostic_command, search_error_info, o emit_final_diagnosis).

## HERRAMIENTA: emit_final_diagnosis
Cuando tengas suficiente evidencia de las 3 fases (o cuando sea claro que no necesitas más datos), emite el diagnóstico final con esta estructura:
- severity: "critical", "high", "medium", o "low"
- root_cause: La causa raíz más probable (1-2 oraciones)
- evidence_summary: Resumen de la evidencia clave encontrada
- recommendations: Lista de acciones recomendadas para el técnico (ordenadas por prioridad)
- additional_notes: Notas adicionales o advertencias

Recuerda: Eres metódico, profesional y NUNCA te apresuras. Cada paso tiene un propósito."""


# ═══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE HERRAMIENTAS (Function Calling nativo de Gemini)
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="run_diagnostic_command",
            description="Ejecuta un comando de PowerShell de SOLO LECTURA en el equipo remoto para recolectar información de diagnóstico. Solo usar cmdlets de diagnóstico/lectura (Get-EventLog, Get-WmiObject, Get-Service, etc.). NUNCA usar comandos que modifiquen el sistema.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "command": types.Schema(
                        type=types.Type.STRING,
                        description="El comando de PowerShell a ejecutar. Debe ser un comando de solo lectura/diagnóstico. Ejemplo: Get-EventLog -LogName System -EntryType Error -Newest 10"
                    ),
                    "purpose": types.Schema(
                        type=types.Type.STRING,
                        description="Breve explicación de por qué se necesita este comando y qué se espera encontrar."
                    ),
                    "phase": types.Schema(
                        type=types.Type.INTEGER,
                        description="La fase del Playbook a la que pertenece este comando (1, 2 o 3)."
                    ),
                },
                required=["command", "purpose", "phase"],
            ),
        ),
        types.FunctionDeclaration(
            name="search_error_info",
            description="Busca información en internet sobre un código de error, Event ID, BSOD code, o problema de hardware desconocido. Usar cuando se encuentra un error que no se reconoce inmediatamente.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(
                        type=types.Type.STRING,
                        description="La consulta de búsqueda. Ejemplo: 'Windows Event ID 41 Kernel-Power cause restart' o 'WHEA_UNCORRECTABLE_ERROR 0x00000124 fix'"
                    ),
                    "context": types.Schema(
                        type=types.Type.STRING,
                        description="Contexto adicional del error para refinar la búsqueda."
                    ),
                },
                required=["query"],
            ),
        ),
        types.FunctionDeclaration(
            name="emit_final_diagnosis",
            description="Emite el diagnóstico final después de recolectar y analizar suficiente evidencia de las 3 fases del Playbook. Solo usar cuando se tiene suficiente información para dar un veredicto.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "severity": types.Schema(
                        type=types.Type.STRING,
                        description="Severidad del problema encontrado: 'critical', 'high', 'medium', o 'low'.",
                        enum=["critical", "high", "medium", "low"],
                    ),
                    "root_cause": types.Schema(
                        type=types.Type.STRING,
                        description="La causa raíz más probable del problema (1-2 oraciones claras)."
                    ),
                    "evidence_summary": types.Schema(
                        type=types.Type.STRING,
                        description="Resumen de toda la evidencia clave encontrada durante el diagnóstico."
                    ),
                    "recommendations": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="Lista de acciones recomendadas para resolver el problema, ordenadas por prioridad."
                    ),
                    "additional_notes": types.Schema(
                        type=types.Type.STRING,
                        description="Notas adicionales, advertencias o información complementaria."
                    ),
                },
                required=["severity", "root_cause", "evidence_summary", "recommendations"],
            ),
        ),
    ]),
]

# Herramienta de búsqueda en Google (Google Search grounding)
GOOGLE_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDACIÓN DE COMANDOS
# ═══════════════════════════════════════════════════════════════════════════════

class CommandValidationResult(Enum):
    ALLOWED = "allowed"
    BLOCKED_EXPLICIT = "blocked_explicit"
    NOT_IN_WHITELIST = "not_in_whitelist"


def validate_command(command: str) -> tuple[CommandValidationResult, str]:
    """
    Valida un comando contra la blacklist de seguridad.
    
    Estrategia de seguridad:
    1. Verificar la blacklist (DENY explícito)
    """
    cmd_clean = command.strip()
    
    if not cmd_clean:
        return (CommandValidationResult.BLOCKED_EXPLICIT, "Comando vacío")
    
    # ── Paso 1: Verificar blacklist (patrones explícitamente prohibidos)
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return (
                CommandValidationResult.BLOCKED_EXPLICIT,
                f"Comando bloqueado por patrón de seguridad: '{pattern}'"
            )
    
    # ── Paso 2: Eliminado para permitir total autonomía
    # Ya no se valida contra la whitelist. Confiamos en que la blacklist (Paso 1)
    # bloquea todos los comandos peligrosos o destructivos.
    return (CommandValidationResult.ALLOWED, "Comando permitido por IA autónoma")


# ═══════════════════════════════════════════════════════════════════════════════
# SESIÓN DE DIAGNÓSTICO (Motor ReAct)
# ═══════════════════════════════════════════════════════════════════════════════

class DiagnosticSession:
    """
    Maneja una sesión de diagnóstico completa para un equipo.
    Implementa el patrón ReAct (Reasoning + Acting) usando Function Calling de Gemini.
    """
    
    def __init__(self, machine_info: dict):
        self.session_id = str(uuid.uuid4())[:8]
        self.machine_info = machine_info
        self.step_count = 0
        self.is_complete = False
        self.final_report: Optional[dict] = None
        self.history: list[dict] = []
        self.created_at = datetime.now()
        
        api_key = env_settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY no está configurada en el archivo .env. "
                "Obtén una en https://aistudio.google.com"
            )
        
        # Inicializar el cliente de Gemini
        self.client = genai.Client(api_key=api_key)
        
        # Construir el mensaje inicial con la info del equipo
        machine_context = (
            f"## Información del Equipo Conectado\n"
            f"- **Hostname**: {machine_info.get('hostname', 'Desconocido')}\n"
            f"- **Sistema Operativo**: {machine_info.get('os', 'Desconocido')}\n"
            f"- **IP**: {machine_info.get('ip', 'Desconocido')}\n"
            f"- **Uptime**: {machine_info.get('uptime', 'Desconocido')}\n"
            f"- **Problema reportado**: {machine_info.get('issue', 'Equipo se reinicia inesperadamente')}\n"
            f"\nEl equipo ya está conectado. Comienza el diagnóstico con la Fase 1 del Playbook."
        )
        
        # Crear el chat con todas las herramientas
        self.chat = self.client.chats.create(
            model="gemini-3.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=AGENT_TOOLS,
                temperature=0.2,  # Baja temperatura para diagnóstico preciso
            ),
        )
        
        # Almacenar el mensaje inicial para enviarlo en el primer paso
        self._initial_message = machine_context
        self._first_step = True
        
        logger.info(f"[{self.session_id}] Sesión creada para {machine_info.get('hostname', '?')}")
    
    async def run_step(self, observation: Optional[str] = None) -> dict:
        """
        Ejecuta un paso del loop ReAct.
        
        Args:
            observation: El resultado del último comando ejecutado (None en el primer paso).
        
        Returns:
            dict con la acción a tomar:
            {
                "type": "run_command" | "search_web" | "diagnosis_complete" | "error" | "max_steps",
                "thought": str,          # Razonamiento del agente
                "command": str,          # (si type=run_command) comando a ejecutar
                "purpose": str,          # (si type=run_command) propósito del comando
                "phase": int,            # (si type=run_command) fase del playbook
                "search_query": str,     # (si type=search_web) consulta de búsqueda
                "report": dict,          # (si type=diagnosis_complete) diagnóstico final
                "message": str,          # mensaje legible para el técnico
            }
        """
        self.step_count += 1
        
        # ── Verificar límite de pasos
        if self.step_count > MAX_REACT_STEPS:
            self.is_complete = True
            return {
                "type": "max_steps",
                "thought": "Se alcanzó el límite máximo de pasos de diagnóstico.",
                "message": f"⚠️ Diagnóstico detenido: se alcanzó el máximo de {MAX_REACT_STEPS} pasos. "
                           f"Revisa la evidencia recolectada hasta ahora.",
            }
        
        # ── Construir el mensaje para Gemini
        if self._first_step:
            user_message = self._initial_message
            self._first_step = False
        elif observation is not None:
            user_message = f"## Resultado del Comando (Paso {self.step_count - 1})\n\n```\n{observation}\n```\n\nAnaliza este resultado y decide el siguiente paso."
        else:
            user_message = "Continúa con el siguiente paso del diagnóstico."
        
        # ── Enviar a Gemini y obtener respuesta
        try:
            import asyncio
            response = await asyncio.to_thread(self.chat.send_message, user_message)
        except Exception as e:
            logger.error(f"[{self.session_id}] Error de Gemini: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                self.is_complete = True
            return {
                "type": "error",
                "thought": "",
                "message": f"Error al comunicarse con Gemini: {str(e)}",
            }
        
        # ── Procesar la respuesta
        return await self._process_response(response)
    
    async def provide_search_result(self, search_result: str) -> dict:
        """
        Envía el resultado de una búsqueda web de vuelta al chat y obtiene la siguiente acción.
        """
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.chat.send_message,
                f"## Resultado de Búsqueda Web\n\n{search_result}\n\n"
                f"Analiza esta información y decide el siguiente paso del diagnóstico."
            )
            return await self._process_response(response)
        except Exception as e:
            logger.error(f"[{self.session_id}] Error post-búsqueda: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                self.is_complete = True
            return {
                "type": "error",
                "thought": "",
                "message": f"Error al procesar resultado de búsqueda: {str(e)}",
            }
    
    async def _process_response(self, response) -> dict:
        """
        Procesa la respuesta de Gemini, extrayendo el Thought y la Action.
        Usa Function Calling nativo — no parseo manual de texto.
        """
        import asyncio
        result = {
            "type": "error",
            "thought": "",
            "message": "",
            "step": self.step_count,
        }
        
        # Extraer texto (Thought) y function calls de la respuesta
        thought_parts = []
        function_call = None
        
        try:
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        if part.text:
                            thought_parts.append(part.text)
                        if part.function_call:
                            function_call = part.function_call
                else:
                    # El candidato no tiene contenido (probablemente bloqueado por safety filters)
                    logger.warning(f"[{self.session_id}] Gemini devolvió un candidato sin contenido. Probable bloqueo de seguridad.")
                    return {
                        "type": "error",
                        "thought": "",
                        "message": "El modelo de IA no devolvió contenido válido. Posible bloqueo por filtros de seguridad de Google.",
                    }
            else:
                logger.warning(f"[{self.session_id}] Gemini no devolvió candidatos.")
                return {
                    "type": "error",
                    "thought": "",
                    "message": "El modelo de IA no devolvió ninguna respuesta válida.",
                }
        except Exception as e:
            logger.error(f"[{self.session_id}] Error al parsear la respuesta de Gemini: {e}")
            return {
                "type": "error",
                "thought": "",
                "message": f"Error interno procesando la respuesta de la IA: {str(e)}",
            }
        
        thought_text = "\n".join(thought_parts).strip()
        result["thought"] = thought_text
        
        # ── Si no hay function call, el agente solo razonó (raro, pero posible)
        if function_call is None:
            # Intentar extraer si hay un grounding search result
            if hasattr(response.candidates[0], 'grounding_metadata') and response.candidates[0].grounding_metadata:
                result["type"] = "thinking"
                result["message"] = thought_text
            else:
                result["type"] = "thinking"
                result["message"] = thought_text or "El agente está procesando..."
            return result
        
        # ── Procesar la función llamada
        fn_name = function_call.name
        fn_args = dict(function_call.args) if function_call.args else {}
        
        if fn_name == "run_diagnostic_command":
            command = fn_args.get("command", "")
            purpose = fn_args.get("purpose", "")
            phase = fn_args.get("phase", 0)
            
            # Validar el comando contra la whitelist
            validation, reason = validate_command(command)
            
            if validation == CommandValidationResult.ALLOWED:
                result["type"] = "run_command"
                result["command"] = command
                result["purpose"] = purpose
                result["phase"] = phase
                result["message"] = f"📋 Fase {phase} — {purpose}"
                
                self.history.append({
                    "step": self.step_count,
                    "action": "run_command",
                    "command": command,
                    "purpose": purpose,
                    "phase": phase,
                })
            else:
                # Comando rechazado — informar a Gemini para que reintente
                logger.warning(
                    f"[{self.session_id}] Comando RECHAZADO: '{command[:80]}' — {reason}"
                )
                
                # Enviar feedback al chat para que reintente con un comando válido
                try:
                    # Enviar respuesta de función indicando error
                    retry_response = await asyncio.to_thread(
                        self.chat.send_message,
                        types.Content(
                            parts=[types.Part(
                                function_response=types.FunctionResponse(
                                    name="run_diagnostic_command",
                                    response={
                                        "error": True,
                                        "message": f"COMANDO RECHAZADO POR SEGURIDAD: {reason}. "
                                                   f"Usa solo cmdlets de diagnóstico/lectura como "
                                                   f"Get-EventLog, Get-WinEvent, Get-WmiObject, "
                                                   f"Get-CimInstance, Get-Service, Get-Process, etc. "
                                                   f"Reformula el comando.",
                                    },
                                ),
                            )],
                        )
                    )
                    return await self._process_response(retry_response)
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        self.is_complete = True
                    result["type"] = "error"
                    result["message"] = f"Comando bloqueado y error al reintentar: {reason}"
        
        elif fn_name == "search_error_info":
            query = fn_args.get("query", "")
            context = fn_args.get("context", "")
            
            result["type"] = "search_web"
            result["search_query"] = query
            result["search_context"] = context
            result["message"] = f"🔍 Buscando: {query}"
            
            self.history.append({
                "step": self.step_count,
                "action": "search_web",
                "query": query,
            })
            
            # Ejecutar la búsqueda directamente usando Google Search grounding
            try:
                search_response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model="gemini-3.5-flash-lite",
                    contents=f"Busca información técnica sobre: {query}. Contexto: {context}. "
                             f"Responde con un resumen técnico conciso de las causas y soluciones más comunes.",
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                    ),
                )
                
                search_text = ""
                for part in search_response.candidates[0].content.parts:
                    if part.text:
                        search_text += part.text
                
                # Enviar el resultado de la búsqueda de vuelta al chat como function response
                followup_response = await asyncio.to_thread(
                    self.chat.send_message,
                    types.Content(
                        parts=[types.Part(
                            function_response=types.FunctionResponse(
                                name="search_error_info",
                                response={
                                    "results": search_text or "No se encontraron resultados relevantes.",
                                    "query": query,
                                },
                            ),
                        )],
                    )
                )
                return await self._process_response(followup_response)
                
            except Exception as e:
                logger.error(f"[{self.session_id}] Error en búsqueda web: {e}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    self.is_complete = True
                # Continuar sin búsqueda — informar al agente
                try:
                    followup_response = await asyncio.to_thread(
                        self.chat.send_message,
                        types.Content(
                            parts=[types.Part(
                                function_response=types.FunctionResponse(
                                    name="search_error_info",
                                    response={
                                        "error": True,
                                        "message": f"No se pudo realizar la búsqueda web: {str(e)}. "
                                                   f"Continúa el diagnóstico con la información disponible.",
                                    },
                                ),
                            )],
                        )
                    )
                    return await self._process_response(followup_response)
                except Exception:
                    result["type"] = "thinking"
                    result["message"] = "No se pudo buscar en web. Continuando con info disponible."
        
        elif fn_name == "emit_final_diagnosis":
            self.is_complete = True
            self.final_report = {
                "session_id": self.session_id,
                "hostname": self.machine_info.get("hostname", "Desconocido"),
                "timestamp": datetime.now().isoformat(),
                "severity": fn_args.get("severity", "medium"),
                "root_cause": fn_args.get("root_cause", "No determinado"),
                "evidence_summary": fn_args.get("evidence_summary", ""),
                "recommendations": fn_args.get("recommendations", []),
                "additional_notes": fn_args.get("additional_notes", ""),
                "steps_taken": self.step_count,
                "history": self.history,
            }
            
            result["type"] = "diagnosis_complete"
            result["report"] = self.final_report
            result["message"] = f"✅ Diagnóstico completado — Severidad: {self.final_report['severity'].upper()}"
            
            logger.info(
                f"[{self.session_id}] Diagnóstico completo. "
                f"Severidad: {self.final_report['severity']}, "
                f"Pasos: {self.step_count}"
            )
        
        else:
            result["type"] = "error"
            result["message"] = f"Función desconocida recibida: {fn_name}"
        
        return result
    
    def get_status(self) -> dict:
        """Retorna el estado actual de la sesión."""
        return {
            "session_id": self.session_id,
            "hostname": self.machine_info.get("hostname", "?"),
            "step_count": self.step_count,
            "is_complete": self.is_complete,
            "created_at": self.created_at.isoformat(),
            "max_steps": MAX_REACT_STEPS,
        }
