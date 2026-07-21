<script setup>
import { ref, onMounted, computed } from 'vue'
import { API_BASE, authFetch } from '@/config'

const alerts = ref([])
const loading = ref(true)
const error = ref('')
const searchTerm = ref('')

async function fetchSecurityAlerts() {
  loading.value = true
  error.value = ''
  try {
    const res = await authFetch(`${API_BASE}/graph/security-radar`)
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    alerts.value = await res.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSecurityAlerts()
})

const filteredAlerts = computed(() => {
  if (!searchTerm.value) return alerts.value
  const term = searchTerm.value.toLowerCase()
  return alerts.value.filter(a => {
    return (a.userDisplayName?.toLowerCase() || '').includes(term) ||
           (a.userPrincipalName?.toLowerCase() || '').includes(term) ||
           (a.ipAddress || '').includes(term) ||
           (a.location?.countryOrRegion?.toLowerCase() || '').includes(term)
  })
})

const uniqueIPs = computed(() => new Set(alerts.value.map(a => a.ipAddress).filter(Boolean)).size)
const topTarget = computed(() => {
  if (alerts.value.length === 0) return 'Ninguno'
  const counts = {}
  let maxCount = 0
  let topUser = ''
  alerts.value.forEach(a => {
    const u = a.userDisplayName || a.userPrincipalName || 'Desconocido'
    counts[u] = (counts[u] || 0) + 1
    if (counts[u] > maxCount) {
      maxCount = counts[u]
      topUser = u
    }
  })
  return topUser
})
const topCountry = computed(() => {
  if (alerts.value.length === 0) return 'Ninguno'
  const counts = {}
  let maxCount = 0
  let topLoc = ''
  alerts.value.forEach(a => {
    const l = a.location?.countryOrRegion || 'Desconocido'
    counts[l] = (counts[l] || 0) + 1
    if (counts[l] > maxCount) {
      maxCount = counts[l]
      topLoc = l
    }
  })
  return topLoc
})

function formatDateTime(isoStr) {
  if (!isoStr) return '--'
  const d = new Date(isoStr)
  return d.toLocaleString('es-CO', { 
    month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' 
  })
}

function getErrorDescription(code) {
  const map = {
    '50126': 'Credenciales inválidas',
    '50053': 'IP maliciosa / Fuerza bruta',
    '50057': 'Cuenta deshabilitada',
    '50058': 'Token revocado / Sesión inválida',
    '50074': 'MFA requerido',
    '50158': 'Desafío de seguridad no superado',
    '53003': 'Bloqueado por Acceso Condicional'
  }
  return map[code] || `Error ${code}`
}

function getCountryFlag(countryCode) {
  if (!countryCode) return '🌍'
  // Convert 2-letter country code to emoji flag
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char =>  127397 + char.charCodeAt())
  return String.fromCodePoint(...codePoints)
}
</script>

