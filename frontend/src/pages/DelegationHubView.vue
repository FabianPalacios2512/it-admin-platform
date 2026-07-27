<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6 fade-in flex flex-col h-[calc(100vh-64px)]">
    <!-- Header -->
    <div class="mb-5 shrink-0">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600 font-medium">Delegación de Activos</span>
      </div>
      <div class="flex justify-between items-end">
        <div>
          <h2 class="text-2xl font-semibold text-slate-900 tracking-tight flex items-center gap-2">
            <svg class="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"></path>
            </svg>
            Buzones Compartidos & Delegaciones
          </h2>
          <p class="text-sm text-slate-500 mt-1">Supervisa los buzones compartidos y ejecuta procesos de offboarding.</p>
        </div>
        <button v-if="!showWizard" @click="showWizard = true" class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"></path></svg>
          Nuevo Offboarding / Delegación
        </button>
      </div>
    </div>

    <!-- Dashboard View -->
    <div v-if="!showWizard" class="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col animate-fade-in">
      
      <!-- Toolbar -->
      <div class="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
        <div class="relative">
          <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          <input type="text" v-model="searchQuery" placeholder="Buscar buzón o delegado..." class="pl-9 pr-4 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 w-64" />
        </div>
        <button @click="fetchSharedMailboxes" class="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
          <svg :class="['w-4 h-4', isLoading ? 'animate-spin' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          Sincronizar Exchange
        </button>
      </div>

      <!-- Global Error Banner -->
      <div v-if="globalError" class="bg-red-50 border-l-4 border-red-500 p-4 mx-4 mt-4 rounded-r-lg flex justify-between items-start animate-fade-in">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 text-red-600 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
          <div>
            <h4 class="text-sm font-bold text-red-800">No se pudo abrir el OneDrive</h4>
            <p class="text-xs text-red-700 mt-1">{{ globalError }}</p>
          </div>
        </div>
        <button @click="globalError = ''" class="text-red-500 hover:text-red-700">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>

      <!-- Table -->
      <div class="flex-1 overflow-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-slate-50 border-y border-slate-100 text-[11px] uppercase tracking-wider text-slate-500 font-semibold sticky top-0 z-10 shadow-sm">
              <th class="px-6 py-3">Buzón Compartido</th>
              <th class="px-6 py-3">Nombre</th>
              <th class="px-6 py-3">Delegados (Con Acceso)</th>
              <th class="px-6 py-3 text-right">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="isLoading" v-for="i in 5" :key="i" class="animate-pulse">
              <td class="px-6 py-4"><div class="h-4 bg-slate-200 rounded w-48"></div></td>
              <td class="px-6 py-4"><div class="h-4 bg-slate-200 rounded w-32"></div></td>
              <td class="px-6 py-4"><div class="h-4 bg-slate-200 rounded w-64"></div></td>
              <td class="px-6 py-4"><div class="h-8 bg-slate-200 rounded w-28 ml-auto"></div></td>
            </tr>
            <tr v-if="!isLoading && filteredMailboxes.length === 0" class="hover:bg-slate-50/50">
              <td colspan="4" class="px-6 py-12 text-center text-slate-500 text-sm">
                No se encontraron buzones compartidos. Usa el botón "Sincronizar Exchange" para actualizar la lista.
              </td>
            </tr>
            <tr v-for="mbx in filteredMailboxes" :key="mbx.Mailbox" class="hover:bg-slate-50/80 transition-colors group">
              <td class="px-6 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-xs">
                    {{ mbx.DisplayName ? mbx.DisplayName.charAt(0) : 'B' }}
                  </div>
                  <div>
                    <p class="text-sm font-semibold text-slate-800">{{ mbx.Mailbox }}</p>
                    <p class="text-[11px] text-slate-400">SharedMailbox</p>
                  </div>
                </div>
              </td>
              <td class="px-6 py-3.5 text-sm text-slate-600">{{ mbx.DisplayName }}</td>
              <td class="px-6 py-3.5">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="del in (mbx.Delegates ? mbx.Delegates.split(',') : [])" :key="del" class="px-2 py-0.5 bg-slate-100 text-slate-600 border border-slate-200 rounded-md text-[11px] font-medium whitespace-nowrap">
                    {{ del.trim() }}
                  </span>
                  <span v-if="!mbx.Delegates" class="text-xs text-slate-400 italic">Sin delegados locales</span>
                </div>
              </td>
              <td class="px-6 py-3.5 text-right flex justify-end gap-2">
                <a :href="`https://outlook.office.com/mail/${mbx.Mailbox}/`" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-50 hover:text-blue-600 transition-colors shadow-sm" title="Abrir Buzón">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                  Buzón
                </a>
                <button @click="openOneDrive(mbx.Mailbox)" class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-50 hover:text-sky-600 transition-colors shadow-sm" title="Abrir OneDrive">
                  <svg v-if="loadingOneDrive === mbx.Mailbox" class="animate-spin h-3.5 w-3.5 text-sky-600" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"></path></svg>
                  OneDrive
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Wizard View (Offboarding) -->
    <div v-if="showWizard" class="flex-1 flex flex-col animate-slide-in">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-bold text-slate-800">Asistente de Offboarding y Delegación</h3>
        <button @click="showWizard = false" class="text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors">Volver al Dashboard</button>
      </div>

      <!-- Stepper Navigation -->
      <div class="mb-6">
        <div class="flex items-center justify-between relative">
          <div class="absolute left-0 top-1/2 -translate-y-1/2 w-full h-0.5 bg-slate-200 z-0"></div>
          <div class="absolute left-0 top-1/2 -translate-y-1/2 h-0.5 bg-blue-600 z-0 transition-all duration-300" :style="{ width: progressWidth }"></div>
          
          <div v-for="(step, index) in steps" :key="index" class="relative z-10 flex flex-col items-center">
            <div :class="['w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm border-2 transition-colors duration-300', currentStep >= index ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-slate-300 text-slate-400']">
              {{ index + 1 }}
            </div>
            <span :class="['absolute top-11 text-[11px] font-semibold whitespace-nowrap transition-colors duration-300', currentStep >= index ? 'text-blue-700' : 'text-slate-400']">{{ step.title }}</span>
          </div>
        </div>
      </div>

      <!-- Step Content -->
      <div class="flex-1 overflow-y-auto bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <!-- Step 1: Origen y Saneamiento -->
        <div v-if="currentStep === 0" class="animate-fade-in">
          <h3 class="text-lg font-bold text-slate-800 mb-4">Paso 1: Buzón Origen y Sanitización</h3>
          <div class="mb-6">
            <label class="block text-[12px] font-bold text-slate-600 uppercase tracking-wider mb-2">Buzón a Delegar (UPN)</label>
            <input type="email" v-model="payload.source_upn" placeholder="ej. ejimenez@empresa.com" class="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div class="space-y-4 border border-slate-100 rounded-lg p-4 bg-slate-50/50">
            <label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" v-model="payload.convert_shared" class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500" />
              <div>
                <p class="text-sm font-semibold text-slate-700">Convertir a Buzón Compartido</p>
                <p class="text-[11px] text-slate-500">Transforma el buzón de usuario a compartido (liberando costos).</p>
              </div>
            </label>
            <label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" v-model="payload.remove_license" class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500" />
              <div>
                <p class="text-sm font-semibold text-slate-700">Remover Licencias de Microsoft 365</p>
                <p class="text-[11px] text-slate-500">Desasigna todas las licencias (M365 E3, E5, etc.) inmediatamente.</p>
              </div>
            </label>
            <label class="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" v-model="payload.hide_gal" class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500" />
              <div>
                <p class="text-sm font-semibold text-slate-700">Ocultar de la GAL (Global Address List)</p>
                <p class="text-[11px] text-slate-500">Oculta el buzón de la libreta de direcciones para que nadie envíe correos por error.</p>
              </div>
            </label>
          </div>
        </div>

        <!-- Step 2: Delegación Granular -->
        <div v-if="currentStep === 1" class="animate-fade-in">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-bold text-slate-800">Paso 2: Delegación (Time-bound Access)</h3>
            <button @click="addTarget" class="px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 font-semibold text-xs rounded-lg transition-colors border border-blue-200">
              + Añadir Usuario
            </button>
          </div>
          <div v-if="payload.targets.length === 0" class="text-center py-8 text-slate-400 text-sm italic">
            No hay usuarios destino. Haz clic en "+ Añadir Usuario" para otorgar acceso.
          </div>
          <div class="space-y-4">
            <div v-for="(target, idx) in payload.targets" :key="idx" class="flex flex-wrap md:flex-nowrap items-end gap-3 p-4 bg-slate-50 border border-slate-200 rounded-lg relative group">
              <div class="flex-1 min-w-[200px]">
                <label class="block text-[11px] font-bold text-slate-500 uppercase mb-1">Usuario Destino (UPN)</label>
                <input type="email" v-model="target.upn" placeholder="jdoe@empresa.com" class="w-full px-3 py-1.5 text-sm bg-white border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 outline-none" />
              </div>
              <div class="w-36">
                <label class="block text-[11px] font-bold text-slate-500 uppercase mb-1">Permiso</label>
                <select v-model="target.permission" class="w-full px-3 py-1.5 text-sm bg-white border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 outline-none">
                  <option value="FullAccess">Full Access</option>
                  <option value="SendAs">Send As</option>
                </select>
              </div>
              <div class="w-48">
                <label class="block text-[11px] font-bold text-slate-500 uppercase mb-1">Caducidad (Opcional)</label>
                <input type="datetime-local" v-model="target.expiration" class="w-full px-3 py-1.5 text-sm bg-white border border-slate-300 rounded focus:ring-1 focus:ring-blue-500 outline-none text-slate-600" />
              </div>
              <button @click="removeTarget(idx)" class="px-2 py-1.5 text-red-500 hover:bg-red-50 rounded transition-colors self-end mb-0.5">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Step 3: Retención de Archivos -->
        <div v-if="currentStep === 2" class="animate-fade-in">
          <h3 class="text-lg font-bold text-slate-800 mb-4">Paso 3: Retención de OneDrive / SharePoint</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <label :class="['border rounded-lg p-4 cursor-pointer transition-all', payload.retention_action === 'none' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300']">
              <div class="flex items-center gap-2 mb-2">
                <input type="radio" value="none" v-model="payload.retention_action" class="w-4 h-4 text-blue-600" />
                <span class="font-bold text-sm text-slate-800">No accionar</span>
              </div>
              <p class="text-[11px] text-slate-500 pl-6">El OneDrive seguirá intacto hasta que se venza su periodo de retención normal.</p>
            </label>
            <label :class="['border rounded-lg p-4 cursor-pointer transition-all', payload.retention_action === 'transfer' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300']">
              <div class="flex items-center gap-2 mb-2">
                <input type="radio" value="transfer" v-model="payload.retention_action" class="w-4 h-4 text-blue-600" />
                <span class="font-bold text-sm text-slate-800">Transferir Propiedad</span>
              </div>
              <p class="text-[11px] text-slate-500 pl-6 mb-3">Transfiere todo el contenido del OneDrive a otro usuario administrador o jefe directo.</p>
              <input v-if="payload.retention_action === 'transfer'" type="email" v-model="payload.retention_target" placeholder="upn.destino@empresa.com" class="ml-6 w-[calc(100%-24px)] px-3 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500" />
            </label>
            <label :class="['border rounded-lg p-4 cursor-pointer transition-all', payload.retention_action === 'link' ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:border-slate-300']">
              <div class="flex items-center gap-2 mb-2">
                <input type="radio" value="link" v-model="payload.retention_action" class="w-4 h-4 text-blue-600" />
                <span class="font-bold text-sm text-slate-800">Generar Link Maestro</span>
              </div>
              <p class="text-[11px] text-slate-500 pl-6">Genera un enlace temporal de acceso total para descargar los archivos antes de purgar el disco.</p>
            </label>
          </div>
        </div>

        <!-- Step 4: Resumen -->
        <div v-if="currentStep === 3" class="animate-fade-in">
          <h3 class="text-lg font-bold text-slate-800 mb-2">Paso 4: Verificación Final</h3>
          <div class="bg-amber-50 border-l-4 border-amber-500 p-4 mb-6 rounded-r-lg">
            <div class="flex items-start gap-3">
              <svg class="w-5 h-5 text-amber-600 mt-0.5 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
              <div>
                <h4 class="text-sm font-bold text-amber-800">Atención Crítica</h4>
                <p class="text-xs text-amber-700 mt-1">Vas a ejecutar modificaciones en Exchange y Graph API. La remoción de licencias es destructiva e inmediata. Asegúrate de que el payload sea correcto. Todo quedará grabado en la Auditoría bajo tu usuario.</p>
              </div>
            </div>
          </div>
          <div class="bg-slate-900 rounded-lg p-4 font-mono text-xs text-green-400 overflow-x-auto shadow-inner">
            <pre>{{ formattedPayload }}</pre>
          </div>
          <div v-if="executionError" class="mt-4 p-3 bg-red-50 text-red-700 text-sm border border-red-200 rounded">
            <span class="font-bold">Error: </span> {{ executionError }}
          </div>
          <div v-if="executionSuccess" class="mt-4 p-3 bg-emerald-50 text-emerald-700 text-sm border border-emerald-200 rounded">
            <span class="font-bold">Éxito: </span> {{ executionMessage || 'Operación completada y auditada en el sistema.' }}
          </div>
        </div>

      </div>

      <!-- Wizard Error Banner -->
      <div v-if="wizardError" class="mx-6 mt-2 p-3 bg-red-50 text-red-700 text-sm border border-red-200 rounded flex items-center gap-2 animate-fade-in">
        <svg class="w-5 h-5 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
        <span>{{ wizardError }}</span>
      </div>

      <!-- Footer Controls -->
      <div class="mt-4 flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm shrink-0">
        <button @click="currentStep--" :disabled="currentStep === 0 || isExecuting" class="px-6 py-2 border border-slate-300 text-slate-600 font-semibold rounded-lg hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
          Anterior
        </button>
        <button v-if="currentStep < 3" @click="nextStep" class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
          Siguiente
        </button>
        <button v-else @click="executeDelegation" :disabled="isExecuting || executionSuccess" class="px-6 py-2 bg-emerald-600 text-white font-semibold rounded-lg hover:bg-emerald-700 transition-colors shadow-sm flex items-center gap-2 disabled:opacity-50">
          <svg v-if="isExecuting" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          <span v-if="!isExecuting">Ejecutar Offboarding (PROD)</span>
          <span v-else>Ejecutando...</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const showWizard = ref(false)
