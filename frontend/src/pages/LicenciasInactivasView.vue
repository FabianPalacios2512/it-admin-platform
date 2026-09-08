<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { getFriendlyLicenseName } from '../utils/licenses'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const loading = ref(false)
const error = ref('')
const users = ref([])
const skus = ref([]) // <--- Añadimos variable para los skus reales
const sortColumn = ref('displayName')
const sortDesc = ref(false)
const searchQuery = ref('')

// Filtros avanzados
const accountStateFilter = ref('Todas') // Todas, Habilitadas, Inhabilitadas, Bloqueadas
const inactivityDaysFilter = ref('Todos') // Todos, > 30 días, > 60 días, > 90 días
const selectedLicenses = ref([]) // Array de licencias seleccionadas
const isLicenseDropdownOpen = ref(false)

// Multi-tenant
const availableTenants = ref([])
const selectedTenant = ref('1')

const availableLicenses = computed(() => {
  if (!skus.value || skus.value.length === 0) return []
  return skus.value.map(s => getFriendlyLicenseName(s.skuPartNumber)).sort()
})

const showToast = ref(false)
const toastType = ref('success')
const toastTitle = ref('')
const toastMessage = ref('')
let toastTimer = null

// Notas
const isNoteModalOpen = ref(false)
const editingNoteUser = ref(null)
const noteText = ref('')
const savingNote = ref(false)
const exportingToExcel = ref(false)

const currentTab = ref('inactivas')
const auditHistory = ref([])
const loadingHistory = ref(false)

function displayToast(type, title, message) {
  toastType.value = type
  toastTitle.value = title
  toastMessage.value = message
  showToast.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { showToast.value = false }, 5000)
}

function toggleLicense(lic) {
  const idx = selectedLicenses.value.indexOf(lic)
  if (idx > -1) selectedLicenses.value.splice(idx, 1)
  else selectedLicenses.value.push(lic)
}

// Para simular el estado de la cuenta si la API no lo trae (para demostración UI/UX)
// En producción, esto vendría en u.accountEnabled y u.isBlocked
function getAccountState(u) {
  if (u.isBlocked) return 'Bloqueadas'
  if (u.accountEnabled === false) return 'Inhabilitadas'
  return 'Habilitadas'
}

async function fetchTenants() {
  try {
    const res = await authFetch(`${API_BASE}/licenses/tenants`)
    const data = await res.json()
    if (res.ok && data.success) {
      availableTenants.value = data.data
    }
  } catch (err) {
    console.error("Error cargando tenants", err)
  }
}

