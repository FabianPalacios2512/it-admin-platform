<#
.SYNOPSIS
    Extrae los datos de monitoreo de FortiGates desde Zabbix.
.DESCRIPTION
    Script en PowerShell que se autentica contra la API de Zabbix (JSON-RPC)
    y extrae los últimos valores de las métricas clave para dispositivos 
    en el grupo 'FortiGates' o que contienen 'Forti' en el nombre.
#>

param(
    [string]$ZabbixURL = "http://192.168.20.4/api_jsonrpc.php",
    [string]$ZabbixUser = "Admin",
    [string]$ZabbixPass = "zabbix",
    [string]$OutputFile = "fortigates_data.json"
)

Function Invoke-ZabbixAPI {
    param (
        [string]$Method,
        [Hashtable]$Params,
        [string]$AuthToken
    )
    
    $body = @{
        jsonrpc = "2.0"
        method = $Method
        params = $Params
        id = 1
    }

    if ($AuthToken) {
        $body.auth = $AuthToken
    }

    $jsonBody = $body | ConvertTo-Json -Depth 5 -Compress
    
    try {
        $response = Invoke-RestMethod -Uri $ZabbixURL -Method Post -Body $jsonBody -ContentType "application/json" -ErrorAction Stop
        if ($response.error) {
            Write-Error "Zabbix API Error: $($response.error.data)"
            return $null
        }
        return $response.result
    } catch {
        Write-Error "Failed to call Zabbix API: $_"
        return $null
    }
}

# 1. Login
$auth = Invoke-ZabbixAPI -Method "user.login" -Params @{ username = $ZabbixUser; password = $ZabbixPass }
if (-not $auth) { exit 1 }

# 2. Get FortiGate Hosts (By group name or host name wildcard)
$hostsParams = @{
    output = @("hostid", "name", "host", "available", "snmp_available", "status")
    selectInterfaces = @("ip")
    search = @{ name = "Forti" }
    searchByAny = $true
}
$hosts = Invoke-ZabbixAPI -Method "host.get" -Params $hostsParams -AuthToken $auth

if (-not $hosts) {
    Write-Host "No FortiGate hosts found."
    exit 0
}

# Extract Host IDs
$hostIds = $hosts | Select-Object -ExpandProperty hostid

# 3. Get Items for these hosts (CPU, Mem, Sessions, VPN, Traffic)
$itemsParams = @{
    output = @("itemid", "hostid", "name", "key_", "lastvalue", "lastclock")
    hostids = $hostIds
    search = @{ 
        key_ = @("system.cpu.util", "vm.memory.util", "fortignw.sessions", "vpn", "ipsec", "net.if.in", "net.if.out", "system.uptime", "fgsyssesscount", "fgvpntunupcount", "fgipsintrusionsblocked")
    }
    searchByAny = $true
}
$items = Invoke-ZabbixAPI -Method "item.get" -Params $itemsParams -AuthToken $auth

# 4. Get active triggers for these hosts
$triggersParams = @{
    output = @("triggerid", "priority")
    selectHosts = @("hostid")
    hostids = $hostIds
    filter = @{ value = 1; status = 0 } # value=1 means PROBLEM, status=0 means ENABLED
    monitored = $true
}
$activeTriggers = Invoke-ZabbixAPI -Method "trigger.get" -Params $triggersParams -AuthToken $auth

# Process and unify data
$finalData = @()

