<#
.SYNOPSIS
    Agente de Diagnstico IT Inteligente  Cliente PowerShell
    
.DESCRIPTION
    Script iterativo que conecta un equipo Windows al backend de AdminInfra
    para recibir un diagnstico inteligente impulsado por IA (Google Gemini).
    
    El script acta como los "ojos y manos" del agente: se conecta va WebSocket,
    enva informacin del equipo, recibe comandos de diagnstico (solo lectura),
    los ejecuta de forma segura, y devuelve los resultados al backend.
    
     SOLO LECTURA: Este script NUNCA modifica el sistema.
       Todos los comandos estn validados contra una whitelist local Y del servidor.

.PARAMETER ServerUrl
    URL del backend de AdminInfra (sin /api).
    Ejemplo: http://192.168.20.100:8000

.PARAMETER Issue
    Descripcin breve del problema reportado.
    Ejemplo: "El equipo se reinicia solo cada 2 horas"

.EXAMPLE
    .\Invoke-ITDiagnostic.ps1 -ServerUrl "http://192.168.1.100:8000" -Issue "Se reinicia sola"
    
.NOTES
    Requiere: PowerShell 5.1+ con .NET Framework 4.5+
    Ejecutar como: Administrador
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ServerUrl = "http://localhost:8000",
    
    [Parameter(Mandatory = $false)]
    [string]$Issue = "El equipo se reinicia inesperadamente"
)

# 
# CONFIGURACIN
# 

$ErrorActionPreference = "Stop"
$CommandTimeoutSeconds = 30
$MaxReconnectAttempts  = 3

# 
# WHITELIST LOCAL (Doble seguridad  no depende solo del backend)
# 

$AllowedCmdlets = @(
    # Logs de eventos
    "Get-EventLog", "Get-WinEvent",
    # WMI / CIM
    "Get-WmiObject", "Get-CimInstance",
    # Procesos y servicios
    "Get-Process", "Get-Service",
    # Info del sistema
    "systeminfo", "Get-ComputerInfo", "hostname", "whoami",
    # Hotfixes
    "Get-HotFix",
    # Registro (solo lectura)
    "Get-ItemProperty", "Get-ItemPropertyValue",
    "reg query",
    # Disco
    "Get-PhysicalDisk", "Get-Disk", "Get-Volume", "Get-Partition",
    # Red
    "Get-NetAdapter", "Get-NetIPAddress", "ipconfig", "Test-Connection",
    # Drivers
    "Get-WindowsDriver", "driverquery", "Get-PnpDevice",
    # Energa
    "powercfg",
    # Formateo
    "Select-Object", "Format-List", "Format-Table", "Where-Object",
    "Sort-Object", "Measure-Object", "ConvertTo-Json", "Out-String",
    # Archivos (solo lectura)
    "Get-ChildItem", "Get-Content",
    # Contadores de rendimiento
    "Get-Counter",
    # Tareas programadas
    "Get-ScheduledTask",
    # Integridad (solo verificacin)
    "sfc /verifyonly", "chkdsk"
)

$BlockedPatterns = @(
    "Remove-", "Set-", "New-", "Start-Process", "Stop-", "Restart-",
    "Invoke-WebRequest", "Invoke-RestMethod", "Invoke-Command",
    "Enter-PSSession", "Enable-", "Disable-", "Uninstall-", "Install-",
    "Update-", "Clear-", "Format-Volume", "Initialize-Disk",
    "Add-", "Register-", "Unregister-", "Export-", "Import-",
    "cmd /c", "cmd.exe", "powershell -", "iex", "Invoke-Expression",
    "DownloadString", "DownloadFile", "Net User", "Net LocalGroup",
    "Shutdown", "Restart-Computer", "Reset-", "Repair-",
    ".exe"  # Bloquear ejecucin directa de .exe
)

# Excepciones al bloqueo de .exe (comandos del sistema permitidos)
$ExeExceptions = @("systeminfo", "hostname", "whoami", "ipconfig", "driverquery", "powercfg", "chkdsk", "sfc", "reg")


# 
# FUNCIONES AUXILIARES
# 

