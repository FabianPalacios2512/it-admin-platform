<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  userProfile: { type: Object, required: true },
  accountOptions: { type: Object, default: null }
})

const emit = defineEmits(['close', 'saved'])
const API_BASE = '/api/v1'

// Estado de pestañas
const activeTab = ref('general')
const tabs = [
  { id: 'general', name: 'General', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  { id: 'cuenta', name: 'Cuenta', icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
  { id: 'miembro', name: 'Miembro de', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' },
]

// Datos General
const general = ref({
  givenName: '', initials: '', sn: '', displayName: '',
  description: '', physicalDeliveryOfficeName: '',
  telephoneNumber: '', mail: '',
  title: '', department: '', manager: ''
})

// Datos Cuenta
const cuenta = ref({
  upnPrefix: '', upnSuffix: '@local.code', sAMAccountName: '',
  must_change_password: false,
  cannot_change_password: false,
  password_never_expires: false,
  store_reversible_encryption: false,
  account_disabled: false,
})

// Miembro de / Grupos
const groups = ref([])
const groupSearchQuery = ref('')
const groupSearchResults = ref([])
const searchingGroups = ref(false)

// Jefe Inmediato
const managerSearchQuery = ref('')
const managerSearchResults = ref([])
const searchingManager = ref(false)
const selectedManagerName = ref('')

// Estado Global
const saving = ref(false)
const resultMsg = ref(null)

onMounted(() => {
  general.value = {
    givenName: props.userProfile.firstName || '',
    initials: '',
    sn: props.userProfile.lastName || '',
    displayName: props.userProfile.fullName || '',
    description: props.userProfile.description || '',
    physicalDeliveryOfficeName: props.userProfile.office === 'Sin oficina' ? '' : (props.userProfile.office || ''),
    telephoneNumber: props.userProfile.phone || '',
    mail: props.userProfile.email || '',
    title: props.userProfile.jobTitle || props.userProfile.title || '',
    department: props.userProfile.department || '',
    manager: ''
  }
  
  if (props.userProfile.manager) {
    selectedManagerName.value = props.userProfile.manager
  }
  
  if (props.accountOptions) {
    const defaultUpn = props.userProfile.email ? props.userProfile.username + '@' + (props.userProfile.email.split('@')[1] || 'local.code') : props.userProfile.username + '@local.code'
    const parts = defaultUpn.split('@')
    cuenta.value = {
      upnPrefix: parts[0] || props.userProfile.username,
      upnSuffix: '@' + (parts[1] || 'local.code'),
      sAMAccountName: props.userProfile.username || '',
      must_change_password: props.accountOptions.must_change_password || false,
      cannot_change_password: props.accountOptions.cannot_change_password || false,
      password_never_expires: props.accountOptions.password_never_expires || false,
      store_reversible_encryption: props.accountOptions.store_reversible_encryption || false,
      account_disabled: props.accountOptions.account_disabled || false,
    }
  }

  if (props.userProfile.groups) {
    groups.value = [...props.userProfile.groups]
  }
})

// Búsqueda de Jefe Inmediato
let managerSearchTimeout = null
watch(managerSearchQuery, (q) => {
  clearTimeout(managerSearchTimeout)
  if (!q || q.length < 3) { 
    managerSearchResults.value = []
    return 
  }
  managerSearchTimeout = setTimeout(async () => {
    searchingManager.value = true
    try {
      const res = await fetch(`${API_BASE}/accounts/search?q=${encodeURIComponent(q)}&limit=5`)
      const data = await res.json()
      managerSearchResults.value = Array.isArray(data) ? data : (data.data || [])
    } catch { 
      managerSearchResults.value = [] 
    }
    searchingManager.value = false
  }, 300)
})

const selectManager = (manager) => {
  general.value.manager = manager.dn || manager.userPrincipalName || manager.username
  selectedManagerName.value = manager.fullName || manager.displayName
  managerSearchQuery.value = ''
  managerSearchResults.value = []
}

const clearManager = () => {
  general.value.manager = ''
  selectedManagerName.value = ''
}


// Búsqueda de Grupos
let groupSearchTimeout = null
watch(groupSearchQuery, (q) => {
  clearTimeout(groupSearchTimeout)
  if (q.length < 2) { groupSearchResults.value = []; return }
  groupSearchTimeout = setTimeout(async () => {
    searchingGroups.value = true
    try {
      const res = await fetch(`${API_BASE}/accounts/groups/search?q=${encodeURIComponent(q)}&limit=10`)
      groupSearchResults.value = await res.json()
    } catch { 
      groupSearchResults.value = [] 
    }
    searchingGroups.value = false
  }, 300)
})

const addGroup = async (group) => {
  try {
    const res = await fetch(`${API_BASE}/accounts/groups/add`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: props.userProfile.username, group_dn: group.dn })
    })
    const data = await res.json()
    if (data.success) {
      if (!groups.value.find(g => g.dn === group.dn)) {
        groups.value.push({ name: group.name, dn: group.dn })
      }
      groupSearchQuery.value = ''
      groupSearchResults.value = []
    } else {
      resultMsg.value = { success: false, text: data.error }
    }
  } catch (e) {
    resultMsg.value = { success: false, text: e.message }
  }
}

