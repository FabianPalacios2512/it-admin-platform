<script setup>
import { ref, onMounted, computed } from 'vue'

const emit = defineEmits(['close'])
const API_BASE = '/api/v1'

const activeTab = ref('servers') // 'servers' o 'env'

// --- ESTADO: SERVIDORES ---
const servers = ref([])
const loading = ref(true)
const error = ref('')
const successMsg = ref('')

// Modo formulario servidores
const showForm = ref(false)
const testingConnection = ref(false)
const saving = ref(false)
const testResult = ref(null)
const isGeneratingKey = ref(false)
const generatedPublicKey = ref(null)
const authMethod = ref('password') // 'password' o 'key'

const formData = ref({
  id: null,
  name: '',
  server_type: 'da',
  ip: '',
  domain: '',
  admin_user: '',
  admin_pass: '',
  allowed_groups: 'SG_Admins_SoporteTI',
  is_primary: false,
  // v2.0 Multi-OS
  os_type: 'windows',
  ssh_user: '',
  ssh_key: '',
  ssh_port: 22,
})

// Computed: ¿El servidor actual es Linux?
const isLinux = computed(() => formData.value.os_type === 'linux')

const fetchServers = async () => {
  loading.value = true
  try {
    const res = await fetch(`${API_BASE}/servers/`)
    if (!res.ok) throw new Error('Error al cargar servidores')
    servers.value = await res.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const openForm = (server = null) => {
  testResult.value = null
  error.value = ''
  successMsg.value = ''
  authMethod.value = 'password'
  
  if (server) {
    formData.value = {
      id: server.id,
      name: server.name,
      server_type: server.server_type,
      ip: server.ip,
      domain: server.domain,
      admin_user: server.admin_user,
      admin_pass: '',
      allowed_groups: server.allowed_groups,
      is_primary: server.is_primary,
      // v2.0
      os_type: server.os_type || 'windows',
      ssh_user: server.ssh_user || '',
      ssh_key: '',
      ssh_port: server.ssh_port || 22,
    }
    authMethod.value = server.ssh_key ? 'key' : 'password'
  } else {
    formData.value = {
      id: null,
      name: '',
      server_type: 'da',
      ip: '',
      domain: 'code.local',
      admin_user: 'code\\administrador',
      admin_pass: '',
      allowed_groups: 'SG_Admins_SoporteTI',
      is_primary: servers.value.length === 0,
      // v2.0
      os_type: 'windows',
      ssh_user: '',
      ssh_key: '',
      ssh_port: 22,
    }
  }
  generatedPublicKey.value = null
  showForm.value = true
}

// Cambia OS type y limpia campos del otro OS
const setOsType = (type) => {
  formData.value.os_type = type
  if (type === 'windows') {
    formData.value.server_type = 'da' // Default Windows
    formData.value.ssh_user = ''
    formData.value.ssh_key = ''
    formData.value.ssh_port = 22
  } else {
    formData.value.server_type = 'generic' // Default Linux
    formData.value.domain = ''
    formData.value.admin_user = ''
  }
  testResult.value = null
  generatedPublicKey.value = null
}

const testConnection = async () => {
  if (!formData.value.ip) {
    testResult.value = { success: false, message: 'Falta IP o Hostname.' }
    return
  }
  if (isLinux.value && !formData.value.ssh_user) {
    testResult.value = { success: false, message: 'Falta el Usuario SSH.' }
    return
  }
  if (!isLinux.value && !formData.value.admin_user) {
    testResult.value = { success: false, message: 'Falta el Usuario Administrador.' }
    return
  }
  
  testingConnection.value = true
  testResult.value = null
  
  try {
    let res
    if (formData.value.id && !formData.value.admin_pass) {
      res = await fetch(`${API_BASE}/servers/${formData.value.id}/test`, { method: 'POST' })
    } else {
      res = await fetch(`${API_BASE}/servers/test-new`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData.value)
      })
    }
    
    const data = await res.json()
    testResult.value = { success: data.success, message: data.message }
  } catch (err) {
    testResult.value = { success: false, message: 'Error de red.' }
  } finally {
    testingConnection.value = false
  }
}

