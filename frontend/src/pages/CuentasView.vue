<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import CreateUserDrawer from '../components/CreateUserDrawer.vue'
import BaseModal from '../components/common/BaseModal.vue'
import DiagnoseModal from '../components/DiagnoseModal.vue'

const router = useRouter()
const route = useRoute()

const showCreateDrawer = ref(false)
const showDiagnoseModal = ref(false)
const searchQuery = ref('')
const users = ref([])
const isLoading = ref(false)  // true solo mientras no tenemos NINGÚN dato
const isStreaming = ref(false) // true mientras el SSE sigue trayendo más datos
const streamProgress = ref(0)  // usuarios recibidos hasta ahora
const streamTotal = ref(0)     // total estimado del servidor
let searchTimeout = null
let sseController = null       // AbortController para cancelar SSE si el usuario navega

const activeFilter = ref('activos') // todos, activos, deshabilitados, bloqueados

const API_BASE = '/api/v1'

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function authFetch(url, opts = {}) {
  const token = localStorage.getItem('access_token')
  opts.headers = { ...(opts.headers || {}), 'Authorization': `Bearer ${token}` }
  return fetch(url, opts)
}

// â”€â”€ Avatar Colors (deterministic from initials) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const avatarColors = [
  'bg-blue-600', 'bg-emerald-600', 'bg-violet-600', 'bg-amber-600',
  'bg-rose-600', 'bg-cyan-600', 'bg-indigo-600', 'bg-teal-600',
  'bg-pink-600', 'bg-sky-600', 'bg-fuchsia-600', 'bg-lime-600',
]
function getAvatarColor(name) {
  if (!name) return avatarColors[0]
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return avatarColors[Math.abs(hash) % avatarColors.length]
}
function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
}

const statusColors = {
  active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  locked: 'bg-red-50 text-red-700 border-red-200',
  disabled: 'bg-slate-100 text-slate-500 border-slate-200',
}
const statusLabels = {
  active: 'Activo',
  locked: 'Bloqueado',
  disabled: 'Deshabilitado',
}

// â”€â”€ Selection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const selectedUsers = ref(new Set())
const selectAll = ref(false)

function toggleSelectAll() {
  if (selectAll.value) {
    let added = 0;
    paginatedUsers.value.forEach(u => {
      if (selectedUsers.value.size < 3 && !selectedUsers.value.has(u.username)) {
        selectedUsers.value.add(u.username)
        added++;
      }
    })
    if (paginatedUsers.value.length > 3 && added > 0) {
      alert("Límite de seguridad (Prevención de desastres): Solo se han seleccionado hasta 3 cuentas de esta página.")
    } else if (added === 0 && selectedUsers.value.size >= 3) {
      alert("Límite de seguridad: No puedes seleccionar más de 3 cuentas en total.")
    }
    // Si no se pudieron seleccionar todos de la página, quitamos el check de selectAll
    if (paginatedUsers.value.some(u => !selectedUsers.value.has(u.username))) {
      selectAll.value = false
    }
  } else {
    paginatedUsers.value.forEach(u => selectedUsers.value.delete(u.username))
  }
  selectedUsers.value = new Set(selectedUsers.value)
}

function toggleUser(username) {
  if (selectedUsers.value.has(username)) {
    selectedUsers.value.delete(username)
  } else {
    if (selectedUsers.value.size >= 3) {
      alert("Límite de seguridad (Prevención de desastres): Solo puedes seleccionar un máximo de 3 cuentas al mismo tiempo para evitar daños masivos accidentales en el Directorio Activo.")
      return // Evita que se seleccione
    }
    selectedUsers.value.add(username)
  }
  // Force reactivity
  selectedUsers.value = new Set(selectedUsers.value)
  selectAll.value = paginatedUsers.value.length > 0 && paginatedUsers.value.every(u => selectedUsers.value.has(u.username))
}

const hasSelection = computed(() => selectedUsers.value.size > 0)
const hasSingleSelection = computed(() => selectedUsers.value.size === 1)
const singleSelectedUser = computed(() => hasSingleSelection.value ? Array.from(selectedUsers.value)[0] : null)
const isSingleCloudUser = computed(() => {
  if (!hasSingleSelection.value) return false
  const username = singleSelectedUser.value
  return licensesSummary.value[username.toLowerCase()] === true
})

// â”€â”€ Copy UPN â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const copiedUpn = ref(null)
let copyTimeout = null
function copyUpn(upn, event) {
  event.stopPropagation()
  navigator.clipboard.writeText(upn)
  copiedUpn.value = upn
  if (copyTimeout) clearTimeout(copyTimeout)
  copyTimeout = setTimeout(() => copiedUpn.value = null, 1500)
}

