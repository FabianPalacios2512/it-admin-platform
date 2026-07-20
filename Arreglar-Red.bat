@echo off
echo ========================================================
echo CORRIGIENDO DIRECCIONES DE RED EN EL FRONTEND...
echo ========================================================

powershell.exe -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0frontend\src' -Recurse -File -Filter '*.vue' | ForEach-Object { $c = Get-Content $_.FullName; $c = $c -replace 'http://localhost:8000/api/v1', '/api/v1'; Set-Content -Path $_.FullName -Value $c -Encoding UTF8 }"

echo Red corregida exitosamente.
echo ========================================================
echo PREPARANDO EL EMPAQUETADOR MAESTRO...
echo ========================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Empaquetar-Todo.ps1"
pause
