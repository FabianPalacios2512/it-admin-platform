$ErrorActionPreference = "Stop"
$SourceDir = $PSScriptRoot
$DestDir = "C:\AdminInfra"
$ServiceName = "AdminInfraService"
$Port = 8000

Write-Host "Iniciando instalacion..." -ForegroundColor Cyan

if (Get-Service $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service $ServiceName -Force
    Start-Sleep -Seconds 2
    if (Test-Path "$DestDir\nssm.exe") {
        & "$DestDir\nssm.exe" remove $ServiceName confirm
    }
}

Get-Process -Name AdminInfraBackend -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

if (Test-Path $DestDir) { Remove-Item $DestDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
Copy-Item -Path "$SourceDir\*" -Destination $DestDir -Recurse -Force

$NssmPath = "$DestDir\nssm.exe"
if (-Not (Test-Path $NssmPath)) { throw "nssm.exe no encontrado" }

& $NssmPath install $ServiceName "$DestDir\backend\AdminInfraBackend.exe" ""
& $NssmPath set $ServiceName AppDirectory "$DestDir\backend"
& $NssmPath set $ServiceName AppEnvironmentExtra "PYTHONIOENCODING=utf-8"
& $NssmPath set $ServiceName AppStdout "$DestDir\service_error.log"
& $NssmPath set $ServiceName AppStderr "$DestDir\service_error.log"
& $NssmPath set $ServiceName Description "AdminInfra Core (Standalone)"
& $NssmPath set $ServiceName Start SERVICE_AUTO_START

New-NetFirewallRule -DisplayName "AdminInfra Port $Port" -Direction Inbound -LocalPort $Port -Protocol TCP -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null

Start-Service $ServiceName

try {
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $PngPath = "$DestDir\backend\dist\logo.png"
    $IcoPath = "$DestDir\logo.ico"
    if (Test-Path $PngPath) {
        Add-Type -AssemblyName System.Drawing
        $bmp = New-Object System.Drawing.Bitmap($PngPath)
        $resized = New-Object System.Drawing.Bitmap($bmp, 256, 256)
        $iconHandle = $resized.GetHicon()
        $icon = [System.Drawing.Icon]::FromHandle($iconHandle)
        $icoStream = New-Object System.IO.FileStream($IcoPath, [System.IO.FileMode]::Create)
        $icon.Save($icoStream)
        $icoStream.Close()
        $icon.Dispose()
        $resized.Dispose()
        $bmp.Dispose()
    }
    $ShortcutPath = "$DesktopPath\AdminInfra.url"
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = "http://localhost:$Port"
    if (Test-Path $IcoPath) { $Shortcut.IconFile = $IcoPath; $Shortcut.IconIndex = 0 }
    $Shortcut.Save()
} catch {}

Write-Host "Instalacion completada con exito." -ForegroundColor Green
Start-Sleep -Seconds 5
