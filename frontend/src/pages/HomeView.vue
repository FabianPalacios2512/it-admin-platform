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
let pollInterval = null

const lockedAccountsList = ref([])
const wifiStats = ref({
  totalAps: 0,
  offlineAps: 0,
  totalClients: 0,
  avgExperience: 0
})

const printerStatus = ref({
  spoolerOk: true,
  jammed: 0
})

onMounted(async () => {
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
            time: d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }),
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
  
  await Promise.all([fetchEvents(), fetchHealthStats(), fetchGraphData(), fetchLockedAccounts(), fetchWifiStats()])
  pollInterval = setInterval(() => { fetchEvents(); fetchHealthStats(); fetchGraphData(); fetchLockedAccounts(); fetchWifiStats(); }, 10000)
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
        time: d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }),
        date: d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' }),
        rawDate: d
      }
  })
  return [...radarLogs, ...auditLogs].sort((a, b) => b.rawDate - a.rawDate)
})

const getBarColor = (val) => {
  if (val > 85) return 'bg-red-500'
  if (val > 70) return 'bg-amber-500'
  return 'bg-green-500'
}

const getInitials = (name) => {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

const handleUnlock = async (username) => {
  if (!confirm(`¿Estás seguro de desbloquear la cuenta de ${username}?`)) return
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
    } else {
      alert("Error al desbloquear la cuenta.")
    }
  } catch (e) {
    alert("Error de red al intentar desbloquear.")
  }
}
</script>

