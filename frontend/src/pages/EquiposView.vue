<script setup>
import { ref, onMounted, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const devices = ref([])
const loading = ref(false)
const error = ref('')
const searchQuery = ref('')

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

async function fetchDevices() {
  loading.value = true
  error.value = ''
  try {
    const res = await authFetch(`${API_BASE}/devices/`)
    const data = await res.json()
    if (res.ok && data.success) {
      devices.value = data.data
    } else {
      error.value = data.detail || 'Error al obtener equipos'
    }
  } catch (e) {
    error.value = 'Error de red: ' + e.message
  } finally {
    loading.value = false
  }
}

async function pingDevice(device) {
  device.status = 'pinging'
  try {
    const res = await authFetch(`${API_BASE}/devices/ping`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hostname: device.hostname })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      device.status = data.online ? 'online' : 'offline'
    } else {
      device.status = 'error'
      displayToast('error', 'Error Ping', data.detail)
    }
  } catch (e) {
    device.status = 'error'
  }
}

async function rebootDevice(device) {
  if (!confirm(`¿Estás seguro que deseas reiniciar forzadamente el equipo ${device.hostname}?`)) return
  try {
    const res = await authFetch(`${API_BASE}/devices/reboot`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hostname: device.hostname })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      displayToast('success', 'Comando Enviado', `Se ordenó el reinicio de ${device.hostname}.`)
    } else {
      displayToast('error', 'Error al reiniciar', data.detail)
    }
  } catch (e) {
    displayToast('error', 'Fallo de Red', e.message)
  }
}

async function checkBitLocker(device) {
  displayToast('info', 'Consultando BitLocker...', `Conectando con ${device.hostname}...`)
  try {
    const res = await authFetch(`${API_BASE}/devices/bitlocker`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hostname: device.hostname })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      if (data.data) {
        displayToast('success', 'Estado BitLocker', `Estado: ${data.data.VolumeStatus}, Encriptación: ${data.data.EncryptionPercentage}%`)
      } else {
        displayToast('error', 'Sin BitLocker', `El equipo ${device.hostname} no tiene cifrado BitLocker activo.`)
      }
    } else {
      displayToast('error', 'Error WMI', data.detail)
    }
  } catch (e) {
    displayToast('error', 'Fallo de Red', e.message)
  }
}

const filteredDevices = computed(() => {
  if (!searchQuery.value) return devices.value
  const q = searchQuery.value.toLowerCase()
  return devices.value.filter(d => 
    d.hostname.toLowerCase().includes(q) || 
    d.os.toLowerCase().includes(q) ||
    (d.description && d.description.toLowerCase().includes(q))
  )
})

const selectedDevices = ref(new Set())
const selectAll = ref(false)

function toggleSelectAll() {
  if (selectAll.value) {
    filteredDevices.value.forEach(d => selectedDevices.value.add(d.hostname))
  } else {
    filteredDevices.value.forEach(d => selectedDevices.value.delete(d.hostname))
  }
}

function toggleDevice(hostname) {
  if (selectedDevices.value.has(hostname)) {
    selectedDevices.value.delete(hostname)
  } else {
    selectedDevices.value.add(hostname)
  }
  selectedDevices.value = new Set(selectedDevices.value)
  selectAll.value = filteredDevices.value.length > 0 && filteredDevices.value.every(d => selectedDevices.value.has(d.hostname))
}

const hasSelection = computed(() => selectedDevices.value.size > 0)
const hasSingleSelection = computed(() => selectedDevices.value.size === 1)
const singleSelectedDevice = computed(() => {
  if (!hasSingleSelection.value) return null
  const hostname = Array.from(selectedDevices.value)[0]
  return devices.value.find(d => d.hostname === hostname)
})

function handlePingSelection() {
  if (hasSingleSelection.value) {
    pingDevice(singleSelectedDevice.value)
  } else {
    Array.from(selectedDevices.value).forEach(hostname => {
      const dev = devices.value.find(d => d.hostname === hostname)
      if (dev) pingDevice(dev)
    })
  }
}

