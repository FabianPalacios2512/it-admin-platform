import wmi
import pythoncom
from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.core.config import settings
import datetime

def sync_ad_events():
    db = SessionLocal()
    print("🔍 [AD Sync] Buscando eventos nativos en el Domain Controller...")
    
    # Inicializar el modelo COM en este hilo (requerido para WMI en background/scheduler)
    pythoncom.CoInitialize()
    try:
        # WMI usando la Cuenta de Servicio (Súper Administrador)
        c = wmi.WMI(computer=settings.LDAP_SERVER_IP, user=settings.SERVICE_USER, password=settings.SERVICE_PASS)
        
        # Consulta de Eventos de Seguridad: 4767 (Desbloqueo), 4724 (Reset Pass)
        # Limitamos la consulta para no saturar la red con miles de eventos
        wql = "SELECT * FROM Win32_NTLogEvent WHERE Logfile='Security' AND (EventCode='4767' OR EventCode='4724')"
        logs = c.query(wql)
        
        nuevos = 0
        for log in logs:
            event_id = f"{log.RecordNumber}-{log.EventCode}"
            
            if not db.query(AuditLog).filter(AuditLog.event_id == event_id).first():
                action_name = "Desbloqueó cuenta" if log.EventCode == '4767' else "Reset de Contraseña"
                
                # Intentar extraer el usuario afectado y el administrador de los InsertionStrings
                # En Eventos Windows 4724 y 4767:
                # InsertionStrings[1] = Usuario Afectado (Target Account Name)
                # InsertionStrings[4] = Administrador (Subject Account Name)
                
                target_user = "Sistema"
                admin_user = "Admin AD Nativo"
                
                try:
                    if log.InsertionStrings and len(log.InsertionStrings) >= 5:
                        target_user = log.InsertionStrings[1]
                        admin_user = log.InsertionStrings[4]
                except Exception as parse_e:
                    print(f"No se pudo parsear InsertionStrings: {parse_e}")
                
                audit = AuditLog(
                    username=admin_user,
                    action=action_name,
                    target=target_user, 
                    status="Completado",
                    source="AD Nativo",
                    event_id=event_id,
                )
                db.add(audit)
                nuevos += 1
                
        db.commit()
        print(f"✅ [AD Sync] Se importaron {nuevos} eventos nativos (WMI).")
        
    except Exception as e:
        print(f"❌ [AD Sync] Aviso: Falló conexión WMI. (Revisa Firewall, Permisos DCOM, IP). Error: {e}")
    finally:
        db.close()
        # Liberar los recursos de COM
        pythoncom.CoUninitialize()