foreach ($h in $hosts) {
    $hid = $h.hostid
    $hostItems = $items | Where-Object { $_.hostid -eq $hid }

    # Variables for metrics
    $cpu = 0
    $ram = 0
    $sessions = 0
    $vpnUp = 0
    $vpnDown = 0
    $uptimeSeconds = 0
    $ipsBlocked = 0
    $interfaces = @{}

    foreach ($item in $hostItems) {
        $key = $item.key_.ToLower()
        $val = 0
        if ([double]::TryParse($item.lastvalue, [ref]$val)) {
            if ($key -like "*system.cpu.util*") { $cpu = [Math]::Round($val, 1) }
            elseif ($key -like "*vm.memory.util*") { $ram = [Math]::Round($val, 1) }
            elseif ($key -like "*system.uptime*") { $uptimeSeconds = $val }
            elseif ($key -match "fortignw.sessions|fgsyssesscount") { $sessions = $val }
            elseif ($key -match "fgipsintrusionsblocked") { $ipsBlocked = $val }
            elseif ($key -match "fgvpntunupcount") { $vpnUp = $val }
            elseif ($key -match "vpn|ipsec" -and $key -notmatch "fgvpntunupcount") {
                if ($key -match "status") {
                    if ($val -eq 1) { $vpnUp++ } else { $vpnDown++ }
                } else {
                    $vpnUp += $val
                }
            }
            elseif ($key -like "*net.if.in*") { 
                if ($item.name -match "Interface (.*?):") {
                    $ifName = $matches[1]
                    if (-not $interfaces.ContainsKey($ifName)) { $interfaces[$ifName] = @{ in_bps = 0; out_bps = 0; in_itemid = ""; out_itemid = "" } }
                    $interfaces[$ifName].in_bps += $val
                    $interfaces[$ifName].in_itemid = $item.itemid
                }
            }
            elseif ($key -like "*net.if.out*") { 
                if ($item.name -match "Interface (.*?):") {
                    $ifName = $matches[1]
                    if (-not $interfaces.ContainsKey($ifName)) { $interfaces[$ifName] = @{ in_bps = 0; out_bps = 0; in_itemid = ""; out_itemid = "" } }
                    $interfaces[$ifName].out_bps += $val
                    $interfaces[$ifName].out_itemid = $item.itemid
                }
            }
        }
    }

    $hostTriggers = if ($activeTriggers) { $activeTriggers | Where-Object { $_.hosts.hostid -contains $hid -or $_.hosts[0].hostid -eq $hid } } else { @() }
    $alertsCount = if ($hostTriggers) { @($hostTriggers).Count } else { 0 }
    $hasCriticalAlert = if ($hostTriggers) { @($hostTriggers | Where-Object { [int]$_.priority -ge 4 }).Count -gt 0 } else { $false }

    # Zabbix Availability: 1 = Available, 2 = Unavailable, 0 = Unknown (ZBX agent)
    # SNMP Availability: 1 = Available, 2 = Unavailable, 0 = Unknown
    $statusText = if ($h.available -eq '2' -or $h.snmp_available -eq '2' -or $hasCriticalAlert) { "Offline" } else { "Online" }

    # CRITICAL: Si el equipo está Offline, vaciamos las métricas. 
    # Zabbix guarda el 'lastvalue', pero si está apagado, esos datos están obsoletos (stale).
    if ($statusText -eq "Offline") {
        $cpu = 0
        $ram = 0
        $sessions = 0
        $vpnUp = 0
        $vpnDown = 0
        $uptimeSeconds = 0
        $ipsBlocked = 0
        $interfaces.Clear()
    }

    # Format Uptime
    $uptimeStr = "N/A"
    if ($uptimeSeconds -gt 0) {
        $ts = [timespan]::fromseconds($uptimeSeconds)
        if ($ts.Days -gt 0) {
            $uptimeStr = "Up $($ts.Days)d $($ts.Hours)h"
        } else {
            $uptimeStr = "Up $($ts.Hours)h $($ts.Minutes)m"
        }
    }

    $activeInterfaces = @()
    foreach ($ifKey in $interfaces.Keys) {
        $inVal = $interfaces[$ifKey].in_bps
        $outVal = $interfaces[$ifKey].out_bps
        if ($inVal -gt 0 -or $outVal -gt 0) {
            $activeInterfaces += @{ 
                name = $ifKey
                in_bps = $inVal
                out_bps = $outVal
                in_itemid = $interfaces[$ifKey].in_itemid
                out_itemid = $interfaces[$ifKey].out_itemid
            }
        }
    }

    $finalData += @{
        hostid = $hid
        hostname = $h.name
        ip = if ($h.interfaces) { $h.interfaces[0].ip } else { "N/A" }
        status = $statusText
        metrics = @{
            cpu = $cpu
            ram = $ram
            active_sessions = $sessions
            uptime_str = $uptimeStr
            ips_blocked = $ipsBlocked
            vpn_tunnels_up = $vpnUp
            vpn = @{
                up = $vpnUp
                down = $vpnDown
            }
            interfaces = $activeInterfaces
            alerts = $alertsCount
        }
    }
}

