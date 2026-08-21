"""Inspección real de GPOs: LDAP (enlaces/estado) + reporte en el DC."""
import json
import logging
import re

from ldap3 import SUBTREE

from app.services.ad_service import _get_admin_connection, _get_search_base, _paged_search, _parse_ad_timestamp
from app.services.dc_exec import run_on_dc

logger = logging.getLogger(__name__)

_CSE = {
    "{35378EAC-683F-11D2-A89A-00C04FBBCFA2}": "Directivas de registro (Administrative Templates)",
    "{25537BA6-77A8-11D2-9B6C-0000F8080861}": "Redirección de carpetas",
    "{3610EDA5-77EF-11D2-8DC5-00C04FA31A66}": "Servicios de Microsoft Disk Quota",
    "{42B5FAAE-6536-11D2-AE5A-0000F87571E3}": "Scripts (inicio/apagado/logon/logoff)",
    "{827D319E-6EAC-11D2-A4EA-00C04F79F83A}": "Seguridad (Security Settings)",
    "{B1BE8D72-D9C9-11D2-A4B0-00C04FB9942E}": "Public Key / certificados",
    "{C6DC5466-785A-11D2-84D0-00C04FB169F7}": "Software Installation",
    "{AADCED64-746C-4633-A97C-D61349046527}": "Preferencias: unidades de red",
    "{5794DAFD-BE60-433F-88A2-1A31939AC01F}": "Preferencias: unidades mapeadas",
    "{B087BE9D-ED37-454F-AF9C-04291E351182}": "Preferencias: registro",
    "{E472D224-8132-4E19-A00D-E22708A61EF1}": "Preferencias: impresoras",
    "{17D89FEC-5C44-4972-B12D-241CAEF74509}": "Preferencias: archivos",
    "{0AC5A4F4-5B95-4488-ABE0-ED5CF7A6304F}": "Preferencias: scheduled tasks",
    "{F9C7741B-2B64-43D3-99C6-3FF628041C21}": "Preferencias: servicios",
    "{91FBB303-0CD5-4055-BF42-E512A681B325}": "Preferencias: variables de entorno",
    "{C418A6C4-4F56-41C6-9164-39BCBE7CED4C}": "Preferencias: accesos directos",
    "{3BAE7E51-E707-4F80-942A-5DC6C77A8DDC}": "Preferencias: carpetas",
    "{6A4C5F53-3A7E-4B3A-8C4C-1A3B3E1C6E2A}": "Windows Firewall",
    "{D76B6B31-044D-4D5C-8A03-6281C2530B2F}": "Internet Explorer Maintenance",
}

_INQUIRY_RE = re.compile(
    r"(sirve|hace|afecta|aplica|alcance|activa|inactiva|qu[eé]\s+es|diagnost|revisar|"
    r"analizar|explica|detalle|configur|vincul|enlace|link|ou\b|a qui[eé]n|para qu[eé]|"
    r"razon|raz[oó]n|estado)",
    re.IGNORECASE,
)


def _parse_cse_names(raw) -> list[str]:
    text = str(raw or "")
    found = []
    for guid, label in _CSE.items():
        if guid.lower() in text.lower() and label not in found:
            found.append(label)
    return found


def _parse_gplink(gplink: str, target_guid: str) -> dict | None:
    if not gplink or not target_guid:
        return None
    guid = target_guid.strip("{}").lower()
    for part in str(gplink).split("]"):
        if guid not in part.lower():
            continue
        flag = 0
        if ";" in part:
            try:
                flag = int(part.rsplit(";", 1)[-1].strip("[ "))
            except ValueError:
                flag = 0
        return {
            "enabled": flag not in (1, 3),
            "enforced": flag in (2, 3),
        }
    return None


