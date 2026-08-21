<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import BaseModal from '../components/common/BaseModal.vue'
import EditProfileModal from '../components/EditProfileModal.vue'

const router = useRouter()
const route = useRoute()
const API_BASE = '/api/v1'

const userProfile    = ref(null)
const accountOptions = ref(null)
const allAttributes  = ref([])
const folderGroups   = ref([])
const isLoading      = ref(true)
const error          = ref(null)
const activeTab      = ref('general')
const showEditModal  = ref(false)

// â”€â”€ Modal contraseña â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const showPasswordModal  = ref(false)
const mustChangePassword = ref(true)
const unlockOnReset      = ref(false)
const generatedPassword  = ref('')
const confirmPassword    = ref('')
const confirmError       = ref('')
const resetLoading       = ref(false)
const resetResult        = ref(null)

const foldersLoading = ref(false)
const expandedFolders = ref(new Set())

// â”€â”€ Desbloqueo directo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const unlockLoading = ref(false)
const unlockResult  = ref(null)

// â”€â”€ Opciones de cuenta â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const optionsSaving  = ref(false)
const optionsResult  = ref(null)
const localOptions   = ref({})

// â”€â”€ Editor de atributos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const attrFilter       = ref('')
const editingAttr      = ref(null)   // { name, value }
const editingValue     = ref('')
const attrSaving       = ref(false)
const attrResult       = ref(null)
const showOnlySet      = ref(false)

const tabs = [
  { id: 'general',   name: 'General',           icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  { id: 'account',   name: 'Cuenta',             icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
  { id: 'groups',    name: 'Miembro de',         icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z' },
  { id: 'attributes',name: 'Editor de atributos',icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
  { id: 'folders',   name: 'Carpetas asignadas', icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z' },
  { id: 'licenses',  name: 'Licencias Microsoft 365', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
  { id: 'alias',     name: 'Alias de Correo (ProxyAddresses)', icon: 'M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207' },
  { id: 'email-delegation', name: 'Correo (Delegación)', icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' },
  { id: 'entra',     name: 'Nube (Entra ID)',                  icon: 'M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z' }
]

const filteredTabs = computed(() => {
  if (userProfile.value?.isCloudOnly) {
    return tabs.filter(t => ['general', 'account', 'licenses', 'entra', 'email-delegation'].includes(t.id))
  }
  return tabs
})

import { getFriendlyLicenseName } from '@/utils/licenses'

// --- Licencias ---
const availableLicenses = ref([])
const userLicenses = ref([])
const selectedSku = ref('')
const assigningLicense = ref(false)
const fetchingLicenses = ref(false)

const getLicenseName = (skuId, skuPartNumber) => {
  return getFriendlyLicenseName(skuPartNumber)
}



async function fetchLicenses() {
  fetchingLicenses.value = true
  try {
    const promises = [
      authFetch('/api/v1/graph/licenses').then(res => res.ok ? res.json() : [])
    ]
    
    if (userProfile.value?.username) {
      promises.push(
        authFetch(`/api/v1/graph/licenses/${userProfile.value.username}`).then(res => res.ok ? res.json() : null)
      )
    }

    const [allLicensesData, userLicensesData] = await Promise.all(promises)
    
    availableLicenses.value = allLicensesData || []
    
    if (userLicensesData && userLicensesData.success) {
      userLicenses.value = userLicensesData.data || []
    }
  } catch (e) {
    console.error("Error fetching licenses:", e)
  } finally {
    fetchingLicenses.value = false
  }
}

async function assignLicense() {
  if (!selectedSku.value) return
  assigningLicense.value = true
  try {
    const username = userProfile.value.username
    const res = await authFetch('/api/v1/graph/licenses/assign', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, sku_id: selectedSku.value })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      const selectedObj = availableLicenses.value.find(l => l.skuId === selectedSku.value)
      const skuName = getLicenseName(selectedSku.value, selectedObj ? selectedObj.skuPartNumber : '')
      alert(`Licencia asignada: ${skuName}`)
      selectedSku.value = ''
      fetchLicenses()
    } else {
      alert("Error al asignar: " + (data.detail || "Error desconocido"))
    }
  } catch (e) {
    console.error("Error de red:", e)
    alert("Error de red al asignar licencia.")
  } finally {
    assigningLicense.value = false
  }
}

const removingLicense = ref(null)
async function removeLicense(skuId) {
  if (!confirm('¿Estás seguro de quitar esta licencia al usuario?')) return
  removingLicense.value = skuId
  try {
    const username = userProfile.value.username
    const res = await authFetch('/api/v1/graph/licenses/remove', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, sku_id: skuId })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      alert(`Licencia removida correctamente`)
      fetchLicenses()
    } else {
      alert("Error al remover: " + (data.detail || "Error desconocido"))
    }
  } catch (e) {
    console.error("Error de red:", e)
    alert("Error de red al remover licencia.")
  } finally {
    removingLicense.value = null
  }
}

const token = localStorage.getItem('access_token')
const adminUser = localStorage.getItem('display_name') || 'Admin'

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

// â”€â”€ Gestión de Alias â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const newAlias = ref('')
const newAliasPrefix = ref('smtp:')
const aliasLoading = ref(false)
const aliasStatus = ref('')

// â”€â”€ Gestión de Correo (Delegación) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const emailDelegates = ref([])
const loadingDelegates = ref(false)
const delegateSearch = ref('')
const selectedDelegatePermission = ref('SendAs')
const isAssigningDelegate = ref(false)

const delegateSuggestions = ref([])
const showDelegateSuggestions = ref(false)
let delegateSuggestTimeout = null

watch(delegateSearch, (newVal) => {
  clearTimeout(delegateSuggestTimeout)
  if (!newVal || newVal.length < 3) {
    delegateSuggestions.value = []
    showDelegateSuggestions.value = false
    return
  }
  delegateSuggestTimeout = setTimeout(async () => {
    try {
      const res = await authFetch(`${API_BASE}/accounts/search?q=${encodeURIComponent(newVal)}&limit=10`)
      if (res.ok) {
        delegateSuggestions.value = await res.json()
        showDelegateSuggestions.value = delegateSuggestions.value.length > 0
      }
    } catch(e) {}
  }, 300)
})

function selectDelegateSuggestion(user) {
  delegateSearch.value = user.userPrincipalName || user.username
  showDelegateSuggestions.value = false
}

function hideDelegateSuggestions() {
  setTimeout(() => {
    showDelegateSuggestions.value = false
  }, 200)
}

async function fetchDelegates() {
  if (!userProfile.value?.username) return
  loadingDelegates.value = true
  try {
    const res = await authFetch(`/api/v1/exchange/${userProfile.value.username}/delegates`)
    if (res.ok) {
      const data = await res.json()
      emailDelegates.value = data.data || []
    }
  } catch (e) {
    console.error("Error al cargar delegados:", e)
  } finally {
    loadingDelegates.value = false
  }
}

async function assignDelegate() {
  if (!delegateSearch.value) return
  isAssigningDelegate.value = true
  try {
    const res = await authFetch(`/api/v1/exchange/${userProfile.value.username}/delegates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delegate: delegateSearch.value, permission: selectedDelegatePermission.value })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      alert("Permiso de correo asignado exitosamente")
      delegateSearch.value = ''
      fetchDelegates()
    } else {
      alert("Error: " + (data.detail || data.error || "Desconocido"))
    }
  } catch (e) {
    alert("Error de red al asignar permiso")
  } finally {
    isAssigningDelegate.value = false
  }
}

async function removeDelegate(delegateUser, permission) {
  if (!confirm(`¿Remover permiso de ${permission} a ${delegateUser}?`)) return
  try {
    const res = await authFetch(`/api/v1/exchange/${userProfile.value.username}/delegates`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delegate: delegateUser, permission: permission })
    })
    if (res.ok) {
      fetchDelegates()
    } else {
      alert("Error al remover permiso")
    }
  } catch (e) {
    alert("Error de red al remover permiso")
  }
}

async function addAlias() {
  if (!newAlias.value.trim()) return
  aliasLoading.value = true
  aliasStatus.value = ''
  try {
    const res = await authFetch(`${API_BASE}/accounts/proxy-addresses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: userProfile.value.username, alias: newAliasPrefix.value + newAlias.value.trim(), action: 'add', admin_user: adminUser })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      newAlias.value = ''
      aliasStatus.value = "Alias agregado y sincronización iniciada."
      const r = await authFetch(`${API_BASE}/accounts/profile/${userProfile.value.username}`)
      if (r.ok) userProfile.value = await r.json()
    } else {
      aliasStatus.value = `Error: ${data.detail || data.error}`
    }
  } catch (e) {
    aliasStatus.value = `Error de red: ${e.message}`
  } finally {
    aliasLoading.value = false
    setTimeout(() => { aliasStatus.value = '' }, 5000)
  }
}

async function removeAlias(alias) {
  if (!confirm(`¿Eliminar alias ${alias}?`)) return
  aliasLoading.value = true
  aliasStatus.value = ''
  try {
    const res = await authFetch(`${API_BASE}/accounts/proxy-addresses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: userProfile.value.username, alias: alias, action: 'remove', admin_user: adminUser })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      aliasStatus.value = "Alias eliminado y sincronización iniciada."
      const r = await authFetch(`${API_BASE}/accounts/profile/${userProfile.value.username}`)
      if (r.ok) userProfile.value = await r.json()
    } else {
      aliasStatus.value = `Error: ${data.detail || data.error}`
    }
  } catch (e) {
    aliasStatus.value = `Error de red: ${e.message}`
  } finally {
    aliasLoading.value = false
    setTimeout(() => { aliasStatus.value = '' }, 5000)
  }
}

// ── Gestión de Grupos M365 ──────────────────────────────────────────────────
const allM365Groups = ref([])
const userM365Groups = ref([])
const selectedM365Group = ref('')
const m365GroupLoading = ref(false)
const isFetchingDevices = ref(false)
const userDevices = ref([])
const isSyncingAd = ref(false)
const userMailbox = ref({})
const userEntraStatus = ref(null)
const entraStatusLoading = ref(false)
const showSyncModal = ref(false)
const syncModalTitle = ref('')
const syncModalMessage = ref('')
const syncModalType = ref('success')

async function syncLocalAD() {
  isSyncingAd.value = true
  try {
    const res = await authFetch(`${API_BASE}/graph/sync-ad`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: userProfile.value.username })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      addNotification({
        type: 'info',
        title: 'Sincronización Iniciada',
        message: 'La tarea de sincronización de Entra ID se ha iniciado en segundo plano. Te avisaremos cuando termine.'
      })
    } else {
      addNotification({
        type: 'error',
        title: 'Error de Sincronización',
        message: data.detail || data.error || 'Fallo al iniciar sincronización'
      })
    }
  } catch (e) {
    addNotification({ type: 'error', title: 'Error de Conexión', message: "Error de red: " + e.message })
  } finally {
    isSyncingAd.value = false
  }
}

async function fetchM365Groups() {
  m365GroupLoading.value = true
  try {
    const resAll = await authFetch(`${API_BASE}/groups/`)
    if (resAll.ok) {
      allM365Groups.value = await resAll.json()
    }
    const resUser = await authFetch(`${API_BASE}/groups/user/${userProfile.value.username}`)
    if (resUser.ok) {
      const data = await resUser.json()
      if (data.success) userM365Groups.value = data.data
    }
  } catch (e) {
    console.error("Error cargando grupos M365", e)
  } finally {
    m365GroupLoading.value = false
  }
}

async function addM365Group() {
  if (!selectedM365Group.value) return
  m365GroupLoading.value = true
  try {
    const res = await authFetch(`${API_BASE}/groups/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: userProfile.value.username, group_id: selectedM365Group.value })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      alert("Agregado al grupo M365.")
      selectedM365Group.value = ''
      await fetchM365Groups()
    } else {
      alert(`Error: ${data.detail || data.message || 'Error al agregar'}`)
    }
  } catch (e) {
    alert("Error de red: " + e.message)
  } finally {
    m365GroupLoading.value = false
  }
}

async function removeM365Group(groupId, groupName) {
  if (!confirm(`¿Remover al usuario del grupo ${groupName}?`)) return
  m365GroupLoading.value = true
  try {
    const res = await authFetch(`${API_BASE}/groups/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: userProfile.value.username, group_id: groupId })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      alert("Usuario removido del grupo M365.")
      await fetchM365Groups()
    } else {
      alert(`Error: ${data.detail || data.message || 'Error al remover'}`)
    }
  } catch (e) {
    alert("Error de red: " + e.message)
  } finally {
    m365GroupLoading.value = false
  }
}

// ── Offboarding Automático ──────────────────────────────────────────────────
const showOffboardModal = ref(false)
const offboardLoading = ref(false)
const offboardResult = ref(null)

async function offboardUser() {
  offboardLoading.value = true
  offboardResult.value = null
  try {
    const res = await authFetch(`${API_BASE}/accounts/offboard/${userProfile.value.username}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_user: adminUser })
    })
    const data = await res.json()
    if (res.ok) {
      offboardResult.value = data
      // Recargar perfil para reflejar cuenta deshabilitada
      const profileRes = await authFetch(`${API_BASE}/accounts/profile/${userProfile.value.username}`)
      if (profileRes.ok) userProfile.value = await profileRes.json()
    } else {
      offboardResult.value = { success: false, message: data.detail || 'Error en baja' }
    }
  } catch (e) {
    offboardResult.value = { success: false, message: 'Error de red: ' + e.message }
  } finally {
    offboardLoading.value = false
  }
}