# 5. Get History for active interfaces
$historyItemIds = @()
foreach ($h in $finalData) {
    foreach ($iface in $h.metrics.interfaces) {
        if ($iface.in_itemid) { $historyItemIds += $iface.in_itemid }
        if ($iface.out_itemid) { $historyItemIds += $iface.out_itemid }
    }
}

if ($historyItemIds.Count -gt 0) {
    # Unix timestamp for 60 minutes ago
    $timeFrom = [int][DateTimeOffset]::Now.AddMinutes(-60).ToUnixTimeSeconds()
    $historyParams = @{
        output = @("itemid", "clock", "value")
        history = 3 # 3 = numeric unsigned (used for bps)
        itemids = $historyItemIds
        time_from = $timeFrom
        sortfield = "clock"
        sortorder = "ASC"
    }
    $historyRaw = Invoke-ZabbixAPI -Method "history.get" -Params $historyParams -AuthToken $auth
    
    # Group by itemid
    $historyLookup = @{}
    if ($historyRaw) {
        foreach ($row in $historyRaw) {
            if (-not $historyLookup.ContainsKey($row.itemid)) { $historyLookup[$row.itemid] = @() }
            $historyLookup[$row.itemid] += @{ clock = $row.clock; value = $row.value }
        }
    }

    # Attach history back to each interface
    foreach ($h in $finalData) {
        foreach ($iface in $h.metrics.interfaces) {
            $ifaceHistory = @()
            $inHist = if ($historyLookup.ContainsKey($iface.in_itemid)) { $historyLookup[$iface.in_itemid] } else { @() }
            $outHist = if ($historyLookup.ContainsKey($iface.out_itemid)) { $historyLookup[$iface.out_itemid] } else { @() }
            
            # Use the length of the longest array to build the timeline
            $maxCount = [Math]::Max($inHist.Count, $outHist.Count)
            
            for ($i = 0; $i -lt $maxCount; $i++) {
                $inObj = if ($i -lt $inHist.Count) { $inHist[$i] } else { $null }
                $outObj = if ($i -lt $outHist.Count) { $outHist[$i] } else { $null }
                
                $clockToUse = if ($inObj) { $inObj.clock } elseif ($outObj) { $outObj.clock } else { 0 }
                if ($clockToUse -eq 0) { continue }
                
                $inVal = if ($inObj) { [double]$inObj.value / 1000 } else { 0 } # Convert bps to Kbps directly
                $outVal = if ($outObj) { [double]$outObj.value / 1000 } else { 0 }
                
                # Format time
                $dt = [DateTimeOffset]::FromUnixTimeSeconds([long]$clockToUse).ToLocalTime()
                $timeStr = $dt.ToString("HH:mm")
                
                $ifaceHistory += @{ time = $timeStr; in = [Math]::Round($inVal, 1); out = [Math]::Round($outVal, 1) }
            }
            $iface.history = $ifaceHistory
        }
    }
}

ConvertTo-Json -InputObject $finalData -Depth 10 | Out-File -FilePath $OutputFile -Encoding utf8
Write-Host "Success: Data exported to $OutputFile"