onMounted(() => {
  fetchDevices()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6">
    <!-- Breadcrumb & Header -->
    <div class="mb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600 font-medium">Equipos AD</span>
      </div>
      <h2 class="text-2xl font-semibold text-slate-900 tracking-tight">Equipos y Endpoints</h2>
      <p class="text-sm text-gray-500 mt-1">Administración de computadoras del dominio Active Directory.</p>
    </div>

    <!-- Filters & Search -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
      <div class="flex items-center gap-1">
        <button @click="fetchDevices" class="text-[12px] font-medium text-slate-700 hover:text-blue-600 hover:bg-slate-50 px-3 py-1.5 rounded transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
      </div>
      <div class="relative w-full md:w-[280px]">
        <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <input v-model="searchQuery" type="text" placeholder="Buscar equipo..." class="w-full pl-8 pr-3 py-1.5 text-[12px] bg-transparent border-b border-slate-300 hover:border-slate-400 focus:border-blue-500 outline-none text-slate-800 placeholder-slate-400 transition-colors" />
      </div>
    </div>

    <!-- Data Table (Borderless) -->
    <div class="flex flex-col">
      <div class="overflow-x-auto">
        <table class="w-full text-left min-w-[800px]">
          <thead>
            <tr class="border-b border-slate-200">
              <th class="w-1/4 px-3 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors">Hostname</th>
              <th class="w-1/6 px-3 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors">OS</th>
              <th class="w-1/6 px-3 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors">Estado Red</th>
              <th class="w-1/6 px-3 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors">Último Acceso</th>
              <th class="w-24 px-3 py-3 text-[11px] font-semibold text-slate-500 hover:text-slate-800 cursor-pointer transition-colors text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="px-2 py-16 text-center">
                <div class="inline-block w-6 h-6 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin mb-3"></div>
                <p class="text-[13px] text-slate-500">Buscando computadoras en Active Directory...</p>
              </td>
            </tr>
            <tr v-else-if="error">
              <td colspan="5" class="px-2 py-16 text-center">
                <div class="inline-flex items-center gap-2 bg-red-50 text-red-700 px-4 py-2 rounded-lg text-[13px]">
                  <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  {{ error }}
                </div>
              </td>
            </tr>
            <tr v-else-if="filteredDevices.length === 0">
              <td colspan="5" class="px-2 py-16 text-center">
                <p class="text-[13px] text-slate-500">No se encontraron equipos que coincidan con la búsqueda.</p>
              </td>
            </tr>
            <tr v-else v-for="dev in filteredDevices" :key="dev.hostname" class="border-b border-slate-100 transition-colors duration-150 cursor-pointer group hover:bg-slate-50">
              <td class="px-3 py-2.5">
                <div class="flex items-center gap-3">
                  <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-slate-100 text-slate-500 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
                  </div>
                  <div>
                    <span class="text-[13px] font-medium text-slate-800 group-hover:text-blue-600 transition-colors">{{ dev.hostname }}</span>
                    <p v-if="dev.description" class="text-[11px] text-slate-500 mt-0.5 truncate max-w-[200px] xl:max-w-[250px]" :title="dev.description">{{ dev.description }}</p>
                  </div>
                </div>
              </td>
              <td class="px-3 py-2.5">
                <div class="text-[12px] text-slate-600 truncate max-w-[150px] xl:max-w-[200px]" :title="dev.os">
                  {{ dev.os.replace('Windows', 'Win').replace('Professional', 'Pro') }}
                </div>
              </td>
              <td class="px-3 py-2.5">
                <button v-if="dev.status === 'unknown' || !dev.status" @click.stop="pingDevice(dev)" class="text-[11px] font-semibold text-slate-500 hover:text-blue-600 hover:bg-blue-50 px-2 py-0.5 rounded transition-colors border border-transparent hover:border-blue-200">
                  Check Ping
                </button>
                <div v-else-if="dev.status === 'pinging'" class="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-300 animate-pulse"></span> Pinging...
                </div>
                <div v-else-if="dev.status === 'online'" class="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Online
                </div>
                <div v-else-if="dev.status === 'offline'" class="flex items-center gap-1.5 text-[11px] font-semibold text-red-500">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span> Offline
                </div>
                <div v-else class="text-[11px] text-red-500">Error</div>
              </td>
              <td class="px-3 py-2.5 text-[11px] text-slate-500 font-mono">
                {{ dev.last_logon }}
              </td>
              <td class="px-3 py-2.5 text-right">
                <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button @click.stop="pingDevice(dev)" title="Hacer Ping" class="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  </button>
                  <button @click.stop="checkBitLocker(dev)" title="Ver BitLocker" class="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded transition-colors">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                  </button>
                  <button @click.stop="rebootDevice(dev)" title="Reiniciar" class="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Toast Notification -->
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <transition enter-active-class="transition ease-out duration-300 transform" enter-from-class="opacity-0 translate-y-[-1rem] scale-95" enter-to-class="opacity-100 translate-y-0 scale-100" leave-active-class="transition ease-in duration-200" leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-95">
        <div v-if="showToast" :class="['pointer-events-auto flex items-start p-4 rounded-lg shadow-lg border max-w-sm w-full', toastType === 'success' ? 'bg-white border-emerald-100' : toastType === 'info' ? 'bg-white border-blue-100' : 'bg-white border-red-100']">
          <div :class="['flex-shrink-0 mr-3', toastType === 'success' ? 'text-emerald-500' : toastType === 'info' ? 'text-blue-500' : 'text-red-500']">
            <svg v-if="toastType === 'success'" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-else-if="toastType === 'info'" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <div class="flex-1 pt-0.5">
            <h3 class="text-[13px] font-semibold text-slate-800">{{ toastTitle }}</h3>
            <p class="mt-1 text-[12px] text-slate-500">{{ toastMessage }}</p>
          </div>
          <button @click="showToast = false" class="ml-4 flex-shrink-0 text-slate-400 hover:text-slate-600 focus:outline-none">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </transition>
    </div>
  </div>
</template>
