from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.printer_service import (
    get_printers,
    get_drivers,
    add_printer,
    update_printer_ip,
    clear_spooler,
    print_test_page,
    delete_printer,
    restart_spooler,
    generate_mapping_script,
    get_printer_jobs,
    get_printer_history
)

router = APIRouter()

class PrinterCreate(BaseModel):
    name: str
    ip: str
    driver: str
    shared: bool = False
    share_name: Optional[str] = ""

class PrinterUpdate(BaseModel):
    new_name: str
    new_ip: str
    shared: bool = False
    share_name: Optional[str] = ""


@router.get("/", response_model=List[Dict[str, Any]])
def list_printers():
    """Obtiene la lista de todas las impresoras gestionadas."""
    try:
        return get_printers()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drivers", response_model=List[str])
def list_drivers():
    """Obtiene los drivers instalados en el servidor."""
    try:
        return get_drivers()
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create_printer(req: PrinterCreate):
    """Agrega una nueva impresora."""
    try:
        add_printer(req.name, req.ip, req.driver, req.shared, req.share_name)
        return {"success": True, "message": f"Impresora '{req.name}' agregada correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{name}")
def update_printer(name: str, req: PrinterUpdate):
    """Edita la impresora (reenruta IP o cambia nombre)."""
    try:
        update_printer_ip(name, req.new_name, req.new_ip, req.shared, req.share_name)
        return {"success": True, "message": f"Impresora actualizada a {req.new_ip}."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/clear-spooler")
def printer_clear_spooler(name: str):
    """Vacía la cola de impresión atascada."""
    try:
        clear_spooler(name)
        return {"success": True, "message": f"Cola de impresión de '{name}' limpiada."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{name}/test-page")
def printer_test_page(name: str):
    """Imprime una página de prueba."""
    try:
        print_test_page(name)
        return {"success": True, "message": f"Página de prueba enviada a '{name}'."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}")
def remove_printer(name: str):
    """Elimina la impresora de forma segura."""
    try:
        delete_printer(name)
        return {"success": True, "message": f"Impresora '{name}' eliminada correctamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restart-spooler")
def api_restart_spooler():
    """Reinicia el servicio Print Spooler globalmente en el servidor de impresión."""
    try:
        restart_spooler()
        return {"success": True, "message": "Spooler reiniciado exitosamente."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/mapping-script")
def api_mapping_script(name: str):
    """Retorna un script de PowerShell para mapear una impresora compartida."""
    try:
        script = generate_mapping_script(name)
        return {"success": True, "script": script}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/jobs")
def api_get_printer_jobs(name: str):
    """Retorna los trabajos actuales en la cola de impresión."""
    try:
        jobs = get_printer_jobs(name)
        return jobs
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/history")
def api_get_printer_history(name: str):
    """Retorna el historial de impresiones (Auditoría)."""
    try:
        history = get_printer_history(name, limit=50)
        return history
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


