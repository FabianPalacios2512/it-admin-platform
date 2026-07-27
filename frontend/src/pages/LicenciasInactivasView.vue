<script setup>
import { ref, onMounted, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const loading = ref(false)
const error = ref('')
const users = ref([])
const sortColumn = ref('daysInactive')
const sortDesc = ref(true)
const searchQuery = ref('')
const daysThreshold = ref(90)

const showToast = ref(false)
const toastType = ref('success')
const toastTitle = ref('')
const toastMessage = ref('')
let toastTimer = null

function displayToast(type, title, message) {
  toastType.value = type
  toastTitle.value = title
  toastMessage.value = message
  showToast.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { showToast.value = false }, 5000)
}

async function fetchInactiveUsers() {
  loading.value = true
  error.value = ''
  try {
    const res = await authFetch(`${API_BASE}/licenses/inactive?days=${daysThreshold.value}`)
    const data = await res.json()
    if (res.ok && data.success) {
      users.value = data.data
      if (users.value.length === 0) {
        displayToast('success', '¡Excelente!', `No se encontraron licencias inactivas (más de ${daysThreshold.value} días).`)
      } else {
        displayToast('warning', 'Licencias Inactivas', `Se encontraron ${users.value.length} cuentas inactiva(s).`)
      }
    } else {
      error.value = data.detail || 'Error al obtener datos'
      displayToast('error', 'Error API', error.value)
    }
  } catch (e) {
    error.value = 'Fallo de Red: ' + e.message
    displayToast('error', 'Fallo de Red', e.message)
  } finally {
    loading.value = false
  }
}

const filteredAndSortedUsers = computed(() => {
  let result = users.value
  
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(u => 
      u.userPrincipalName.toLowerCase().includes(q) ||
      u.displayName.toLowerCase().includes(q)
    )
  }
  
  result.sort((a, b) => {
    let valA = a[sortColumn.value]
    let valB = b[sortColumn.value]
    
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (typeof valB === 'string') valB = valB.toLowerCase()
    
    if (valA < valB) return sortDesc.value ? 1 : -1
    if (valA > valB) return sortDesc.value ? -1 : 1
    return 0
  })
  
  return result
})

function toggleSort(column) {
  if (sortColumn.value === column) {
    sortDesc.value = !sortDesc.value
  } else {
    sortColumn.value = column
    sortDesc.value = true
  }
}

const totalLicenses = computed(() => users.value.length)
const avgDaysInactive = computed(() => {
  if (totalLicenses.value === 0) return 0
  const validDays = users.value.filter(u => u.daysInactive !== 9999)
  if (validDays.length === 0) return `>${daysThreshold.value}` // Todos son nunca
  const sum = validDays.reduce((acc, u) => acc + u.daysInactive, 0)
  return Math.round(sum / validDays.length)
})
const estimatedWaste = computed(() => totalLicenses.value * 15) // USD 15 por licencia

onMounted(() => {
  fetchInactiveUsers()
})

