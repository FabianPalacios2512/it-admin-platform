<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const healthStats = ref({
  total_users: 0,
  enabled_users: 0,
  disabled_users: 0,
  password_never_expires: 0,
  inactive_users_90d: 0,
  locked_users: 0,
  new_computers: 0,
})

const syncStatus = ref(null)
const securityRadar = ref([])
const recentEvents = ref([])
const lockedAccountsList = ref([])
const zabbixHosts = ref([])
const lastFetchAt = ref(null)

let pollInterval = null

const wifiStats = ref({
  totalAps: 0,
  offlineAps: 0,
  totalClients: 0,
  avgExperience: 0
})

const fetchEvents = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/audit', { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      recentEvents.value = data.slice(0, 15).map(event => {
        const d = new Date(event.timestamp + 'Z')
        return {
          id: event.id,
          rawDate: d,
          time: d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          date: d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' }),
          type: event.status === 'Error' ? 'error' : event.status === 'Pendiente' ? 'warn' : 'info',
          user: event.username,
          module: event.target?.includes('AD') ? 'Active Directory' : (event.target?.includes('Print') ? 'Impresoras' : 'Sistema'),
          action: event.action,
          target: event.target,
          status: event.status
        }
      })
    }
  } catch (e) {}
}

const fetchHealthStats = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/accounts/health-stats', { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) healthStats.value = await res.json()
  } catch (e) {}
}

const fetchGraphData = async () => {
  const token = localStorage.getItem('access_token')
  const headers = { 'Authorization': `Bearer ${token}` }
  try {
    const [resSync, resSec] = await Promise.all([
      fetch('/api/v1/graph/sync-status', { headers }).catch(() => ({ok: false})),
      fetch('/api/v1/graph/security-radar', { headers }).catch(() => ({ok: false}))
    ])

    if (resSync.ok) {
      const syncData = await resSync.json()
      syncStatus.value = syncData.onPremisesLastSyncDateTime
    }
    if (resSec.ok) securityRadar.value = await resSec.json()
  } catch (e) {}
}

const fetchLockedAccounts = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/accounts/locked', { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      lockedAccountsList.value = await res.json()
    }
  } catch (e) {}
}

const fetchWifiStats = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/wifi/aps?site=default', { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      const result = await res.json()
      const aps = result.data || []

      let clients = 0
      let totalExp = 0
      let expCount = 0
      let offline = 0

      aps.forEach(ap => {
        clients += ap.clients_count || 0
        if (ap.status !== 'online') {
          offline++
        } else if (ap.clients_count > 0) {
          totalExp += ap.satisfaction || 0
          expCount++
        }
      })

      wifiStats.value = {
        totalAps: aps.length,
        offlineAps: offline,
        totalClients: clients,
        avgExperience: expCount > 0 ? Math.round(totalExp / expCount) : 0
      }
    }
  } catch (e) {}
}

const fetchZabbixData = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/zabbix/hosts', { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      zabbixHosts.value = data.data || []
    }
  } catch (e) {}
}

onMounted(async () => {
  const fetchAll = async () => {
    await Promise.all([
      fetchEvents(), fetchHealthStats(), fetchGraphData(),
      fetchLockedAccounts(), fetchWifiStats(), fetchZabbixData()
    ])
    lastFetchAt.value = Date.now()
  }

  await fetchAll()
  pollInterval = setInterval(fetchAll, 15000)
})

onUnmounted(() => { if (pollInterval) clearInterval(pollInterval) })

const combinedLogs = computed(() => {
  const auditLogs = recentEvents.value.map(log => ({
    id: `audit-${log.id}`,
    isSecurity: false,
    user: log.user,
    module: log.module,
    action: log.action,
    target: log.target,
    severity: log.type,
    statusText: log.status,
    time: log.time,
    date: log.date,
    rawDate: log.rawDate
  }))

  const radarLogs = securityRadar.value.map(log => {
      const d = new Date(log.createdDateTime)
      return {
        id: `radar-${log.id}`,
        isSecurity: true,
        user: log.userDisplayName || log.userPrincipalName,
        module: 'Entra ID',
        action: 'Sign-in Blocked',
        target: log.ipAddress || '-',
        severity: log.status?.errorCode === 50126 ? 'warn' : 'error',
        statusText: 'Bloqueado',
        time: d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        date: d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' }),
        rawDate: d
      }
  })
  return [...radarLogs, ...auditLogs].sort((a, b) => b.rawDate - a.rawDate)
})

