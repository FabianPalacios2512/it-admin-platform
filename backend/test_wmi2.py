import sys
from app.core.database import SessionLocal
from app.models.server import ServerConfig
from app.services.monitoring_service import _get_windows_top_processes

db = SessionLocal()
server = db.query(ServerConfig).filter(ServerConfig.ip == '192.168.20.100').first()
print('is_local_ip:', server.ip)
res = _get_windows_top_processes(server)
print('Result:', res)
db.close()
