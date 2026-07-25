import subprocess
import json

def get_critical_ad_events(limit: int = 50):
    """
    Obtiene eventos críticos de seguridad del Directorio Activo.
    Requiere que el servicio se ejecute con permisos para leer el Security Log (ej. Administrador).
    Eventos de interés:
    - 4724: Intento de reseteo de contraseña.
    - 4725: Cuenta deshabilitada.
    - 4738: Cuenta modificada (sirve para detectar cambios como "La contraseña nunca expira").
    - 4726: Cuenta eliminada.
    - 4728, 4732, 4756: Miembro añadido a un grupo global/local/universal con privilegios.
    """
    
    ps_script = f"""
    $eventIds = @(4724, 4725, 4738, 4726)
    
    try {{
        $events = Get-WinEvent -FilterHashtable @{{LogName='Security'; ID=$eventIds}} -MaxEvents {limit} -ErrorAction Stop
        
        $results = @()
        foreach ($event in $events) {{
            # Parsear propiedades del mensaje usando XML
            $xml = [xml]$event.ToXml()
            $eventData = $xml.Event.EventData.Data
            
            $targetUser = ($eventData | Where-Object {{ $_.Name -eq 'TargetUserName' }}).'#text'
            $subjectUser = ($eventData | Where-Object {{ $_.Name -eq 'SubjectUserName' }}).'#text'
            
            # En el evento 4738, UserAccountControl viejo y nuevo se muestran
            $uacOld = ($eventData | Where-Object {{ $_.Name -eq 'OldUacValue' }}).'#text'
            $uacNew = ($eventData | Where-Object {{ $_.Name -eq 'NewUacValue' }}).'#text'
            
            $action = "Desconocida"
            if ($event.Id -eq 4724) {{ $action = "Reseteo de Contraseña" }}
            if ($event.Id -eq 4725) {{ $action = "Cuenta Deshabilitada" }}
            if ($event.Id -eq 4726) {{ $action = "Cuenta Eliminada" }}
            if ($event.Id -eq 4738) {{ 
                $action = "Modificación de Atributos"
                if ($uacNew -match "0x10000" -and $uacOld -notmatch "0x10000") {{
                    $action = "Activado: La contraseña nunca expira"
                }} elseif ($uacNew -match "0x2" -and $uacOld -notmatch "0x2") {{
                    $action = "Cuenta Deshabilitada (UAC)"
                }}
            }}
            
            # Evitar logs del sistema (computadoras terminan con $)
            if ($subjectUser -notmatch '\$$') {{
                $results += @{{
                    EventID = $event.Id
                    TimeCreated = $event.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
                    Action = $action
                    TargetUser = $targetUser
                    AdminUser = $subjectUser
                    Message = $event.Message -replace "`r`n"," "
                }}
            }}
        }}
        $results | ConvertTo-Json -Compress -Depth 5
    }} catch {{
        Write-Output ( [PSCustomObject]@{{ error=$_.Exception.Message }} | ConvertTo-Json -Compress )
    }}
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True, timeout=60
    )
    
    if result.returncode != 0:
        raise ValueError(f"Error ejecutando Get-WinEvent: {result.stderr}")
        
    try:
        if not result.stdout.strip():
            return []
        data = json.loads(result.stdout.strip())
        if isinstance(data, dict) and "error" in data:
            # Podría ser que no haya permisos
            raise ValueError(f"Error de PowerShell: {data['error']}")
        
        # PowerShell puede devolver un solo objeto si hay 1 evento
        if isinstance(data, dict) and "EventID" in data:
            return [data]
            
        return data
    except json.JSONDecodeError:
        raise ValueError(f"Error decodificando salida: {result.stdout}")
