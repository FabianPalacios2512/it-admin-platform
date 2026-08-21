"""
Script de prueba para crear GPO LOCALMENTE (sin WinRM)
Este script ejecuta PowerShell localmente en el backend que está unido al dominio.
"""
import subprocess

# Tu ruta de wallpaper
wallpaper_path = r"\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg"
gpo_name = "Fondo_Pantalla_TEST_LOCAL"

# Script de PowerShell (igual que usa ad_service.py)
script = f"""
$ErrorActionPreference = 'Stop'
$gpoName = "{gpo_name}"

Write-Output "=== INICIANDO CREACIÓN DE GPO ==="
Write-Output "Nombre: $gpoName"
Write-Output "Wallpaper: {wallpaper_path}"

try {{
    # Crear GPO
    Write-Output "Creando GPO..."
    $gpo = New-GPO -Name $gpoName
    Write-Output "GPO creado con GUID: $($gpo.Id)"
    
    # Configurar wallpaper
    Write-Output "Configurando wallpaper..."
    Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ValueName "Wallpaper" -Type String -Value "{wallpaper_path}"
    
    Write-Output "Configurando estilo de wallpaper (centrado/ajustado)..."
    Set-GPRegistryValue -Name $gpoName -Key "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -ValueName "WallpaperStyle" -Type String -Value "2"
    
    Write-Output "=== GPO CREADO EXITOSAMENTE ==="
    
    # Opcional: Vincular a un OU
    # Write-Output "Vinculando GPO a DC=code,DC=local..."
    # New-GPLink -Name $gpoName -Target "DC=code,DC=local" -LinkEnabled Yes
    # Write-Output "GPO vinculado exitosamente"
    
}} catch {{
    Write-Error "ERROR: $_"
    Write-Output "Detalles del error:"
    Write-Output $_.Exception.Message
    Write-Output $_.Exception.StackTrace
    exit 1
}}
"""

print("Ejecutando PowerShell LOCALMENTE...")
print("=" * 60)

try:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        encoding='utf-8',
        errors='replace'
    )
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nRETURN CODE: {result.returncode}")
    
    if result.returncode == 0:
        print("\n✅ ¡ÉXITO! GPO creado correctamente")
        print(f"Ahora puedes ir a la consola de GPO y ver '{gpo_name}'")
    else:
        print("\n❌ ERROR: El script falló")
        with open("gpo_local_debug.log", "w", encoding='utf-8') as f:
            f.write(f"SCRIPT:\n{script}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nRETURN CODE: {result.returncode}")
        print("Log guardado en: gpo_local_debug.log")
        
except subprocess.TimeoutExpired:
    print("❌ TIMEOUT: El script tardó más de 30 segundos")
except Exception as e:
    print(f"❌ EXCEPCIÓN: {e}")
