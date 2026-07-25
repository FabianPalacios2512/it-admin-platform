<script setup>
import { ref, onMounted, computed } from 'vue'

const logs = ref([])
const adLogs = ref([])
const isLoading = ref(false)
const filterSource = ref('')
const filterAction = ref('')
const activeTab = ref('web') // 'web' o 'ad'

const API_BASE = '/api/v1'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('access_token')
  opts.headers = { ...(opts.headers || {}), 'Authorization': `Bearer ${token}` }
  return fetch(url, opts)
}

async function fetchLogs() {
  isLoading.value = true
  try {
    if (activeTab.value === 'web') {
      let url = `${API_BASE}/audit?limit=200`
      if (filterSource.value) url += `&source=${encodeURIComponent(filterSource.value)}`
      if (filterAction.value) url += `&action=${encodeURIComponent(filterAction.value)}`
      
      const res = await authFetch(url)
      if (res.ok) {
        logs.value = await res.json()
      }
    } else {
      let url = `${API_BASE}/audit/ad-events?limit=200`
      const res = await authFetch(url)
      if (res.ok) {
        const data = await res.json()
        if (data.success) {
            adLogs.value = data.data
        } else {
            console.error('Error in AD events:', data.error)
        }
      }
    }
  } catch (err) {
    console.error(err)
  } finally {
    isLoading.value = false
  }
}

function formatDate(ds) {
  if (!ds) return ''
  const d = new Date(ds)
  return d.toLocaleString()
}

