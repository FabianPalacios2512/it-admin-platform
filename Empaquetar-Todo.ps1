$ErrorActionPreference = "Stop"
$Workspace = $PSScriptRoot
$SetupDir = "$Workspace\AdminInfra-Instalador"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EMPAQUETANDO TODO EL PROYECTO (VERSION DEFINITIVA)     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Crear carpeta limpia
Write-Host "[1/4] Creando estructura limpia..." -ForegroundColor Yellow
if (Test-Path $SetupDir) { Remove-Item $SetupDir -Recurse -Force }
New-Item -ItemType Directory -Path "$SetupDir\backend" | Out-Null

# 2. Compilar Frontend
Write-Host "[2/4] Compilando el Frontend (Interfaz)..." -ForegroundColor Yellow
Set-Location "$Workspace\frontend"
cmd.exe /c "npm install"
cmd.exe /c "npm run build"
Copy-Item "$Workspace\frontend\dist" -Destination "$SetupDir\backend\dist" -Recurse -Force

# 3. Compilar Backend
Write-Host "[3/4] Compilando el Backend a .EXE (Tomara un par de minutos)..." -ForegroundColor Yellow
Set-Location "$Workspace\backend"
& .\venv\Scripts\python.exe -m pip install pyinstaller
& .\venv\Scripts\pyinstaller.exe --name AdminInfraBackend --onefile --paths . --collect-submodules app --hidden-import wmi --hidden-import pythoncom --hidden-import httpx --hidden-import uvicorn.logging --hidden-import uvicorn.loops --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols --hidden-import uvicorn.protocols.http --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import uvicorn.lifespan.off run.py

# 4. Mover archivos al instalador final
Write-Host "[4/4] Empaquetando y organizando todo..." -ForegroundColor Yellow
Copy-Item "$Workspace\backend\dist\AdminInfraBackend.exe" -Destination "$SetupDir\backend\AdminInfraBackend.exe" -Force

# 4.1 Copiar .env sin contraseñas (en blanco)
if (Test-Path "$Workspace\backend\.env") {
    $envContent = Get-Content "$Workspace\backend\.env"
    $newEnv = $envContent | Where-Object { $_ -notmatch "^ENTRA_" -and $_ -notmatch "^APP_PORT" }
    $newEnv | Set-Content "$SetupDir\backend\.env"
}

# 4.2 Copiar utilidades (nssm)
$OldNssm = "$Workspace\AdminInfra-Setup\nssm.exe"
if (Test-Path $OldNssm) {
    Copy-Item $OldNssm -Destination "$SetupDir\nssm.exe" -Force
}

# 4.3 Generar Install.ps1 limpio
$InstallScript = @"
`$ErrorActionPreference = "Stop"
`$SourceDir = `$PSScriptRoot
`$DestDir = "C:\AdminInfra"
`$ServiceName = "AdminInfraService"
`$Port = 8000

Write-Host "Iniciando instalacion..." -ForegroundColor Cyan

if (Get-Service `$ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service `$ServiceName -Force
    Start-Sleep -Seconds 2
    if (Test-Path "`$DestDir\nssm.exe") {
        & "`$DestDir\nssm.exe" remove `$ServiceName confirm
    }
}

Get-Process -Name AdminInfraBackend -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

if (Test-Path `$DestDir) { Remove-Item `$DestDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path `$DestDir | Out-Null
Copy-Item -Path "`$SourceDir\*" -Destination `$DestDir -Recurse -Force

`$NssmPath = "`$DestDir\nssm.exe"
if (-Not (Test-Path `$NssmPath)) { throw "nssm.exe no encontrado" }

& `$NssmPath install `$ServiceName "`$DestDir\backend\AdminInfraBackend.exe" ""
& `$NssmPath set `$ServiceName AppDirectory "`$DestDir\backend"
& `$NssmPath set `$ServiceName AppEnvironmentExtra "PYTHONIOENCODING=utf-8"
& `$NssmPath set `$ServiceName AppStdout "`$DestDir\service_error.log"
& `$NssmPath set `$ServiceName AppStderr "`$DestDir\service_error.log"
& `$NssmPath set `$ServiceName Description "AdminInfra Core (Standalone)"
& `$NssmPath set `$ServiceName Start SERVICE_AUTO_START

New-NetFirewallRule -DisplayName "AdminInfra Port `$Port" -Direction Inbound -LocalPort `$Port -Protocol TCP -Action Allow -Profile Any -ErrorAction SilentlyContinue | Out-Null

Start-Service `$ServiceName

try {
    `$DesktopPath = [Environment]::GetFolderPath("Desktop")
    `$PngPath = "`$DestDir\backend\dist\logo.png"
    `$IcoPath = "`$DestDir\logo.ico"
    if (Test-Path `$PngPath) {
        Add-Type -AssemblyName System.Drawing
        `$bmp = New-Object System.Drawing.Bitmap(`$PngPath)
        `$resized = New-Object System.Drawing.Bitmap(`$bmp, 256, 256)
        `$iconHandle = `$resized.GetHicon()
        `$icon = [System.Drawing.Icon]::FromHandle(`$iconHandle)
        `$icoStream = New-Object System.IO.FileStream(`$IcoPath, [System.IO.FileMode]::Create)
        `$icon.Save(`$icoStream)
        `$icoStream.Close()
        `$icon.Dispose()
        `$resized.Dispose()
        `$bmp.Dispose()
    }
    `$ShortcutPath = "`$DesktopPath\AdminInfra.url"
    `$WshShell = New-Object -ComObject WScript.Shell
    `$Shortcut = `$WshShell.CreateShortcut(`$ShortcutPath)
    `$Shortcut.TargetPath = "http://localhost:`$Port"
    if (Test-Path `$IcoPath) { `$Shortcut.IconFile = `$IcoPath; `$Shortcut.IconIndex = 0 }
    `$Shortcut.Save()
} catch {}

Write-Host "Instalacion completada con exito." -ForegroundColor Green
Start-Sleep -Seconds 5
"@

$InstallScript | Set-Content "$SetupDir\Install.ps1"

# 4.4 Generar Setup.bat
$SetupBat = @"
@echo off
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Install.ps1"
pause
"@
$SetupBat | Set-Content "$SetupDir\Setup.bat"

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " ¡CARPETA EMPAQUETADA CREADA CON EXITO! " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Busca la carpeta nueva llamada 'AdminInfra-Instalador'."
Write-Host "Esa es LA UNICA carpeta que necesitas llevarte al servidor."
Write-Host "Presiona cualquier tecla para cerrar esta ventana..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