const showUnlockModal = ref(false)
const unlockTargetUser = ref(null)
const unlockLoading = ref(false)
const unlockError = ref(null)

const handleUnlock = (username) => {
  unlockTargetUser.value = username
  unlockError.value = null
  showUnlockModal.value = true
}

const executeUnlock = async () => {
  const username = unlockTargetUser.value
  unlockLoading.value = true
  unlockError.value = null
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/accounts/unlock', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    })
    if (res.ok) {
      lockedAccountsList.value = lockedAccountsList.value.filter(u => u.username !== username)
      healthStats.value.locked_users = Math.max(0, healthStats.value.locked_users - 1)
      showUnlockModal.value = false
    } else {
      const data = await res.json().catch(() => ({}))
      unlockError.value = data.detail || data.message || "Error al desbloquear la cuenta."
    }
  } catch (e) {
    unlockError.value = "Error de red al intentar desbloquear."
  } finally {
    unlockLoading.value = false
  }
}

const firewalls = computed(() => {
  return zabbixHosts.value.filter(h => h.hostname.toUpperCase().includes('FGT-') || h.hostname.toUpperCase().includes('FORTIGATE'))
})

const firewallsOffline = computed(() => {
  return firewalls.value.filter(h => h.status === 'Offline')
})

const servers = computed(() => {
  return zabbixHosts.value.filter(h => !h.hostname.toUpperCase().includes('FGT-') && !h.hostname.toUpperCase().includes('FORTIGATE'))
})

const serversOnline = computed(() => servers.value.filter(h => h.status !== 'Offline'))

const serverAlerts = computed(() => {
  return servers.value.filter(h => h.status === 'Offline' || h.status === 'Warning' || h.cpu > 90 || h.ram > 95)
})

const serversNeedingWatch = computed(() => {
  return servers.value.filter(h =>
    h.status === 'Offline' || h.status === 'Warning' || h.cpu >= 80 || h.ram >= 80
  )
})

const topConsumers = computed(() => {
  return [...servers.value]
    .sort((a, b) => (Number(b.ram) || 0) - (Number(a.ram) || 0))
    .slice(0, 6)
})

const syncMeta = computed(() => {
  if (!syncStatus.value) return { label: 'Sin datos', tone: 'info', detail: 'Esperando reporte AD Connect', ageMin: null }
  const d = new Date(syncStatus.value)
  if (Number.isNaN(d.getTime())) return { label: 'Sin datos', tone: 'info', detail: 'Esperando reporte AD Connect', ageMin: null }
  const ageMin = Math.max(0, Math.round((Date.now() - d.getTime()) / 60000))
  const timeStr = d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
  const dateStr = d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit' })
  if (ageMin > 60) return { label: 'Retrasada', tone: 'warn', detail: `${dateStr} ${timeStr}`, ageMin }
  return { label: 'Sincronizado', tone: 'ok', detail: `${dateStr} ${timeStr}`, ageMin }
})

const identityTone = computed(() => healthStats.value.locked_users > 0 ? 'warn' : 'ok')
const serversTone = computed(() => {
  if (servers.value.some(s => s.status === 'Offline')) return 'crit'
  if (serversNeedingWatch.value.length) return 'warn'
  return servers.value.length ? 'ok' : 'info'
})
const networkTone = computed(() => wifiStats.value.offlineAps > 0 ? 'warn' : (wifiStats.value.totalAps ? 'ok' : 'info'))
const firewallTone = computed(() => firewallsOffline.value.length ? 'crit' : (firewalls.value.length ? 'ok' : 'info'))
const securityTone = computed(() => securityRadar.value.length ? 'warn' : 'ok')

const overallTone = computed(() => {
  const tones = [serversTone.value, firewallTone.value, networkTone.value, identityTone.value, securityTone.value, syncMeta.value.tone]
  if (tones.includes('crit')) return 'crit'
  if (tones.includes('warn')) return 'warn'
  return 'ok'
})

const overallLabel = computed(() => {
  if (overallTone.value === 'crit') return 'Atención requerida'
  if (overallTone.value === 'warn') return 'Excepciones activas'
  return 'Operativa'
})

