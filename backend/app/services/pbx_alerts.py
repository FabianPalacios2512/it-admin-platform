import logging
import asyncio
from app.api.v1.pbx_recordings import run_vulnerability_scan
from app.services.graph_service import MicrosoftGraphService

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
        
        if not compromised and not under_attack:
            logger.info("Escaneo PBX completado. No se detectaron brechas ni ataques masivos.")
            return
            
        logger.warning(f"¡Alerta! Brechas: {len(compromised)}, Bajo ataque: {len(under_attack)}")
        
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
