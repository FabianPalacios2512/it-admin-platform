<script setup>
import { ref, onMounted, computed, watch } from 'vue'

const props = defineProps({
  userProfile: { type: Object, required: true },
  accountOptions: { type: Object, default: null }
})

const emit = defineEmits(['close', 'saved'])
const API_BASE = '/api/v1'

// â”€â”€ PestaÃ±as â”€â”€
const activeTab = ref('general')
const tabs = [
  { id: 'general', name: 'General' },
  { id: 'cuenta', name: 'Cuenta' },
  { id: 'miembro', name: 'Miembro de' },
]

// â”€â”€ General â”€â”€
const general = ref({
  givenName: '', initials: '', sn: '', displayName: '',
  description: '', physicalDeliveryOfficeName: '',
  telephoneNumber: '', mail: '',
})

// â”€â”€ Cuenta â”€â”€
const cuenta = ref({
  upnPrefix: '', upnSuffix: '@local.code', sAMAccountName: '',
  must_change_password: false,
  cannot_change_password: false,
  password_never_expires: false,
  store_reversible_encryption: false,
  account_disabled: false,
})

// â”€â”€ Miembro de â”€â”€
const groups = ref([])
const groupSearchQuery = ref('')
const groupSearchResults = ref([])
const searchingGroups = ref(false)

// â”€â”€ Estado global â”€â”€
const saving = ref(false)
const resultMsg = ref(null)

onMounted(() => {
  // General
  general.value = {
    givenName: props.userProfile.firstName || '',
    initials: '',
    sn: props.userProfile.lastName || '',
    displayName: props.userProfile.fullName || '',
    description: props.userProfile.description || '',
    physicalDeliveryOfficeName: props.userProfile.office === 'Sin oficina' ? '' : (props.userProfile.office || ''),
    telephoneNumber: props.userProfile.phone || '',
    mail: props.userProfile.email || '',
  }
  // Cuenta
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
  // Grupos
  if (props.userProfile.groups) {
    groups.value = [...props.userProfile.groups]
  }
})

