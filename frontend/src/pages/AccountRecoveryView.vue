<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const API_BASE = '/api/v1'
const blockedUsers = ref([])
const isLoading = ref(true)
const searchQuery = ref('')
const selectedUsername = ref(null)
let refreshInterval = null

// Reseteo de contraseña
const showPasswordResetModal = ref(false)
const mustChangePassword = ref(true)
const generatedPassword = ref('')
const resetLoading = ref(false)
const resetResult = ref(null)

// Desbloqueo
const unlockLoading = ref(false)
const unlockResult = ref(null)

async function fetchLockedAccounts() {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/accounts/locked`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      blockedUsers.value = await res.json()
      // Si el usuario seleccionado ya no está bloqueado, deseleccionar
      if (selectedUsername.value && !blockedUsers.value.find(u => u.username === selectedUsername.value)) {
        selectedUsername.value = null
      }
    }
  } catch (err) {
    console.error('Error cargando cuentas bloqueadas:', err)
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  await fetchLockedAccounts()
  // Refrescar cada 15 segundos
  refreshInterval = setInterval(fetchLockedAccounts, 15000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

const filteredUsers = computed(() => {
  if (!searchQuery.value) return blockedUsers.value
  const q = searchQuery.value.toLowerCase()
  return blockedUsers.value.filter(
    u => u.fullName.toLowerCase().includes(q) || u.username.toLowerCase().includes(q)
  )
})

const selectedUser = computed(() =>
  blockedUsers.value.find(u => u.username === selectedUsername.value) || null
)

const dataFields = computed(() => {
  if (!selectedUser.value) return []
  const u = selectedUser.value
  return [
    { label: 'sAMAccountName',     value: u.username, mono: true },
    { label: 'Correo',             value: u.email || 'Sin correo' },
    { label: 'Departamento',       value: u.department || 'Sin departamento' },
    { label: 'Responsable',        value: u.manager || 'No asignado' },
    { label: 'Intentos fallidos',  value: u.badPwdCount, highlight: true },
    { label: 'Bloqueado desde',    value: u.lockoutTime },
    { label: 'Último inicio',      value: u.lastLogon || 'N/A' },
    { label: 'distinguishedName',  value: u.distinguishedName, mono: true, full: true },
  ]
})

const flagLabels = {
  PASSWORD_NEVER_EXPIRES: 'Contraseña nunca expira',
  MUST_CHANGE_PASSWORD:   'Debe cambiar la clave',
  ACCOUNT_DISABLED:       'Cuenta deshabilitada',
  LOCKOUT:                'Bloqueo activo',
  NORMAL_ACCOUNT:         'Cuenta normal',
}

function selectUser(username) {
  selectedUsername.value = username
  showPasswordResetModal.value = false
  unlockResult.value = null
}

function regeneratePassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@$#'
  let pwd = ''
  for (let i = 0; i < 14; i++) pwd += chars.charAt(Math.floor(Math.random() * chars.length))
  generatedPassword.value = pwd
}

function openPasswordReset() {
  regeneratePassword()
  resetResult.value = null
  showPasswordResetModal.value = true
}

function closePasswordReset() {
  showPasswordResetModal.value = false
}

async function executePasswordReset() {
  resetLoading.value = true
  resetResult.value = null
  try {
    const token = localStorage.getItem('access_token')
    const adminUser = localStorage.getItem('display_name') || 'Admin'
    const res = await fetch(`${API_BASE}/accounts/reset-password`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({
        username: selectedUser.value.username,
        new_password: generatedPassword.value,
        must_change: mustChangePassword.value,
        admin_user: adminUser,
      })
    })
    const data = await res.json()
    resetResult.value = data
  } catch (err) {
    resetResult.value = { success: false, error: err.message }
  } finally {
    resetLoading.value = false
  }
}

async function executeUnlock() {
  unlockLoading.value = true
  unlockResult.value = null
  try {
    const token = localStorage.getItem('access_token')
    const adminUser = localStorage.getItem('display_name') || 'Admin'
    const res = await fetch(`${API_BASE}/accounts/unlock`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}` 
      },
      body: JSON.stringify({
        username: selectedUser.value.username,
        admin_user: adminUser,
      })
    })
    const data = await res.json()
    unlockResult.value = data
    if (data.success) {
      // Refrescar la lista inmediatamente
      await fetchLockedAccounts()
    }
  } catch (err) {
    unlockResult.value = { success: false, error: err.message }
  } finally {
    unlockLoading.value = false
  }
}
</script>