const removeGroup = async (group) => {
  try {
    const res = await fetch(`${API_BASE}/accounts/groups/remove`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: props.userProfile.username, group_dn: group.dn })
    })
    const data = await res.json()
    if (data.success) {
      groups.value = groups.value.filter(g => g.dn !== group.dn)
    } else {
      resultMsg.value = { success: false, text: data.error }
    }
  } catch (e) {
    resultMsg.value = { success: false, text: e.message }
  }
}

// Aplicar Cambios
const applyChanges = async () => {
  saving.value = true
  resultMsg.value = null
  try {
    const res1 = await fetch(`${API_BASE}/accounts/profile/bulk-edit`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: props.userProfile.username, updates: general.value })
    })
    const d1 = await res1.json()
    if (!d1.success) throw new Error(d1.error || 'Error al actualizar perfil')

    const upnUpdates = {}
    const finalUpn = `${cuenta.value.upnPrefix}${cuenta.value.upnSuffix}`
    if (finalUpn) upnUpdates.userPrincipalName = finalUpn
    if (cuenta.value.sAMAccountName && cuenta.value.sAMAccountName !== props.userProfile.username) {
      upnUpdates.sAMAccountName = cuenta.value.sAMAccountName
    }
    if (Object.keys(upnUpdates).length > 0) {
      await fetch(`${API_BASE}/accounts/profile/bulk-edit`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: props.userProfile.username, updates: upnUpdates })
      })
    }

    const res3 = await fetch(`${API_BASE}/accounts/account-options`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: props.userProfile.username,
        options: {
          must_change_password: cuenta.value.must_change_password,
          cannot_change_password: cuenta.value.cannot_change_password,
          password_never_expires: cuenta.value.password_never_expires,
          store_reversible_encryption: cuenta.value.store_reversible_encryption,
          account_disabled: cuenta.value.account_disabled,
        }
      })
    })
    const d3 = await res3.json()
    if (!d3.success) throw new Error(d3.error || 'Error al actualizar opciones')

    resultMsg.value = { success: true, text: 'Cambios aplicados correctamente.' }
  } catch (e) {
    resultMsg.value = { success: false, text: e.message }
  }
  saving.value = false
}

