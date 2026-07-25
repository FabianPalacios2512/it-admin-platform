import sys
sys.path.append('.')
from app.services.printer_service import get_drivers

try:
    print(get_drivers())
except Exception as e:
    print(e)
