<script setup>
import { ref, computed } from 'vue'
import BaseModal from './common/BaseModal.vue'

const emit = defineEmits(['close'])

const sourceUser = ref('')
const targetUser = ref('')

const isAnalyzing = ref(false)
const isExecuting = ref(false)
const analyzeError = ref('')
const executeError = ref('')
const executeSuccess = ref(false)
const results = ref([])

const delta = ref(null)

const API_BASE = '/api/v1'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('access_token')
  opts.headers = { ...(opts.headers || {}), 'Authorization': `Bearer ${token}` }
  return fetch(url, opts)
}

const canAnalyze = computed(() => sourceUser.value.trim().length > 0 && targetUser.value.trim().length > 0)

const analyzeDelta = async () => {
  if (!canAnalyze.value) return
  isAnalyzing.value = true
  analyzeError.value = ''
  delta.value = null
  executeError.value = ''
  executeSuccess.value = false
  
  try {
    const res = await authFetch(`${API_BASE}/fileserver/clone-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_user: sourceUser.value.trim(),
        target_user: targetUser.value.trim()
      })
    })
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error analizando permisos')
    }
    
    const data = await res.json()
    delta.value = data.delta
  } catch (err) {
    analyzeError.value = err.message
  } finally {
    isAnalyzing.value = false
  }
}

const executeClone = async () => {
  if (!delta.value) return
  
  isExecuting.value = true
  executeError.value = ''
  
  try {
    const res = await authFetch(`${API_BASE}/fileserver/clone-execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_user: sourceUser.value.trim(),
        target_user: targetUser.value.trim(),
        delta: delta.value
      })
    })
    
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error ejecutando clonación')
    }
    
    const data = await res.json()
    executeSuccess.value = true
    results.value = data.results || []
  } catch (err) {
    executeError.value = err.message
  } finally {
    isExecuting.value = false
  }
}

const totalChanges = computed(() => {
  if (!delta.value) return 0
  return (delta.value.groups_to_add?.length || 0) + (delta.value.folders_to_add?.length || 0)
})

</script>

<template>
  <BaseModal :show="true" title="Clonar Permisos (Usuario Espejo)" @close="emit('close')">
    <template #body>
      <div class="space-y-6 px-4 pb-4">
        <div class="bg-indigo-50 border-l-4 border-indigo-500 p-4 rounded-md">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-indigo-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm text-indigo-700">
                Esta herramienta calcula los permisos que tiene el <strong>Usuario Origen</strong> y se los aplica al <strong>Usuario Destino</strong>. No se eliminarán permisos preexistentes.
              </p>
            </div>
          </div>
        </div>

        <!-- Formularios de búsqueda -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">Usuario Origen (Plantilla)</label>
            <input v-model="sourceUser" type="text" placeholder="Ej. j.perez" class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" :disabled="isAnalyzing || isExecuting">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">Usuario Destino (Nuevo)</label>
            <input v-model="targetUser" type="text" placeholder="Ej. m.lopez" class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" :disabled="isAnalyzing || isExecuting">
          </div>
        </div>

        <div class="flex justify-center mt-4">
          <button @click="analyzeDelta" :disabled="!canAnalyze || isAnalyzing || isExecuting" class="bg-slate-800 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-slate-700 disabled:opacity-50 transition-colors flex items-center gap-2">
            <svg v-if="isAnalyzing" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
            </svg>
            Analizar y Comparar
          </button>
        </div>

        <!-- Errores -->
        <div v-if="analyzeError" class="bg-red-50 text-red-600 p-3 rounded-md text-sm border border-red-100">
          {{ analyzeError }}
        </div>
        <div v-if="executeError" class="bg-red-50 text-red-600 p-3 rounded-md text-sm border border-red-100">
          {{ executeError }}
        </div>
        <div v-if="executeSuccess" class="bg-emerald-50 text-emerald-700 p-4 rounded-md text-sm border border-emerald-100">
          <p class="font-bold mb-2 flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
            Clonación completada con éxito.
          </p>
          <ul class="list-disc pl-5 space-y-1 mt-2 text-xs">
            <li v-for="(r, i) in results" :key="i">{{ r }}</li>
          </ul>
        </div>

        <!-- Vista Previa del Delta -->
        <div v-if="delta && !executeSuccess" class="mt-6 border-t border-slate-200 pt-6">
          <h3 class="text-sm font-semibold text-slate-900 mb-2">
            Permisos a clonar (Nuevos accesos para {{ targetUser }})
          </h3>
          
          <div v-if="totalChanges === 0" class="text-center py-6 bg-slate-50 rounded-lg border border-slate-200">
            <p class="text-sm text-slate-500 font-medium">El destino ya cuenta con los mismos accesos (o superiores).</p>
            <p class="text-xs text-slate-400 mt-1">No se detectaron diferencias para clonar.</p>
          </div>

          <div v-else class="space-y-4">
            <!-- Grupos AD -->
            <div v-if="delta.groups_to_add?.length > 0">
              <h4 class="text-xs font-medium text-slate-500 uppercase mb-2">Membresía de Grupos (AD)</h4>
              <ul class="bg-white border border-slate-200 rounded-md divide-y divide-slate-100">
                <li v-for="grp in delta.groups_to_add" :key="grp" class="p-3 flex items-center gap-3 text-sm text-slate-700">
                  <svg class="w-5 h-5 text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                  Se agregará a: <span class="font-semibold">{{ grp }}</span>
                </li>
              </ul>
            </div>

            <!-- Carpetas Directas -->
            <div v-if="delta.folders_to_add?.length > 0">
              <h4 class="text-xs font-medium text-slate-500 uppercase mb-2">Permisos Explícitos en Carpetas</h4>
              <ul class="bg-white border border-slate-200 rounded-md divide-y divide-slate-100">
                <li v-for="(fld, i) in delta.folders_to_add" :key="i" class="p-3 flex items-center justify-between text-sm text-slate-700">
                  <div class="flex items-center gap-3">
                    <svg class="w-5 h-5 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                    <span>{{ fld.path }}</span>
                  </div>
                  <span class="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
                    {{ fld.access }}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </template>
    
    <template #footer>
      <div class="flex justify-end gap-3 px-4 pb-4">
        <button @click="emit('close')" class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500" :disabled="isExecuting">
          {{ executeSuccess ? 'Cerrar' : 'Cancelar' }}
        </button>
        <button 
          v-if="!executeSuccess"
          @click="executeClone" 
          :disabled="!delta || totalChanges === 0 || isExecuting || isAnalyzing" 
          class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center gap-2"
        >
          <svg v-if="isExecuting" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Ejecutar Clonación
        </button>
      </div>
    </template>
  </BaseModal>
</template>
