import uuid
import time
from typing import Dict, Any, Callable
import asyncio
from fastapi import BackgroundTasks

# En memoria para simplificar (Si se reinicia el servidor, se pierden las tareas, lo cual es aceptable para esta escala)
_TASKS: Dict[str, Dict[str, Any]] = {}

def create_task(task_type: str, username: str, description: str) -> str:
    """Crea una nueva tarea en estado 'pending' y retorna su ID."""
    task_id = str(uuid.uuid4())
    _TASKS[task_id] = {
        "id": task_id,
        "type": task_type,
        "username": username, # Quién inició la tarea (para filtrar)
        "description": description,
        "status": "processing",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time()
    }
    return task_id

def get_task(task_id: str) -> Dict[str, Any]:
    return _TASKS.get(task_id)

def get_user_tasks(username: str, status: str = None) -> list:
    """Obtiene las tareas recientes de un usuario (para polling)."""
    # Limpiamos tareas viejas (> 24h)
    clean_old_tasks()
    
    tasks = []
    for t_id, t in _TASKS.items():
        if t["username"] == username:
            if status and t["status"] != status:
                continue
            tasks.append(t)
    # Ordenar por creadas recientemente
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    return tasks

def update_task_status(task_id: str, status: str, result: Any = None, error: str = None, progress: int = None):
    if task_id in _TASKS:
        _TASKS[task_id]["status"] = status
        if result is not None:
            _TASKS[task_id]["result"] = result
        if error is not None:
            _TASKS[task_id]["error"] = error
        if progress is not None:
            _TASKS[task_id]["progress"] = progress
        _TASKS[task_id]["updated_at"] = time.time()

def clean_old_tasks():
    """Elimina tareas que lleven más de 24 horas en el diccionario."""
    current_time = time.time()
    keys_to_delete = [k for k, v in _TASKS.items() if current_time - v["created_at"] > 86400]
    for k in keys_to_delete:
        del _TASKS[k]

async def run_async_task(task_id: str, func: Callable, *args, **kwargs):
    """Ejecuta una función asíncrona (o síncrona en un hilo separado) y actualiza el estado."""
    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            # Ejecuta la función síncrona en un hilo para no bloquear el event loop
            import functools
            loop = asyncio.get_running_loop()
            bound_func = functools.partial(func, *args, **kwargs)
            result = await loop.run_in_executor(None, bound_func)
        
        update_task_status(task_id, "completed", result=result, progress=100)
    except Exception as e:
        update_task_status(task_id, "error", error=str(e))
