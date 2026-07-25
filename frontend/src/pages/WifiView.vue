<script setup>
import { ref, onMounted, computed, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

const currentTab = ref('aps')
const error = ref('')
const loading = ref(false)
const processingMac = ref('')

const sites = ref([])
const selectedSite = ref('')
const clients = ref([])
const aps = ref([])

// Filtros Clientes
const searchQuery = ref('')
const selectedAp = ref('')
const clientStatusFilter = ref('all') // 'all', 'active', 'blocked'

// Filtros APs
const apFilter = ref('all') // 'all' o 'offline'
const selectedApDetails = ref(null) // Para el Modal
const modalTab = ref('active') // 'active' o 'history'
const historicalClients = ref([])
const loadingHistory = ref(false)

// KPIs
const totalAps = computed(() => aps.value.length)
const onlineAps = computed(() => aps.value.filter(a => a.status === 'online').length)
const offlineAps = computed(() => aps.value.filter(a => a.status !== 'online').length)
const onlinePercentage = computed(() => totalAps.value > 0 ? Math.round((onlineAps.value / totalAps.value) * 100) : 0)

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...(opts.headers || {}) } })
}

const loadSites = async () => {
  loading.value = true
  try {
    const res = await authFetch(`${API_BASE}/wifi/sites`)
    const data = await res.json()
    if (res.ok && data.success) {
      sites.value = data.data
      if (sites.value.length > 0 && !selectedSite.value) {
        selectedSite.value = sites.value[0].name
      }
    } else {
      error.value = data.detail || 'Error cargando sitios'
    }
  } catch (e) {
    error.value = 'Fallo de red conectando con el backend (Sitios)'
  } finally {
    loading.value = false
  }
}

const loadAps = async () => {
  if (!selectedSite.value) return
  loading.value = true
  try {
    const res = await authFetch(`${API_BASE}/wifi/aps?site=${selectedSite.value}`)
    const data = await res.json()
    if (res.ok && data.success) {
      aps.value = data.data
    } else {
      error.value = data.detail || 'Error cargando Access Points'
    }
  } catch (e) {
    error.value = 'Fallo de red conectando con el backend'
  } finally {
    loading.value = false
  }
}

const loadClients = async () => {
  if (!selectedSite.value) return
  loading.value = true
  try {
    const res = await authFetch(`${API_BASE}/wifi/clients?site=${selectedSite.value}`)
    const data = await res.json()
    if (res.ok && data.success) {
      clients.value = data.data
    } else {
      error.value = data.detail || 'Error cargando Clientes'
    }
  } catch (e) {
    error.value = 'Fallo de red conectando con el backend'
  } finally {
    loading.value = false
  }
}

const loadData = () => {
  if (selectedSite.value) {
    loadAps()
    loadClients()
  }
}

const filteredClients = computed(() => {
  return clients.value.filter(c => {
    const textMatch = !searchQuery.value || (c.hostname && c.hostname.toLowerCase().includes(searchQuery.value.toLowerCase())) || (c.mac && c.mac.toLowerCase().includes(searchQuery.value.toLowerCase()))
    const apMatch = !selectedAp.value || c.ap_mac === selectedAp.value
    
    // Filtro Cruzado de Estado
    let statusMatch = true
    if (clientStatusFilter.value === 'blocked') statusMatch = c.is_blocked
    if (clientStatusFilter.value === 'active') statusMatch = !c.is_blocked

    return textMatch && apMatch && statusMatch
  })
})

const sortedAps = computed(() => {
  let filtered = aps.value;
  if (apFilter.value === 'offline') {
    filtered = filtered.filter(a => a.status !== 'online');
  }
  return [...filtered].sort((a, b) => {
    if (a.status !== 'online' && b.status === 'online') return -1;
    if (a.status === 'online' && b.status !== 'online') return 1;
    return (a.name || '').localeCompare(b.name || '');
  })
})

const getApName = (mac) => {
  const ap = aps.value.find(a => a.mac === mac)
  return ap ? ap.name : mac
}

const clientsForSelectedAp = computed(() => {
  if (!selectedApDetails.value) return [];
  return clients.value.filter(c => c.ap_mac === selectedApDetails.value.mac);
})

