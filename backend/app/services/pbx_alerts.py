import logging
import asyncio
import httpx
from app.services.graph_service import MicrosoftGraphService
from app.core.database import SessionLocal
from app.models.pbx_alert import PBXAlert
from app.api.v1.pbx_recordings import run_vulnerability_scan, get_raw_logs_for_ip
from app.services.llm_rotator import llm_rotator

logger = logging.getLogger(__name__)

async def check_pbx_and_alert():
    """
    Ejecuta el escáner de vulnerabilidades del PBX y envía un correo 
    si detecta extensiones comprometidas o ataques masivos.
    """
    try:
        logger.info("Iniciando escaneo automático de seguridad del PBX...")
        result = run_vulnerability_scan()
        
        if result.get("status") != "success":
            logger.error(f"El escáner PBX falló: {result.get('message')}")
            return
            
        data = result.get("data", {})
        compromised = data.get("compromised", [])
        
        under_attack = [u for u in data.get("under_attack", []) if u.get("failed_attempts", 0) >= 10]
        
        toll_fraud = data.get("toll_fraud", [])
        
        # Guardar en base de datos de manera persistente
        try:
            db = SessionLocal()
            
            async def process_alert(alert_type, extension, attacker_ip, details, destination=None):
                exists = db.query(PBXAlert).filter_by(
                    alert_type=alert_type, 
                    extension=extension, 
                    attacker_ip=attacker_ip,
                    destination=destination,
                    resolved=False
                ).first()
                
                if exists:
                    return

                # Geolocation y AI check para ips atacantes
                ai_summary_text = None
                is_malicious = True # Por defecto verdadero si es toll_fraud o falla geolocation
                
                if attacker_ip and attacker_ip != 'Multiple' and alert_type in ['BREACH', 'BRUTE_FORCE']:
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as http_client:
                            geo_resp = await http_client.get(f"http://ip-api.com/json/{attacker_ip}")
                            geo_data = geo_resp.json()
                            if geo_data.get("status") == "success":
                                country = geo_data.get("country")
                                # Si no es Colombia, pasa a AI
                                if country != "Colombia":
                                    raw_logs = get_raw_logs_for_ip(attacker_ip)
                                    ai_result = await llm_rotator.analyze_logs(attacker_ip, raw_logs)
                                    is_malicious = ai_result.get("is_malicious", True)
                                    ai_summary_text = ai_result.get("summary")
                    except Exception as e:
                        logger.error(f"Error en Geolocation/AI para IP {attacker_ip}: {str(e)}")

                if is_malicious:
                    new_alert = PBXAlert(
                        alert_type=alert_type,
                        extension=extension,
                        attacker_ip=attacker_ip,
                        destination=destination,
                        details=details,
                        ai_summary=ai_summary_text
                    )
                    db.add(new_alert)

            for comp in compromised:
                await process_alert('BREACH', comp.get('extension'), comp.get('attacker_ip'), f"Fallos previos: {comp.get('failed_attempts_before_success')}")
                    
            for atk in under_attack:
                await process_alert('BRUTE_FORCE', atk.get('extension'), atk.get('last_ip', 'Multiple'), f"Intentos fallidos: {atk.get('failed_attempts')}")
                    
            for fraud in toll_fraud:
                await process_alert('TOLL_FRAUD', fraud.get('extension'), None, f"Hora: {fraud.get('time')}", destination=fraud.get('destination'))
                    
            db.commit()
        except Exception as db_err:
            logger.error(f"Error guardando alertas en BD: {str(db_err)}")
        finally:
            if 'db' in locals():
                db.close()
                
        if not compromised and not under_attack and not toll_fraud:
            logger.info("Escaneo PBX completado. No se detectaron brechas, ataques masivos ni fraude.")
            return
            
        logger.warning(f"¡Alerta! Brechas: {len(compromised)}, Bajo ataque: {len(under_attack)}, Fraude: {len(toll_fraud)}")
        
        # Construir cuerpo del correo
        html_body = "<h2>⚠️ Alerta de Seguridad PBX ⚠️</h2>"
        
        if compromised:
            html_body += "<h3 style='color: #dc2626;'>🚨 BRECHA DETECTADA (Secuestro Exitoso)</h3>"
            html_body += "<p>El sistema automático ha detectado inicios de sesión exitosos provenientes de direcciones IP maliciosas que previamente intentaron ataques de fuerza bruta.</p>"
            html_body += "<table border='1' cellpadding='10' style='border-collapse: collapse; text-align: left;'>"
            html_body += "<tr style='background-color: #f87171; color: white;'><th>Extensión</th><th>IP del Atacante</th><th>Fallos previos antes de entrar</th></tr>"
            
            for comp in compromised:
                html_body += f"<tr>"
                html_body += f"<td><b>{comp.get('extension')}</b></td>"
                html_body += f"<td>{comp.get('attacker_ip')}</td>"
                html_body += f"<td>{comp.get('failed_attempts_before_success')} intentos fallidos</td>"
                html_body += f"</tr>"
                
            html_body += "</table>"
            html_body += "<br><p>Por favor ingrese a la Plataforma IT, bloquee las IP y cambie la contraseña de las extensiones afectadas de inmediato.</p><hr>"
            
        if under_attack:
            html_body += "<h3 style='color: #ea580c;'>🛡️ FUERZA BRUTA DETECTADA (Sin Éxito Aún)</h3>"
            html_body += "<p>Se han detectado múltiples intentos fallidos de adivinar las contraseñas de las siguientes extensiones. Los atacantes aún no han logrado entrar, pero se recomienda bloquear sus IPs preventivamente en el Dashboard de la Plataforma IT.</p>"
            html_body += "<table border='1' cellpadding='10' style='border-collapse: collapse; text-align: left;'>"
            html_body += "<tr style='background-color: #fb923c; color: white;'><th>Extensión Objetivo</th><th>Intentos Fallidos Acumulados</th></tr>"
            
            for atk in under_attack:
                html_body += f"<tr>"
                html_body += f"<td><b>{atk.get('extension')}</b></td>"
                html_body += f"<td>{atk.get('failed_attempts')} intentos bloqueados</td>"
                html_body += f"</tr>"
                
            html_body += "</table><br>"
            
        if toll_fraud:
            html_body += "<h3 style='color: #9f1239;'>🚨 FRAUDE TELEFÓNICO DETECTADO (Toll Fraud)</h3>"
            html_body += "<p>Se han detectado llamadas sospechosas al extranjero (números que empiezan con 800/80 o >12 dígitos) en horario no hábil (9 PM - 7 AM). Posible inyección SIP o secuestro de PBX para generar llamadas de alto costo.</p>"
            html_body += "<table border='1' cellpadding='10' style='border-collapse: collapse; text-align: left;'>"
            html_body += "<tr style='background-color: #be123c; color: white;'><th>Extensión Origen</th><th>Destino (Sospechoso)</th><th>Hora de la Llamada</th></tr>"
            
            for fraud in toll_fraud:
                html_body += f"<tr>"
                html_body += f"<td><b>{fraud.get('extension')}</b></td>"
                html_body += f"<td>{fraud.get('destination')}</td>"
                html_body += f"<td>{fraud.get('time')}</td>"
                html_body += f"</tr>"
                
            html_body += "</table>"
            html_body += "<br><p>Por favor revise el Troncal SIP inmediatamente y bloquee la extensión en la PBX o en el portal de su proveedor (WolkVox/C&W) para detener el consumo facturado.</p><hr>"
        
        
        # Enviar correo usando Graph API
        graph_svc = MicrosoftGraphService()
        to_email = "fabian.paternina@hogarymoda.com.co"
        sender_upn = "testciber@hogarymoda.com.co"
        subject = "🚨 ALERTA DE SEGURIDAD: Monitoreo PBX Issabel"
        
        mail_result = await graph_svc.send_mail(sender_upn, to_email, subject, html_body)
        
        if mail_result.get("success"):
            logger.info("Correo de alerta PBX enviado exitosamente.")
        else:
            logger.error(f"Error al enviar el correo de alerta: {mail_result.get('error')}")

    except Exception as e:
        logger.error(f"Error crítico en check_pbx_and_alert: {str(e)}")
