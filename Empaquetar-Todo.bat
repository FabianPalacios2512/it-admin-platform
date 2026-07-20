@echo off
echo ========================================================
echo PREPARANDO EL EMPAQUETADOR MAESTRO...
echo ========================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Empaquetar-Todo.ps1"
pause
