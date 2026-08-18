
import sys
sys.path.append('.')
from app.core.database import SessionLocal
from app.models.server import ServerConfig
from app.services.monitoring_service import _get_windows_top_processes
import logging
logging.basicConfig(level=logging.DEBUG)

db = SessionLocal()
server = db.query(ServerConfig).filter(ServerConfig.ip == '192.168.20.100').first()
print('Server ID:', server.id, 'IP:', server.ip)
print(_get_windows_top_processes(server))
db.close()

