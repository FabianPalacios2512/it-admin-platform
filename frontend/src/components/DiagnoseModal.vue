<script setup>
import { ref } from 'vue'
import BaseModal from './common/BaseModal.vue'

const emit = defineEmits(['close'])

const username = ref('')
const isLoading = ref(false)
const result = ref(null)
const errorMsg = ref(null)

const API_BASE = '/api/v1'

function authFetch(url, opts = {}) {
  const token = localStorage.getItem('access_token')
  opts.headers = { ...(opts.headers || {}), 'Authorization': `Bearer ${token}` }
  return fetch(url, opts)
}

async function runDiagnosis() {
  if (!username.value.trim()) return
  
  isLoading.value = true
  result.value = null
  errorMsg.value = null
  
  try {
    const res = await authFetch(`${API_BASE}/accounts/diagnose/${encodeURIComponent(username.value.trim())}`)
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Error en el servidor')
    }
    result.value = await res.json()
  } catch (err) {
    errorMsg.value = err.message
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <BaseModal :show="true" title="Diagnóstico Express (Helpdesk Triage)" @close="emit('close')">
    <template #body>
      <div class="space-y-4 px-4 pb-4">
        <p class="text-sm text-slate-500">
          Ingresa el nombre de usuario (sAMAccountName) para verificar instantáneamente su estado en Active Directory y Microsoft Entra ID.
        </p>
      
      <div class="flex gap-2">
        <input 
          v-model="username"
          @keyup.enter="runDiagnosis"
          type="text" 
          placeholder="Ej: f.paternina" 
          class="flex-1 rounded-md border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border outline-none"
          :disabled="isLoading"
        />
        <button 
          @click="runDiagnosis"
          :disabled="isLoading || !username"
          class="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
        >
          <span v-if="isLoading" class="mr-2 h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
          Diagnosticar
        </button>
      </div>

      <div v-if="errorMsg" class="rounded-md bg-red-50 p-4 mt-4">
        <div class="flex">
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">Error en el diagnóstico</h3>
            <div class="mt-2 text-sm text-red-700">
              <p>{{ errorMsg }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="result" class="mt-6 space-y-6">
        
        <!-- Active Directory Status -->
        <div class="rounded-lg border border-slate-200 overflow-hidden">
          <div class="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
            <h3 class="text-sm font-semibold text-slate-700">Active Directory (Local)</h3>
            <span v-if="result.ad_status === 'ok'" class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
              OK
            </span>
            <span v-else class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
              Alerta
            </span>
          </div>
          <div class="p-4 bg-white">
            <div v-if="result.ad_issues && result.ad_issues.length > 0">
              <ul class="list-disc pl-5 space-y-1">
                <li v-for="issue in result.ad_issues" :key="issue" class="text-sm text-red-600 font-medium">
                  {{ issue }}
                </li>
              </ul>
            </div>
            <div v-else class="text-sm text-slate-500 flex items-center">
              <svg class="h-4 w-4 text-emerald-500 mr-2" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              No se detectaron problemas de bloqueo ni deshabilitación.
            </div>
          </div>
        </div>

        <!-- Microsoft Entra ID Status -->
        <div class="rounded-lg border border-slate-200 overflow-hidden">
          <div class="bg-slate-50 px-4 py-3 border-b border-slate-200 flex justify-between items-center">
            <h3 class="text-sm font-semibold text-slate-700">Microsoft Entra ID (Nube)</h3>
            <span v-if="result.entra_status === 'ok'" class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
              OK
            </span>
            <span v-else class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
              Alerta
            </span>
          </div>
          <div class="p-4 bg-white">
            <div v-if="result.entra_issues && result.entra_issues.length > 0">
              <ul class="list-disc pl-5 space-y-1">
                <li v-for="issue in result.entra_issues" :key="issue" class="text-sm text-red-600 font-medium">
                  {{ issue }}
                </li>
              </ul>
            </div>
            <div v-else class="text-sm text-slate-500 flex items-center">
              <svg class="h-4 w-4 text-emerald-500 mr-2" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Cuenta habilitada y sincronizada correctamente.
            </div>

            <div class="mt-4 pt-4 border-t border-slate-100">
              <h4 class="text-xs font-medium text-slate-500 uppercase tracking-wider mb-2">Licencias Asignadas</h4>
              <div v-if="result.licenses && result.licenses.length > 0" class="flex flex-wrap gap-2">
                <span v-for="lic in result.licenses" :key="lic" class="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
                  {{ lic }}
                </span>
              </div>
              <div v-else class="text-sm text-slate-500">
                Ninguna licencia asignada.
              </div>
            </div>
          </div>
        </div>
        
      </div>
      </div>
    </template>
    <template #footer>
      <button @click="emit('close')" class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50">Cerrar</button>
    </template>
  </BaseModal>
</template>