async function fetchInactiveUsers() {
  loading.value = true
  error.value = ''
  try {
    // Llamada simultánea a ambos endpoints
    const [resUsers, resSkus] = await Promise.all([
      authFetch(`${API_BASE}/licenses/inactive?tenant=${selectedTenant.value}`),
      authFetch(`${API_BASE}/licenses/skus?tenant=${selectedTenant.value}`)
    ])

    const dataUsers = await resUsers.json()
    const dataSkus = await resSkus.json()

    if (resUsers.ok && dataUsers.success && resSkus.ok && dataSkus.success) {
      users.value = dataUsers.data.map(u => ({
        ...u,
        accountEnabled: u.accountEnabled !== undefined ? u.accountEnabled : true,
        isBlocked: u.isBlocked !== undefined ? u.isBlocked : false,
      }))
      
      skus.value = dataSkus.data || []
      
      displayToast('success', 'Datos Actualizados', `Se cargaron ${users.value.length} registros y cuotas reales.`)
    } else {
      error.value = dataUsers.detail || dataSkus.detail || 'Error al obtener datos'
      displayToast('error', 'Error API', error.value)
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function fetchHistory() {
  loadingHistory.value = true
  try {
    const res = await authFetch(`${API_BASE}/licenses/audit/history`)
    const data = await res.json()
    if (data.success) {
      auditHistory.value = data.data
    }
  } catch (err) {
    displayToast('error', 'Error', 'No se pudo cargar el historial')
  } finally {
    loadingHistory.value = false
  }
}

function openNoteModal(user) {
  editingNoteUser.value = user
  noteText.value = user.note || ''
  isNoteModalOpen.value = true
}

async function saveNote(actionType = "NOTE") {
  if (!editingNoteUser.value) return
  savingNote.value = true
  
  // Estimate saved USD based on license count if recovered
  let usd = 0
  if (actionType === "RECOVERED") {
    usd = (editingNoteUser.value.licenses?.length || 1) * 15 // $15 per license assumed
  }

  try {
    const payload = {
      userId: editingNoteUser.value.id,
      userPrincipalName: editingNoteUser.value.userPrincipalName,
      displayName: editingNoteUser.value.displayName,
      note: noteText.value,
      action: actionType,
      licenses: editingNoteUser.value.licenses?.join(", ") || "",
      savedUsd: usd
    }
    
    const res = await authFetch(`${API_BASE}/licenses/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (res.ok && data.success) {
      editingNoteUser.value.note = noteText.value
      
      if (actionType === "RECOVERED") {
        displayToast('success', 'Licencia Recuperada', 'Registro de ahorro guardado correctamente')
        // Optimistically remove from current list
        users.value = users.value.filter(u => u.id !== editingNoteUser.value.id)
      } else {
        displayToast('success', 'Nota guardada', 'La nota de auditoría se ha actualizado correctamente')
      }
      
      isNoteModalOpen.value = false
    } else {
      displayToast('error', 'Error al guardar', data.detail || 'Error desconocido')
    }
  } catch (e) {
    displayToast('error', 'Error de red', e.message)
  } finally {
    savingNote.value = false
  }
}

async function exportToExcel() {
  exportingToExcel.value = true
  try {
    const sheetName = selectedLicenses.value.length > 0 
      ? selectedLicenses.value.join(", ") 
      : "Todas"
      
    const res = await authFetch(`${API_BASE}/licenses/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sheetName: sheetName, data: filteredAndSortedUsers.value })
    })
    
    if (res.ok) {
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = "Limpieza_Licencias.xlsx"
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      
      displayToast('success', 'Exportación Exitosa', `Se ha descargado y actualizado la hoja "${sheetName}" en Documentos.`)
    } else {
      const data = await res.json()
      displayToast('error', 'Error al exportar', data.detail || 'Ocurrió un error inesperado')
    }
  } catch (e) {
    displayToast('error', 'Error de red', e.message)
  } finally {
    exportingToExcel.value = false
  }
}

const filteredAndSortedUsers = computed(() => {
  let result = users.value
  
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(u => 
      (u.userPrincipalName && u.userPrincipalName.toLowerCase().includes(q)) ||
      (u.displayName && u.displayName.toLowerCase().includes(q))
    )
  }
  
  result = result.filter(u => {
    // Filtro de Estado
    const state = getAccountState(u)
    const statePass = accountStateFilter.value === 'Todas' || state === accountStateFilter.value

    // Filtro de Inactividad (exigimos que esté inactivo tanto en AD Local como en M365)
    const inactivityCloud = Math.min(u.daysInactiveAd ?? 9999, u.daysInactiveOutlook ?? 9999)
    const inactivityLocal = u.daysInactiveLocalAd ?? 9999
    const inactivity = Math.min(inactivityLocal, inactivityCloud)
    
    let inactPass = true
    if (inactivityDaysFilter.value === '> 30 días') inactPass = inactivity > 30
    else if (inactivityDaysFilter.value === '> 60 días') inactPass = inactivity > 60
    else if (inactivityDaysFilter.value === '> 90 días') inactPass = inactivity > 90

    // Filtro de Licencias
    let licPass = true
    if (selectedLicenses.value.length > 0) {
      const userLics = u.licenses ? u.licenses.map(l => getFriendlyLicenseName(l)) : []
      licPass = selectedLicenses.value.some(selLic => userLics.includes(selLic))
    }
    
    return true && statePass && inactPass && licPass;
  })
  
  result.sort((a, b) => {
    let valA = a[sortColumn.value]
    let valB = b[sortColumn.value]
    
    if (valA == null) valA = ''
    if (valB == null) valB = ''
    
    if (typeof valA === 'string') valA = valA.toLowerCase()
    if (typeof valB === 'string') valB = valB.toLowerCase()
    
    if (valA < valB) return sortDesc.value ? 1 : -1
    if (valA > valB) return sortDesc.value ? -1 : 1
    return 0
  })
  
  return result
})

// Paginación
const currentPage = ref(1)
const itemsPerPage = ref(50)

const totalPages = computed(() => Math.ceil(filteredAndSortedUsers.value.length / itemsPerPage.value) || 1)

const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredAndSortedUsers.value.slice(start, end)
})

