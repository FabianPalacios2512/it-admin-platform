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
        
        # Consulta de Eventos de Seguridad: 
        # 4767 (Desbloqueo), 4724 (Reset Pass), 4722 (Habilitar), 4725 (Deshabilitar), 4728 (Grupo), 4738 (Cambio cuenta)
        # Limitamos la consulta para no saturar la red con miles de eventos
        wql = "SELECT * FROM Win32_NTLogEvent WHERE Logfile='Security' AND (EventCode='4767' OR EventCode='4724' OR EventCode='4722' OR EventCode='4725' OR EventCode='4728' OR EventCode='4738')"
        logs = c.query(wql)
        
        nuevos = 0
        for log in logs:
            event_id = f"{log.RecordNumber}-{log.EventCode}"
            
            if not db.query(AuditLog).filter(AuditLog.event_id == event_id).first():
                
                # Mapeo de Acciones
                action_name = "Auditoría AD"
                if log.EventCode == '4767': action_name = "Desbloqueó cuenta"
                elif log.EventCode == '4724' or log.EventCode == '4723': action_name = "Reset de Contraseña"
                elif log.EventCode == '4722': action_name = "Habilitó cuenta"
                elif log.EventCode == '4725': action_name = "Deshabilitó cuenta"
                elif log.EventCode == '4728': action_name = "Añadió usuario a Grupo Global"
                elif log.EventCode == '4738': action_name = "Modificó atributos de cuenta"
                
                # Intentar extraer el usuario afectado y el administrador de los InsertionStrings
                # En Eventos Windows 4724, 4767, 4722, 4725, 4738:
                # InsertionStrings[1] = Usuario Afectado (Target Account Name)
                # InsertionStrings[4] = Administrador (Subject Account Name)
                # En Eventos 4728 (Grupos):
                # InsertionStrings[0] = Miembro Añadido
                # InsertionStrings[2] = Grupo
                # InsertionStrings[6] = Administrador
                
                target_user = "Sistema"
                admin_user = "Admin AD Nativo"
                
                try:
                    if log.InsertionStrings:
                        if log.EventCode == '4728' and len(log.InsertionStrings) >= 7:
                            target_user = f"{log.InsertionStrings[0]} -> {log.InsertionStrings[2]}"
                            admin_user = log.InsertionStrings[6]
                        elif len(log.InsertionStrings) >= 5:
                            target_user = log.InsertionStrings[1]
                            admin_user = log.InsertionStrings[4]
                            
                            # Para 4738 podríamos buscar si cambió password_never_expires, pero WMI no facilita fácilmente todos los flags modificados, 
                            # lo marcamos como "Modificó atributos".
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