// â”€â”€ Kebab Menu & MFA Context â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const openMenuUser = ref(null)
const menuPosition = ref({ top: 0, left: 0 })
const isMfaContext = ref(false)
const mfaLoading = ref(false)
const mfaTargetUser = ref(null)
const mfaState = ref('disabled')
const mfaActionLoading = ref(false)

function toggleMenu(username, event) {
  event.stopPropagation()
  if (openMenuUser.value === username) {
    openMenuUser.value = null
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  menuPosition.value = {
    top: rect.bottom + 4,
    left: rect.right - 180,
  }
  openMenuUser.value = username
}
function closeMenu() { openMenuUser.value = null }
function handleGlobalClick() { closeMenu() }
onMounted(() => document.addEventListener('click', handleGlobalClick))
onUnmounted(() => document.removeEventListener('click', handleGlobalClick))

async function enterMfaContext(username) {
  closeMenu()
  isMfaContext.value = true
  mfaTargetUser.value = username
  mfaLoading.value = true
  selectedUsers.value = new Set([username])
  
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${username}/mfa-status`)
    if (res.ok) {
      const data = await res.json()
      mfaState.value = data.mfaState || 'disabled'
    } else {
      mfaState.value = 'disabled'
    }
  } catch (e) {
    console.error("Error fetching MFA status", e)
    mfaState.value = 'disabled'
  }
  
  // Sutil delay para efecto de carga fluida
  setTimeout(() => mfaLoading.value = false, 500)
}

function exitMfaContext() {
  isMfaContext.value = false
  mfaTargetUser.value = null
  selectedUsers.value = new Set()
}

async function changeMfaStatus(enable) {
  mfaActionLoading.value = true
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${mfaTargetUser.value}/mfa-status`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enable })
    })
    if (res.ok) {
      mfaState.value = enable ? 'enabled' : 'disabled'
      alert(`MFA ${enable ? 'Habilitado' : 'Deshabilitado'} correctamente.`)
    } else {
      const data = await res.json()
      alert("Error al cambiar estado de MFA: " + (data.detail || data.message || "Desconocido"))
    }
  } catch (e) {
    alert("Error de red al cambiar MFA: " + e.message)
  } finally {
    mfaActionLoading.value = false
  }
}

// â”€â”€ Action Modals State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const showResetPwModal = ref(false)
const showMfaModal = ref(false)
const showOffboardModal = ref(false)
const actionTargetUser = ref(null)
const actionLoading = ref(false)
const actionResult = ref(null)

// Password reset modal specifics
const generatedPassword = ref('')
function generateSecurePassword() {
  const u = 'ABCDEFGHJKLMNPQRSTUVWXYZ', l = 'abcdefghjkmnpqrstuvwxyz', d = '23456789', s = '!@#$%&*'
  let pwd = u[~~(Math.random()*u.length)] + l[~~(Math.random()*l.length)] + d[~~(Math.random()*d.length)] + s[~~(Math.random()*s.length)]
  const all = u+l+d+s
  for (let i=0;i<10;i++) pwd += all[~~(Math.random()*all.length)]
  return pwd.split('').sort(()=>Math.random()-.5).join('')
}

// â”€â”€ Command Actions (Single User) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function commandViewProfile() {
  if (singleSelectedUser.value) router.push('/cuentas/usuario/' + singleSelectedUser.value)
}
function commandResetMfa() {
  if (singleSelectedUser.value) {
    actionTargetUser.value = singleSelectedUser.value
    actionResult.value = null
    showMfaModal.value = true
  }
}
function commandOffboard() {
  if (singleSelectedUser.value) {
    actionTargetUser.value = singleSelectedUser.value
    actionResult.value = null
    showOffboardModal.value = true
  }
}

function promptResetMfa(username) {
  actionTargetUser.value = username
  actionResult.value = null
  showMfaModal.value = true
}