// ── MFA y Sesiones ──────────────────────────────────────────────────────────
const resetMfaLoading = ref(false)
const revokeLoading = ref(false)

async function resetMFA() {
  if (!confirm(`¿Estás seguro de que deseas restablecer los métodos MFA para ${userProfile.value.username}?`)) return
  resetMfaLoading.value = true
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${userProfile.value.username}/reset-mfa`, { method: 'POST' })
    const data = await res.json()
    alert(res.ok ? data.message : `Error: ${data.detail || data.message}`)
  } catch(e) {
    alert("Error de red: " + e.message)
  } finally {
    resetMfaLoading.value = false
  }
}

async function revokeSessions() {
  if (!confirm(`¿Deseas cerrar todas las sesiones activas en la nube para ${userProfile.value.username}?`)) return
  revokeLoading.value = true
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${userProfile.value.username}/revoke-sessions`, { method: 'POST' })
    const data = await res.json()
    if (res.ok && data.success) {
      addNotification({
        type: 'info',
        title: 'Revocación Iniciada',
        message: `Se ha iniciado el cierre de sesiones para ${userProfile.value.username} en segundo plano.`
      })
    } else {
      addNotification({
        type: 'error',
        title: 'Error',
        message: data.detail || data.message || 'Error al iniciar revocación'
      })
    }
  } catch(e) {
    addNotification({ type: 'error', title: 'Error de Red', message: e.message })
  } finally {
    revokeLoading.value = false
  }
}

// ── Vista 360 (Hardware y Mailbox) ──────────────────────────────────

// ── Carga inicial ──────────────────────────────────────────────────
async function fetchUserProfile() {
  const username = route.params.username
  const profileRes = await authFetch(`${API_BASE}/accounts/profile/${username}`)
  if (profileRes.ok) {
    userProfile.value = await profileRes.json()
  }
}

onMounted(async () => {
  const username = route.params.username
  try {
    // 1. Carga Rápida (Directorio Activo Local)
    const [profileRes, optsRes] = await Promise.all([
      authFetch(`${API_BASE}/accounts/profile/${username}`),
      authFetch(`${API_BASE}/accounts/account-options/${username}`)
    ])

    if (profileRes.ok) {
      userProfile.value = await profileRes.json()
    } else {
      error.value = `Usuario '${username}' no encontrado en el Directorio Activo.`
    }

    if (optsRes.ok) {
      accountOptions.value = await optsRes.json()
      localOptions.value = { ...accountOptions.value }
    }

    if (userProfile.value?.status === 'locked') unlockOnReset.value = true

    // 2. Desbloquear la vista inmediatamente para que el usuario pueda interactuar
    isLoading.value = false

    // Carga asíncrona del estado de Entra para mostrar en General (AD Connect)
    loadUserEntraStatus(username)

    // No cargamos Dispositivos aquí para no bloquear el sistema.
    // Se cargarán "Lazy" (perezosamente) cuando el usuario haga clic en sus pestañas.

  } catch (err) {
    error.value = `Error de conexión: ${err.message}`
    isLoading.value = false
  }
})

async function loadUserEntraStatus(username) {
  if (userEntraStatus.value) return
  userEntraStatus.value = { loading: true }
  
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${username}/entra-status`)
    if (res.ok) {
      const e = await res.json()
      if (e.success) userEntraStatus.value = e.data
      else userEntraStatus.value = { error: e.error || 'No encontrado en Entra ID' }
    } else if (res.status === 404) {
      userEntraStatus.value = { notSynced: true }
    } else {
      try {
        const err = await res.json()
        userEntraStatus.value = { error: err.detail || 'Error en Graph API' }
      } catch {
        userEntraStatus.value = { error: `Error HTTP ${res.status}` }
      }
    }
  } catch (err) {
    console.error("Error cargando estado de Entra:", err)
    userEntraStatus.value = { notSynced: true }
  }
}

// Carga perezosa de atributos y carpetas y Entra ID
watch(activeTab, async (tab) => {
  const username = route.params.username
  if (tab === 'attributes' && allAttributes.value.length === 0) {
    const res = await authFetch(`${API_BASE}/accounts/attributes/${username}`)
    if (res.ok) allAttributes.value = await res.json()
  }

  if (tab === 'entra') {
    // mailbox y devices se cargan lazy en la pestaña entra
    authFetch(`${API_BASE}/graph/users/${username}/mailbox`)
      .then(async (res) => {
        if (res.ok) {
          const m = await res.json()
          if (m.success) userMailbox.value = m.data
        } else {
          try {
            const err = await res.json()
            userMailbox.value = { error: err.detail || 'Error cargando buzón' }
          } catch {
            userMailbox.value = { error: `Error HTTP ${res.status}` }
          }
        }
      }).catch(err => console.error("Error cargando buzón:", err))

    authFetch(`${API_BASE}/graph/users/${username}/devices`)
      .then(async (res) => {
        if (res.ok) {
          const d = await res.json()
          if (d.success) userDevices.value = d.data
        }
      }).catch(err => console.error("Error cargando dispositivos:", err))
  }
  if (tab === 'folders' && folderGroups.value.length === 0) {
    loadFolderGroups()
  }
  if (tab === 'licenses') {
    fetchLicenses()
  }
  if (tab === 'groups') {
    fetchM365Groups()
  }
  if (tab === 'email-delegation') {
    fetchDelegates()
  }
})

async function refreshCurrentView() {
  fetchUserProfile()
  if (activeTab.value === 'attributes') {
    const username = route.params.username
    const res = await authFetch(`${API_BASE}/accounts/attributes/${username}`)
    if (res.ok) allAttributes.value = await res.json()
  }
  if (activeTab.value === 'entra') {
    loadUserEntraStatus()
    // mailbox y devices
  }
  if (activeTab.value === 'folders') loadFolderGroups()
  if (activeTab.value === 'licenses') fetchLicenses()
  if (activeTab.value === 'groups') fetchM365Groups()
  if (activeTab.value === 'email-delegation') fetchDelegates()
}

function goBack() { router.push('/cuentas') }

// ── Contraseña ───────────────────────────────────────
function generateSecurePassword() {
  const u = 'ABCDEFGHJKLMNPQRSTUVWXYZ', l = 'abcdefghjkmnpqrstuvwxyz', d = '23456789', s = '!@#$%&*'
  let pwd = u[~~(Math.random()*u.length)] + l[~~(Math.random()*l.length)] + d[~~(Math.random()*d.length)] + s[~~(Math.random()*s.length)]
  const all = u+l+d+s
  for (let i=0;i<10;i++) pwd += all[~~(Math.random()*all.length)]
  return pwd.split('').sort(()=>Math.random()-.5).join('')
}

function openPasswordModal() {
  generatedPassword.value = ''
  confirmPassword.value = ''
  confirmError.value = ''
  resetResult.value = null
  mustChangePassword.value = true
  unlockOnReset.value = userProfile.value?.status === 'locked'
  showPasswordModal.value = true
}
function closePasswordModal() { showPasswordModal.value = false }

async function executePasswordReset() {
  if (confirmPassword.value !== generatedPassword.value) { confirmError.value = 'Las contraseñas no coinciden.'; return }
  confirmError.value = ''
  resetLoading.value = true
  resetResult.value = null
  try {
    if (unlockOnReset.value && userProfile.value.status === 'locked') {
      await authFetch(`${API_BASE}/accounts/unlock`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ username: userProfile.value.username, admin_user: adminUser }) })
    }
    const res = await authFetch(`${API_BASE}/accounts/reset-password`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ username: userProfile.value.username, new_password: generatedPassword.value, must_change: mustChangePassword.value, admin_user: adminUser })
    })
    resetResult.value = await res.json()
    if (resetResult.value.success) {
      setTimeout(async () => {
        const r = await authFetch(`${API_BASE}/accounts/profile/${userProfile.value.username}`)
        if (r.ok) userProfile.value = await r.json()
      }, 600)
    }
  } catch (e) {
    resetResult.value = { success: false, error: e.message }
  } finally { resetLoading.value = false }
}

// ── Desbloqueo directo ──────────────────────────────────────────────────────
async function executeUnlock() {
  unlockLoading.value = true; unlockResult.value = null
  try {
    const res = await authFetch(`${API_BASE}/accounts/unlock`, { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ username: userProfile.value.username, admin_user: adminUser }) })
    unlockResult.value = await res.json()
    if (unlockResult.value.success) {
      setTimeout(async () => {
        const r = await authFetch(`${API_BASE}/accounts/profile/${userProfile.value.username}`)
        if (r.ok) userProfile.value = await r.json()
      }, 600)
    }
  } catch (e) { unlockResult.value = { success: false, error: e.message }
  } finally { unlockLoading.value = false }
}

// ── Opciones de cuenta ──────────────────────────────────────────────────────
async function saveAccountOptions() {
  optionsSaving.value = true; optionsResult.value = null
  try {
    const res = await authFetch(`${API_BASE}/accounts/account-options`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ username: userProfile.value.username, options: localOptions.value, admin_user: adminUser })
    })
    optionsResult.value = await res.json()
    if (optionsResult.value.success) {
      const r = await authFetch(`${API_BASE}/accounts/profile/${userProfile.value.username}`)
      if (r.ok) userProfile.value = await r.json()
    }
  } catch (e) { optionsResult.value = { success: false, error: e.message }
  } finally { optionsSaving.value = false }
}

// ── Editor de atributos ─────────────────────────────────────────────────────
const filteredAttributes = computed(() => {
  let list = allAttributes.value
  if (showOnlySet.value) list = list.filter(a => a.value !== '<no establecido>')
  if (attrFilter.value) {
    const q = attrFilter.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(q) || a.value.toLowerCase().includes(q))
  }
  return list
})

function startEditing(attr) {
  if (attr.readonly) return
  // Si intentan editar proxyAddresses desde el editor genérico, los enviamos a la pestaña especializada
  if (attr.name === 'proxyAddresses') {
    activeTab.value = 'alias'
    return
  }
  editingAttr.value = attr
  editingValue.value = attr.value === '<no establecido>' ? '' : attr.value
  attrResult.value = null
}

function cancelEditing() { editingAttr.value = null; editingValue.value = '' }

function handleAttrKeydown(event) {
  if (event.target.tagName.toLowerCase() === 'input') return
  if (event.ctrlKey || event.altKey || event.metaKey) return
  if (event.key.length !== 1) return
  
  const char = event.key.toLowerCase()
  const attr = filteredAttributes.value.find(a => a.name.toLowerCase().startsWith(char))
  
  if (attr) {
    const el = document.getElementById('attr-' + attr.name)
    if (el) el.scrollIntoView({ behavior: 'auto', block: 'center' })
  }
}

async function saveAttribute() {
  if (!editingAttr.value) return
  attrSaving.value = true; attrResult.value = null
  try {
    const res = await authFetch(`${API_BASE}/accounts/attributes`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ username: userProfile.value.username, attr_name: editingAttr.value.name, new_value: editingValue.value, admin_user: adminUser })
    })
    attrResult.value = await res.json()
    if (attrResult.value.success) {
      const idx = allAttributes.value.findIndex(a => a.name === editingAttr.value.name)
      if (idx >= 0) allAttributes.value[idx].value = editingValue.value || '<no establecido>'
      editingAttr.value = null
    }
  } catch (e) { attrResult.value = { success: false, error: e.message }
  } finally { attrSaving.value = false }
}

// ── Carpetas Compartidas (ACL) ──────────────────────────────────────────────
async function updateFolderPermission(folder) {
  if (folder.access === 'Sin Acceso') return removeFolderPermission(folder, true);
  const parts = folder.path.split('/');
  const shareName = parts[0];
  const subpath = parts.slice(1).join('\\'); 
  const permissionMap = { 'Control Total': 'FullControl', 'Modificar': 'Modify', 'Lectura y Ejecución': 'ReadAndExecute', 'Lectura': 'Read', 'Escritura': 'Write', 'Denegar Acceso': 'Deny', 'Tránsito / Solo Lectura (Explícito)': 'ReadAndExecute' };
  const mappedPerm = permissionMap[folder.access];
  if (!mappedPerm) return;

  const isInherited = folder.inherited || folder.origin.includes('Heredado');
  if (isInherited && folder.access !== 'Denegar Acceso') {
    if (!confirm('Para modificar este permiso heredado, debemos deshabilitar la herencia. ¿Continuar?')) { loadFolderGroups(); return; }
    try {
      const bRes = await authFetch(`${API_BASE}/fileserver/shares/${shareName}/acl/break-inheritance`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subpath }) });
      const bData = await bRes.json();
      if (!bData.success) throw new Error(bData.detail || 'Error rompiendo herencia');
    } catch(e) { alert('Error rompiendo herencia: ' + e.message); loadFolderGroups(); return; }
  }

  try {
    const res = await authFetch(`${API_BASE}/fileserver/shares/${shareName}/acl/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account: userProfile.value.username, permission: mappedPerm, subpath: subpath }) });
    const data = await res.json();
    if (!data.success) throw new Error(data.detail || 'Error actualizando permiso');
    folder.origin = `Explícito (${userProfile.value.username})`;
    folder.inherited = false;
  } catch (e) { console.error(e); alert('Error al actualizar permiso: ' + e.message); loadFolderGroups(); }
}

