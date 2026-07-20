<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import Sparkline from '@/components/common/Sparkline.vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const servers = ref([])
const loading = ref(false)
const error = ref('')
const lastUpdate = ref('')
let pollInterval = null

async function fetchStats() {
  loading.value = true
  error.value = ''
  try {
    const res = await authFetch(`${API_BASE}/monitoring/`)
    const data = await res.json()
    if (res.ok && data.success) {
      const now = new Date()
      lastUpdate.value = now.toLocaleTimeString('es-CO')
      
      data.data.forEach(incomingSrv => {
        let existingSrv = servers.value.find(s => s.id === incomingSrv.id)
        
        // Garantizar que tenga estructura history si el backend por alguna razÃ³n no la enviÃ³ aÃºn
        if (!incomingSrv.history) {
          incomingSrv.history = { cpu: Array(20).fill(0), ram: Array(20).fill(0) }
        }

        if (!existingSrv) {
          servers.value.push(incomingSrv)
        } else {
          existingSrv.stats = incomingSrv.stats
          existingSrv.name = incomingSrv.name
          existingSrv.type = incomingSrv.type
          existingSrv.ip = incomingSrv.ip
          existingSrv.history = incomingSrv.history
        }
      })
      
      // Remover servidores que ya no existen en la BD
      const incomingIds = data.data.map(s => s.id)
      servers.value = servers.value.filter(s => incomingIds.includes(s.id))
      
    } else {
      error.value = data.detail || 'Error al obtener estadÃ­sticas.'
    }
  } catch (e) {
    error.value = 'Fallo de red al conectar con el backend.'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(() => {
    fetchStats()
  }, 5000) // Poll every 5 seconds
}

function stopPolling() {
  if (pollInterval) clearInterval(pollInterval)
}

function getProgressColorHex(percent) {
  if (percent >= 90) return '#EF4444' // red-500
  if (percent >= 75) return '#F59E0B' // amber-500
  return '#10B981' // emerald-500
}

function getProgressColorClass(percent) {
  if (percent >= 90) return 'bg-red-500'
  if (percent >= 75) return 'bg-amber-500'
  return 'bg-emerald-500'
}

function getTextClass(percent) {
  if (percent >= 90) return 'text-red-600'
  if (percent >= 75) return 'text-amber-600'
  return 'text-emerald-600'
}

function formatDecimal(val) {
  const num = parseFloat(val)
  if (isNaN(num)) return val
  return num.toFixed(2)
}

const statsSummary = computed(() => {
  const online = servers.value.filter(s => s.stats.status === 'online').length
  const offline = servers.value.filter(s => s.stats.status !== 'online').length
  const total = servers.value.length
  return { online, offline, total }
})

// Mantiene un orden alfabÃ©tico estricto en la UI para evitar parpadeos y reordenamientos
const sortedServers = computed(() => {
  return [...servers.value].sort((a, b) => a.name.localeCompare(b.name))
})

onMounted(() => {
  fetchStats()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header & Global Stats -->
    <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-6 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 tracking-tight">Centro de Monitoreo</h1>
        <p class="text-sm text-gray-500 mt-1 flex items-center gap-2">
          Monitoreo en vivo de infraestructura de servidores
          <span v-if="lastUpdate" class="text-xs font-medium px-2 py-0.5 bg-gray-100 rounded text-gray-500 hidden md:inline-block">Actualizado: {{ lastUpdate }}</span>
        </p>
      </div>
      
      <div class="flex flex-wrap items-center gap-4">
        <!-- Resumen Global -->
        <div class="flex items-center gap-6 pr-6 border-r border-gray-200">
          <div class="flex flex-col">
            <span class="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-0.5">Total Servers</span>
            <span class="text-2xl font-bold text-gray-800 leading-none">{{ statsSummary.total }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-xs font-semibold text-emerald-500 uppercase tracking-wider mb-0.5">Healthy</span>
            <span class="text-2xl font-bold text-gray-800 leading-none">{{ statsSummary.online }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-xs font-semibold text-red-500 uppercase tracking-wider mb-0.5">Alerts</span>
            <span class="text-2xl font-bold text-red-600 leading-none">{{ statsSummary.offline }}</span>
          </div>
        </div>
      
        <button @click="fetchStats" :disabled="loading" class="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors disabled:opacity-50">
          <svg :class="['h-4 w-4', loading ? 'animate-spin' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Forzar Sincronización
        </button>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-sm flex gap-3">
      <svg class="h-5 w-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-if="servers.length === 0 && !loading" class="bg-white rounded-xl shadow-sm border border-gray-200 p-16 text-center">
      <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" /></svg>
      <h3 class="text-lg font-semibold text-gray-900">No hay servidores registrados</h3>
      <p class="text-sm text-gray-500 mt-2">Ve al mÃ³dulo de ConfiguraciÃ³n para agregar infraestructura.</p>
    </div>

    <!-- Server Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      
      <!-- Server Card -->
      <div v-for="srv in sortedServers" :key="srv.id" class="bg-white rounded-xl shadow-sm border border-gray-200 flex flex-col hover:shadow-md transition-shadow overflow-hidden">
        
        <!-- Compact Header -->
        <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between" :class="srv.stats.status === 'online' ? 'bg-white' : 'bg-red-50/50'">
          <div class="flex items-center gap-3">
            <!-- Icono Limpio Outline sin fondos -->
            <div :class="['flex items-center justify-center shrink-0', srv.stats.status === 'online' ? 'text-gray-500' : 'text-red-500']">
              <svg v-if="srv.type === 'da'" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
              <svg v-else-if="srv.type === 'rds'" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
              <svg v-else class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" /></svg>
            </div>
            <div class="flex flex-col">
              <h3 class="font-bold text-gray-900 text-base leading-tight">{{ srv.name }}</h3>
              <span class="text-xs font-medium text-gray-500 leading-tight mt-0.5">{{ srv.ip }}</span>
            </div>
          </div>
          <div>
            <span v-if="srv.stats.status === 'online'" class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 text-[10px] font-bold border border-emerald-200">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> ONLINE
            </span>
            <span v-else class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-red-50 text-red-700 text-[10px] font-bold border border-red-200">
              <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span> OFFLINE
            </span>
          </div>
        </div>

        <!-- Body -->
        <div class="p-4 flex-1 flex flex-col gap-4">
          
          <!-- Offline State -->
          <div v-if="srv.stats.status !== 'online'" class="flex-1 flex flex-col items-center justify-center text-center py-6">
            <div class="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-2">
              <svg class="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            </div>
            <p class="text-sm font-bold text-red-600 mb-0.5">Connection Error</p>
            <p class="text-xs text-gray-500 px-4 leading-relaxed break-all">{{ srv.stats.error || 'Timeout or credentials failure.' }}</p>
          </div>

          <!-- Online State (3 Columns) -->
          <template v-else>
            <div class="grid grid-cols-3 gap-5">
              
              <!-- Column 1: CPU (Time Series Area Chart) -->
              <div class="flex flex-col bg-gray-50 rounded-xl p-3 border border-gray-100 overflow-hidden relative group">
                <div class="flex justify-between items-start mb-2 relative z-10">
                  <span class="text-xs font-bold text-gray-500 uppercase tracking-widest">CPU</span>
                  <span :class="['text-2xl font-bold leading-none', getTextClass(srv.stats.CPU)]">{{ srv.stats.CPU }}%</span>
                </div>
                <!-- Sparkline Chart -->
                <div class="h-20 w-full mt-auto -mb-3 -mx-1 opacity-90 group-hover:opacity-100 transition-opacity">
                  <Sparkline 
                    :data="srv.history?.cpu || []" 
                    :color="getProgressColorHex(srv.stats.CPU)" 
                    :min="0" :max="100" 
                  />
                </div>
              </div>
              
              <!-- Column 2: RAM (Time Series Area Chart) -->
              <div class="flex flex-col bg-gray-50 rounded-xl p-3 border border-gray-100 overflow-hidden relative group">
                <div class="flex justify-between items-start mb-1 relative z-10">
                  <span class="text-xs font-bold text-gray-500 uppercase tracking-widest">Mem</span>
                  <span :class="['text-2xl font-bold leading-none', getTextClass(srv.stats.RAM_Percent)]">{{ srv.stats.RAM_Percent }}%</span>
                </div>
                <div class="text-[10px] font-medium text-gray-500 relative z-10 text-right leading-none mb-1">
                  {{ formatDecimal(srv.stats.RAM_Used) }} / {{ formatDecimal(srv.stats.RAM_Total) }} GB
                </div>
                <!-- Sparkline Chart -->
                <div class="h-16 w-full mt-auto -mb-3 -mx-1 opacity-90 group-hover:opacity-100 transition-opacity">
                  <Sparkline 
                    :data="srv.history?.ram || []" 
                    :color="getProgressColorHex(srv.stats.RAM_Percent)" 
                    :min="0" :max="100" 
                  />
                </div>
              </div>

              <!-- Column 3: Storage (Linear) -->
              <div class="flex flex-col justify-center">
                <span class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2 text-center">Discos</span>
                <div class="space-y-3">
                  <div v-for="disk in srv.stats.Disks" :key="disk.DeviceID" class="bg-gray-50 rounded-lg p-2 border border-gray-100">
                    <div class="flex justify-between items-end mb-1.5">
                      <div class="flex items-center gap-1.5">
                        <span class="text-[10px] font-bold text-gray-700 bg-white border border-gray-200 px-1.5 py-0.5 rounded">{{ disk.DeviceID }}</span>
                        <span class="text-[11px] font-semibold text-gray-600">{{ Math.round(((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100) }}%</span>
                      </div>
                      <span class="text-[9px] font-medium text-gray-500">{{ formatDecimal(disk.FreeGB) }} GB Libres</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div :class="['h-full rounded-full transition-all duration-1000 ease-out', getProgressColorClass(((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100)]" :style="`width: ${((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100}%`"></div>
                    </div>
                  </div>
                  <div v-if="!srv.stats.Disks || !srv.stats.Disks.length" class="text-xs text-gray-400 text-center">
                    -
                  </div>
                </div>
              </div>

            </div>

            <!-- Footer: Uptime (Compact) -->
            <div class="mt-auto pt-2 border-t border-gray-100 flex items-center justify-end">
              <span class="text-[10px] text-gray-400 font-medium">Uptime: <span class="font-semibold text-gray-600 ml-1">{{ srv.stats.UptimeDays }}d {{ srv.stats.UptimeHours }}h</span></span>
            </div>
          </template>
        </div>
      </div>
      
    </div>
  </div>
</template>