// -----------------------------------------------------
// GENERADOR DE LLAVES SSH
// -----------------------------------------------------
const generateSshKey = async () => {
  isGeneratingKey.value = true
  testResult.value = null
  generatedPublicKey.value = null
  
  try {
    const res = await fetch(`${API_BASE}/servers/generate-ssh-key`, {
      method: 'POST'
    })
    const data = await res.json()
    if (data.success) {
      formData.value.ssh_key = data.private_key
      generatedPublicKey.value = data.public_key
    } else {
      alert("Error del servidor al generar llave: " + data.message)
    }
  } catch (e) {
    alert("Error de red al intentar generar la llave.")
  } finally {
    isGeneratingKey.value = false
  }
}

const copyPublicKey = async () => {
  if (!generatedPublicKey.value) return
  try {
    await navigator.clipboard.writeText(generatedPublicKey.value)
  } catch (err) {
    console.error("Error al copiar: ", err)
  }
}

const saveServer = async () => {
  saving.value = true
  error.value = ''
  
  try {
    const isEdit = !!formData.value.id
    const url = isEdit ? `${API_BASE}/servers/${formData.value.id}` : `${API_BASE}/servers/`
    const method = isEdit ? 'PUT' : 'POST'
    
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData.value)
    })
    
    const data = await res.json()
    if (!data.success) throw new Error(data.detail || data.error || 'Error al guardar')
    
    successMsg.value = data.message
    showForm.value = false
    fetchServers()
    
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

const deleteServer = async (id) => {
  if (!confirm('¿Estás seguro de eliminar este servidor?')) return
  
  try {
    const res = await fetch(`${API_BASE}/servers/${id}`, { method: 'DELETE' })
    const data = await res.json()
    if (data.success) {
      successMsg.value = data.message
      setTimeout(() => { successMsg.value = '' }, 3000)
      fetchServers()
    }
  } catch (err) {
    console.error(err)
  }
}

// --- ESTADO: ENTORNO (Master Password) ---
const envSetupState = ref('loading') // 'loading', 'needs_setup', 'needs_unlock', 'unlocked'
const masterPassword = ref('')
const envError = ref('')
const envSuccess = ref('')
const envSaving = ref(false)

const envData = ref({
  ENTRA_TENANT_ID: '',
  ENTRA_CLIENT_ID: '',
  ENTRA_CLIENT_SECRET: ''
})

const showEntraSecret = ref(false)

const fetchEnvStatus = async () => {
  try {
    const res = await fetch(`${API_BASE}/system/status`)
    const data = await res.json()
    if (data.is_setup) {
      envSetupState.value = 'needs_unlock'
    } else {
      envSetupState.value = 'needs_setup'
    }
  } catch (err) {
    envError.value = 'Error al conectar con el servidor.'
  }
}

const setupMasterPassword = async () => {
  if (!masterPassword.value || masterPassword.value.length < 6) {
    envError.value = 'La clave debe tener al menos 6 caracteres.'
    return
  }
  
  envSaving.value = true
  envError.value = ''
  try {
    const res = await fetch(`${API_BASE}/system/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ master_password: masterPassword.value })
    })
    
    if (!res.ok) throw new Error('Error al configurar la clave maestra.')
    
    envSuccess.value = 'Clave maestra configurada correctamente. Ahora puedes desbloquear la bóveda.'
    setTimeout(() => { envSuccess.value = '' }, 4000)
    
    masterPassword.value = ''
    envSetupState.value = 'needs_unlock'
  } catch (err) {
    envError.value = err.message
  } finally {
    envSaving.value = false
  }
}

const unlockVault = async () => {
  if (!masterPassword.value) return
  
  envSaving.value = true
  envError.value = ''
  try {
    const res = await fetch(`${API_BASE}/system/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ master_password: masterPassword.value })
    })
    
    if (!res.ok) {
      if (res.status === 401) throw new Error('Clave maestra incorrecta.')
      throw new Error('Error al verificar la clave.')
    }
    
    const data = await res.json()
    envData.value = data
    envSetupState.value = 'unlocked'
    envSuccess.value = 'Bóveda desbloqueada.'
    setTimeout(() => { envSuccess.value = '' }, 2000)
    
  } catch (err) {
    envError.value = err.message
  } finally {
    envSaving.value = false
  }
}

