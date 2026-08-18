import sys
import socket
from app.core.database import SessionLocal
from app.models.server import ServerConfig
from app.services.monitoring_service import _get_windows_top_processes, logger
import logging
logging.basicConfig(level=logging.WARNING)

def is_local_ip(target_ip):
    if target_ip in ["127.0.0.1", "localhost", "::1"]:
        return True
    try:
        return target_ip in [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None)]
    except Exception:
        return False

db = SessionLocal()
server = db.query(ServerConfig).filter(ServerConfig.ip == '192.168.20.100').first()
print('is_local_ip:', is_local_ip(server.ip))
res = _get_windows_top_processes(server)
print('Result:', res)
db.close()