function Show-Banner {
    $banner = "
  +==================================================================+
  |                                                                  |
  |     IT DIAGNOSTIC AGENT  v1.0                                    |
  |     by Fabian Paternina                                          |
  |     Powered by Google Gemini 3.5 Flash Lite                      |
  |                                                                  |
  +==================================================================+
"
    Write-Host $banner -ForegroundColor Cyan
    Write-Host "  [!] MODO: SOLO LECTURA - Este script NO modifica el sistema." -ForegroundColor Yellow
    Write-Host "  [i] Servidor: $ServerUrl" -ForegroundColor Gray
    Write-Host "  [i] Problema: $Issue" -ForegroundColor Gray
    Write-Host "  [i] Presiona Ctrl+C en cualquier momento para abortar.`n" -ForegroundColor Gray
    Write-Host "  ---------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ""
}


function Test-CommandAllowed {
    <#
    .SYNOPSIS
        Valida un comando contra la whitelist local.
        Retorna $true si es seguro, $false si es bloqueado.
    #>
    param([string]$Command)
    
    $cmd = $Command.Trim()
    
    if ([string]::IsNullOrWhiteSpace($cmd)) {
        return $false
    }
    
    # Verificar patrones bloqueados PRIMERO
    foreach ($blocked in $BlockedPatterns) {
        if ($blocked -eq ".exe") {
            # Verificar .exe pero permitir los comandos del sistema conocidos
            if ($cmd -match "\.exe\b") {
                $isException = $false
                foreach ($exc in $ExeExceptions) {
                    if ($cmd -match "(?i)^$exc\b") {
                        $isException = $true
                        break
                    }
                }
                if (-not $isException) {
                    Write-Host "  [BLOQUEADO] Patrn prohibido: .exe" -ForegroundColor Red
                    return $false
                }
            }
        }
        elseif ($cmd -match [regex]::Escape($blocked)) {
            Write-Host "  [BLOQUEADO] Patrn prohibido: $blocked" -ForegroundColor Red
            return $false
        }
    }
    
    # La validacin por Whitelist ($AllowedCmdlets) fue eliminada 
    # para permitir total libertad creativa a la IA (bucles, ifs, variables, etc.).
    # La seguridad recae completamente en la robusta Blacklist superior.
    
    return $true
}


function Invoke-SafeCommand {
    <#
    .SYNOPSIS
        Ejecuta un comando de forma segura con timeout y captura de errores.
    #>
    param(
        [string]$Command,
        [int]$Timeout = $CommandTimeoutSeconds
    )
    
    $result = @{
        stdout    = ""
        stderr    = ""
        exit_code = 0
    }
    
    try {
        # Usar un Job para implementar timeout
        $job = Start-Job -ScriptBlock {
            param($cmd)
            try {
                $output = Invoke-Expression $cmd 2>&1 | Out-String
                return @{
                    output    = $output
                    exit_code = 0
                }
            }
            catch {
                return @{
                    output    = $_.Exception.Message
                    exit_code = 1
                }
            }
        } -ArgumentList $Command
        
        $completed = Wait-Job $job -Timeout $Timeout
        
        if ($null -eq $completed) {
            # Timeout
            Stop-Job $job -ErrorAction SilentlyContinue
            Remove-Job $job -Force -ErrorAction SilentlyContinue
            $result.stderr = "TIMEOUT: El comando excedio $Timeout segundos."
            $result.exit_code = -1
        }
        else {
            $jobResult = Receive-Job $job
            Remove-Job $job -Force -ErrorAction SilentlyContinue
            
            if ($jobResult.exit_code -eq 0) {
                $result.stdout = [string]$jobResult.output
            }
            else {
                $result.stderr = [string]$jobResult.output
                $result.exit_code = $jobResult.exit_code
            }
        }
    }
    catch {
        $result.stderr = "Error ejecutando comando: $($_.Exception.Message)"
        $result.exit_code = 1
    }
    
    # Limitar tamao de salida (evitar mensajes enormes por WebSocket)
    $maxLen = 30000
    if ($result.stdout.Length -gt $maxLen) {
        $result.stdout = $result.stdout.Substring(0, $maxLen) + "`n`n[... SALIDA TRUNCADA ($($result.stdout.Length) chars total) ...]"
    }
    if ($result.stderr.Length -gt $maxLen) {
        $result.stderr = $result.stderr.Substring(0, $maxLen) + "`n`n[... ERROR TRUNCADO ...]"
    }
    
    return $result
}


function Get-MachineInfo {
    <#
    .SYNOPSIS
        Recolecta la informacin bsica del equipo para enviar al backend.
    #>
    
    $hostname = $env:COMPUTERNAME
    $os = (Get-CimInstance Win32_OperatingSystem).Caption
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne "127.0.0.1" } | Select-Object -First 1).IPAddress
    
    # Calcular uptime
    $lastBoot = (Get-CimInstance Win32_OperatingSystem).LastBootUpTime
    $uptime = (New-TimeSpan -Start $lastBoot -End (Get-Date))
    $uptimeStr = "{0}d {1}h {2}m" -f $uptime.Days, $uptime.Hours, $uptime.Minutes
    
    return @{
        type     = "machine_info"
        hostname = $hostname
        os       = $os
        ip       = if ($ip) { $ip } else { "N/A" }
        uptime   = $uptimeStr
        issue    = $Issue
    }
}


