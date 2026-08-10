<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

// ── Estado
const activeTab = ref('command')  // 'command' | 'live' | 'history'
const activeSessions = ref([])
const completedSessions = ref([])
const selectedSession = ref(null)
const selectedSessionEvents = ref([])
const viewerWs = ref(null)
const isViewerConnected = ref(false)
const loading = ref(false)
const commandCopied = ref(false)
const eventLogEl = ref(null)
let pollInterval = null

// ── Generar comando PowerShell
// Por defecto, asumimos que el backend corre en el puerto 8000 de la misma IP
const defaultUrl = window.location.protocol + '//' + window.location.hostname + ':8000'
const serverUrl = ref(defaultUrl)
const issueDescription = ref('')

const generatedCommand = computed(() => {
  const url = serverUrl.value.replace(/\/$/, '')
  const issue = issueDescription.value.trim() || 'El equipo se reinicia inesperadamente'
  return `powershell -ExecutionPolicy Bypass -Command "& { Invoke-WebRequest -Uri '${url}/api/v1/diagnostics/script' -OutFile '$env:TEMP\\Invoke-ITDiagnostic.ps1'; & '$env:TEMP\\Invoke-ITDiagnostic.ps1' -ServerUrl '${url}' -Issue '${issue}' }"`
})

const simpleCommand = computed(() => {
  const url = serverUrl.value.replace(/\/$/, '')
  const issue = issueDescription.value.trim() || 'El equipo se reinicia inesperadamente'
  return `.\\Invoke-ITDiagnostic.ps1 -ServerUrl "${url}" -Issue "${issue}"`
})

function copyCommand(text) {
  navigator.clipboard.writeText(text)
  commandCopied.value = true
  setTimeout(() => { commandCopied.value = false }, 3000)
}

// ── Polling de sesiones activas
async function fetchSessions() {
  try {
    const [activeRes, historyRes] = await Promise.all([
      authFetch(`${API_BASE}/diagnostics/sessions`),
      authFetch(`${API_BASE}/diagnostics/history`)
    ])
    
    if (activeRes.ok) {
      const data = await activeRes.json()
      activeSessions.value = data.active_sessions || []
    }
    if (historyRes.ok) {
      const data = await historyRes.json()
      completedSessions.value = data.sessions || []
    }
  } catch (e) {
    console.error('Error fetching sessions:', e)
  }
}