// â”€â”€ API Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
async function executeResetPassword() {
  actionLoading.value = true
  actionResult.value = null
  try {
    const adminUser = JSON.parse(atob(localStorage.getItem('access_token').split('.')[1])).sub || 'admin'
    const res = await authFetch(`${API_BASE}/accounts/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: actionTargetUser.value,
        new_password: generatedPassword.value,
        must_change: true,
        unlock: true,
        admin_user: adminUser
      })
    })
    const data = await res.json()
    actionResult.value = { success: res.ok, message: res.ok ? (data.message || 'Contraseña restablecida correctamente') : (data.detail || 'Error') }
  } catch(e) {
    actionResult.value = { success: false, message: 'Error de red: ' + e.message }
  } finally {
    actionLoading.value = false
  }
}

async function executeResetMfa() {
  actionLoading.value = true
  actionResult.value = null
  try {
    const res = await authFetch(`${API_BASE}/graph/users/${actionTargetUser.value}/reset-mfa`, { method: 'POST' })
    const data = await res.json()
    actionResult.value = { success: res.ok, message: res.ok ? (data.message || 'MFA restablecido') : (data.detail || data.message || 'Error') }
  } catch(e) {
    actionResult.value = { success: false, message: 'Error de red: ' + e.message }
  } finally {
    actionLoading.value = false
  }
}

async function executeOffboard() {
  actionLoading.value = true
  actionResult.value = null
  try {
    const adminUser = JSON.parse(atob(localStorage.getItem('access_token').split('.')[1])).sub || 'admin'
    const res = await authFetch(`${API_BASE}/accounts/offboard/${actionTargetUser.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_user: adminUser })
    })
    const data = await res.json()
    actionResult.value = { success: res.ok, message: res.ok ? (data.message || 'Offboarding completado') : (data.detail || 'Error en baja') }
    if (res.ok) fetchUsers()
  } catch(e) {
    actionResult.value = { success: false, message: 'Error de red: ' + e.message }
  } finally {
    actionLoading.value = false
  }
}

// â”€â”€ Bulk Actions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const bulkLoading = ref(false)

async function bulkResetPassword() {
  if (!confirm(`¿Restablecer contraseñ     para ${selectedUsers.value.size} usuario(s)?`)) return
  bulkLoading.value = true
  const adminUser = JSON.parse(atob(localStorage.getItem('access_token').split('.')[1])).sub || 'admin'
  let success = 0, fail = 0
  for (const username of selectedUsers.value) {
    try {
      const res = await authFetch(`${API_BASE}/accounts/quick-reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, admin_user: adminUser })
      })
      if (res.ok) success++; else fail++
    } catch { fail++ }
  }
  alert(`Resultado: ${success} exitosos, ${fail} fallidos`)
  selectedUsers.value = new Set()
  selectAll.value = false
  bulkLoading.value = false
}

async function bulkUnlock() {
  if (!confirm(`¿Desbloquear ${selectedUsers.value.size} cuenta(s)?`)) return
  bulkLoading.value = true
  let success = 0, fail = 0
  for (const username of selectedUsers.value) {
    try {
      const res = await authFetch(`${API_BASE}/accounts/unlock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      })
      if (res.ok) success++; else fail++
    } catch { fail++ }
  }
  alert(`Resultado: ${success} desbloqueados, ${fail} fallidos`)
  selectedUsers.value = new Set()
  selectAll.value = false
  bulkLoading.value = false
  fetchUsers()
}

