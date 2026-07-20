<script setup>
import { ref, onMounted } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const sessions = ref([])
const loading = ref(false)
const error = ref('')

const schedule = ref({
  cron_time: '23:00',
  cron_days: '0,1,2,3,4,5,6',
  temp_path: 'C:\\conteo',
  file_prefix: 'Nova_est',
  is_active: false,
  last_run: 'No disponible',
  next_run: 'No disponible'
})
const scheduleLoading = ref(false)
const scheduleStatus = ref('')
const scheduleStatusType = ref('success')

// Toast state
const showToast = ref(false)
const toastType = ref('success')
const toastTitle = ref('')
const toastMessage = ref('')
let toastTimer = null

const daysList = [
  { value: '0', label: 'L' },
  { value: '1', label: 'M' },
  { value: '2', label: 'M' },
  { value: '3', label: 'J' },
  { value: '4', label: 'V' },
  { value: '5', label: 'S' },
  { value: '6', label: 'D' }
]

// Custom Confirm Modal State
const confirmModal = ref({
  show: false,
  title: '',
  message: '',
  btnText: 'Confirmar',
  btnClass: 'bg-red-600 hover:bg-red-700 text-white',
  action: null,
  cancelAction: null
})

function openConfirm(title, message, btnText, btnClass, action, cancelAction = null) {
  confirmModal.value = { show: true, title, message, btnText, btnClass, action, cancelAction }
}

function closeConfirm() {
  if (confirmModal.value.cancelAction) confirmModal.value.cancelAction()
  confirmModal.value.show = false
}

function executeConfirm() {
  if (confirmModal.value.action) confirmModal.value.action()
  confirmModal.value.show = false
}

function displayToast(type, title, message) {
  toastType.value = type
  toastTitle.value = title
  toastMessage.value = message
  showToast.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { showToast.value = false }, 5000)
}

function isDaySelected(dayValue) {
  if (!schedule.value.cron_days) return false
  return schedule.value.cron_days.split(',').includes(dayValue)
}

function toggleDay(dayValue) {
  let currentDays = schedule.value.cron_days ? schedule.value.cron_days.split(',') : []
  if (currentDays.includes(dayValue)) {
    currentDays = currentDays.filter(d => d !== dayValue)
  } else {
    currentDays.push(dayValue)
  }
  schedule.value.cron_days = currentDays.sort().join(',')
}

async function fetchSessions() {
  loading.value = true
  error.value = ''
  try {
    const queryParams = new URLSearchParams({
      temp_path: schedule.value.temp_path,
      file_prefix: schedule.value.file_prefix
    }).toString()
    
    const res = await authFetch(`${API_BASE}/rds/sessions?${queryParams}`)
    const data = await res.json()
    if (res.ok && data.success) {
      sessions.value = data.data
    } else {
      error.value = data.detail || 'Error al obtener sesiones'
    }
  } catch (e) {
    error.value = 'Error de red: ' + e.message
  } finally {
    loading.value = false
  }
}

async function fetchSchedule() {
  try {
    const res = await authFetch(`${API_BASE}/rds/schedule`)
    const data = await res.json()
    if (res.ok && data.success && data.data) {
      schedule.value = data.data
    }
  } catch (e) {
    console.error("Error fetching schedule:", e)
  }
}

async function saveSchedule() {
  scheduleLoading.value = true
  scheduleStatus.value = ''
  try {
    const res = await authFetch(`${API_BASE}/rds/schedule`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(schedule.value)
    })
    const data = await res.json()
    if (res.ok && data.success) {
      scheduleStatusType.value = 'success'
      scheduleStatus.value = 'Guardado.'
      fetchSchedule()
    } else {
      scheduleStatusType.value = 'error'
      scheduleStatus.value = data.detail || 'Error al guardar.'
    }
  } catch (e) {
    scheduleStatusType.value = 'error'
    scheduleStatus.value = 'Error de red.'
  } finally {
    scheduleLoading.value = false
    setTimeout(() => { scheduleStatus.value = '' }, 3000)
  }
}

