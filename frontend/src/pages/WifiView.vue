<script setup>
import { ref, onMounted, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

const currentTab = ref('clients')
const error = ref('')
const loading = ref(false)
const processingMac = ref('')

const clients = ref([])
const aps = ref([])

// Filtros Clientes
const searchQuery = ref('')
const selectedAp = ref('')
const showOnlyBlocked = ref(false)

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...(opts.headers || {}) } })
}

const loadAps = async () => {
  loading.value = true
  try {
    const res = await authFetch(`${API_BASE}/wifi/aps`)
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
  loading.value = true
  try {
    const res = await authFetch(`${API_BASE}/wifi/clients`)
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

const filteredClients = computed(() => {
  return clients.value.filter(c => {
    // Buscar texto
    const textMatch = !searchQuery.value || (c.hostname && c.hostname.toLowerCase().includes(searchQuery.value.toLowerCase())) || (c.mac && c.mac.toLowerCase().includes(searchQuery.value.toLowerCase()))
    
    // Filtro AP
    const apMatch = !selectedAp.value || c.ap_mac === selectedAp.value

    // Filtro Bloqueados
    const blockMatch = !showOnlyBlocked.value || c.is_blocked

    return textMatch && apMatch && blockMatch
  })
})

const getApName = (mac) => {
  const ap = aps.value.find(a => a.mac === mac)
  return ap ? ap.name : mac
}

const toggleBlock = async (client) => {
  processingMac.value = client.mac
  try {
    const endpoint = client.is_blocked ? 'unblock' : 'block'
    const res = await authFetch(`${API_BASE}/wifi/clients/${client.mac}/${endpoint}`, { method: 'POST' })
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
  if (!confirm(`Â¿EstÃ¡s seguro de reiniciar el Access Point: ${ap.name}?`)) return
  processingMac.value = ap.mac
  try {
    const res = await authFetch(`${API_BASE}/wifi/aps/${ap.mac}/restart`, { method: 'POST' })
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

onMounted(() => {
  loadAps()
  loadClients()
})
</script>

<template>
  <div class="h-full flex flex-col font-sans">
    
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
      <div>
        <h1 class="text-xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
          <svg class="w-6 h-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
          </svg>
          Gestión Wi-Fi (UniFi)
        </h1>
        <p class="text-sm text-slate-500 mt-1">Centraliza y administra dispositivos inalámbricos y clientes conectados.</p>
      </div>
      
      <div class="flex gap-2">
        <button @click="loadAps(); loadClients()" class="flex items-center gap-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-3 py-1.5 rounded-sm text-sm font-medium transition-colors shadow-sm">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-sm text-sm mb-4 flex gap-3">
      <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      {{ error }}
    </div>

    <!-- Tabs -->
    <div class="flex gap-4 border-b border-slate-200 mb-4 px-1">
      <button 
        @click="currentTab = 'clients'" 
        :class="['pb-2 text-sm font-medium transition-colors border-b-2', currentTab === 'clients' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300']">
        Clientes Wi-Fi
      </button>
      <button 
        @click="currentTab = 'aps'" 
        :class="['pb-2 text-sm font-medium transition-colors border-b-2', currentTab === 'aps' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300']">
        Access Points (Hardware)
      </button>
    </div>

    <!-- Contenido Tabs -->
    <div class="flex-1 bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden flex flex-col">
      <div v-if="loading" class="flex-1 flex items-center justify-center">
        <span class="w-8 h-8 border-2 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></span>
      </div>
      
      <!-- TAB CLIENTES -->
      <template v-else-if="currentTab === 'clients'">
        <div class="p-3 border-b border-slate-200 bg-slate-50 flex flex-wrap gap-4 items-center">
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="Buscar por Nombre o MAC..." 
            class="flex-1 min-w-[200px] max-w-sm px-3 py-1.5 border border-slate-300 rounded-sm text-[13px] focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
          <select 
            v-model="selectedAp" 
            class="px-3 py-1.5 border border-slate-300 rounded-sm text-[13px] text-slate-700 bg-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="">Todos los APs</option>
            <option v-for="ap in aps" :key="ap.mac" :value="ap.mac">{{ ap.name }}</option>
          </select>
          <label class="flex items-center gap-2 text-[13px] text-slate-700 cursor-pointer">
            <input type="checkbox" v-model="showOnlyBlocked" class="rounded text-indigo-600 focus:ring-indigo-500">
            Mostrar solo bloqueados
          </label>
        </div>
        
        <div class="flex-1 overflow-auto">
          <table class="w-full text-left text-[13px]">
            <thead class="bg-slate-50 border-b border-slate-200 sticky top-0 z-10 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th class="px-5 py-3">Dispositivo (Hostname)</th>
                <th class="px-5 py-3">Dirección IP</th>
                <th class="px-5 py-3">Dirección MAC</th>
                <th class="px-5 py-3">Punto de Acceso</th>
                <th class="px-5 py-3">Estado</th>
                <th class="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-slate-700">
              <tr v-if="filteredClients.length === 0">
                <td colspan="6" class="px-5 py-8 text-center text-slate-500">No se encontraron clientes con esos filtros.</td>
              </tr>
              <tr v-for="client in filteredClients" :key="client.mac" class="hover:bg-slate-50 transition-colors">
                <td class="px-5 py-2 font-medium text-slate-800">{{ client.hostname }}</td>
                <td class="px-5 py-2 font-mono text-slate-600">{{ client.ip || 'N/A' }}</td>
                <td class="px-5 py-2 font-mono text-slate-500 text-[11px] uppercase">{{ client.mac }}</td>
                <td class="px-5 py-2">{{ getApName(client.ap_mac) }}</td>
                <td class="px-5 py-2">
                  <span v-if="client.is_blocked" class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-800">
                    Bloqueado
                  </span>
                  <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800">
                    Activo
                  </span>
                </td>
                <td class="px-5 py-2 text-right">
                  <button 
                    @click="toggleBlock(client)" 
                    :disabled="processingMac === client.mac"
                    :class="[
                      'border px-3 py-1 text-[11px] rounded-sm font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-1 ml-auto min-w-[90px]',
                      client.is_blocked ? 'border-emerald-600 text-emerald-700 hover:bg-emerald-50' : 'border-red-600 text-red-700 hover:bg-red-50'
                    ]"
                  >
                    <svg v-if="processingMac === client.mac" class="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin shrink-0"></svg>
                    <span>{{ client.is_blocked ? 'Desbloquear' : 'Bloquear' }}</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      
      <!-- TAB APs -->
      <template v-else-if="currentTab === 'aps'">
        <div class="flex-1 overflow-auto">
          <table class="w-full text-left text-[13px]">
            <thead class="bg-slate-50 border-b border-slate-200 sticky top-0 z-10 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th class="px-5 py-3">Nombre AP</th>
                <th class="px-5 py-3">DirecciÃ³n IP</th>
                <th class="px-5 py-3">Modelo</th>
                <th class="px-5 py-3">Estado</th>
                <th class="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-slate-700">
              <tr v-if="aps.length === 0">
                <td colspan="5" class="px-5 py-8 text-center text-slate-500">No hay Access Points registrados.</td>
              </tr>
              <tr v-for="ap in aps" :key="ap.mac" class="hover:bg-slate-50 transition-colors">
                <td class="px-5 py-3 font-medium text-slate-800">{{ ap.name }}</td>
                <td class="px-5 py-3 font-mono text-slate-600">{{ ap.ip }}</td>
                <td class="px-5 py-3 text-slate-500">{{ ap.model }}</td>
                <td class="px-5 py-3">
                  <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[11px] font-medium border"
                    :class="ap.status === 'online' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200'">
                    <span class="w-1.5 h-1.5 rounded-full" :class="ap.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'"></span>
                    {{ ap.status === 'online' ? 'Online' : 'Offline' }}
                  </span>
                </td>
                <td class="px-5 py-3 text-right">
                  <button 
                    @click="restartAp(ap)" 
                    :disabled="processingMac === ap.mac || ap.status !== 'online'"
                    class="border border-amber-600 text-amber-700 hover:bg-amber-50 px-3 py-1 text-[11px] rounded-sm font-medium transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-1 min-w-[80px]"
                    title="Reiniciar Access Point"
                  >
                    <svg v-if="processingMac === ap.mac" class="w-3 h-3 animate-spin shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    <svg v-else class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    <span>Reiniciar</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

    </div>
  </div>
</template>