const servicesAvailablePct = computed(() => {
  const total = servers.value.length + firewalls.value.length
  if (!total) return null
  const down = servers.value.filter(s => s.status === 'Offline').length + firewallsOffline.value.length
  return Math.round(((total - down) / total) * 100)
})

const parseDate = (dateStr) => {
  if (!dateStr) return null;
  
  const parts = dateStr.split(/[\s/:]+/);
  if (parts.length >= 3 && parts.length <= 6) {
    const [day, month, year, h, m, s] = parts;
    if (year && year.length === 4) {
      // El backend de AD entrega los eventos en UTC sin la 'Z'. 
      // Si la parseamos como local, queda en el futuro y da "hace unos segundos".
      const d = new Date(`${year}-${month}-${day}T${h||'00'}:${m||'00'}:${s||'00'}Z`);
      if (!Number.isNaN(d.getTime())) return d;
    }
  }
  
  let d = new Date(dateStr);
  if (!Number.isNaN(d.getTime())) return d;
  
  return null;
}

const timeAgo = (dateStr) => {
  const d = parseDate(dateStr);
  if (!d) return { text: '', isRecent: false, timestamp: 0 };
  
  const diffMs = Date.now() - d.getTime();
  const diffSec = Math.max(0, Math.round(diffMs / 1000));
  const diffMin = Math.round(diffSec / 60);
  const diffHour = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHour / 24);

  let text = '';
  if (diffMin < 1) text = 'hace unos segundos';
  else if (diffMin < 60) text = `hace ${diffMin} min`;
  else if (diffHour < 24) text = `hace ${diffHour} hora${diffHour > 1 ? 's' : ''}`;
  else text = `hace ${diffDay} día${diffDay > 1 ? 's' : ''}`;

  return { text, isRecent: diffHour < 1, timestamp: d.getTime() };
}

const attentionQueue = computed(() => {
  const items = []
  const lockedCount = lockedAccountsList.value.length;

  lockedAccountsList.value.forEach((acc) => {
    const t = timeAgo(acc.lockoutTime);
    items.push({
      id: `lock-${acc.username}`,
      tone: 'crit',
      kind: 'Identidad',
      title: acc.fullName || acc.username,
      meta: acc.username,
      timeText: t.text,
      isRecent: t.isRecent,
      timestamp: t.timestamp || 0,
      status: 'LOCKED',
      route: '/cuentas?estado=bloqueados',
      unlock: acc.username
    })
  })

  if (lockedCount <= 3) {
    servers.value.forEach((srv) => {
      const offline = srv.status === 'Offline'
      const hot = Number(srv.cpu) >= 80 || Number(srv.ram) >= 80 || srv.status === 'Warning'
      if (!offline && !hot) return
      const crit = offline || Number(srv.cpu) > 90 || Number(srv.ram) > 95
      items.push({
        id: `srv-${srv.hostid}`,
        tone: crit ? 'crit' : 'warn',
        kind: 'Servidor',
        title: srv.hostname,
        meta: `${srv.ip || '—'}`,
        timeText: '',
        isRecent: false,
        timestamp: 0,
        cpu: Number(srv.cpu),
        ram: Number(srv.ram),
        status: offline ? 'OFFLINE' : (Number(srv.ram) >= 80 || Number(srv.cpu) >= 80 ? 'WARNING' : srv.status?.toUpperCase()),
        route: '/monitoring-zabbix',
        unlock: null
      })
    })

    firewallsOffline.value.forEach((fw) => {
      items.push({
        id: `fw-${fw.hostid}`,
        tone: 'crit',
        kind: 'Firewall',
        title: fw.hostname,
        meta: fw.ip || 'Perímetro',
        timeText: '',
        isRecent: false,
        timestamp: 0,
        status: 'OFFLINE',
        route: '/monitoring-zabbix',
        unlock: null
      })
    })

    if (wifiStats.value.offlineAps > 0) {
      items.push({
        id: 'wifi-offline',
        tone: 'warn',
        kind: 'Wi-Fi',
        title: `${wifiStats.value.offlineAps} AP fuera de línea`,
        meta: `${wifiStats.value.totalAps} access points · ${wifiStats.value.totalClients} clientes`,
        timeText: '',
        isRecent: false,
        timestamp: 0,
        status: 'WARNING',
        route: '/wifi',
        unlock: null
      })
    }
  }

  items.sort((a, b) => {
    if (a.timestamp !== b.timestamp) {
      return b.timestamp - a.timestamp;
    }
    const rank = { crit: 0, warn: 1 }
    return rank[a.tone] - rank[b.tone]
  })

  return items
})