// Resetear a página 1 cuando cambien los filtros o el ordenamiento
watch([searchQuery, inactivityDaysFilter, accountStateFilter, selectedLicenses, sortColumn, sortDesc], () => {
  currentPage.value = 1
})

watch(selectedTenant, () => {
  selectedLicenses.value = [] // Reset license filters when switching tenant
  fetchInactiveUsers()
})

function toggleSort(column) {
  if (sortColumn.value === column) {
    sortDesc.value = !sortDesc.value
  } else {
    sortColumn.value = column
    sortDesc.value = false
  }
}

// KPIs Dinámicos
const totalFiltered = computed(() => filteredAndSortedUsers.value.length)
const avgDaysInactive = computed(() => {
  if (totalFiltered.value === 0) return 0
  const validDays = filteredAndSortedUsers.value.map(u => {
    const cloud = Math.min(u.daysInactiveAd ?? 9999, u.daysInactiveOutlook ?? 9999)
    const local = u.daysInactiveLocalAd ?? 9999
    return Math.min(cloud, local)
  }).filter(d => d !== 9999)
  if (validDays.length === 0) return `>90`
  const sum = validDays.reduce((acc, d) => acc + d, 0)
  return Math.round(sum / validDays.length)
})
const estimatedWaste = computed(() => totalFiltered.value * 15) // USD 15 por licencia mock

const isFilteredByLicense = computed(() => selectedLicenses.value.length > 0)

// Motor de cuotas para KPIs mutables (Datos Reales del Tenant)
const licenseKPIs = computed(() => {
  if (!isFilteredByLicense.value) return []
  return selectedLicenses.value.map(lic => {
    
    // Buscar el SKU real basándose en el nombre amigable
    const matchingSku = skus.value.find(s => getFriendlyLicenseName(s.skuPartNumber) === lic)
    
    let total = 0
    let assigned = 0

    if (matchingSku) {
      total = matchingSku.prepaidUnits ? matchingSku.prepaidUnits.enabled : 0
      assigned = matchingSku.consumedUnits || 0
    } else {
      // Si el SKU no se encuentra en el tenant, lo mostramos en 0/0
      total = 0
      assigned = 0
    }
    
    const percentage = total > 0 ? (assigned / total) * 100 : 0
    return {
      name: lic,
      assigned,
      total,
      percentage
    }
  })
})

onMounted(() => {
  fetchTenants()
  fetchInactiveUsers()
  fetchHistory()
  
  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('license-dropdown-container')
    if (dropdown && !dropdown.contains(e.target)) {
      isLicenseDropdownOpen.value = false
    }
  })
})

