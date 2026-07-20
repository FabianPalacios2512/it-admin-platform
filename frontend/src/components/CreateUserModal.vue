<script setup>
import { ref, computed, onMounted } from 'vue'

const emit = defineEmits(['close', 'user-created'])
const API_BASE = '/api/v1'

const step = ref(1) // 1 = Identidad, 2 = Seguridad, 3 = Resumen

// â”€â”€ Estado del formulario â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const formData = ref({
  firstName: '',
  initials: '',
  lastName: '',
  fullName: '',
  upn: '',
  samAccountName: '',
  ou: '',
  password: '',
  mustChangePassword: true,
  cannotChangePassword: false,
  passwordNeverExpires: false,
  accountDisabled: false
})

const confirmPassword = ref('')
const passwordVisible = ref(false)
const confirmVisible = ref(false)

// â”€â”€ OUs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const ous = ref([])
const loadingOUs = ref(true)

onMounted(async () => {
  try {
    const res = await fetch(`${API_BASE}/accounts/ous`)
    if (res.ok) {
      ous.value = await res.json()
      // Por defecto seleccionar Users si existe
      const defaultUsers = ous.value.find(o => o.name === 'Users')
      if (defaultUsers) formData.value.ou = defaultUsers.dn
      else if (ous.value.length > 0) formData.value.ou = ous.value[0].dn
    }
  } catch (e) {
    console.error("Error al cargar OUs:", e)
  } finally {
    loadingOUs.value = false
  }
})

// â”€â”€ LÃ³gica UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Autogenerar Full Name y Login Name
function updateFullName() {
  const parts = [formData.value.firstName, formData.value.initials, formData.value.lastName].filter(Boolean)
  formData.value.fullName = parts.join(' ')
}

function updateLogonName() {
  if (!formData.value.firstName) return
  const first = formData.value.firstName.toLowerCase().trim()
  const last = formData.value.lastName ? formData.value.lastName.toLowerCase().trim() : ''
  const logon = (first[0] + last).replace(/[^a-z0-9]/g, '')
  if (!formData.value.upn) formData.value.upn = logon
  if (!formData.value.samAccountName) formData.value.samAccountName = logon
}

// ValidaciÃ³n de pasos
const step1Valid = computed(() => formData.value.firstName && formData.value.lastName && formData.value.fullName && formData.value.upn && formData.value.samAccountName && formData.value.ou)
const step2Valid = computed(() => formData.value.password && formData.value.password === confirmPassword.value)

// â”€â”€ Reglas mutuamente excluyentes como en AD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function handleOptionChange(option) {
  if (option === 'mustChangePassword' && formData.value.mustChangePassword) {
    formData.value.cannotChangePassword = false
    formData.value.passwordNeverExpires = false
  } else if ((option === 'cannotChangePassword' || option === 'passwordNeverExpires') && (formData.value.cannotChangePassword || formData.value.passwordNeverExpires)) {
    formData.value.mustChangePassword = false
  }
}

// â”€â”€ EnvÃ­o â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const isSubmitting = ref(false)
const submitResult = ref(null)