// ── Viewer WebSocket (monitoreo en tiempo real)
function connectViewer(sessionId) {
  disconnectViewer()
  selectedSession.value = sessionId
  selectedSessionEvents.value = []
  activeTab.value = 'live'
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.hostname}:8000/api/v1/diagnostics/ws/viewer/${sessionId}`
  
  const ws = new WebSocket(wsUrl)
  viewerWs.value = ws
  
  ws.onopen = () => {
    isViewerConnected.value = true
  }
  
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'viewer_connected') return
      selectedSessionEvents.value.push(msg)
      // Auto-scroll
      nextTick(() => {
        if (eventLogEl.value) {
          eventLogEl.value.scrollTop = eventLogEl.value.scrollHeight
        }
      })
    } catch (e) {
      console.error('Error parsing viewer message:', e)
    }
  }
  
  ws.onclose = () => {
    isViewerConnected.value = false
  }
  
  ws.onerror = () => {
    isViewerConnected.value = false
  }
}

function disconnectViewer() {
  if (viewerWs.value) {
    viewerWs.value.close()
    viewerWs.value = null
  }
  isViewerConnected.value = false
}

// ── Ver detalle de sesión completada
async function viewCompletedSession(sessionId) {
  loading.value = true
  selectedSession.value = sessionId
  activeTab.value = 'live'
  try {
    const res = await authFetch(`${API_BASE}/diagnostics/history/${sessionId}`)
    if (res.ok) {
      const data = await res.json()
      selectedSessionEvents.value = data.event_log || []
    }
  } catch (e) {
    console.error('Error:', e)
  } finally {
    loading.value = false
  }
}

// ── Helpers de UI
function getSeverityConfig(severity) {
  const map = {
    critical: { label: 'Crítico', bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500' },
    high:     { label: 'Alto', bg: 'bg-orange-100', text: 'text-orange-700', dot: 'bg-orange-500' },
    medium:   { label: 'Medio', bg: 'bg-yellow-100', text: 'text-yellow-700', dot: 'bg-yellow-500' },
    low:      { label: 'Bajo', bg: 'bg-green-100', text: 'text-green-700', dot: 'bg-green-500' },
  }
  return map[severity] || map.medium
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatDate(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) + ' ' + d.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
}

function getEventIcon(type) {
  const icons = {
    'session_started':      '🔌',
    'agent_thought':        '🧠',
    'execute_command':      '🔬',
    'command_result':       '🖵️',
    'command_blocked':      '🛡️',
    'command_timeout':      '⏱️',
    'search_web':           '🔍',
    'diagnosis_complete':   '✅',
    'diagnosis_incomplete': '⚠️',
    'session_end':          '🏁',
    'session_disconnected': '❌',
    'error':                '🔴',
    'status_update':        '📡',
  }
  return icons[type] || '•'
}

// ── Lifecycle
onMounted(async () => {
  // Try to get the real server IP from the backend
  try {
    const res = await authFetch(`${API_BASE}/diagnostics/server-ip`)
    if (res.ok) {
      const data = await res.json()
      serverUrl.value = `http://${data.ip}:${data.port}`
    }
  } catch (e) {
    console.error('No se pudo obtener la IP del servidor:', e)
  }

  fetchSessions()
  pollInterval = setInterval(fetchSessions, 5000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
  disconnectViewer()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-gray-900 tracking-tight">Diagnóstico IT con IA</h1>
        <p class="text-sm text-gray-500 mt-1">Agente inteligente de diagnóstico remoto · Powered by Google Gemini</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Indicador de sesiones activas -->
        <div v-if="activeSessions.length > 0" class="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-lg">
          <span class="relative flex h-2.5 w-2.5">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
          <span class="text-sm font-medium text-emerald-700">{{ activeSessions.length }} sesión{{ activeSessions.length > 1 ? 'es' : '' }} activa{{ activeSessions.length > 1 ? 's' : '' }}</span>
        </div>
        <button @click="fetchSessions" class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors">
          <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
      </div>
    </div>
    
    <!-- Tabs -->
    <div class="border-b border-gray-200">
      <nav class="flex gap-6">
        <button 
          @click="activeTab = 'command'" 
          :class="['pb-3 text-sm font-medium border-b-2 transition-colors', activeTab === 'command' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700']"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
            Generar comando
          </span>
        </button>
        <button 
          @click="activeTab = 'live'" 
          :class="['pb-3 text-sm font-medium border-b-2 transition-colors', activeTab === 'live' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700']"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
            Monitor en vivo
            <span v-if="activeSessions.length" class="bg-emerald-500 text-white text-xs rounded-full px-1.5 py-0.5 leading-none">{{ activeSessions.length }}</span>
          </span>
        </button>
        <button 
          @click="activeTab = 'history'" 
          :class="['pb-3 text-sm font-medium border-b-2 transition-colors', activeTab === 'history' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700']"
        >
          <span class="flex items-center gap-2">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            Historial
            <span v-if="completedSessions.length" class="bg-gray-200 text-gray-600 text-xs rounded-full px-1.5 py-0.5 leading-none">{{ completedSessions.length }}</span>
          </span>
        </button>
      </nav>
    </div>

    <div v-if="activeTab === 'command'" class="flex flex-col items-center justify-center w-full max-w-3xl mx-auto py-10 lg:py-20">
      
      <!-- Título Saludo tipo IA -->
      <div class="text-center mb-8">
        <h2 class="text-3xl font-semibold text-slate-800 mb-3 tracking-tight">¿Qué ocurre en el equipo?</h2>
        <p class="text-slate-500 text-sm">Describe el problema para generar automáticamente el payload de diagnóstico.</p>
      </div>

      <!-- Área de Input (Estilo ChatGPT/Gemini) -->
      <div class="w-full relative bg-white rounded-2xl shadow-sm border border-slate-200 focus-within:border-blue-500 focus-within:shadow-md focus-within:ring-4 focus-within:ring-blue-500/10 transition-all">
        <textarea 
          v-model="issueDescription" 
          rows="1"
          class="w-full px-5 py-5 text-slate-700 bg-transparent outline-none resize-none min-h-[70px] text-base"
          placeholder="Ej: El equipo se apagó inesperadamente..."
          @input="$event.target.style.height = 'auto'; $event.target.style.height = $event.target.scrollHeight + 'px'"
        ></textarea>
        
        <!-- Controles Inferiores del Input -->
        <div class="flex items-center justify-between px-3 pb-3">
          <!-- Opciones Avanzadas (Izquierda) -->
          <details class="group relative">
            <summary class="p-2 rounded-full hover:bg-slate-100 text-slate-400 cursor-pointer list-none transition-colors" title="Configuración de Red" style="list-style: none;">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
            </summary>
            <!-- Menú Flotante Configuración -->
            <div class="absolute bottom-full left-0 mb-3 w-72 bg-white rounded-xl shadow-lg border border-slate-100 p-4 z-20">
              <label class="block text-xs font-semibold text-slate-700 mb-1.5">URL del servidor</label>
              <input v-model="serverUrl" type="text" class="w-full px-3 py-2 border border-slate-200 bg-slate-50 rounded-lg text-xs outline-none focus:border-blue-500 focus:bg-white transition-colors" placeholder="http://192.168.1.100:8000" />
            </div>
          </details>

          <!-- Botón Principal (Derecha) -->
          <button 
            @click="copyCommand(generatedCommand)"
            :class="commandCopied ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-slate-900 hover:bg-slate-800'"
            class="flex items-center gap-2 px-5 py-2 rounded-xl text-white text-sm font-semibold transition-all shadow-sm"
          >
            <template v-if="commandCopied">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
              Copiado al portapapeles
            </template>
            <template v-else>
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
              Generar Comando
            </template>
          </button>
        </div>
      </div>

      <!-- Detalles Técnicos Ocultos (Discreto) -->
      <details class="group mt-8 w-full max-w-2xl">
        <summary class="text-xs font-medium text-slate-400 hover:text-slate-600 cursor-pointer flex items-center justify-center gap-1.5 transition-colors" style="list-style: none;">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
          Ver comandos generados
        </summary>
        <div class="mt-4 bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">PowerShell Remoto (Recomendado)</label>
            <pre class="bg-slate-900 text-emerald-400 text-xs px-4 py-3 rounded-lg overflow-x-auto font-mono whitespace-pre-wrap break-all">{{ generatedCommand }}</pre>
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">Ejecución Local (Alternativa)</label>
            <pre class="bg-slate-800 text-slate-300 text-xs px-4 py-3 rounded-lg overflow-x-auto font-mono whitespace-pre-wrap break-all">{{ simpleCommand }}</pre>
          </div>
        </div>
      </details>
    </div>

    <!-- ═══════════════════════ TAB: Monitor en Vivo ═══════════════════════ -->
    <div v-if="activeTab === 'live'" class="space-y-4">
      <!-- Lista de sesiones activas -->
      <div v-if="!selectedSession" class="space-y-4">
        <div v-if="activeSessions.length === 0" class="bg-white rounded-xl p-16 text-center shadow-sm border border-gray-100">
          <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
          <h3 class="text-lg font-semibold text-gray-900">No hay sesiones activas</h3>
          <p class="text-sm text-gray-500 mt-2">Cuando un técnico ejecute el script de diagnóstico en un equipo, aparecerá aquí.</p>
          <button @click="activeTab = 'command'" class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors">
            Generar comando de conexión
          </button>
        </div>
        
        <div v-for="session in activeSessions" :key="session.session_id" class="bg-white rounded-xl p-5 shadow-sm border border-gray-100 hover:border-blue-200 transition-colors cursor-pointer" @click="connectViewer(session.session_id)">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div class="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                <svg class="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
              </div>
              <div>
                <p class="text-sm font-semibold text-gray-900">{{ session.hostname }}</p>
                <p class="text-xs text-gray-500">Sesión {{ session.session_id }} · Paso {{ session.step_count }}/{{ session.max_steps }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <span class="relative flex h-3 w-3">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <span class="text-sm text-emerald-600 font-medium">En progreso</span>
              <svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
            </div>
          </div>
          <!-- Progress bar -->
          <div class="mt-3 w-full bg-gray-100 rounded-full h-1.5">
            <div class="bg-blue-500 h-1.5 rounded-full transition-all" :style="{ width: `${Math.round(session.step_count / session.max_steps * 100)}%` }"></div>
          </div>
        </div>
      </div>
      
      <!-- Vista de detalle de sesión -->
      <div v-else>
        <button @click="selectedSession = null; disconnectViewer(); selectedSessionEvents = []" class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
          Volver a sesiones
        </button>
        
        <div class="flex items-center gap-3 mb-4">
          <h2 class="text-lg font-semibold text-gray-900">Sesión {{ selectedSession }}</h2>
          <span v-if="isViewerConnected" class="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-50 rounded text-xs text-emerald-600 font-medium">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            En vivo
          </span>
          <span v-else class="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-500 font-medium">Historial</span>
        </div>
        
        <!-- Event Log -->
        <div ref="eventLogEl" class="bg-white rounded-xl p-6 max-h-[60vh] overflow-y-auto space-y-4 shadow-sm border border-gray-200">
          <div v-if="selectedSessionEvents.length === 0" class="text-center py-8">
            <p class="text-gray-500 text-sm">Esperando eventos...</p>
          </div>
          
          <div v-for="(event, idx) in selectedSessionEvents" :key="idx" class="flex gap-4 text-sm pb-4 border-b border-gray-50 last:border-0 last:pb-0">
            <span class="text-lg leading-none flex-shrink-0 mt-0.5">{{ getEventIcon(event.type) }}</span>
            <div class="flex-1 min-w-0">
              <!-- Thought del agente -->
              <template v-if="event.type === 'agent_thought'">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-[10px] font-bold tracking-wide uppercase">
                    🧠 Razonamiento
                  </span>
                  <p class="text-indigo-700 text-xs font-semibold">{{ event.hypothesis || `Paso ${event.step}` }}</p>
                </div>
                <p class="text-gray-600 text-sm whitespace-pre-wrap leading-relaxed">{{ event.thought }}</p>
              </template>
              
              <!-- Comando ejecutado -->
              <template v-else-if="event.type === 'execute_command'">
                <div class="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-50 border border-violet-200 text-violet-700 text-[10px] font-bold tracking-wide">
                    🔬 Hipótesis
                  </span>
                  <p class="text-blue-700 text-xs font-semibold">{{ event.hypothesis || 'Investigación general' }}</p>
                </div>
                <p class="text-gray-500 text-xs mb-1.5 italic">{{ event.purpose }}</p>
                <pre class="text-gray-800 text-xs bg-gray-900 text-emerald-300 px-3 py-2.5 rounded-lg overflow-x-auto font-mono leading-relaxed">$ {{ event.command }}</pre>
              </template>
              
              <!-- Resultado del comando -->
              <template v-else-if="event.type === 'command_result'">
                <div class="flex items-center gap-2 mb-1.5">
                  <p class="text-xs font-semibold" :class="event.exit_code === 0 ? 'text-emerald-700' : 'text-red-600'">
                    {{ event.exit_code === 0 ? '✅ Ejecutado' : '❌ Error' }} (exit code: {{ event.exit_code }})
                  </p>
                  <span v-if="event.stderr" class="inline-flex items-center px-1.5 py-0.5 rounded bg-red-100 text-red-600 text-[10px] font-bold">
                    STDERR
                  </span>
                </div>
                <pre v-if="event.stdout" class="text-gray-600 text-xs bg-gray-50 border border-gray-100 px-3 py-2 rounded-lg overflow-x-auto max-h-40 overflow-y-auto font-mono whitespace-pre-wrap">{{ event.stdout }}</pre>
                <pre v-if="event.stderr" class="text-red-700 text-xs bg-red-50 border border-red-100 px-3 py-2 rounded-lg mt-1 overflow-x-auto font-mono">{{ event.stderr }}</pre>
              </template>
              
              <!-- Búsqueda web -->
              <template v-else-if="event.type === 'search_web'">
                <p class="text-blue-600 text-sm font-medium">Buscando: <em class="text-gray-600 font-normal">"{{ event.query }}"</em></p>
              </template>
              
              <!-- Sesión iniciada -->
              <template v-else-if="event.type === 'session_started'">
                <p class="text-emerald-700 text-sm font-semibold">Equipo conectado: <span class="text-gray-900">{{ event.machine_info?.hostname }}</span> ({{ event.machine_info?.ip }})</p>
                <p class="text-gray-500 text-xs mt-1">OS: {{ event.machine_info?.os }} · Uptime: {{ event.machine_info?.uptime }}</p>
                <p class="text-gray-600 text-sm mt-1 bg-gray-50 px-3 py-2 rounded border border-gray-100">Problema: {{ event.machine_info?.issue }}</p>
              </template>
              
              <!-- Diagnóstico completo -->
              <template v-else-if="event.type === 'diagnosis_complete'">
                <div class="bg-gray-50 rounded-xl p-5 mt-2 border border-gray-200 shadow-sm">
                  <div class="flex items-center gap-2 mb-4 pb-3 border-b border-gray-200">
                    <span :class="['px-2.5 py-1 rounded-md text-xs font-bold shadow-sm', getSeverityConfig(event.report?.severity).bg, getSeverityConfig(event.report?.severity).text]">
                      {{ getSeverityConfig(event.report?.severity).label }}
                    </span>
                    <span class="text-gray-900 text-base font-semibold">Diagnóstico Finalizado</span>
                  </div>
                  <p class="text-gray-900 text-sm font-semibold mb-2">{{ event.report?.root_cause }}</p>
                  <p class="text-gray-600 text-sm mb-4 leading-relaxed">{{ event.report?.evidence_summary }}</p>
                  <div v-if="event.report?.recommendations" class="space-y-2 mt-4 bg-white p-4 rounded-lg border border-gray-100">
                    <p class="text-gray-900 text-sm font-semibold">Recomendaciones sugeridas:</p>
                    <ul class="list-disc pl-5 space-y-1">
                      <li v-for="(rec, i) in event.report.recommendations" :key="i" class="text-gray-700 text-sm">{{ rec }}</li>
                    </ul>
                  </div>
                  <p v-if="event.report?.additional_notes" class="text-gray-500 text-xs mt-3 italic">Nota: {{ event.report.additional_notes }}</p>
                </div>
              </template>
              
              <!-- Comando bloqueado -->
              <template v-else-if="event.type === 'command_blocked'">
                <p class="text-red-600 text-sm font-medium">Bloqueado por seguridad: <code class="bg-red-50 px-1 rounded text-red-700 text-xs">{{ event.command }}</code></p>
              </template>
              
              <!-- Otros eventos -->
              <template v-else>
                <p class="text-gray-600 text-sm">{{ event.message || event.type }}</p>
              </template>
              
              <!-- Timestamp -->
              <p v-if="event.timestamp" class="text-gray-400 text-[10px] mt-1 font-medium">{{ formatTime(event.timestamp) }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════ TAB: Historial ═══════════════════════ -->
    <div v-if="activeTab === 'history'">
      <div v-if="completedSessions.length === 0" class="bg-white rounded-xl p-16 text-center shadow-sm border border-gray-100">
        <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <h3 class="text-lg font-semibold text-gray-900">Sin historial de diagnósticos</h3>
        <p class="text-sm text-gray-500 mt-2">Las sesiones completadas aparecerán aquí.</p>
      </div>
      
      <div v-else class="space-y-2">
        <div 
          v-for="session in completedSessions" :key="session.session_id"
          @click="viewCompletedSession(session.session_id)"
          class="bg-white rounded-xl p-4 shadow-sm border border-gray-100 hover:border-gray-200 cursor-pointer transition-colors"
        >
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-4">
              <div :class="['w-10 h-10 rounded-lg flex items-center justify-center', session.final_report ? getSeverityConfig(session.final_report.severity).bg : 'bg-gray-100']">
                <span class="text-lg">{{ session.is_complete ? '✅' : '⚠️' }}</span>
              </div>
              <div>
                <p class="text-sm font-semibold text-gray-900">{{ session.hostname }}</p>
                <p class="text-xs text-gray-500">{{ session.issue }}</p>
              </div>
            </div>
            <div class="flex items-center gap-4 text-right">
              <div>
                <span v-if="session.final_report" :class="['px-2 py-0.5 rounded text-xs font-bold', getSeverityConfig(session.final_report.severity).bg, getSeverityConfig(session.final_report.severity).text]">
                  {{ getSeverityConfig(session.final_report.severity).label }}
                </span>
                <span v-else class="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-500 font-medium">Incompleto</span>
                <p class="text-xs text-gray-400 mt-1">{{ formatDate(session.completed_at) }}</p>
              </div>
              <svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
            </div>
          </div>
          <p v-if="session.final_report" class="text-xs text-gray-500 mt-2 truncate">{{ session.final_report.root_cause }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Scrollbar styling para el event log */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.1);
  border-radius: 3px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(0,0,0,0.2);
}
</style>