<template>
  <div class="font-sans antialiased text-gray-900 bg-transparent min-h-full pb-4 flex flex-col gap-4">
    
    <!-- Top KPIs -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      <!-- Módulo AD -->
      <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">AD: Bloqueos</span>
          <span class="text-3xl font-extrabold text-gray-900 leading-none">{{ healthStats.locked_users }}</span>
        </div>
        <span v-if="healthStats.locked_users > 0" class="h-2.5 w-2.5 rounded-full bg-red-500 shrink-0"></span>
        <span v-else class="h-2.5 w-2.5 rounded-full bg-green-500 shrink-0"></span>
      </div>

      <!-- Módulo Impresión -->
      <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">Spooler</span>
          <span v-if="printerStatus.jammed > 0" class="text-3xl font-extrabold text-gray-900 leading-none">{{ printerStatus.jammed }} <span class="text-xs font-semibold text-red-600 uppercase tracking-wider">Atascos</span></span>
          <span v-else-if="!printerStatus.spoolerOk" class="text-3xl font-extrabold text-red-600 leading-none">Caído</span>
          <span v-else class="text-3xl font-extrabold text-gray-900 leading-none">OK</span>
        </div>
        <span v-if="printerStatus.jammed > 0 || !printerStatus.spoolerOk" class="h-2.5 w-2.5 rounded-full bg-red-500 shrink-0"></span>
        <span v-else class="h-2.5 w-2.5 rounded-full bg-green-500 shrink-0"></span>
      </div>

      <!-- Módulo Entra ID -->
      <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">Entra ID Sync</span>
          <span class="text-xs text-gray-400">{{ syncStatus ? new Date(syncStatus).toLocaleString('es-CO') : '--/--/----' }}</span>
        </div>
        <span v-if="syncStatus" class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-green-100 text-green-700 shrink-0">Activa</span>
        <span v-else class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-100 text-amber-700 shrink-0">Pendiente</span>
      </div>

      <!-- Módulo Seguridad -->
      <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm p-4 flex items-center justify-between">
        <div>
          <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-1">Seguridad</span>
          <span class="text-3xl font-extrabold text-gray-900 leading-none">{{ securityRadar.length }} <span class="text-xs text-gray-400 font-medium">alertas</span></span>
        </div>
        <span v-if="securityRadar.length > 0" class="h-2.5 w-2.5 rounded-full bg-red-500 shrink-0"></span>
        <span v-else class="h-2.5 w-2.5 rounded-full bg-green-500 shrink-0"></span>
      </div>
    </div>

    <!-- Middle Section: Grid 2 Columnas -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      
      <!-- Salud de Red Wi-Fi -->
      <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm flex flex-col">
        <div class="px-4 py-3 border-b border-gray-200 bg-gray-50 flex justify-between items-center rounded-t-xl">
          <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado de Red Wi-Fi</h2>
          <button class="text-xs font-medium text-blue-600 hover:underline" @click="router.push('/wifi')">Ir al Dashboard</button>
        </div>
        <div class="p-5 flex flex-col justify-center gap-6 flex-1">
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-gray-50 rounded-lg p-3 text-center border border-gray-100">
              <span class="block text-3xl font-extrabold text-gray-900">{{ wifiStats.totalAps }}</span>
              <span class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mt-1">Access Points</span>
            </div>
            <div class="bg-gray-50 rounded-lg p-3 text-center border border-gray-100">
              <span class="block text-3xl font-extrabold text-blue-600">{{ wifiStats.totalClients }}</span>
              <span class="block text-[11px] font-semibold text-gray-500 uppercase tracking-wider mt-1">Disp. Conectados</span>
            </div>
          </div>
          
          <div class="space-y-4 px-2">
            <div>
              <div class="flex justify-between items-center mb-1">
                <span class="text-sm font-medium text-gray-700 flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full" :class="wifiStats.offlineAps > 0 ? 'bg-red-500' : 'bg-green-500'"></span>
                  APs Offline
                </span>
                <span class="text-sm font-bold" :class="wifiStats.offlineAps > 0 ? 'text-red-600' : 'text-gray-900'">{{ wifiStats.offlineAps }}</span>
              </div>
            </div>
            
            <div>
              <div class="flex justify-between items-center mb-1">
                <span class="text-sm font-medium text-gray-700">Experiencia Promedio</span>
                <span class="text-sm font-bold text-gray-900">{{ wifiStats.avgExperience }}%</span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="h-2 rounded-full transition-all duration-1000" 
                     :class="wifiStats.avgExperience >= 80 ? 'bg-green-500' : (wifiStats.avgExperience >= 50 ? 'bg-yellow-500' : 'bg-red-500')"
                     :style="{width: wifiStats.avgExperience + '%'}"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Últimas Cuentas Bloqueadas (Actionable Queue) -->
      <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm flex flex-col">
        <div class="px-4 py-3 border-b border-gray-200 bg-gray-50 flex justify-between items-center rounded-t-xl">
          <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Últimas Cuentas Bloqueadas</h2>
          <button class="text-xs font-medium text-blue-600 hover:underline" @click="router.push('/cuentas?estado=bloqueados')">Ver todas</button>
        </div>
        <div class="p-4 flex-1 flex flex-col">
          <template v-if="lockedAccountsList.length > 0">
            <div class="space-y-1">
              <div v-for="(acc, index) in lockedAccountsList" :key="index" 
                   class="flex items-center justify-between py-2.5 px-3 -mx-1 rounded-lg hover:bg-gray-50/80 transition duration-150 ease-in-out cursor-pointer">
                <div class="flex items-center gap-3 min-w-0">
                  <!-- Avatar con iniciales + badge de bloqueo -->
                  <div class="relative shrink-0">
                    <div class="h-8 w-8 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-xs font-bold">
                      {{ getInitials(acc.displayName) }}
                    </div>
                    <span class="absolute -bottom-0.5 -right-0.5 block h-3 w-3 rounded-full bg-red-500 border-2 border-white"></span>
                  </div>
                  <div class="flex flex-col min-w-0">
                    <span class="text-sm font-semibold text-gray-900 truncate">{{ acc.fullName || acc.username }}</span>
                    <span class="text-xs text-gray-500 truncate">Bloqueado en AD: {{ acc.lockoutTime }}</span>
                  </div>
                </div>
                <div class="flex items-center gap-3 shrink-0 ml-3">
                  <button @click.stop="handleUnlock(acc.username)" 
                          class="text-blue-600 hover:bg-blue-50 px-3 py-1 rounded-md text-xs font-medium transition-colors whitespace-nowrap">
                    Desbloquear
                  </button>
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="flex-1 flex flex-col items-center justify-center text-center py-6">
              <svg class="w-7 h-7 text-green-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <p class="text-sm font-semibold text-gray-900">Operación normal</p>
              <p class="text-xs text-gray-400 mt-0.5">Cero bloqueos reportados.</p>
            </div>
          </template>
        </div>
      </div>

    </div>

    <!-- Bottom Section: Auditoría Global -->
    <div class="bg-white rounded-xl border border-gray-200/75 shadow-sm flex flex-col max-h-72 overflow-hidden">
      <div class="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between shrink-0 rounded-t-xl">
        <h2 class="text-xs font-semibold text-gray-500 uppercase tracking-wider">Auditoría Global</h2>
      </div>
      <div class="overflow-y-auto">
        <table class="w-full text-left border-collapse">
          <thead class="sticky top-0 bg-gray-50 shadow-[0_1px_0_0_#e5e7eb] z-10">
            <tr>
              <th class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider bg-gray-50">Fecha / Hora</th>
              <th class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider bg-gray-50">Usuario</th>
              <th class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider bg-gray-50">Módulo</th>
              <th class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider bg-gray-50">Acción / Target</th>
              <th class="px-4 py-2.5 text-[11px] font-semibold text-gray-500 uppercase tracking-wider text-right bg-gray-50">Estado</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="log in combinedLogs" :key="log.id" class="hover:bg-gray-50/80 transition duration-150 ease-in-out cursor-default">
              <td class="px-4 py-2 whitespace-nowrap">
                <span class="text-sm text-gray-900 block">{{ log.date }}</span>
                <span class="text-xs text-gray-400 block">{{ log.time }}</span>
              </td>
              <td class="px-4 py-2">
                <span class="text-sm font-medium text-gray-900 block truncate max-w-[120px]" :title="log.user">{{ log.user }}</span>
              </td>
              <td class="px-4 py-2">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 text-gray-700">{{ log.module || 'Sistema' }}</span>
              </td>
              <td class="px-4 py-2">
                <span class="text-sm text-gray-900 block leading-tight">{{ log.action }}</span>
                <span class="text-xs font-mono text-gray-400 truncate max-w-[250px] block mt-0.5" :title="log.target">{{ log.target }}</span>
              </td>
              <td class="px-4 py-2 text-right">
                <span v-if="log.severity === 'info'" class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-green-100 text-green-700">Éxito</span>
                <span v-else-if="log.severity === 'error'" class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-100 text-red-700">Error</span>
                <span v-else class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-100 text-amber-700">Advertencia</span>
              </td>
            </tr>
            <tr v-if="combinedLogs.length === 0">
              <td colspan="5" class="px-4 py-8 text-center text-gray-500 text-sm">Sin eventos recientes en la auditoría global.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>
