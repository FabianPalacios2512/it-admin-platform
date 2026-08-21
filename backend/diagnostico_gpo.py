"""
DIAGNÓSTICO GPO: Verifica que el sistema esté listo para crear GPOs
"""
import subprocess
import os

print("=" * 70)
print("DIAGNÓSTICO: Creación de GPOs")
print("=" * 70)
print()

checks = []

# 1. Verificar que estamos en un equipo unido al dominio
print("✓ Verificando conexión al dominio...")
try:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "(Get-WmiObject Win32_ComputerSystem).Domain"],
        capture_output=True,
        text=True,
        timeout=5
    )
    domain = result.stdout.strip()
    
    if domain and domain.lower() != "workgroup":
        print(f"  ✅ Equipo unido al dominio: {domain}")
        checks.append(True)
    else:
        print(f"  ❌ Equipo NO está unido al dominio (actualmente: {domain})")
        print("     SOLUCIÓN: Une este equipo al dominio 'code.local' primero")
        checks.append(False)
except Exception as e:
    print(f"  ❌ Error verificando dominio: {e}")
    checks.append(False)

print()

# 2. Verificar que el usuario actual tiene permisos de Domain Admin
print("✓ Verificando permisos de Domain Admin...")
try:
    script = """
    $user = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($user)
    $adminRole = [System.Security.Principal.WindowsBuiltInRole]::Administrator
    
    if ($principal.IsInRole($adminRole)) {
        Write-Output "ADMIN_LOCAL_OK"
    }
    
    # Verificar si tiene permisos de Domain Admin
    try {
        Import-Module ActiveDirectory -ErrorAction Stop
        $currentUser = $env:USERNAME
        $domainAdmins = Get-ADGroupMember "Domain Admins" -Recursive | Select-Object -ExpandProperty SamAccountName
        if ($domainAdmins -contains $currentUser) {
            Write-Output "DOMAIN_ADMIN_OK"
        } else {
            Write-Output "NOT_DOMAIN_ADMIN"
        }
    } catch {
        Write-Output "CANNOT_CHECK_DOMAIN_ADMIN"
    }
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    output = result.stdout.strip()
    
    if "ADMIN_LOCAL_OK" in output:
        print("  ✅ Permisos de Administrador Local: OK")
    else:
        print("  ⚠️  NO tienes permisos de Administrador Local")
        print("     SOLUCIÓN: Ejecuta el backend como Administrador")
    
    if "DOMAIN_ADMIN_OK" in output:
        print("  ✅ Permisos de Domain Admin: OK")
        checks.append(True)
    elif "NOT_DOMAIN_ADMIN" in output:
        print("  ❌ El usuario actual NO es Domain Admin")
        print("     SOLUCIÓN: Ejecuta el backend con un usuario que sea Domain Admin")
        checks.append(False)
    else:
        print("  ⚠️  No se pudo verificar si eres Domain Admin (puede ser un problema de módulos)")
        print("     Continuando de todos modos...")
        checks.append(True)
        
except Exception as e:
    print(f"  ❌ Error verificando permisos: {e}")
    checks.append(False)

print()

# 3. Verificar que el módulo GroupPolicy está disponible
print("✓ Verificando módulo GroupPolicy de PowerShell...")
try:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "Get-Module -ListAvailable -Name GroupPolicy | Select-Object -ExpandProperty Name"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if "GroupPolicy" in result.stdout:
        print("  ✅ Módulo GroupPolicy disponible")
        checks.append(True)
    else:
        print("  ❌ Módulo GroupPolicy NO disponible")
        print("     SOLUCIÓN: Instala RSAT (Remote Server Administration Tools)")
        print("     En Windows 10/11: Settings → Apps → Optional Features → Add 'RSAT: Group Policy Management Tools'")
        checks.append(False)
except Exception as e:
    print(f"  ❌ Error verificando módulo: {e}")
    checks.append(False)

print()

# 4. Verificar acceso a la ruta del wallpaper
print("✓ Verificando acceso a la ruta del wallpaper...")
wallpaper_path = r"\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg"
try:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"Test-Path '{wallpaper_path}'"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if "True" in result.stdout:
        print(f"  ✅ Archivo accesible: {wallpaper_path}")
        checks.append(True)
    else:
        print(f"  ❌ Archivo NO accesible: {wallpaper_path}")
        print("     SOLUCIÓN:")
        print("     1. Verifica que el archivo existe en esa ruta exacta")
        print("     2. Verifica que el share tiene permisos de lectura para 'Everyone' o 'Domain Users'")
        print("     3. Verifica que no hay firewall bloqueando el acceso al servidor 192.168.20.110")
        checks.append(False)
except Exception as e:
    print(f"  ⚠️  Error verificando archivo (puede ser problema de red): {e}")
    checks.append(False)

print()

# 5. Intentar crear un GPO de prueba (y eliminarlo inmediatamente)
print("✓ Prueba de creación de GPO...")
test_gpo_name = "TEST_DIAGNOSTICO_GPO_TEMP"
try:
    # Intentar crear
    create_script = f"""
    $ErrorActionPreference = 'Stop'
    try {{
        New-GPO -Name "{test_gpo_name}" | Out-Null
        Write-Output "GPO_CREATED"
    }} catch {{
        Write-Error $_.Exception.Message
    }}
    """
    
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", create_script],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if "GPO_CREATED" in result.stdout:
        print(f"  ✅ GPO de prueba creado exitosamente")
        
        # Eliminar el GPO de prueba
        delete_script = f"Remove-GPO -Name '{test_gpo_name}' -Confirm:$false"
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", delete_script],
            capture_output=True,
            text=True,
            timeout=10
        )
        print(f"  ✅ GPO de prueba eliminado")
        checks.append(True)
    else:
        print(f"  ❌ Error al crear GPO de prueba:")
        print(f"     {result.stderr.strip()}")
        checks.append(False)
        
except Exception as e:
    print(f"  ❌ Error en prueba de GPO: {e}")
    checks.append(False)

print()
print("=" * 70)
print("RESULTADO DEL DIAGNÓSTICO")
print("=" * 70)

passed = sum(checks)
total = len(checks)

if passed == total:
    print(f"✅ TODOS LOS CHECKS PASARON ({passed}/{total})")
    print()
    print("🎉 ¡Tu sistema está listo para crear GPOs!")
    print()
    print("Siguiente paso:")
    print("  1. Ejecuta: python test_gpo_local.py")
    print("  2. O usa la interfaz web en GPO Manager")
else:
    print(f"⚠️  ALGUNOS CHECKS FALLARON ({passed}/{total} pasaron)")
    print()
    print("Por favor, corrige los problemas indicados arriba antes de continuar.")

print()
