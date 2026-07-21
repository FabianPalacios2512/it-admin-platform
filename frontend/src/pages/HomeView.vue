<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { getFriendlyLicenseName } from '@/utils/licenses'

// --- Data State ---
const healthStats = ref({
  total_users: 0,
  enabled_users: 0,
  disabled_users: 0,
  password_never_expires: 0,
  inactive_users_90d: 0,
  locked_users: 0,
  new_computers: 0,
})

const licenses = ref([])
const syncStatus = ref(null)
const securityRadar = ref([])
const recentEvents = ref([])
const showADDetails = ref(false)

// --- Polling ---
let pollInterval = null

onMounted(async () => {
  const fetchEvents = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/audit', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        recentEvents.value = data.slice(0, 20).map(event => {
          const d = new Date(event.timestamp + 'Z') 
          return {
            id: event.id,
            rawDate: d,
            time: d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
            date: d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit' }),
            type: event.status === 'Error' ? 'error' : event.status === 'Pendiente' ? 'warn' : 'info',
            user: event.username,
            action: event.action,
            target: event.target,
            status: event.status
          }
        })
      }
    } catch (error) {
      console.error("Error fetching audit logs:", error)
    }
  }

  const fetchHealthStats = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch('/api/v1/accounts/health-stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        healthStats.value = await res.json()
      }
    } catch (error) {
      console.error("Error fetching health stats:", error)
    }
  }

  const fetchGraphData = async () => {
    const token = localStorage.getItem('access_token')
    const headers = { 'Authorization': `Bearer ${token}` }
    
    try {
      const [resLic, resSync, resSec] = await Promise.all([
        fetch('/api/v1/graph/licenses', { headers }).catch(() => ({ok: false})),
        fetch('/api/v1/graph/sync-status', { headers }).catch(() => ({ok: false})),
        fetch('/api/v1/graph/security-radar', { headers }).catch(() => ({ok: false}))
      ])
      
      if (resLic.ok) licenses.value = await resLic.json()
      if (resSync.ok) {
        const syncData = await resSync.json()
        syncStatus.value = syncData.onPremisesLastSyncDateTime
      }
      if (resSec.ok) securityRadar.value = await resSec.json()
    } catch (err) {
      console.error("Error fetching graph data:", err)
    }
  }
  
  await Promise.all([fetchEvents(), fetchHealthStats(), fetchGraphData()])
  
  pollInterval = setInterval(() => {
    fetchEvents()
    fetchHealthStats()
    fetchGraphData()
  }, 10000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

// --- Semantic Helpers ---
const syncStatusInfo = computed(() => {
  if (!syncStatus.value) return { text: 'PENDING', class: 'text-slate-500 bg-slate-100 border-slate-200' }
  const lastSync = new Date(syncStatus.value)
  const now = new Date()
  const diffHours = (now - lastSync) / (1000 * 60 * 60)
  
  if (diffHours < 1) return { text: 'OK', class: 'text-emerald-700 bg-emerald-50 border-emerald-200' }
  if (diffHours < 3) return { text: 'WARN', class: 'text-amber-700 bg-amber-50 border-amber-200' }
  return { text: 'ERR', class: 'text-red-700 bg-red-50 border-red-200' }
})

const getLicenseColor = (consumed, total) => {
  if (!total) return 'bg-slate-300'
  const percent = consumed / total
  if (percent > 0.95) return 'bg-red-400'
  if (percent > 0.85) return 'bg-amber-400'
  return 'bg-blue-400'
}

const combinedLogs = computed(() => {
  const auditLogs = recentEvents.value.map(log => ({
    id: `audit-${log.id}`,
    isSecurity: false,
    user: log.user,
    action: log.action,
    target: log.target,
    severity: log.type,
    ip: '-',
    location: 'Internal',
    errorCode: log.status,
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
        action: 'Sign-in Blocked',
        target: 'Entra ID',
        severity: log.status?.errorCode === 50126 ? 'warn' : 'error',
        ip: log.ipAddress || '-',
        location: log.location?.city ? `${log.location.countryOrRegion}` : '-',
        errorCode: log.status?.errorCode || 'FAIL',
        time: d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        date: d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit' }),
        rawDate: d
      }
  })
  
  return [...radarLogs, ...auditLogs].sort((a, b) => b.rawDate - a.rawDate)
})

const severityClasses = {
  info: 'border-l-blue-400',
  warn: 'border-l-amber-400',
  error: 'border-l-red-500 bg-red-50/30'
}

const severityText = {
  info: 'text-blue-600',
  warn: 'text-amber-600',
  error: 'text-red-600 font-medium'
}

// --- License Assignment Logic ---
// Removido temporalmente del Dashboard por solicitud del usuario (se movió a Cuentas)
</script>

<template>
  <div class="font-sans antialiased bg-transparent min-h-full">
    <!-- Header Global & Breadcrumb -->
    <div class="mb-4 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-slate-900 tracking-tight">IT Operations Center</h1>
        <p class="text-xs text-slate-500 mt-0.5">Gestión global de infraestructura y eventos de seguridad</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
        </span>
        <span class="text-xs font-medium text-slate-600 uppercase tracking-wider">System Online</span>
      </div>
    </div>

    <!-- Barra de Estado (Top KPIs) -->
    <div class="bg-white border border-slate-200 rounded-md mb-6 flex divide-x divide-slate-100 overflow-hidden">
      <!-- KPI 1 -->
      <div class="flex-1 p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
        <div class="flex flex-col">
          <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Equipos Pendientes</span>
          <div class="flex items-baseline gap-2">
            <span class="text-2xl font-bold text-slate-900 leading-none">{{ healthStats.new_computers }}</span>
            <span v-if="healthStats.new_computers > 0" class="text-[10px] font-medium text-blue-700 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded">Action Req.</span>
          </div>
        </div>
        <svg class="w-6 h-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"></path></svg>
      </div>

      <!-- KPI 2 -->
      <div class="flex-1 p-4 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer" @click="$router.push('/cuentas?estado=bloqueados')">
        <div class="flex flex-col">
          <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Cuentas Bloqueadas</span>
          <div class="flex items-baseline gap-2">
            <span class="text-2xl font-bold text-slate-900 leading-none">{{ healthStats.locked_users }}</span>
            <span v-if="healthStats.locked_users > 0" class="text-[10px] font-medium text-red-700 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">Critical</span>
          </div>
        </div>
        <svg class="w-6 h-6 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
      </div>

      <!-- KPI 3 -->
      <div class="flex-1 p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
        <div class="flex flex-col">
          <span class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1">Active Directory</span>
          <div class="flex items-baseline gap-2">
            <span class="text-2xl font-bold text-slate-900 leading-none">{{ healthStats.enabled_users }}</span>
            <span class="text-[10px] text-slate-500 font-medium">Activos</span>
          </div>
        </div>
        <div class="text-right">
           <span class="inline-block mt-2 text-[10px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded uppercase tracking-wide">Sys OK</span>
        </div>
      </div>
    </div>

    <!-- Main Content (Consola) -->
    <div class="flex flex-col lg:flex-row gap-6 items-start">
      
      <!-- Columna Principal: Logs de Seguridad y Auditoría (70%) -->
      <div class="w-full lg:w-[70%] bg-white border border-slate-200 rounded-md flex flex-col">
        <div class="px-4 py-3 border-b border-slate-200 flex items-center justify-between bg-slate-50/50 rounded-t-md">
          <h2 class="text-[13px] font-semibold text-slate-900 uppercase tracking-wide">Eventos del Sistema & Seguridad</h2>
          <span class="text-[11px] text-slate-500 font-mono flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            Live Monitor
          </span>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-200">
                <th class="px-4 py-2.5 font-semibold w-8"></th>
                <th class="px-2 py-2.5 font-semibold">Time</th>
                <th class="px-4 py-2.5 font-semibold">User</th>
                <th class="px-4 py-2.5 font-semibold">Action / Target</th>
                <th class="px-4 py-2.5 font-semibold">IP / Location</th>
                <th class="px-4 py-2.5 font-semibold text-right">Code</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-[12px]">
              <tr v-for="log in combinedLogs" :key="log.id" :class="['group hover:bg-slate-50/70 transition-colors', log.severity === 'error' ? 'bg-red-50/20' : '']">
                <td class="px-0 py-0">
                   <div :class="['w-1 h-10', severityClasses[log.severity]]"></div>
                </td>
                <td class="px-2 py-2 whitespace-nowrap">
                  <div class="flex flex-col">
                    <span class="font-mono text-slate-700">{{ log.time }}</span>
                    <span class="font-mono text-[10px] text-slate-400">{{ log.date }}</span>
                  </div>
                </td>
                <td class="px-4 py-2">
                  <span class="font-medium text-slate-900">{{ log.user }}</span>
                </td>
                <td class="px-4 py-2">
                  <div class="flex flex-col">
                    <span :class="['font-medium', severityText[log.severity]]">{{ log.action }}</span>
                    <span class="text-[10px] text-slate-500 font-mono mt-0.5 flex items-center gap-1">
                      <svg v-if="log.isSecurity" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                      {{ log.target }}
                    </span>
                  </div>
                </td>
                <td class="px-4 py-2">
                  <div class="flex flex-col">
                    <span class="font-mono text-slate-700">{{ log.ip }}</span>
                    <span class="text-[10px] text-slate-500">{{ log.location }}</span>
                  </div>
                </td>
                <td class="px-4 py-2 text-right whitespace-nowrap">
                  <span class="font-mono text-[11px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">{{ log.errorCode }}</span>
                </td>
              </tr>
              <tr v-if="combinedLogs.length === 0">
                <td colspan="6" class="px-4 py-8 text-center text-slate-500 text-xs">No hay eventos recientes registrados.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Columna Lateral: Infraestructura & Servicios (30%) -->
      <div class="w-full lg:w-[30%] flex flex-col gap-6">
        
        <!-- Estado de Servicios Locales -->
        <div class="bg-white border border-slate-200 rounded-md">
          <div class="px-4 py-3 border-b border-slate-200 bg-slate-50/50 rounded-t-md">
            <h2 class="text-[13px] font-semibold text-slate-900 uppercase tracking-wide">Infraestructura Core</h2>
          </div>
          <div class="p-4">
            <ul class="space-y-4">
              <!-- Sync Status -->
              <li class="flex items-center justify-between">
                <div>
                  <p class="text-[12px] font-medium text-slate-800">Entra Connect Sync</p>
                  <p class="text-[10px] text-slate-500 font-mono mt-0.5">{{ syncStatus ? new Date(syncStatus).toLocaleTimeString('es-CO') : '--:--' }}</p>
                </div>
                <span :class="['text-[10px] font-bold px-1.5 py-0.5 rounded border', syncStatusInfo.class]">
                  {{ syncStatusInfo.text }}
                </span>
              </li>
              <!-- DC Status -->
              <li class="flex items-center justify-between">
                <div>
                  <p class="text-[12px] font-medium text-slate-800">Domain Controller</p>
                  <p class="text-[10px] text-slate-500 font-mono mt-0.5">192.168.20.100</p>
                </div>
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded border text-emerald-700 bg-emerald-50 border-emerald-200">OK</span>
              </li>
              <!-- File Server Status -->
              <li class="flex items-center justify-between">
                <div>
                  <p class="text-[12px] font-medium text-slate-800">File Server (DFS)</p>
                  <p class="text-[10px] text-slate-500 font-mono mt-0.5">192.168.20.110</p>
                </div>
                <span class="text-[10px] font-bold px-1.5 py-0.5 rounded border text-emerald-700 bg-emerald-50 border-emerald-200">OK</span>
              </li>
            </ul>
          </div>
        </div>

        <!-- M365 Licenses (Estilo Microsoft Admin Center) -->
        <div class="bg-white border border-slate-200 rounded-md p-5 flex flex-col">
          <h2 class="text-[14px] font-semibold text-slate-900 mb-1">Desglose de licencias de usuario</h2>
          <p class="text-[12px] text-slate-600 mb-4">Usuarios activos de su configuración</p>
          <div class="text-[32px] font-bold text-slate-900 mb-6 leading-none">{{ healthStats.enabled_users }}</div>
          
          <p class="text-[12px] text-slate-600 mb-3">Licencias por tipo</p>
          
          <div class="space-y-4 mb-8">
            <div v-for="sku in licenses" :key="sku.skuId" class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between text-[12px]">
                <span class="text-slate-800" :title="sku.skuPartNumber">{{ getFriendlyLicenseName(sku.skuPartNumber) }}</span>
                <span class="text-slate-500 font-mono text-[11px]">{{ sku.consumedUnits }}/{{ sku.prepaidUnits?.enabled || 0 }}</span>
              </div>
              <div class="w-full bg-slate-100 rounded-full h-1.5">
                <div class="bg-blue-600 h-1.5 rounded-full" :style="{ width: `${(sku.consumedUnits / (sku.prepaidUnits?.enabled || 1)) * 100}%` }"></div>
              </div>
            </div>
            <div v-if="!licenses.length" class="text-[12px] text-slate-500">Consultando Graph API...</div>
          </div>

          <div class="mt-auto flex flex-col gap-2.5">
            <button class="w-full py-1.5 px-4 bg-white border border-slate-300 rounded hover:bg-slate-50 text-[13px] font-medium text-slate-700 transition-colors" @click="$router.push('/cuentas')">Asignar licencia</button>
            <button class="w-full py-1.5 px-4 bg-white border border-slate-300 rounded hover:bg-slate-50 text-[13px] font-medium text-slate-700 transition-colors" @click="$router.push('/cuentas')">Administración usuarios</button>
          </div>
        </div>

        <!-- AD Status Resumen -->
        <div class="bg-white border border-slate-200 rounded-md">
           <div class="px-4 py-3 border-b border-slate-200 bg-slate-50/50 rounded-t-md flex justify-between items-center">
            <h2 class="text-[13px] font-semibold text-slate-900 uppercase tracking-wide">AD Metrics</h2>
            <button @click="showADDetails = !showADDetails" class="text-[10px] font-medium text-blue-600 hover:text-blue-700 transition-colors">
              {{ showADDetails ? 'Ocultar' : 'Ver mÃ¡s' }}
            </button>
          </div>
          <div class="p-4">
            <div class="flex items-center gap-4">
               <div class="flex-1 flex items-baseline justify-between border-b border-slate-100 pb-2">
                 <span class="text-[11px] font-medium text-slate-500">Inactivos (+90d)</span>
                 <span class="font-bold text-red-600 font-mono">{{ healthStats.inactive_users_90d }}</span>
               </div>
            </div>
            
            <div v-show="showADDetails" class="mt-3 space-y-2">
              <div class="flex items-center justify-between border-b border-slate-100 pb-2">
                 <span class="text-[11px] font-medium text-slate-500">Total Usuarios</span>
                 <span class="font-bold text-slate-700 font-mono">{{ healthStats.total_users }}</span>
               </div>
               <div class="flex items-center justify-between border-b border-slate-100 pb-2">
                 <span class="text-[11px] font-medium text-slate-500">Deshabilitados</span>
                 <span class="font-bold text-slate-700 font-mono">{{ healthStats.disabled_users }}</span>
               </div>
               <div class="flex items-center justify-between">
                 <span class="text-[11px] font-medium text-slate-500">Nunca Expira</span>
                 <span class="font-bold text-amber-600 font-mono">{{ healthStats.password_never_expires }}</span>
               </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>
