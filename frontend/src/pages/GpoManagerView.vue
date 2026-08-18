<script setup>
import { ref } from 'vue'
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

async function authFetch(url, opts = {}) {
  const token = localStorage.getItem('access_token')
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json', ...(opts.headers || {}) } })
}

// Variables Reactivas
const aiPrompt = ref('')
const generatedScript = ref('')
const isGenerating = ref(false)
const isExecuting = ref(false)
const executionResult = ref(null)

// Templates State
const templates = ref([
  {
    id: 'wallpaper',
    title: 'Fondo de Pantalla Corporativo',
    icon: '🖼️',
    params: { path: '\\\\Servidor\\Share\\fondo.jpg' }
  },
  {
    id: 'network_drive',
    title: 'Mapear Unidad de Red',
    icon: '🗄️',
    params: { letter: 'Z:', path: '\\\\Servidor\\Share' }
  },
  {
    id: 'screen_lock',
    title: 'Bloqueo de Pantalla Automático',
    icon: '🔒',
    params: { minutes: '15' }
  },
  {
    id: 'printer',
    title: 'Desplegar Impresora',
    icon: '🖨️',
    params: { path: '\\\\PrintServer\\Impresora1' }
  }
])

const generateTemplate = async (template) => {
  isGenerating.value = true
  executionResult.value = null
  try {
    const response = await authFetch(`${API_BASE}/gpo/generate/template`, {
      method: 'POST',
      body: JSON.stringify({
        template_type: template.id,
        params: template.params
      })
    })
    const data = await response.json()
    generatedScript.value = data.script
  } catch (error) {
    console.error('Error al generar template:', error)
    alert('Error al generar el script de la plantilla.')
  } finally {
    isGenerating.value = false
  }
}

const generateAi = async () => {
  if (!aiPrompt.value.trim()) return
  
  isGenerating.value = true
  executionResult.value = null
  try {
    const response = await authFetch(`${API_BASE}/gpo/generate/ai`, {
      method: 'POST',
      body: JSON.stringify({
        prompt: aiPrompt.value
      })
    })
    const data = await response.json()
    generatedScript.value = data.script
    aiPrompt.value = ''
  } catch (error) {
    console.error('Error en generación por IA:', error)
    alert('Error al contactar con la IA para generar el GPO.')
  } finally {
    isGenerating.value = false
  }
}

const executeGpo = async () => {
  if (!generatedScript.value) return
  
  isExecuting.value = true
  executionResult.value = null
  
  try {
    const response = await authFetch(`${API_BASE}/gpo/execute`, {
      method: 'POST',
      body: JSON.stringify({
        script: generatedScript.value
      })
    })
    const data = await response.json()
    
    executionResult.value = {
      success: response.ok,
      stdout: data.stdout,
      stderr: data.stderr,
      error: !response.ok ? data.detail || 'Error desconocido' : null
    }
  } catch (error) {
    console.error('Error al ejecutar GPO:', error)
    executionResult.value = {
      success: false,
      error: error.message
    }
  } finally {
    isExecuting.value = false
  }
}
</script>