async function removeFolderPermission(folder, skipConfirm = false) {
  const isInherited = folder.inherited || folder.origin.includes('Heredado');
  if (isInherited) {
    if (!confirm('Este permiso es heredado. ¿Deshabilitar herencia y quitar acceso?')) { loadFolderGroups(); return; }
    const parts = folder.path.split('/');
    const shareName = parts[0];
    const subpath = parts.slice(1).join('\\');
    try {
      const bRes = await authFetch(`${API_BASE}/fileserver/shares/${shareName}/acl/break-inheritance`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subpath }) });
      const bData = await bRes.json();
      if (!bData.success) throw new Error(bData.detail || 'Error rompiendo herencia');
    } catch(e) { alert('Error rompiendo herencia: ' + e.message); loadFolderGroups(); return; }
  } else if (!skipConfirm && !confirm(`¿Revocar acceso a ${folder.path}?`)) { loadFolderGroups(); return; }
  
  const parts = folder.path.split('/');
  const shareName = parts[0];
  const subpath = parts.slice(1).join('\\');
  try {
    const res = await authFetch(`${API_BASE}/fileserver/shares/${shareName}/acl/remove`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ account: userProfile.value.username, subpath: subpath }) });
    const data = await res.json();
    if (!data.success) throw new Error(data.detail || 'Error revocando permiso');
    folder.access = 'Sin Acceso';
    folder.origin = 'No asignado';
    folder.inherited = false;
  } catch (e) { console.error(e); alert('Error al revocar permiso: ' + e.message); loadFolderGroups(); }
}

async function loadFolderGroups() {
  if (userProfile.value) {
    foldersLoading.value = true
    try {
      const res = await authFetch(`${API_BASE}/accounts/folders/${userProfile.value.username}`)
      if (res.ok) folderGroups.value = await res.json()
    } catch (e) { console.error('Error cargando carpetas', e) }
    finally { foldersLoading.value = false }
  }
}

const folderSearchQuery = ref('');

const visibleFolderGroups = computed(() => {
  let filtered = folderGroups.value;
  
  if (folderSearchQuery.value) {
    let rawQuery = folderSearchQuery.value.trim();
    
    // SMART SEARCH (Rutas UNC)
    if (rawQuery.includes('\\') || rawQuery.startsWith('//')) {
      rawQuery = rawQuery.replace(/\\/g, '/');
      if (rawQuery.startsWith('//')) rawQuery = rawQuery.substring(2);
      
      const parts = rawQuery.split('/').filter(p => p);
      if (parts.length >= 2) {
        // parts[0] es la IP o Nombre del Servidor (ej. APXEIO o 192.168.1.80) -> lo ignoramos
        rawQuery = parts.slice(1).join('/');
      }
    }
    
    const query = rawQuery.toLowerCase();
    filtered = filtered.filter(f => f.path.toLowerCase().includes(query));
    return filtered; // Mostrar todas las coincidencias
  }

  return filtered.filter(folder => {
    const parts = folder.path.split('/');
    if (parts.length === 1) return true;
    return expandedFolders.value.has(parts[0]);
  });
})

function toggleFolder(folderPath) {
  const newSet = new Set(expandedFolders.value);
  if (newSet.has(folderPath)) newSet.delete(folderPath); else newSet.add(folderPath);
  expandedFolders.value = newSet;
}

function hasChildren(rootPath) {
  return folderGroups.value.some(f => f.path.startsWith(rootPath + '/') && f.path.split('/').length > 1);
}

const foldersSubTab = ref('view');
const cloneSourceUser = ref('');
const isAnalyzingClone = ref(false);
const isExecutingClone = ref(false);
const cloneDelta = ref(null);
const cloneAnalyzeError = ref('');
const cloneExecuteError = ref('');
const cloneExecuteSuccess = ref(false);
const cloneResults = ref([]);

const cloneTotalChanges = computed(() => {
  if (!cloneDelta.value) return 0;
  return (cloneDelta.value.groups_to_add?.length || 0) + (cloneDelta.value.folders_to_add?.length || 0);
});

async function analyzeClone() {
  if (!cloneSourceUser.value) return;
  isAnalyzingClone.value = true;
  cloneAnalyzeError.value = '';
  cloneDelta.value = null;
  cloneExecuteError.value = '';
  cloneExecuteSuccess.value = false;
  
  try {
    const res = await authFetch(`${API_BASE}/fileserver/clone-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_user: cloneSourceUser.value.trim(),
        target_user: userProfile.value.username
      })
    });
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error analizando permisos');
    }
    
    const data = await res.json();
    cloneDelta.value = data.delta;
  } catch (err) {
    cloneAnalyzeError.value = err.message;
  } finally {
    isAnalyzingClone.value = false;
  }
}

import { useTasks } from '@/composables/useTasks'
const { addNotification } = useTasks()

async function executeClone() {
  if (!cloneDelta.value) return;
  
  isExecutingClone.value = true;
  cloneExecuteError.value = '';
  
  try {
    const res = await authFetch(`${API_BASE}/fileserver/clone-execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_user: cloneSourceUser.value.trim(),
        target_user: userProfile.value.username,
        delta: cloneDelta.value,
        admin_user: adminUser
      })
    });
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error ejecutando clonación');
    }
    
    // Alerta Inmediata de "Fire-and-forget"
    addNotification({
      type: 'info',
      title: 'Clonación Iniciada',
      message: `Estamos copiando los permisos de ${cloneSourceUser.value} a ${userProfile.value.username}. Te avisaremos cuando finalice.`
    });
    
    cloneExecuteSuccess.value = true;
    
    // Ocultar delta y vaciar el form para que el usuario pueda seguir
    setTimeout(() => {
      cloneSourceUser.value = '';
      cloneDelta.value = null;
      cloneExecuteSuccess.value = false;
      foldersSubTab.value = 'view';
    }, 3000);
    
  } catch (err) {
    cloneExecuteError.value = err.message;
  } finally {
    isExecutingClone.value = false;
  }
}

const statusConfig = computed(() => {
  if (!userProfile.value) return {}
  return {
    active:   { label: 'Activa',         color: 'bg-emerald-50 text-emerald-700 border-emerald-200', dot: 'bg-emerald-500' },
    locked:   { label: 'Bloqueada',      color: 'bg-red-50 text-red-700 border-red-200',             dot: 'bg-red-500 animate-pulse' },
    disabled: { label: 'Deshabilitada',  color: 'bg-amber-50 text-amber-700 border-amber-200',       dot: 'bg-amber-500' },
  }[userProfile.value.status] || { label: userProfile.value.status, color: 'bg-slate-50 text-slate-500', dot: 'bg-slate-400' }
})
</script>