function formatDate(isoString) {
  if (!isoString) return 'Nunca ha iniciado sesión'
  return new Date(isoString).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

function getDaysDisplay(days) {
  if (days === 9999) return 'Nunca'
  return `${days} días`
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6 fade-in">
    <!-- Toast (Tailwind version) -->
    <Transition name="toast">
      <div v-if="showToast" class="fixed bottom-4 right-4 z-50 flex items-center p-4 mb-4 w-full max-w-sm text-gray-500 bg-white rounded-lg shadow dark:text-gray-400 dark:bg-gray-800" role="alert">
        <div class="inline-flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-lg"
             :class="{'text-green-500 bg-green-100': toastType === 'success', 'text-red-500 bg-red-100': toastType === 'error', 'text-orange-500 bg-orange-100': toastType === 'warning', 'text-blue-500 bg-blue-100': toastType === 'info'}">
          <svg v-if="toastType === 'success'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>
          <svg v-if="toastType === 'error'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
          <svg v-if="toastType === 'warning'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
        </div>
        <div class="ml-3 text-sm font-normal">
          <span class="font-semibold text-gray-900 block">{{ toastTitle }}</span>
          {{ toastMessage }}
        </div>
        <button type="button" class="ml-auto -mx-1.5 -my-1.5 bg-white text-gray-400 hover:text-gray-900 rounded-lg focus:ring-2 focus:ring-gray-300 p-1.5 hover:bg-gray-100 inline-flex h-8 w-8" @click="showToast = false">
          <span class="sr-only">Close</span>
          <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
        </button>
      </div>
    </Transition>

    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
      <div>
        <div class="flex items-center gap-1.5 mb-1">
          <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
          <span class="text-[11px] text-slate-300">/</span>
          <span class="text-[11px] text-slate-600 font-medium">Licencias Inactivas</span>
        </div>
        <h2 class="text-2xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
          <svg class="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          Optimizador de Licencias Cloud
        </h2>
        <p class="text-sm text-gray-500 mt-1">Identifica usuarios con licencias asignadas que no han iniciado sesión en Microsoft 365.</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2 text-sm text-slate-600">
          <label for="daysFilter" class="font-medium">Inactivo por más de:</label>
          <select id="daysFilter" v-model="daysThreshold" @change="fetchInactiveUsers" class="text-[12px] bg-slate-50 border border-slate-200 text-slate-700 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer">
            <option :value="30">30 días</option>
            <option :value="60">60 días</option>
            <option :value="90">90 días</option>
            <option :value="120">120 días</option>
            <option :value="180">180 días</option>
          </select>
        </div>
        <button @click="fetchInactiveUsers" :disabled="loading" class="text-[12px] font-medium text-slate-700 hover:text-blue-600 hover:bg-slate-50 px-4 py-2 rounded border border-slate-200 transition-colors flex items-center gap-2">
          <svg v-if="!loading" class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          <svg v-else class="w-4 h-4 text-slate-400 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          {{ loading ? 'Analizando...' : 'Refrescar' }}
        </button>
      </div>
    </div>

    <!-- Executive Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-5 flex items-center gap-4">
        <div class="w-12 h-12 rounded-lg flex items-center justify-center bg-blue-50 text-blue-600">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Licencias Inactivas Encontradas</p>
          <p class="text-2xl font-bold text-slate-900 leading-tight">{{ totalLicenses }}</p>
        </div>
      </div>
      
      <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-5 flex items-center gap-4">
        <div class="w-12 h-12 rounded-lg flex items-center justify-center bg-orange-50 text-orange-500">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Promedio de Inactividad</p>
          <p class="text-2xl font-bold text-slate-900 leading-tight">{{ avgDaysInactive }} <span v-if="avgDaysInactive !== '>'+daysThreshold" class="text-sm font-normal text-slate-500">días</span></p>
        </div>
      </div>
      
      <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-5 flex items-center gap-4">
        <div class="w-12 h-12 rounded-lg flex items-center justify-center bg-red-50 text-red-600">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Dinero Desperdiciado (Est. Mensual)</p>
          <p class="text-2xl font-bold text-red-600 leading-tight">${{ estimatedWaste.toLocaleString() }} <span class="text-sm font-normal text-slate-500">USD</span></p>
        </div>
      </div>
    </div>

    <!-- DataGrid -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
      <div class="p-4 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-4">
        <h3 class="text-[14px] font-semibold text-slate-800">Detalle de Usuarios (Solo Lectura)</h3>
        <div class="relative w-full sm:w-[300px]">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <input type="text" v-model="searchQuery" placeholder="Buscar usuario o UPN..." class="w-full pl-9 pr-3 py-1.5 text-[12px] bg-slate-50 border border-slate-200 rounded focus:border-blue-500 focus:bg-white outline-none text-slate-800 placeholder-slate-400 transition-colors">
        </div>
      </div>
      
      <div class="overflow-x-auto min-h-[400px]">
        <table class="w-full text-left min-w-[800px]" v-if="!loading && filteredAndSortedUsers.length > 0">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/50">
              <th @click="toggleSort('displayName')" class="w-1/4 px-4 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors select-none">
                <div class="flex items-center gap-1">
                  Nombre a Mostrar
                  <svg v-if="sortColumn === 'displayName'" class="w-3 h-3" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
              <th @click="toggleSort('userPrincipalName')" class="w-1/4 px-4 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors select-none">
                <div class="flex items-center gap-1">
                  Identificador Único (UPN)
                  <svg v-if="sortColumn === 'userPrincipalName'" class="w-3 h-3" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
              <th @click="toggleSort('lastSignInDateTime')" class="w-1/4 px-4 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors select-none">
                <div class="flex items-center gap-1">
                  Último Inicio de Sesión
                  <svg v-if="sortColumn === 'lastSignInDateTime'" class="w-3 h-3" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
              <th @click="toggleSort('daysInactive')" class="w-1/4 px-4 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors select-none">
                <div class="flex items-center gap-1">
                  Días Inactivo
                  <svg v-if="sortColumn === 'daysInactive'" class="w-3 h-3" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in filteredAndSortedUsers" :key="user.id" class="border-b border-slate-100 transition-colors duration-150 hover:bg-slate-50" :class="{'bg-red-50/30 hover:bg-red-50/50 border-b-red-100': user.daysInactive >= 120}">
              <td class="px-4 py-2.5 text-[13px] font-medium text-slate-800">
                <div class="flex items-center gap-2">
                  <div class="w-6 h-6 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center text-[10px] font-bold">
                    {{ user.displayName.substring(0,2).toUpperCase() }}
                  </div>
                  {{ user.displayName }}
                </div>
              </td>
              <td class="px-4 py-2.5 text-[12px] text-slate-500">{{ user.userPrincipalName }}</td>
              <td class="px-4 py-2.5 text-[12px] text-slate-600">{{ formatDate(user.lastSignInDateTime) }}</td>
              <td class="px-4 py-2.5">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium" :class="user.daysInactive >= 120 ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800'">
                  {{ getDaysDisplay(user.daysInactive) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        
        <div v-else-if="loading" class="flex flex-col items-center justify-center py-16 text-slate-500">
          <div class="inline-block w-8 h-8 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
          <p class="text-[13px]">Analizando registros de inicio de sesión en Azure AD...</p>
        </div>
        
        <div v-else class="flex flex-col items-center justify-center py-16 text-slate-500">
          <svg class="w-12 h-12 text-emerald-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <p class="text-[14px] font-medium text-slate-700">No se encontraron licencias inactivas</p>
          <p class="text-[12px] mt-1">Tu entorno está optimizado con los criterios actuales.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(20px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
.fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