def find_gpo_ldap(name: str) -> dict | None:
    needle = (name or "").strip()
    if not needle:
        return None
    conn = _get_admin_connection()
    search_base = _get_search_base()
    try:
        entries = _paged_search(
            conn,
            "CN=Policies,CN=System," + search_base,
            "(objectClass=groupPolicyContainer)",
            ["displayName", "cn", "whenChanged", "whenCreated", "flags", "gPCMachineExtensionNames", "gPCUserExtensionNames", "displayNamePrintable"],
        )
        match = None
        for entry in entries:
            attrs = entry.entry_attributes_as_dict
            display = str(attrs.get("displayName", [""])[0] or "")
            cn = str(attrs.get("cn", [""])[0] or "")
            if display.lower() == needle.lower() or cn.lower() == needle.lower() or needle.lower() in display.lower():
                match = attrs
                if display.lower() == needle.lower():
                    break
        if not match:
            return None

        guid = str(match.get("cn", [""])[0] or "")
        flags = match.get("flags", [0])[0] or 0
        if flags == 3:
            status = "Inactivo"
        elif flags == 1:
            status = "Equipo activo / Usuario deshabilitado"
        elif flags == 2:
            status = "Usuario activo / Equipo deshabilitado"
        else:
            status = "Activo"

        links = []
        linked_objs = _paged_search(
            conn,
            search_base,
            "(gPLink=*)",
            ["distinguishedName", "name", "gPLink"],
        )
        for obj in linked_objs:
            oattrs = obj.entry_attributes_as_dict
            gplink = str((oattrs.get("gPLink") or [""])[0] or "")
            info = _parse_gplink(gplink, guid)
            if not info:
                continue
            dn = str((oattrs.get("distinguishedName") or [""])[0] or "")
            links.append({
                "name": str((oattrs.get("name") or [dn])[0] or dn),
                "dn": dn,
                "link_enabled": info["enabled"],
                "enforced": info["enforced"],
            })

        return {
            "name": str(match.get("displayName", [needle])[0] or needle),
            "guid": guid,
            "status": status,
            "flags": flags,
            "modified": _parse_ad_timestamp((match.get("whenChanged") or [None])[0]),
            "computer_extensions": _parse_cse_names(match.get("gPCMachineExtensionNames")),
            "user_extensions": _parse_cse_names(match.get("gPCUserExtensionNames")),
            "links": links,
        }
    finally:
        conn.unbind()


def inspect_gpo_settings(name: str) -> dict:
    safe = name.replace("'", "''")
    script = f"""
$gpoName = '{safe}'
$gpo = Get-GPO -Name $gpoName -ErrorAction Stop
$xml = [xml](Get-GPOReport -Guid $gpo.Id -ReportType Xml)
$settings = New-Object System.Collections.Generic.List[string]
foreach ($n in $xml.SelectNodes("//*[local-name()='Name']")) {{
    $p = $n.ParentNode
    if ($p -eq $null) {{ continue }}
    $ln = $p.LocalName
    if ($ln -in @('Policy','PreferenceSettings','Shortcut','DriveMapSettings','Printer','Registry','Folder','ScheduledTasks','Script')) {{
        $state = ''
        $st = $p['State']
        if ($st) {{ $state = [string]$st }}
        $val = ([string]$n.InnerText).Trim()
        if ($val -and $val.Length -lt 140) {{
            if ($state) {{ $settings.Add("$val ($state)") }} else {{ $settings.Add($val) }}
        }}
    }}
}}
$uniq = $settings | Select-Object -Unique | Select-Object -First 35
$perms = @()
try {{
    $perms = @(Get-GPPermission -Name $gpoName -All -ErrorAction SilentlyContinue | ForEach-Object {{
        "$($_.Trustee.Name)=$($_.Permission)"
    }} | Select-Object -First 12)
}} catch {{ }}

$compVersion = [int]($xml.GPO.Computer.VersionDirectory)
$userVersion = [int]($xml.GPO.User.VersionDirectory)
if ($uniq.Count -eq 0 -and $compVersion -eq 0 -and $userVersion -eq 0) {{
    $uniq = @("GPO VACÍA (No contiene ninguna configuración aplicada)")
}}

@{{
    name = $gpo.DisplayName
    status = [string]$gpo.GpoStatus
    computer = [string]$xml.GPO.Computer.Enabled
    user = [string]$xml.GPO.User.Enabled
    settings = @($uniq)
    filtering = @($perms)
}} | ConvertTo-Json -Compress -Depth 4
"""
    raw = run_on_dc(script, wait_s=40, capture=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw[:2500]}


def diagnose_gpo(name: str, *, with_settings: bool = True) -> dict:
    ldap = find_gpo_ldap(name)
    if not ldap:
        return {"error": f"No encontré la GPO '{name}' en el dominio."}
    result = dict(ldap)
    if with_settings:
        try:
            settings = inspect_gpo_settings(ldap["name"])
            result["dc_status"] = settings.get("status")
            result["computer_enabled"] = settings.get("computer")
            result["user_enabled"] = settings.get("user")
            result["settings"] = settings.get("settings") or settings.get("raw")
            result["security_filtering"] = settings.get("filtering")
        except Exception as exc:
            logger.warning("No se pudo leer el reporte de GPO %s: %s", name, exc)
            result["settings_error"] = str(exc)
    return result


def mentioned_gpos(text: str, known_names: list[str]) -> list[str]:
    blob = (text or "")
    hits = []
    for name in sorted({n for n in known_names if n}, key=len, reverse=True):
        if len(name) < 3:
            continue
        if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", blob, re.IGNORECASE):
            hits.append(name)
        if len(hits) >= 2:
            break
    return hits


def looks_like_inquiry(text: str) -> bool:
    return bool(_INQUIRY_RE.search(text or ""))
