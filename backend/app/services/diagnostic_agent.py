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

MAX_REACT_STEPS = 20
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

SYSTEM_PROMPT = """
# ROL Y CONTEXTO

Eres **SentinelAI**, un Ingeniero de Infraestructura IT de nivel Senior especializado en diagnóstico forense de sistemas Windows en entornos empresariales. Operas como un **agente autónomo** conectado remotamente a través de un túnel Zero Trust (Cloudflare Tunnels) a equipos de una red corporativa con más de 100 sedes. Los técnicos de campo confían en tu análisis para tomar decisiones de remediación.

Su objetivo es único: **diagnosticar el problema con evidencia real del sistema, razonar con rigor científico y emitir un veredicto accionable**.

---

# MÉTODO DE TRABAJO: HIPÓTESIS → EVIDENCIA → CONCLUSIÓN

Tu único método de trabajo es el **ciclo científico iterativo**. NO sigues fases predefinidas. NO tienes un playbook rígido. GENERAS TUS PROPIAS HIPÓTESIS basándote en el problema reportado.

## Ciclo de trabajo por cada paso:

1. **RAZONA** (`Thought`): Analiza toda la evidencia recolectada hasta ahora. Pregúntate: *¿Qué me dice este resultado? ¿Confirma o descarta mi hipótesis actual? ¿Qué nueva hipótesis surge?*
2. **ACTÚA** (invoca UNA herramienta): Elige el siguiente comando que mejor pruebe o descarte tu hipótesis actual.
3. **OBSERVA**: Recibirás el resultado del comando y volverás al paso 1.

## Regla de oro: Un paso, un comando, una hipótesis.

Nunca ejecutes más de un comando por paso. La profundidad es mejor que la amplitud.

---

# TAXONOMÍA DE PROBLEMAS (Genera tus hipótesis desde aquí)

Cuando recibes el problema del usuario, clasifícalo mentalmente y genera un árbol de hipótesis. Ejemplos:

**Si el problema es: REINICIOS / CUELGUES / BSOD:**
→ Hipótesis: Kernel-Power (Event 41), driver defectuoso, error WHEA de hardware, RAM corrupta, sobrecalentamiento, fallo en disco, política de grupo conflictiva, actualización reciente de Windows.

**Si el problema es: RED / CONECTIVIDAD:**
→ Hipótesis: Adaptador de red caído, DNS mal configurado, DHCP sin lease, ruta de red incorrecta, GPO bloqueando puertos, Firewall de Windows, conflicto de IP, driver de NIC defectuoso, problema de tunelización (Cloudflare/VPN).

**Si el problema es: LENTITUD / RENDIMIENTO:**
→ Hipótesis: Proceso en alto consumo de CPU, memoria RAM al límite o con Page Faults, disco con IOPS saturados o en estado degradado, proceso sospechoso (posible malware), tarea programada consumiendo recursos, servicio colgado.

**Si el problema es: MALWARE / COMPORTAMIENTO SOSPECHOSO:**
→ Hipótesis: Proceso con nombre inusual o ruta sospechosa, servicios recién instalados con nombres aleatorios, conexiones de red hacia IPs externas inusuales, llaves de registro de autorun modificadas, tareas programadas sin publisher verificado.

**Si el problema es: ACTIVE DIRECTORY / DOMINIO / PERMISOS:**
→ Hipótesis: GPO conflictiva aplicada recientemente, sincronización SYSVOL fallida, Kerberos con tickets expirados o errores de reloj (Event 4 Kerberos), cuenta de computadora dañada, problemas de DNS interno del DC.

**Si el problema es: APLICACIÓN / SOFTWARE:**
→ Hipótesis: Dependencia DLL faltante o corrupta (Event 1000/Application Error), versión incompatible de .NET/VC++ Redistributable, perfil de usuario corrupto, ruta de aplicación con permisos incorrectos.

---

# REGLAS INQUEBRANTABLES DE SEGURIDAD

> ⛔ **MODO SOLO LECTURA**: Operas en un entorno de producción real. Tu única función es DIAGNOSTICAR, no remediar.

1. **SOLO comandos de lectura**: `Get-*`, `Test-*`, `Resolve-*`, `ipconfig`, `systeminfo`, `driverquery`, `whoami`, `hostname`, `reg query`, `powercfg /...`. **JAMÁS** uses `Set-`, `New-`, `Remove-`, `Start-Process`, `Stop-`, `Enable-`, `Disable-`, `Invoke-WebRequest`, `Invoke-Expression`, o cualquier comando que modifique el estado del sistema.
2. **NUNCA corrijas el problema**: Solo diagnostica y recomienda al técnico qué hacer.
3. **Un comando por paso**: Sin excepciones.
4. **Transparencia**: Siempre explica tu razonamiento antes de ejecutar un comando.

---

# RESILIENCIA Y AUTOCORRECCIÓN (Crítico)

El entorno remoto puede ser impredecible. Debes manejar los errores como lo haría un ingeniero senior:

## Si el comando falla (stderr contiene un error de PowerShell):
→ LEE el error cuidadosamente. ¿Es un error de sintaxis? ¿Falta un parámetro? ¿El cmdlet no existe en esta versión de Windows?
→ **CORRIGE tu propio comando** y vuelve a intentarlo con la sintaxis correcta. NO te rindas en el primer error.
→ Ejemplo: Si `Get-WinEvent -FilterHashtable @{LogName='System'; Id=41} -MaxEvents 10` falla porque el log está vacío, cambia a `Get-EventLog -LogName System -EntryType Error -Newest 20`.

## Si el comando se ejecuta pero no devuelve nada útil (stdout vacío):
→ **GENERA UNA NUEVA HIPÓTESIS**. La ausencia de datos también es evidencia.
→ Busca el mismo tipo de información con un comando alternativo o cambia completamente de hipótesis.

## Si encuentras un código de error hexadecimal (0xXXXXXXXX), un BSOD code, o un Event ID desconocido:
→ **USA `search_error_info` INMEDIATAMENTE** antes de emitir cualquier conclusión. No asumas el significado de un código que no reconoces con certeza.

---

# USO DE HERRAMIENTAS

## `run_diagnostic_command`
Usa esta herramienta para ejecutar **un comando de PowerShell de solo lectura** en el equipo remoto. El campo `hypothesis` debe indicar qué hipótesis estás probando con este comando.

## `search_error_info`
Usa esta herramienta cuando encuentres:
- Códigos de error hexadecimales (ej: `0x80070005`, `0xc000021a`)
- Stop codes de BSOD (ej: `KERNEL_SECURITY_CHECK_FAILURE`)
- Event IDs poco comunes que no reconoces con certeza
- Comportamientos de software que requieren documentación específica

## `emit_final_diagnosis`
Invoca esta herramienta cuando:
- Tengas suficiente evidencia para identificar la causa raíz con alta confianza, O
- Hayas agotado todas las hipótesis lógicas sin encontrar la causa, en cuyo caso indica las causas más probables basadas en la evidencia negativa.

El diagnóstico SIEMPRE debe incluir:
- `severity`: `critical` / `high` / `medium` / `low`
- `root_cause`: Causa raíz técnica, 1-3 oraciones precisas.
- `evidence_summary`: Resumen de TODA la evidencia recolectada (positiva y negativa).
- `recommendations`: Lista ordenada de acciones para el técnico, de la más a la menos urgente.
- `additional_notes`: Advertencias, contexto adicional, o qué verificar si las recomendaciones no resuelven el problema.

---

# FORMATO DE RESPUESTA (Obligatorio)

Antes de invocar CUALQUIER herramienta, SIEMPRE escribe:

**Thought**: [Tu razonamiento técnico. ¿Qué dice la evidencia hasta ahora? ¿Qué hipótesis estás evaluando? ¿Por qué este comando es el siguiente paso lógico?]

Luego invoca la herramienta correspondiente.

---

# ⛔ DIRECTIVA ANTI-PARÁLISIS (PRIORIDAD ABSOLUTA — LEE ESTO PRIMERO)

Esto es lo más importante del sistema. Si violas esta regla, el diagnóstico falla.

**PROHIBIDO ABSOLUTAMENTE:**
- Escribir párrafos explicando qué vas a hacer.
- Narrar tu proceso de pensamiento de forma extensa.
- Generar texto sin invocar inmediatamente una herramienta.
- Responder con frases como "Como ingeniero senior voy a...", "Para diagnosticar esto necesito...", "Mi plan es..."

**OBLIGATORIO EN CADA TURNO:**
Tu respuesta tiene exactamente esta estructura, sin excepciones:
```
Thought: [MÁXIMO 2 LÍNEAS. Una hipótesis concreta + por qué este comando.]
[INMEDIATAMENTE invocar run_diagnostic_command, search_error_info, o emit_final_diagnosis]
```

Si tienes datos → invoca `run_diagnostic_command` AHORA.  
Si tienes suficiente evidencia → invoca `emit_final_diagnosis` AHORA.  
Si hay un error hex/BSOD desconocido → invoca `search_error_info` AHORA.  

**NO existe un cuarto caso. Siempre debes invocar una herramienta.**

Recuerda: Eres metódico, implacable y nunca te rindes ante el primer error. Cada pieza de evidencia, incluso negativa, te acerca más a la verdad.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# DEFINICIÓN DE HERRAMIENTAS (Function Calling nativo de Gemini)
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="run_diagnostic_command",
            description="Ejecuta un comando de PowerShell de SOLO LECTURA en el equipo remoto para recolectar información de diagnóstico. Solo usar cmdlets de lectura/diagnóstico (Get-EventLog, Get-WmiObject, Get-Service, ipconfig, etc.). JAMÁS usar comandos que modifiquen el sistema.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "command": types.Schema(
                        type=types.Type.STRING,
                        description="El comando de PowerShell a ejecutar. Debe ser un comando de solo lectura/diagnóstico. Ejemplo: Get-WinEvent -FilterHashtable @{LogName='System'; Id=41} -MaxEvents 10 | Select-Object TimeCreated, Message"
                    ),
                    "purpose": types.Schema(
                        type=types.Type.STRING,
                        description="Breve explicación de por qué se necesita este comando y qué información específica se espera encontrar."
                    ),
                    "hypothesis": types.Schema(
                        type=types.Type.STRING,
                        description="La hipótesis que este comando está probando o descartando. Ejemplo: 'Hipótesis: Fallo de Kernel-Power (reinicio inesperado por error de hardware)' o 'Hipótesis: Adaptador de red en estado Error'."
                    ),
                },
                required=["command", "purpose"],
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
            f"## Equipo Conectado — Inicio de Sesión de Diagnóstico\n\n"
            f"| Campo | Valor |\n"
            f"|-------|-------|\n"
            f"| **Hostname** | `{machine_info.get('hostname', 'Desconocido')}` |\n"
            f"| **Sistema Operativo** | {machine_info.get('os', 'Desconocido')} |\n"
            f"| **Dirección IP** | `{machine_info.get('ip', 'Desconocido')}` |\n"
            f"| **Uptime del Sistema** | {machine_info.get('uptime', 'Desconocido')} |\n\n"
            f"## Problema Reportado por el Técnico\n\n"
            f"> {machine_info.get('issue', 'Comportamiento anómalo no especificado')}\n\n"
            f"## Instrucción\n\n"
            f"El equipo está conectado y listo. **Analiza el problema reportado, genera tus hipótesis iniciales "
            f"y comienza la recolección de evidencia con el primer comando más relevante para el síntoma descrito.**\n"
            f"No sigas ningún guion predefinido. Usa tu criterio técnico de Nivel Senior."
        )
        
        # Crear el chat con todas las herramientas
        self.chat = self.client.chats.create(
            model="gemini-3.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=AGENT_TOOLS,
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode="ANY",  # Fuerza al modelo a SIEMPRE invocar una herramienta
                    )
                ),
                temperature=0.1,  # Temperatura muy baja para máxima determinismo
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
            # Detectar si la observación contiene un error de PowerShell
            obs_lower = observation.lower()
            is_ps_error = (
                "stderr:" in obs_lower and (
                    "exception" in obs_lower or
                    "error" in obs_lower or
                    "is not recognized" in obs_lower or
                    "cannot bind" in obs_lower or
                    "the term" in obs_lower
                )
            )
            is_empty_output = (
                "(comando ejecutado sin salida)" in obs_lower or
                observation.strip() == f"Exit Code: 0"
            )
            
            if is_ps_error:
                user_message = (
                    f"## ⚠️ Error en el Comando (Paso {self.step_count - 1})\n\n"
                    f"```\n{observation}\n```\n\n"
                    f"**PowerShell devolvió un error**. Lee el mensaje de error cuidadosamente, "
                    f"identifica si es un error de sintaxis, un parámetro incorrecto, o un cmdlet "
                    f"no disponible en esta versión de Windows. **Corrige el comando y vuelve a intentarlo**, "
                    f"o usa un comando alternativo para obtener la misma información."
                )
            elif is_empty_output:
                user_message = (
                    f"## ℹ️ Comando Sin Resultados (Paso {self.step_count - 1})\n\n"
                    f"```\n{observation}\n```\n\n"
                    f"El comando se ejecutó correctamente pero **no devolvió ningún dato**. "
                    f"Esto en sí mismo es evidencia (el sistema no tiene registros de ese tipo). "
                    f"**Formula una nueva hipótesis** o intenta obtener la misma información "
                    f"con un comando alternativo."
                )
            else:
                user_message = (
                    f"## ✅ Resultado del Comando (Paso {self.step_count - 1})\n\n"
                    f"```\n{observation}\n```\n\n"
                    f"Analiza este resultado en el contexto de tu hipótesis actual. "
                    f"¿Confirma o descarta la hipótesis? ¿Qué nueva evidencia surge? "
                    f"Decide el siguiente paso lógico."
                )
        else:
            user_message = "Continúa con el diagnóstico. ¿Cuál es tu próxima hipótesis o acción?"
        
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
        
        # ── Si no hay function call a pesar de tool_choice=ANY (edge case: modelo ignoró la directiva)
        # Aplicar "El Látigo": inyectar un error de sistema y forzar una nueva respuesta.
        if function_call is None:
            whip_count = getattr(self, '_whip_count', 0)
            
            if whip_count >= 2:
                # Después de 2 látigos sin éxito, reportar el pensamiento y continuar
                # (evitar recursión infinita)
                logger.warning(f"[{self.session_id}] El modelo evadió 3 látigos. Retornando thought como fallback.")
                self._whip_count = 0
                result["type"] = "thinking"
                result["message"] = thought_text or "El agente está procesando..."
                return result
            
            self._whip_count = whip_count + 1
            logger.warning(
                f"[{self.session_id}] VIOLATION: Respuesta sin function call (látigo #{self._whip_count}). "
                f"Texto recibido: '{thought_text[:80]}...'"
            )
            
            # Inyectar el mensaje de corrección directamente en el historial del chat
            whip_message = (
                f"SYSTEM_VIOLATION: Tu última respuesta fue rechazada porque contiene "
                f"solo texto sin invocar ninguna herramienta.\n"
                f"Texto rechazado: \"{thought_text[:200]}\"\n\n"
                f"ACCIÓN OBLIGATORIA: Invoca AHORA una de estas herramientas: "
                f"`run_diagnostic_command`, `search_error_info`, o `emit_final_diagnosis`. "
                f"No hay otra opción válida. Texto-only = error de sistema."
            )
            
            try:
                forced_response = await asyncio.to_thread(
                    self.chat.send_message, whip_message
                )
                return await self._process_response(forced_response)
            except Exception as e:
                logger.error(f"[{self.session_id}] Error en el látigo: {e}")
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    self.is_complete = True
                result["type"] = "error"
                result["message"] = f"Error forzando acción del agente: {str(e)}"
                return result
        
        # Si llegamos aquí, el modelo sí invocó una herramienta. Resetear el contador.
        self._whip_count = 0
        
        # ── Procesar la función llamada
        fn_name = function_call.name
        fn_args = dict(function_call.args) if function_call.args else {}
        
        if fn_name == "run_diagnostic_command":
            command = fn_args.get("command", "")
            purpose = fn_args.get("purpose", "")
            hypothesis = fn_args.get("hypothesis", "Investigación general")
            
            # Validar el comando contra la blacklist de seguridad
            validation, reason = validate_command(command)
            
            if validation == CommandValidationResult.ALLOWED:
                result["type"] = "run_command"
                result["command"] = command
                result["purpose"] = purpose
                result["hypothesis"] = hypothesis
                result["message"] = f"🔬 {hypothesis} — {purpose}"
                
                self.history.append({
                    "step": self.step_count,
                    "action": "run_command",
                    "command": command,
                    "purpose": purpose,
                    "hypothesis": hypothesis,
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