const saveEnvData = async () => {
  envSaving.value = true
  envError.value = ''
  try {
    const payload = {
      master_password: masterPassword.value,
      ...envData.value
    }
    
    const res = await fetch(`${API_BASE}/system/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (!res.ok) throw new Error('Error al guardar la configuración.')
    
    envSuccess.value = 'Configuración de Entra ID guardada y recargada.'
    setTimeout(() => { envSuccess.value = '' }, 3000)
  } catch (err) {
    envError.value = err.message
  } finally {
    envSaving.value = false
  }
}

const handleTabSwitch = (tab) => {
  activeTab.value = tab
  if (tab === 'env' && envSetupState.value === 'loading') {
    fetchEnvStatus()
  }
}

onMounted(() => {
  fetchServers()
})
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
    <div class="bg-white rounded-md shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
      
      <!-- Header with Tabs -->
      <div class="border-b border-slate-200 bg-slate-50">
        <div class="flex items-center justify-between px-6 py-4">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-slate-800 text-white flex items-center justify-center shrink-0">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <h2 class="text-[14px] font-bold text-slate-800 tracking-tight">Configuración del Sistema</h2>
              <p class="text-[11px] text-slate-500">Administra los parámetros base de la infraestructura</p>
            </div>
          </div>
          <button @click="emit('close')" class="text-slate-400 hover:text-slate-600 p-1 rounded-sm transition-colors">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>
        
        <!-- Tabs Nav -->
        <div class="px-6 flex items-center gap-6">
          <button 
            @click="handleTabSwitch('servers')"
            :class="['pb-3 text-[12px] font-bold uppercase tracking-wider transition-colors border-b-2', activeTab === 'servers' ? 'border-slate-800 text-slate-800' : 'border-transparent text-slate-400 hover:text-slate-600']"
          >
            Servidores de Base
          </button>
          <button 
            @click="handleTabSwitch('env')"
            :class="['pb-3 text-[12px] font-bold uppercase tracking-wider transition-colors border-b-2', activeTab === 'env' ? 'border-slate-800 text-slate-800' : 'border-transparent text-slate-400 hover:text-slate-600']"
          >
            Integración Microsoft Entra
          </button>
        </div>
      </div>

      <!-- Body -->
      <div class="p-6 overflow-y-auto flex-1 bg-slate-50 relative min-h-[300px]">
        
        <!-- TAB: SERVIDORES -->
        <div v-show="activeTab === 'servers'" class="h-full">
          <div v-if="successMsg" class="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[12px] rounded-sm">
            {{ successMsg }}
          </div>

          <!-- LISTA de servidores -->
          <div v-if="!showForm">
            <div class="flex justify-end mb-4">
              <button @click="openForm()" class="flex items-center gap-1.5 bg-slate-800 hover:bg-slate-900 text-white px-3 py-1.5 rounded-sm text-[12px] font-medium transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                Agregar Servidor
              </button>
            </div>

            <div v-if="loading" class="flex justify-center py-8">
              <span class="w-6 h-6 border-2 border-slate-300 border-t-slate-800 rounded-full animate-spin"></span>
            </div>

            <div v-else-if="servers.length === 0" class="text-center py-12 bg-white border border-slate-200 rounded-sm">
              <svg class="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
              <p class="text-[13px] font-medium text-slate-600">No hay servidores configurados.</p>
            </div>

            <div v-else class="space-y-3">
              <div v-for="server in servers" :key="server.id" class="bg-white border border-slate-200 rounded-sm p-4 flex items-center justify-between shadow-sm hover:border-slate-300 transition-colors">
                <div class="flex items-center gap-4">
                  <!-- Icono OS -->
                  <div :class="['w-10 h-10 rounded-sm flex items-center justify-center shrink-0 text-lg', server.os_type === 'linux' ? 'bg-slate-100' : (server.server_type === 'da' ? 'bg-indigo-50' : 'bg-slate-50')]">
                    <span v-if="server.os_type === 'linux'">🐧</span>
                    <svg v-else class="w-5 h-5" :class="server.server_type === 'da' ? 'text-indigo-600' : 'text-slate-600'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
                    </svg>
                  </div>
                  <div>
                    <div class="flex items-center gap-2">
                      <h3 class="text-[13px] font-bold text-slate-800">{{ server.name }}</h3>
                      <span v-if="server.is_primary" class="bg-emerald-100 text-emerald-800 text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-sm">Primario</span>
                      <!-- Badge OS -->
                      <span :class="['text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-sm', server.os_type === 'linux' ? 'bg-slate-100 text-slate-600' : 'bg-slate-100 text-slate-500']">
                        {{ server.os_type === 'linux' ? 'Linux' : 'Windows' }}
                      </span>
                    </div>
                    <p class="text-[11px] text-slate-500 flex items-center gap-2 mt-0.5">
                      <span class="font-medium text-slate-600">{{ server.server_type_label }}</span>
                      <span>•</span>
                      <span class="font-mono">{{ server.ip }}</span>
                      <span v-if="server.os_type === 'linux'" class="font-mono text-slate-400">:{{ server.ssh_port || 22 }}</span>
                    </p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <button @click="openForm(server)" class="text-slate-400 hover:text-indigo-600 p-1.5 transition-colors" title="Editar">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                  </button>
                  <button @click="deleteServer(server.id)" class="text-slate-400 hover:text-red-600 p-1.5 transition-colors" title="Eliminar">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- FORMULARIO: Nuevo / Editar Servidor -->
          <div v-else class="bg-white border border-gray-100 p-6 rounded-xl shadow-sm">
            <div class="flex items-center gap-3 mb-6 pb-4 border-b border-gray-100">
              <button @click="showForm = false" class="text-gray-400 hover:text-gray-700 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18"/></svg>
              </button>
              <h3 class="text-lg font-semibold text-gray-900">{{ formData.id ? 'Editar servidor' : 'Nuevo servidor' }}</h3>
            </div>

            <div v-if="error" class="mb-5 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-md">
              {{ error }}
            </div>

            <!-- ── SELECTOR DE OS ───────────────────────────────────────── -->
            <div class="mb-6">
              <label class="block text-sm font-medium text-gray-700 mb-2">Sistema operativo</label>
              <div class="flex gap-1 bg-gray-100 p-1 rounded-lg">
                <button
                  type="button"
                  @click="setOsType('windows')"
                  :class="['flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium transition-all outline-none focus:ring-2 focus:ring-blue-500/20', formData.os_type === 'windows' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700']"
                >
                  <span>🪟</span> Windows
                </button>
                <button
                  type="button"
                  @click="setOsType('linux')"
                  :class="['flex-1 flex items-center justify-center gap-2 py-2 rounded-md text-sm font-medium transition-all outline-none focus:ring-2 focus:ring-blue-500/20', formData.os_type === 'linux' ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500 hover:text-gray-700']"
                >
                  <span>🐧</span> Linux (SSH)
                </button>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-5">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Nombre del servidor</label>
                <input v-model="formData.name" type="text" placeholder="Ej: SRV-UBUNTU-01" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 placeholder:text-gray-400"/>
              </div>
              
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Tipo de servidor</label>
                <select v-model="formData.server_type" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20">
                  <template v-if="!isLinux">
                    <option value="da">Directorio Activo</option>
                    <option value="ha">Alta Disponibilidad (HA)</option>
                    <option value="files">Servidor de Archivos</option>
                    <option value="printers">Servidor de Impresoras</option>
                    <option value="app">Servidor de Aplicaciones</option>
                    <option value="rds">Servidor RDS / Escritorio Remoto</option>
                  </template>
                  <template v-else>
                    <option value="pbx">PBX / Telefonía (Issabel)</option>
                    <option value="web">Servidor Web</option>
                    <option value="db">Base de Datos</option>
                    <option value="docker">Docker / Contenedores</option>
                    <option value="generic">Genérico</option>
                  </template>
                </select>
              </div>

              <!-- IP + Puerto -->
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1.5">IP o hostname</label>
                <input v-model="formData.ip" type="text" placeholder="Ej: 192.168.20.100" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 font-mono placeholder:text-gray-400"/>
              </div>

              <div v-if="isLinux">
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Puerto SSH</label>
                <input v-model.number="formData.ssh_port" type="number" min="1" max="65535" placeholder="22" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 font-mono placeholder:text-gray-400"/>
              </div>
              <div v-else-if="formData.server_type === 'da' || formData.server_type === 'ha'">
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Dominio</label>
                <input v-model="formData.domain" type="text" placeholder="Ej: code.local" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 placeholder:text-gray-400"/>
              </div>

              <!-- CREDENCIALES SEPARADAS POR OS -->
              <div class="col-span-2 flex items-center gap-3 mt-4 mb-2">
                <h4 class="text-xs uppercase tracking-wider font-semibold text-gray-500 whitespace-nowrap">
                  {{ isLinux ? 'Credenciales SSH' : 'Credenciales de servicio' }}
                </h4>
                <hr class="w-full border-gray-200" />
              </div>

              <!-- WINDOWS: Usuario + Contraseña -->
              <template v-if="!isLinux">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1.5">Usuario administrador</label>
                  <input v-model="formData.admin_user" type="text" placeholder="Ej: code\administrador" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 font-mono placeholder:text-gray-400"/>
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1.5">Contraseña</label>
                  <input v-model="formData.admin_pass" type="password" :placeholder="formData.id ? 'Dejar en blanco para no cambiar' : 'Requerido'" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 placeholder:text-gray-400"/>
                </div>
              </template>

              <!-- LINUX: Usuario SSH + Contraseña o Llave -->
              <template v-else>
                <div class="col-span-2">
                  <label class="block text-sm font-medium text-gray-700 mb-1.5">Usuario SSH</label>
                  <input v-model="formData.ssh_user" type="text" placeholder="Ej: root, ubuntu, admin" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 font-mono placeholder:text-gray-400"/>
                </div>
                
                <div class="col-span-2 mt-2">
                  <label class="block text-sm font-medium text-gray-700 mb-2">Método de autenticación</label>
                  <div class="flex gap-6 p-3 bg-gray-50 border border-gray-200 rounded-md">
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input type="radio" v-model="authMethod" value="password" class="w-4 h-4 text-blue-600 bg-white border-gray-300 focus:ring-blue-500 focus:ring-2 focus:ring-offset-1" />
                      <span class="text-sm text-gray-700 font-medium">Contraseña</span>
                    </label>
                    <label class="flex items-center gap-2 cursor-pointer">
                      <input type="radio" v-model="authMethod" value="key" class="w-4 h-4 text-blue-600 bg-white border-gray-300 focus:ring-blue-500 focus:ring-2 focus:ring-offset-1" />
                      <span class="text-sm text-gray-700 font-medium">Llave SSH</span>
                    </label>
                  </div>
                </div>

                <div v-if="authMethod === 'password'" class="col-span-2 mt-2">
                  <label class="block text-sm font-medium text-gray-700 mb-1.5">Contraseña SSH</label>
                  <input v-model="formData.admin_pass" type="password" :placeholder="formData.id ? 'Dejar en blanco para no cambiar' : 'Requerida'" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 placeholder:text-gray-400"/>
                </div>
                
                <div v-else class="col-span-2 mt-2">
                  <label class="block text-sm font-medium text-gray-700 mb-1.5 flex justify-between items-center">
                    Llave privada SSH
                  </label>
                  <textarea v-model="formData.ssh_key" rows="6" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm font-mono text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 placeholder:text-gray-400" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;..."></textarea>
                  
                  <div class="flex justify-end mt-2">
                    <button @click.prevent="generateSshKey" :disabled="isGeneratingKey" class="text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline transition-colors outline-none focus:ring-2 focus:ring-blue-500/20 rounded-sm disabled:opacity-50">
                      {{ isGeneratingKey ? 'Generando llaves...' : 'Generar nueva llave automáticamente' }}
                    </button>
                  </div>

                  <div v-if="generatedPublicKey" class="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-md">
                    <p class="text-sm font-semibold text-gray-900 mb-1">Llave generada con éxito</p>
                    <p class="text-sm text-gray-600 mb-3 leading-relaxed">
                      Copia esta <b>Llave Pública</b> y agrégala a las claves SSH de tu servidor antes de probar la conexión.
                    </p>
                    <div class="flex items-center gap-2">
                      <input readonly :value="generatedPublicKey" class="w-full text-xs p-2 bg-white border border-gray-200 rounded-md font-mono text-gray-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 select-all"/>
                      <button @click.prevent="copyPublicKey" class="px-4 py-2 bg-white border border-gray-200 hover:bg-gray-50 hover:text-gray-900 text-gray-700 font-medium text-sm rounded-md transition-colors whitespace-nowrap outline-none focus:ring-2 focus:ring-blue-500/20">Copiar</button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Grupos permitidos (solo para tipo DA en Windows) -->
              <div v-if="!isLinux && formData.server_type === 'da'" class="col-span-2 mt-4">
                <label class="block text-sm font-medium text-gray-700 mb-1.5">Grupos permitidos para login</label>
                <input v-model="formData.allowed_groups" type="text" placeholder="Ej: SG_Admins_SoporteTI" class="w-full bg-white border border-gray-200 rounded-md px-3 py-2 text-sm text-gray-900 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 placeholder:text-gray-400"/>
              </div>

              <div class="col-span-2 flex items-center gap-3 mt-4">
                <input v-model="formData.is_primary" type="checkbox" id="primaryCheck" class="w-4 h-4 rounded text-blue-600 bg-white border-gray-300 focus:ring-blue-500 focus:ring-2 focus:ring-offset-1 transition-all"/>
                <label for="primaryCheck" class="text-sm text-gray-700 font-medium cursor-pointer select-none">
                  Establecer como servidor principal
                </label>
              </div>
            </div>

            <!-- Pruebas y guardado (Footer) -->
            <div class="mt-8 pt-5 border-t border-gray-100 flex items-center justify-between">
              <div class="flex items-center gap-3">
                <button @click="testConnection" :disabled="testingConnection" type="button" class="text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 border border-gray-200 px-4 py-2 rounded-lg transition-all outline-none focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 flex items-center gap-2">
                  <span v-if="testingConnection" class="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin"></span>
                  <span>{{ isLinux ? 'Probar SSH' : 'Probar conexión' }}</span>
                </button>
                <span v-if="testResult" :class="['text-sm font-medium flex items-center gap-2', testResult.success ? 'text-emerald-600' : 'text-red-600']">
                  <span :class="['w-2 h-2 rounded-full', testResult.success ? 'bg-emerald-500' : 'bg-red-500']"></span>
                  {{ testResult.message }}
                </span>
              </div>

              <div class="flex items-center gap-3">
                <button @click="showForm = false" type="button" class="text-sm font-medium text-gray-500 hover:text-gray-800 hover:underline px-3 py-2 transition-colors outline-none focus:ring-2 focus:ring-gray-400/20 rounded-md">Cancelar</button>
                <button @click="saveServer" :disabled="saving" type="button" class="text-sm font-semibold text-white bg-gray-900 hover:bg-black px-6 py-2.5 rounded-lg flex items-center gap-2 transition-all outline-none focus:ring-2 focus:ring-gray-900/20 disabled:opacity-50">
                  <span v-if="saving" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                  Guardar servidor
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- TAB: ENTORNO (ENTRA ID) -->
        <div v-show="activeTab === 'env'" class="h-full">
          
          <div v-if="envSuccess" class="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 text-[12px] rounded-sm">
            {{ envSuccess }}
          </div>
          <div v-if="envError" class="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 text-[12px] rounded-sm">
            {{ envError }}
          </div>

          <!-- Estado de carga -->
          <div v-if="envSetupState === 'loading'" class="flex justify-center py-12">
            <span class="w-6 h-6 border-2 border-slate-300 border-t-slate-800 rounded-full animate-spin"></span>
          </div>

          <!-- Estado: Requiere setup -->
          <div v-else-if="envSetupState === 'needs_setup'" class="flex flex-col items-center justify-center py-10 bg-white border border-slate-200 rounded-sm">
            <svg class="w-12 h-12 text-slate-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <h3 class="text-[14px] font-bold text-slate-800 mb-1">Bóveda de Seguridad Desactivada</h3>
            <p class="text-[12px] text-slate-500 mb-6 text-center max-w-sm">Para proteger las credenciales de Microsoft Entra y variables del sistema, debes crear una Clave Maestra.</p>
            
            <div class="w-full max-w-xs space-y-3">
              <input v-model="masterPassword" type="password" placeholder="Nueva Clave Maestra" class="w-full border border-slate-300 rounded-sm px-3 py-2 text-[12px] focus:border-slate-800 outline-none"/>
              <button @click="setupMasterPassword" :disabled="envSaving" class="w-full bg-slate-800 hover:bg-slate-900 text-white py-2 rounded-sm text-[12px] font-medium transition-colors">
                Establecer Clave y Proteger
              </button>
            </div>
          </div>

          <!-- Estado: Bloqueado (Pedir clave) -->
          <div v-else-if="envSetupState === 'needs_unlock'" class="flex flex-col items-center justify-center py-10 bg-white border border-slate-200 rounded-sm">
            <svg class="w-12 h-12 text-slate-800 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <h3 class="text-[14px] font-bold text-slate-800 mb-1">Bóveda de Entorno Bloqueada</h3>
            <p class="text-[12px] text-slate-500 mb-6 text-center max-w-sm">Ingresa la Clave Maestra para revelar y editar las credenciales de Microsoft Entra.</p>
            
            <form @submit.prevent="unlockVault" class="w-full max-w-xs space-y-3">
              <input v-model="masterPassword" type="password" placeholder="Clave Maestra" class="w-full border border-slate-300 rounded-sm px-3 py-2 text-[12px] focus:border-slate-800 outline-none text-center tracking-widest"/>
              <button type="submit" :disabled="envSaving" class="w-full bg-slate-800 hover:bg-slate-900 text-white py-2 rounded-sm text-[12px] font-medium transition-colors">
                Desbloquear Bóveda
              </button>
            </form>
          </div>

          <!-- Estado: Desbloqueado -->
          <div v-else-if="envSetupState === 'unlocked'" class="bg-white border border-emerald-200 p-5 rounded-sm relative shadow-sm">
            <div class="absolute top-4 right-4 bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-sm flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Bóveda Abierta
            </div>

            <h3 class="text-[13px] font-bold text-slate-800 mb-1">Credenciales de Microsoft Entra ID</h3>
            <p class="text-[11px] text-slate-500 mb-6 border-b border-slate-100 pb-3">Estos parámetros controlan la sincronización y autenticación con Microsoft Graph y la nube corporativa.</p>

            <div class="space-y-4">
              <div>
                <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Entra Tenant ID</label>
                <input v-model="envData.ENTRA_TENANT_ID" type="text" placeholder="Ej. b9af4dc2-f021-..." class="w-full border border-slate-300 rounded-sm px-3 py-2 text-[12px] focus:border-slate-800 outline-none font-mono"/>
              </div>
              <div>
                <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Entra Client ID (Application ID)</label>
                <input v-model="envData.ENTRA_CLIENT_ID" type="text" placeholder="Ej. e6b5baa0-1fc9-..." class="w-full border border-slate-300 rounded-sm px-3 py-2 text-[12px] focus:border-slate-800 outline-none font-mono"/>
              </div>
              <div>
                <label class="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1.5">Entra Client Secret</label>
                <div class="relative">
                  <input v-model="envData.ENTRA_CLIENT_SECRET" :type="showEntraSecret ? 'text' : 'password'" placeholder="••••••••••••••" class="w-full border border-slate-300 rounded-sm pl-3 pr-10 py-2 text-[12px] focus:border-slate-800 outline-none font-mono"/>
                  <button type="button" @click="showEntraSecret = !showEntraSecret" class="absolute inset-y-0 right-0 px-3 flex items-center text-slate-400 hover:text-slate-600">
                    <svg v-if="showEntraSecret" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.29 3.29m0 0a10.05 10.05 0 015.188-1.556c4.478 0 8.268 2.943 9.542 7a10.02 10.02 0 01-4.132 5.411m0 0l-3.29-3.29" /></svg>
                    <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                  </button>
                </div>
              </div>
            </div>

            <div class="mt-6 pt-4 border-t border-slate-100 flex justify-end">
              <button @click="saveEnvData" :disabled="envSaving" class="text-[12px] font-medium text-white bg-emerald-600 hover:bg-emerald-700 px-6 py-2 rounded-sm flex items-center gap-2 transition-colors disabled:opacity-50">
                <span v-if="envSaving" class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                Guardar Credenciales Entra ID
              </button>
            </div>
          </div>

        </div>

      </div>
    </div>
  </div>
</template>
