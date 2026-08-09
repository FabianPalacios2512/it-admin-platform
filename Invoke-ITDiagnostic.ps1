<#
.SYNOPSIS
    Agente de Diagnostico IT Inteligente - Cliente PowerShell
.DESCRIPTION
    Script que conecta un equipo Windows al backend de AdminInfra via WebSocket
    para recibir un diagnostico inteligente impulsado por Google Gemini AI.
    SOLO LECTURA: este script NUNCA modifica el sistema.
.PARAMETER ServerUrl
    URL del backend. Ej: http://192.168.20.100:8000
.PARAMETER Issue
    Descripcion del problema. Ej: El equipo se reinicia solo
.NOTES
    Requiere PowerShell 5.1+ | Ejecutar como Administrador
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ServerUrl = "http://localhost:8000",
    [Parameter(Mandatory = $false)]
    [string]$Issue = "El equipo se reinicia inesperadamente"
)

# UTF-8 FIX - ANTES de cualquier Write-Host
$null = chcp 65001 2>$null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$ErrorActionPreference = "Stop"
$CommandTimeoutSeconds = 30
$MaxReconnectAttempts = 3

$AllowedCmdlets = @(
    "Get-EventLog", "Get-WinEvent", "Get-WmiObject", "Get-CimInstance",
    "Get-Process", "Get-Service", "systeminfo", "Get-ComputerInfo", "hostname", "whoami",
    "Get-HotFix", "Get-ItemProperty", "Get-ItemPropertyValue", "reg query",
    "Get-PhysicalDisk", "Get-Disk", "Get-Volume", "Get-Partition",
    "Get-NetAdapter", "Get-NetIPAddress", "ipconfig", "Test-Connection",
    "Get-WindowsDriver", "driverquery", "Get-PnpDevice", "powercfg",
    "Select-Object", "Format-List", "Format-Table", "Where-Object",
    "Sort-Object", "Measure-Object", "ConvertTo-Json", "Out-String",
    "Get-ChildItem", "Get-Content", "Get-Counter", "Get-ScheduledTask",
    "sfc /verifyonly", "chkdsk", "Get-NetTCPConnection", "Get-NetRoute",
    "netstat", "Resolve-DnsName", "Test-NetConnection", "Get-DnsClientCache"
)

$BlockedPatterns = @(
    "Remove-", "Set-", "New-", "Start-Process", "Stop-", "Restart-",
    "Invoke-WebRequest", "Invoke-RestMethod", "Invoke-Command",
    "Enter-PSSession", "Enable-", "Disable-", "Uninstall-", "Install-",
    "Update-", "Clear-", "Format-Volume", "Initialize-Disk",
    "Add-", "Register-", "Unregister-", "Export-", "Import-",
    "cmd /c", "cmd.exe", "powershell -", "iex", "Invoke-Expression",
    "DownloadString", "DownloadFile", "Net User", "Net LocalGroup",
    "Shutdown", "Restart-Computer", "Reset-", "Repair-", ".exe"
)

$ExeExceptions = @("systeminfo", "hostname", "whoami", "ipconfig", "driverquery", "powercfg", "chkdsk", "sfc", "reg", "netstat")