onMounted(() => {
  fetchLogs()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6">
    <div class="mb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600 font-medium">Auditoría IT</span>
      </div>
      <h2 class="text-2xl font-semibold text-slate-900 tracking-tight">Auditoría Profunda de AD (IT Compliance)</h2>
      <p class="mt-2 text-sm text-slate-500">
        Registro inmutable de acciones críticas de seguridad. Incluye operaciones en plataforma y eventos directos en los Controladores de Dominio.
      </p>
    </div>

    <!-- Pestañas -->
    <div class="border-b border-slate-200 mb-6">
      <nav class="-mb-px flex gap-6" aria-label="Tabs">
        <button 
          @click="activeTab = 'web'; fetchLogs()" 
          :class="['whitespace-nowrap pb-3 px-1 border-b-2 font-medium text-sm', activeTab === 'web' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300']"
        >
          Acciones en Plataforma Web
        </button>
        <button 
          @click="activeTab = 'ad'; fetchLogs()" 
          :class="['whitespace-nowrap pb-3 px-1 border-b-2 font-medium text-sm flex items-center gap-2', activeTab === 'ad' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300']"
        >
          Event Viewer (Directorio Activo)
          <span class="bg-indigo-100 text-indigo-600 py-0.5 px-2 rounded-full text-[10px]">Nuevo</span>
        </button>
      </nav>
    </div>

    <!-- Filtros (solo para web) -->
    <div v-if="activeTab === 'web'" class="bg-white p-4 rounded-lg border border-slate-200 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-xs font-medium text-slate-700 mb-1">Origen</label>
        <select v-model="filterSource" class="text-sm rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 py-2 pl-3 pr-8 border">
          <option value="">Todos los orígenes</option>
          <option value="Web">Plataforma Web</option>
          <option value="AD Nativo">Active Directory (Nativo)</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-medium text-slate-700 mb-1">Acción</label>
        <select v-model="filterAction" class="text-sm rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 py-2 pl-3 pr-8 border">
          <option value="">Todas las acciones</option>
          <option value="Desbloqueó">Desbloqueos</option>
          <option value="Reset">Reseteos de Clave</option>
          <option value="Habilitó">Habilitaciones</option>
          <option value="Deshabilitó">Deshabilitaciones</option>
          <option value="Grupo">Modificación de Grupos</option>
          <option value="atributos">Cambio de atributos</option>
        </select>
      </div>
      <button @click="fetchLogs" class="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
        Filtrar
      </button>
      <button @click="filterSource=''; filterAction=''; fetchLogs()" class="bg-white text-slate-700 border border-slate-300 px-4 py-2 rounded-md text-sm font-medium hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
        Limpiar
      </button>
    </div>

    <!-- Tabla (Web) -->
    <div v-if="activeTab === 'web'" class="bg-white shadow-sm ring-1 ring-slate-200 rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-slate-200">
        <thead class="bg-slate-50">
          <tr>
            <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-slate-900 sm:pl-6">Fecha/Hora</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Usuario (Autor)</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Acción</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Objetivo / Afectado</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Origen</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200 bg-white">
          <tr v-if="isLoading">
            <td colspan="5" class="px-3 py-10 text-center text-sm text-slate-500">
              Cargando registros...
            </td>
          </tr>
          <tr v-else-if="logs.length === 0">
            <td colspan="5" class="px-3 py-10 text-center text-sm text-slate-500">
              No se encontraron registros de auditoría.
            </td>
          </tr>
          <tr v-else v-for="log in logs" :key="log.id" class="hover:bg-slate-50">
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-slate-500 sm:pl-6">{{ formatDate(log.timestamp) }}</td>
            <td class="whitespace-nowrap px-3 py-4 text-sm font-medium text-slate-900">{{ log.username }}</td>
            <td class="px-3 py-4 text-sm">
              <span :class="[
                'inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset',
                log.action.includes('Reset') || log.action.includes('Deshabilitó') || log.action.includes('atributos') || log.action.includes('Offboarding') ? 'bg-red-50 text-red-700 ring-red-600/10' : 'bg-blue-50 text-blue-700 ring-blue-700/10'
              ]">
                {{ log.action }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-slate-500">{{ log.target }}</td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-slate-500">
              <span v-if="log.source === 'Web'" class="inline-flex items-center gap-1.5">
                <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                Web
              </span>
              <span v-else class="inline-flex items-center gap-1.5">
                <span class="h-1.5 w-1.5 rounded-full bg-indigo-500"></span>
                AD Nativo
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Tabla (AD Nativo) -->
    <div v-if="activeTab === 'ad'" class="bg-white shadow-sm ring-1 ring-slate-200 rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-slate-200">
        <thead class="bg-slate-50">
          <tr>
            <th scope="col" class="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-slate-900 sm:pl-6">Fecha (Log AD)</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Admin (Autor)</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Acción Crítica</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">Usuario Afectado</th>
            <th scope="col" class="px-3 py-3.5 text-left text-sm font-semibold text-slate-900">EventID</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-200 bg-white">
          <tr v-if="isLoading">
            <td colspan="5" class="px-3 py-10 text-center text-sm text-slate-500">
              Consultando logs de seguridad en el Event Viewer...
            </td>
          </tr>
          <tr v-else-if="adLogs.length === 0">
            <td colspan="5" class="px-3 py-10 text-center text-sm text-slate-500">
              No se encontraron eventos críticos recientes en AD.
            </td>
          </tr>
          <tr v-else v-for="(log, idx) in adLogs" :key="idx" class="hover:bg-slate-50">
            <td class="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-slate-500 sm:pl-6">{{ log.TimeCreated }}</td>
            <td class="whitespace-nowrap px-3 py-4 text-sm font-bold text-slate-900">{{ log.AdminUser }}</td>
            <td class="px-3 py-4 text-sm">
              <span :class="[
                'inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset',
                log.Action.includes('Deshabilitada') || log.Action.includes('nunca expira') ? 'bg-red-50 text-red-700 ring-red-600/10' : 'bg-orange-50 text-orange-700 ring-orange-700/10'
              ]" :title="log.Message">
                {{ log.Action }}
              </span>
            </td>
            <td class="whitespace-nowrap px-3 py-4 text-sm font-medium text-slate-700">{{ log.TargetUser }}</td>
            <td class="whitespace-nowrap px-3 py-4 text-sm text-slate-500 font-mono">{{ log.EventID }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