const systems = computed(() => [
  {
    name: 'Active Directory',
    icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z',
    tone: identityTone.value,
    status: healthStats.value.locked_users > 0 ? 'WARNING' : 'OPERATIVA',
    detail: healthStats.value.locked_users > 0
      ? `${healthStats.value.locked_users} cuenta(s) bloqueada(s)`
      : 'Sin bloqueos',
    extra: `${healthStats.value.enabled_users}/${healthStats.value.total_users || 0} habilitadas · ${healthStats.value.inactive_users_90d} inactivas 90d`,
    route: '/cuentas'
  },
  {
    name: 'Servidores',
    icon: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01',
    tone: serversTone.value,
    status: serversTone.value === 'crit' ? 'CRITICAL' : serversTone.value === 'warn' ? 'WARNING' : 'OPERATIVA',
    detail: `${serversOnline.value.length}/${servers.value.length || 0} en línea`,
    extra: `${serversNeedingWatch.value.length} requieren atención`,
    route: '/monitoring-zabbix'
  },
  {
    name: 'Wi-Fi',
    icon: 'M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M4.222 9.222a16.97 16.97 0 0115.556 0',
    tone: networkTone.value,
    status: wifiStats.value.offlineAps > 0 ? 'WARNING' : 'OPERATIVA',
    detail: `${wifiStats.value.totalAps - wifiStats.value.offlineAps}/${wifiStats.value.totalAps || 0} AP en línea`,
    extra: `${wifiStats.value.totalClients} clientes`,
    route: '/wifi'
  },
  {
    name: 'Entra ID',
    icon: 'M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z',
    tone: syncMeta.value.tone,
    status: syncMeta.value.label.toUpperCase(),
    detail: syncMeta.value.ageMin != null ? `Última sync ${syncMeta.value.detail}` : syncMeta.value.detail,
    extra: syncMeta.value.ageMin != null ? `hace ${syncMeta.value.ageMin} min` : '—',
    route: '/seguridad'
  },
  {
    name: 'Firewall',
    icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
    tone: firewallTone.value,
    status: firewallTone.value === 'crit' ? 'OFFLINE' : firewalls.value.length ? 'OPERATIVA' : 'SIN DATO',
    detail: `${firewalls.value.length - firewallsOffline.value.length}/${firewalls.value.length || 0} operativos`,
    extra: firewallsOffline.value.length ? `${firewallsOffline.value.length} caídos` : 'Perímetro estable',
    route: '/monitoring-zabbix'
  },
  {
    name: 'Seguridad',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
    tone: securityTone.value,
    status: securityRadar.value.length ? 'WARNING' : 'SIN INCIDENTES',
    detail: securityRadar.value.length ? `${securityRadar.value.length} sign-in bloqueado(s)` : 'Sin incidentes críticos',
    extra: 'Entra ID · radar',
    route: '/seguridad'
  }
])

const toneDot = (tone) => ({
  ok: 'bg-blue-500',
  warn: 'bg-amber-500',
  crit: 'bg-red-500',
  info: 'bg-slate-400'
}[tone] || 'bg-slate-400')

const toneText = (tone) => ({
  ok: 'text-slate-700',
  warn: 'text-amber-700',
  crit: 'text-red-700',
  info: 'text-slate-500'
}[tone] || 'text-slate-500')

const toneBadge = (tone) => {
  const color = {
    ok: 'text-slate-400',
    warn: 'text-amber-500',
    crit: 'text-red-500',
    info: 'text-slate-400'
  }[tone] || 'text-slate-400';
  return `${color} font-bold text-[10px] tracking-widest uppercase`;
}

const toneIndicator = (tone) => {
  return {
    ok: 'bg-blue-400',
    warn: 'bg-amber-400 animate-pulse',
    crit: 'bg-red-400 animate-pulse',
    info: 'bg-slate-300'
  }[tone] || 'bg-slate-300'
}