async function bulkDisable() {
  if (!confirm(`¿Bloquear inicio de sesión para ${selectedUsers.value.size} usuario(s)?`)) return
  bulkLoading.value = true
  const adminUser = JSON.parse(atob(localStorage.getItem('access_token').split('.')[1])).sub || 'admin'
  let success = 0, fail = 0
  for (const username of selectedUsers.value) {
    try {
      const res = await authFetch(`${API_BASE}/accounts/account-options/${username}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_disabled: true, admin_user: adminUser })
      })
      if (res.ok) success++; else fail++
    } catch { fail++ }
  }
  alert(`Resultado: ${success} bloqueados, ${fail} fallidos`)
  selectedUsers.value = new Set()
  selectAll.value = false
  bulkLoading.value = false
  fetchUsers()
}

function exportCsv() {
  const selected = users.value.filter(u => selectedUsers.value.has(u.username))
  const headers = ['Nombre,Usuario,Cargo,Departamento,Estado']
  const rows = selected.map(u => `"${u.fullName}","${u.userPrincipalName || u.username}","${u.title || ''}","${u.department || ''}","${statusLabels[u.status] || u.status}"`)
  const csv = [...headers, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `usuarios_${new Date().toISOString().slice(0,10)}.csv`
  link.click()
}

const lockedUsers = ref(new Set())
const seenLockedUsers = ref(new Set(JSON.parse(localStorage.getItem('seen_locked_users') || '[]')))

const newLockedUsersCount = computed(() => {
  let count = 0
  for (const user of lockedUsers.value) {
    if (!seenLockedUsers.value.has(user)) count++
  }
  return count
})

function markLockedAsSeen() {
  seenLockedUsers.value = new Set(lockedUsers.value)
  localStorage.setItem('seen_locked_users', JSON.stringify(Array.from(seenLockedUsers.value)))
}

async function fetchUsers() {
  // Si ya hay usuarios en memoria, no mostrar pantalla de carga completa
  if (users.value.length === 0) isLoading.value = true
  isStreaming.value = true
  streamProgress.value = 0
  streamTotal.value = 0

  // Cancelar SSE anterior si existe
  if (sseController) sseController.abort()
  sseController = new AbortController()

  const token = localStorage.getItem('access_token')

  try {
    // Cargar usuarios bloqueados en paralelo (es rápido)
    const resLocked = await authFetch(`${API_BASE}/accounts/locked`).catch(() => ({ ok: false, json: () => [] }))
    if (resLocked.ok) {
      const lockedData = await resLocked.json()
      lockedUsers.value = new Set(lockedData.map(u => u.username))
    }

    // Iniciar SSE stream
    const response = await fetch(`${API_BASE}/accounts/stream`, {
      headers: { 'Authorization': `Bearer ${token}` },
      signal: sseController.signal
    })

    if (!response.ok) throw new Error('Error iniciando stream')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const msg = JSON.parse(line.slice(6))
          if (msg.type === 'meta') {
            streamTotal.value = msg.total
          } else if (msg.type === 'batch') {
            if (isLoading.value) isLoading.value = false
            const newUsers = msg.users.map(u => ({
              ...u,
              status: lockedUsers.value.has(u.username) ? 'locked' : u.status
            }))
            const existingSet = new Set(users.value.map(u => u.username))
            const toAdd = newUsers.filter(u => !existingSet.has(u.username))
            if (msg.offset === 0) {
              users.value = newUsers  // Primer batch: reemplazar
            } else {
              users.value = users.value.concat(toAdd)
            }
            streamProgress.value = users.value.length

          } else if (msg.type === 'done') {
            isStreaming.value = false
            isLoading.value = false
            // Cargar licencias en background (no bloquea la UI)
            fetchLicensesSummary()

          } else if (msg.type === 'error') {
            console.error('[SSE] Error:', msg.message)
            isLoading.value = false
            isStreaming.value = false
          }
        } catch (e) { /* línea parcial, ignorar */ }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('Error en stream:', err)
      // Fallback: usar endpoint normal si SSE falla
      try {
        const res = await authFetch(`${API_BASE}/accounts/search?q=&limit=5000`)
        if (res.ok) users.value = await res.json()
      } catch { /* ignore */ }
    }
  } finally {
    isLoading.value = false
    isStreaming.value = false
  }
}

const licensesSummary = ref({})
async function fetchLicensesSummary(token) {
  try {
    const res = await authFetch(`${API_BASE}/graph/licenses/summary`)
    if (res.ok) {
      const data = await res.json()
      if (data.success) licensesSummary.value = data.data
    }
  } catch (err) {
    console.error("Error fetching licenses summary:", err)
  }
}

// BÃºsqueda en tiempo real con debounce
watch(searchQuery, (newVal) => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    fetchUsers()
  }, 300)
})

onMounted(() => {
  if (route.query.estado) {
    const validStates = ['todos', 'activos', 'deshabilitados', 'bloqueados']
    const param = route.query.estado.toLowerCase()
    if (validStates.includes(param)) activeFilter.value = param
  }
  fetchUsers()
})

onUnmounted(() => {
  // Cancelar SSE al salir de la vista para no desperdiciar recursos
  if (sseController) sseController.abort()
})

const filteredUsers = computed(() => {
  let filtered = users.value
  // Filtro por búsqueda: completamente en memoria, instantáneo
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase().trim()
    filtered = filtered.filter(u =>
      (u.fullName || '').toLowerCase().includes(q) ||
      (u.username || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q) ||
      (u.department || '').toLowerCase().includes(q)
    )
  }
  // Filtro por pestaña
  if (activeFilter.value === 'activos') filtered = filtered.filter(u => u.status === 'active')
  else if (activeFilter.value === 'deshabilitados') filtered = filtered.filter(u => u.status === 'disabled')
  else if (activeFilter.value === 'bloqueados') filtered = filtered.filter(u => u.status === 'locked')
  else if (activeFilter.value === 'licenciados') filtered = filtered.filter(u => licensesSummary.value[u.username.toLowerCase()] === true)
  else if (activeFilter.value === 'sin_licencia') filtered = filtered.filter(u => licensesSummary.value[u.username.toLowerCase()] === false)
  return filtered
})

const currentPage = ref(1)
const itemsPerPage = ref(25)
const totalPages = computed(() => Math.ceil(filteredUsers.value.length / itemsPerPage.value))
const paginatedUsers = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  return filteredUsers.value.slice(start, start + itemsPerPage.value)
})
function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }

watch([activeFilter], () => {
  currentPage.value = 1
  selectedUsers.value = new Set()
  selectAll.value = false
})

function goToUserProfile(username) {
  router.push('/cuentas/usuario/' + username)
}

function setFilter(filter) {
  activeFilter.value = filter
  router.replace({ query: { ...route.query, estado: filter } })
  if (filter === 'bloqueados') {
    markLockedAsSeen()
  }
}

</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6">
    <!-- Breadcrumb & Header -->
    <div class="mb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600 font-medium">Cuentas AD</span>
      </div>
      <h2 class="text-2xl font-semibold text-slate-900 tracking-tight">Directorio de Usuarios</h2>
    </div>

    <!-- Command Bar (Global) -->
    <div v-if="!isMfaContext" class="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-200 pb-3 gap-3">
      <div class="flex items-center gap-1 flex-wrap">
        <button @click="showDiagnoseModal = true" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"/></svg>
          Diagnóstico Express
        </button>
        <div class="w-px h-4 bg-gray-300 mx-1"></div>
        <button @click="showCreateDrawer = true" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
          Nuevo (AD)
        </button>
        <button @click="fetchUsers" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
        <button @click="bulkUnlock" :disabled="!hasSelection || bulkLoading" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default">
          <svg class="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z"/></svg>
          Desbloquear (AD)
        </button>
        <button @click="bulkResetPassword" :disabled="!hasSelection || bulkLoading" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/></svg>
          Restablecer clave (AD)
        </button>
        <button v-if="activeFilter !== 'bloqueados'" @click="enterMfaContext(singleSelectedUser)" :disabled="!isSingleCloudUser" :title="!isSingleCloudUser ? 'Solo disponible para usuarios en la nube (con licencia)' : ''" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>
          MFA por usuario (M365)
        </button>
        <button @click="bulkDisable" :disabled="!hasSelection || bulkLoading" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/></svg>
          Deshabilitar (AD)
        </button>
        <button @click="exportCsv" :disabled="!hasSelection" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          Exportar
        </button>
      </div>
      <!-- SelecciÃ³n -->
      <div class="flex items-center justify-end gap-3">
        <transition name="modal">
          <span v-if="hasSelection" class="text-[12px] text-slate-500 font-semibold transition-opacity duration-300">
            {{ selectedUsers.size }} seleccionado{{ selectedUsers.size > 1 ? 's' : '' }}
          </span>
        </transition>
      </div>
    </div>

    <!-- Command Bar (MFA Context) -->
    <transition name="modal">
      <div v-if="isMfaContext" class="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-200 pb-3 gap-3">
        <div class="flex items-center gap-1 flex-wrap">
          <button @click="exitMfaContext" class="text-[12px] font-medium text-slate-700 hover:text-blue-600 hover:bg-slate-50 px-3 py-1.5 rounded transition-colors flex items-center gap-2">
            <svg class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
            Volver a usuarios
          </button>
          <div class="w-px h-4 bg-slate-200 mx-1"></div>
          <button @click="changeMfaStatus(true)" :disabled="mfaState === 'enabled' || mfaActionLoading" class="text-[12px] font-medium text-slate-700 hover:text-blue-600 hover:bg-slate-50 px-3 py-1.5 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
            Habilitar MFA
          </button>
          <button @click="changeMfaStatus(false)" :disabled="mfaState === 'disabled' || mfaActionLoading" class="text-[12px] font-medium text-slate-700 hover:text-blue-600 hover:bg-slate-50 px-3 py-1.5 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
            Deshabilitar MFA
          </button>
          <button @click="promptResetMfa(mfaTargetUser)" :disabled="mfaActionLoading" class="text-[12px] font-medium text-slate-700 hover:text-blue-600 hover:bg-slate-50 px-3 py-1.5 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed">
            Restablecer métodos
          </button>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[12px] text-slate-500 font-medium">
            Estado de MFA: <span :class="mfaState === 'enabled' ? 'text-emerald-600 font-semibold' : 'text-slate-500 font-semibold'">{{ mfaState === 'enabled' ? 'Habilitado' : 'Deshabilitado' }}</span>
          </span>
        </div>
      </div>
    </transition>

    <!-- Filters & Search (No card, just text buttons) -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
      <div class="flex items-center gap-1 overflow-x-auto hide-scrollbar">
        <button @click="setFilter('todos')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='todos' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Todos</button>
        <button @click="setFilter('activos')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='activos' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Activos</button>
        <button @click="setFilter('deshabilitados')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='deshabilitados' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Deshabilitados</button>
        <button @click="setFilter('bloqueados')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap flex items-center gap-1.5', activeFilter==='bloqueados' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">
          Bloqueados
          <span v-if="newLockedUsersCount > 0" class="flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-white">
            {{ newLockedUsersCount > 9 ? '9+' : newLockedUsersCount }}
          </span>
        </button>
        <div class="w-px h-4 bg-gray-200 mx-2"></div>
        <button @click="setFilter('licenciados')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='licenciados' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Con Licencia</button>
        <button @click="setFilter('sin_licencia')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='sin_licencia' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Sin Licencia</button>
      </div>
      <div class="relative w-full md:w-[280px]">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <input v-model="searchQuery" type="text" placeholder="Buscar usuarios..." class="w-full pl-9 pr-3 py-1.5 text-sm bg-white border border-gray-300 rounded text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" />
      </div>
    </div>

    <!-- Data Table (Borderless) -->
    <div class="flex flex-col">
      <div class="overflow-x-auto hide-scrollbar">
        <table class="w-full text-left min-w-[1000px]">
          <thead>
            <tr class="border-b border-gray-300 bg-gray-50/50">
              <th class="pl-2 py-2 w-10">
                <input type="checkbox" v-model="selectAll" @change="toggleSelectAll" class="w-3.5 h-3.5 border-gray-300 rounded focus:ring-blue-500 cursor-pointer text-blue-600 transition-colors">
              </th>
              <th class="w-1/4 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Nombre para mostrar</th>
              <th class="w-1/6 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Nombre de usuario</th>
              <th class="w-1/6 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Cargo</th>
              <th class="w-1/6 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Departamento</th>
              <th class="w-24 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors text-center">Sincronización</th>
              <th class="w-32 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors text-center">Licencia M365</th>
              <th class="w-24 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors text-center">Estado</th>
            </tr>
          </thead>
          <tbody :class="{'opacity-50 pointer-events-none animate-pulse': isMfaContext && mfaLoading}">
            <!-- Skeleton rows mientras carga el primer batch -->
            <tr v-if="isLoading" v-for="i in 10" :key="'skel-' + i">
              <td class="pl-2 py-2 w-10"><div class="w-3.5 h-3.5 bg-gray-200 rounded animate-pulse"></div></td>
              <td class="px-3 py-2">
                <div class="flex items-center gap-2.5">
                  <div class="w-6 h-6 rounded-full bg-gray-200 animate-pulse shrink-0"></div>
                  <div class="h-3 bg-gray-200 rounded animate-pulse" :style="{ width: (60 + (i * 17) % 80) + 'px' }"></div>
                </div>
              </td>
              <td class="px-3 py-2"><div class="h-3 bg-gray-200 rounded animate-pulse w-24"></div></td>
              <td class="px-3 py-2"><div class="h-3 bg-gray-200 rounded animate-pulse w-20"></div></td>
              <td class="px-3 py-2"><div class="h-3 bg-gray-200 rounded animate-pulse w-20"></div></td>
              <td class="px-3 py-2 text-center"><div class="h-3 bg-gray-200 rounded animate-pulse w-6 mx-auto"></div></td>
              <td class="px-3 py-2 text-center"><div class="h-3 bg-gray-200 rounded animate-pulse w-6 mx-auto"></div></td>
              <td class="px-3 py-2 text-center"><div class="h-4 bg-gray-200 rounded-full animate-pulse w-14 mx-auto"></div></td>
            </tr>
            <tr v-else-if="!isLoading && filteredUsers.length === 0 && !isStreaming">
              <td colspan="9" class="px-2 py-16 text-center">
                <p class="text-[13px] text-slate-500">No se encontraron usuarios que coincidan con la búsqueda o el filtro.</p>
              </td>
            </tr>
            <tr 
              v-else
              v-for="user in paginatedUsers" 
              :key="user.username"
              @click="goToUserProfile(user.username)"
              :class="['border-b border-gray-200 transition-colors duration-150 cursor-pointer group', selectedUsers.has(user.username) ? 'bg-blue-50' : 'hover:bg-gray-50']"
            >
              <td class="pl-2 py-1.5 w-10" @click.stop>
                <input type="checkbox" :checked="selectedUsers.has(user.username)" @change="toggleUser(user.username)" class="w-3.5 h-3.5 border-gray-300 rounded focus:ring-blue-500 cursor-pointer text-blue-600 transition-colors">
              </td>
              <td class="px-3 py-1.5">
                <div class="flex items-center gap-2.5">
                  <div :class="['w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-white text-[9px] font-medium', getAvatarColor(user.fullName)]">
                    {{ getInitials(user.fullName) }}
                  </div>
                  <span class="text-[13px] font-medium text-gray-900 group-hover:text-blue-600 transition-colors">{{ user.fullName }}</span>
                </div>
              </td>
              <td class="px-3 py-1.5">
                <div class="flex items-center gap-1.5 group/upn">
                  <span class="text-[13px] text-gray-600">{{ user.username.split('@')[0] }}</span>
                  <button 
                    @click="copyUpn(user.username.split('@')[0], $event)" 
                    class="text-gray-400 hover:text-gray-700 opacity-0 group-hover/upn:opacity-100 transition-all p-0.5 rounded hover:bg-gray-200 shrink-0 relative"
                  >
                    <svg v-if="copiedUpn === user.username.split('@')[0]" class="w-3.5 h-3.5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
                    <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                    <span v-if="copiedUpn === user.username.split('@')[0]" class="absolute -top-7 left-1/2 -translate-x-1/2 bg-white text-gray-800 text-[10px] font-medium px-2 py-1 rounded shadow border border-gray-200 whitespace-nowrap z-30">
                      Copiado
                    </span>
                  </button>
                </div>
              </td>
              <td class="px-3 py-1.5">
                <div class="text-[13px] text-gray-600 truncate max-w-[150px] xl:max-w-[180px]" :title="user.title">{{ user.title || '—' }}</div>
              </td>
              <td class="px-3 py-1.5">
                <div class="text-[13px] text-gray-600 truncate max-w-[150px] xl:max-w-[180px]" :title="user.department">{{ user.department || '—' }}</div>
              </td>
              <td class="px-3 py-1.5 text-center">
                <span class="text-[11px] text-slate-700">{{ user.ou === 'Nube' ? 'No' : 'Sí' }}</span>
              </td>
              <td class="px-3 py-1.5 text-center">
                <span v-if="licensesSummary[user.username.toLowerCase()] === true" class="text-[11px] text-slate-700">
                  Sí
                </span>
                <span v-else-if="licensesSummary[user.username.toLowerCase()] === false" class="text-[11px] text-slate-400">No</span>
              </td>
              <td class="px-3 py-1.5 text-center">
                <span class="inline-flex items-center gap-1.5 text-[11px] text-slate-700">
                  <span :class="['w-1.5 h-1.5 rounded-full', user.status === 'active' ? 'bg-emerald-500' : user.status === 'locked' ? 'bg-red-500' : 'bg-slate-300']"></span>
                  {{ statusLabels[user.status] || user.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Pagination -->
      <div class="py-4 flex justify-between items-center text-[12px] text-slate-500">
        <span>
          Mostrando {{ paginatedUsers.length }} de {{ filteredUsers.length }}
          <span v-if="isStreaming && streamTotal > 0" class="ml-2 text-blue-500 font-medium">
            · Cargando {{ streamProgress.toLocaleString() }} / {{ streamTotal.toLocaleString() }}
            <span class="inline-block w-2.5 h-2.5 ml-1 border border-blue-400 border-t-blue-600 rounded-full animate-spin align-middle"></span>
          </span>
        </span>
        <div class="flex items-center gap-1" v-if="totalPages > 1">
          <button @click="prevPage" :disabled="currentPage === 1" class="p-1 hover:text-slate-800 disabled:opacity-30 disabled:hover:text-slate-500 transition-colors"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg></button>
          <span class="px-2 font-medium">{{ currentPage }} / {{ totalPages }}</span>
          <button @click="nextPage" :disabled="currentPage === totalPages" class="p-1 hover:text-slate-800 disabled:opacity-30 disabled:hover:text-slate-500 transition-colors"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg></button>
        </div>
      </div>
    </div>

    <!-- â•â•â•â•â•â•â•â•â•â•â• MODALS â•â•â•â•â•â•â•â•â•â•â• -->

    <!-- Modal: Restablecer Contraseña -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showResetPwModal" class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="showResetPwModal = false">
          <div class="bg-white rounded-lg shadow-2xl w-[420px] max-w-[90vw] p-6">
            <div class="flex items-center justify-between mb-5">
              <h3 class="text-[15px] font-bold text-slate-800">Restablecer Contraseña</h3>
              <button @click="showResetPwModal = false" class="text-slate-400 hover:text-slate-600 p-1"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
            </div>
            
            <p class="text-[12px] text-slate-500 mb-4">Se generará una contraseña temporal para <span class="font-bold text-slate-800">{{ actionTargetUser }}</span>. El usuario deberá cambiarla en su próximo inicio de sesión.</p>
            
            <div class="bg-slate-50 border border-slate-200 rounded p-3 mb-4">
              <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">Nueva contraseña</label>
              <div class="flex items-center gap-2">
                <input type="text" v-model="generatedPassword" class="flex-1 text-[13px] font-mono text-slate-800 bg-white border border-slate-300 rounded px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400" />
                <button @click="generatedPassword = generateSecurePassword()" class="text-[11px] text-blue-600 hover:text-blue-800 font-semibold shrink-0 px-2 py-1.5 hover:bg-blue-50 rounded transition-colors">Regenerar</button>
              </div>
            </div>

            <div v-if="actionResult" :class="['text-[12px] p-3 rounded mb-4 border flex items-center gap-2', actionResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
              <svg v-if="actionResult.success" class="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
              {{ actionResult.message }}
            </div>

            <div class="flex justify-end gap-2">
              <button @click="showResetPwModal = false" class="px-4 py-2 text-[12px] font-medium text-slate-600 bg-white border border-slate-300 rounded hover:bg-slate-50 transition-colors">Cerrar</button>
              <button @click="executeResetPassword" :disabled="actionLoading || !generatedPassword" class="px-4 py-2 text-[12px] font-bold text-white bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm">
                <span v-if="actionLoading" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
                {{ actionLoading ? 'Procesando...' : 'Restablecer' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <!-- Modal: MFA Reset -->
    <BaseModal 
      :show="showMfaModal" 
      title="Forzar re-registro MFA" 
      @close="showMfaModal = false"
    >
      <template #body>
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4 flex items-start gap-3">
          <svg class="w-5 h-5 text-gray-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
          <div>
            <p class="font-medium text-gray-900 mb-1">¿Está seguro?</p>
            <p class="text-gray-600 leading-relaxed">Esto eliminarÃ¡ todos los métodos de autenticaciÃ³n (Microsoft Authenticator, SMS, etc.) del usuario <span class="font-bold">{{ actionTargetUser }}</span>. DeberÃ¡ re-registrar su MFA en el prÃ³ximo inicio de sesión.</p>
          </div>
        </div>

        <div v-if="actionResult" :class="['p-4 rounded-lg mt-4 border flex items-center gap-2', actionResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
          {{ actionResult.message }}
        </div>
      </template>

      <template #footer>
        <button @click="showMfaModal = false" class="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
          Cancelar
        </button>
        <button @click="executeResetMfa" :disabled="actionLoading" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm">
          <span v-if="actionLoading" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          Restablecer MFA
        </button>
      </template>
    </BaseModal>

    <!-- Modal: Offboarding -->
    <Teleport to="body">
      <transition name="modal">
        <div v-if="showOffboardModal" class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="showOffboardModal = false">
          <div class="bg-white rounded-lg shadow-2xl w-[440px] max-w-[90vw] p-6">
            <div class="flex items-center justify-between mb-5">
              <h3 class="text-[15px] font-bold text-red-700">Desvincular (Offboarding)</h3>
              <button @click="showOffboardModal = false" class="text-slate-400 hover:text-slate-600 p-1"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg></button>
            </div>
            
            <div class="bg-red-50 border border-red-200 rounded p-3 mb-4 flex items-start gap-2">
              <svg class="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
              <div>
                <p class="text-[12px] font-bold text-red-800 mb-1">Acción irreversible</p>
                <p class="text-[11px] text-red-700 leading-relaxed mb-2">Se ejecutarán las siguientes acciones para <span class="font-bold">{{ actionTargetUser }}</span>:</p>
                <ul class="text-[11px] text-red-700 list-disc pl-4 space-y-0.5 leading-relaxed">
                  <li>Deshabilitar la cuenta en Entra ID</li>
                  <li>Generar una contraseña aleatoria</li>
                  <li>Revocar todas las sesiones activas de M365</li>
                </ul>
              </div>
            </div>

            <div v-if="actionResult" :class="['text-[12px] p-3 rounded mb-4 border flex items-center gap-2', actionResult.success ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200']">
              {{ actionResult.message }}
            </div>

            <div class="flex justify-end gap-2">
              <button @click="showOffboardModal = false" class="px-4 py-2 text-[12px] font-medium text-slate-600 bg-white border border-slate-300 rounded hover:bg-slate-50 transition-colors">Cancelar</button>
              <button @click="executeOffboard" :disabled="actionLoading" class="px-4 py-2 text-[12px] font-bold text-white bg-red-600 hover:bg-red-700 rounded disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm">
                <span v-if="actionLoading" class="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin"></span>
                {{ actionLoading ? 'Ejecutando...' : 'Confirmar Offboarding' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>

    <CreateUserDrawer :is-open="showCreateDrawer" @close="showCreateDrawer = false" @user-created="fetchUsers(); showCreateDrawer = false" />

    <!-- Modal Diagnóstico Express -->
    <DiagnoseModal v-if="showDiagnoseModal" @close="showDiagnoseModal = false" />
  </div>
</template>

<style scoped>
/* Toolbar transition */
.toolbar-enter-active, .toolbar-leave-active {
  transition: all 0.2s ease;
}
.toolbar-enter-from, .toolbar-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Modal transition */
.modal-enter-active, .modal-leave-active {
  transition: all 0.2s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
.modal-enter-from > div, .modal-leave-to > div {
  transform: scale(0.96);
}
</style>