async function toggleActiveStatus() {
  if (schedule.value.is_active) {
    openConfirm(
      'Desactivar Apagón Automático',
      '¿Estás seguro de que deseas desactivar la limpieza programada? Los archivos temporales ya no se borrarán automáticamente.',
      'Desactivar',
      'bg-amber-600 hover:bg-amber-700 text-white',
      async () => {
        scheduleLoading.value = true
        try {
          const res = await authFetch(`${API_BASE}/rds/schedule/disable`, { method: 'POST' })
          if (res.ok) fetchSchedule()
        } catch (e) {
          console.error(e)
        } finally {
          scheduleLoading.value = false
        }
      },
      () => {
        // Revertir switch si cancela
        schedule.value.is_active = true
      }
    )
  } else {
    // Si estaba inactivo, lo guardamos para activarlo
    schedule.value.is_active = true
    saveSchedule()
  }
}

async function killAndClean(session) {
  openConfirm(
    'Cerrar Sesión',
    `¿Estás seguro de cerrar la sesión de Windows y borrar los temporales del usuario <strong>${session.username}</strong>?`,
    'Cerrar Sesión',
    'bg-red-600 hover:bg-red-700 text-white',
    async () => {
      const origState = session.state
      session.state = 'Borrando...'
      
      try {
        const res = await authFetch(`${API_BASE}/rds/sessions/kill-and-clean`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            session_id: session.session_id, 
            username: session.username,
            temp_path: schedule.value.temp_path,
            file_prefix: schedule.value.file_prefix
          })
        })
        const data = await res.json()
        if (res.ok && data.success) {
          displayToast('success', 'Éxito', `Sesión de ${session.username} cerrada.`)
          fetchSessions()
        } else {
          session.state = origState
          displayToast('error', 'Error', data.detail || 'No se pudo cerrar la sesión.')
        }
      } catch (e) {
        session.state = origState
        displayToast('error', 'Error', 'Fallo de red.')
      }
    }
  )
}

async function massKill() {
  if (sessions.value.length === 0) return
  openConfirm(
    'Cerrar TODAS las sesiones',
    `¿Estás absolutamente seguro de cerrar las <strong>${sessions.value.length}</strong> sesiones activas y borrar todos sus archivos temporales? Esta acción desconectarÃ¡ a todos los usuarios de forma inmediata.`,
    'Cerrar Todo',
    'bg-red-600 hover:bg-red-700 text-white',
    async () => {
      for (const s of sessions.value) {
        s.state = 'Borrando...'
      }
      
      // Ejecuta apagÃ³n llamando a cada uno en serie para no saturar
      let errors = 0
      for (const s of sessions.value) {
        try {
          const res = await authFetch(`${API_BASE}/rds/sessions/kill-and-clean`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              session_id: s.session_id, 
              username: s.username,
              temp_path: schedule.value.temp_path,
              file_prefix: schedule.value.file_prefix
            })
          })
          if (!res.ok) errors++
        } catch (e) {
          errors++
        }
      }
      
      if (errors > 0) {
        displayToast('error', 'Cierre Masivo', `Finalizado con ${errors} errores.`)
      } else {
        displayToast('success', 'Cierre Masivo', 'Todas las sesiones fueron cerradas.')
      }
      fetchSessions()
    }
  )
}

onMounted(async () => {
  await fetchSchedule()
  fetchSessions()
})
</script>