const barColor = (val) => {
  if (val >= 90) return 'bg-red-400'
  if (val >= 80) return 'bg-amber-400'
  return 'bg-slate-200'
}

const formatPct = (val) => {
  const n = Number(val)
  return Number.isFinite(n) ? `${n.toFixed(0)}%` : '—'
}

const go = (path) => router.push(path)
</script>

<template>
  <div class="font-sans text-slate-800 min-h-full flex flex-col gap-4">

    <!-- Page title -->
    <div class="flex items-end justify-between gap-4 shrink-0">
      <div>
        <h1 class="text-xl font-semibold text-slate-900 tracking-tight leading-none">Centro de Control</h1>
        <p class="text-[11px] text-slate-500 mt-1 uppercase tracking-wider">
          Operaciones · Identidad · Servidores · Red · Seguridad
        </p>
      </div>
      <div class="flex items-center gap-3 text-[11px] shrink-0">
        <span class="font-mono text-slate-400">
          {{ lastFetchAt ? new Date(lastFetchAt).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—' }}
        </span>
        <span class="inline-flex items-center gap-2 font-semibold uppercase tracking-wider" :class="toneBadge(overallTone)">
          {{ overallLabel }}
        </span>
      </div>
    </div>

    <!-- NIVEL 1: Estado general -->
    <section class="bg-white rounded-xl shadow-[0_2px_8px_rgb(0,0,0,0.04)] border border-slate-100">
      <div class="px-6 py-5 flex items-center justify-between">
        <h2 class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Estado general de infraestructura</h2>
        <span class="text-[11px] text-slate-400 font-mono">
          {{ servicesAvailablePct != null ? servicesAvailablePct + '% servicios disponibles' : 'sin telemetría de hosts' }}
        </span>
      </div>
      <div class="grid grid-cols-2 xl:grid-cols-6 relative pb-4 px-2">
        <button type="button" class="group text-left px-4 py-3 hover:bg-slate-50/50 rounded-lg transition-all duration-300 flex flex-col justify-between bg-white" @click="go('/monitoring-zabbix')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                Infraestructura
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full" :class="toneIndicator(overallTone)"></div>
              <div class="text-[14px] font-semibold text-slate-900">{{ overallLabel }}</div>
            </div>
            <div class="text-[11px] text-slate-500 mt-1">{{ servicesAvailablePct != null ? servicesAvailablePct + '% de disponibilidad global' : 'Sin telemetría' }}</div>
          </div>
        </button>

        <button type="button" class="group text-left px-4 py-3 hover:bg-slate-50/50 rounded-lg transition-all duration-300 flex flex-col justify-between bg-white" @click="go('/cuentas')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                Identidad
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full" :class="toneIndicator(identityTone)"></div>
              <div class="text-[14px] font-semibold text-slate-900">{{ healthStats.locked_users > 0 ? 'Excepciones' : 'Saludable' }}</div>
            </div>
            <div class="text-[11px] text-slate-500 mt-1">{{ healthStats.enabled_users }}/{{ healthStats.total_users || 0 }} cuentas activas</div>
          </div>
        </button>

        <button type="button" class="group text-left px-4 py-3 hover:bg-slate-50/50 rounded-lg transition-all duration-300 flex flex-col justify-between bg-white" @click="go('/monitoring-zabbix')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" /></svg>
                Servidores
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full" :class="toneIndicator(serversTone)"></div>
              <div class="text-[14px] font-semibold text-slate-900">{{ serversTone === 'ok' ? 'Estables' : serversTone === 'crit' ? 'Crítico' : 'Atención' }}</div>
            </div>
            <div class="text-[11px] text-slate-500 mt-1">{{ serversOnline.length }}/{{ servers.length || 0 }} en línea · {{ serversNeedingWatch.length }} alertas</div>
          </div>
        </button>

        <button type="button" class="group text-left px-4 py-3 hover:bg-slate-50/50 rounded-lg transition-all duration-300 flex flex-col justify-between bg-white" @click="go('/wifi')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M4.222 9.222a16.97 16.97 0 0115.556 0" /></svg>
                Red Local
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full" :class="toneIndicator(networkTone)"></div>
              <div class="text-[14px] font-semibold text-slate-900">{{ wifiStats.offlineAps ? 'Fallas en APs' : 'Operativa' }}</div>
            </div>
            <div class="text-[11px] text-slate-500 mt-1">{{ wifiStats.totalAps - wifiStats.offlineAps }}/{{ wifiStats.totalAps || 0 }} AP online · {{ wifiStats.totalClients }} clientes</div>
          </div>
        </button>

        <button type="button" class="group text-left px-4 py-3 hover:bg-slate-50/50 rounded-lg transition-all duration-300 flex flex-col justify-between bg-white" @click="go('/seguridad')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                Seguridad
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full" :class="toneIndicator(securityTone)"></div>
              <div class="text-[14px] font-semibold text-slate-900">{{ securityRadar.length ? 'Incidentes detectados' : 'Sin incidentes' }}</div>
            </div>
            <div class="text-[11px] text-slate-500 mt-1">{{ securityRadar.length }} sign-in bloqueados recientemente</div>
          </div>
        </button>

        <button type="button" class="group text-left px-4 py-3 hover:bg-slate-50/50 rounded-lg transition-all duration-300 flex flex-col justify-between bg-white" @click="go('/seguridad')">
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" /></svg>
                Entra ID
              </div>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full" :class="toneIndicator(syncMeta.tone)"></div>
              <div class="text-[14px] font-semibold text-slate-900">{{ syncMeta.label }}</div>
            </div>
            <div class="text-[11px] text-slate-500 mt-1 truncate">{{ syncMeta.detail }}</div>
          </div>
        </button>
      </div>
    </section>

    <!-- NIVEL 2: Atención + Sistemas -->
    <div class="grid grid-cols-1 xl:grid-cols-5 gap-4 min-h-0">

      <section class="xl:col-span-3 bg-white rounded-xl shadow-[0_2px_8px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col min-h-[280px] max-h-[360px]">
        <div class="px-6 py-5 flex items-center justify-between shrink-0">
          <h2 class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Excepciones de infraestructura</h2>
          <span class="font-mono text-[11px] tabular-nums text-slate-400">
            {{ attentionQueue.length }}
          </span>
        </div>
        <div v-if="attentionQueue.length === 0" class="flex-1 flex items-center px-6 pb-6 text-[13px] text-slate-500">
          Sin excepciones activas. Identidad, servidores y perímetro estables.
        </div>
        <div v-else class="flex-1 overflow-y-auto px-4 pb-4 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <div
            v-for="item in attentionQueue.slice(0, 5)"
            :key="item.id"
            class="group flex items-center gap-4 px-4 py-4 rounded-lg hover:bg-slate-50/50 cursor-pointer transition-colors mb-1"
            @click="go(item.route)"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between mb-1.5">
                <div class="flex items-center gap-2.5">
                  <span class="text-[10px] font-bold uppercase tracking-wider text-slate-500">{{ item.kind }}</span>
                  <span class="w-1 h-1 rounded-full bg-slate-300"></span>
                  <span class="text-[11px] font-mono text-slate-400">{{ item.meta }}</span>
                  <template v-if="item.timeText">
                    <span class="w-1 h-1 rounded-full bg-slate-300"></span>
                    <span class="text-[11px]" :class="item.isRecent ? 'text-red-500 font-medium' : 'text-slate-400'">{{ item.timeText }}</span>
                  </template>
                </div>
                <span v-if="item.kind !== 'Identidad'" :class="toneBadge(item.tone)">{{ item.status }}</span>
              </div>
              
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <span class="text-[14px] font-semibold text-slate-900 truncate">{{ item.title }}</span>
                  <span v-if="item.kind === 'Identidad'" class="bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 rounded-md text-[10px] font-semibold tracking-wider uppercase">LOCKED</span>
                </div>
                
                <button
                  v-if="item.unlock"
                  type="button"
                  class="shrink-0 px-3 py-1 text-[11px] font-medium border border-red-200 rounded-md bg-white hover:bg-red-50 text-red-700 transition-all"
                  @click.stop="handleUnlock(item.unlock)"
                >
                  Desbloquear
                </button>
              </div>

              <!-- Mini bars for Servers -->
              <div v-if="item.cpu !== undefined" class="mt-3 flex items-center gap-4">
                <div class="flex-1 flex items-center gap-2">
                  <span class="text-[10px] font-mono text-slate-500 w-10 tabular-nums">CPU {{ formatPct(item.cpu) }}</span>
                  <div class="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div class="h-full" :class="barColor(item.cpu)" :style="{ width: Math.min(100, item.cpu || 0) + '%' }"></div>
                  </div>
                </div>
                <div class="flex-1 flex items-center gap-2">
                  <span class="text-[10px] font-mono text-slate-500 w-10 tabular-nums">RAM {{ formatPct(item.ram) }}</span>
                  <div class="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div class="h-full" :class="barColor(item.ram)" :style="{ width: Math.min(100, item.ram || 0) + '%' }"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Ghost Button -->
          <div v-if="attentionQueue.length > 5" class="px-2 mt-2">
            <button
              type="button"
              class="w-full py-2.5 rounded-lg border border-transparent text-[12px] font-medium text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-all"
              @click="go('/cuentas')"
            >
              Ver todas las excepciones ({{ attentionQueue.length - 5 }})
            </button>
          </div>
        </div>
      </section>

      <section class="xl:col-span-2 bg-white rounded-xl shadow-[0_2px_8px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col min-h-[280px] max-h-[360px]">
        <div class="px-6 py-5 flex items-center justify-between shrink-0">
          <h2 class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Estado de sistemas</h2>
        </div>
        <div class="flex-1 overflow-y-auto px-4 pb-4 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <button
            v-for="sys in systems"
            :key="sys.name"
            type="button"
            class="group w-full text-left px-4 py-3 rounded-lg hover:bg-slate-50/50 flex items-start gap-3 transition-colors mb-1"
            @click="go(sys.route)"
          >
            <svg class="w-4 h-4 shrink-0 text-slate-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" :d="sys.icon" />
            </svg>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-2 mb-0.5">
                <span class="text-[13px] font-semibold text-slate-900">{{ sys.name }}</span>
                <span :class="toneBadge(sys.tone)">{{ sys.status }}</span>
              </div>
              <div class="text-[11px] text-slate-600 mb-0.5">{{ sys.detail }}</div>
              <div class="text-[10px] font-mono text-slate-400">{{ sys.extra }}</div>
            </div>
          </button>
        </div>
      </section>
    </div>

    <!-- NIVEL 3: Consumo -->
    <section class="bg-white rounded-xl shadow-[0_2px_8px_rgb(0,0,0,0.04)] border border-slate-100 pb-2">
      <div class="px-6 py-5 flex items-center justify-between">
        <h2 class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Salud de servidores</h2>
        <button type="button" class="text-[11px] font-medium text-blue-600 hover:text-blue-700 transition-colors" @click="go('/monitoring-zabbix')">Ver todos</button>
      </div>
      <div class="overflow-x-auto px-2">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Host</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">IP</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Estado</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider w-44">CPU</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider w-44">RAM</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="srv in topConsumers"
              :key="srv.hostid"
              class="hover:bg-slate-50/50 cursor-pointer rounded-lg transition-colors"
              @click="go('/monitoring-zabbix')"
            >
              <td class="px-4 py-3 whitespace-nowrap rounded-l-lg">
                <div class="flex items-center gap-2.5">
                  <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" /></svg>
                  <span class="text-[13px] font-semibold text-slate-900">{{ srv.hostname }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-[11px] font-mono text-slate-500">{{ srv.ip || '—' }}</td>
              <td class="px-4 py-3">
                <span :class="srv.status === 'Offline' ? toneBadge('crit') : (srv.status === 'Warning' || srv.ram >= 80 || srv.cpu >= 80 ? toneBadge('warn') : toneBadge('ok'))">
                  {{ srv.status === 'Offline' ? 'OFFLINE' : (srv.ram >= 80 || srv.cpu >= 80 || srv.status === 'Warning' ? 'WARNING' : 'OPERATIVA') }}
                </span>
              </td>
              <td class="px-4 py-3">
                <div class="flex items-center gap-2.5">
                  <span class="w-10 text-[11px] font-mono tabular-nums text-slate-700">{{ formatPct(srv.cpu) }}</span>
                  <div class="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div class="h-full transition-all duration-500" :class="barColor(srv.cpu)" :style="{ width: Math.min(100, Number(srv.cpu) || 0) + '%' }"></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 rounded-r-lg">
                <div class="flex items-center gap-2.5">
                  <span class="w-10 text-[11px] font-mono tabular-nums text-slate-700">{{ formatPct(srv.ram) }}</span>
                  <div class="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                    <div class="h-full transition-all duration-500" :class="barColor(srv.ram)" :style="{ width: Math.min(100, Number(srv.ram) || 0) + '%' }"></div>
                  </div>
                </div>
              </td>
            </tr>
            <tr v-if="topConsumers.length === 0">
              <td colspan="5" class="px-4 py-8 text-center text-[12px] text-slate-400">Sin hosts de Zabbix en este momento.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- NIVEL 4: Auditoría -->
    <section class="bg-white rounded-xl shadow-[0_2px_8px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col min-h-[240px] pb-2">
      <div class="px-6 py-5 flex items-center justify-between">
        <h2 class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Actividad reciente</h2>
        <button type="button" class="text-[11px] font-medium text-blue-600 hover:text-blue-700" @click="go('/auditoria')">Registro completo</button>
      </div>
      <div class="overflow-x-auto px-2">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider whitespace-nowrap">Fecha / Hora</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Usuario</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Módulo</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Acción</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Target</th>
              <th class="px-4 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider text-right">Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="log in combinedLogs"
              :key="log.id"
              class="hover:bg-slate-50/50 cursor-pointer rounded-lg transition-colors"
              @click="go(log.isSecurity ? '/seguridad' : '/auditoria')"
            >
              <td class="px-4 py-3 whitespace-nowrap rounded-l-lg">
                <span class="text-[12px] font-mono text-slate-600">{{ log.date }}</span>
                <span class="text-[11px] font-mono text-slate-400 ml-2">{{ log.time }}</span>
              </td>
              <td class="px-4 py-3 text-[12px] font-medium text-slate-800 truncate max-w-[160px]" :title="log.user">{{ log.user }}</td>
              <td class="px-4 py-3 text-[11px] text-slate-500 uppercase tracking-wider whitespace-nowrap">{{ log.module || 'Sistema' }}</td>
              <td class="px-4 py-3 text-[12px] text-slate-800">{{ log.action }}</td>
              <td class="px-4 py-3 text-[11px] font-mono text-slate-500 truncate max-w-[240px]" :title="log.target">{{ log.target }}</td>
              <td class="px-4 py-3 text-right rounded-r-lg">
                <span class="text-[10px] font-semibold uppercase tracking-wider"
                      :class="log.severity === 'info' ? 'text-slate-600' : log.severity === 'error' ? 'text-red-700' : 'text-amber-700'">
                  {{ log.statusText || (log.severity === 'info' ? 'Éxito' : log.severity === 'error' ? 'Error' : 'Advertencia') }}
                </span>
              </td>
            </tr>
            <tr v-if="combinedLogs.length === 0">
              <td colspan="6" class="px-4 py-8 text-center text-[12px] text-slate-400">Sin eventos recientes.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Modal Unlock Confirmation -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showUnlockModal" class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="showUnlockModal = false">
          <div class="bg-white rounded-xl shadow-2xl w-[400px] max-w-[90vw] p-6 border border-slate-100">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-[15px] font-bold text-slate-900">Desbloquear Cuenta</h3>
              <button @click="showUnlockModal = false" class="text-slate-400 hover:text-slate-600 transition-colors p-1 rounded-md hover:bg-slate-100">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            
            <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-5 flex items-start gap-3">
              <svg class="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
              <div>
                <p class="text-[13px] font-medium text-slate-800 mb-1">Confirmación requerida</p>
                <p class="text-[12px] text-slate-600 leading-relaxed">¿Estás seguro de desbloquear la cuenta de <span class="font-bold">{{ unlockTargetUser }}</span> en Active Directory?</p>
              </div>
            </div>

            <div v-if="unlockError" class="mb-4 p-3 bg-red-50 text-red-700 text-[12px] rounded border border-red-200">
              {{ unlockError }}
            </div>

            <div class="flex justify-end gap-2">
              <button @click="showUnlockModal = false" class="px-4 py-2 text-[12px] font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors">Cancelar</button>
              <button @click="executeUnlock" :disabled="unlockLoading" class="px-4 py-2 text-[12px] font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm">
                <span v-if="unlockLoading" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
                {{ unlockLoading ? 'Procesando...' : 'Desbloquear' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>