<template>
  <div class="h-full flex flex-col bg-slate-50 relative overflow-y-auto">
    <!-- Header Borderless -->
    <div class="bg-white px-8 py-6 sticky top-0 z-10 shrink-0">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center text-red-600">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Security Radar</h1>
          </div>
          <p class="text-[13px] text-slate-500 max-w-2xl">Monitor de ataques e intentos de intrusión detectados por Microsoft Entra ID en las cuentas de la organización.</p>
        </div>
        
        <div class="flex items-center gap-3">
          <div class="relative">
            <svg class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input v-model="searchTerm" type="text" placeholder="Buscar IP, país o usuario..." class="w-full md:w-64 pl-9 pr-4 py-2 text-[12px] bg-slate-50 border border-slate-200 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-700 placeholder-slate-400">
          </div>
          <button @click="fetchSecurityAlerts" :disabled="loading" class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-bold rounded shadow-sm disabled:opacity-50 transition-colors">
            <svg :class="['w-4 h-4', loading ? 'animate-spin' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {{ loading ? 'Sincronizando...' : 'Actualizar' }}
          </button>
        </div>
      </div>
    </div>

    <div class="p-8 max-w-[1400px] w-full mx-auto">
      <!-- Error Message -->
      <div v-if="error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded text-red-700 flex items-start gap-3">
        <svg class="w-5 h-5 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
        <div>
          <h3 class="text-[13px] font-bold">Error de sincronización con Microsoft Graph</h3>
          <p class="text-[12px] mt-1">{{ error }}</p>
        </div>
      </div>

      <!-- KPIs (Summary Cards) -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm flex flex-col justify-between">
          <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Ataques Recientes</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-3xl font-black text-slate-800">{{ alerts.length }}</span>
            <span class="text-[11px] text-slate-500 font-medium">bloqueos</span>
          </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm flex flex-col justify-between">
          <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">IPs Maliciosas</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-3xl font-black text-red-600">{{ uniqueIPs }}</span>
            <span class="text-[11px] text-slate-500 font-medium">fuentes únicas</span>
          </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm flex flex-col justify-between">
          <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">País Mayor Riesgo</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-[18px] font-bold text-slate-800 truncate" :title="topCountry">{{ topCountry }}</span>
          </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm flex flex-col justify-between">
          <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Usuario Más Atacado</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-[16px] font-bold text-slate-800 truncate" :title="topTarget">{{ topTarget }}</span>
          </div>
        </div>
      </div>

      <!-- Main Table -->
      <div class="bg-white border border-slate-200 rounded-md shadow-sm overflow-hidden flex flex-col">
        <div class="bg-slate-50 border-b border-slate-200 px-5 py-3 flex items-center justify-between">
          <h2 class="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Registro de Intrusiones (Últimos 100)</h2>
          <span v-if="!loading" class="text-[10px] text-slate-500 font-medium bg-white px-2 py-0.5 rounded-sm border border-slate-200">{{ filteredAlerts.length }} resultados</span>
        </div>

        <div class="overflow-x-auto min-h-[400px]">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-white border-b border-slate-100">
                <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap">Fecha / Hora</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Usuario Objetivo</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Origen (IP & País)</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Estado / Error</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Aplicación</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-if="loading && alerts.length === 0">
                <td colspan="5" class="px-5 py-16 text-center">
                  <div class="w-8 h-8 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-3"></div>
                  <span class="text-[12px] text-slate-500 font-medium">Cargando registros de auditoría...</span>
                </td>
              </tr>
              <tr v-else-if="filteredAlerts.length === 0">
                <td colspan="5" class="px-5 py-16 text-center text-[13px] text-slate-400 font-medium">
                  No se encontraron intrusiones o alertas de seguridad.
                </td>
              </tr>
              <tr v-for="alert in filteredAlerts" :key="alert.id" class="hover:bg-slate-50/50 transition-colors group">
                <!-- Fecha -->
                <td class="px-5 py-3 align-top">
                  <span class="text-[12px] font-medium text-slate-700 whitespace-nowrap">{{ formatDateTime(alert.createdDateTime) }}</span>
                </td>
                
                <!-- Usuario Objetivo -->
                <td class="px-5 py-3 align-top">
                  <div class="flex flex-col">
                    <span class="text-[12px] font-bold text-slate-900 truncate max-w-[200px]">{{ alert.userDisplayName || 'Desconocido' }}</span>
                    <span class="text-[11px] text-slate-500 font-mono truncate max-w-[200px]">{{ alert.userPrincipalName }}</span>
                  </div>
                </td>

                <!-- Origen -->
                <td class="px-5 py-3 align-top">
                  <div class="flex items-center gap-2">
                    <span class="text-base" :title="alert.location?.countryOrRegion">{{ getCountryFlag(alert.location?.countryOrRegion?.toUpperCase()) }}</span>
                    <div class="flex flex-col">
                      <span class="text-[12px] font-mono font-bold text-slate-800">{{ alert.ipAddress }}</span>
                      <span class="text-[10px] text-slate-500 uppercase tracking-wide">{{ alert.location?.city || 'Ciudad Desconocida' }}, {{ alert.location?.countryOrRegion || 'País Desconocido' }}</span>
                    </div>
                  </div>
                </td>

                <!-- Estado -->
                <td class="px-5 py-3 align-top">
                  <div class="flex flex-col items-start gap-1">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-red-100 text-red-700 border border-red-200">
                      BLOQUEADO
                    </span>
                    <span class="text-[11px] text-slate-600 font-medium" :title="'Error Code: ' + alert.status?.errorCode">
                      {{ getErrorDescription(String(alert.status?.errorCode)) }} ({{ alert.status?.errorCode }})
                    </span>
                  </div>
                </td>

                <!-- App -->
                <td class="px-5 py-3 align-top">
                  <div class="flex flex-col">
                    <span class="text-[12px] font-medium text-slate-800">{{ alert.appDisplayName || 'Desconocida' }}</span>
                    <span class="text-[10px] text-slate-400 font-mono" v-if="alert.clientAppUsed">{{ alert.clientAppUsed }}</span>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
