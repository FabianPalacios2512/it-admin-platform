"""
Endpoint WebSocket para el Agente de Diagnóstico IT.

Maneja la comunicación bidireccional entre el script de PowerShell
(ejecutándose en el equipo afectado) y el motor ReAct del agente.

También soporta "viewers" WebSocket para que el panel de administración
pueda monitorear sesiones de diagnóstico en tiempo real.

Protocolo (PS ↔ Backend):
  PS → Backend:  {"type": "machine_info", ...}  |  {"type": "command_result", ...}
  Backend → PS:  {"type": "execute_command", ...} | {"type": "status_update", ...} | {"type": "diagnosis_complete", ...}

Protocolo (Viewer ↔ Backend):
  Backend → Viewer: Replica todos los mensajes de la sesión (thought, command, result, diagnosis)
"""

import json
import asyncio
import logging
import socket
import os
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.services.diagnostic_agent import (
    DiagnosticSession,
    COMMAND_TIMEOUT_SECONDS,
)

router = APIRouter()
logger = logging.getLogger("diagnostics_ws")

# ── Almacén de sesiones activas y completadas (en memoria)
active_sessions: dict[str, dict] = {}
completed_sessions: list[dict] = []  # Últimas N sesiones completadas
MAX_COMPLETED_SESSIONS = 50

# ── Viewers conectados por sesión (admin panel WebSockets)
session_viewers: dict[str, list[WebSocket]] = {}


async def send_json(ws: WebSocket, data: dict):
    """Envía un mensaje JSON al WebSocket con manejo de errores."""
    try:
        await ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
    except Exception as e:
        logger.error(f"Error al enviar WS: {e}")


async def broadcast_to_viewers(session_id: str, data: dict):
    """Envía un mensaje a todos los viewers conectados a una sesión."""
    viewers = session_viewers.get(session_id, [])
    dead_viewers = []
    for viewer_ws in viewers:
        try:
            await viewer_ws.send_text(json.dumps(data, ensure_ascii=False, default=str))
        except Exception:
            dead_viewers.append(viewer_ws)
    # Limpiar viewers desconectados
    for dv in dead_viewers:
        viewers.remove(dv)


def save_completed_session(session: DiagnosticSession, event_log: list):
    """Guarda una sesión completada en el historial."""
    record = {
        "session_id": session.session_id,
        "hostname": session.machine_info.get("hostname", "?"),
        "ip": session.machine_info.get("ip", "?"),
        "os": session.machine_info.get("os", "?"),
        "issue": session.machine_info.get("issue", "?"),
        "started_at": session.created_at.isoformat(),
        "completed_at": datetime.now().isoformat(),
        "steps_taken": session.step_count,
        "is_complete": session.is_complete,
        "final_report": session.final_report,
        "event_log": event_log,  # Historial completo de eventos para replay
    }
    completed_sessions.insert(0, record)
    # Mantener solo las últimas N
    while len(completed_sessions) > MAX_COMPLETED_SESSIONS:
        completed_sessions.pop()


