<script setup>
import { ref, onMounted, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const filters = ref({
  recipient: '',
  sender: '',
  subject: '',
  qtype: 'All'
})

const quarantineTypes = [
  { value: 'All', label: 'Todos los Tipos' },
  { value: 'Spam', label: 'Spam' },
  { value: 'HighConfidenceSpam', label: 'Spam (Alta Confianza)' },
  { value: 'Phish', label: 'Phishing' },
  { value: 'HighConfidencePhish', label: 'Phishing (Alta Confianza)' },
  { value: 'Malware', label: 'Malware' }
]

const emails = ref([])
const loading = ref(false)
const error = ref('')

const isCheckingSetup = ref(true)
const isSetupReady = ref(false)
const setupDetails = ref(null)
const isSettingUp = ref(false)
const showSetupResult = ref(false)
const setupResultData = ref(null)

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

onMounted(async () => {
  try {
    const res = await authFetch(`${API_BASE}/quarantine/status`)
    const data = await res.json()
    if (res.ok && data.success) {
      setupDetails.value = data.data
      isSetupReady.value = data.data.module_installed && data.data.cert_installed
      if (isSetupReady.value) {
        searchQuarantine() // Auto-load recent items
      }
    }
  } catch (e) {
    console.error("Error checking setup", e)
  } finally {
    isCheckingSetup.value = false
  }
})

async function runSetup() {
  isSettingUp.value = true
  try {
    const res = await authFetch(`${API_BASE}/quarantine/setup`, { method: 'POST' })
    const data = await res.json()
    if (res.ok && data.success) {
      setupResultData.value = data.data
      showSetupResult.value = true
      isSetupReady.value = true
    } else {
      displayToast('error', 'Error en Configuración', data.detail || 'Error al ejecutar scripts.')
    }
  } catch (e) {
    displayToast('error', 'Red', 'Error: ' + e.message)
  } finally {
    isSettingUp.value = false
  }
}

async function searchQuarantine() {
  loading.value = true
  error.value = ''
  emails.value = []
  
  try {
    const params = new URLSearchParams()
    if (filters.value.recipient) params.append('email', filters.value.recipient.replace(/[<>]/g, '').trim())
    if (filters.value.sender) params.append('sender', filters.value.sender.replace(/[<>]/g, '').trim())
    if (filters.value.subject) params.append('subject', filters.value.subject.trim())
    if (filters.value.qtype && filters.value.qtype !== 'All') params.append('qtype', filters.value.qtype)
      
    const url = `${API_BASE}/quarantine/search?${params.toString()}`
    const res = await authFetch(url)
    const data = await res.json()
    
    if (res.ok && data.success) {
      emails.value = data.data || []
      if (emails.value.length === 0) {
        displayToast('info', 'Sin resultados', 'No se encontraron correos en cuarentena con estos filtros.')
      }
    } else {
      error.value = data.detail || 'Error al buscar en cuarentena.'
      displayToast('error', 'Error', error.value)
    }
  } catch (e) {
    error.value = 'Fallo de Red: ' + e.message
    displayToast('error', 'Red', error.value)
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  filters.value = { recipient: '', sender: '', subject: '', qtype: 'All' }
  searchQuarantine()
}

const showReleaseModal = ref(false)
const selectedEmail = ref(null)
const isReleasing = ref(false)

function openReleaseConfirm(email) {
  selectedEmail.value = email
  showReleaseModal.value = true
}

function cancelRelease() {
  showReleaseModal.value = false
  selectedEmail.value = null
}

async function confirmRelease() {
  if (!selectedEmail.value) return
  
  isReleasing.value = true
  try {
    const payload = {
      identity: selectedEmail.value.Identity,
      user_email: selectedEmail.value.RecipientAddress || 'Varios Destinatarios',
      username_requesting: localStorage.getItem('username') || 'Unknown User'
    }
    
    const res = await authFetch(`${API_BASE}/quarantine/release`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    const data = await res.json()
    if (res.ok && data.success) {
      displayToast('success', 'Éxito', 'Correo liberado correctamente. (Auditoría Registrada)')
      // Remove from list
      emails.value = emails.value.filter(e => e.Identity !== selectedEmail.value.Identity)
    } else {
      displayToast('error', 'Error', data.detail || 'No se pudo liberar el correo.')
    }
  } catch (e) {
    displayToast('error', 'Red', 'Error al comunicar con el servidor: ' + e.message)
  } finally {
    isReleasing.value = false
    showReleaseModal.value = false
    selectedEmail.value = null
  }
}

function getTypeStyle(type) {
  if (!type) return 'bg-slate-100 text-slate-800'
  const t = type.toLowerCase()
  if (t.includes('phish')) return 'bg-red-100 text-red-800'
  if (t.includes('malware')) return 'bg-purple-100 text-purple-800'
  if (t.includes('spam')) return 'bg-orange-100 text-orange-800'
  return 'bg-blue-100 text-blue-800'
}
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6 fade-in flex flex-col h-[calc(100vh-64px)]">
    <!-- Setup Overlay -->
    <div v-if="!isCheckingSetup && !isSetupReady" class="bg-white p-8 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col items-center justify-center text-center">
      <div class="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-4">
        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
      </div>
      <h2 class="text-xl font-bold text-slate-800 mb-2">Conexión con Microsoft 365 Requerida</h2>
      <p class="text-slate-500 mb-6 max-w-md">El sistema detecta que el backend se reinició con un usuario distinto (Administrador) y requiere generar los permisos locales nuevamente para poder conectar con Exchange Online.</p>
      <button @click="runSetup" :disabled="isSettingUp" class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50">
        <svg v-if="isSettingUp" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
        {{ isSettingUp ? 'Configurando...' : 'Generar Certificado Local' }}
      </button>
    </div>

    <!-- Toast Notification -->
    <Transition name="toast">
      <div v-if="showToast" class="fixed bottom-4 right-4 z-[999] flex items-center p-4 mb-4 w-full max-w-sm text-gray-500 bg-white rounded-lg shadow-lg border border-slate-100" role="alert">
        <div class="inline-flex items-center justify-center flex-shrink-0 w-8 h-8 rounded-lg"
             :class="{'text-green-500 bg-green-100': toastType === 'success', 'text-red-500 bg-red-100': toastType === 'error', 'text-orange-500 bg-orange-100': toastType === 'warning', 'text-blue-500 bg-blue-100': toastType === 'info'}">
          <svg v-if="toastType === 'success'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>
          <svg v-if="toastType === 'error'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
          <svg v-if="toastType === 'info'" class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/></svg>
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
    <div class="mb-5 shrink-0">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600 font-medium">Dashboard Cuarentena</span>
      </div>
      <div class="flex justify-between items-end">
        <div>
          <h2 class="text-2xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
            <svg class="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
            Centro de Cuarentena (Defender)
          </h2>
          <p class="text-sm text-gray-500 mt-1">Explora, filtra y libera correos atrapados globalmente.</p>
        </div>
        <button v-if="isSetupReady" @click="searchQuarantine" class="text-[13px] bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" :class="{'animate-spin': loading}"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar Lista
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isCheckingSetup" class="flex-1 flex items-center justify-center">
      <div class="inline-block w-8 h-8 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin"></div>
    </div>

    <!-- Setup Required Banner -->
    <div v-else-if="!isSetupReady" class="bg-white rounded-xl shadow-sm border border-orange-200 p-8 text-center animate-[slideUp_0.3s_ease-out] mx-auto w-full max-w-3xl mt-10">
      <div class="w-16 h-16 bg-orange-100 text-orange-500 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
      </div>
      <h3 class="text-xl font-bold text-slate-800 mb-2">Configuración Requerida</h3>
      <p class="text-[14px] text-slate-600 mb-6 max-w-xl mx-auto">
        Para conectarse a Exchange Online de forma desatendida, este servidor backend requiere el módulo <code class="bg-slate-100 px-1 py-0.5 rounded text-orange-600">ExchangeOnlineManagement</code> y un certificado de autenticación local.
      </p>
      
      <div class="flex flex-col sm:flex-row justify-center gap-4">
        <div class="bg-slate-50 p-4 rounded-lg text-left flex-1 max-w-xs border border-slate-200 mx-auto">
          <p class="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Estado del Servidor</p>
          <div class="flex items-center gap-2 mb-2">
            <span :class="setupDetails?.module_installed ? 'text-green-500' : 'text-slate-400'">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
            </span>
            <span class="text-[13px] text-slate-700">Módulo PS Instalado</span>
          </div>
          <div class="flex items-center gap-2">
            <span :class="setupDetails?.cert_installed ? 'text-green-500' : 'text-slate-400'">
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
            </span>
            <span class="text-[13px] text-slate-700">Certificado Generado</span>
          </div>
        </div>
      </div>
      
      <div class="mt-8">
        <button @click="runSetup" :disabled="isSettingUp" class="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium text-[14px] px-8 py-3 rounded-lg shadow-sm transition-all disabled:opacity-70 disabled:cursor-not-allowed">
          <svg v-if="isSettingUp" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          <svg v-else class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
          {{ isSettingUp ? 'Configurando entorno...' : 'Instalar y Configurar Ahora' }}
        </button>
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="fade-in flex flex-col flex-1 min-h-0">
      
      <!-- Filter Bar -->
      <div class="bg-white rounded-t-xl border border-slate-200 p-4 shrink-0 shadow-sm z-10">
        <div class="flex flex-wrap items-end gap-4">
          <div class="flex-1 min-w-[200px]">
            <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Destinatario</label>
            <div class="relative">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
              <input type="text" v-model="filters.recipient" @keyup.enter="searchQuarantine" placeholder="maria@empresa.com" class="w-full pl-9 pr-3 py-2 text-[13px] bg-slate-50 border border-slate-200 rounded-lg focus:border-blue-500 focus:bg-white outline-none transition-colors" />
            </div>
          </div>
          
          <div class="flex-1 min-w-[200px]">
            <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Remitente</label>
            <div class="relative">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
              <input type="text" v-model="filters.sender" @keyup.enter="searchQuarantine" placeholder="ventas@proveedor.com" class="w-full pl-9 pr-3 py-2 text-[13px] bg-slate-50 border border-slate-200 rounded-lg focus:border-blue-500 focus:bg-white outline-none transition-colors" />
            </div>
          </div>

          <div class="flex-1 min-w-[200px]">
            <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Asunto</label>
            <div class="relative">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <input type="text" v-model="filters.subject" @keyup.enter="searchQuarantine" placeholder="Cotización..." class="w-full pl-9 pr-3 py-2 text-[13px] bg-slate-50 border border-slate-200 rounded-lg focus:border-blue-500 focus:bg-white outline-none transition-colors" />
            </div>
          </div>
          
          <div class="w-[200px]">
            <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Razón de Cuarentena</label>
            <select v-model="filters.qtype" class="w-full px-3 py-2 text-[13px] bg-slate-50 border border-slate-200 rounded-lg focus:border-blue-500 focus:bg-white outline-none transition-colors">
              <option v-for="t in quarantineTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>

          <div class="flex gap-2">
            <button @click="clearFilters" class="px-4 py-2 text-[13px] font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors" title="Limpiar Filtros">
              Limpiar
            </button>
            <button @click="searchQuarantine" :disabled="loading" class="px-6 py-2 text-[13px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center justify-center gap-2 min-w-[120px]">
              <svg v-if="!loading" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              <svg v-else class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
              {{ loading ? 'Filtrando...' : 'Filtrar' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Data Table -->
      <div class="bg-white border-x border-b border-slate-200 rounded-b-xl shadow-sm flex-1 overflow-hidden flex flex-col">
        <div class="flex-1 overflow-auto relative">
          
          <table class="w-full text-left min-w-[1000px]">
            <thead class="sticky top-0 bg-white shadow-sm z-10">
              <tr class="border-b border-slate-200 bg-slate-50/90 backdrop-blur">
                <th class="px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider w-[220px]">Destinatario</th>
                <th class="px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider w-[220px]">Remitente</th>
                <th class="px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Asunto</th>
                <th class="px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider w-[160px]">Fecha (UTC)</th>
                <th class="px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider w-[120px]">Razón</th>
                <th class="px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider w-[100px] text-center">Acción</th>
              </tr>
            </thead>
            
            <tbody v-if="loading && emails.length === 0">
              <tr>
                <td colspan="6" class="px-4 py-16 text-center">
                  <div class="inline-block w-8 h-8 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-3"></div>
                  <p class="text-[13px] text-slate-500">Consultando a Microsoft 365 Defender...</p>
                </td>
              </tr>
            </tbody>
            
            <tbody v-else-if="emails.length === 0">
              <tr>
                <td colspan="6" class="px-4 py-16 text-center">
                  <svg class="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 19v-8.93a2 2 0 01.89-1.664l7-4.666a2 2 0 012.22 0l7 4.666A2 2 0 0121 10.07V19M3 19a2 2 0 002 2h14a2 2 0 002-2M3 19l6.75-4.5M21 19l-6.75-4.5M3 10l6.75 4.5M21 10l-6.75 4.5m0 0l-1.14.76a2 2 0 01-2.22 0l-1.14-.76" /></svg>
                  <p class="text-[14px] font-medium text-slate-700">No hay correos en cuarentena</p>
                  <p class="text-[13px] text-slate-500 mt-1">Modifica los filtros o intenta de nuevo más tarde.</p>
                </td>
              </tr>
            </tbody>

            <tbody v-else>
              <tr v-for="(email, idx) in emails" :key="email.Identity" class="border-b border-slate-100 hover:bg-slate-50/80 transition-colors group">
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-bold shrink-0">
                      {{ email.RecipientAddress ? email.RecipientAddress.charAt(0).toUpperCase() : '?' }}
                    </div>
                    <span class="text-[12px] font-medium text-slate-800 truncate block max-w-[180px]" :title="email.RecipientAddress">
                      {{ email.RecipientAddress }}
                    </span>
                  </div>
                </td>
                <td class="px-4 py-3 text-[12px] text-slate-600 truncate max-w-[200px]" :title="email.SenderAddress">
                  {{ email.SenderAddress }}
                </td>
                <td class="px-4 py-3 text-[12px] text-slate-800 font-medium">
                  <div class="truncate max-w-[300px]" :title="email.Subject">{{ email.Subject || '(Sin Asunto)' }}</div>
                </td>
                <td class="px-4 py-3 text-[12px] text-slate-500">
                  {{ email.ReceivedTime.replace('T', ' ') }}
                </td>
                <td class="px-4 py-3">
                  <span :class="['inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium whitespace-nowrap', getTypeStyle(email.QuarantineTypes)]">
                    {{ email.QuarantineTypes }}
                  </span>
                </td>
                <td class="px-4 py-3 text-center">
                  <button @click="openReleaseConfirm(email)" class="text-[11px] font-semibold text-white bg-blue-600 hover:bg-blue-700 px-3 py-1.5 rounded shadow-sm transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 inline-flex items-center gap-1.5 w-full justify-center">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" /></svg>
                    Liberar
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

        </div>
        <div class="px-4 py-2 border-t border-slate-200 bg-slate-50 text-[11px] text-slate-500 flex justify-between items-center">
          <span>Mostrando {{ emails.length }} correos retenidos.</span>
          <span v-if="emails.length >= 100" class="text-orange-600 flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Límite de visualización (100) alcanzado. Usa filtros para acotar.
          </span>
        </div>
      </div>
    </div>
    
    <!-- Release Confirmation Modal -->
    <Transition name="modal">
      <div v-if="showReleaseModal" class="fixed inset-0 z-[999] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all">
          <div class="flex items-center justify-between p-4 border-b border-slate-100 bg-slate-50">
            <h3 class="text-[15px] font-semibold text-slate-800 flex items-center gap-2">
              <svg class="w-5 h-5 text-orange-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
              Confirmación de Seguridad
            </h3>
            <button @click="cancelRelease" class="text-slate-400 hover:text-slate-600 transition-colors">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          
          <div class="p-5">
            <p class="text-[13px] text-slate-700 mb-4">¿Estás seguro que deseas liberar este correo de la cuarentena? Será entregado inmediatamente a <strong class="text-slate-900">{{ selectedEmail?.RecipientAddress }}</strong>.</p>
            
            <div v-if="selectedEmail" class="bg-orange-50/50 border-l-4 border-orange-400 p-3 rounded-r-lg mb-5">
              <p class="text-[12px] text-slate-800 mb-1.5"><span class="font-semibold text-slate-600 w-[70px] inline-block">De:</span> {{ selectedEmail.SenderAddress }}</p>
              <p class="text-[12px] text-slate-800 mb-1.5"><span class="font-semibold text-slate-600 w-[70px] inline-block">Para:</span> {{ selectedEmail.RecipientAddress }}</p>
              <p class="text-[12px] text-slate-800 line-clamp-2"><span class="font-semibold text-slate-600 w-[70px] inline-block">Asunto:</span> {{ selectedEmail.Subject || '(Sin Asunto)' }}</p>
            </div>
            
            <p class="text-[11px] text-slate-500 flex gap-2">
              <svg class="w-4 h-4 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
              Esta acción quedará registrada bajo tu usuario en la bitácora de auditoría del sistema.
            </p>
          </div>
          
          <div class="px-5 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-2">
            <button @click="cancelRelease" :disabled="isReleasing" class="px-4 py-2 text-[12px] font-medium text-slate-600 hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors">
              Cancelar
            </button>
            <button @click="confirmRelease" :disabled="isReleasing" class="px-4 py-2 text-[12px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-70">
              <svg v-if="isReleasing" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
              <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
              {{ isReleasing ? 'Liberando...' : 'Confirmar y Liberar' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Setup Result Modal (Same as before) -->
    <Transition name="modal">
      <div v-if="showSetupResult" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden transform transition-all">
          <div class="bg-green-600 px-6 py-4 flex items-center justify-between">
            <h3 class="text-lg font-bold text-white flex items-center gap-2">
              <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
              ¡Entorno Configurado con Éxito!
            </h3>
            <button @click="showSetupResult = false" class="text-white/70 hover:text-white transition-colors">
              <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
          <div class="p-6">
            <p class="text-[14px] text-slate-700 mb-6">
              El módulo de PowerShell y el certificado se instalaron correctamente en este servidor. 
              Para que el sistema se conecte a Microsoft 365, por favor sigue estos 4 pasos en el portal de Azure:
            </p>
            
            <div class="space-y-4 mb-6">
              <div class="flex gap-4">
                <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">1</div>
                <div>
                  <p class="text-[13px] font-semibold text-slate-800">Busca el archivo del certificado</p>
                  <p class="text-[12px] text-slate-600">Se exportó automáticamente a: <code class="bg-slate-100 text-slate-800 px-1 py-0.5 rounded">{{ setupResultData?.cer_path }}</code></p>
                </div>
              </div>
              <div class="flex gap-4">
                <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">2</div>
                <div>
                  <p class="text-[13px] font-semibold text-slate-800">Súbelo a Entra ID</p>
                  <p class="text-[12px] text-slate-600">Ve a Registros de Aplicaciones -> Admin DA -> Certificados y Secretos -> Cargar Certificado.</p>
                </div>
              </div>
              <div class="flex gap-4">
                <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">3</div>
                <div>
                  <p class="text-[13px] font-semibold text-slate-800">Valida que coincida la Huella Digital (Thumbprint)</p>
                  <p class="text-[12px] text-slate-600">Verifica que Azure muestre este valor: <code class="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded font-mono">{{ setupResultData?.thumbprint }}</code></p>
                </div>
              </div>
              <div class="flex gap-4">
                <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold shrink-0">4</div>
                <div>
                  <p class="text-[13px] font-semibold text-slate-800">Asigna Permisos y Roles</p>
                  <p class="text-[12px] text-slate-600">En la app, agrega el permiso de API <span class="font-medium">Exchange.ManageAsApp</span> (y otorga consentimiento). Luego, en Roles de Entra, haz miembro a la app del rol <span class="font-medium">Administrador de Exchange</span>.</p>
                </div>
              </div>
            </div>
            
            <div class="flex justify-end pt-4 border-t border-slate-100">
              <button @click="showSetupResult = false; searchQuarantine()" class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors">
                ¡Entendido, Comenzar a usar!
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

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
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-active .transform,
.modal-leave-active .transform {
  transition: transform 0.3s ease;
}
.modal-enter-from .transform {
  transform: scale(0.95) translateY(-20px);
}
.modal-leave-to .transform {
  transform: scale(0.95) translateY(-20px);
}
.fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