<template>
  <!-- Contenedor Edge-to-Edge -->
  <div class="flex h-[calc(100vh-64px)] w-full overflow-hidden bg-white">
    
    <!-- Columna Izquierda: Sub-menú Pegado -->
    <div class="hidden md:flex flex-col w-64 bg-white border-r border-slate-200 shrink-0 overflow-y-auto">
      <div class="p-5 pb-2">
        <h2 class="text-[11px] font-bold text-slate-500 uppercase tracking-widest">Administrar</h2>
      </div>
      <nav class="flex flex-col gap-1 px-3 pb-6">
        <button v-for="tab in filteredTabs" :key="tab.id" @click="activeTab = tab.id"
          :class="['flex items-center gap-3 px-3 py-2 text-sm transition-all text-left w-full rounded-md', activeTab === tab.id ? 'bg-blue-50 text-blue-700 font-semibold' : 'text-gray-600 hover:bg-gray-100']">
          <svg :class="['w-4 h-4 shrink-0', activeTab === tab.id ? 'text-blue-700' : 'text-gray-400']" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" :d="tab.icon"/></svg>
          <span class="truncate">{{ tab.name }}</span>
        </button>
      </nav>
    </div>

    <!-- Columna Derecha: Área de Contenido -->
    <div class="flex-1 overflow-y-auto flex flex-col relative bg-gray-50">

      <!-- Modals and Overlays -->
      <Teleport to="body">
        <EditProfileModal 
          v-if="showEditModal && userProfile" 
          :user-profile="userProfile" 
          :account-options="accountOptions"
          @close="showEditModal = false" 
          @saved="showEditModal = false; fetchUserProfile()" 
        />
      </Teleport>

      <Teleport to="body">
        <div v-if="showPasswordModal && userProfile" class="fixed inset-0 z-[100] flex items-start justify-center pt-16">
          <div class="fixed inset-0 bg-black/30 backdrop-blur-[2px]" @click="closePasswordModal"></div>
          <div class="relative w-[480px] bg-white border border-slate-200 rounded-md shadow-2xl flex flex-col z-10">
            <div class="flex items-center justify-between px-5 py-3 border-b border-slate-200 bg-slate-50 rounded-t-md">
              <div class="flex items-center gap-2">
                <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
                <span class="text-[13px] font-semibold text-slate-800">Restablecer contraseña</span>
              </div>
              <button @click="closePasswordModal" class="text-slate-400 hover:text-slate-700 p-0.5">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="p-5 flex flex-col gap-4">
              <div class="flex items-center gap-3 p-3 bg-slate-50 border border-slate-100 rounded-sm">
                <div class="w-10 h-10 rounded-sm bg-white border border-slate-200 flex items-center justify-center shrink-0">
                  <span class="text-sm font-semibold text-slate-500">{{ userProfile.fullName.split(' ').map(n => n[0]).slice(0,2).join('') }}</span>
                </div>
                <div class="min-w-0">
                  <p class="text-[13px] font-semibold text-slate-800 truncate">{{ userProfile.fullName }}</p>
                  <p class="text-[11px] text-slate-500 font-mono">{{ userProfile.userPrincipalName || userProfile.email || userProfile.username }}</p>
                </div>
              </div>
              <div>
                <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Nueva contraseña</label>
                <div class="flex gap-1.5">
                  <input v-model="generatedPassword" type="password" class="flex-1 bg-white border border-slate-200 rounded-sm text-[14px] text-slate-800 font-mono px-3 py-2 focus:outline-none focus:ring-1 focus:ring-slate-400 tracking-wide"/>
                </div>
              </div>
              <div>
                <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Confirmar contraseña</label>
                <input v-model="confirmPassword" type="text" placeholder="Escribe la contraseña nuevamente para confirmar" :class="['w-full border rounded-sm text-[13px] font-mono px-3 py-2 focus:outline-none transition-colors', confirmError ? 'border-red-300 bg-red-50/30' : confirmPassword && confirmPassword===generatedPassword ? 'border-emerald-300 bg-emerald-50/20' : 'border-slate-200 bg-white focus:ring-1 focus:ring-slate-400']"/>
                <p v-if="confirmError" class="text-[11px] text-red-600 mt-1">{{ confirmError }}</p>
                <p v-else-if="confirmPassword && confirmPassword===generatedPassword" class="text-[11px] text-emerald-600 mt-1 flex items-center gap-1">
                  <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                  Contraseñas coinciden
                </p>
              </div>
              <div class="space-y-2">
                <label class="flex items-center gap-2.5 cursor-pointer">
                  <input type="checkbox" v-model="mustChangePassword" class="w-3.5 h-3.5 border-slate-300 cursor-pointer rounded-sm"/>
                  <span class="text-[12px] text-slate-700">Cambiar en el siguiente inicio de sesión</span>
                </label>
                <label v-if="userProfile.status==='locked'" class="flex items-center gap-2.5 cursor-pointer">
                  <input type="checkbox" v-model="unlockOnReset" class="w-3.5 h-3.5 border-slate-300 cursor-pointer rounded-sm"/>
                  <span class="text-[12px] text-slate-700">Desbloquear la cuenta</span>
                </label>
              </div>
              <div v-if="resetResult" :class="['text-[12px] px-4 py-2.5 rounded-sm border flex items-center gap-2', resetResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
                {{ resetResult.success ? resetResult.message : resetResult.error }}
              </div>
            </div>
            <div class="flex justify-end px-5 py-3 border-t border-slate-200 bg-slate-50/50 gap-2 rounded-b-md">
              <button v-if="resetResult && resetResult.success" @click="closePasswordModal" class="text-[12px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-5 py-1.5">Aceptar</button>
              <template v-else>
                <button @click="closePasswordModal" class="text-[12px] font-medium text-slate-600 hover:text-slate-800 px-4 py-1.5">Cancelar</button>
                <button @click="executePasswordReset" :disabled="resetLoading || !confirmPassword" class="text-[12px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-5 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed">
                  {{ resetLoading ? 'Ejecutando...' : 'Aplicar' }}
                </button>
              </template>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Top Action Bar (Breadcrumbs & Acciones Generales) -->
      <div class="bg-white px-6 py-2.5 shrink-0 flex items-center justify-between sticky top-0 z-10">
        <div class="flex items-center gap-1.5">
          <router-link to="/" class="text-[11px] text-slate-500 hover:text-blue-600 transition-colors">Panel de control</router-link>
          <span class="text-[11px] text-slate-400">/</span>
          <router-link to="/cuentas" class="text-[11px] text-slate-500 hover:text-blue-600 transition-colors">Cuentas AD</router-link>
          <span class="text-[11px] text-slate-400">/</span>
          <span class="text-[11px] text-slate-800 font-medium">Propiedades del usuario</span>
        </div>
        <div class="flex items-center gap-1">
          <button @click="refreshCurrentView" class="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-700 hover:bg-slate-100 rounded transition-colors mr-2">
            <svg class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Actualizar
          </button>
          <button @click="showEditModal = true" :disabled="!userProfile" class="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-700 hover:bg-slate-100 rounded transition-colors disabled:opacity-40">
            <svg class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
            Editar propiedades
          </button>
          <button @click="openPasswordModal" :disabled="!userProfile" class="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-700 hover:bg-slate-100 rounded transition-colors disabled:opacity-40">
            <svg class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
            Restablecer contraseña
          </button>
          <button @click="showOffboardModal = true" :disabled="!userProfile" class="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-red-700 hover:bg-red-50 border border-transparent hover:border-red-200 rounded transition-colors disabled:opacity-40 ml-1">
            <svg class="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7a4 4 0 11-8 0 4 4 0 018 0zM9 14a6 6 0 00-6 6v1h12v-1a6 6 0 00-6-6zM21 12l-6 6m0-6l6 6"/></svg>
            Desvincular (Offboarding)
          </button>
          <button v-if="userProfile && userProfile.status==='locked'" @click="executeUnlock" :disabled="unlockLoading" class="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-700 hover:bg-slate-100 rounded transition-colors disabled:opacity-50">
            <svg class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/></svg>
            {{ unlockLoading ? 'Desbloqueando...' : 'Desbloquear cuenta' }}
          </button>
          <div class="h-4 w-px bg-slate-300 mx-1"></div>
          <button @click="goBack" class="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-slate-600 hover:text-slate-900 transition-colors hover:bg-slate-100 rounded">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
            Cerrar
          </button>
        </div>
      </div>

      <!-- Contenido del Perfil (Header) -->
      <div class="bg-white px-8 py-6 shrink-0">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 rounded-full bg-blue-100/50 text-blue-700 border border-blue-200 flex items-center justify-center shrink-0">
            <span v-if="userProfile" class="text-lg font-bold">{{ userProfile.fullName.split(' ').map(n => n[0]).slice(0,2).join('') }}</span>
            <div v-else class="w-6 h-6 rounded-full bg-blue-200/50 animate-pulse"></div>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-3">
              <h1 v-if="userProfile" class="text-xl font-bold text-slate-900 truncate">{{ userProfile.fullName }}</h1>
              <div v-else class="h-6 w-48 bg-slate-200 rounded-sm animate-pulse"></div>
              
              <span v-if="userProfile" :class="['inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border text-[10px] font-semibold uppercase tracking-wider', statusConfig.color]">
                <span :class="['w-1.5 h-1.5 rounded-full', statusConfig.dot]"></span>
                {{ statusConfig.label }}
              </span>
              <div v-else class="h-5 w-16 bg-slate-200 rounded-sm animate-pulse"></div>
            </div>
            <p v-if="userProfile" class="text-[13px] text-slate-500 mt-1">{{ userProfile.userPrincipalName || userProfile.email || userProfile.username }}</p>
            <div v-else class="h-3.5 w-32 bg-slate-200 rounded-sm animate-pulse mt-1.5"></div>
          </div>
        </div>
        <div v-if="unlockResult" class="mt-4">
          <div :class="['text-[12px] px-4 py-2 rounded-sm border flex items-center gap-2 inline-block', unlockResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
            {{ unlockResult.success ? unlockResult.message : unlockResult.error }}
          </div>
        </div>
      </div>

      <!-- Área de Pestañas (Tarjetas Blancas) -->
      <div class="p-6 md:p-8 w-full max-w-[1400px] relative">
        <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 gap-3">
          <div class="w-8 h-8 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
          <span class="text-[13px] text-slate-500">Consultando información del usuario...</span>
        </div>

        <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-sm p-8 text-center max-w-2xl">
          <p class="text-sm text-red-700 font-medium">{{ error }}</p>
          <button @click="goBack" class="mt-4 text-[12px] text-slate-600 border border-slate-200 bg-white hover:bg-slate-50 rounded-sm px-4 py-1.5">Volver</button>
        </div>

        <template v-else-if="userProfile">
          <div v-if="activeTab==='general'">
            <div class="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div class="grid grid-cols-1 lg:grid-cols-5">
                <!-- Columna Izquierda: Información Personal + Organización (60%) -->
                <div class="lg:col-span-3 p-6 lg:border-r border-gray-200">
                  <!-- Información Personal -->
                  <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Información personal</h3>
                  <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                    <template v-for="[label, val] in [['Nombre', userProfile.firstName], ['Apellido', userProfile.lastName], ['Nombre mostrado', userProfile.fullName], ['Descripción', userProfile.description], ['Correo electrónico', userProfile.email], ['Teléfono', userProfile.phone], ['Celular', userProfile.mobile], ['Último inicio de sesión', userProfile.lastLogon]]" :key="label">
                      <div class="flex flex-col">
                        <dt class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{{ label }}</dt>
                        <dd :class="['text-sm font-medium', val ? 'text-gray-900' : 'text-gray-400 italic']">{{ val || '—' }}</dd>
                      </div>
                    </template>
                  </dl>

                  <!-- Divisor suave -->
                  <div class="border-b border-gray-100 my-6"></div>

                  <!-- Organización -->
                  <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4">Organización</h3>
                  <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                    <template v-for="[label, val] in [['Cargo', userProfile.title], ['Departamento', userProfile.department], ['Empresa', userProfile.company], ['Jefe directo', userProfile.manager], ['Oficina', userProfile.office]]" :key="label">
                      <div class="flex flex-col">
                        <dt class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">{{ label }}</dt>
                        <dd :class="['text-sm font-medium', val ? 'text-gray-900' : 'text-gray-400 italic']">{{ val || '—' }}</dd>
                      </div>
                    </template>
                  </dl>
                </div>

                <!-- Columna Derecha: Estado de Seguridad (40%) -->
                <div class="lg:col-span-2 p-6 border-t lg:border-t-0 border-gray-200">
                  <div v-if="accountOptions">
                    <div class="flex items-center justify-between mb-5">
                      <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest">Estado de Seguridad</h3>
                      <span v-if="optionsSaving" class="text-[10px] text-blue-600 font-medium animate-pulse">Guardando...</span>
                      <span v-else-if="optionsResult?.success" class="text-[10px] text-emerald-600 font-medium">Guardado ✓</span>
                    </div>
                    <ul class="space-y-4">
                      <li v-for="(label, key) in { account_locked: 'Cuenta bloqueada', account_disabled: 'Cuenta deshabilitada', must_change_password: 'Debe cambiar contraseña al inicio', password_never_expires: 'La contraseña nunca expira', smart_card_required: 'Requiere tarjeta inteligente', trusted_for_delegation: 'Confianza para delegación', store_reversible_encryption: 'Cifrado reversible' }" :key="key" class="flex items-center justify-between gap-3">
                        <span class="text-sm text-gray-900">{{ label }}</span>
                        <button
                          type="button"
                          role="switch"
                          :aria-checked="localOptions[key]"
                          :disabled="key === 'account_locked' && !accountOptions.account_locked"
                          @click="localOptions[key] = !localOptions[key]; saveAccountOptions()"
                          :class="[
                            'relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                            localOptions[key] ? 'bg-blue-600' : 'bg-gray-300',
                            (key === 'account_locked' && !accountOptions.account_locked) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
                          ]"
                        >
                          <span
                            :class="[
                              'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                              localOptions[key] ? 'translate-x-4' : 'translate-x-0'
                            ]"
                          ></span>
                        </button>
                      </li>
                    </ul>
                    <div v-if="optionsResult && !optionsResult.success" class="mt-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                      Error: {{ optionsResult.error }}
                    </div>
                    <div v-if="userEntraStatus && userEntraStatus.signInActivity" class="mt-6 pt-4 border-t border-gray-100">
                      <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider block mb-2">Último inicio en la nube</span>
                      <p class="text-sm text-gray-900 font-medium">
                        {{ userEntraStatus.signInActivity.lastSignInDateTime ? new Date(userEntraStatus.signInActivity.lastSignInDateTime).toLocaleString() : 'Nunca' }}
                      </p>
                      <p v-if="userEntraStatus.signInActivity.ipAddress" class="text-xs text-gray-500 mt-1 font-mono">
                        IP: {{ userEntraStatus.signInActivity.ipAddress }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Vista 360: Activos y Correo -->
            <div class="mt-8 pt-6 border-t border-slate-100 col-span-full">
              <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4">Vista 360 de Activos (M365)</h3>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Hardware Asignado -->
                <div class="bg-slate-50 border border-slate-200 rounded-sm p-4">
                  <div class="flex items-center gap-2 mb-3">
                    <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg>
                    <h4 class="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Hardware Registrado</h4>
                  </div>
                  <ul v-if="userDevices.length > 0" class="space-y-3">
                    <li v-for="dev in userDevices" :key="dev.id" class="flex items-center justify-between border-b border-slate-100 pb-2 last:border-0 last:pb-0">
                      <div class="flex items-center gap-3">
                        <svg class="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                        <div>
                          <p class="text-[13px] font-bold text-slate-800">{{ dev.displayName }}</p>
                          <p class="text-[11px] text-slate-500">{{ dev.operatingSystem }}</p>
                        </div>
                      </div>
                      <span :class="['px-2 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wide border', dev.isCompliant ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
                        {{ dev.isCompliant ? 'Compliant' : 'No Compliant' }}
                      </span>
                    </li>
                  </ul>
                  <div v-else class="text-[12px] text-slate-400 italic">No hay dispositivos registrados.</div>
                </div>

                <!-- Estado del Buzón -->
                <div class="bg-slate-50 border border-slate-200 rounded-sm p-4">
                  <div class="flex items-center gap-2 mb-3">
                    <svg class="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
                    <h4 class="text-[12px] font-bold text-slate-700 uppercase tracking-wider">Estado del Buzón</h4>
                  </div>
                  <div v-if="userMailbox && userMailbox.hasMailbox">
                    <div class="flex items-center gap-2 mb-3">
                      <span class="px-2 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wide border bg-emerald-50 text-emerald-700 border-emerald-200">
                        Buzón Activo (Exchange)
                      </span>
                    </div>

                    <div v-if="userMailbox.issue_warning" class="mt-3">
                      <p class="text-[12px] text-slate-700 mb-1 font-medium">Uso de Almacenamiento</p>
                      <div class="w-full bg-slate-200 rounded-full h-2.5 mb-1 relative overflow-hidden">
                        <div :class="['h-2.5 rounded-full transition-all', (userMailbox.storage_used / userMailbox.issue_warning) > 0.9 ? 'bg-red-500' : 'bg-blue-500']" :style="{ width: Math.min(100, Math.round((userMailbox.storage_used / userMailbox.issue_warning) * 100)) + '%' }"></div>
                      </div>
                      <div class="flex justify-between text-[10px] text-slate-500 font-bold uppercase">
                        <span>Usado: {{ (userMailbox.storage_used / 1024 / 1024 / 1024).toFixed(2) }} GB</span>
                        <span>Límite: {{ (userMailbox.issue_warning / 1024 / 1024 / 1024).toFixed(2) }} GB</span>
                      </div>
                    </div>
                    <div v-else-if="userMailbox.report_error" class="mt-3">
                      <p class="text-[10px] text-slate-500 italic">* Nota: No se pudo obtener la capacidad en GB ({{ userMailbox.report_error }}).</p>
                    </div>
                  </div>
                  <div v-else-if="userMailbox && userMailbox.debug_data" class="text-[10px] text-slate-500 overflow-hidden break-all h-32 overflow-y-auto bg-slate-100 p-2 rounded">
                    <strong>DEBUG (assignedPlans):</strong><br/>
                    {{ userMailbox.debug_data.length === 0 ? 'No tiene ningún assignedPlan' : userMailbox.debug_data }}
                  </div>
                  <div v-else-if="userMailbox && userMailbox.error" class="text-[12px] text-red-600 font-bold bg-red-50 p-2 border border-red-200">
                    Error Graph API: {{ userMailbox.error }}
                  </div>
                  <div v-else class="text-[12px] text-slate-400 italic">No se detecta buzón activo (Posiblemente sin licencia de Exchange asignada en M365).</div>
                </div>
              </div>
            </div>



            <div class="mt-8 pt-4 border-t border-slate-100 col-span-full">
              <p class="text-[11px] uppercase text-slate-500 tracking-wider mb-2 font-semibold">Distinguished Name</p>
              <div class="flex items-start gap-2">
                <div class="flex-1 bg-slate-50 border border-slate-200 rounded-sm px-3 py-2 text-[11px] font-mono text-slate-700 break-all leading-relaxed">
                  {{ userProfile.distinguishedName }}
                </div>
                <button @click="navigator.clipboard.writeText(userProfile.distinguishedName)" title="Copiar" class="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 border border-transparent hover:border-slate-200 rounded-sm transition-colors shrink-0">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                </button>
              </div>
            </div>
          </div>

          <div v-else-if="activeTab==='account'">
            <div class="grid grid-cols-1 lg:grid-cols-2">
              
              <!-- Columna Izquierda: Datos -->
              <div class="lg:border-r border-gray-200 lg:pr-8 pb-8 lg:pb-0">
                
                <!-- Identidad de Red -->
                <div>
                  <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest mt-2 mb-4 border-b border-gray-100 pb-2">Identidad de Red</h3>
                  <dl class="space-y-4">
                    <div class="flex flex-col">
                      <dt class="text-[11px] text-gray-400 uppercase mb-0.5">sAMAccountName</dt>
                      <dd class="flex items-center text-sm font-mono text-gray-900">
                        {{ userProfile.username }}
                        <button @click="navigator.clipboard.writeText(userProfile.username)" title="Copiar" class="text-gray-400 hover:text-blue-500 cursor-pointer ml-2 transition-colors">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        </button>
                      </dd>
                    </div>
                    <div class="flex flex-col">
                      <dt class="text-[11px] text-gray-400 uppercase mb-0.5">UPN (User Principal)</dt>
                      <dd class="flex items-center text-sm font-mono text-gray-900">
                        {{ userProfile.userPrincipalName || userProfile.username }}
                        <button @click="navigator.clipboard.writeText(userProfile.userPrincipalName || userProfile.username)" title="Copiar" class="text-gray-400 hover:text-blue-500 cursor-pointer ml-2 transition-colors">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        </button>
                      </dd>
                    </div>
                    <div class="flex flex-col">
                      <dt class="text-[11px] text-gray-400 uppercase mb-0.5">Nombre anterior (Win2000)</dt>
                      <dd class="flex items-center text-sm font-mono text-gray-900">
                        {{ (userProfile.userPrincipalName ? userProfile.userPrincipalName.split('@')[1].split('.')[0].toUpperCase() + '\\' : '') + userProfile.username }}
                        <button @click="navigator.clipboard.writeText((userProfile.userPrincipalName ? userProfile.userPrincipalName.split('@')[1].split('.')[0].toUpperCase() + '\\\\' : '') + userProfile.username)" title="Copiar" class="text-gray-400 hover:text-blue-500 cursor-pointer ml-2 transition-colors">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                        </button>
                      </dd>
                    </div>
                  </dl>
                </div>

                <!-- Auditoría de Acceso -->
                <div>
                  <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest mt-10 mb-4 border-b border-gray-100 pb-2">Auditoría de Acceso</h3>
                  <dl class="space-y-4">
                    <div class="flex flex-col">
                      <dt class="text-[11px] text-gray-400 uppercase mb-0.5">Último inicio de sesión</dt>
                      <dd class="text-sm font-mono text-gray-900">{{ userProfile.lastLogon }}</dd>
                    </div>
                    <div class="flex flex-col">
                      <dt class="text-[11px] text-gray-400 uppercase mb-0.5">Cuenta creada</dt>
                      <dd class="text-sm font-mono text-gray-900">{{ userProfile.created }}</dd>
                    </div>
                    <div class="flex flex-col">
                      <dt class="text-[11px] text-gray-400 uppercase mb-0.5">Último cambio de clave</dt>
                      <dd class="text-sm font-mono text-gray-900">{{ userProfile.passwordLastSet }}</dd>
                    </div>
                    <div class="flex flex-col pt-2">
                      <dt class="text-[11px] text-gray-400 uppercase mb-1">Intentos fallidos</dt>
                      <dd>
                        <span v-if="userProfile.badPwdCount === 0" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-800">
                          0 Intentos
                        </span>
                        <span v-else class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-800">
                          {{ userProfile.badPwdCount }} Intentos fallidos
                        </span>
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>

              <!-- Columna Derecha: Seguridad -->
              <div class="lg:pl-8">
                <div v-if="localOptions && Object.keys(localOptions).length">
                  <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest mt-2 mb-4 border-b border-gray-100 pb-2">Seguridad y Opciones</h3>
                  
                  <!-- Estado de Bloqueo -->
                  <div class="mb-8">
                    <div v-if="!accountOptions.account_locked" class="bg-green-50 border border-green-200 rounded p-2 px-3 flex items-center gap-2">
                      <svg class="w-4 h-4 text-green-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
                      <span class="text-xs font-bold text-green-900">Cuenta Segura ({{ userProfile.badPwdCount }} intentos fallidos)</span>
                    </div>
                    <div v-else class="bg-red-50 border border-red-200 rounded p-3 flex flex-col gap-2">
                      <div class="flex items-center gap-2">
                        <svg class="w-4 h-4 text-red-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
                        <span class="text-sm font-bold text-red-900">Cuenta Bloqueada</span>
                      </div>
                      <button @click="localOptions.account_locked = false; saveAccountOptions()" :disabled="optionsSaving" class="bg-red-600 hover:bg-red-700 text-white text-xs font-bold py-1.5 px-3 rounded shadow-sm transition-colors disabled:opacity-50 self-start">
                        {{ optionsSaving ? 'Desbloqueando...' : 'Desbloquear Cuenta Ahora' }}
                      </button>
                    </div>
                  </div>

                  <!-- Controles Avanzados -->
                  <div>
                    <div class="space-y-1.5">
                      <label v-for="(label, key) in { must_change_password: 'El usuario debe cambiar la contraseña en el siguiente inicio de sesión', password_never_expires: 'La contraseña nunca expira', account_disabled: 'La cuenta está deshabilitada', smart_card_required: 'Se requiere tarjeta inteligente para el inicio de sesión', trusted_for_delegation: 'La cuenta es de confianza para delegación', store_reversible_encryption: 'Almacenar contraseña con cifrado reversible' }" :key="key" class="flex items-center gap-2 cursor-pointer group hover:bg-gray-50 p-1 -mx-1 rounded transition-colors">
                        <input type="checkbox" v-model="localOptions[key]" @change="saveAccountOptions()" :disabled="key === 'account_locked'" class="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 transition-colors cursor-pointer disabled:cursor-not-allowed"/>
                        <span :class="['text-sm font-medium', localOptions[key] && (key === 'account_disabled' || key === 'must_change_password') ? 'text-yellow-700' : 'text-gray-700']">
                          {{ label }}
                        </span>
                      </label>
                    </div>

                    <div class="mt-4 min-h-[24px]">
                      <div v-if="optionsSaving" class="text-xs text-blue-600 font-medium animate-pulse flex items-center gap-1.5">
                        <span class="w-3 h-3 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></span>
                        Aplicando cambios...
                      </div>
                      <div v-if="optionsResult && !optionsSaving" :class="['text-xs px-3 py-2 rounded-md border', optionsResult.success ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200']">
                        {{ optionsResult.success ? optionsResult.message : optionsResult.error }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div v-if="userEntraStatus && userEntraStatus.onPremisesSyncEnabled" class="bg-white rounded-lg border border-gray-200 shadow-sm mt-5 p-6">
              <h3 class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                <svg class="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                Propiedades Locales (AD Connect)
              </h3>
              <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-y-4 gap-x-8">
                <div class="flex flex-col lg:col-span-3">
                  <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Nombre distintivo (DN) local</span>
                  <span class="text-sm font-medium text-gray-900 break-all">{{ userEntraStatus.onPremisesDistinguishedName || '--' }}</span>
                </div>
                <div class="flex flex-col">
                  <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Identificador inmutable local</span>
                  <span class="text-sm font-medium text-gray-900">{{ userEntraStatus.onPremisesImmutableId || '--' }}</span>
                </div>
                <div class="flex flex-col">
                  <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Nombre de cuenta SAM local</span>
                  <span class="text-sm font-medium text-gray-900">{{ userEntraStatus.onPremisesSamAccountName || '--' }}</span>
                </div>
                <div class="flex flex-col">
                  <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Nombre de dominio local</span>
                  <span class="text-sm font-medium text-gray-900">{{ userEntraStatus.onPremisesDomainName || '--' }}</span>
                </div>
                <div class="flex flex-col lg:col-span-3">
                  <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Identificador de seguridad (SID) local</span>
                  <span class="text-sm font-medium text-gray-900 break-all">{{ userEntraStatus.onPremisesSecurityIdentifier || '--' }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="activeTab==='groups'">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              
              <!-- Grupos Locales AD -->
              <div>
                <div class="flex items-center justify-between mb-4">
                  <div class="flex items-center gap-2">
                    <svg class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                    <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Grupos Locales (Active Directory)</h3>
                  </div>
                  <span class="text-[11px] text-slate-400 bg-slate-50 border border-slate-200 rounded-sm px-2 py-0.5">{{ userProfile.groups.length }} grupos</span>
                </div>
                
                <div class="mb-4 flex items-center gap-2 w-full">
                  <input type="text" placeholder="Buscar grupo local..." class="flex-1 w-full border border-slate-300 rounded px-2 py-1.5 text-[12px] bg-white outline-none focus:border-blue-500" />
                  <button class="px-3 py-1.5 bg-blue-600 text-white text-[12px] rounded font-semibold disabled:opacity-50 flex items-center gap-1.5 shrink-0 hover:bg-blue-700 transition-colors">
                    Agregar
                  </button>
                </div>
                <div class="border border-slate-200 rounded-sm overflow-hidden">
                  <table class="w-full text-left">
                    <thead>
                      <tr class="bg-slate-50 border-b border-slate-200">
                        <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Nombre del grupo</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      <tr v-for="(group, idx) in userProfile.groups" :key="idx" class="hover:bg-slate-50/50">
                        <td class="px-4 py-3">
                          <div class="flex items-center gap-2">
                            <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                            <span class="text-[12px] font-semibold text-slate-800 font-mono">{{ group.name }}</span>
                          </div>
                        </td>
                      </tr>
                      <tr v-if="userProfile.groups.length === 0">
                        <td class="px-4 py-10 text-center text-[12px] text-slate-400">Este usuario no pertenece a ningún grupo local.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Grupos M365 -->
              <div>
                <div class="flex items-center justify-between mb-4">
                  <div class="flex items-center gap-2">
                    <svg class="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/></svg>
                    <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Grupos y Equipos (Microsoft 365)</h3>
                  </div>
                  <span class="text-[11px] text-slate-400 bg-slate-50 border border-slate-200 rounded-sm px-2 py-0.5">{{ userM365Groups.length }} grupos</span>
                </div>
                
                <div class="mb-4 flex items-center gap-2 w-full">
                  <select v-model="selectedM365Group" class="flex-1 w-full border border-slate-300 rounded px-2 py-1.5 text-[12px] bg-white outline-none focus:border-blue-500">
                    <option value="" disabled>Seleccione un grupo M365...</option>
                    <option v-for="g in allM365Groups" :key="g.id" :value="g.id">
                      {{ g.displayName }} {{ g.groupTypes?.includes('Unified') ? '(M365/Teams)' : '(Seguridad)' }}
                    </option>
                  </select>
                  <button @click="addM365Group" :disabled="!selectedM365Group || m365GroupLoading" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 transition-colors text-white text-[12px] rounded font-semibold disabled:opacity-50 flex items-center gap-1.5 shrink-0">
                    <span v-if="m365GroupLoading" class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin shrink-0"></span>
                    Agregar
                  </button>
                </div>

                <div class="border border-slate-200 rounded-sm overflow-hidden">
                  <table class="w-full text-left">
                    <thead>
                      <tr class="bg-slate-50 border-b border-slate-200">
                        <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Nombre del grupo</th>
                        <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider text-right">Acción</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      <tr v-for="group in userM365Groups" :key="group.id" class="hover:bg-slate-50/50">
                        <td class="px-4 py-3">
                          <div class="flex items-center gap-2">
                            <svg v-if="group.groupTypes?.includes('Unified')" class="w-3.5 h-3.5 text-blue-500 shrink-0" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                            <svg v-else class="w-3.5 h-3.5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                            <span class="text-[12px] font-semibold text-slate-800 font-mono">{{ group.displayName }}</span>
                          </div>
                        </td>
                        <td class="px-4 py-3 text-right">
                          <button @click="removeM365Group(group.id, group.displayName)" :disabled="m365GroupLoading" class="text-[11px] text-red-500 hover:text-red-700 disabled:opacity-50">Remover</button>
                        </td>
                      </tr>
                      <tr v-if="userM365Groups.length === 0">
                        <td colspan="2" class="px-4 py-10 text-center text-[12px] text-slate-400">
                          <div v-if="m365GroupLoading" class="w-5 h-5 mx-auto border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                          <span v-else>Este usuario no pertenece a grupos en M365.</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          </div>

          <div v-else-if="activeTab==='attributes'">
            <div class="flex items-center gap-3 mb-3 flex-wrap bg-white p-3 rounded-md border border-slate-200 shadow-sm">
              <div class="relative flex-1 min-w-[200px]">
                <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                <input v-model="attrFilter" type="text" placeholder="Filtrar atributo..." class="w-full pl-8 pr-3 py-1.5 text-[12px] border border-slate-200 rounded-sm focus:outline-none focus:ring-1 focus:ring-slate-400 bg-slate-50"/>
              </div>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="showOnlySet" class="w-3.5 h-3.5 border-slate-300"/>
                <span class="text-[12px] text-slate-600 font-medium">Solo con valor</span>
              </label>
              <div class="h-4 w-px bg-slate-200 mx-2"></div>
              <span class="text-[11px] font-bold text-slate-400 bg-slate-50 px-2 py-1 rounded border border-slate-100">{{ filteredAttributes.length }} atributos</span>
            </div>
            
            <div v-if="attrResult" :class="['text-[12px] px-4 py-2 rounded-sm border mb-3 flex items-center gap-2', attrResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
              {{ attrResult.success ? attrResult.message : attrResult.error }}
            </div>
            
            <div v-if="editingAttr" class="mb-3 border border-blue-200 bg-blue-50/50 rounded-sm p-3 shadow-sm flex flex-col md:flex-row items-center gap-3">
              <div class="flex items-center gap-2 shrink-0">
                <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                <span class="text-[12px] font-semibold text-slate-800">Editar: <span class="font-mono text-blue-700">{{ editingAttr.name }}</span></span>
              </div>
              <input v-model="editingValue" type="text" :placeholder="editingAttr.value" class="flex-1 w-full border border-blue-300 rounded-sm text-[12px] font-mono px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400 bg-white"/>
              <div class="flex gap-2 shrink-0">
                <button @click="saveAttribute" :disabled="attrSaving" class="text-[12px] font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-sm px-4 py-1.5 disabled:opacity-50 flex items-center gap-1.5">
                  <span v-if="attrSaving" class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                  {{ attrSaving ? 'Guardando...' : 'Guardar' }}
                </button>
                <button @click="cancelEditing" class="text-[12px] font-medium text-slate-600 bg-white border border-slate-300 hover:bg-slate-50 rounded-sm px-3 py-1.5">Cancelar</button>
              </div>
            </div>
            
            <div class="border border-slate-200 rounded-md overflow-hidden bg-white shadow-sm flex flex-col">
              <div class="overflow-y-auto max-h-[600px] w-full focus:outline-none" tabindex="0" @keydown="handleAttrKeydown">
                <table class="w-full text-left relative">
                  <thead class="sticky top-0 z-10 bg-slate-50 border-b border-slate-200 shadow-sm">
                    <tr>
                      <th class="px-4 py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-[220px]">Atributo</th>
                      <th class="px-4 py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Valor</th>
                      <th class="px-3 py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-12 text-center">Ed.</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100">
                    <tr v-for="attr in filteredAttributes" :key="attr.name" :id="'attr-' + attr.name" class="hover:bg-slate-50/50 transition-colors">
                      <td class="px-4 py-1 font-mono text-[11px] text-slate-700 font-semibold">{{ attr.name }}</td>
                      <td class="px-4 py-1 text-[11px] font-mono max-w-0 truncate">
                        <span :class="attr.value === '<no establecido>' ? 'text-slate-300 italic' : 'text-slate-600'" :title="attr.value">{{ attr.value }}</span>
                      </td>
                      <td class="px-3 py-1 text-center">
                        <button v-if="!attr.readonly" @click="startEditing(attr)" class="text-slate-400 hover:text-blue-600 transition-colors p-1 rounded hover:bg-blue-50" title="Editar Atributo">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
                        </button>
                        <span v-else class="text-[10px] text-slate-200 italic">—</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div v-else-if="activeTab==='folders'">
            <!-- Sub-tabs para Carpetas -->
            <div class="flex border-b border-slate-200 mb-5">
              <button @click="foldersSubTab = 'view'" :class="['px-4 py-2 text-sm font-medium border-b-2 transition-colors', foldersSubTab === 'view' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300']">
                Permisos Actuales y Asignación
              </button>
              <button @click="foldersSubTab = 'clone'" :class="['px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2', foldersSubTab === 'clone' ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300']">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" /></svg>
                Clonar Permisos (Usuario Espejo)
              </button>
            </div>

            <!-- TAB: VIEW / ASSIGN -->
            <div v-if="foldersSubTab === 'view'">
              <div class="flex items-center justify-between mb-5">
                <div class="flex items-center gap-2">
                  <svg class="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
                  <h3 class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Recursos de red y carpetas asignadas</h3>
                </div>
                <div class="relative w-64">
                  <input v-model="folderSearchQuery" type="text" placeholder="Buscar carpeta..." class="w-full pl-8 pr-3 py-1.5 bg-white border border-slate-200 rounded-sm text-[12px] outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-shadow">
                  <svg class="w-4 h-4 text-slate-400 absolute left-2.5 top-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                </div>
              </div>
            <div v-if="foldersLoading" class="flex flex-col items-center justify-center py-16 gap-3 border border-slate-200 rounded-sm bg-slate-50/50">
              <div class="w-6 h-6 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin"></div>
              <span class="text-[12px] text-slate-500 font-medium">Consultando permisos en el servidor...</span>
            </div>
            <div v-else-if="folderGroups.length > 0" class="border border-slate-200 rounded-sm overflow-hidden">
              <table class="w-full text-left">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200">
                    <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ruta de la Carpeta</th>
                    <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-48">Permiso</th>
                    <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider hidden lg:table-cell">Origen</th>
                    <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider text-center w-20">Acciones</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                  <tr v-for="(folder, i) in visibleFolderGroups" :key="i" class="hover:bg-slate-50/50">
                    <td class="px-4 py-3" :style="{ paddingLeft: (1 + (folder.path.split('/').length - 1) * 2) + 'rem' }">
                      <div class="flex items-center gap-2">
                        <!-- Conector visual para subcarpetas -->
                        <svg v-if="folder.path.split('/').length > 1" class="w-4 h-4 text-slate-300 shrink-0 mt-[-4px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 4v6a2 2 0 002 2h14m-4-4l4 4-4 4"/></svg>
                        
                        <template v-if="folder.path.split('/').length === 1">
                          <button v-if="hasChildren(folder.path)" @click="toggleFolder(folder.path)" class="p-0.5 hover:bg-slate-200 rounded-sm text-slate-400 transition-colors">
                            <svg class="w-3.5 h-3.5 transition-transform duration-200" :class="{ 'rotate-90': expandedFolders.has(folder.path) }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
                          </button>
                          <svg class="w-5 h-5 text-blue-500 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                          <span class="text-[12px] font-semibold text-slate-800">{{ folder.path }}</span>
                        </template>
                        <template v-else>
                          <svg class="w-5 h-5 text-amber-400 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                          <span class="text-[12px] font-semibold text-slate-700">{{ folder.path.split('/').pop() }}</span>
                        </template>
                      </div>
                    </td>
                    <td class="px-4 py-3">
                      <select v-model="folder.access" @change="updateFolderPermission(folder)" class="w-full text-[11px] font-medium bg-white border border-slate-200 rounded-sm px-2 py-1 outline-none focus:border-blue-400 cursor-pointer">
                        <option value="Control Total">Control Total</option>
                        <option value="Modificar">Modificar</option>
                        <option value="Lectura y Ejecución">Lectura y Ejecución</option>
                        <option value="Escritura">Escritura</option>
                        <option value="Lectura">Lectura</option>
                        <option value="Denegar Acceso" class="text-red-600 font-bold">Denegar Acceso</option>
                        <option value="Sin Acceso" class="text-slate-400">Sin Acceso</option>
                      </select>
                    </td>
                    <td class="px-4 py-3 text-[10px] font-mono text-slate-400 hidden lg:table-cell">{{ folder.origin }}</td>
                    <td class="px-4 py-3 text-center">
                      <button v-if="folder.access !== 'Sin Acceso'" @click="removeFolderPermission(folder)" class="text-slate-400 hover:text-red-600 transition-colors p-1">
                        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="border border-dashed border-slate-200 rounded-sm p-10 text-center">
              <p class="text-[13px] font-medium text-slate-500">Sin acceso a carpetas</p>
            </div>
          </div>

          <!-- TAB: CLONE -->
          <div v-else-if="foldersSubTab === 'clone'" class="pt-2">
            <div class="bg-indigo-50 border-l-4 border-indigo-500 p-4 rounded-md mb-6">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-indigo-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <p class="text-sm text-indigo-700">
                    Ingresa el nombre del <strong>Usuario Origen (Plantilla)</strong>. Se calcularán sus permisos y se copiarán a <strong>{{ userProfile?.username }}</strong> sin afectar sus permisos actuales.
                  </p>
                </div>
              </div>
            </div>

            <div class="flex items-end gap-4 mb-6 bg-white p-4 rounded-lg border border-slate-200">
              <div class="flex-1 max-w-sm">
                <label class="block text-xs font-medium text-slate-700 mb-1">Usuario Origen (sAMAccountName)</label>
                <input v-model="cloneSourceUser" @keyup.enter="analyzeClone" type="text" placeholder="Ej. j.perez" class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none" :disabled="isAnalyzingClone || isExecutingClone">
              </div>
              <button @click="analyzeClone" :disabled="!cloneSourceUser || isAnalyzingClone || isExecutingClone" class="bg-slate-800 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-slate-700 disabled:opacity-50 transition-colors flex items-center gap-2">
                <svg v-if="isAnalyzingClone" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
                Comparar Permisos
              </button>
            </div>

            <!-- Errores -->
            <div v-if="cloneAnalyzeError" class="bg-red-50 text-red-600 p-3 rounded-md text-sm border border-red-100 mb-4">{{ cloneAnalyzeError }}</div>
            <div v-if="cloneExecuteError" class="bg-red-50 text-red-600 p-3 rounded-md text-sm border border-red-100 mb-4">{{ cloneExecuteError }}</div>
            <div v-if="cloneExecuteSuccess" class="bg-emerald-50 text-emerald-700 p-4 rounded-md text-sm border border-emerald-100 mb-4">
              <p class="font-bold mb-2 flex items-center gap-2">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg>
                Clonación completada con éxito.
              </p>
              <ul class="list-disc pl-5 space-y-1 mt-2 text-xs">
                <li v-for="(r, i) in cloneResults" :key="i">{{ r }}</li>
              </ul>
            </div>

            <!-- Vista Previa -->
            <div v-if="cloneDelta && !cloneExecuteSuccess" class="bg-white border border-slate-200 rounded-lg p-5">
              <h3 class="text-sm font-semibold text-slate-900 mb-4">
                Permisos a agregar para {{ userProfile?.username }}
              </h3>
              
              <div v-if="cloneTotalChanges === 0" class="text-center py-8 bg-slate-50 rounded-lg border border-slate-100">
                <p class="text-sm text-slate-500 font-medium">El usuario ya cuenta con los mismos accesos (o superiores).</p>
                <p class="text-xs text-slate-400 mt-1">No se detectaron diferencias para clonar.</p>
              </div>

              <div v-else class="space-y-6">
                <!-- Grupos AD -->
                <div v-if="cloneDelta.groups_to_add?.length > 0">
                  <h4 class="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Se unirá a estos Grupos de AD:</h4>
                  <div class="flex flex-wrap gap-2">
                    <span v-for="grp in cloneDelta.groups_to_add" :key="grp" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs font-medium text-slate-700">
                      <svg class="w-3.5 h-3.5 text-indigo-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                      {{ grp }}
                    </span>
                  </div>
                </div>

                <!-- Carpetas -->
                <div v-if="cloneDelta.folders_to_add?.length > 0">
                  <h4 class="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Se otorgarán estos permisos de carpeta:</h4>
                  <ul class="border border-slate-200 rounded-md divide-y divide-slate-100">
                    <li v-for="(fld, i) in cloneDelta.folders_to_add" :key="i" class="p-3 flex items-center justify-between text-sm hover:bg-slate-50">
                      <div class="flex items-center gap-3">
                        <svg class="w-4 h-4 text-blue-500 shrink-0" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                        <span class="font-medium text-slate-700">{{ fld.path }}</span>
                      </div>
                      <span class="inline-flex items-center rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700 ring-1 ring-inset ring-blue-700/20">
                        {{ fld.access }}
                      </span>
                    </li>
                  </ul>
                </div>
                
                <div class="pt-4 flex justify-end">
                  <button @click="executeClone" :disabled="isExecutingClone" class="bg-indigo-600 text-white px-5 py-2.5 rounded-md text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm">
                    <svg v-if="isExecutingClone" class="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    Confirmar y Aplicar Clonación
                  </button>
                </div>
              </div>
            </div>
          </div>
          </div>
          
          <div v-else-if="activeTab==='email-delegation'">
            <div class="flex justify-between items-center mb-5 pb-3 border-b border-slate-100">
              <div>
                <h2 class="text-[14px] font-bold text-slate-800 uppercase tracking-wide">Correo (Delegación)</h2>
                <p class="text-[11px] text-slate-500 mt-0.5">Administre permisos de buzón (Send As, Full Access) vía Exchange Online</p>
              </div>
              <button @click="fetchDelegates" class="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                Actualizar
              </button>
            </div>

            <div class="bg-white border border-slate-200 rounded-md shadow-sm p-5 mb-5">
              <h3 class="text-[12px] font-bold text-slate-700 mb-3 uppercase tracking-wider">Asignar Permiso</h3>
              <div class="flex flex-wrap items-end gap-3">
                <div class="flex-1 min-w-[250px] relative">
                  <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Usuario Delegado</label>
                  <input 
                    v-model="delegateSearch" 
                    @focus="delegateSuggestions.length > 0 && (showDelegateSuggestions = true)"
                    @blur="hideDelegateSuggestions"
                    type="text" 
                    placeholder="Ej. jperez@empresa.com o Juan Pérez" 
                    class="w-full bg-white border border-slate-200 rounded-sm text-[13px] text-slate-800 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <!-- Custom Dropdown para Autocompletado -->
                  <div v-if="showDelegateSuggestions" class="absolute left-0 right-0 top-full mt-1 bg-white border border-slate-200 shadow-lg rounded-sm z-50 max-h-60 overflow-y-auto">
                    <ul>
                      <li 
                        v-for="user in delegateSuggestions" 
                        :key="user.userPrincipalName || user.username" 
                        @mousedown.prevent="selectDelegateSuggestion(user)"
                        class="px-3 py-2 text-[12px] hover:bg-blue-50 cursor-pointer border-b border-slate-100 last:border-0"
                      >
                        <div class="font-bold text-slate-800">{{ user.fullName }}</div>
                        <div class="text-[11px] text-slate-500 font-mono">{{ user.userPrincipalName || user.username }}</div>
                      </li>
                    </ul>
                  </div>
                </div>
                <div class="w-48">
                  <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Nivel de Acceso</label>
                  <select v-model="selectedDelegatePermission" class="w-full bg-white border border-slate-200 rounded-sm text-[13px] text-slate-800 px-3 py-2 focus:outline-none focus:ring-1 focus:ring-blue-500">
                    <option value="SendAs">Send As (Enviar como)</option>
                    <option value="SendOnBehalf">Send on Behalf (En nombre de)</option>
                    <option value="FullAccess">Full Access (Acceso Total)</option>
                  </select>
                </div>
                <button @click="assignDelegate" :disabled="isAssigningDelegate || !delegateSearch" class="bg-blue-600 text-white px-5 py-2 rounded-sm text-[13px] font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2">
                  <svg v-if="isAssigningDelegate" class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Agregar
                </button>
              </div>
            </div>

            <div class="bg-white border border-slate-200 rounded-md shadow-sm flex flex-col">
              <div class="bg-slate-50 border-b border-slate-200 px-4 py-2.5">
                <h3 class="text-[11px] font-bold text-slate-600 uppercase tracking-wider">Delegados Actuales</h3>
              </div>
              <div v-if="loadingDelegates" class="p-8 flex justify-center">
                <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <div v-else-if="emailDelegates.length > 0" class="overflow-x-auto">
                <table class="w-full text-left">
                  <thead class="bg-white border-b border-slate-100">
                    <tr>
                      <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Usuario Delegado</th>
                      <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Permiso</th>
                      <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider w-24 text-center">Acciones</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100">
                    <tr v-for="del in emailDelegates" :key="del.user + del.permission" class="hover:bg-slate-50/50 transition-colors group">
                      <td class="px-4 py-2.5 text-[12px] text-slate-800 font-medium">
                        <div class="flex items-center gap-2">
                          <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                          {{ del.user }}
                        </div>
                      </td>
                      <td class="px-4 py-2.5 text-[11px] font-bold text-indigo-700">
                        <span class="bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100 uppercase tracking-wide">{{ del.permission }}</span>
                      </td>
                      <td class="px-4 py-2.5 text-center">
                        <button @click="removeDelegate(del.user, del.permission)" class="text-slate-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-all p-1 rounded hover:bg-red-50">
                          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="p-8 text-center text-[12px] text-slate-500">
                No hay delegados asignados a este buzón.
              </div>
            </div>
          </div>

          <div v-else-if="activeTab==='licenses'">
            <div class="flex justify-between items-center mb-5 pb-3 border-b border-slate-100">
              <div>
                <h2 class="text-[14px] font-bold text-slate-800 uppercase tracking-wide">Licencias y Aplicaciones</h2>
                <p class="text-[11px] text-slate-500 mt-0.5">Administre el acceso a los servicios de M365 (Sincronizado vía Microsoft Graph)</p>
              </div>
              <button @click="fetchLicenses" class="flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                Sincronizar
              </button>
            </div>

            <div v-if="fetchingLicenses" class="py-12 flex flex-col items-center border border-slate-200 rounded-md bg-slate-50/50">
              <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-3"></div>
              <span class="text-[12px] text-slate-500 font-medium">Sincronizando con Microsoft Graph...</span>
            </div>
            
            <div v-else class="grid grid-cols-1 md:grid-cols-12 gap-5">
              
              <!-- Columna Izquierda: Licencias Asignadas (Span 8) -->
              <div class="md:col-span-8 bg-white border border-slate-200 rounded-md shadow-sm flex flex-col">
                <div class="bg-slate-50 border-b border-slate-200 px-4 py-2.5">
                  <h3 class="text-[11px] font-bold text-slate-600 uppercase tracking-wider">Licencias actuales del usuario</h3>
                </div>
                
                <div v-if="userLicenses.length > 0" class="flex-1">
                  <table class="w-full text-left">
                    <thead class="bg-white border-b border-slate-100">
                      <tr>
                        <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">Producto (M365)</th>
                        <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider w-48">ID de SKU</th>
                        <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider w-24 text-right">Acciones</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                      <tr v-for="lic in userLicenses" :key="lic.skuId" class="hover:bg-slate-50/50 transition-colors">
                        <td class="px-4 py-2.5 text-[12px] text-slate-800 font-semibold flex items-center gap-2">
                          <svg class="w-4 h-4 text-blue-500" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z"/></svg>
                          {{ getLicenseName(lic.skuId, lic.skuPartNumber) }}
                        </td>
                        <td class="px-4 py-2.5 text-[11px] font-mono text-slate-500">
                          {{ lic.skuId }}
                        </td>
                        <td class="px-4 py-2.5 text-right">
                          <button 
                            @click="removeLicense(lic.skuId)" 
                            :disabled="removingLicense === lic.skuId"
                            class="text-[11px] font-bold text-red-500 hover:text-red-700 hover:underline disabled:opacity-50 transition-colors"
                          >
                            <span v-if="removingLicense === lic.skuId" class="inline-block animate-spin mr-1">↻</span>
                            {{ removingLicense === lic.skuId ? 'Quitando...' : 'Quitar' }}
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="py-12 flex-1 flex items-center justify-center text-center">
                  <span class="text-[12px] font-medium text-slate-400">Este usuario no tiene licencias asignadas.</span>
                </div>
              </div>
              
              <!-- Columna Derecha: Asignar nueva licencia (Span 4) -->
              <div class="md:col-span-4 bg-white border border-slate-200 rounded-md shadow-sm p-4 flex flex-col h-fit">
                <h3 class="text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-4 border-b border-slate-100 pb-2">Asignar nueva licencia</h3>
                
                <div class="flex flex-col gap-3">
                  <div class="relative">
                    <select v-model="selectedSku" class="w-full h-[36px] pl-3 pr-8 text-[12px] font-medium text-slate-700 bg-slate-50 border border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none rounded appearance-none cursor-pointer transition-colors">
                      <option value="" disabled>Seleccione un plan de licencia...</option>
                      <option 
                        v-for="sku in availableLicenses" 
                        :key="sku.skuId" 
                        :value="sku.skuId"
                        :disabled="((sku.prepaidUnits?.enabled || 0) - sku.consumedUnits) <= 0"
                      >
                        {{ getLicenseName(sku.skuId, sku.skuPartNumber) }} ({{ Math.max(0, (sku.prepaidUnits?.enabled || 0) - sku.consumedUnits) }} disponibles) {{ ((sku.prepaidUnits?.enabled || 0) - sku.consumedUnits) < 0 ? `(Sobreasignadas: ${sku.consumedUnits - (sku.prepaidUnits?.enabled || 0)}) - Sin stock` : (((sku.prepaidUnits?.enabled || 0) - sku.consumedUnits) === 0 ? '- Sin stock' : '') }}
                      </option>
                    </select>
                    <svg class="w-4 h-4 text-slate-500 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                  
                  <button @click="assignLicense" :disabled="!selectedSku || assigningLicense" class="w-full flex items-center justify-center gap-2 h-[36px] text-[12px] font-bold rounded text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-700 shadow-sm">
                    <span v-if="assigningLicense" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
                    <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                    {{ assigningLicense ? 'Asignando...' : 'Asignar Licencia' }}
                  </button>
                </div>
              </div>
              
            </div>
          </div>

          <div v-else-if="activeTab==='alias'">
            <div class="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-5 pb-3 border-b border-slate-100">
              <div>
                <h2 class="text-[14px] font-bold text-slate-800 uppercase tracking-wide">Alias de Correo (ProxyAddresses)</h2>
                <p class="text-[11px] text-slate-500 mt-0.5">Gestione las direcciones de correo secundarias (Exchange/Entra ID)</p>
              </div>
              
              <!-- Formulario Compacto Flex -->
              <div class="flex items-center gap-2 bg-slate-50 border border-slate-200 p-1.5 rounded-md shadow-sm w-full md:w-auto">
                <select v-model="newAliasPrefix" class="bg-white border border-slate-300 rounded text-[11px] px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono text-slate-700 h-[30px]">
                  <option value="smtp:">smtp:</option>
                  <option value="SMTP:">SMTP:</option>
                  <option value="SIP:">SIP:</option>
                </select>
                <input v-model="newAlias" type="text" placeholder="alias@dominio.com" class="w-full md:w-48 px-3 py-1.5 text-[11px] border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono transition-all h-[30px]" @keydown.enter="addAlias" />
                <button @click="addAlias" :disabled="aliasLoading || !newAlias.trim()" class="px-3 h-[30px] bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-bold rounded disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5 shrink-0">
                  <span v-if="aliasLoading" class="w-3 h-3 border-2 border-white/50 border-t-white rounded-full animate-spin"></span>
                  <svg v-else class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                  Agregar
                </button>
              </div>
            </div>

            <div v-if="aliasStatus" class="mb-4 p-2 bg-blue-50 text-blue-700 text-[11px] font-medium rounded border border-blue-100 flex items-center gap-2">
              <svg class="w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {{ aliasStatus }}
            </div>

            <div class="border border-slate-200 rounded-md overflow-hidden bg-white shadow-sm">
              <div class="bg-slate-50 border-b border-slate-200 px-4 py-2 flex items-center justify-between">
                <h3 class="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Direcciones Actuales</h3>
                <span class="text-[10px] text-slate-400 font-medium bg-white px-2 py-0.5 rounded border border-slate-100">{{ userProfile.proxyAddresses?.length || 0 }} registradas</span>
              </div>
              
              <ul v-if="userProfile.proxyAddresses && userProfile.proxyAddresses.length > 0" class="divide-y divide-slate-100">
                <li v-for="alias in userProfile.proxyAddresses" :key="alias" class="flex items-center justify-between px-4 py-1.5 hover:bg-slate-50/50 group transition-colors">
                  <div class="flex items-center gap-2.5">
                    <svg class="w-3.5 h-3.5 text-slate-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" /></svg>
                    <span :class="['font-mono text-[11px]', alias.startsWith('SMTP:') ? 'font-bold text-slate-800' : 'text-slate-600 font-medium']">{{ alias }}</span>
                    <span v-if="alias.startsWith('SMTP:')" class="text-[9px] bg-emerald-100 text-emerald-700 px-1.5 rounded font-bold uppercase tracking-wider">Primario</span>
                  </div>
                  <button @click="removeAlias(alias)" :disabled="aliasLoading" class="text-slate-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50 p-1" title="Eliminar Alias">
                    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                  </button>
                </li>
              </ul>
              
              <div v-else class="p-6 text-center bg-slate-50/50">
                <p class="text-[12px] text-slate-400 font-medium">Este usuario no tiene alias configurados.</p>
              </div>
            </div>
          </div>

          <div v-else-if="activeTab==='entra'" class="bg-slate-50 rounded-lg p-5 w-full">
            <div class="w-full">
              
              <div v-if="entraStatusLoading" class="flex justify-center py-12">
                <div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>

              <div v-else-if="userEntraStatus && userEntraStatus.id" class="grid grid-cols-1 md:grid-cols-12 gap-5">
                
                <!-- Columna Izquierda: Información Básica (Span 8) -->
                <div class="md:col-span-8 bg-white border border-slate-200 shadow-sm rounded-md p-5 flex flex-col">
                  <div class="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
                    <h2 class="text-[14px] font-bold text-slate-800 uppercase tracking-wide">Información Básica</h2>
                    <button 
                      @click="syncLocalAD" 
                      :disabled="isSyncingAd"
                      class="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded transition-colors disabled:opacity-50"
                    >
                      <svg v-if="isSyncingAd" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                      {{ isSyncingAd ? 'Sincronizando...' : 'Forzar Sinc.' }}
                    </button>
                  </div>
                  
                  <div class="grid grid-cols-2 gap-4 flex-1">
                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-1">Estado de la cuenta</span>
                      <div class="flex items-center gap-2">
                        <svg v-if="userEntraStatus.accountEnabled" class="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        <svg v-else class="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                        <span class="text-[13px] font-medium text-slate-800">{{ userEntraStatus.accountEnabled ? 'Habilitado' : 'Deshabilitado' }}</span>
                      </div>
                    </div>
                    
                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-1">Sincronización local</span>
                      <div class="flex items-center gap-2">
                        <svg v-if="userEntraStatus.onPremisesSyncEnabled" class="w-4 h-4 text-emerald-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        <svg v-else class="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd"/></svg>
                        <span class="text-[13px] font-medium text-slate-800">{{ userEntraStatus.onPremisesSyncEnabled ? 'Sí' : 'No (Solo nube)' }}</span>
                      </div>
                    </div>

                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-1">Id. del objeto</span>
                      <span class="text-[12px] font-mono text-slate-600 flex items-center gap-1.5">
                        {{ userEntraStatus.id.substring(0, 18) }}...
                        <button @click="navigator.clipboard.writeText(userEntraStatus.id)" class="text-blue-500 hover:text-blue-700" title="Copiar ID Completo"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg></button>
                      </span>
                    </div>

                    <div class="flex flex-col">
                      <span class="text-[11px] text-slate-400 font-bold uppercase tracking-wider mb-1">Última sincronización</span>
                      <span class="text-[13px] font-medium text-slate-800">{{ userEntraStatus.onPremisesLastSyncDateTime ? new Date(userEntraStatus.onPremisesLastSyncDateTime).toLocaleString() : '--' }}</span>
                    </div>
                  </div>
                </div>

                <!-- Columna Derecha: Seguridad de Acceso (Span 4) -->
                <div class="md:col-span-4 bg-white border border-slate-200 shadow-sm rounded-md p-5 flex flex-col">
                  <div class="flex items-center mb-4 border-b border-slate-100 pb-3">
                    <h2 class="text-[14px] font-bold text-slate-800 uppercase tracking-wide">Seguridad (Nube)</h2>
                  </div>
                  <div class="flex flex-col gap-3 flex-1 justify-center">
                    <button @click="resetMFA" :disabled="resetMfaLoading" class="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-[12px] font-bold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 hover:border-slate-400 transition-colors disabled:opacity-50 shadow-sm">
                      <svg v-if="resetMfaLoading" class="w-4 h-4 animate-spin text-slate-600" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      <svg v-else class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
                      {{ resetMfaLoading ? 'Restableciendo...' : 'Restablecer MFA' }}
                    </button>
                    
                    <button @click="revokeSessions" :disabled="revokeLoading" class="flex items-center justify-center gap-2 w-full px-4 py-2.5 text-[12px] font-bold text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50 hover:border-slate-400 transition-colors disabled:opacity-50 shadow-sm">
                      <svg v-if="revokeLoading" class="w-4 h-4 animate-spin text-slate-600" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                      <svg v-else class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                      {{ revokeLoading ? 'Cerrando Sesiones...' : 'Cerrar Sesiones Activas' }}
                    </button>
                  </div>
                </div>

                <!-- Fila Inferior: Auditoría de Atributos (Span 12) -->
                <div class="md:col-span-12 bg-white border border-slate-200 shadow-sm rounded-md p-5">
                  <h2 class="text-[14px] font-bold text-slate-800 uppercase tracking-wide mb-4 border-b border-slate-100 pb-3">Auditoría de atributos</h2>
                  
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                    
                    <!-- UPN -->
                    <div class="flex items-start gap-3">
                      <div class="shrink-0 mt-0.5">
                        <svg v-if="userProfile.userPrincipalName?.toLowerCase() === userEntraStatus.userPrincipalName?.toLowerCase()" class="w-5 h-5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20" title="Coinciden"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        <svg v-else class="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20" title="Diferencia"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                      </div>
                      <div class="w-full">
                        <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Nombre principal de usuario (UPN)</h3>
                        <div class="grid grid-cols-2 gap-4 bg-slate-50/50 rounded border border-slate-100 p-2.5">
                          <div>
                            <span class="block text-[10px] text-slate-500 mb-0.5">LOCAL</span>
                            <span class="text-[13px] font-medium text-slate-800 break-all">{{ userProfile.userPrincipalName || '--' }}</span>
                          </div>
                          <div>
                            <span class="block text-[10px] text-slate-500 mb-0.5">NUBE</span>
                            <span class="text-[13px] font-medium text-slate-800 break-all">{{ userEntraStatus.userPrincipalName || '--' }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- Mail -->
                    <div class="flex items-start gap-3">
                      <div class="shrink-0 mt-0.5">
                        <svg v-if="userProfile.email?.toLowerCase() === userEntraStatus.mail?.toLowerCase()" class="w-5 h-5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20" title="Coinciden"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        <svg v-else class="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20" title="Diferencia"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                      </div>
                      <div class="w-full">
                        <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Correo electrónico</h3>
                        <div class="grid grid-cols-2 gap-4 bg-slate-50/50 rounded border border-slate-100 p-2.5">
                          <div>
                            <span class="block text-[10px] text-slate-500 mb-0.5">LOCAL</span>
                            <span class="text-[13px] font-medium text-slate-800 break-all">{{ userProfile.email || '--' }}</span>
                          </div>
                          <div>
                            <span class="block text-[10px] text-slate-500 mb-0.5">NUBE</span>
                            <span class="text-[13px] font-medium text-slate-800 break-all">{{ userEntraStatus.mail || '--' }}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <!-- ProxyAddresses -->
                    <div class="flex items-start gap-3 md:col-span-2">
                      <div class="shrink-0 mt-0.5">
                        <svg v-if="JSON.stringify([...(userProfile.proxyAddresses||[])].sort()) === JSON.stringify([...(userEntraStatus.proxyAddresses||[])].sort())" class="w-5 h-5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20" title="Coinciden"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        <svg v-else class="w-5 h-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20" title="Diferencia"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                      </div>
                      <div class="w-full">
                        <h3 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">Alias (ProxyAddresses)</h3>
                        <div class="grid grid-cols-2 gap-4 bg-slate-50/50 rounded border border-slate-100 p-2.5">
                          <div>
                            <span class="block text-[10px] text-slate-500 mb-1">LOCAL</span>
                            <ul v-if="userProfile.proxyAddresses && userProfile.proxyAddresses.length > 0" class="space-y-1">
                              <li v-for="alias in userProfile.proxyAddresses" :key="alias" class="text-[12px] font-mono text-slate-800 break-all">{{ alias }}</li>
                            </ul>
                            <span v-else class="text-[12px] italic text-slate-400">Sin alias</span>
                          </div>
                          <div>
                            <span class="block text-[10px] text-slate-500 mb-1">NUBE</span>
                            <ul v-if="userEntraStatus.proxyAddresses && userEntraStatus.proxyAddresses.length > 0" class="space-y-1">
                              <li v-for="alias in userEntraStatus.proxyAddresses" :key="alias" class="text-[12px] font-mono text-slate-800 break-all">{{ alias }}</li>
                            </ul>
                            <span v-else class="text-[12px] italic text-slate-400">Sin alias</span>
                          </div>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>
              </div>
              <div v-else-if="userEntraStatus && userEntraStatus.error">
                <div class="flex items-center gap-3 p-4 bg-red-50 text-red-800 rounded-sm">
                  <svg class="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
                  <span>{{ userEntraStatus.error }}</span>
                </div>
              </div>

              <div v-else-if="userEntraStatus && userEntraStatus.notSynced" class="flex flex-col items-center justify-center py-16 text-center">
                <svg class="w-16 h-16 text-slate-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
                <h3 class="text-[15px] font-semibold text-slate-600 mb-1">Usuario no sincronizado</h3>
                <p class="text-[12px] text-slate-400 max-w-sm">Este usuario aún no existe en Microsoft Entra ID. Ejecute una sincronización de AD Connect o espere al próximo ciclo automático para que aparezca en la nube.</p>
                <button @click="syncLocalAD" :disabled="isSyncingAd" class="mt-4 flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded transition-colors disabled:opacity-50">
                  <svg v-if="isSyncingAd" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                  {{ isSyncingAd ? 'Sincronizando...' : 'Forzar sincronización de AD Connect' }}
                </button>
              </div>

              <div v-else-if="userEntraStatus && userEntraStatus.loading" class="flex flex-col items-center justify-center py-20 gap-3">
                <div class="w-8 h-8 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                <span class="text-[13px] text-slate-500">Consultando con Microsoft Graph...</span>
              </div>

              <div v-else class="flex flex-col items-center justify-center py-16 text-center">
                <svg class="w-16 h-16 text-slate-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
                <p class="text-[12px] text-slate-400">No se pudo cargar la información de Entra ID para este usuario.</p>
              </div>
        </div>
      </div>
    </template>
  </div>
  </div>
</div>
    <!-- Modal de Offboarding Automático -->
    <BaseModal 
      :show="showOffboardModal" 
      title="Confirmar baja de usuario (Offboarding)" 
      @close="showOffboardModal = false"
    >
      <template #body>
        <div v-if="!offboardResult">
          <div class="mb-4 space-y-2">
            <p>Al confirmar el offboarding para <strong>{{ userProfile.displayName }}</strong> ({{ userProfile.username }}), el sistema realizará automáticamente las siguientes acciones:</p>
            <ul class="list-disc pl-5 space-y-1 mt-2">
              <li>Deshabilitar la cuenta en el Active Directory local.</li>
              <li>Revocar inmediatamente todas las sesiones de inicio de sesión en Entra ID / Microsoft 365.</li>
              <li>Remover todas las licencias de Office/Microsoft 365 asignadas al usuario.</li>
              <li>Generar un script sugerido para convertir su buzón a Compartido.</li>
            </ul>
          </div>
        </div>
        
        <div v-else>
          <div :class="['mb-4 p-4 rounded-lg border', offboardResult.success ? 'bg-emerald-50 border-emerald-200 text-emerald-800' : 'bg-red-50 border-red-200 text-red-800']">
            <h4 class="font-bold mb-2">{{ offboardResult.message }}</h4>
            <ul v-if="offboardResult.results" class="list-disc pl-5 space-y-1">
              <li v-for="(res, i) in offboardResult.results" :key="i">{{ res }}</li>
            </ul>
          </div>
          
          <div v-if="offboardResult.success && offboardResult.exchange_script" class="mt-4">
            <label class="block font-bold text-gray-500 uppercase tracking-widest mb-2 text-xs">Script de Exchange Online (Buzón Compartido)</label>
            <div class="relative bg-gray-900 rounded-lg p-3 border border-gray-700">
              <code class="text-emerald-400 font-mono break-all">{{ offboardResult.exchange_script }}</code>
            </div>
            <p class="text-gray-400 mt-2 text-xs">Copia y ejecuta este script en Exchange Online PowerShell para conservar el buzón sin costo.</p>
          </div>
        </div>
      </template>

      <template #footer>
        <div v-if="!offboardResult" class="flex gap-3 w-full justify-end">
          <button @click="showOffboardModal = false" class="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 font-medium transition-colors">
            Cancelar
          </button>
          <button @click="offboardUser" :disabled="offboardLoading" class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg disabled:opacity-50 flex items-center gap-2 transition-colors">
            <span v-if="offboardLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            Confirmar Baja
          </button>
        </div>
        <div v-else class="flex justify-end w-full">
          <button @click="showOffboardModal = false" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition-colors">
            Cerrar
          </button>
        </div>
      </template>
    </BaseModal>
    <!-- Toast Notification -->
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      <transition enter-active-class="transition ease-out duration-300 transform" enter-from-class="opacity-0 translate-y-[-1rem] scale-95" enter-to-class="opacity-100 translate-y-0 scale-100" leave-active-class="transition ease-in duration-200" leave-from-class="opacity-100 scale-100" leave-to-class="opacity-0 scale-95">
        <div v-if="showSyncModal" :class="['pointer-events-auto flex items-start p-4 rounded-lg shadow-lg border max-w-sm w-full', syncModalType === 'success' ? 'bg-white border-emerald-100' : 'bg-white border-red-100']">
          <div :class="['flex-shrink-0 mr-3', syncModalType === 'success' ? 'text-emerald-500' : 'text-red-500']">
            <svg v-if="syncModalType === 'success'" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          </div>
          <div class="flex-1 pt-0.5">
            <h3 class="text-[13px] font-semibold text-slate-800">{{ syncModalTitle }}</h3>
            <p class="mt-1 text-[12px] text-slate-500">{{ syncModalMessage }}</p>
          </div>
          <button @click="showSyncModal = false" class="ml-4 flex-shrink-0 text-slate-400 hover:text-slate-600 focus:outline-none">
            <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </transition>
    </div>
</template>