function Show-Banner {
    param([string]$ServerUrl, [string]$Issue, [hashtable]$SysInfo)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # PALETA DE COLORES - Sistema Cyber-Corp
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    $clrPrimary   = "Cyan"
    $clrAccent    = "Green"
    $clrAlert     = "Yellow"
    $clrText      = "White"
    $clrSecondary = "Gray"
    $clrDim       = "DarkGray"

    Clear-Host

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # BANNERS ROTATIVOS - Arte ASCII Cyber-Corp (3 disenos)
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

        $b1_b64 = 'CgogIOKWiOKWiOKWiOKWiOKWiOKWiOKVlyDilojilojilZcg4paI4paI4paI4paI4paI4pWXICDilojilojilojilojilojilojilZcg4paI4paI4paI4pWXICAg4paI4paI4pWXIOKWiOKWiOKWiOKWiOKWiOKWiOKVlyDilojilojilojilojilojilojilojilZfilojilojilojilojilojilojilojilojilZfilojilojilZcg4paI4paI4paI4paI4paI4paI4pWXCiAg4paI4paI4pWU4pWQ4pWQ4paI4paI4pWX4paI4paI4pWR4paI4paI4pWU4pWQ4pWQ4paI4paI4pWX4paI4paI4pWU4pWQ4pWQ4pWQ4pWQ4pWdIOKWiOKWiOKWiOKWiOKVlyAg4paI4paI4pWR4paI4paI4pWU4pWQ4pWQ4pWQ4paI4paI4pWX4paI4paI4pWU4pWQ4pWQ4pWQ4pWQ4pWd4pWa4pWQ4pWQ4paI4paI4pWU4pWQ4pWQ4pWd4paI4paI4pWR4paI4paI4pWU4pWQ4pWQ4pWQ4pWQ4pWdCiAg4paI4paI4pWRICDilojilojilZHilojilojilZHilojilojilojilojilojilojilojilZHilojilojilZEgIOKWiOKWiOKWiOKVl+KWiOKWiOKVlOKWiOKWiOKVlyDilojilojilZHilojilojilZEgICDilojilojilZHilojilojilojilojilojilojilojilZcgICDilojilojilZEgICDilojilojilZHilojilojilZEKICDilojilojilZEgIOKWiOKWiOKVkeKWiOKWiOKVkeKWiOKWiOKVlOKVkOKVkOKWiOKWiOKVkeKWiOKWiOKVkSAgIOKWiOKWiOKVkeKWiOKWiOKVkeKVmuKWiOKWiOKVl+KWiOKWiOKVkeKWiOKWiOKVkSAgIOKWiOKWiOKVkeKVmuKVkOKVkOKVkOKVkOKWiOKWiOKVkSAgIOKWiOKWiOKVkSAgIOKWiOKWiOKVkeKWiOKWiOKVkQogIOKWiOKWiOKWiOKWiOKWiOKWiOKVlOKVneKWiOKWiOKVkeKWiOKWiOKVkSAg4paI4paI4pWR4pWa4paI4paI4paI4paI4paI4paI4pWU4pWd4paI4paI4pWRIOKVmuKWiOKWiOKWiOKWiOKVkeKVmuKWiOKWiOKWiOKWiOKWiOKWiOKVlOKVneKWiOKWiOKWiOKWiOKWiOKWiOKWiOKVkSAgIOKWiOKWiOKVkSAgIOKWiOKWiOKVkeKVmuKWiOKWiOKWiOKWiOKWiOKWiOKVlwogIOKVmuKVkOKVkOKVkOKVkOKVkOKVnSDilZrilZDilZ3ilZrilZDilZ0gIOKVmuKVkOKVnSDilZrilZDilZDilZDilZDilZDilZ0g4pWa4pWQ4pWdICDilZrilZDilZDilZDilZ0g4pWa4pWQ4pWQ4pWQ4pWQ4pWQ4pWdIOKVmuKVkOKVkOKVkOKVkOKVkOKVkOKVnSAgIOKVmuKVkOKVnSAgIOKVmuKVkOKVnSDilZrilZDilZDilZDilZDilZDilZ0KCiAgICAgICAgICAgICAgICAgICAgICBbIFpFUk8gVFJVU1QgRElBR05PU1RJQyBFTkdJTkUgXQo='
    $banner1 = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b1_b64))

    $b2_b64 = 'CgogIOKVlOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVlwogIOKVkSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg4pWRCiAg4pWRICAgIC9cICAvXCBfX18gIF9fXyAgL19cICAvXCAgL1wvXCBfX18gIC9cIC9cICAgL1wgIC9cX19fIC98ICB8ICB8ICAvXCAg4pWRCiAg4pWRICAgLyAvXy8gLy8gXyBcLyBfX3wvL19cXC8gL18vIC8gIFYgIC8gXyBcLyAvLyAvIC9fLyAvIC1fKVwgXHwgfCAgfCBcLyAg4pWRCiAg4pWRICAvXy8gL18vIFxfX18vXF9fXy9fLyBcX1xfX19fL3xffF98X1xfX18vXy8gXF9cX19fXy9cX19ffCAgXF98X3wgIHxfL19cIOKVkQogIOKVkSAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAg4pWRCiAg4pWRICA+PiBTRU5USU5FTEFJICA6OiAgUkVNT1RFIElUIEZPUkVOU0lDUyAgOjogIHYyLjAgIDo6ICBDT1JQIEdSQURFICAgICAgIOKVkQogIOKVmuKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVkOKVnQo='
    $banner2 = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b2_b64))

    $b3_b64 = 'CgogIOKUjOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUgOKUkAogIOKUgiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICDilIIKICDilIIgICAgQUQ6SU5GUkEg4pa4IERJQUdOT1NUSUMgRU5HSU5FICAgICAgICAgICAgICAgICAgICBbIFNFQ1VSRSBDSEFOTkVMIF0gICDilIIKICDilIIgICAg4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSA4pSAICAgIOKUggogIOKUgiAgICBUQVJHRVQgQUNRVUlTSVRJT04g4pyTICAgIFBBWUxPQUQ6IFJFQUQtT05MWSDinJMgICAgQUkgQ09SRTogT05MSU5FIOKckyAgIOKUggogIOKUgiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICDilIIKICDilJTilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilIDilJgK'
    $banner3 = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($b3_b64))

    $banners  = @($banner1, $banner2, $banner3)
    $selected = $banners | Get-Random
    Write-Host $selected -ForegroundColor $clrPrimary

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # BLOQUE DE CREDITOS
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    Write-Host $("  " + "$([char]0x2500)" * 73) -ForegroundColor $clrDim
    Write-Host ""

    Write-Host "  [+] " -ForegroundColor $clrAccent -NoNewline
    Write-Host "ZERO TRUST DIAGNOSTIC ENGINE v2.0" -ForegroundColor $clrText
    
    Write-Host "  [+] " -ForegroundColor $clrAccent -NoNewline
    Write-Host "Arquitectura y Desarrollo por: " -ForegroundColor $clrSecondary -NoNewline
    Write-Host "Fabian Paternina" -ForegroundColor $clrText
    
    Write-Host "  [+] " -ForegroundColor $clrAccent -NoNewline
    Write-Host "Powered by " -ForegroundColor $clrSecondary -NoNewline
    Write-Host "Google Gemini AI" -ForegroundColor $clrPrimary -NoNewline
    Write-Host "  -  SentinelAI Core Active`n" -ForegroundColor $clrDim
    
    Write-Host $("  " + "$([char]0x2500)" * 73) -ForegroundColor $clrDim

    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # BLOQUE DE ESTADO Y SEGURIDAD Y CONTEXTO COMPACTO (El "Grid")
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    Write-Host "`n  [!] " -ForegroundColor $clrAlert -NoNewline
    Write-Host "MODO SEGURO: Politicas de solo lectura aplicadas  |  CANAL: Zero Trust Tunnel Cifrado`n" -ForegroundColor $clrSecondary
    
    Write-Host $("  " + "$([char]0x2500)" * 73) -ForegroundColor $clrDim

    # Procesamiento y padding para el Grid Ultra-Compacto
    $osClean = $SysInfo.os -replace "Microsoft ", ""
    if ($osClean.Length -gt 18) { $osClean = $osClean.Substring(0,15) + "..." }
    $taskClean = $Issue
    if ($taskClean.Length -gt 24) { $taskClean = $taskClean.Substring(0,21) + "..." }
    $targetClean = $ServerUrl -replace "http://", "" -replace "https://", ""
    
    $col1 = 32; $col2 = 22
    Write-Host "`n  " -NoNewline
    Write-Host ("Target: " + $targetClean).PadRight($col1) -ForegroundColor $clrText -NoNewline
    Write-Host "| " -ForegroundColor $clrDim -NoNewline
    Write-Host ("Host: " + $SysInfo.hostname).PadRight($col2) -ForegroundColor $clrSecondary -NoNewline
    Write-Host "| " -ForegroundColor $clrDim -NoNewline
    Write-Host ("IP: " + $SysInfo.ip) -ForegroundColor $clrSecondary

    Write-Host "  " -NoNewline
    Write-Host ("Task: " + $taskClean).PadRight($col1) -ForegroundColor $clrText -NoNewline
    Write-Host "| " -ForegroundColor $clrDim -NoNewline
    Write-Host ("OS: " + $osClean).PadRight($col2) -ForegroundColor $clrSecondary -NoNewline
    Write-Host "| " -ForegroundColor $clrDim -NoNewline
    Write-Host ("Uptime: " + $SysInfo.uptime) -ForegroundColor $clrSecondary

    Write-Host "`n"
    Write-Host $("  " + "$([char]0x2500)" * 73) -ForegroundColor $clrDim
    Write-Host "`n  [CTRL+C]" -ForegroundColor $clrAlert -NoNewline
    Write-Host " Abortar sesion en cualquier momento.`n" -ForegroundColor $clrDim
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
                    Write-Host "  [BLOQUEADO] Patron prohibido: .exe" -ForegroundColor Red
                    return $false
                }
            }
        }
        elseif ($cmd -match [regex]::Escape($blocked)) {
            Write-Host "  [BLOQUEADO] Patron prohibido: $blocked" -ForegroundColor Red
            return $false
        }
    }
    
    # La validacion por Whitelist ($AllowedCmdlets) fue eliminada 
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
    
    # Limitar tamano de salida (evitar mensajes enormes por WebSocket)
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
        Recolecta la informacion basica del equipo para enviar al backend.
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
    $segment = New-Object System.ArraySegment[byte] -ArgumentList @(, $bytes)
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
        $segment = New-Object System.ArraySegment[byte] -ArgumentList @(, $buffer)
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
            throw "El servidor cerro la conexion."
        }
        
        $chunk = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $received.Count)
        [void]$result.Append($chunk)
        
    } while (-not $received.EndOfMessage)
    
    $cts.Dispose()
    return $result.ToString()
}


