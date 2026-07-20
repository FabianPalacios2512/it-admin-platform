@echo off
echo Iniciando compilacion de AdminInfra...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Build-Exe.ps1"
pause