@router.websocket("/ws")
async def diagnostic_websocket(websocket: WebSocket):
    """
    WebSocket principal del agente de diagnóstico.
    
    Flujo:
    1. Acepta conexión del script de PowerShell
    2. Espera mensaje initial de `machine_info`
    3. Crea una DiagnosticSession con el motor ReAct
    4. Entra en el loop: agent decide → envía comando → PS ejecuta → envía resultado → repite
    5. Termina cuando el agente emite diagnóstico final o se alcanza el límite de pasos
    """
    await websocket.accept()
    session = None
    session_id = None
    event_log = []  # Registro de todos los eventos para el viewer
    
    try:
        # ─────────────────────────────────────────────────────────────
        # PASO 1: Recibir información inicial del equipo
        # ─────────────────────────────────────────────────────────────
        await send_json(websocket, {
            "type": "status_update",
            "message": "Conexión establecida. Esperando información del equipo...",
            "phase": 0,
        })
        
        # Esperar el primer mensaje con timeout
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            initial_msg = json.loads(raw)
        except asyncio.TimeoutError:
            await send_json(websocket, {
                "type": "error",
                "message": "Timeout: No se recibió información del equipo en 30 segundos."
            })
            await websocket.close()
            return
        except json.JSONDecodeError:
            await send_json(websocket, {
                "type": "error",
                "message": "Error: El mensaje inicial no es JSON válido."
            })
            await websocket.close()
            return
        
        if initial_msg.get("type") != "machine_info":
            await send_json(websocket, {
                "type": "error",
                "message": f"Error: Se esperaba 'machine_info', se recibió '{initial_msg.get('type')}'"
            })
            await websocket.close()
            return
        
        machine_info = {
            "hostname": initial_msg.get("hostname", "Desconocido"),
            "os": initial_msg.get("os", "Desconocido"),
            "ip": initial_msg.get("ip", "Desconocido"),
            "uptime": initial_msg.get("uptime", "Desconocido"),
            "issue": initial_msg.get("issue", "Equipo se reinicia inesperadamente"),
        }
        
        logger.info(f"Equipo conectado: {machine_info['hostname']} ({machine_info['ip']})")
        
        # ─────────────────────────────────────────────────────────────
        # PASO 2: Crear la sesión del agente
        # ─────────────────────────────────────────────────────────────
        try:
            session = DiagnosticSession(machine_info)
            session_id = session.session_id
        except ValueError as e:
            await send_json(websocket, {
                "type": "error",
                "message": f"Error de configuración: {str(e)}"
            })
            await websocket.close()
            return
        
        active_sessions[session_id] = {
            "session": session,
            "websocket": websocket,
            "machine_info": machine_info,
            "started_at": datetime.now().isoformat(),
            "event_log": event_log,
        }
        
        # Inicializar lista de viewers para esta sesión
        session_viewers[session_id] = []
        
        status_msg = {
            "type": "status_update",
            "message": f"🧠 Agente de diagnóstico inicializado (sesión {session_id}). "
                       f"Analizando {machine_info['hostname']}...",
            "phase": 1,
            "session_id": session_id,
        }
        await send_json(websocket, status_msg)
        
        # Broadcast a viewers: sesión iniciada
        init_event = {
            "type": "session_started",
            "session_id": session_id,
            "machine_info": machine_info,
            "timestamp": datetime.now().isoformat(),
        }
        event_log.append(init_event)
        await broadcast_to_viewers(session_id, init_event)
        
        # ─────────────────────────────────────────────────────────────
        # PASO 3: Loop ReAct principal
        # ─────────────────────────────────────────────────────────────
        observation = None  # Primera iteración no tiene observación
        
        while not session.is_complete:
            # ── Esperar para no agotar la cuota de la API (Gemini 3.5 Flash = 5 RPM)
            await asyncio.sleep(12)
            
            # ── Pedir al agente el siguiente paso
            try:
                agent_result = await session.run_step(observation)
            except Exception as e:
                logger.error(f"[{session_id}] Error en run_step: {e}")
                error_event = {
                    "type": "error",
                    "message": f"Error del agente: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
                await send_json(websocket, error_event)
                event_log.append(error_event)
                await broadcast_to_viewers(session_id, error_event)
                await asyncio.sleep(1)  # Dar tiempo al cliente para recibir el mensaje
                break
            
            action_type = agent_result.get("type", "error")
            
            # ── Enviar el "Thought" del agente al técnico (transparencia)
            thought = agent_result.get("thought", "")
            if thought:
                thought_event = {
                    "type": "agent_thought",
                    "thought": thought,
                    "step": agent_result.get("step", session.step_count),
                    "timestamp": datetime.now().isoformat(),
                }
                await send_json(websocket, thought_event)
                event_log.append(thought_event)
                await broadcast_to_viewers(session_id, thought_event)
            
            # ── ACCIÓN: Ejecutar comando en PowerShell
            if action_type == "run_command":
                command = agent_result["command"]
                purpose = agent_result.get("purpose", "")
                phase = agent_result.get("phase", 0)
                
                cmd_event = {
                    "type": "execute_command",
                    "command": command,
                    "purpose": purpose,
                    "phase": phase,
                    "step": session.step_count,
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Enviar comando al PowerShell
                await send_json(websocket, cmd_event)
                event_log.append(cmd_event)
                await broadcast_to_viewers(session_id, cmd_event)
                
                # Esperar resultado del PowerShell
                try:
                    raw_result = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=COMMAND_TIMEOUT_SECONDS + 10
                    )
                    cmd_result = json.loads(raw_result)
                except asyncio.TimeoutError:
                    logger.warning(f"[{session_id}] Timeout esperando resultado de PS")
                    observation = (
                        "ERROR: Timeout — el comando tardó más de "
                        f"{COMMAND_TIMEOUT_SECONDS} segundos en ejecutarse. "
                        "Puede que el equipo esté bajo carga o el comando sea muy pesado."
                    )
                    timeout_event = {
                        "type": "command_timeout",
                        "command": command,
                        "step": session.step_count,
                        "timestamp": datetime.now().isoformat(),
                    }
                    event_log.append(timeout_event)
                    await broadcast_to_viewers(session_id, timeout_event)
                    continue
                except json.JSONDecodeError:
                    observation = "ERROR: La respuesta del PowerShell no es JSON válido."
                    continue
                
                if cmd_result.get("type") == "command_result":
                    stdout = cmd_result.get("stdout", "")
                    stderr = cmd_result.get("stderr", "")
                    exit_code = cmd_result.get("exit_code", -1)
                    
                    # Registrar para viewers
                    result_event = {
                        "type": "command_result",
                        "command": command,
                        "stdout": stdout[:2000] if stdout else "",  # Truncar para viewers
                        "stderr": stderr[:1000] if stderr else "",
                        "exit_code": exit_code,
                        "step": session.step_count,
                        "timestamp": datetime.now().isoformat(),
                    }
                    event_log.append(result_event)
                    await broadcast_to_viewers(session_id, result_event)
                    
                    # Construir la observación para el agente
                    observation = f"Exit Code: {exit_code}\n"
                    if stdout:
                        observation += f"STDOUT:\n{stdout}\n"
                    if stderr:
                        observation += f"STDERR:\n{stderr}\n"
                    if not stdout and not stderr:
                        observation += "(Comando ejecutado sin salida)\n"
                    
                    if len(observation) > 15000:
                        observation = observation[:14000] + "\n\n[... SALIDA TRUNCADA — MUY LARGA ...]"
                
                elif cmd_result.get("type") == "error":
                    observation = f"ERROR al ejecutar el comando: {cmd_result.get('message', 'Error desconocido')}"
                
                elif cmd_result.get("type") == "command_blocked":
                    observation = (
                        f"COMANDO BLOQUEADO por la whitelist local del PowerShell: "
                        f"{cmd_result.get('message', '')}. Usa un comando de solo lectura."
                    )
                    blocked_event = {
                        "type": "command_blocked",
                        "command": command,
                        "message": cmd_result.get("message", ""),
                        "step": session.step_count,
                        "timestamp": datetime.now().isoformat(),
                    }
                    event_log.append(blocked_event)
                    await broadcast_to_viewers(session_id, blocked_event)
                
                else:
                    observation = f"Respuesta inesperada del PowerShell: {json.dumps(cmd_result)[:500]}"
            
            # ── ACCIÓN: Búsqueda web (ya manejada internamente por el agente)
            elif action_type == "search_web":
                search_event = {
                    "type": "search_web",
                    "query": agent_result.get("search_query", ""),
                    "message": agent_result.get("message", "Buscando..."),
                    "step": session.step_count,
                    "timestamp": datetime.now().isoformat(),
                }
                await send_json(websocket, {
                    "type": "status_update",
                    "message": agent_result.get("message", "Buscando información..."),
                    "phase": 0,
                })
                event_log.append(search_event)
                await broadcast_to_viewers(session_id, search_event)
                observation = None
                continue
            
            # ── ACCIÓN: Diagnóstico completo
            elif action_type == "diagnosis_complete":
                report = agent_result.get("report", {})
                
                complete_msg = {
                    "type": "diagnosis_complete",
                    "report": report,
                    "message": agent_result.get("message", "Diagnóstico completado."),
                }
                await send_json(websocket, complete_msg)
                
                diagnosis_event = {
                    "type": "diagnosis_complete",
                    "report": report,
                    "timestamp": datetime.now().isoformat(),
                }
                event_log.append(diagnosis_event)
                await broadcast_to_viewers(session_id, diagnosis_event)
                
                logger.info(
                    f"[{session_id}] Diagnóstico completo para {machine_info['hostname']}. "
                    f"Severidad: {report.get('severity', '?')}"
                )
                break
            
            # ── ACCIÓN: Máximo de pasos alcanzado
            elif action_type == "max_steps":
                max_event = {
                    "type": "diagnosis_incomplete",
                    "message": agent_result.get("message", "Máximo de pasos alcanzado."),
                    "history": session.history,
                    "timestamp": datetime.now().isoformat(),
                }
                await send_json(websocket, max_event)
                event_log.append(max_event)
                await broadcast_to_viewers(session_id, max_event)
                break
            
            # ── ACCIÓN: Solo pensando (sin acción concreta)
            elif action_type == "thinking":
                observation = None
            
            # ── ERROR
            elif action_type == "error":
                error_event = {
                    "type": "error",
                    "message": agent_result.get("message", "Error desconocido del agente."),
                    "timestamp": datetime.now().isoformat(),
                }
                await send_json(websocket, error_event)
                event_log.append(error_event)
                await broadcast_to_viewers(session_id, error_event)
                observation = None
        
        # ─────────────────────────────────────────────────────────────
        # PASO 4: Cierre limpio
        # ─────────────────────────────────────────────────────────────
        end_event = {
            "type": "session_end",
            "message": "Sesión de diagnóstico finalizada.",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
        }
        await send_json(websocket, end_event)
        event_log.append(end_event)
        await broadcast_to_viewers(session_id, end_event)
    
    except WebSocketDisconnect:
        logger.info(f"[{session_id or '?'}] PowerShell desconectado.")
        if session_id:
            dc_event = {
                "type": "session_disconnected",
                "message": "El equipo remoto se desconectó.",
                "timestamp": datetime.now().isoformat(),
            }
            event_log.append(dc_event)
            await broadcast_to_viewers(session_id, dc_event)
    except Exception as e:
        logger.error(f"[{session_id or '?'}] Error inesperado en WS: {e}", exc_info=True)
        try:
            await send_json(websocket, {
                "type": "error",
                "message": f"Error interno del servidor: {str(e)}",
            })
            await asyncio.sleep(1)
        except Exception:
            pass
    finally:
        # Guardar sesión completada en historial
        if session:
            save_completed_session(session, event_log)
        
        # Limpiar sesión activa y viewers
        if session_id and session_id in active_sessions:
            del active_sessions[session_id]
        if session_id and session_id in session_viewers:
            # Notificar a viewers que la sesión terminó
            for viewer_ws in session_viewers[session_id]:
                try:
                    await viewer_ws.close()
                except Exception:
                    pass
            del session_viewers[session_id]
        
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/viewer/{session_id}")
async def viewer_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket para que el admin panel pueda observar una sesión activa en tiempo real.
    Recibe réplicas de todos los eventos de la sesión.
    """
    await websocket.accept()
    
    if session_id not in active_sessions:
        await send_json(websocket, {
            "type": "error",
            "message": f"Sesión '{session_id}' no encontrada o ya finalizada."
        })
        await websocket.close()
        return
    
    # Enviar historial acumulado hasta ahora (replay)
    session_data = active_sessions[session_id]
    event_log = session_data.get("event_log", [])
    
    await send_json(websocket, {
        "type": "viewer_connected",
        "session_id": session_id,
        "replay_events": len(event_log),
    })
    
    for event in event_log:
        await send_json(websocket, event)
    
    # Registrar como viewer
    if session_id not in session_viewers:
        session_viewers[session_id] = []
    session_viewers[session_id].append(websocket)
    
    try:
        # Mantener la conexión abierta hasta que el viewer se desconecte
        while True:
            await websocket.receive_text()  # Solo para detectar desconexión
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if session_id in session_viewers and websocket in session_viewers[session_id]:
            session_viewers[session_id].remove(websocket)


@router.get("/sessions")
async def list_diagnostic_sessions():
    """Lista las sesiones de diagnóstico activas (para monitoreo)."""
    sessions = []
    for sid, data in active_sessions.items():
        session: DiagnosticSession = data["session"]
        sessions.append(session.get_status())
    return {"active_sessions": sessions, "count": len(sessions)}


@router.get("/history")
async def list_completed_sessions():
    """Lista las últimas sesiones de diagnóstico completadas."""
    return {
        "sessions": completed_sessions,
        "count": len(completed_sessions),
    }


@router.get("/history/{session_id}")
async def get_session_detail(session_id: str):
    """Retorna el detalle completo de una sesión completada (con event log)."""
    for record in completed_sessions:
        if record["session_id"] == session_id:
            return record
    return {"error": "Sesión no encontrada", "session_id": session_id}


@router.get("/script")
async def get_powershell_script():
    """Sirve el script de PowerShell para el agente (Invoke-ITDiagnostic.ps1)."""
    # The script is in the root of the project (2 levels up from backend root)
    script_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "Invoke-ITDiagnostic.ps1")
    script_path = os.path.abspath(script_path)
    
    if not os.path.exists(script_path):
        return {"error": "Script not found on server"}
        
    return FileResponse(
        path=script_path,
        media_type="text/plain",
        filename="Invoke-ITDiagnostic.ps1"
    )


@router.get("/server-ip")
async def get_server_ip():
    """Retorna la IP local del servidor donde corre el backend."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No necesita conectar realmente, solo para obtener la ruta
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return {"ip": ip, "port": 8000}
    except Exception:
        return {"ip": "127.0.0.1", "port": 8000}
