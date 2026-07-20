<script setup>
import { ref, onMounted } from 'vue'

const API_BASE = '/api/v1'

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const successMessage = ref('')

const config = ref({
  LDAP_SERVER: '',
  LDAP_USER: '',
  LDAP_PASSWORD: '',
  SECRET_KEY: '',
  ENTRA_TENANT_ID: '',
  ENTRA_CLIENT_ID: '',
  ENTRA_CLIENT_SECRET: ''
})

const showPassword = ref({
  LDAP_PASSWORD: false,
  SECRET_KEY: false,
  ENTRA_CLIENT_SECRET: false
})

const fetchConfig = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/system/config`)
    if (!res.ok) throw new Error('Error al cargar la configuración del sistema')
    const data = await res.json()
    // Populate form with existing config
    for (const key in config.value) {
      if (data[key] !== undefined) {
        config.value[key] = data[key]
      }
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  error.value = ''
  successMessage.value = ''
  try {
    const res = await fetch(`${API_BASE}/system/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(config.value)
    })
    
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Error al guardar la configuración')
    }
    
    const data = await res.json()
    successMessage.value = data.message || 'Configuración guardada exitosamente.'
    
    // Ocultar el mensaje después de 3 segundos
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
    
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

const toggleVisibility = (field) => {
  showPassword.value[field] = !showPassword.value[field]
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-4 sm:py-6 font-sans flex flex-col h-full">
    
    <!-- Breadcrumb & Header -->
    <div class="mb-6 border-b border-gray-100 pb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/login" class="text-[11px] text-gray-400 hover:text-gray-600 transition-colors">&larr; Volver al Inicio de Sesión</router-link>
      </div>
      <h2 class="text-2xl font-semibold text-gray-900 tracking-tight">Configuración General</h2>
      <p class="text-sm text-gray-500 mt-1">
        Gestione las variables de entorno del sistema. Los cambios aplicarán de forma inmediata en el backend.
      </p>
    </div>

    <!-- Estado de Carga Inicial -->
    <div v-if="loading" class="py-16 flex flex-col items-center justify-center">
      <div class="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mb-3"></div>
      <span class="text-sm text-gray-500 font-medium">Cargando configuraciÃ³n...</span>
    </div>

    <!-- Contenido del Formulario -->
    <div v-else class="space-y-8">
      
      <!-- Mensajes de Alerta -->
      <div v-if="error" class="p-3 bg-red-50 border border-red-100 rounded text-sm text-red-600">
        {{ error }}
      </div>
      <div v-if="successMessage" class="p-3 bg-green-50 border border-green-100 rounded text-sm text-green-700">
        {{ successMessage }}
      </div>

      <!-- SecciÃ³n 1: Conexión a Directorio Activo -->
      <div>
        <h3 class="text-base font-semibold text-gray-900 mb-4">Conexión a Directorio Activo</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
          
          <div class="col-span-1">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Servidor LDAP (URI)</label>
            <input v-model="config.LDAP_SERVER" type="text" class="w-full px-3 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors" placeholder="ldap://dominio.local">
          </div>

          <div class="col-span-1">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Usuario (Service Account)</label>
            <input v-model="config.LDAP_USER" type="text" class="w-full px-3 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors" placeholder="DOMINIO\svc_admin">
          </div>

          <div class="col-span-1 relative">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Contraseña LDAP</label>
            <div class="relative">
              <input v-model="config.LDAP_PASSWORD" :type="showPassword.LDAP_PASSWORD ? 'text' : 'password'" class="w-full pl-3 pr-10 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors" placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢">
              <button type="button" @click="toggleVisibility('LDAP_PASSWORD')" class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors">
                <svg v-if="showPassword.LDAP_PASSWORD" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0a10.05 10.05 0 015.188-1.556c4.478 0 8.268 2.943 9.542 7a10.02 10.02 0 01-4.132 5.411m0 0l-3.29-3.29" /></svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              </button>
            </div>
          </div>

          <div class="col-span-1 relative">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Clave Secreta de App (JWT)</label>
            <div class="relative">
              <input v-model="config.SECRET_KEY" :type="showPassword.SECRET_KEY ? 'text' : 'password'" class="w-full pl-3 pr-10 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors" placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢">
              <button type="button" @click="toggleVisibility('SECRET_KEY')" class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors">
                <svg v-if="showPassword.SECRET_KEY" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0a10.05 10.05 0 015.188-1.556c4.478 0 8.268 2.943 9.542 7a10.02 10.02 0 01-4.132 5.411m0 0l-3.29-3.29" /></svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              </button>
            </div>
          </div>

        </div>
      </div>

      <hr class="border-gray-100">

      <!-- SecciÃ³n 2: Integraciones -->
      <div>
        <h3 class="text-base font-semibold text-gray-900 mb-4">Integraciones (Entra ID / Cloud)</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
          
          <div class="col-span-1">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Entra ID Tenant ID</label>
            <input v-model="config.ENTRA_TENANT_ID" type="text" class="w-full px-3 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors font-mono" placeholder="Ej. b9af4dc2-f021-4ba0-84b1-...">
          </div>

          <div class="col-span-1">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Entra ID Client ID (Application ID)</label>
            <input v-model="config.ENTRA_CLIENT_ID" type="text" class="w-full px-3 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors font-mono" placeholder="Ej. e6b5baa0-1fc9-49d3-9982-...">
          </div>

          <div class="col-span-2 relative">
            <label class="block text-[13px] font-medium text-gray-900 mb-1">Entra ID Client Secret</label>
            <div class="relative">
              <input v-model="config.ENTRA_CLIENT_SECRET" :type="showPassword.ENTRA_CLIENT_SECRET ? 'text' : 'password'" class="w-full pl-3 pr-10 py-2 bg-white border border-gray-200 rounded text-[13px] text-gray-900 focus:outline-none focus:border-gray-400 focus:ring-0 placeholder-gray-400 transition-colors font-mono" placeholder="â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢">
              <button type="button" @click="toggleVisibility('ENTRA_CLIENT_SECRET')" class="absolute inset-y-0 right-0 px-3 flex items-center text-gray-400 hover:text-gray-600 transition-colors">
                <svg v-if="showPassword.ENTRA_CLIENT_SECRET" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0a10.05 10.05 0 015.188-1.556c4.478 0 8.268 2.943 9.542 7a10.02 10.02 0 01-4.132 5.411m0 0l-3.29-3.29" /></svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
              </button>
            </div>
          </div>

        </div>
      </div>

      <!-- Action Buttons -->
      <div class="pt-6 border-t border-gray-100 flex justify-end">
        <button @click="saveConfig" :disabled="saving" class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-semibold rounded shadow-sm transition-colors disabled:opacity-50 flex items-center gap-2">
          <span v-if="saving" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          Guardar Configuración
        </button>
      </div>

    </div>
  </div>
</template>