const isLoading = ref(false)
const mailboxes = ref([])
const searchQuery = ref('')

const steps = [
  { title: 'Saneamiento' },
  { title: 'Delegación' },
  { title: 'Retención' },
  { title: 'Confirmación' }
]

const currentStep = ref(0)
const isExecuting = ref(false)
const executionError = ref('')
const executionSuccess = ref(false)
const executionMessage = ref('')

const payload = ref({
  source_upn: '',
  convert_shared: true,
  remove_license: true,
  hide_gal: true,
  retention_action: 'none',
  retention_target: '',
  targets: []
})

// Dashboard Logic
const fetchSharedMailboxes = async () => {
  isLoading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/delegation/shared-mailboxes', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await res.json()
    if (res.ok) {
      mailboxes.value = Array.isArray(data) ? data : []
    }
  } catch (e) {
    console.error("Error fetching mailboxes", e)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchSharedMailboxes()
})

const loadingOneDrive = ref(null)

const openOneDrive = async (upn) => {
  if (!upn) return;
  loadingOneDrive.value = upn;
  try {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`/api/v1/delegation/onedrive-link/${upn}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    if (res.ok && data.url) {
      window.open(data.url, '_blank');
    } else {
      alert(data.detail || "Error obteniendo el link de OneDrive. Es posible que el usuario no tenga licencia o OneDrive aprovisionado.");
    }
  } catch (e) {
    alert("Fallo de red conectando al API de Graph.");
  } finally {
    loadingOneDrive.value = null;
  }
}

const filteredMailboxes = computed(() => {
  if (!searchQuery.value) return mailboxes.value
  const q = searchQuery.value.toLowerCase()
  return mailboxes.value.filter(m => 
    (m.Mailbox && m.Mailbox.toLowerCase().includes(q)) || 
    (m.DisplayName && m.DisplayName.toLowerCase().includes(q)) ||
    (m.Delegates && m.Delegates.toLowerCase().includes(q))
  )
})

// Wizard Logic
const progressWidth = computed(() => {
  return `${(currentStep.value / (steps.length - 1)) * 100}%`
})

const formattedPayload = computed(() => {
  const displayPayload = JSON.parse(JSON.stringify(payload.value))
  displayPayload.targets.forEach(t => {
    if(t.expiration) {
       t.expiration = new Date(t.expiration).toISOString()
    } else {
       t.expiration = null
    }
  })
  return JSON.stringify(displayPayload, null, 2)
})

const addTarget = () => {
  payload.value.targets.push({
    upn: '',
    permission: 'FullAccess',
    expiration: ''
  })
}

const removeTarget = (index) => {
  payload.value.targets.splice(index, 1)
}

const wizardError = ref('')

const nextStep = () => {
  wizardError.value = ''
  if (currentStep.value === 0 && !payload.value.source_upn) {
    wizardError.value = "Ingresa el buzón origen."
    return
  }
  if (currentStep.value === 1) {
    for (const t of payload.value.targets) {
      if (!t.upn) {
        wizardError.value = "Todos los destinos deben tener UPN."
        return
      }
    }
  }
  if (currentStep.value === 2 && payload.value.retention_action === 'transfer' && !payload.value.retention_target) {
    wizardError.value = "Debes indicar a quién vas a transferir los archivos."
    return
  }
  
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

const executeDelegation = async () => {
  isExecuting.value = true
  executionError.value = ''
  executionSuccess.value = false
  executionMessage.value = ''
  
  try {
    const finalPayload = JSON.parse(formattedPayload.value)
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/delegation/execute', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(finalPayload)
    })
    
    const data = await res.json()
    if (res.ok) {
      executionSuccess.value = true
      executionMessage.value = data.message || 'Operación completada y auditada en el sistema.'
      // Refresh background data
      setTimeout(() => {
        fetchSharedMailboxes()
      }, 3000)
    } else {
      executionError.value = data.detail || 'Error en el servidor de Exchange'
    }
  } catch(e) {
    executionError.value = 'Fallo de red conectando al API'
  } finally {
    isExecuting.value = false
  }
}
</script>

<style scoped>
.fade-in {
  animation: fadeIn 0.4s ease-in-out;
}
.animate-fade-in {
  animation: slideUpFade 0.3s ease-out;
}
.animate-slide-in {
  animation: slideInRight 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes slideUpFade {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
</style>