async function submitForm() {
  isSubmitting.value = true
  submitResult.value = null
  
  try {
    const res = await fetch(`${API_BASE}/accounts/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...formData.value, admin_user: "Admin (Web)" })
    })
    const data = await res.json()
    submitResult.value = data
  } catch (err) {
    submitResult.value = { success: false, error: err.message }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-[100] flex items-center justify-center pt-10 pb-10">
    <div class="fixed inset-0 bg-black/40 backdrop-blur-[2px]" @click="emit('close')"></div>
    <div class="relative w-[540px] bg-white border border-slate-200 rounded-sm shadow-2xl flex flex-col z-10 max-h-full overflow-hidden">
      
      <!-- HEADER -->
      <div class="flex items-center justify-between px-5 py-3 border-b border-slate-200 bg-slate-50">
        <div class="flex items-center gap-2">
          <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/></svg>
          <span class="text-[13px] font-semibold text-slate-800">Nuevo Objeto - Usuario</span>
        </div>
        <button @click="emit('close')" class="text-slate-400 hover:text-slate-700 p-0.5">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <!-- BODY -->
      <div class="p-6 overflow-y-auto">
        <!-- Paso 1: Identidad -->
        <div v-if="step === 1" class="space-y-4">
          <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-100 pb-2">Identidad y UbicaciÃ³n</div>
          
          <div class="grid grid-cols-12 gap-3">
            <div class="col-span-5">
              <label class="block text-[11px] text-slate-500 mb-1">Nombre</label>
              <input v-model="formData.firstName" @input="updateFullName(); updateLogonName()" type="text" class="w-full border border-slate-200 rounded-sm text-[12px] px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400"/>
            </div>
            <div class="col-span-2">
              <label class="block text-[11px] text-slate-500 mb-1">Iniciales</label>
              <input v-model="formData.initials" @input="updateFullName()" type="text" class="w-full border border-slate-200 rounded-sm text-[12px] px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400"/>
            </div>
            <div class="col-span-5">
              <label class="block text-[11px] text-slate-500 mb-1">Apellidos</label>
              <input v-model="formData.lastName" @input="updateFullName(); updateLogonName()" type="text" class="w-full border border-slate-200 rounded-sm text-[12px] px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400"/>
            </div>
          </div>
          
          <div>
            <label class="block text-[11px] text-slate-500 mb-1">Nombre completo</label>
            <input v-model="formData.fullName" type="text" class="w-full border border-slate-200 rounded-sm text-[12px] px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400"/>
          </div>

          <div class="pt-2">
            <label class="block text-[11px] text-slate-500 mb-1">Nombre de inicio de sesiÃ³n de usuario</label>
            <div class="flex gap-2">
              <input v-model="formData.upn" type="text" class="flex-1 border border-slate-200 rounded-sm text-[12px] font-mono px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400"/>
              <div class="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-sm text-[12px] font-mono text-slate-600">@code.local</div>
            </div>
          </div>

          <div class="grid grid-cols-[100px_1fr] gap-2 items-end">
            <div>
              <label class="block text-[11px] text-slate-500 mb-1">Pre-Win2000</label>
              <div class="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-sm text-[12px] font-mono text-slate-600">CODE\</div>
            </div>
            <div>
              <input v-model="formData.samAccountName" type="text" class="w-full border border-slate-200 rounded-sm text-[12px] font-mono px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400"/>
            </div>
          </div>

          <div class="pt-2">
            <label class="block text-[11px] text-slate-500 mb-1">UbicaciÃ³n (Unidad Organizativa)</label>
            <select v-model="formData.ou" :disabled="loadingOUs" class="w-full border border-slate-200 rounded-sm text-[11px] px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400 bg-white">
              <option v-if="loadingOUs" value="">Cargando OUs del AD...</option>
              <option v-for="ou in ous" :key="ou.dn" :value="ou.dn">{{ ou.name }} ({{ ou.type }}) - {{ ou.dn }}</option>
            </select>
          </div>
        </div>

        <!-- Paso 2: ContraseÃ±a -->
        <div v-else-if="step === 2" class="space-y-5">
          <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-100 pb-2">ContraseÃ±a y Seguridad</div>
          
          <div class="space-y-3">
            <div>
              <label class="block text-[11px] text-slate-500 mb-1">ContraseÃ±a</label>
              <div class="relative">
                <input v-model="formData.password" :type="passwordVisible ? 'text' : 'password'" class="w-full border border-slate-200 rounded-sm text-[13px] px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-400 font-mono"/>
                <button @click="passwordVisible = !passwordVisible" class="absolute right-2 top-1.5 text-slate-400 hover:text-slate-600">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                </button>
              </div>
            </div>
            <div>
              <label class="block text-[11px] text-slate-500 mb-1">Confirmar contraseÃ±a</label>
              <div class="relative">
                <input v-model="confirmPassword" :type="confirmVisible ? 'text' : 'password'" :class="['w-full border rounded-sm text-[13px] px-3 py-1.5 focus:outline-none font-mono', confirmPassword && confirmPassword !== formData.password ? 'border-red-300 focus:ring-red-400' : 'border-slate-200 focus:ring-slate-400']"/>
                <button @click="confirmVisible = !confirmVisible" class="absolute right-2 top-1.5 text-slate-400 hover:text-slate-600">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                </button>
              </div>
              <p v-if="confirmPassword && confirmPassword !== formData.password" class="text-[10px] text-red-600 mt-1">Las contraseÃ±as no coinciden.</p>
            </div>
          </div>

          <div class="border border-slate-200 rounded-sm p-3 space-y-2 mt-4 bg-slate-50/50">
            <label class="flex items-start gap-2 cursor-pointer">
              <input type="checkbox" v-model="formData.mustChangePassword" @change="handleOptionChange('mustChangePassword')" class="mt-0.5 w-3.5 h-3.5 border-slate-300 rounded-sm accent-slate-700"/>
              <span class="text-[11px] text-slate-700 font-medium">El usuario debe cambiar la contraseÃ±a en el siguiente inicio de sesiÃ³n</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="formData.cannotChangePassword" @change="handleOptionChange('cannotChangePassword')" class="w-3.5 h-3.5 border-slate-300 rounded-sm accent-slate-700"/>
              <span class="text-[11px] text-slate-700 font-medium">El usuario no puede cambiar la contraseÃ±a</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="formData.passwordNeverExpires" @change="handleOptionChange('passwordNeverExpires')" class="w-3.5 h-3.5 border-slate-300 rounded-sm accent-slate-700"/>
              <span class="text-[11px] text-slate-700 font-medium">La contraseÃ±a nunca expira</span>
            </label>
            <div class="pt-2 border-t border-slate-200 mt-2"></div>
            <label class="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" v-model="formData.accountDisabled" class="w-3.5 h-3.5 border-slate-300 rounded-sm accent-slate-700"/>
              <span class="text-[11px] text-slate-700 font-medium">La cuenta estÃ¡ deshabilitada</span>
            </label>
          </div>
        </div>

        <!-- Paso 3: Resumen -->
        <div v-else-if="step === 3" class="space-y-4">
          <div class="text-[11px] font-semibold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-100 pb-2">Resumen de creaciÃ³n</div>
          
          <div v-if="submitResult" :class="['p-4 rounded-sm border', submitResult.success ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200']">
            <div class="flex gap-3">
              <svg v-if="submitResult.success" class="w-5 h-5 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <svg v-else class="w-5 h-5 text-red-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <div>
                <p :class="['text-[13px] font-bold', submitResult.success ? 'text-emerald-800' : 'text-red-800']">{{ submitResult.success ? 'Â¡Usuario creado con Ã©xito!' : 'Error de creaciÃ³n' }}</p>
                <p :class="['text-[12px] mt-1', submitResult.success ? 'text-emerald-700' : 'text-red-700']">{{ submitResult.message || submitResult.error }}</p>
              </div>
            </div>
          </div>
          
          <div v-if="!submitResult" class="text-[12px] text-slate-600 space-y-1 bg-slate-50 p-4 border border-slate-200 rounded-sm">
            <p>Al hacer clic en Finalizar, se crearÃ¡ el siguiente objeto en el Directorio Activo:</p>
            <div class="mt-4 space-y-2 font-mono text-[11px] text-slate-800">
              <p><strong>Nombre completo:</strong> {{ formData.fullName }}</p>
              <p><strong>Nombre de inicio de sesiÃ³n:</strong> {{ formData.upn }}@code.local</p>
              <p><strong>Ruta LDAP:</strong> {{ formData.ou }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- FOOTER -->
      <div class="flex items-center justify-between px-5 py-3 border-t border-slate-200 bg-slate-50">
        <div class="text-[11px] font-medium text-slate-400">Paso {{ step }} de 3</div>
        <div class="flex items-center gap-2">
          <button v-if="step > 1 && !submitResult" @click="step--" class="text-[12px] font-medium text-slate-600 hover:text-slate-800 px-4 py-1.5 bg-white border border-slate-300 rounded-sm hover:bg-slate-50 transition-colors">AtrÃ¡s</button>
          
          <button v-if="step === 1" @click="step++" :disabled="!step1Valid" class="text-[12px] font-medium text-white bg-slate-800 hover:bg-slate-900 rounded-sm px-5 py-1.5 disabled:opacity-40 transition-colors">Siguiente &gt;</button>
          <button v-else-if="step === 2" @click="step++" :disabled="!step2Valid" class="text-[12px] font-medium text-white bg-slate-800 hover:bg-slate-900 rounded-sm px-5 py-1.5 disabled:opacity-40 transition-colors">Siguiente &gt;</button>
          <button v-else-if="step === 3 && !submitResult" @click="submitForm" :disabled="isSubmitting" class="text-[12px] font-medium text-white bg-slate-800 hover:bg-slate-900 rounded-sm px-5 py-1.5 disabled:opacity-40 transition-colors flex items-center gap-1.5">
            <span v-if="isSubmitting" class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            Finalizar
          </button>
          
          <button v-if="submitResult && submitResult.success" @click="emit('user-created'); emit('close')" class="text-[12px] font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-sm px-5 py-1.5 transition-colors">Cerrar</button>
          <button v-if="submitResult && !submitResult.success" @click="step--" class="text-[12px] font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-50 rounded-sm px-5 py-1.5 transition-colors">Corregir datos</button>
        </div>
      </div>
    </div>
  </div>
</template>
