# SOLUCIÓN: Creación de GPOs para Fondos de Pantalla

## 🔥 PROBLEMA IDENTIFICADO

El error **NO era WinRM**. El log real mostraba:

```
New-GPO : Acceso a la red denegado. (HRESULT: 0x80070041)
El servidor no es funcional. Nombre: "WIN-G1GRN0DCKJA.code.local"
```

**Causa raíz:** "Double-hop authentication" fallando. Cuando ejecutabas PowerShell remotamente vía WinRM, los comandos de GPO (`New-GPO`, `Set-GPRegistryValue`) intentaban comunicarse con el Domain Controller pero no podían porque WinRM no puede hacer esa segunda autenticación.

## ✅ SOLUCIÓN IMPLEMENTADA

**Ejecutar PowerShell LOCALMENTE** (como lo hace TODA tu aplicación):

- ✅ `ad_service.py` ejecuta PowerShell localmente con `subprocess.run()`
- ✅ `fs_service.py` ejecuta PowerShell localmente
- ✅ `printer_service.py` ejecuta PowerShell localmente
- ✅ `exchange_service.py` ejecuta PowerShell localmente
- ❌ `gpo.py` estaba intentando usar WinRM remotamente (ERROR)

**Ahora `gpo.py` también ejecuta localmente**, porque tu backend YA está unido al dominio como `code\administrador`.

## 🧪 PRUEBA RÁPIDA

Ejecuta este script de prueba:

```bash
cd backend
python test_gpo_local.py
```

Esto creará un GPO llamado `Fondo_Pantalla_TEST_LOCAL` con tu ruta:
```
\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg
```

## 📝 LO QUE CAMBIÓ EN EL CÓDIGO

### `backend/app/api/v1/gpo.py` (Línea 114-154)

**ANTES (WinRM remoto - FALLABA):**
```python
import winrm
session = winrm.Session(cfg["ip"], auth=(...), transport='ntlm')
r = session.run_ps(final_script)
```

**AHORA (PowerShell local - FUNCIONA):**
```python
result = subprocess.run(
    ["powershell", "-NoProfile", "-NonInteractive", "-Command", final_script],
    capture_output=True,
    text=True,
    timeout=60
)
```

### Template de Wallpaper (Línea 34-47)

**AHORA sin `-Server` y `-Domain`** (no son necesarios cuando ejecutas localmente):

```powershell
$gpoName = "Mi_GPO"
New-GPO -Name $gpoName | Out-Null
Set-GPRegistryValue -Name $gpoName -Key "HKCU\Software\..." -ValueName "Wallpaper" -Type String -Value "\\servidor\share\imagen.jpg"
```

## 🎯 CÓMO CREAR TU GPO DE FONDO DE PANTALLA

### Opción 1: Desde la UI (Recomendado)

1. Ve a **GPO Manager** en la plataforma
2. Click en "Nueva Política"
3. Selecciona **"Fondo de Pantalla"**
4. Ingresa la ruta: `\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg`
5. Selecciona el OU destino (ej: `DC=code,DC=local` para todos)
6. Click "Crear GPO"

### Opción 2: Prueba directa (Script Python)

```bash
cd backend
python test_gpo_local.py
```

### Opción 3: Prueba manual (PowerShell directo)

Abre PowerShell como Administrador en tu laptop (que ya está en el dominio):

```powershell
$gpoName = "Wallpaper_Hogar_Moda"
New-GPO -Name $gpoName
Set-GPRegistryValue -Name $gpoName -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" -ValueName "Wallpaper" -Type String -Value "\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg"
Set-GPRegistryValue -Name $gpoName -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" -ValueName "WallpaperStyle" -Type String -Value "2"
New-GPLink -Name $gpoName -Target "DC=code,DC=local" -LinkEnabled Yes
```

## 🔍 VERIFICACIÓN

Después de crear el GPO:

1. Abre **Consola de Administración de Directivas de Grupo** (`gpmc.msc`)
2. Navega a `code.local` → `Group Policy Objects`
3. Busca tu GPO recién creado
4. Verifica que esté vinculado al OU correcto
5. En un equipo cliente, ejecuta: `gpupdate /force`
6. Reinicia sesión → El fondo de pantalla debe cambiar

## 📌 REQUISITOS

✅ El backend (laptop donde corre la app) **DEBE estar unida al dominio**  
✅ El usuario que corre el backend **DEBE tener permisos de Domain Admin**  
✅ La ruta del wallpaper **DEBE ser accesible por todos los usuarios** (permisos de lectura)  
✅ El archivo **DEBE existir** en la ruta especificada

## 🚨 TROUBLESHOOTING

### Si dice "Access Denied" o "Acceso denegado":
- Verifica que el usuario `code\administrador` tenga permisos de Domain Admin
- Verifica que el backend esté corriendo con ese usuario (no como otro usuario local)

### Si dice "File not found":
- Verifica que la ruta UNC sea correcta: `\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg`
- Verifica que el archivo exista: desde PowerShell ejecuta `Test-Path "\\192.168.20.110\Fondos de pantalla\Fondodepantalla.jpg"`
- Verifica los permisos del share: debe tener permisos de lectura para "Everyone" o "Domain Users"

### Si el GPO no se aplica a los clientes:
- Verifica que el GPO esté **vinculado** a un OU que contenga los equipos
- Ejecuta `gpupdate /force` en el equipo cliente
- Verifica con `gpresult /R` que el GPO esté listado
- Reinicia sesión (algunos cambios requieren logout/login)

## 📊 LOGS

Si algo falla, revisa:
- `backend/gpo_debug.log` - Log detallado del último intento
- `backend/gpo_local_debug.log` - Log del script de prueba

## ✨ VENTAJAS DE ESTA SOLUCIÓN

1. ✅ **Más rápida**: No hay overhead de WinRM
2. ✅ **Más segura**: Usa la autenticación nativa del dominio
3. ✅ **Más confiable**: No depende de configuración de WinRM en el DC
4. ✅ **Consistente**: Usa el mismo método que todos los demás módulos de la app
5. ✅ **Sin configuración extra**: No necesitas habilitar puertos ni servicios adicionales

---

**Creado:** 18 de Agosto, 2026  
**Autor:** IT Admin Platform - AdInfra F2
