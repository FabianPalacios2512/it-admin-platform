import asyncio
import subprocess
import json
from datetime import datetime, timezone, timedelta
from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.models.delegation import TemporaryDelegation

def log_audit(username: str, action: str, target: str, status: str, source: str = "DelegationHub"):
    """Registra una acción en la auditoría."""
    db = SessionLocal()
    try:
        log_entry = AuditLog(
            username=username,
            action=action,
            target=target,
            status=status,
            source=source
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
    finally:
        db.close()

async def execute_powershell(command: str) -> str:
    """Ejecuta un comando en PowerShell y retorna el resultado."""
    from app.services.graph_service import check_exchange_setup
    from app.core.config import env_settings
    
    setup_status = await check_exchange_setup()
    thumbprint = setup_status.get("thumbprint")
    connect_cmd = ""
    if thumbprint:
        client_id = env_settings.ENTRA_CLIENT_ID
        tenant_domain = "105code.cloud"
        connect_cmd = f'Connect-ExchangeOnline -CertificateThumbprint "{thumbprint}" -AppId "{client_id}" -Organization "{tenant_domain}" -ShowProgress $false -ErrorAction Stop'

    # Envolver en un try/catch de PowerShell para capturar errores como JSON
    ps_command = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        {connect_cmd}
        {command}
        Write-Output '{{"success": true}}'
    }} catch {{
        $err = $_.Exception.Message
        Write-Output "{{\\"error\\": \\"$err\\"}}"
    }}
    """
    
    import tempfile
    import os
    fd, ps_file_path = tempfile.mkstemp(suffix=".ps1")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(ps_command)
        
    try:
        def run_ps():
            import subprocess
            return subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file_path],
                capture_output=True,
                text=True
            )
        process = await asyncio.to_thread(run_ps)
        stdout, stderr = process.stdout, process.stderr
    finally:
        if os.path.exists(ps_file_path):
            try:
                os.remove(ps_file_path)
            except:
                pass
                
    if stderr:
        print(f"[PowerShell Error] {stderr.strip()}")
        
    out_text = stdout.strip()
    return out_text

async def grant_mailbox_permission(source_upn: str, target_upn: str, permission: str) -> bool:
    """Otorga permisos usando el módulo de Exchange (elevado)."""
    if permission == "FullAccess":
        cmd = f"Add-MailboxPermission -Identity '{source_upn}' -User '{target_upn}' -AccessRights FullAccess -InheritanceType All -AutoMapping $true"
    elif permission == "SendAs":
        cmd = f"Add-RecipientPermission -Identity '{source_upn}' -Trustee '{target_upn}' -AccessRights SendAs -Confirm:$false"
    else:
        return False # SendOnBehalf etc puede requerir Set-Mailbox
        
    result = await execute_powershell(f"import-module ExchangeOnlineManagement; {cmd}")
    
    # Evaluar si hubo error
    if "error" in result.lower() and "success" not in result.lower():
        # A veces el usuario ya tiene el permiso y tira error. O falló de verdad.
        print(f"Grant Permission Result: {result}")
        if "already exists" in result.lower() or "ya existe" in result.lower():
            return True
        return False
        
    return True

async def revoke_mailbox_permission(source_upn: str, target_upn: str, permission: str) -> bool:
    """Revoca permisos usando el módulo de Exchange."""
    if permission == "FullAccess":
        cmd = f"Remove-MailboxPermission -Identity '{source_upn}' -User '{target_upn}' -AccessRights FullAccess -InheritanceType All -Confirm:$false"
    elif permission == "SendAs":
        cmd = f"Remove-RecipientPermission -Identity '{source_upn}' -Trustee '{target_upn}' -AccessRights SendAs -Confirm:$false"
    else:
        return False
        
    result = await execute_powershell(f"import-module ExchangeOnlineManagement; {cmd}")
    if "error" in result.lower() and "success" not in result.lower():
        print(f"Revoke Permission Result: {result}")
        return False
    return True

async def sanitize_mailbox(source_upn: str, convert_shared: bool, hide_gal: bool):
    """
    Convierte a compartido y oculta de la GAL (vía PowerShell).
    """
    cmds = []
    if convert_shared:
        cmds.append(f"Set-Mailbox -Identity '{source_upn}' -Type Shared")
    if hide_gal:
        cmds.append(f"Set-Mailbox -Identity '{source_upn}' -HiddenFromAddressListsEnabled $true")
        
    if cmds:
        full_cmd = "; ".join(cmds)
        result = await execute_powershell(full_cmd)
        
        # Check for specific known AD Connect / DirSync error
        if "sincronizando desde su organizaci" in result.lower() or "synchronized from your on-premises" in result.lower():
            raise Exception("No se puede Ocultar de la GAL (Libreta de Direcciones) porque el usuario se sincroniza desde el Active Directory local (AD Connect). Desmarca la opción 'Ocultar de la GAL' e inténtalo de nuevo. Deberás ocultarlo desde el servidor AD local.")
            
        if "error" in result.lower() and "success" not in result.lower():
            # If the only error is that it's already shared, ignore it
            if "ya es del tipo" in result.lower() or "already of type" in result.lower():
                pass # It's just a warning
            else:
                raise Exception(f"Fallo en Exchange: {result}")

async def get_shared_mailboxes() -> list:
    """
    Obtiene todos los buzones compartidos y sus delegados.
    """
    cmd = """
    $mailboxes = Get-Mailbox -RecipientTypeDetails SharedMailbox -ResultSize 50
    $results = @()
    foreach ($mbx in $mailboxes) {
        $perms = Get-MailboxPermission -Identity $mbx.UserPrincipalName | Where-Object {($_.User -notlike "NT AUTHORITY\\*") -and ($_.IsInherited -eq $false)}
        $delegates = $perms | Select-Object -ExpandProperty User
        $delegatesStr = ""
        if ($delegates) {
            if ($delegates -is [array]) {
                $delegatesStr = $delegates -join ", "
            } else {
                $delegatesStr = $delegates
            }
        }
        $results += [PSCustomObject]@{
            Mailbox = $mbx.UserPrincipalName
            DisplayName = $mbx.DisplayName
            Delegates = $delegatesStr
        }
    }
    $results | ConvertTo-Json
    """
    result = await execute_powershell(f"import-module ExchangeOnlineManagement; {cmd}")
    if "error" in result.lower() and "success" not in result.lower():
        print(f"Error en get_shared_mailboxes: {result}")
        return []
        
    try:
        clean_result = result.replace('{"success": true}', '').strip()
        start_idx = -1
        for i, char in enumerate(clean_result):
            if char in ['{', '[']:
                start_idx = i
                break
        if start_idx != -1:
            json_str = clean_result[start_idx:]
            data = json.loads(json_str)
            if isinstance(data, dict) and "error" not in data:
                return [data]
            if isinstance(data, dict) and "error" in data:
                return []
            return data
        return []
    except Exception as e:
        print(f"Error parsing json in get_shared_mailboxes: {e}")
        return []

def revoke_expired_delegations():
    """Tarea programada (CRON) para revocar permisos temporales."""
    print(f"[{datetime.now()}] Iniciando barrido de delegaciones expiradas...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Buscar expiradas y activas
        expired = db.query(TemporaryDelegation).filter(
            TemporaryDelegation.expiration_date <= now,
            TemporaryDelegation.status == "Active"
        ).all()
        
        for reg in expired:
            try:
                # El loop de asyncio puede no estar en el mismo hilo, usamos run_coroutine_threadsafe o creamos un loop temporal si estamos en un thread síncrono.
                # APScheduler ejecuta en un thread normal.
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    revoke_mailbox_permission(reg.source_upn, reg.target_upn, reg.permission_type)
                )
                loop.close()
                
                if success:
                    reg.status = "Revoked"
                    log_audit("SYSTEM_CRON", f"Revocación Automática {reg.permission_type}", f"{reg.target_upn} -> {reg.source_upn}", "Éxito")
                else:
                    reg.status = "Failed"
                    log_audit("SYSTEM_CRON", f"Fallo Revocación {reg.permission_type}", f"{reg.target_upn} -> {reg.source_upn}", "Error")
            except Exception as ex:
                print(f"Error revoking {reg.id}: {ex}")
                reg.status = "Failed"
                log_audit("SYSTEM_CRON", f"Excepción Revocación {reg.permission_type}", f"{reg.target_upn} -> {reg.source_upn}", "Error")
        
        db.commit()
    except Exception as e:
        print(f"Error en revoke_expired_delegations: {e}")
    finally:
        db.close()