<template>
  <div class="h-full flex flex-col font-sans">
    
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
      <div>
        <h1 class="text-xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
          <svg class="w-6 h-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Gestor RDS (Novasoft)
        </h1>
        <p class="text-sm text-slate-500 mt-1">Gestiona sesiones de Windows y automatiza la limpieza de archivos de control temporales.</p>
      </div>
      
      <div class="flex gap-2">
        <button @click="fetchSessions" class="flex items-center gap-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 px-3 py-1.5 rounded-sm text-sm font-medium transition-colors shadow-sm">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
      </div>
    </div>

    <!-- Error Global -->
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-sm text-sm mb-4 flex gap-3">
      <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      {{ error }}
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 overflow-hidden">
      
      <!-- Panel Izquierdo: Config -->
      <div class="lg:col-span-1 bg-white border border-slate-200 rounded-sm shadow-sm overflow-y-auto">
        <div class="p-3 border-b border-slate-200 bg-slate-50">
          <h3 class="text-[13px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <svg class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            Configuración & Apagón
          </h3>
        </div>
        
        <div class="p-4 space-y-5">
          <!-- Ruta -->
          <div>
            <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Ruta Carpeta Conteo</label>
            <input v-model="schedule.temp_path" type="text" placeholder="Ej: C:\conteo" class="w-full border border-slate-300 rounded-sm px-3 py-1.5 text-[12px] font-mono focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
          </div>
          
          <!-- Prefijo -->
          <div>
            <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Prefijo de Archivo</label>
            <input v-model="schedule.file_prefix" type="text" placeholder="Ej: nova.ft" class="w-full border border-slate-300 rounded-sm px-3 py-1.5 text-[12px] font-mono focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
          </div>
          
          <!-- Hora -->
          <div>
            <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Hora de Ejecución (24H)</label>
            <input v-model="schedule.cron_time" type="time" class="w-full border border-slate-300 rounded-sm px-3 py-1.5 text-[12px] focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
          </div>
          
          <!-- Dias -->
          <div>
            <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Días de la semana</label>
            <div class="flex gap-1.5 justify-between">
              <button 
                v-for="day in daysList" :key="day.value"
                @click="toggleDay(day.value)"
                type="button"
                :class="[
                  'flex-1 h-7 rounded-sm text-[11px] font-bold transition-all border',
                  isDaySelected(day.value) ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm' : 'bg-slate-50 border-slate-200 text-slate-500 hover:bg-slate-100'
                ]"
              >
                {{ day.label }}
              </button>
            </div>
          </div>
          
          <!-- Toggle -->
          <!-- Estado del Apagón -->
          <div class="pt-4 border-t border-slate-100 flex items-center justify-between">
            <div>
              <span class="text-sm font-semibold text-slate-700">Estado del Apagón</span>
              
              <!-- Info de ejecuciÃ³n (solo si está activo) -->
              <div v-if="schedule.is_active" class="mt-1 text-[11px] text-slate-500 space-y-0.5">
                <div class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  Última vez: <span class="font-medium text-slate-700">{{ schedule.last_run }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  Próxima vez: <span class="font-medium text-slate-700">{{ schedule.next_run }}</span>
                </div>
              </div>
            </div>
            
            <button @click="toggleActiveStatus" :class="[schedule.is_active ? 'bg-emerald-500' : 'bg-slate-300', 'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:ring-offset-2']" role="switch" :aria-checked="schedule.is_active">
              <span :class="[schedule.is_active ? 'translate-x-5' : 'translate-x-0', 'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out']"></span>
            </button>
          </div>
          
          <div v-if="scheduleStatus" :class="['text-[11px] p-2 rounded-sm text-center font-medium mt-2', scheduleStatusType === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700']">
            {{ scheduleStatus }}
          </div>
          
          <button @click="saveSchedule" :disabled="scheduleLoading" class="w-full bg-slate-800 hover:bg-slate-900 text-white font-medium py-2 px-4 rounded-sm transition-colors flex items-center justify-center gap-2 mt-4 text-sm disabled:opacity-50">
            <svg v-if="scheduleLoading" class="w-3.5 h-3.5 border-2 border-slate-300 border-t-white rounded-full animate-spin shrink-0"></svg>
            Guardar Cambios
          </button>
        </div>
      </div>

      <!-- Panel Derecho: Tabla Live -->
      <div class="lg:col-span-3 bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden flex flex-col">
        <div class="p-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h3 class="text-[13px] font-bold text-slate-700 uppercase tracking-wider flex items-center gap-2">
            <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
            Sesiones Activas (Live)
            <span class="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[10px] ml-1">{{ sessions.length }} usuarios</span>
          </h3>
          <button @click="massKill" :disabled="sessions.length === 0" class="border border-red-600 text-red-600 hover:bg-red-50 px-3 py-1 rounded-sm text-[11px] font-bold transition-colors disabled:opacity-50">
            CERRAR TODAS LAS SESIONES
          </button>
        </div>
        
        <div class="flex-1 overflow-auto">
          <table class="w-full text-left text-[13px]">
            <thead class="bg-slate-50 border-b border-slate-200 sticky top-0 z-10 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th class="px-5 py-3">Nombre Completo</th>
                <th class="px-5 py-3">Usuario (UPN)</th>
                <th class="px-5 py-3">Estado</th>
                <th class="px-5 py-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-slate-700">
              <tr v-if="loading" class="bg-white">
                <td colspan="4" class="px-5 py-12 text-center">
                  <span class="w-8 h-8 border-2 border-slate-200 border-t-indigo-600 rounded-full animate-spin inline-block mb-2"></span>
                  <p class="text-sm text-slate-500 font-medium">Buscando archivos temporales y sesiones de Windows...</p>
                </td>
              </tr>
              <tr v-else-if="sessions.length === 0" class="bg-white">
                <td colspan="4" class="px-5 py-12 text-center text-slate-500">
                  <svg class="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                  <p class="text-[13px] font-medium">El sistema está limpio.</p>
                  <p class="text-[12px] text-slate-400 mt-1">No se encontraron archivos nova.ft* atrapados.</p>
                </td>
              </tr>
              <tr v-for="session in sessions" :key="session.username" class="hover:bg-slate-50 transition-colors">
                <td class="px-5 py-2">
                  <div class="font-medium text-slate-800">{{ session.full_name }}</div>
                  <div class="text-[10px] text-slate-400 font-mono mt-0.5" v-if="session.session_id">ID: {{ session.session_id }} ({{ session.session_name }})</div>
                  <div class="text-[10px] text-amber-500 font-mono mt-0.5" v-else>Sin Sesión de Windows (Archivo zombi)</div>
                </td>
                <td class="px-5 py-2 font-mono text-slate-600">{{ session.username }}</td>
                <td class="px-5 py-2">
                  <span :class="[
                    'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-medium border',
                    session.state.toLowerCase() === 'active' || session.state.toLowerCase() === 'activo' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 
                    session.state.toLowerCase() === 'disc' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-50 text-slate-600 border-slate-200'
                  ]">
                    <span :class="[
                      'w-1.5 h-1.5 rounded-full',
                      session.state.toLowerCase() === 'active' || session.state.toLowerCase() === 'activo' ? 'bg-emerald-500' : 
                      session.state.toLowerCase() === 'disc' ? 'bg-amber-500' : 'bg-slate-400'
                    ]"></span>
                    {{ session.state }}
                  </span>
                </td>
                <td class="px-5 py-2 text-right">
                  <button 
                    @click="killAndClean(session)"
                    :disabled="session.state === 'Borrando...'"
                    class="border border-red-600 text-red-700 hover:bg-red-50 px-3 py-1 text-[11px] rounded-sm font-medium transition-colors disabled:opacity-50 inline-flex items-center gap-1 ml-auto min-w-[100px] justify-center"
                  >
                    <svg v-if="session.state === 'Borrando...'" class="w-3 h-3 border-2 border-red-600 border-t-transparent rounded-full animate-spin shrink-0"></svg>
                    <svg v-else class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    <span>Cerrar Sesión</span>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- Toast Notification -->
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <transition enter-active-class="transition ease-out duration-300 transform" enter-from-class="opacity-0 translate-y-[-1rem] scale-95" enter-to-class="opacity-100 translate-y-0 scale-100" leave-active-class="transition ease-in duration-200" leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-95">
        <div v-if="showToast" :class="['pointer-events-auto flex items-start p-3 rounded-sm shadow-lg border max-w-sm w-full', toastType === 'success' ? 'bg-white border-emerald-200' : 'bg-white border-red-200']">
          <div :class="['flex-shrink-0 mr-3', toastType === 'success' ? 'text-emerald-500' : 'text-red-500']">
            <svg v-if="toastType === 'success'" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <div class="flex-1 pt-0.5">
            <h3 class="text-[13px] font-semibold text-slate-800">{{ toastTitle }}</h3>
            <p class="mt-0.5 text-[12px] text-slate-500">{{ toastMessage }}</p>
          </div>
          <button @click="showToast = false" class="ml-4 flex-shrink-0 text-slate-400 hover:text-slate-600 focus:outline-none">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </transition>
    </div>

    <!-- Custom Confirm Modal -->
    <transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="transition-opacity duration-200" leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="confirmModal.show" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/20 p-4">
        <div class="bg-white rounded-md shadow-2xl max-w-md w-full overflow-hidden border border-slate-200 transform transition-all">
          <div class="p-5 border-b border-slate-100 flex items-center gap-3">
            <div class="flex-shrink-0 text-red-600">
              <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            </div>
            <h3 class="text-lg font-bold text-slate-800">{{ confirmModal.title }}</h3>
          </div>
          <div class="p-5 text-sm text-slate-600 leading-relaxed" v-html="confirmModal.message"></div>
          <div class="bg-slate-50 p-4 flex items-center justify-end gap-3 border-t border-slate-100">
            <button @click="closeConfirm" class="px-4 py-2 border border-slate-300 rounded-sm text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors">
              Cancelar
            </button>
            <button @click="executeConfirm" :class="['px-4 py-2 rounded-sm text-sm font-medium transition-colors shadow-sm', confirmModal.btnClass]">
              {{ confirmModal.btnText }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>