<template>
  <div class="relative">
    <!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
    <!-- Modal Técnico sin Overlay          -->
    <!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
    <div
      v-if="showPasswordResetModal"
      class="fixed top-20 left-1/2 -translate-x-1/2 w-[28rem] bg-white border border-slate-300 shadow-xl rounded-sm z-50 flex flex-col"
    >
      <div class="flex items-center justify-between px-4 py-2 border-b border-slate-200 bg-slate-50">
        <span class="text-[12px] font-semibold text-slate-800">Restablecer contraseña â€” {{ selectedUser?.username }}</span>
        <button @click="closePasswordReset" class="text-slate-400 hover:text-slate-700 transition-colors">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="p-5 flex flex-col gap-4">
        <div>
          <label class="block text-[11px] font-semibold text-slate-500 mb-1">Nueva contraseña temporal</label>
          <div class="flex gap-2">
            <input
              type="text"
              readonly
              v-model="generatedPassword"
              class="flex-1 bg-slate-50 border border-slate-200 rounded-sm text-[13px] text-slate-800 font-mono px-3 py-1.5 focus:outline-none"
            />
            <button
              @click="regeneratePassword"
              title="Generar nueva contraseña"
              class="flex items-center justify-center w-8 h-8 bg-white border border-slate-300 hover:bg-slate-50 rounded-sm transition-colors shrink-0"
            >
              <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
        
        <label class="flex items-start gap-2 cursor-pointer group">
          <input
            type="checkbox"
            v-model="mustChangePassword"
            class="mt-0.5 w-3.5 h-3.5 rounded-sm border-slate-300 text-slate-800 focus:ring-slate-500 focus:ring-offset-0 cursor-pointer"
          />
          <div>
            <span class="text-[12px] text-slate-700 font-medium group-hover:text-slate-900 transition-colors">
              El usuario debe cambiar la contraseña en el siguiente inicio de sesión
            </span>
          </div>
        </label>

        <!-- Resultado del reset -->
        <div v-if="resetResult" :class="['text-[12px] px-3 py-2 rounded-sm border', resetResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
          {{ resetResult.success ? resetResult.message : resetResult.error }}
        </div>
      </div>
      <div class="flex justify-end px-4 py-3 border-t border-slate-200 bg-slate-50 gap-2">
        <button @click="closePasswordReset" class="text-[12px] font-medium text-slate-600 hover:text-slate-800 px-3 py-1.5">
          Cancelar
        </button>
        <button 
          @click="executePasswordReset"
          :disabled="resetLoading"
          class="text-[12px] font-medium text-white bg-slate-800 hover:bg-slate-900 rounded-sm px-4 py-1.5 transition-colors disabled:opacity-50"
        >
          {{ resetLoading ? 'Ejecutando...' : 'Ejecutar' }}
        </button>
      </div>
    </div>

    <!-- Breadcrumb -->
    <div class="mb-5">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <router-link to="/cuentas" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Cuentas AD</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600">Recuperación de cuentas</span>
      </div>
      <h2 class="text-base font-semibold text-slate-800">Cuentas bloqueadas</h2>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-20">
      <div class="inline-block w-8 h-8 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin"></div>
      <span class="text-sm text-slate-500 ml-3">Consultando cuentas bloqueadas en el Directorio Activo...</span>
    </div>

    <!-- Sin cuentas bloqueadas -->
    <div v-else-if="blockedUsers.length === 0" class="bg-white border border-slate-200 rounded-sm p-12 text-center">
      <svg class="w-12 h-12 text-emerald-400 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
      <h3 class="text-sm font-semibold text-slate-800 mb-1">¡Sin cuentas bloqueadas!</h3>
      <p class="text-[12px] text-slate-400">No se detectaron cuentas bloqueadas en el Directorio Activo en este momento.</p>
      <p class="text-[11px] text-slate-300 mt-2">Se actualiza automáticamente cada 15 segundos</p>
    </div>

    <!-- Layout: sidebar estrecho + panel principal -->
    <div v-else class="flex flex-col lg:flex-row gap-5">

      <!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
      <!-- Columna izquierda â€” w-80 fijo     -->
      <!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
      <div class="w-full lg:w-80 shrink-0">
        <div class="bg-white border border-slate-200 rounded-sm overflow-hidden flex flex-col h-auto lg:h-[calc(100vh-12rem)]">

          <!-- Búsqueda -->
          <div class="p-3 border-b border-slate-200">
            <div class="relative">
              <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Buscar cuenta..."
                class="w-full pl-8 pr-3 py-1.5 text-[11px] bg-white border border-slate-200 rounded-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 focus:border-slate-400"
              />
            </div>
          </div>

          <!-- Lista -->
          <div class="flex-1 overflow-y-auto">
            <button
              v-for="user in filteredUsers"
              :key="user.username"
              @click="selectUser(user.username)"
              :class="[
                'w-full text-left px-4 py-3 transition-colors',
                selectedUsername === user.username
                  ? 'bg-slate-50'
                  : 'hover:bg-slate-50/60'
              ]"
            >
              <p class="text-[13px] font-semibold text-slate-800 leading-tight">{{ user.fullName }}</p>
              <p class="text-[11px] text-slate-500 font-mono mt-0.5">{{ user.username }}</p>
              <p class="text-[11px] text-red-700 mt-1">Bloqueado: {{ user.lockoutTime }}</p>
            </button>

            <div v-if="filteredUsers.length === 0 && blockedUsers.length > 0" class="px-4 py-10 text-center">
              <p class="text-[11px] text-slate-400">Sin resultados.</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="px-4 py-2 border-t border-slate-200">
            <p class="text-[10px] text-slate-400">{{ blockedUsers.length }} cuentas bloqueadas â€¢ Actualización en vivo</p>
          </div>
        </div>
      </div>

      <!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
      <!-- Panel derecho â€” ocupa el resto         -->
      <!-- â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• -->
      <div class="flex-1 min-w-0">
        <div class="bg-white border border-slate-200 rounded-sm overflow-hidden flex flex-col h-auto lg:h-[calc(100vh-12rem)]">

          <!-- Header -->
          <div class="px-6 py-4 border-b border-slate-200 shrink-0">
            <template v-if="selectedUser">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-sm font-semibold text-slate-800">{{ selectedUser.fullName }}</h3>
                  <p class="text-[11px] text-slate-500 font-mono mt-0.5">{{ selectedUser.username }}</p>
                </div>
                <p class="text-[11px] text-red-700 hidden sm:block">Bloqueado: {{ selectedUser.lockoutTime }}</p>
              </div>
            </template>
            <p v-else class="text-sm text-slate-400">Selecciona una cuenta para ver los detalles.</p>
          </div>

          <!-- Cuerpo -->
          <div v-if="selectedUser" class="flex-1 overflow-y-auto">

            <!-- Atributos -->
            <div class="px-6 py-5">
              <p class="text-[11px] text-slate-400 font-medium mb-3">Atributos de la cuenta</p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-10">
                <div
                  v-for="(field, i) in dataFields"
                  :key="i"
                  :class="['py-2 border-b border-slate-100', field.full ? 'sm:col-span-2' : '']"
                >
                  <p class="text-[11px] text-slate-500">{{ field.label }}</p>
                  <p
                    :class="[
                      'text-[12px] mt-0.5',
                      field.mono ? 'font-mono text-slate-600 break-all text-[11px]' : '',
                      field.highlight ? 'font-semibold text-red-700' : 'text-slate-800',
                    ]"
                  >{{ field.value }}</p>
                </div>
              </div>
            </div>

            <!-- Flags de seguridad -->
            <div class="px-6 pb-5">
              <p class="text-[11px] text-slate-400 font-medium mb-2.5">
                Atributos de seguridad
                <span class="text-slate-300 font-mono ml-1">userAccountControl</span>
              </p>
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="flag in selectedUser.flags"
                  :key="flag"
                  :class="[
                    'text-[11px] border rounded-sm px-2 py-0.5',
                    flag === 'LOCKOUT' || flag === 'ACCOUNT_DISABLED' 
                      ? 'text-red-700 bg-red-50 border-red-200' 
                      : 'text-slate-700 bg-slate-100 border-slate-200'
                  ]"
                >
                  {{ flagLabels[flag] || flag }}
                </span>
              </div>
            </div>

            <!-- Resultado de desbloqueo -->
            <div v-if="unlockResult" class="px-6 pb-4">
              <div :class="['text-[12px] px-3 py-2 rounded-sm border', unlockResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
                {{ unlockResult.success ? unlockResult.message : unlockResult.error }}
              </div>
            </div>

            <!-- Separador -->
            <div class="border-t border-slate-200"></div>

            <!-- Acciones -->
            <div class="px-6 py-4 flex items-center justify-end gap-2">
              <button
                @click="openPasswordReset"
                class="text-[12px] font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-1.5 transition-colors"
              >
                Restablecer contraseña
              </button>
              <button 
                @click="executeUnlock"
                :disabled="unlockLoading"
                class="text-[12px] font-medium text-white bg-slate-800 hover:bg-slate-900 rounded-sm px-4 py-1.5 transition-colors disabled:opacity-50"
              >
                {{ unlockLoading ? 'Desbloqueando...' : 'Desbloquear cuenta' }}
              </button>
            </div>
          </div>

          <!-- Estado vacío -->
          <div v-else class="flex-1 flex items-center justify-center">
            <div class="text-center">
              <p class="text-xs text-slate-400">Selecciona una cuenta de la lista</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