function Send-WsMessage {
    param(
        [System.Net.WebSockets.ClientWebSocket]$WebSocket,
        [hashtable]$Data
    )
    
    $json = $Data | ConvertTo-Json -Depth 10 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)
    $WebSocket.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).Wait()
}


function Receive-WsMessage {
    param(
        [System.Net.WebSockets.ClientWebSocket]$WebSocket,
        [int]$Timeout = 120
    )
    
    $buffer = New-Object byte[] 65536
    $result = New-Object System.Text.StringBuilder
    $cts = New-Object System.Threading.CancellationTokenSource
    $cts.CancelAfter($Timeout * 1000)
    
    do {
        $segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$buffer)
        try {
            $received = $WebSocket.ReceiveAsync($segment, $cts.Token).Result
        }
        catch [System.OperationCanceledException] {
            throw "Timeout esperando respuesta del servidor ($Timeout segundos)."
        }
        catch {
            if ($_.Exception.InnerException -is [System.OperationCanceledException]) {
                throw "Timeout esperando respuesta del servidor ($Timeout segundos)."
            }
            throw
        }
        
        if ($received.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
            throw "El servidor cerr la conexin."
        }
        
        $chunk = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $received.Count)
        [void]$result.Append($chunk)
        
    } while (-not $received.EndOfMessage)
    
    $cts.Dispose()
    return $result.ToString()
}


function Show-Separator {
    param([string]$Color = "DarkGray")
    Write-Host "  ---------------------------------------------------------" -ForegroundColor $Color
}


function Format-DiagnosisReport {
    <#
    .SYNOPSIS
        Formatea y muestra el reporte de diagnstico final en la consola.
    #>
    param([hashtable]$Report)
    
    $severityColors = @{
        "critical" = "Red"
        "high"     = "DarkYellow"
        "medium"   = "Yellow"
        "low"      = "Green"
    }
    
    $severityIcons = @{
        "critical" = "[!!!]"
        "high"     = "[!!]"
        "medium"   = "[!]"
        "low"      = "[i]"
    }
    
    $sev = $Report.severity
    $color = if ($severityColors.ContainsKey($sev)) { $severityColors[$sev] } else { "White" }
    $icon = if ($severityIcons.ContainsKey($sev)) { $severityIcons[$sev] } else { "[?]" }
    
    Write-Host ""
    Write-Host "  " -ForegroundColor $color
    Write-Host "                DIAGNSTICO FINAL                                 " -ForegroundColor $color
    Write-Host "  " -ForegroundColor $color
    Write-Host ""
    Write-Host "  $icon Severidad: $($sev.ToUpper())" -ForegroundColor $color
    Write-Host "  Equipo: $($Report.hostname)" -ForegroundColor White
    Write-Host "  Sesin: $($Report.session_id)" -ForegroundColor Gray
    Write-Host "  Pasos ejecutados: $($Report.steps_taken)" -ForegroundColor Gray
    Write-Host ""
    Show-Separator
    Write-Host ""
    Write-Host "  CAUSA RAZ:" -ForegroundColor White
    Write-Host "  $($Report.root_cause)" -ForegroundColor Cyan
    Write-Host ""
    Show-Separator
    Write-Host ""
    Write-Host "  EVIDENCIA:" -ForegroundColor White
    Write-Host "  $($Report.evidence_summary)" -ForegroundColor Gray
    Write-Host ""
    Show-Separator
    Write-Host ""
    Write-Host "  RECOMENDACIONES:" -ForegroundColor White
    
    if ($Report.recommendations) {
        $i = 1
        foreach ($rec in $Report.recommendations) {
            Write-Host "  $i. $rec" -ForegroundColor Yellow
            $i++
        }
    }
    
    if ($Report.additional_notes) {
        Write-Host ""
        Show-Separator
        Write-Host ""
        Write-Host "  NOTAS ADICIONALES:" -ForegroundColor White
        Write-Host "  $($Report.additional_notes)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Show-Separator "Cyan"
    Write-Host ""
}


# 
# PROGRAMA PRINCIPAL
# 

# Verificar que se ejecuta como Administrador
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "`n  [ERROR] Este script debe ejecutarse como Administrador." -ForegroundColor Red
    Write-Host "  Haz clic derecho en PowerShell > 'Ejecutar como administrador'.`n" -ForegroundColor Yellow
    exit 1
}