<template>
  <div class="h-full bg-slate-50 flex flex-col p-8 overflow-y-auto w-full">
    
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-slate-800 tracking-tight">Gestor de Políticas (GPO) con IA</h1>
      <p class="text-sm text-slate-500 mt-1">
        Despliegue rápido e inteligente de directivas de grupo en el Directorio Activo.
      </p>
    </div>

    <!-- Quick Actions (Templates) -->
    <div class="mb-10">
      <h2 class="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wider">Acciones Rápidas (Plantillas)</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        
        <!-- Wallpaper -->
        <div class="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <span class="text-2xl">{{ templates[0].icon }}</span>
            <h3 class="font-medium text-slate-800 text-sm">{{ templates[0].title }}</h3>
          </div>
          <div class="space-y-3">
            <div>
              <label class="text-[11px] font-medium text-slate-500 mb-1 block">Ruta de la Imagen (UNC)</label>
              <input v-model="templates[0].params.path" type="text" class="w-full text-xs rounded-md border-slate-200 focus:ring-primary focus:border-primary shadow-sm" placeholder="\\Servidor\Share\img.jpg">
            </div>
            <button @click="generateTemplate(templates[0])" :disabled="isGenerating" class="w-full text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 rounded-md font-medium transition-colors">
              Generar Script
            </button>
          </div>
        </div>

        <!-- Network Drive -->
        <div class="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <span class="text-2xl">{{ templates[1].icon }}</span>
            <h3 class="font-medium text-slate-800 text-sm">{{ templates[1].title }}</h3>
          </div>
          <div class="space-y-3">
            <div class="flex gap-2">
              <div class="w-1/3">
                <label class="text-[11px] font-medium text-slate-500 mb-1 block">Letra</label>
                <input v-model="templates[1].params.letter" type="text" class="w-full text-xs rounded-md border-slate-200 focus:ring-primary focus:border-primary shadow-sm">
              </div>
              <div class="w-2/3">
                <label class="text-[11px] font-medium text-slate-500 mb-1 block">Ruta (UNC)</label>
                <input v-model="templates[1].params.path" type="text" class="w-full text-xs rounded-md border-slate-200 focus:ring-primary focus:border-primary shadow-sm">
              </div>
            </div>
            <button @click="generateTemplate(templates[1])" :disabled="isGenerating" class="w-full text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 rounded-md font-medium transition-colors">
              Generar Script
            </button>
          </div>
        </div>

        <!-- Screen Lock -->
        <div class="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <span class="text-2xl">{{ templates[2].icon }}</span>
            <h3 class="font-medium text-slate-800 text-sm">{{ templates[2].title }}</h3>
          </div>
          <div class="space-y-3">
            <div>
              <label class="text-[11px] font-medium text-slate-500 mb-1 block">Minutos de inactividad</label>
              <input v-model="templates[2].params.minutes" type="number" class="w-full text-xs rounded-md border-slate-200 focus:ring-primary focus:border-primary shadow-sm">
            </div>
            <button @click="generateTemplate(templates[2])" :disabled="isGenerating" class="w-full text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 rounded-md font-medium transition-colors">
              Generar Script
            </button>
          </div>
        </div>

        <!-- Printer -->
        <div class="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <span class="text-2xl">{{ templates[3].icon }}</span>
            <h3 class="font-medium text-slate-800 text-sm">{{ templates[3].title }}</h3>
          </div>
          <div class="space-y-3">
            <div>
              <label class="text-[11px] font-medium text-slate-500 mb-1 block">Ruta de Impresora</label>
              <input v-model="templates[3].params.path" type="text" class="w-full text-xs rounded-md border-slate-200 focus:ring-primary focus:border-primary shadow-sm">
            </div>
            <button @click="generateTemplate(templates[3])" :disabled="isGenerating" class="w-full text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 py-2 rounded-md font-medium transition-colors">
              Generar Script
            </button>
          </div>
        </div>

      </div>
    </div>

    <!-- AI Panel -->
    <div class="mb-10 flex gap-6">
      <div class="w-1/2 flex flex-col">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wider flex items-center gap-2">
          <svg class="w-4 h-4 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          GPO a Medida (Con IA)
        </h2>
        <div class="bg-white rounded-xl border border-slate-200/60 p-5 shadow-sm flex flex-col h-full">
          <p class="text-xs text-slate-500 mb-4">Describe la política que necesitas implementar en lenguaje natural. El asistente generará el script de PowerShell exacto.</p>
          <textarea 
            v-model="aiPrompt" 
            rows="5" 
            class="w-full text-sm rounded-lg border-slate-200 focus:ring-primary focus:border-primary shadow-sm resize-none mb-4" 
            placeholder="Ej: Crea una política que bloquee el acceso a los puertos USB para todos los usuarios."
          ></textarea>
          <div class="mt-auto flex justify-end">
            <button @click="generateAi" :disabled="isGenerating || !aiPrompt.trim()" class="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50">
              <svg v-if="isGenerating" class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              {{ isGenerating ? 'Generando...' : 'Generar con IA' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Preview and Execute -->
      <div class="w-1/2 flex flex-col">
        <h2 class="text-sm font-semibold text-slate-700 mb-4 uppercase tracking-wider">Vista Previa del Script</h2>
        <div class="bg-slate-900 rounded-xl border border-slate-800 p-4 shadow-sm flex flex-col h-full overflow-hidden relative group">
          
          <div v-if="!generatedScript" class="flex-1 flex items-center justify-center text-slate-500 text-sm">
            El script generado aparecerá aquí para tu revisión.
          </div>
          <div v-else class="flex-1 overflow-auto bg-slate-900 text-slate-300 font-mono text-xs rounded p-2">
            <pre><code>{{ generatedScript }}</code></pre>
          </div>

          <!-- Execution status overlay/messages -->
          <div v-if="executionResult" class="mt-4 p-3 rounded-lg text-xs" :class="executionResult.success ? 'bg-emerald-900/30 border border-emerald-800/50 text-emerald-400' : 'bg-red-900/30 border border-red-800/50 text-red-400'">
            <div class="font-bold mb-1">{{ executionResult.success ? 'Ejecución Exitosa' : 'Error en Ejecución' }}</div>
            <pre class="whitespace-pre-wrap font-sans text-[11px] opacity-80">{{ executionResult.stdout || executionResult.error || executionResult.stderr }}</pre>
          </div>

          <div class="mt-4 flex justify-end shrink-0 pt-4 border-t border-slate-800">
            <button @click="executeGpo" :disabled="!generatedScript || isExecuting" class="inline-flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition-colors shadow-sm disabled:opacity-50">
              <svg v-if="isExecuting" class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
              {{ isExecuting ? 'Ejecutando en el DC...' : 'Aprobar y Ejecutar' }}
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Scrollbar customizado para el pre */
pre::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
pre::-webkit-scrollbar-track {
  background: transparent;
}
pre::-webkit-scrollbar-thumb {
  background-color: #334155;
  border-radius: 4px;
}
</style>