function Show-Separator {
    param([string]$Color = "DarkGray")
    Write-Host "  $("$([char]0x2500)" * 57)" -ForegroundColor $Color
}


function Format-DiagnosisReport {
    <#
    .SYNOPSIS
        Formatea y muestra el reporte de diagnostico final en la consola.
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
    Write-Host "                DIAGNOSTICO FINAL                                 " -ForegroundColor $color
    Write-Host "  " -ForegroundColor $color
    Write-Host ""
    Write-Host "  $icon Severidad: $($sev.ToUpper())" -ForegroundColor $color
    Write-Host "  Equipo: $($Report.hostname)" -ForegroundColor White
    Write-Host "  Sesion: $($Report.session_id)" -ForegroundColor Gray
    Write-Host "  Pasos ejecutados: $($Report.steps_taken)" -ForegroundColor Gray
    Write-Host ""
    Show-Separator
    Write-Host ""
    Write-Host "  CAUSA RAÃZ:" -ForegroundColor White
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
    Write-Host ""
    Write-Host "  [ERROR] Este script debe ejecutarse como Administrador." -ForegroundColor Red
    Write-Host "  Haz clic derecho en PowerShell > Ejecutar como administrador." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# 1. Recolectar info antes del banner para inyectarla en el Grid
$sysInfo = Get-MachineInfo

# 2. Renderizar Interfaz Compacta y Banners Rotativos Originales
Show-Banner -ServerUrl $ServerUrl -Issue $Issue -SysInfo $sysInfo

# 3. Unica linea elegante de conexion
Write-Host "  [+] Estableciendo Secure Web-Socket & SysInfo Sync... " -ForegroundColor Gray -NoNewline

# Construir la URL del WebSocket
$wsUrl = $ServerUrl -replace "^http", "ws"
$wsUrl = "$wsUrl/api/v1/diagnostics/ws"

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
            break
        }
        catch {
            $errMsg = if ($_.Exception.InnerException) { $_.Exception.InnerException.Message } else { $_.Exception.Message }
            if ($attempt -ge $MaxReconnectAttempts) {
                Write-Host "`n  [FATAL] No se pudo conectar al servidor despues de $MaxReconnectAttempts intentos. Error: $errMsg" -ForegroundColor Red
                exit 1
            }
            Start-Sleep -Seconds 5
        }
    }
    
    # Sincronizacion inicial invisible en consola
    $welcomeRaw = Receive-WsMessage -WebSocket $ws -Timeout 10
    Send-WsMessage -WebSocket $ws -Data $sysInfo
    
    # Rematar linea elegante con el [OK]
    Write-Host "[OK]" -ForegroundColor Green
    Write-Host $("  " + "$([char]0x2500)" * 73) -ForegroundColor DarkGray
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
            Write-Host "  [ERROR] Mensaje del servidor no es JSON valido." -ForegroundColor Red
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
                
                Write-Host "  +--------------------------------------------------" -ForegroundColor DarkCyan
                Write-Host "  | Hipotesis / Paso $stepNumber" -ForegroundColor Cyan
                Write-Host "  | Proposito: $purpose" -ForegroundColor White
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
                }
                elseif ($cmdResult.stderr) {
                    $preview = $cmdResult.stderr.Substring(0, [Math]::Min(200, $cmdResult.stderr.Length))
                }
                else {
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
            
            # -- Actualizacion de estado del agente
            "status_update" {
                Write-Host "  [Agente] $($msg.message)" -ForegroundColor Cyan
                Write-Host ""
            }
            
            # -- Diagnostico completo
            "diagnosis_complete" {
                Write-Host "  [OK] El agente ha completado el diagnostico." -ForegroundColor Green
                Write-Host ""
                
                # Convertir PSObject a hashtable para el formateador
                $report = @{}
                $msg.report.PSObject.Properties | ForEach-Object { $report[$_.Name] = $_.Value }
                
                Format-DiagnosisReport -Report $report
                
                $sessionActive = $false
            }
            
            # -- Diagnostico incompleto (maximo de pasos)
            "diagnosis_incomplete" {
                Write-Host "  [ADVERTENCIA] $($msg.message)" -ForegroundColor Yellow
                Write-Host ""
                $sessionActive = $false
            }
            
            # -- Fin de sesion
            "session_end" {
                Write-Host "  [i] $($msg.message)" -ForegroundColor Gray
                $sessionActive = $false
            }
            
            # -- Error del servidor
            "error" {
                Write-Host "  [ERROR del Servidor] $($msg.message)" -ForegroundColor Red
                Write-Host ""
                # No romper el loop por un error, el agente puede recuperarse
            }
            
            # -- Mensaje desconocido
            default {
                Write-Host "  [?] Mensaje desconocido (tipo: $msgType): $msgRaw" -ForegroundColor DarkYellow
            }
        }
    }
}
catch {
    $ex = $_.Exception
    # Desempaquetar AggregateException de las llamadas a .Wait() para ver el error real
    while ($ex -is [System.AggregateException] -and $ex.InnerException) {
        $ex = $ex.InnerException
    }
    
    if ($ex -is [System.Net.WebSockets.WebSocketException]) {
        Write-Host "`n  [DESCONEXION] La conexion con el servidor se perdio o fue cerrada abruptamente." -ForegroundColor Yellow
        Write-Host "  [Detalle] $($ex.Message)" -ForegroundColor DarkYellow
    }
    else {
        Write-Host "`n  [ERROR FATAL] $($ex.Message)" -ForegroundColor Red
        if ($ex.InnerException) {
            Write-Host "  [Detalle] $($ex.InnerException.Message)" -ForegroundColor DarkRed
        }
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
    
    Write-Host "`n  $("$([char]0x2500)" * 57)" -ForegroundColor DarkGray
    Write-Host "  Sesion de diagnostico finalizada." -ForegroundColor Gray
    Write-Host "  Presiona Enter para cerrar..." -ForegroundColor Gray
    Write-Host ""
    Read-Host
}