const activeClientsForAp = computed(() => clientsForSelectedAp.value.filter(c => !c.is_blocked))
const blockedClientsForAp = computed(() => clientsForSelectedAp.value.filter(c => c.is_blocked))
const showBlockedInModal = ref(false)

const toggleBlock = async (client) => {
  processingMac.value = client.mac
  try {
    const endpoint = client.is_blocked ? 'unblock' : 'block'
    const res = await authFetch(`${API_BASE}/wifi/clients/${client.mac}/${endpoint}?site=${selectedSite.value}`, { method: 'POST' })
    if (res.ok) {
      client.is_blocked = !client.is_blocked
    } else {
      const err = await res.json()
      alert(`Error: ${err.detail}`)
    }
  } catch (e) {
    alert('Fallo al ejecutar el comando')
  } finally {
    processingMac.value = ''
  }
}

const restartAp = async (ap) => {
  if (!confirm(`¿Estás seguro de reiniciar el Access Point: ${ap.name}?`)) return
  processingMac.value = ap.mac
  try {
    const res = await authFetch(`${API_BASE}/wifi/aps/${ap.mac}/restart?site=${selectedSite.value}`, { method: 'POST' })
    if (res.ok) {
      alert(`Reinicio enviado a ${ap.name}`)
    } else {
      const err = await res.json()
      alert(`Error: ${err.detail}`)
    }
  } catch (e) {
    alert('Fallo al ejecutar el comando')
  } finally {
    processingMac.value = ''
  }
}

const loadApHistory = async (mac) => {
  loadingHistory.value = true
  historicalClients.value = []
  try {
    const res = await authFetch(`${API_BASE}/wifi/aps/${mac}/history?site=${selectedSite.value}`)
    const data = await res.json()
    if (res.ok && data.success) {
      historicalClients.value = data.data
    }
  } catch (e) {
    console.error("Error loading AP history", e)
  } finally {
    loadingHistory.value = false
  }
}

const openApDetails = (ap) => {
  selectedApDetails.value = ap
  modalTab.value = 'active'
  showBlockedInModal.value = false
  loadApHistory(ap.mac)
}

watch(selectedSite, (newSite) => {
  if (newSite) loadData()
})

onMounted(async () => {
  await loadSites()
  if (selectedSite.value) {
    loadData()
  }
})
</script>

