<script setup>
import { ref, onMounted, computed } from 'vue'

const API_BASE = '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const activeTab = ref('signIns') // 'signIns', 'riskyUsers', 'riskDetections'

const alerts = ref([])
const riskyUsers = ref([])
const riskDetections = ref([])

const loading = ref(true)
const error = ref('')
const licenseError = ref(false)
const searchTerm = ref('')

async function fetchData() {
  loading.value = true
  error.value = ''
  licenseError.value = false
  try {
    const p1 = authFetch(`${API_BASE}/graph/security-radar`).then(r => r.ok ? r.json() : [])
    const p2 = authFetch(`${API_BASE}/graph/security/risky-users`).then(r => r.ok ? r.json() : {error: 'error'})
    const p3 = authFetch(`${API_BASE}/graph/security/risk-detections`).then(r => r.ok ? r.json() : {error: 'error'})
    
    const [d1, d2, d3] = await Promise.all([p1, p2, p3])
    
    alerts.value = Array.isArray(d1) ? d1 : []
    
    if (d2.error === 'license_required' || d3.error === 'license_required') {
      licenseError.value = true
    } else {
      riskyUsers.value = Array.isArray(d2) ? d2 : []
      riskDetections.value = Array.isArray(d3) ? d3 : []
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
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

function formatDateTime(isoStr) {
  if (!isoStr) return '--'
  const d = new Date(isoStr)
  return d.toLocaleString('es-CO', { 
    month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit'
  })
}

function getErrorDescription(code) {
  const map = {
    '50126': 'Credenciales inválidas',
    '50053': 'IP maliciosa / Fuerza bruta',
    '50057': 'Cuenta deshabilitada',
    '50058': 'Token revocado / Sesión inválida',
    '50074': 'MFA requerido',
    '50158': 'Desafío de seguridad falló',
    '53003': 'Bloqueado por Acceso Condicional'
  }
  return map[code] || `Error ${code}`
}

function getCountryFlag(countryCode) {
  if (!countryCode) return '🌍'
  const codePoints = countryCode.toUpperCase().split('').map(char => 127397 + char.charCodeAt())
  return String.fromCodePoint(...codePoints)
}

async function revokeSessions(username) {
  if (!confirm(`¿Estás seguro de que deseas revocar todas las sesiones de ${username}? El usuario será desconectado de todos sus dispositivos.`)) return
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${username}/revoke-sessions`, { method: 'POST' })
    if (res.ok) alert('Sesiones revocadas exitosamente.')
    else alert('Error al revocar sesiones.')
  } catch(e) {
    alert('Error de red.')
  }
}
</script>

<template>
  <div class="h-full flex flex-col bg-slate-50 relative overflow-y-auto">
    <!-- Header Borderless -->
    <div class="bg-white px-8 py-6 sticky top-0 z-10 shrink-0 border-b border-slate-200 shadow-sm">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <div class="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center text-white">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 tracking-tight">Security Operations Center</h1>
          </div>
          <p class="text-[13px] text-slate-500 max-w-2xl">Monitor avanzado de ciberseguridad impulsado por Inteligencia Artificial y Microsoft Entra ID Protection.</p>
        </div>
        
        <div class="flex items-center gap-3">
          <button @click="fetchData" :disabled="loading" class="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-[12px] font-bold rounded shadow-sm disabled:opacity-50 transition-colors">
            <svg :class="['w-4 h-4', loading ? 'animate-spin' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {{ loading ? 'Analizando...' : 'Actualizar Datos' }}
          </button>
        </div>
      </div>
      
      <!-- Navigation Tabs -->
      <div class="flex items-center gap-6 mt-6 border-b border-slate-200">
        <button @click="activeTab='signIns'" :class="['pb-3 text-[13px] font-bold transition-colors border-b-2', activeTab === 'signIns' ? 'text-blue-600 border-blue-600' : 'text-slate-500 border-transparent hover:text-slate-800']">
          Auditoría de Bloqueos ({{ alerts.length }})
        </button>
        <button @click="activeTab='riskyUsers'" :class="['pb-3 text-[13px] font-bold transition-colors border-b-2 flex items-center gap-2', activeTab === 'riskyUsers' ? 'text-red-600 border-red-600' : 'text-slate-500 border-transparent hover:text-slate-800']">
          Usuarios en Riesgo
          <span v-if="riskyUsers.length > 0" class="px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 text-[9px]">{{ riskyUsers.length }}</span>
        </button>
        <button @click="activeTab='riskDetections'" :class="['pb-3 text-[13px] font-bold transition-colors border-b-2 flex items-center gap-2', activeTab === 'riskDetections' ? 'text-amber-600 border-amber-600' : 'text-slate-500 border-transparent hover:text-slate-800']">
          Detecciones de IA
          <span v-if="riskDetections.length > 0" class="px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[9px]">{{ riskDetections.length }}</span>
        </button>
      </div>
    </div>

    <div class="p-8 max-w-[1400px] w-full mx-auto">
      
      <!-- License Warning -->
      <div v-if="licenseError" class="mb-6 p-4 bg-amber-50 border border-amber-200 rounded flex items-start gap-3">
        <svg class="w-5 h-5 shrink-0 mt-0.5 text-amber-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
        <div>
          <h3 class="text-[13px] font-bold text-amber-800">Licencia Insuficiente o Faltan Permisos</h3>
          <p class="text-[12px] text-amber-700 mt-1">Para ver los Usuarios en Riesgo y las Detecciones de IA, asegúrate de haber otorgado los permisos <b>IdentityRiskEvent.Read.All</b> e <b>IdentityRiskyUser.Read.All</b> en Azure AD. Además, se requiere licenciamiento <b>Microsoft Entra ID P2</b> en tu Inquilino.</p>
        </div>
      </div>

      <!-- Tab: Sign Ins -->
      <div v-if="activeTab === 'signIns'">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm">
            <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Ataques Bloqueados</span>
            <div class="text-3xl font-black text-slate-800 mt-2">{{ alerts.length }}</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm">
            <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Fuentes Maliciosas</span>
            <div class="text-3xl font-black text-red-600 mt-2">{{ uniqueIPs }} <span class="text-[12px] font-medium text-slate-500">IPs</span></div>
          </div>
          <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm">
            <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Objetivo Principal</span>
            <div class="text-[14px] font-bold text-slate-800 mt-3 truncate">{{ topTarget }}</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-md p-4 shadow-sm flex flex-col justify-end">
            <input v-model="searchTerm" type="text" placeholder="Buscar IP, país o usuario..." class="w-full px-3 py-1.5 text-[12px] bg-slate-50 border border-slate-200 rounded focus:border-blue-500 outline-none">
          </div>
        </div>

        <div class="bg-white border border-slate-200 rounded-md shadow-sm overflow-hidden">
          <div class="overflow-x-auto min-h-[300px]">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200">
                  <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Fecha / Hora</th>
                  <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Usuario</th>
                  <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Origen</th>
                  <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Estado</th>
                  <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Acción</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-if="loading && alerts.length === 0">
                  <td colspan="5" class="px-5 py-12 text-center text-[12px] text-slate-500">Cargando datos...</td>
                </tr>
                <tr v-for="alert in filteredAlerts" :key="alert.id" class="hover:bg-slate-50 transition-colors">
                  <td class="px-5 py-3 text-[12px] text-slate-700 whitespace-nowrap">{{ formatDateTime(alert.createdDateTime) }}</td>
                  <td class="px-5 py-3">
                    <div class="text-[12px] font-bold text-slate-900">{{ alert.userDisplayName }}</div>
                    <div class="text-[11px] text-slate-500 font-mono">{{ alert.userPrincipalName }}</div>
                  </td>
                  <td class="px-5 py-3">
                    <div class="flex items-center gap-2">
                      <span :title="alert.location?.countryOrRegion">{{ getCountryFlag(alert.location?.countryOrRegion) }}</span>
                      <div>
                        <div class="text-[12px] font-mono font-bold">{{ alert.ipAddress }}</div>
                        <div class="text-[10px] text-slate-500">{{ alert.location?.city }}, {{ alert.location?.countryOrRegion }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="px-5 py-3">
                    <span class="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700 uppercase">{{ getErrorDescription(String(alert.status?.errorCode)) }}</span>
                  </td>
                  <td class="px-5 py-3">
                    <button @click="revokeSessions(alert.userPrincipalName)" class="px-3 py-1 bg-slate-100 hover:bg-red-100 hover:text-red-700 text-slate-600 text-[11px] font-bold rounded transition-colors">Bloquear Sesiones</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab: Risky Users -->
      <div v-if="activeTab === 'riskyUsers'">
        <div v-if="riskyUsers.length === 0 && !loading" class="text-center py-20 bg-white border border-slate-200 rounded-md">
          <svg class="w-16 h-16 text-green-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <h3 class="text-lg font-bold text-slate-800">Cero Usuarios en Riesgo</h3>
          <p class="text-[13px] text-slate-500 mt-1">Ninguna cuenta ha sido comprometida según la IA de Microsoft.</p>
        </div>
        <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-5">
          <div v-for="user in riskyUsers" :key="user.id" class="bg-white border border-red-200 shadow-sm rounded-lg p-5 flex flex-col justify-between">
            <div>
              <div class="flex items-center justify-between mb-3">
                <span class="px-2 py-1 bg-red-100 text-red-700 text-[10px] font-black uppercase rounded tracking-wider">{{ user.riskLevel }} RISK</span>
                <span class="text-[11px] text-slate-400">{{ formatDateTime(user.riskLastUpdatedDateTime) }}</span>
              </div>
              <h3 class="text-[14px] font-bold text-slate-900">{{ user.userDisplayName }}</h3>
              <p class="text-[11px] text-slate-500 font-mono">{{ user.userPrincipalName }}</p>
              <div class="mt-4 p-3 bg-slate-50 rounded border border-slate-100">
                <p class="text-[11px] text-slate-600"><strong>Detalle:</strong> La cuenta ha detectado anomalías críticas o sus credenciales fueron filtradas.</p>
              </div>
            </div>
            <button @click="revokeSessions(user.userPrincipalName)" class="mt-5 w-full py-2 bg-slate-900 hover:bg-black text-white text-[12px] font-bold rounded shadow-sm transition-colors">
              Revocar Sesiones Ahora
            </button>
          </div>
        </div>
      </div>

      <!-- Tab: Risk Detections -->
      <div v-if="activeTab === 'riskDetections'">
        <div class="bg-white border border-slate-200 rounded-md shadow-sm overflow-hidden">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200">
                <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Detección</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Usuario</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Origen</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Nivel</th>
                <th class="px-5 py-3 text-[10px] font-bold text-slate-500 uppercase">Fecha</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-if="riskDetections.length === 0">
                <td colspan="5" class="px-5 py-12 text-center text-[12px] text-slate-500">No hay detecciones de riesgo recientes.</td>
              </tr>
              <tr v-for="det in riskDetections" :key="det.id" class="hover:bg-slate-50">
                <td class="px-5 py-3 text-[12px] font-bold text-amber-700">{{ det.riskEventType }}</td>
                <td class="px-5 py-3 text-[12px] font-medium text-slate-800">{{ det.userDisplayName }}</td>
                <td class="px-5 py-3 text-[12px] font-mono text-slate-600">{{ det.ipAddress || 'N/A' }}</td>
                <td class="px-5 py-3"><span class="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-bold rounded uppercase">{{ det.riskLevel }}</span></td>
                <td class="px-5 py-3 text-[11px] text-slate-500">{{ formatDateTime(det.detectedDateTime) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>
  </div>
</template>
