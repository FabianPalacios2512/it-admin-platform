import sys
import asyncio

from dotenv import load_dotenv
load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import auth, audit, accounts, servers, fileserver, graph, groups, printers, rds, devices, monitoring, wifi, system, terminal, quarantine, licenses
from app.core.database import Base, engine
from app.models.server import ServerConfig
from app.models.rds import RdsConfig  # Ensure table is created
from app.models.delegation import TemporaryDelegation
from app.models.license_audit import LicenseAudit
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.ad_event_sync import sync_ad_events
from app.services.monitoring_service import sync_monitoring_stats
import contextlib

import sqlite3
import os
try:
    if os.path.exists("./it_platform.db"):
        with sqlite3.connect("./it_platform.db") as conn:
            conn.execute("ALTER TABLE rds_configs ADD COLUMN file_prefix VARCHAR DEFAULT 'nova.ft'")
            conn.commit()
except Exception:
    pass

Base.metadata.create_all(bind=engine)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    app.state.scheduler = scheduler
    scheduler.add_job(sync_ad_events, 'interval', minutes=3)
    # scheduler.add_job(sync_monitoring_stats, 'interval', minutes=1) # Desactivado: ahora usamos Zabbix
    from app.services.exchange_service import revoke_expired_delegations
    scheduler.add_job(revoke_expired_delegations, 'cron', hour=2, minute=0)
    scheduler.start()
    
    # Ejecutar una vez al inicio en el background (no bloqueante)
    import datetime
    scheduler.add_job(sync_ad_events, 'date', run_date=datetime.datetime.now())
    # scheduler.add_job(sync_monitoring_stats, 'date', run_date=datetime.datetime.now()) # Desactivado: ahora usamos Zabbix
    
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title="IT Admin Platform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(audit.router, prefix="/api/v1/audit", tags=["audit"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
app.include_router(servers.router, prefix="/api/v1/servers", tags=["servers"])
app.include_router(fileserver.router, prefix="/api/v1/fileserver", tags=["fileserver"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
app.include_router(printers.router, prefix="/api/v1/printers", tags=["printers"])
app.include_router(rds.router, prefix="/api/v1/rds", tags=["rds"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(wifi.router, prefix="/api/v1/wifi", tags=["wifi"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(terminal.router, prefix="/api/v1/terminal", tags=["terminal"])
app.include_router(quarantine.router, prefix="/api/v1/quarantine", tags=["quarantine"])
app.include_router(licenses.router, prefix="/api/v1/licenses", tags=["licenses"])
from app.api.v1 import delegation
app.include_router(delegation.router, prefix="/api/v1/delegation", tags=["delegation"])
from app.api.v1 import diagnostics
app.include_router(diagnostics.router, prefix="/api/v1/diagnostics", tags=["diagnostics"])
from app.api.v1 import zabbix
app.include_router(zabbix.router, prefix="/api/v1/zabbix", tags=["zabbix"])
from app.api.v1 import gpo
app.include_router(gpo.router, prefix="/api/v1/gpo", tags=["gpo"])
from app.api.v1 import exchange
app.include_router(exchange.router, prefix="/api/v1/exchange", tags=["exchange"])
from app.api.v1 import tasks
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
from app.api.v1 import fortigate
app.include_router(fortigate.router, prefix="/api/v1/fortigate", tags=["fortigate"])
# ---------------------------------------------------------
# Integración: Servir Frontend Estático (Vue SPA)
# ---------------------------------------------------------
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
import os

import sys

if getattr(sys, 'frozen', False):
    # Si corre desde PyInstaller .exe, el ejecutable está en la raíz del backend
    base_dir = os.path.dirname(sys.executable)
else:
    # Si corre en desarrollo (python normal)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

frontend_path = os.path.join(base_dir, "dist")

if os.path.exists(frontend_path):
    assets_path = os.path.join(frontend_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        # Evitar capturar rutas de la API que no existen (para que devuelvan JSON 404 nativo)
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        
        # Intentar servir un archivo estático específico (favicon.ico, manifest, etc.)
        file_path = os.path.join(frontend_path, catchall)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Para cualquier otra ruta del navegador, servimos index.html (Vue Router se encarga)
        return FileResponse(os.path.join(frontend_path, "index.html"))
else:
    @app.get("/")
    def read_root():
        return {"message": "Welcome to IT Admin Platform API (Frontend not built)"}

if __name__ == "__main__":
    import uvicorn
    import multiprocessing
    multiprocessing.freeze_support()
    uvicorn.run(app, host="0.0.0.0", port=8000)