<template>
  <div class="h-full flex flex-col font-sans max-w-7xl mx-auto w-full p-4 sm:p-6 lg:p-8 relative">
    
    <!-- Modal Historial AP (Offcanvas / Modal guiado por Guidelines) -->
    <div v-if="selectedApDetails" class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/20 backdrop-blur-[2px]">
      <div class="bg-white max-w-2xl w-full rounded-xl shadow-lg border border-gray-100 overflow-hidden flex flex-col relative h-[80vh]">
        <!-- Modal Header -->
        <div class="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
          <div>
            <h2 class="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
              </svg>
              {{ selectedApDetails.name }}
            </h2>
            <div class="flex gap-4 mt-3">
              <button @click="modalTab = 'active'" :class="['text-sm font-medium transition-colors relative pb-1', modalTab === 'active' ? 'text-gray-900 after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-gray-900' : 'text-gray-500 hover:text-gray-700']">Activos Ahora ({{ clientsForSelectedAp.length }})</button>
              <button @click="modalTab = 'history'" :class="['text-sm font-medium transition-colors relative pb-1', modalTab === 'history' ? 'text-gray-900 after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-gray-900' : 'text-gray-500 hover:text-gray-700']">Historial de Conexiones</button>
            </div>
          </div>
          <button @click="selectedApDetails = null" class="absolute right-6 top-4 text-gray-400 hover:text-gray-600 transition-colors">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        <!-- Modal Body -->
        <div class="p-0 text-sm text-gray-600 overflow-y-auto flex-1">
          
          <!-- TAB ACTIVOS -->
          <template v-if="modalTab === 'active'">
            <div v-if="clientsForSelectedAp.length === 0" class="text-center py-16 px-6">
              <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>No hay clientes conectados a este AP en este momento.</p>
            </div>
            <table v-else class="w-full text-left text-sm border-collapse">
              <thead class="text-gray-500 font-medium text-xs border-b border-gray-100 bg-white sticky top-0 z-10">
                <tr>
                  <th class="px-6 py-3">Dispositivo</th>
                  <th class="px-6 py-3">Red (IP / MAC)</th>
                  <th class="px-6 py-3 text-right">Estado</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <!-- Activos -->
                <tr v-for="client in activeClientsForAp" :key="client.mac" class="hover:bg-gray-50 transition-colors">
                  <td class="px-6 py-3 font-medium text-gray-900">{{ client.hostname || 'Dispositivo Desconocido' }}</td>
                  <td class="px-6 py-3">
                    <div class="font-mono text-[11px] text-gray-900">{{ client.ip || 'Sin IP' }}</div>
                    <div class="font-mono text-[10px] text-gray-400 uppercase mt-0.5">{{ client.mac }}</div>
                  </td>
                  <td class="px-6 py-3 text-right">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-green-50 text-green-700">
                      Activo
                    </span>
                  </td>
                </tr>
                
                <!-- Botón Desplegable para Bloqueados -->
                <tr v-if="blockedClientsForAp.length > 0">
                  <td colspan="3" class="px-6 py-3 text-center bg-gray-50">
                    <button @click="showBlockedInModal = !showBlockedInModal" class="inline-flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-gray-800 transition-colors">
                      <svg class="w-4 h-4 transition-transform" :class="{'rotate-180': showBlockedInModal}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                      {{ showBlockedInModal ? 'Ocultar' : 'Ver' }} {{ blockedClientsForAp.length }} dispositivos bloqueados
                    </button>
                  </td>
                </tr>

                <!-- Bloqueados -->
                <template v-if="showBlockedInModal">
                  <tr v-for="client in blockedClientsForAp" :key="client.mac" class="hover:bg-gray-50 transition-colors opacity-75">
                    <td class="px-6 py-3 font-medium text-gray-900 line-through decoration-gray-300">{{ client.hostname || 'Dispositivo Desconocido' }}</td>
                    <td class="px-6 py-3">
                      <div class="font-mono text-[11px] text-gray-900">{{ client.ip || 'Sin IP' }}</div>
                      <div class="font-mono text-[10px] text-gray-400 uppercase mt-0.5">{{ client.mac }}</div>
                    </td>
                    <td class="px-6 py-3 text-right">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-red-50 text-red-700 border border-red-100">
                        Bloqueado
                      </span>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </template>

          <!-- TAB HISTORIAL -->
          <template v-else-if="modalTab === 'history'">
            <div v-if="loadingHistory" class="flex justify-center items-center py-16">
              <span class="w-6 h-6 border-2 border-gray-200 border-t-gray-800 rounded-full animate-spin"></span>
            </div>
            <div v-else-if="historicalClients.length === 0" class="text-center py-16 px-6">
              <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 00.75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 00-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0112 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 01-.673-.38m0 0A2.18 2.18 0 013 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 013.413-.387m7.5 0V5.25A2.25 2.25 0 0013.5 3h-3a2.25 2.25 0 00-2.25 2.25v.894m7.5 0a48.667 48.667 0 00-7.5 0M12 12.75h.008v.008H12v-.008z" />
              </svg>
              <p>No hay historial de clientes para este AP.</p>
            </div>
            <table v-else class="w-full text-left text-sm border-collapse">
              <thead class="text-gray-500 font-medium text-xs border-b border-gray-100 bg-white sticky top-0 z-10">
                <tr>
                  <th class="px-6 py-3">Dispositivo</th>
                  <th class="px-6 py-3">Red (IP / MAC)</th>
                  <th class="px-6 py-3 text-right">Última Conexión</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="client in historicalClients" :key="client.mac" class="hover:bg-gray-50 transition-colors">
                  <td class="px-6 py-3 font-medium text-gray-900 flex items-center gap-2">
                    {{ client.hostname || 'Desconocido' }}
                    <span v-if="client.is_blocked" class="bg-red-100 text-red-700 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase">Block</span>
                  </td>
                  <td class="px-6 py-3">
                    <div class="font-mono text-[11px] text-gray-900">{{ client.ip || '-' }}</div>
                    <div class="font-mono text-[10px] text-gray-400 uppercase mt-0.5">{{ client.mac }}</div>
                  </td>
                  <td class="px-6 py-3 text-right text-xs text-gray-500">
                    {{ client.last_seen ? new Date(client.last_seen * 1000).toLocaleString() : 'Desconocida' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </template>

        </div>
        <!-- Modal Footer -->
        <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3 mt-auto">
          <button @click="selectedApDetails = null" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-100 transition-colors">
            Cerrar
          </button>
        </div>
      </div>
    </div>

    <!-- Header Minimalista -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
      <div>
        <h1 class="text-2xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
          <svg class="w-6 h-6 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
          </svg>
          Gestión de Red Inalámbrica
        </h1>
        <p class="text-sm text-gray-500 mt-1">Monitoreo de Access Points y dispositivos conectados (UniFi).</p>
      </div>
      
      <div class="flex items-center gap-3">
        <select 
          v-if="sites.length > 0"
          v-model="selectedSite" 
          class="border border-gray-200 bg-gray-50 text-gray-700 py-2 pl-3 pr-8 rounded-lg text-sm font-medium focus:ring-2 focus:ring-gray-200 outline-none"
        >
          <option v-for="site in sites" :key="site.name" :value="site.name">{{ site.desc }}</option>
        </select>
        <button @click="loadData()" class="flex items-center gap-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="bg-gray-50 border border-gray-200 text-gray-700 p-4 rounded-lg text-sm mb-6 flex gap-3 items-center">
      <svg class="w-5 h-5 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      {{ error }}
    </div>

    <!-- KPIs Grid (Visible solo en APs) -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8" v-if="currentTab === 'aps'">
      
      <!-- Total APs -->
      <div class="bg-gray-50 rounded-xl p-5 border border-gray-100 flex flex-col justify-center relative overflow-hidden">
        <div class="flex justify-between items-start mb-2">
          <span class="text-sm font-medium text-gray-500">Total Access Points</span>
          <span class="p-1.5 bg-gray-200 rounded-md text-gray-600">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </span>
        </div>
        <div class="flex items-end gap-2">
          <span class="text-3xl font-semibold text-gray-900">{{ totalAps }}</span>
        </div>
      </div>
      
      <!-- Online / Health -->
      <div class="bg-gray-50 rounded-xl p-5 border border-gray-100 flex flex-col justify-center relative overflow-hidden">
        <div class="flex justify-between items-start mb-2">
          <span class="text-sm font-medium text-gray-500">Online & Health</span>
          <span class="p-1.5 bg-green-100 rounded-md text-green-700">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </span>
        </div>
        <div class="flex items-end gap-3">
          <span class="text-3xl font-semibold text-green-600">{{ onlineAps }}</span>
          <span class="text-sm text-gray-500 mb-1 font-medium">{{ onlinePercentage }}% Health</span>
        </div>
        <!-- Progress Bar Background -->
        <div class="w-full bg-gray-200 rounded-full h-1.5 mt-4">
          <div class="bg-green-500 h-1.5 rounded-full" :style="{ width: onlinePercentage + '%' }"></div>
        </div>
      </div>

      <!-- Offline / Alertas -->
      <div class="bg-gray-50 rounded-xl p-5 border border-gray-100 flex flex-col justify-center relative overflow-hidden">
        <div class="flex justify-between items-start mb-2">
          <span class="text-sm font-medium text-gray-500">Offline / Alertas</span>
          <span class="p-1.5 bg-red-100 rounded-md text-red-700">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          </span>
        </div>
        <div class="flex items-end gap-2">
          <span class="text-3xl font-semibold text-red-600">{{ offlineAps }}</span>
          <span class="text-sm text-gray-500 mb-1 font-medium" v-if="offlineAps > 0">Requieren atención</span>
        </div>
      </div>

    </div>

    <!-- Tabs & Búsqueda alineados -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-gray-100 pb-4 mb-4 gap-4">
      <!-- Tabs Izquierda -->
      <div class="flex gap-6">
        <button 
          @click="currentTab = 'aps'" 
          :class="['text-sm font-medium transition-colors relative pb-4 -mb-4', currentTab === 'aps' ? 'text-gray-900 after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-gray-900' : 'text-gray-500 hover:text-gray-700']">
          Access Points
        </button>
        <button 
          @click="currentTab = 'clients'" 
          :class="['text-sm font-medium transition-colors relative pb-4 -mb-4', currentTab === 'clients' ? 'text-gray-900 after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-gray-900' : 'text-gray-500 hover:text-gray-700']">
          Clientes Wi-Fi
        </button>
      </div>
      
      <!-- Filtros Derecha -->
      <div class="flex items-center gap-3">
        <!-- Filtros de Clientes -->
        <template v-if="currentTab === 'clients'">
          <select v-model="selectedAp" class="border border-gray-200 bg-gray-50 text-gray-700 py-1.5 px-3 rounded-md text-sm outline-none focus:border-gray-300">
            <option value="">Todos los APs</option>
            <option v-for="ap in aps" :key="ap.mac" :value="ap.mac">{{ ap.name }}</option>
          </select>
          <!-- Filtro de estado para Clientes -->
          <div class="flex bg-gray-100 p-1 rounded-lg">
            <button @click="clientStatusFilter = 'all'" :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', clientStatusFilter === 'all' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">Todos</button>
            <button @click="clientStatusFilter = 'active'" :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', clientStatusFilter === 'active' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">Activos</button>
            <button @click="clientStatusFilter = 'blocked'" :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', clientStatusFilter === 'blocked' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">Bloqueados</button>
          </div>
          <!-- Búsqueda -->
          <div class="relative ml-2">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
            <input type="text" v-model="searchQuery" placeholder="Buscar por MAC o Hostname..." class="border border-gray-200 bg-white text-gray-900 py-1.5 pl-9 pr-3 rounded-md text-sm w-64 outline-none focus:border-gray-300 transition-colors">
          </div>
        </template>

        <!-- Filtros de APs -->
        <template v-if="currentTab === 'aps'">
          <div class="flex bg-gray-100 p-1 rounded-lg">
            <button @click="apFilter = 'all'" :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', apFilter === 'all' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">Todos</button>
            <button @click="apFilter = 'offline'" :class="['px-3 py-1 text-xs font-medium rounded-md transition-colors', apFilter === 'offline' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700']">Solo Offline</button>
          </div>
        </template>
      </div>
    </div>

    <!-- Data Grids sin bordes fuertes (Guidelines) -->
    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="flex-1 flex items-center justify-center p-12">
        <span class="w-6 h-6 border-2 border-gray-200 border-t-gray-800 rounded-full animate-spin"></span>
      </div>
      
      <!-- TAB APs -->
      <table v-else-if="currentTab === 'aps'" class="w-full text-left text-sm border-collapse">
        <thead class="text-gray-500 font-medium text-xs border-b border-gray-100">
          <tr>
            <th class="px-2 py-3 font-medium">Access Point</th>
            <th class="px-4 py-3 font-medium">Dirección IP</th>
            <th class="px-4 py-3 font-medium">Modelo</th>
            <th class="px-4 py-3 font-medium">Estado</th>
            <th class="px-4 py-3 font-medium w-48">Experiencia / Clientes</th>
            <th class="px-2 py-3 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody class="text-gray-600">
          <tr v-if="sortedAps.length === 0">
            <td colspan="6" class="px-4 py-12 text-center text-gray-400">No hay Access Points para mostrar.</td>
          </tr>
          <tr v-for="ap in sortedAps" :key="ap.mac" class="hover:bg-gray-50 transition-colors border-b border-gray-50 group">
            <td class="px-2 py-3 font-medium text-gray-900 flex items-center gap-2">
              <svg class="w-5 h-5 text-gray-400 shrink-0 group-hover:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.288 15.038a5.25 5.25 0 017.424 0M5.106 11.856c3.807-3.808 9.98-3.808 13.788 0M1.924 8.674c5.565-5.565 14.587-5.565 20.152 0M12.53 18.22l-.53.53-.53-.53a.75.75 0 011.06 0z" />
              </svg>
              <!-- Nombre interactivo para abrir detalle -->
              <button @click="openApDetails(ap)" class="hover:text-blue-600 hover:underline transition-colors text-left font-semibold">
                {{ ap.name }}
              </button>
            </td>
            <td class="px-4 py-3 font-mono text-xs">{{ ap.ip }}</td>
            <td class="px-4 py-3">{{ ap.model }}</td>
            <td class="px-4 py-3">
              <span v-if="ap.status === 'online'" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700">
                <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                Online
              </span>
              <span v-else class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-100">
                <span class="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                {{ ap.status || 'Offline' }}
              </span>
            </td>
            <td class="px-4 py-3">
              <!-- Barra de Experiencia Real -->
              <div v-if="ap.status === 'online' && ap.clients_count > 0" class="flex items-center gap-3">
                <div class="w-full bg-gray-200 rounded-full h-1.5 flex-1 max-w-[100px]" :title="'Experiencia Wi-Fi: ' + Math.max(0, ap.satisfaction) + '%'">
                  <div 
                    class="h-1.5 rounded-full transition-all duration-500" 
                    :class="ap.satisfaction >= 80 ? 'bg-green-500' : (ap.satisfaction >= 50 ? 'bg-yellow-500' : 'bg-red-500')"
                    :style="{ width: Math.max(0, ap.satisfaction) + '%' }">
                  </div>
                </div>
                <div class="flex flex-col">
                  <span class="text-[10px] font-bold" :class="ap.satisfaction >= 80 ? 'text-green-600' : (ap.satisfaction >= 50 ? 'text-yellow-600' : 'text-red-600')">
                    {{ Math.max(0, ap.satisfaction) }}% Exp.
                  </span>
                  <span class="text-[10px] text-gray-500 font-medium">
                    {{ ap.clients_count }} Clientes
                  </span>
                </div>
              </div>
              <div v-else class="flex items-center gap-3">
                <div class="w-full bg-gray-100 rounded-full h-1.5 flex-1 max-w-[100px]"></div>
                <div class="flex flex-col">
                  <span class="text-[10px] font-bold text-gray-400">N/A</span>
                  <span class="text-[10px] text-gray-400 font-medium">{{ ap.clients_count }} Clientes</span>
                </div>
              </div>
            </td>
            <td class="px-2 py-3 text-right">
              <button 
                @click="restartAp(ap)" 
                :disabled="processingMac === ap.mac || ap.status !== 'online'"
                class="group/btn relative inline-flex items-center justify-center p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-30"
              >
                <svg v-if="processingMac === ap.mac" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                
                <span class="absolute hidden group-hover/btn:block bottom-full mb-1 right-0 w-max bg-gray-900 text-white text-[10px] px-2 py-1 rounded shadow-sm z-10">
                  Reiniciar AP
                </span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- TAB CLIENTES -->
      <table v-else-if="currentTab === 'clients'" class="w-full text-left text-sm border-collapse">
        <thead class="text-gray-500 font-medium text-xs border-b border-gray-100">
          <tr>
            <th class="px-2 py-3 font-medium">Dispositivo</th>
            <th class="px-4 py-3 font-medium">IP</th>
            <th class="px-4 py-3 font-medium">MAC</th>
            <th class="px-4 py-3 font-medium">AP Conectado</th>
            <th class="px-4 py-3 font-medium">Estado</th>
            <th class="px-2 py-3 font-medium text-right">Acciones</th>
          </tr>
        </thead>
        <tbody class="text-gray-600">
          <tr v-if="filteredClients.length === 0">
            <td colspan="6" class="px-4 py-12 text-center text-gray-400">No se encontraron clientes que coincidan con los filtros.</td>
          </tr>
          <tr v-for="client in filteredClients" :key="client.mac" class="hover:bg-gray-50 transition-colors border-b border-gray-50">
            <td class="px-2 py-3 font-medium text-gray-900">{{ client.hostname }}</td>
            <td class="px-4 py-3 font-mono text-xs">{{ client.ip || '-' }}</td>
            <td class="px-4 py-3 font-mono text-xs uppercase">{{ client.mac }}</td>
            <td class="px-4 py-3">{{ getApName(client.ap_mac) }}</td>
            <td class="px-4 py-3">
              <span v-if="client.is_blocked" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                Bloqueado
              </span>
              <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium text-gray-500">
                Activo
              </span>
            </td>
            <td class="px-2 py-3 text-right">
              <button 
                @click="toggleBlock(client)" 
                :disabled="processingMac === client.mac"
                class="text-xs font-medium transition-colors disabled:opacity-50"
                :class="client.is_blocked ? 'text-blue-600 hover:text-blue-800' : 'text-gray-400 hover:text-gray-600'"
              >
                {{ client.is_blocked ? 'Desbloquear' : 'Bloquear' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

    </div>
  </div>
</template>