function formatDate(isoString) {
  if (!isoString) return 'Nunca ha iniciado sesión'
  return new Date(isoString).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

function getDaysDisplay(days) {
  if (days === 9999 || days === undefined || days === null) return 'N/A'
  return `${days} días`
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6 fade-in">
    <!-- Toast -->
    <Transition name="toast">
      <div v-if="showToast" class="fixed bottom-4 right-4 z-50 flex items-center p-4 mb-4 w-full max-w-sm text-gray-500 bg-white rounded-lg shadow dark:text-gray-400 dark:bg-gray-800" role="alert">
        <div class="inline-flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-lg"
             :class="{'text-emerald-500 bg-emerald-100': toastType === 'success', 'text-red-500 bg-red-100': toastType === 'error', 'text-orange-500 bg-orange-100': toastType === 'warning', 'text-blue-500 bg-blue-100': toastType === 'info'}">
          <svg v-if="toastType === 'success'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>
          <svg v-if="toastType === 'error'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
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

    <!-- Header & Toolbar Avanzado -->
    <div class="flex flex-col mb-8 gap-4">
      <div>
        <div class="flex items-center gap-1.5 mb-1">
          <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
          <span class="text-[11px] text-slate-300">/</span>
          <span class="text-[11px] text-slate-600 font-medium">Centro de Auditoría M365</span>
        </div>
        <h2 class="text-2xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
          <svg class="w-6 h-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
          Centro de Auditoría de Identidades y Licencias
        </h2>
        <p class="text-sm text-gray-500 mt-1">Gestión integral de usuarios, asignaciones y cuotas en el tenant de Microsoft 365.</p>
      </div>

      <!-- TABS -->
      <div class="flex border-b border-slate-200">
        <button 
          @click="currentTab = 'inactivas'" 
          :class="currentTab === 'inactivas' ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'"
          class="whitespace-nowrap py-3 px-6 border-b-2 font-medium text-[13px] transition-colors"
        >
          Licencias Activas e Inactivas
        </button>
        <button 
          @click="currentTab = 'historial'; fetchHistory();" 
          :class="currentTab === 'historial' ? 'border-emerald-500 text-emerald-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'"
          class="whitespace-nowrap py-3 px-6 border-b-2 font-medium text-[13px] transition-colors flex items-center gap-2"
        >
          Historial de Ahorros
        </button>
      </div>

      <div v-if="currentTab === 'inactivas'">
        <!-- Barra de Filtros -->
        <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-4 mt-4">
        
        <div class="flex flex-col gap-1 w-full sm:w-auto" v-if="availableTenants.length > 1">
          <label class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Tenant (Dominio)</label>
          <select v-model="selectedTenant" class="text-[13px] bg-indigo-50 border border-indigo-200 text-indigo-800 font-semibold rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 cursor-pointer min-w-[150px] transition-all">
            <option v-for="t in availableTenants" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </div>

        <div class="flex flex-col gap-1 w-full sm:w-auto">
          <label class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Estado Cuenta</label>
          <select v-model="accountStateFilter" class="text-[13px] bg-slate-50 border border-slate-200 text-slate-700 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 cursor-pointer min-w-[140px] transition-all">
            <option value="Todas">Todas</option>
            <option value="Habilitadas">Habilitadas</option>
            <option value="Inhabilitadas">Inhabilitadas</option>
            <option value="Bloqueadas">Bloqueadas</option>
          </select>
        </div>

        <div class="flex flex-col gap-1 w-full sm:w-auto">
          <label class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Inactividad</label>
          <select v-model="inactivityDaysFilter" class="text-[13px] bg-slate-50 border border-slate-200 text-slate-700 rounded-md px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 cursor-pointer min-w-[140px] transition-all">
            <option value="Todos">Todos</option>
            <option value="> 30 días">> 30 días</option>
            <option value="> 60 días">> 60 días</option>
            <option value="> 90 días">> 90 días</option>
          </select>
        </div>

        <div class="flex flex-col gap-1 w-full sm:w-auto relative" id="license-dropdown-container">
          <label class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Licencias</label>
          <button @click="isLicenseDropdownOpen = !isLicenseDropdownOpen" class="text-[13px] bg-slate-50 border border-slate-200 text-slate-700 rounded-md px-3 py-1.5 flex items-center justify-between min-w-[220px] focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all">
            <span class="truncate pr-2">{{ selectedLicenses.length > 0 ? `${selectedLicenses.length} seleccionadas` : 'Todas las licencias' }}</span>
            <svg class="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
          </button>
          
          <div v-if="isLicenseDropdownOpen" class="absolute top-[100%] mt-1 left-0 w-64 bg-white border border-slate-200 rounded-lg shadow-xl z-20 py-2">
            <label v-for="lic in availableLicenses" :key="lic" class="flex items-center px-4 py-2 hover:bg-slate-50 cursor-pointer transition-colors">
              <input type="checkbox" :checked="selectedLicenses.includes(lic)" @change="toggleLicense(lic)" class="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 w-4 h-4 mr-3">
              <span class="text-[13px] text-slate-700">{{ lic }}</span>
            </label>
          </div>
        </div>

        <div class="ml-auto flex items-end gap-2">
          <button @click="exportToExcel" :disabled="exportingToExcel || loading" class="text-[13px] font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 hover:text-emerald-600 px-4 py-1.5 rounded-md transition-colors flex items-center gap-2 shadow-sm h-[34px]">
            <svg v-if="!exportingToExcel" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
            <svg v-else class="w-4 h-4 animate-spin text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {{ exportingToExcel ? 'Exportando...' : 'Exportar a Excel' }}
          </button>
        
          <button @click="fetchInactiveUsers" :disabled="loading" class="text-[13px] font-medium text-white bg-emerald-600 hover:bg-emerald-700 px-5 py-1.5 rounded-md transition-colors flex items-center gap-2 shadow-sm shadow-emerald-600/20 h-[34px]">
            <svg v-if="!loading" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            {{ loading ? 'Actualizando...' : 'Refrescar' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Dynamic KPIs -->
    <div class="mb-8 pl-1">
      <div v-if="!isFilteredByLicense" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="flex flex-col p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center">
              <svg class="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
            </div>
            <p class="text-[13px] font-medium text-slate-500">Usuarios Filtrados</p>
          </div>
          <p class="text-3xl font-semibold text-slate-800">{{ totalFiltered }}</p>
        </div>
        
        <div class="flex flex-col p-4 bg-white rounded-xl border border-slate-100 shadow-sm">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-full bg-orange-50 flex items-center justify-center">
              <svg class="w-4 h-4 text-orange-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <p class="text-[13px] font-medium text-slate-500">Promedio de Inactividad</p>
          </div>
          <div class="flex items-baseline gap-1.5">
            <p class="text-3xl font-semibold text-slate-800">{{ avgDaysInactive }}</p>
            <span v-if="avgDaysInactive !== '>90'" class="text-sm font-medium text-slate-500">días</span>
          </div>
        </div>
        
        <div class="flex flex-col p-4 bg-white rounded-xl border border-slate-100 shadow-sm relative overflow-hidden">
          <div class="absolute -right-4 -bottom-4 opacity-5">
             <svg class="w-32 h-32" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
          </div>
          <div class="flex items-center gap-2 mb-2">
            <div class="w-8 h-8 rounded-full bg-red-50 flex items-center justify-center">
              <svg class="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            </div>
            <p class="text-[13px] font-medium text-slate-500">Desperdicio Mensual Estimado</p>
          </div>
          <div class="flex items-baseline gap-1.5">
            <p class="text-3xl font-semibold text-slate-800">${{ estimatedWaste.toLocaleString() }}</p>
            <span class="text-sm font-medium text-slate-500">USD</span>
          </div>
        </div>
      </div>

      <!-- Cuotas Mutadas por Licencia -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="kpi in licenseKPIs" :key="kpi.name" class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm transition-all hover:border-slate-300">
          <div class="flex justify-between items-start mb-4">
            <h4 class="text-[14px] font-semibold text-slate-800 truncate pr-2">{{ kpi.name }}</h4>
            <span class="inline-flex items-center justify-center px-2 py-1 bg-slate-100 text-slate-600 text-[11px] font-bold rounded-md">
              {{ kpi.assigned }} / {{ kpi.total }}
            </span>
          </div>
          <div class="w-full bg-slate-100 rounded-full h-2.5 mb-2 overflow-hidden">
            <div class="h-2.5 rounded-full transition-all duration-500" 
                 :class="kpi.percentage >= 90 ? 'bg-red-500' : 'bg-emerald-500'" 
                 :style="{ width: `${Math.min(kpi.percentage, 100)}%` }"></div>
          </div>
          <p class="text-[11px] text-slate-500 text-right mt-1 font-medium" :class="kpi.percentage >= 90 ? 'text-red-600' : ''">
            {{ kpi.percentage.toFixed(1) }}% de ocupación
          </p>
        </div>
      </div>
    </div>

    <!-- DataGrid -->
    <div class="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
      <div class="p-4 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-4 bg-slate-50/30">
        <h3 class="text-[14px] font-semibold text-slate-800">Detalle de Identidades</h3>
        <div class="relative w-full sm:w-[300px]">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <input type="text" v-model="searchQuery" placeholder="Buscar usuario o UPN..." class="w-full pl-9 pr-3 py-1.5 text-[13px] bg-white border border-slate-200 rounded-md focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none text-slate-800 placeholder-slate-400 transition-all shadow-sm">
        </div>
      </div>
      
      <div class="overflow-x-auto min-h-[400px]">
        <table class="w-full text-left min-w-[900px]" v-if="!loading && filteredAndSortedUsers.length > 0">
          <thead>
            <tr class="border-b border-slate-200 bg-white">
              <th class="w-[5%] px-3 py-3.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider select-none text-center">
                #
              </th>
              <th @click="toggleSort('displayName')" class="w-[20%] px-5 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider hover:text-slate-800 cursor-pointer transition-colors select-none">
                <div class="flex items-center gap-1.5">
                  Identidad
                  <svg v-if="sortColumn === 'displayName'" class="w-3.5 h-3.5" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
              <th class="w-[12%] px-5 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider select-none">
                Estado Cuenta
              </th>
              <th class="w-[23%] px-5 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider select-none">
                Licencias Asignadas
              </th>
              <th @click="toggleSort('localAdLastLogon')" class="w-[15%] px-5 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider hover:text-slate-800 cursor-pointer transition-colors select-none" title="Último inicio de sesión en Active Directory Local">
                <div class="flex items-center gap-1.5">
                  Inicio Local (AD)
                  <svg v-if="sortColumn === 'localAdLastLogon'" class="w-3.5 h-3.5" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
              <th @click="toggleSort('lastSignInDateTimeAd')" class="w-[15%] px-5 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider hover:text-slate-800 cursor-pointer transition-colors select-none" title="El sistema toma el inicio interactivo (con contraseña) y el de fondo (Outlook/Teams) para mayor precisión.">
                <div class="flex items-center gap-1.5">
                  Inicio Nube (M365)
                  <svg v-if="sortColumn === 'lastSignInDateTimeAd'" class="w-3.5 h-3.5" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
              <th @click="toggleSort('daysInactiveLocalAd')" class="w-[15%] px-5 py-3.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider hover:text-slate-800 cursor-pointer transition-colors select-none" title="Días inactivos considerando el menor tiempo entre el AD local, el inicio interactivo de M365 y el inicio en segundo plano.">
                <div class="flex items-center gap-1.5">
                  Días Inactivo
                  <svg v-if="sortColumn === 'daysInactiveAd'" class="w-3.5 h-3.5" :class="{'rotate-180': !sortDesc}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="(user, index) in paginatedUsers" :key="user.id" class="transition-colors duration-150 hover:bg-slate-50/80 group bg-white">
              <td class="px-3 py-3 text-center text-[11px] font-bold text-slate-400">
                {{ (currentPage - 1) * itemsPerPage + index + 1 }}
              </td>
              <td class="px-5 py-3">
                <div class="flex flex-col relative">
                  <div class="flex items-center gap-2">
                    <span class="text-[13px] font-semibold text-slate-800">{{ user.displayName || 'Sin Nombre' }}</span>
                    
                    <button @click="openNoteModal(user)" class="shrink-0 p-1 rounded-md hover:bg-slate-100 transition-colors" :title="user.note ? 'Editar nota' : 'Añadir nota'">
                      <!-- Icono lleno si tiene nota, contorno si no -->
                      <svg v-if="user.note" class="w-4 h-4 text-emerald-600" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <svg v-else class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                      </svg>
                    </button>
                  </div>
                  
                  <span v-if="user.onPremisesSamAccountName" class="text-[12px] font-bold text-emerald-600 truncate max-w-[250px]" title="Usuario del Active Directory Local">AD: {{ user.onPremisesSamAccountName }}</span>
                  <span class="text-[11px] text-slate-500 truncate max-w-[250px]" title="User Principal Name (UPN)">{{ user.userPrincipalName }}</span>
                </div>
              </td>
              <td class="px-5 py-3">
                <span v-if="getAccountState(user) === 'Habilitadas'" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
                  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Habilitado
                </span>
                <span v-else-if="getAccountState(user) === 'Bloqueadas'" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-red-50 text-red-700 border border-red-100">
                  <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span> Bloqueado
                </span>
                <span v-else class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                  <span class="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Inhabilitado
                </span>
              </td>
              <td class="px-5 py-3 text-[12px] text-slate-600">
                <div v-if="user.licenses && user.licenses.length > 0" class="flex flex-wrap gap-1.5">
                  <span v-for="lic in user.licenses.slice(0, 2)" :key="lic" class="px-2 py-0.5 bg-slate-100 border border-slate-200 rounded text-[10px] font-medium text-slate-700 truncate max-w-[140px]" :title="getFriendlyLicenseName(lic)">
                    {{ getFriendlyLicenseName(lic) }}
                  </span>
                  <span v-if="user.licenses.length > 2" class="px-1.5 py-0.5 bg-slate-50 border border-slate-200 rounded text-[10px] font-medium text-slate-500" :title="user.licenses.slice(2).map(l => getFriendlyLicenseName(l)).join(', ')">
                    +{{ user.licenses.length - 2 }}
                  </span>
                </div>
                <span v-else class="text-[11px] text-slate-400 italic">Sin licencias</span>
              </td>
              <td class="px-5 py-3 text-[12px] text-slate-600">
                <span v-if="user.onPremisesSyncEnabled">
                  {{ formatDate(user.localAdLastLogon) }}
                  <span v-if="user.daysInactiveLocalAd !== undefined && user.daysInactiveLocalAd !== 9999" class="text-red-600 font-semibold ml-1">
                    ({{ user.daysInactiveLocalAd }} días)
                  </span>
                </span>
                <span v-else class="text-[11px] text-slate-400 italic bg-slate-50 px-2 py-0.5 rounded border border-slate-100">
                  Solo Nube (Sin AD)
                </span>
              </td>
              <td class="px-5 py-3 text-[12px] text-slate-600">
                <div class="flex flex-col gap-0.5">
                  <span v-if="user.lastSignInDateTimeAd">
                    {{ formatDate(user.lastSignInDateTimeAd) }}
                    <span v-if="user.daysInactiveAd !== undefined && user.daysInactiveAd !== 9999" class="text-red-600 font-semibold ml-1">
                      ({{ user.daysInactiveAd }}d)
                    </span>
                  </span>
                  <span v-else class="text-[11px] text-slate-400 italic">
                    Sin info. (Req. Premium)
                  </span>
                  <span v-if="user.lastSignInDateTimeOutlook" class="text-[10px] text-slate-400 italic" title="Último inicio en segundo plano (apps, correo, etc)">
                    Fondo: {{ formatDate(user.lastSignInDateTimeOutlook) }}
                    <span v-if="user.daysInactiveOutlook !== undefined && user.daysInactiveOutlook !== 9999" class="text-red-400 font-semibold ml-1">
                      ({{ user.daysInactiveOutlook }}d)
                    </span>
                  </span>
                </div>
              </td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-2">
                  <span class="inline-flex items-center px-2 py-1 rounded-md text-[11px] font-bold font-mono" :class="Math.min(user.daysInactiveLocalAd ?? 9999, Math.min(user.daysInactiveAd ?? 9999, user.daysInactiveOutlook ?? 9999)) >= 90 && Math.min(user.daysInactiveLocalAd ?? 9999, Math.min(user.daysInactiveAd ?? 9999, user.daysInactiveOutlook ?? 9999)) !== 9999 ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-slate-50 text-slate-600 border border-slate-200'">
                    {{ getDaysDisplay(Math.min(user.daysInactiveLocalAd ?? 9999, Math.min(user.daysInactiveAd ?? 9999, user.daysInactiveOutlook ?? 9999))) }}
                  </span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        
        <!-- Paginación -->
        <div v-if="!loading && filteredAndSortedUsers.length > 0" class="px-5 py-4 border-t border-slate-200 flex items-center justify-between bg-white">
          <span class="text-[12px] text-slate-500">Mostrando {{ (currentPage - 1) * itemsPerPage + 1 }} a {{ Math.min(currentPage * itemsPerPage, filteredAndSortedUsers.length) }} de {{ filteredAndSortedUsers.length }} usuarios</span>
          <div class="flex items-center gap-2">
            <button @click="currentPage--" :disabled="currentPage === 1" class="px-3 py-1.5 text-[12px] font-medium rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
              Anterior
            </button>
            <span class="text-[12px] font-bold text-slate-700 px-3">Página {{ currentPage }} de {{ totalPages }}</span>
            <button @click="currentPage++" :disabled="currentPage === totalPages" class="px-3 py-1.5 text-[12px] font-medium rounded-md border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
              Siguiente
            </button>
          </div>
        </div>

        <!-- Loading State -->
        <div v-else-if="loading" class="flex flex-col items-center justify-center py-20 text-slate-500">
          <div class="inline-block w-8 h-8 border-2 border-slate-200 border-t-emerald-600 rounded-full animate-spin mb-4"></div>
          <p class="text-[14px] font-medium text-slate-600">Sincronizando con Microsoft Graph API...</p>
          <p class="text-[12px] text-slate-400 mt-1">Evaluando identidades y cuotas de licencias</p>
        </div>
        
        <!-- Empty State -->
        <div v-else class="flex flex-col items-center justify-center py-20 text-slate-500">
          <div class="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
            <svg class="w-8 h-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <p class="text-[15px] font-semibold text-slate-700">No hay registros que coincidan</p>
          <p class="text-[13px] mt-1 text-slate-500">Intenta ajustar los filtros de estado o inactividad.</p>
        </div>
      </div>
      
      <!-- Fin de la pestaña Inactivas -->
      </div>
      
      <!-- Pestaña Historial -->
      <div v-if="currentTab === 'historial'" class="mt-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div class="flex flex-col p-6 bg-emerald-50 rounded-xl border border-emerald-100 shadow-sm">
            <p class="text-sm font-semibold text-emerald-800 uppercase tracking-wider mb-2">Total Licencias Recuperadas</p>
            <p class="text-4xl font-bold text-emerald-600">{{ auditHistory.length }}</p>
            <p class="text-xs text-emerald-700 mt-2">Licencias que han sido devueltas a la bolsa general.</p>
          </div>
          <div class="flex flex-col p-6 bg-blue-50 rounded-xl border border-blue-100 shadow-sm">
            <p class="text-sm font-semibold text-blue-800 uppercase tracking-wider mb-2">Ahorro Mensual Acumulado</p>
            <p class="text-4xl font-bold text-blue-600">${{ auditHistory.reduce((sum, h) => sum + h.saved_usd, 0).toLocaleString() }} USD</p>
            <p class="text-xs text-blue-700 mt-2">Basado en un costo promedio estimado por licencia.</p>
          </div>
        </div>
        
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200">
                <th class="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase">Fecha</th>
                <th class="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase">Usuario</th>
                <th class="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase">Licencias</th>
                <th class="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase">Nota</th>
                <th class="px-5 py-3 text-[11px] font-bold text-slate-500 uppercase">Ahorro</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in auditHistory" :key="log.id" class="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">
                <td class="px-5 py-3 text-[12px] text-slate-600">{{ formatDate(log.timestamp) }}</td>
                <td class="px-5 py-3">
                  <div class="flex flex-col">
                    <span class="text-[13px] font-semibold text-slate-800">{{ log.display_name }}</span>
                    <span class="text-[11px] text-slate-500">{{ log.user_principal_name }}</span>
                  </div>
                </td>
                <td class="px-5 py-3 text-[12px] text-slate-600 max-w-xs truncate">{{ log.licenses || 'N/A' }}</td>
                <td class="px-5 py-3 text-[12px] text-slate-600">{{ log.note }}</td>
                <td class="px-5 py-3 text-[13px] font-semibold text-emerald-600">${{ log.saved_usd }}</td>
              </tr>
              <tr v-if="auditHistory.length === 0">
                <td colspan="5" class="px-5 py-10 text-center text-slate-500 text-sm">No hay registros de licencias recuperadas aún.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
    </div>
    
    <!-- Modal para Notas -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="isNoteModalOpen" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
          <div class="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden transform transition-all" @click.stop>
            <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
            <h3 class="text-lg font-semibold text-slate-800 flex items-center gap-2">
              <svg class="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" /></svg>
              Nota de Auditoría
            </h3>
            <button @click="isNoteModalOpen = false" class="text-slate-400 hover:text-slate-600 focus:outline-none transition-colors">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          
          <div class="p-6">
            <p class="text-[13px] text-slate-500 mb-4">
              Agrega una nota interna para <strong>{{ editingNoteUser?.displayName }}</strong>. Esta nota solo será visible en este panel para fines de seguimiento.
            </p>
            
            <textarea 
              v-model="noteText" 
              rows="4" 
              class="w-full text-[13px] p-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 outline-none resize-none transition-shadow"
              placeholder="Ej: En revisión por Gestión Humana, Licencia médica, etc..."
            ></textarea>
          </div>
          
          <div class="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3 flex-wrap">
            <button @click="isNoteModalOpen = false" :disabled="savingNote" class="px-4 py-2 text-[13px] font-medium text-slate-600 bg-white border border-slate-200 rounded-md hover:bg-slate-50 focus:outline-none transition-colors disabled:opacity-50">
              Cancelar
            </button>
            <div class="flex gap-2 w-full sm:w-auto mt-2 sm:mt-0">
              <button @click="saveNote('RECOVERED')" :disabled="savingNote" class="px-4 py-2 text-[13px] font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none flex items-center gap-2 transition-colors disabled:opacity-50 shadow-sm shadow-blue-600/20" title="Guardar nota y registrar que le quitaste la licencia para los KPIs">
                Dar de Baja
              </button>
              <button @click="saveNote('NOTE')" :disabled="savingNote" class="px-4 py-2 text-[13px] font-medium text-white bg-emerald-600 rounded-md hover:bg-emerald-700 focus:outline-none flex items-center gap-2 transition-colors disabled:opacity-50 shadow-sm shadow-emerald-600/20">
                <svg v-if="savingNote" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                Guardar Solo Nota
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
    </Teleport>
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
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
