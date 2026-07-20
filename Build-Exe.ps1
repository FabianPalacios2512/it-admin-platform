$ErrorActionPreference = "Stop"

$Workspace = "C:\Users\Fabian Paternina\OneDrive - Hogar y Moda S.A.S\Documentos\ADMIN DA\it-admin-platform"
$BackendDir = "$Workspace\backend"
$SetupDir = "$Workspace\AdminInfra-Setup\backend"

Write-Host "1. Instalando PyInstaller..." -ForegroundColor Cyan
Set-Location $BackendDir
& .\venv\Scripts\python.exe -m pip install pyinstaller

Write-Host "2. Compilando el Backend (Esto tomara unos minutos)..." -ForegroundColor Cyan
& .\venv\Scripts\pyinstaller.exe --name AdminInfraBackend --onefile --hidden-import uvicorn.logging --hidden-import uvicorn.loops --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols --hidden-import uvicorn.protocols.http --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.websockets --hidden-import uvicorn.protocols.websockets.auto --hidden-import uvicorn.lifespan.on --hidden-import uvicorn.lifespan.off app/main.py

Write-Host "3. Copiando el Ejecutable al Instalador..." -ForegroundColor Cyan
Copy-Item "dist\AdminInfraBackend.exe" -Destination "$SetupDir\AdminInfraBackend.exe" -Force

Write-Host "4. Limpiando el Entorno Virtual del Instalador (ya no se necesita)..." -ForegroundColor Cyan
if (Test-Path "$SetupDir\venv") {
    Remove-Item "$SetupDir\venv" -Recurse -Force
}

Write-Host "`n¡Compilación Terminada Exitosamente!" -ForegroundColor Green
Write-Host "Ya puedes tomar la carpeta 'AdminInfra-Setup', llevarla a cualquier servidor Windows, y ejecutar Setup.bat." -ForegroundColor Green
Write-Host "Presiona cualquier tecla para salir..."
$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null
