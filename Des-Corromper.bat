@echo off
echo ========================================================
echo REPARANDO LETRAS Y TILDES CORRUPTAS...
echo ========================================================

python "%~dp0fix_letras.py"

echo Letras reparadas.
echo ========================================================
echo RECONSTRUYENDO EL INSTALADOR...
echo ========================================================
powershell.exe -ExecutionPolicy Bypass -File "%~dp0Empaquetar-Todo.ps1"
pause