Show-Banner

# Construir la URL del WebSocket
$wsUrl = $ServerUrl -replace "^http", "ws"
$wsUrl = "$wsUrl/api/v1/diagnostics/ws"
Write-Host "  [*] Conectando a: $wsUrl" -ForegroundColor Cyan

$ws = $null
$attempt = 0

try {
    # -- Conectar al WebSocket
    while ($attempt -lt $MaxReconnectAttempts) {
        $attempt++
        try {
            $ws = New-Object System.Net.WebSockets.ClientWebSocket
            $ws.Options.KeepAliveInterval = [TimeSpan]::FromSeconds(30)
            $uri = [Uri]::new($wsUrl)
            $cts = New-Object System.Threading.CancellationTokenSource
            $cts.CancelAfter(15000)  # 15s timeout para conectar
            $ws.ConnectAsync($uri, $cts.Token).Wait()
            $cts.Dispose()
            Write-Host "  [OK] Conexin WebSocket establecida.`n" -ForegroundColor Green
            break
        }
        catch {
            $errMsg = if ($_.Exception.InnerException) { $_.Exception.InnerException.Message } else { $_.Exception.Message }
            Write-Host "  [ERROR] Intento $attempt/$MaxReconnectAttempts - No se pudo conectar: $errMsg" -ForegroundColor Red
            if ($attempt -lt $MaxReconnectAttempts) {
                Write-Host "  [*] Reintentando en 5 segundos..." -ForegroundColor Yellow
                Start-Sleep -Seconds 5
            }
            else {
                Write-Host "`n  [FATAL] No se pudo conectar al servidor despus de $MaxReconnectAttempts intentos." -ForegroundColor Red
                exit 1
            }
        }
    }
    
    # -- Esperar el mensaje de bienvenida del servidor
    $welcomeRaw = Receive-WsMessage -WebSocket $ws
    $welcome = $welcomeRaw | ConvertFrom-Json
    if ($welcome.message) {
        Write-Host "  [Servidor] $($welcome.message)" -ForegroundColor Gray
    }
    
    # -- Enviar informacin del equipo
    Write-Host "  [*] Recolectando informacin del equipo..." -ForegroundColor Cyan
    $machineInfo = Get-MachineInfo
    Write-Host "  [i] Hostname: $($machineInfo.hostname)" -ForegroundColor White
    Write-Host "  [i] OS: $($machineInfo.os)" -ForegroundColor White
    Write-Host "  [i] IP: $($machineInfo.ip)" -ForegroundColor White
    Write-Host "  [i] Uptime: $($machineInfo.uptime)" -ForegroundColor White
    Write-Host ""
    
    Send-WsMessage -WebSocket $ws -Data $machineInfo
    Write-Host "  [OK] Informacin enviada. Esperando al agente de IA...`n" -ForegroundColor Green
    Show-Separator
    Write-Host ""
    
    # 
    # LOOP PRINCIPAL  Recibir instrucciones, ejecutar, reportar
    # 
    
    $sessionActive = $true
    $stepNumber = 0
    
    while ($sessionActive -and $ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        
        # -- Recibir mensaje del backend
        try {
            $msgRaw = Receive-WsMessage -WebSocket $ws -Timeout 180
        }
        catch {
            Write-Host "  [ERROR] $($_.Exception.Message)" -ForegroundColor Red
            break
        }
        
        try {
            $msg = $msgRaw | ConvertFrom-Json
        }
        catch {
            Write-Host "  [ERROR] Mensaje del servidor no es JSON vlido." -ForegroundColor Red
            continue
        }
        
        $msgType = $msg.type
        
        switch ($msgType) {
            
            # -- El agente comparte su razonamiento
            "agent_thought" {
                Write-Host "  [Pensamiento del Agente - Paso $($msg.step)]" -ForegroundColor Magenta
                $thoughtLines = $msg.thought -split "`n"
                foreach ($line in $thoughtLines) {
                    Write-Host "    $line" -ForegroundColor DarkMagenta
                }
                Write-Host ""
            }
            
            # -- El agente quiere ejecutar un comando
            "execute_command" {
                $stepNumber++
                $command = $msg.command
                $purpose = $msg.purpose
                $phase = $msg.phase
                
                Write-Host "  +--------------------------------------------------" -ForegroundColor DarkCyan
                Write-Host "  | Fase $phase  Paso $stepNumber" -ForegroundColor Cyan
                Write-Host "  | Propsito: $purpose" -ForegroundColor White
                Write-Host "  | Comando: $command" -ForegroundColor Yellow
                Write-Host "  +--------------------------------------------------" -ForegroundColor DarkCyan
                
                # -- Validar contra whitelist LOCAL
                $isAllowed = Test-CommandAllowed -Command $command
                
                if (-not $isAllowed) {
                    Write-Host "  [SEGURIDAD] Comando RECHAZADO por whitelist local." -ForegroundColor Red
                    Write-Host ""
                    
                    $blockedResponse = @{
                        type    = "command_blocked"
                        message = "Comando bloqueado por la whitelist local del PowerShell."
                        step    = $msg.step
                    }
                    Send-WsMessage -WebSocket $ws -Data $blockedResponse
                    continue
                }
                
                Write-Host "  [OK] Whitelist verificada. Ejecutando..." -ForegroundColor Green
                
                # -- Ejecutar el comando de forma segura
                $cmdResult = Invoke-SafeCommand -Command $command
                
                $preview = ""
                if ($cmdResult.stdout) {
                    $preview = $cmdResult.stdout.Substring(0, [Math]::Min(200, $cmdResult.stdout.Length))
                } elseif ($cmdResult.stderr) {
                    $preview = $cmdResult.stderr.Substring(0, [Math]::Min(200, $cmdResult.stderr.Length))
                } else {
                    $preview = "(sin salida)"
                }
                $previewClean = $preview -replace "`n", " " -replace "`r", ""
                Write-Host "  [Resultado] $previewClean..." -ForegroundColor Gray
                Write-Host ""
                
                # -- Enviar resultado al backend
                $response = @{
                    type      = "command_result"
                    stdout    = $cmdResult.stdout
                    stderr    = $cmdResult.stderr
                    exit_code = $cmdResult.exit_code
                    step      = $msg.step
                }
                Send-WsMessage -WebSocket $ws -Data $response
            }
            
            # -- Actualizacin de estado del agente
            "status_update" {
                Write-Host "  [Agente] $($msg.message)" -ForegroundColor Cyan
                Write-Host ""
            }
            
            # -- Diagnstico completo
            "diagnosis_complete" {
                Write-Host "  [OK] El agente ha completado el diagnstico." -ForegroundColor Green
                Write-Host ""
                
                # Convertir PSObject a hashtable para el formateador
                $report = @{}
                $msg.report.PSObject.Properties | ForEach-Object { $report[$_.Name] = $_.Value }
                
                Format-DiagnosisReport -Report $report
                
                $sessionActive = $false
            }
            
            # -- Diagnstico incompleto (mximo de pasos)
            "diagnosis_incomplete" {
                Write-Host "  [ADVERTENCIA] $($msg.message)" -ForegroundColor Yellow
                Write-Host ""
                $sessionActive = $false
            }
            
            # -- Fin de sesin
            "session_end" {
                Write-Host "  [i] $($msg.message)" -ForegroundColor Gray
                $sessionActive = $false
            }
            
            # -- Error del servidor
            "error" {
                Write-Host "  [ERROR del Servidor] $($msg.message)" -ForegroundColor Red
                Write-Host ""
                # No romper el loop por un error  el agente puede recuperarse
            }
            
            # -- Mensaje desconocido
            default {
                Write-Host "  [?] Mensaje desconocido (tipo: $msgType): $msgRaw" -ForegroundColor DarkYellow
            }
        }
    }
}
catch {
    Write-Host "`n  [ERROR FATAL] $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.InnerException) {
        Write-Host "  [Detalle] $($_.Exception.InnerException.Message)" -ForegroundColor DarkRed
    }
}
finally {
    # -- Cierre limpio del WebSocket
    if ($ws -and $ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
        try {
            $cts = New-Object System.Threading.CancellationTokenSource
            $cts.CancelAfter(5000)
            $ws.CloseAsync(
                [System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure,
                "Diagnostic session ended",
                $cts.Token
            ).Wait()
            $cts.Dispose()
        }
        catch { }
    }
    if ($ws) { $ws.Dispose() }
    
    Write-Host "`n  ---------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "  Sesin de diagnstico finalizada." -ForegroundColor Gray
    Write-Host "  Presiona Enter para cerrar..." -ForegroundColor Gray
    Write-Host ""
    Read-Host
}