const acceptAndClose = async () => {
  await applyChanges()
  if (resultMsg.value?.success) {
    setTimeout(() => {
      emit('saved')
    }, 500)
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/40 backdrop-blur-sm" @click.self="emit('close')">
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
      
      <!-- Cabecera -->
      <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center text-lg font-bold uppercase ring-2 ring-blue-50/50">
            {{ general.givenName.charAt(0) || userProfile.username.charAt(0) }}{{ general.sn.charAt(0) }}
          </div>
          <div>
            <h2 class="text-base font-bold text-slate-800 leading-none">{{ userProfile.fullName }}</h2>
            <p class="text-xs font-medium text-slate-500 mt-1 flex items-center gap-1.5">
              <span class="inline-flex items-center rounded bg-green-50 px-1.5 py-0.5 text-[10px] font-semibold text-green-700 ring-1 ring-inset ring-green-600/20" v-if="!cuenta.account_disabled">Activo</span>
              <span class="inline-flex items-center rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-semibold text-red-700 ring-1 ring-inset ring-red-600/20" v-else>Inactivo</span>
              {{ cuenta.upnPrefix }}{{ cuenta.upnSuffix }}
            </p>
          </div>
        </div>
        <button @click="emit('close')" class="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-full transition-colors">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Contenido Principal -->
      <div class="flex flex-1 overflow-hidden">
        
        <!-- Sidebar Fija con Cero Saltos Visuales -->
        <div class="w-64 bg-slate-50 border-r border-slate-200 p-4 shrink-0 flex flex-col gap-1 overflow-y-auto">
          <button 
            v-for="tab in tabs" 
            :key="tab.id" 
            @click="activeTab = tab.id"
            :class="[
              'flex items-center gap-3 px-4 py-2 rounded-md text-sm font-semibold transition-colors duration-150 w-full text-left h-10',
              activeTab === tab.id 
                ? 'bg-blue-50 text-blue-700' 
                : 'bg-transparent text-slate-600 hover:bg-slate-200/50 hover:text-slate-900'
            ]">
            <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" :d="tab.icon" />
            </svg>
            {{ tab.name }}
          </button>
        </div>

        <!-- Área de Pestañas -->
        <div class="flex-1 p-6 overflow-y-auto bg-white">
          
          <!-- GENERAL -->
          <div v-show="activeTab === 'general'" class="space-y-5 animate-in slide-in-from-right-2 duration-200">
            <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 border-b border-slate-100 pb-1">Identidad</h3>
            
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1">
                <label class="text-xs font-medium text-slate-700">Nombre de pila</label>
                <input v-model="general.givenName" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-medium text-slate-700">Apellidos</label>
                <input v-model="general.sn" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
              <div class="col-span-2 space-y-1">
                <label class="text-xs font-medium text-slate-700">Nombre para mostrar</label>
                <input v-model="general.displayName" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
              <div class="col-span-2 space-y-1">
                <label class="text-xs font-medium text-slate-700">Descripción (Área)</label>
                <input v-model="general.description" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
            </div>

            <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 mt-6 border-b border-slate-100 pb-1">Organización y Contacto</h3>
            <div class="grid grid-cols-2 gap-4">
              <div class="space-y-1">
                <label class="text-xs font-medium text-slate-700">Cargo</label>
                <input v-model="general.title" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-medium text-slate-700">Departamento</label>
                <input v-model="general.department" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
              <div class="col-span-2 space-y-1 relative">
                <label class="text-xs font-medium text-slate-700">Jefe Inmediato</label>
                <div v-if="selectedManagerName" class="flex items-center justify-between border border-slate-300 rounded-md bg-slate-50 px-3 py-1.5">
                  <span class="text-sm font-semibold text-slate-800">{{ selectedManagerName }}</span>
                  <button @click="clearManager" class="text-slate-400 hover:text-red-500" title="Quitar Jefe">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                  </button>
                </div>
                <div v-else>
                  <input v-model="managerSearchQuery" type="text" placeholder="Buscar por nombre..." class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
                  <div v-if="managerSearchQuery.length >= 3" class="absolute left-0 right-0 mt-1 bg-white border border-slate-200 shadow-lg rounded-md overflow-hidden z-10 max-h-48 overflow-y-auto">
                    <div v-if="searchingManager" class="p-2 text-center text-xs text-slate-500">Buscando...</div>
                    <ul v-else-if="managerSearchResults.length > 0">
                      <li v-for="mgr in managerSearchResults" :key="mgr.username || mgr.id" @click="selectManager(mgr)" class="px-3 py-2 hover:bg-blue-50 cursor-pointer text-sm border-b border-slate-50">
                        <div class="font-semibold text-slate-800">{{ mgr.fullName || mgr.displayName }}</div>
                        <div class="text-xs text-slate-500 font-mono truncate">{{ mgr.dn || mgr.userPrincipalName }}</div>
                      </li>
                    </ul>
                    <div v-else class="p-2 text-center text-xs text-slate-500">Sin resultados</div>
                  </div>
                </div>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-medium text-slate-700">Extensión / Teléfono</label>
                <input v-model="general.telephoneNumber" type="text" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
              <div class="space-y-1">
                <label class="text-xs font-medium text-slate-700">Correo electrónico</label>
                <input v-model="general.mail" type="email" class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
              </div>
            </div>
          </div>

          <!-- CUENTA -->
          <div v-show="activeTab === 'cuenta'" class="space-y-6 animate-in slide-in-from-right-2 duration-200">
            <div>
              <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 border-b border-slate-100 pb-1">Inicio de Sesión</h3>
              <div class="space-y-4 mt-3">
                <div class="space-y-1">
                  <label class="text-xs font-medium text-slate-700">Nombre de inicio de sesión de usuario (UPN)</label>
                  <div class="flex gap-2">
                    <input v-model="cuenta.upnPrefix" type="text" class="flex-1 border border-slate-300 rounded-md bg-white text-sm font-mono px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
                    <select v-model="cuenta.upnSuffix" class="w-1/3 border border-slate-300 rounded-md bg-slate-50 text-sm font-mono px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow">
                      <option value="@code.local">@code.local</option>
                      <option value="@local.code">@local.code</option>
                      <option value="@105code.cloud">@105code.cloud</option>
                      <option value="@hogarymoda.com.co">@hogarymoda.com.co</option>
                    </select>
                  </div>
                </div>
                <div class="space-y-1">
                  <label class="text-xs font-medium text-slate-700">Inicio de sesión heredado (Pre-Windows 2000)</label>
                  <div class="flex">
                    <span class="inline-flex items-center px-3 rounded-l-md border border-r-0 border-slate-300 bg-slate-100 text-slate-500 text-sm font-mono font-bold">CODE\</span>
                    <input v-model="cuenta.sAMAccountName" type="text" class="flex-1 w-full px-3 py-1.5 rounded-none rounded-r-md border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"/>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 mt-6 border-b border-slate-100 pb-1">Opciones de la Cuenta</h3>
              <div class="space-y-3 mt-3">
                <label class="flex items-center gap-3 cursor-pointer group">
                  <input type="checkbox" v-model="cuenta.must_change_password" class="w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500 transition-colors"/>
                  <span class="text-sm font-medium text-slate-700 group-hover:text-blue-700 transition-colors">El usuario debe cambiar la contraseña en el siguiente inicio de sesión</span>
                </label>
                <label class="flex items-center gap-3 cursor-pointer group">
                  <input type="checkbox" v-model="cuenta.cannot_change_password" :disabled="cuenta.must_change_password" class="w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500 disabled:opacity-50 transition-colors"/>
                  <span class="text-sm font-medium text-slate-700 group-hover:text-blue-700 transition-colors" :class="{'opacity-50': cuenta.must_change_password}">El usuario no puede cambiar la contraseña</span>
                </label>
                <label class="flex items-center gap-3 cursor-pointer group">
                  <input type="checkbox" v-model="cuenta.password_never_expires" :disabled="cuenta.must_change_password" class="w-4 h-4 rounded text-blue-600 border-slate-300 focus:ring-blue-500 disabled:opacity-50 transition-colors"/>
                  <span class="text-sm font-medium text-slate-700 group-hover:text-blue-700 transition-colors" :class="{'opacity-50': cuenta.must_change_password}">La contraseña nunca expira</span>
                </label>
                
                <div class="pt-3 mt-1 border-t border-slate-100">
                  <label class="flex items-center gap-3 cursor-pointer group">
                    <input type="checkbox" v-model="cuenta.account_disabled" class="w-4 h-4 rounded text-red-600 border-slate-300 focus:ring-red-500 transition-colors"/>
                    <span class="text-sm font-medium text-slate-700 group-hover:text-red-700 transition-colors">La cuenta está deshabilitada</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- MIEMBRO DE -->
          <div v-show="activeTab === 'miembro'" class="space-y-4 animate-in slide-in-from-right-2 duration-200">
            <h3 class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 border-b border-slate-100 pb-1">Grupos Asignados</h3>
            
            <div class="border border-slate-300 rounded-md overflow-hidden bg-white flex flex-col h-64">
              <div class="flex bg-slate-50 border-b border-slate-300">
                <span class="text-xs font-bold text-slate-600 px-3 py-1.5 flex-1 border-r border-slate-300">Nombre del Grupo</span>
                <span class="text-xs font-bold text-slate-600 px-3 py-1.5 flex-1">Ubicación (Distinguished Name)</span>
              </div>
              <div class="flex-1 overflow-y-auto">
                <div v-if="groups.length === 0" class="text-sm text-slate-500 text-center py-10">
                  No pertenece a ningún grupo.
                </div>
                <div v-else v-for="group in groups" :key="group.dn" class="flex border-b border-slate-100 hover:bg-blue-50 group transition-colors">
                  <span class="text-xs font-semibold text-slate-800 px-3 py-2 flex-1 border-r border-slate-100 truncate">{{ group.name }}</span>
                  <span class="text-xs text-slate-500 px-3 py-2 flex-1 font-mono truncate">{{ group.dn }}</span>
                  <button @click="removeGroup(group)" class="opacity-0 group-hover:opacity-100 text-red-600 font-bold text-xs px-3 hover:bg-red-100 transition-colors" title="Quitar">
                    ✕
                  </button>
                </div>
              </div>
            </div>

            <!-- Botones y Buscador -->
            <div class="relative">
              <input 
                v-model="groupSearchQuery" 
                type="text" 
                placeholder="Buscar grupo para añadir..." 
                class="w-full border border-slate-300 rounded-md bg-white text-sm px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-shadow"
              />
              
              <div v-if="groupSearchQuery.length >= 2" class="absolute left-0 right-0 mt-1 bg-white border border-slate-200 shadow-xl rounded-md overflow-hidden z-20">
                <div v-if="searchingGroups" class="p-3 text-center text-xs text-slate-500">
                  Buscando grupos...
                </div>
                <div v-else-if="groupSearchResults.length === 0" class="p-3 text-center text-xs text-slate-500">
                  No se encontraron grupos
                </div>
                <ul v-else class="max-h-48 overflow-y-auto">
                  <li v-for="gr in groupSearchResults" :key="gr.dn" @click="addGroup(gr)" class="px-3 py-2 border-b border-slate-50 hover:bg-blue-50 cursor-pointer transition-colors flex justify-between items-center group/item">
                    <div>
                      <p class="text-sm font-semibold text-slate-800">{{ gr.name }}</p>
                      <p class="text-xs text-slate-400 font-mono truncate max-w-sm">{{ gr.dn }}</p>
                    </div>
                    <span class="text-xs font-bold text-blue-600 bg-white px-2 py-1 rounded border border-blue-200 opacity-0 group-hover/item:opacity-100 transition-opacity">Añadir</span>
                  </li>
                </ul>
              </div>
            </div>
            <p class="text-[11px] text-slate-500">Nota: El grupo "Usuarios del dominio" (Domain Users) es el grupo principal implícito.</p>
          </div>
          
        </div>
      </div>

      <!-- Pie del Modal -->
      <div class="px-6 py-3 bg-slate-50 border-t border-slate-200 shrink-0 flex items-center justify-between rounded-b-xl">
        <div class="flex-1 pr-4">
          <div v-if="resultMsg" class="flex items-center gap-2 animate-in fade-in" :class="resultMsg.success ? 'text-green-600' : 'text-red-600'">
            <span class="text-sm font-medium">{{ resultMsg.text }}</span>
          </div>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <button 
            @click="emit('close')" 
            :disabled="saving"
            class="px-4 py-2 text-sm font-semibold text-slate-600 bg-white border border-slate-300 rounded-md hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
          >
            Cancelar
          </button>
          
          <button 
            @click="applyChanges" 
            :disabled="saving"
            class="px-4 py-2 text-sm font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors disabled:opacity-50"
          >
            Aplicar
          </button>
          
          <button 
            @click="acceptAndClose" 
            :disabled="saving"
            class="px-5 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors shadow-sm disabled:opacity-50 flex items-center gap-2"
          >
            <span v-if="saving" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            {{ saving ? 'Guardando...' : 'Guardar' }}
          </button>
        </div>
      </div>
      
    </div>
  </div>
</template>