// â”€â”€ Buscar grupos â”€â”€
let groupSearchTimeout = null
watch(groupSearchQuery, (q) => {
  clearTimeout(groupSearchTimeout)
  if (q.length < 2) { groupSearchResults.value = []; return }
  groupSearchTimeout = setTimeout(async () => {
    searchingGroups.value = true
    try {
      const res = await fetch(`${API_BASE}/accounts/groups/search?q=${encodeURIComponent(q)}&limit=10`)
      groupSearchResults.value = await res.json()
    } catch { groupSearchResults.value = [] }
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
      groups.value.push({ name: group.name, dn: group.dn })
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

// â”€â”€ Aplicar cambios (General + Cuenta) â”€â”€
const applyChanges = async () => {
  saving.value = true
  resultMsg.value = null
  try {
    // 1. Actualizar atributos generales
    const res1 = await fetch(`${API_BASE}/accounts/profile/bulk-edit`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: props.userProfile.username, updates: general.value })
    })
    const d1 = await res1.json()
    if (!d1.success) throw new Error(d1.error || 'Error al actualizar perfil')

    // 2. Actualizar opciones de cuenta (UPN, sAMAccountName, flags)
    // Primero UPN y sAMAccountName si cambiaron
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

    // 3. Actualizar flags UAC
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
  if (resultMsg.value?.success) emit('saved')
}
</script>

<template>
  <div class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 p-4" @click.self="emit('close')">
    <!-- Ventana estilo Windows -->
    <div class="bg-[#f0f0f0] border border-[#a0a0a0] shadow-[4px_4px_12px_rgba(0,0,0,0.35)] w-full max-w-[480px] flex flex-col select-none" style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">

      <!-- Barra de tÃ­tulo -->
      <div class="bg-gradient-to-r from-[#0078d4] to-[#005a9e] px-3 py-1.5 flex items-center justify-between">
        <span class="text-white text-[12px] font-normal tracking-wide">Propiedades: {{ userProfile.fullName }}</span>
        <button @click="emit('close')" class="text-white/80 hover:text-white hover:bg-red-500 px-2 py-0.5 text-[14px] font-bold leading-none transition-colors">Ã—</button>
      </div>

      <!-- PestaÃ±as -->
      <div class="flex border-b border-[#a0a0a0] bg-[#f0f0f0] px-1 pt-1">
        <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id"
          :class="[
            'px-3 py-1.5 text-[11px] border border-b-0 -mb-[1px] transition-none',
            activeTab === tab.id
              ? 'bg-[#f0f0f0] border-[#a0a0a0] text-black font-normal z-10'
              : 'bg-[#d4d0c8] border-[#a0a0a0] text-[#333] hover:bg-[#e8e4dc]'
          ]">
          {{ tab.name }}
        </button>
      </div>

      <!-- Contenido de la pestaÃ±a -->
      <div class="flex-1 bg-[#f0f0f0] overflow-y-auto" style="max-height: 460px;">

        <!-- â•â•â•â•â•â•â•â• GENERAL â•â•â•â•â•â•â•â• -->
        <div v-if="activeTab === 'general'" class="px-4 py-3">
          <!-- Cabecera con icono y nombre -->
          <div class="flex items-center gap-3 mb-4 pb-3 border-b border-[#c0c0c0]">
            <div class="w-10 h-10 bg-[#d4e7f9] border border-[#7fb0dc] flex items-center justify-center rounded-sm">
              <svg class="w-6 h-6 text-[#4a7fb5]" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
            </div>
            <span class="text-[12px] text-black font-normal">{{ userProfile.fullName }}</span>
          </div>

          <!-- Campos del formulario -->
          <div class="space-y-2.5">
            <!-- Nombre de pila + Iniciales -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">Nombre de pila:</label>
              <input v-model="general.givenName" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
              <label class="text-[11px] text-black shrink-0">Iniciales:</label>
              <input v-model="general.initials" type="text" class="w-[50px] border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
            <!-- Apellidos -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">Apellidos:</label>
              <input v-model="general.sn" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
            <!-- Nombre para mostrar -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">Nombre para mostrar:</label>
              <input v-model="general.displayName" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
            <!-- DescripciÃ³n -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">DescripciÃ³n:</label>
              <input v-model="general.description" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
            <!-- Oficina -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">Oficina:</label>
              <input v-model="general.physicalDeliveryOfficeName" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>

            <div class="h-1"></div>

            <!-- NÃºmero de telÃ©fono -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">NÃºmero de telÃ©fono:</label>
              <input v-model="general.telephoneNumber" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
            <!-- Correo electrÃ³nico -->
            <div class="flex gap-3 items-center">
              <label class="text-[11px] text-black w-[115px] text-right shrink-0">Correo electrÃ³nico:</label>
              <input v-model="general.mail" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
          </div>
        </div>

        <!-- â•â•â•â•â•â•â•â• CUENTA â•â•â•â•â•â•â•â• -->
        <div v-else-if="activeTab === 'cuenta'" class="px-4 py-3">
          <!-- UPN -->
          <div class="mb-4">
            <label class="text-[11px] text-black block mb-1">Nombre de inicio de sesiÃ³n de usuario:</label>
            <div class="flex gap-1">
              <input v-model="cuenta.upnPrefix" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
                <select v-model="cuenta.upnSuffix" class="border border-[#7f9db9] bg-white text-[11px] px-1 py-[3px] focus:outline-none focus:border-[#0078d4]">
                  <option value="@code.local">@code.local</option>
                  <option value="@local.code">@local.code</option>
                  <option value="@105code.cloud">@105code.cloud</option>
                </select>
            </div>
          </div>
          <!-- sAMAccountName -->
          <div class="mb-4">
            <label class="text-[11px] text-black block mb-1">Nombre de inicio de sesiÃ³n de usuario (anterior a Windows 2000):</label>
            <div class="flex gap-1 items-center">
              <span class="text-[11px] text-[#555] bg-[#e8e4dc] border border-[#a0a0a0] px-1.5 py-[3px] shrink-0">CODE\</span>
              <input v-model="cuenta.sAMAccountName" type="text" class="flex-1 border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] focus:outline-none focus:border-[#0078d4]"/>
            </div>
          </div>

          <div class="h-1 border-t border-[#c0c0c0] mb-3"></div>

          <!-- Desbloquear -->
          <label class="flex items-center gap-2 mb-3">
            <input type="checkbox" disabled :checked="false" class="w-3.5 h-3.5"/>
            <span class="text-[11px] text-[#888]">Desbloquear cuenta</span>
          </label>

          <!-- Opciones de cuenta -->
          <div class="border border-[#c0c0c0] p-2.5 mb-3">
            <span class="text-[11px] text-black font-normal block mb-2">Opciones de cuenta</span>
            <div class="space-y-1.5">
              <label class="flex items-start gap-2">
                <input type="checkbox" v-model="cuenta.must_change_password" class="w-3.5 h-3.5 mt-0.5 shrink-0"/>
                <span class="text-[11px] text-black">El usuario debe cambiar la contraseÃ±a en el siguiente inicio de sesiÃ³n</span>
              </label>
              <label class="flex items-start gap-2">
                <input type="checkbox" v-model="cuenta.cannot_change_password" class="w-3.5 h-3.5 mt-0.5 shrink-0"/>
                <span class="text-[11px] text-black">El usuario no puede cambiar la contraseÃ±a</span>
              </label>
              <label class="flex items-start gap-2">
                <input type="checkbox" v-model="cuenta.password_never_expires" class="w-3.5 h-3.5 mt-0.5 shrink-0"/>
                <span class="text-[11px] text-black">La contraseÃ±a nunca expira</span>
              </label>
              <label class="flex items-start gap-2">
                <input type="checkbox" v-model="cuenta.store_reversible_encryption" class="w-3.5 h-3.5 mt-0.5 shrink-0"/>
                <span class="text-[11px] text-black">Almacenar contraseÃ±a utilizando cifrado reversible</span>
              </label>
              <label class="flex items-start gap-2">
                <input type="checkbox" v-model="cuenta.account_disabled" class="w-3.5 h-3.5 mt-0.5 shrink-0"/>
                <span class="text-[11px] text-black">La cuenta estÃ¡ deshabilitada</span>
              </label>
            </div>
          </div>
        </div>

        <!-- â•â•â•â•â•â•â•â• MIEMBRO DE â•â•â•â•â•â•â•â• -->
        <div v-else-if="activeTab === 'miembro'" class="px-4 py-3">
          <label class="text-[11px] text-black block mb-1.5">Miembro de:</label>

          <!-- Lista de grupos -->
          <div class="border border-[#7f9db9] bg-white mb-3" style="min-height: 180px; max-height: 220px; overflow-y: auto;">
            <!-- Cabecera -->
            <div class="flex bg-[#e8e4dc] border-b border-[#c0c0c0] sticky top-0">
              <span class="text-[10px] text-black font-normal px-2 py-1 flex-1 border-r border-[#c0c0c0]">Nombre</span>
              <span class="text-[10px] text-black font-normal px-2 py-1 flex-1">Carpeta de los Servicios de dominio de Active Dir...</span>
            </div>
            <!-- Filas -->
            <div v-for="(group, idx) in groups" :key="idx"
              class="flex cursor-default hover:bg-[#316ac5] hover:text-white group border-b border-[#e8e4dc]">
              <span class="text-[10px] px-2 py-[3px] flex-1 border-r border-[#e8e4dc] truncate group-hover:text-white text-black">{{ group.name }}</span>
              <span class="text-[10px] px-2 py-[3px] flex-1 truncate group-hover:text-white text-[#666]">{{ group.dn }}</span>
            </div>
            <div v-if="groups.length === 0" class="text-[10px] text-[#999] text-center py-6">No pertenece a ningÃºn grupo</div>
          </div>

          <!-- Botones Agregar / Quitar -->
          <div class="flex gap-2 mb-4">
            <button @click="groupSearchQuery = groupSearchQuery || ' '" class="border border-[#a0a0a0] bg-[#f0f0f0] hover:bg-[#e0e0e0] active:bg-[#d0d0d0] text-[11px] text-black px-4 py-1 focus:outline-none">
              Agregar...
            </button>
            <button @click="removeGroup(groups.find(g => true))" :disabled="groups.length === 0" class="border border-[#a0a0a0] bg-[#f0f0f0] hover:bg-[#e0e0e0] active:bg-[#d0d0d0] text-[11px] text-black px-4 py-1 disabled:text-[#aaa] disabled:bg-[#e8e4dc] focus:outline-none">
              Quitar
            </button>
          </div>

          <!-- Buscador de grupos (aparece cuando se da en Agregar) -->
          <div v-if="groupSearchQuery !== null && groupSearchQuery !== ''" class="border border-[#c0c0c0] bg-white p-2 mb-2">
            <label class="text-[10px] text-black block mb-1">Buscar grupo:</label>
            <input v-model="groupSearchQuery" type="text" placeholder="Escriba el nombre del grupo..." autofocus
              class="w-full border border-[#7f9db9] bg-white text-[11px] px-1.5 py-[3px] mb-1.5 focus:outline-none focus:border-[#0078d4]"/>
            <div v-if="searchingGroups" class="text-[10px] text-[#888]">Buscando...</div>
            <div v-for="gr in groupSearchResults" :key="gr.dn"
              class="flex items-center justify-between py-1 px-1 hover:bg-[#e8f0fe] cursor-pointer border-b border-[#eee]"
              @click="addGroup(gr)">
              <span class="text-[10px] text-black">{{ gr.name }}</span>
              <span class="text-[9px] text-[#0078d4]">+ Agregar</span>
            </div>
          </div>

          <!-- Grupo principal -->
          <div class="border-t border-[#c0c0c0] pt-2 mt-2">
            <div class="flex items-center gap-2">
              <span class="text-[11px] text-black font-normal">Grupo principal:</span>
              <span class="text-[11px] text-black">Usuarios del dominio</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Resultado -->
      <div v-if="resultMsg" :class="['text-[10px] px-3 py-1.5 border-t', resultMsg.success ? 'bg-[#dff0d8] text-[#3c763d] border-[#b2dba1]' : 'bg-[#f2dede] text-[#a94442] border-[#e4b9b9]']">
        {{ resultMsg.text }}
      </div>

      <!-- Botones de pie (estilo Windows) -->
      <div class="flex justify-end gap-1.5 px-3 py-2.5 border-t border-[#a0a0a0] bg-[#f0f0f0]">
        <button @click="acceptAndClose" :disabled="saving" class="min-w-[75px] border border-[#0054a6] bg-[#e1ecf7] hover:bg-[#cde0f4] active:bg-[#b8d4f0] text-[11px] text-black px-3 py-[4px] focus:outline-1 focus:outline-[#0078d4] disabled:opacity-50">
          {{ saving ? 'Guardando...' : 'Aceptar' }}
        </button>
        <button @click="emit('close')" class="min-w-[75px] border border-[#a0a0a0] bg-[#f0f0f0] hover:bg-[#e0e0e0] active:bg-[#d0d0d0] text-[11px] text-black px-3 py-[4px] focus:outline-1 focus:outline-[#0078d4]">
          Cancelar
        </button>
        <button @click="applyChanges" :disabled="saving" class="min-w-[75px] border border-[#a0a0a0] bg-[#f0f0f0] hover:bg-[#e0e0e0] active:bg-[#d0d0d0] text-[11px] text-black px-3 py-[4px] focus:outline-1 focus:outline-[#0078d4] disabled:opacity-50">
          Aplicar
        </button>
      </div>
    </div>
  </div>
</template>
