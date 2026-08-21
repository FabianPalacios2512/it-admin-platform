<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import BaseModal from '../components/common/BaseModal.vue'
import ClonePermissionsModal from '../components/ClonePermissionsModal.vue'

const API_BASE = '/api/v1'

// --- ESTADO DEL NAVEGADOR ---
const shares = ref([])
const loading = ref(true)
const error = ref('')

const currentShare = ref(null)
const currentPath = ref('')
const folderContents = ref([])

const isBrowsing = computed(() => currentShare.value !== null)
const breadcrumbs = computed(() => {
  if (!isBrowsing.value) return []
  const parts = currentPath.value.split(/[/\\]/).filter(p => p)
  const crumbs = [{ name: currentShare.value.name, path: '' }]
  let builtPath = ''
  for (const p of parts) {
    builtPath += (builtPath ? '/' : '') + p
    crumbs.push({ name: p, path: builtPath })
  }
  return crumbs
})

const fetchShares = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares`)
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Error al cargar carpetas')
    }
    shares.value = await res.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// --- BUSCADOR INTELIGENTE UNC ---
const smartSearchQuery = ref('')
const handleSmartSearch = () => {
  if (!smartSearchQuery.value) return
  error.value = ''
  let query = smartSearchQuery.value.trim()
  // Normalizar separadores
  query = query.replace(/\\/g, '/')
  // Quitar el prefijo si tiene
  if (query.startsWith('//')) {
    query = query.substring(2)
  }
  // Dividir por partes
  const parts = query.split('/').filter(p => p)
  if (parts.length < 2) {
    error.value = 'Ruta no válida. Debe incluir al menos el servidor y el recurso compartido (ej: \\\\192.168.1.80\\Share)'
    return
  }
  // parts[0] es el servidor, parts[1] es el share
  const targetShareName = parts[1]
  const targetSubpath = parts.slice(2).join('/')
  
  // Buscar el share (case-insensitive)
  const share = shares.value.find(s => s.name.toLowerCase() === targetShareName.toLowerCase())
  if (!share) {
    error.value = `No se encontró el recurso compartido '${targetShareName}' en la lista de Shares principales. Verifica que el servidor se haya reiniciado para cargar recursos ocultos.`
    return
  }
  
  browsePath(share, targetSubpath)
  smartSearchQuery.value = ''
}

const browsePath = async (share, path = '') => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares/${encodeURIComponent(share.name)}/browse?path=${encodeURIComponent(path)}`)
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Error al navegar la ruta')
    }
    folderContents.value = await res.json()
    currentShare.value = share
    currentPath.value = path
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const navigateUp = () => {
  if (!currentPath.value) {
    currentShare.value = null
    fetchShares()
    return
  }
  const parts = currentPath.value.split(/[/\\]/).filter(p => p)
  parts.pop()
  browsePath(currentShare.value, parts.join('/'))
}

const navigateToCrumb = (crumbPath) => {
  browsePath(currentShare.value, crumbPath)
}

const formatSize = (bytes) => {
  if (bytes === 0) return '-'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (isoString) => {
  if (!isoString) return '-'
  const date = new Date(isoString)
  return date.toLocaleString('es-CO')
}

// --- ESTADO DE PERMISOS (ACL) ---
const showPermissionsDrawer = ref(false)
const permissions = ref([])
const loadingPermissions = ref(false)
const selectedItemForAcl = ref(null) // { share_name, path, name }

const openPermissions = async (item, isShare = false) => {
  selectedItemForAcl.value = {
    share_name: isShare ? item.name : currentShare.value.name,
    path: isShare ? '' : (currentPath.value ? `${currentPath.value}/${item.name}` : item.name),
    name: item.name
  }
  showPermissionsDrawer.value = true
  await fetchPermissions()
}

const fetchPermissions = async () => {
  loadingPermissions.value = true
  permissions.value = []
  try {
    const sName = encodeURIComponent(selectedItemForAcl.value.share_name)
    const pPath = encodeURIComponent(selectedItemForAcl.value.path)
    const res = await fetch(`${API_BASE}/fileserver/shares/${sName}/acl?path=${pPath}`)
    if (!res.ok) throw new Error('Error al cargar permisos NTFS')
    permissions.value = await res.json()
  } catch (err) {
    console.error(err)
    alert(err.message)
  } finally {
    loadingPermissions.value = false
  }
}

// --- ESTADO DE AÑADIR PERMISOS (Buscador AD) ---
const showAddPermission = ref(false)
const adSearchQuery = ref('')
const adSearchResults = ref([])
const searchingAD = ref(false)
const selectedADAccount = ref(null)
const selectedPermissionLevel = ref('ReadAndExecute')
const addingPerm = ref(false)

// --- ESTADO DE CONFIRMACIÓN DE ELIMINACIÓN ---
const showConfirmRemove = ref(false)
const pendingRemovePerm = ref(null)
const removingPerm = ref(false)

const searchAD = async () => {
  if (adSearchQuery.value.length < 2) return
  searchingAD.value = true
  adSearchResults.value = []
  try {
    const res = await fetch(`${API_BASE}/fileserver/search-ad?q=${encodeURIComponent(adSearchQuery.value)}&limit=15`)
    if (res.ok) {
      adSearchResults.value = await res.json()
    }
  } catch (err) {
    console.error(err)
  } finally {
    searchingAD.value = false
  }
}

const confirmAddPermission = async () => {
  if (!selectedADAccount.value || addingPerm.value) return
  addingPerm.value = true
  const sName = encodeURIComponent(selectedItemForAcl.value.share_name)
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares/${sName}/acl/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account: selectedADAccount.value.ntaccount,
        permission: selectedPermissionLevel.value,
        subpath: selectedItemForAcl.value.path
      })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail)
    }
    showAddPermission.value = false
    selectedADAccount.value = null
    adSearchQuery.value = ''
    await fetchPermissions()
  } catch (err) {
    alert(`Error: ${err.message}`)
  } finally {
    addingPerm.value = false
  }
}

const removePermission = (perm) => {
  pendingRemovePerm.value = perm
  showConfirmRemove.value = true
}

const confirmRemovePermission = async () => {
  if (!pendingRemovePerm.value) return
  removingPerm.value = true
  const perm = pendingRemovePerm.value
  const sName = encodeURIComponent(selectedItemForAcl.value.share_name)
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares/${sName}/acl/remove`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account: perm.raw_account || perm.account,
        subpath: selectedItemForAcl.value.path
      })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail)
    }
    showConfirmRemove.value = false
    pendingRemovePerm.value = null
    await fetchPermissions()
  } catch (err) {
    showConfirmRemove.value = false
    pendingRemovePerm.value = null
    alert(`Error: ${err.message}`)
  } finally {
    removingPerm.value = false
  }
}

const cancelRemove = () => {
  showConfirmRemove.value = false
  pendingRemovePerm.value = null
}

// --- ESTADO CREAR CARPETA ---
const showCreateFolderModal = ref(false)
const newFolderName = ref('')
const newFolderInherit = ref(true)
const creatingFolder = ref(false)

const openCreateFolder = () => {
  newFolderName.value = ''
  newFolderInherit.value = true
  showCreateFolderModal.value = true
}

const confirmCreateFolder = async () => {
  if (!newFolderName.value || creatingFolder.value) return
  creatingFolder.value = true
  const sName = encodeURIComponent(currentShare.value.name)
  const cPath = currentPath.value
  
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares/${sName}/folders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        folder_name: newFolderName.value,
        base_path: cPath,
        inherit_permissions: newFolderInherit.value
      })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail)
    }
    showCreateFolderModal.value = false
    browsePath(currentShare.value, currentPath.value)
  } catch (err) {
    alert(`Error: ${err.message}`)
  } finally {
    creatingFolder.value = false
  }
}

// --- ACCIONES KEBAB MENU ---
const activeKebab = ref(null)
const toggleKebab = (id) => {
  if (activeKebab.value === id) {
    activeKebab.value = null
  } else {
    activeKebab.value = id
  }
}

const closeKebab = (e) => {
  if (!e.target.closest('.kebab-container')) {
    activeKebab.value = null
  }
}

const generateCloudLink = async (item, isShare) => {
  activeKebab.value = null
  const sName = encodeURIComponent(isShare ? item.name : currentShare.value.name)
  const subPath = isShare ? '' : ((currentPath.value ? currentPath.value + '/' : '') + item.name)
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares/${sName}/share-cloud`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: subPath })
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail)
    }
    const data = await res.json()
    alert(`Enlace generado: ${data.link}`)
  } catch(err) {
    alert(`Error: ${err.message}`)
  }
}

// --- ESTADO AUDITORÍA DE ACCESOS ---
const showAuditDrawer = ref(false)
const auditData = ref([])
const auditingPath = ref('')
const isAuditing = ref(false)

const formatAccess = (rawAccess) => {
  if (!rawAccess) return 'Especial'
  if (rawAccess.includes('FullControl')) return 'Control Total'
  if (rawAccess.includes('Modify')) return 'Modificar'
  if (rawAccess.includes('ReadAndExecute')) return 'Lectura y Ejecución'
  if (rawAccess.includes('Write')) return 'Escritura'
  if (rawAccess.includes('Read')) return 'Lectura'
  return 'Personalizado'
}

const formatAccount = (account) => {
  if (!account) return 'Desconocido'
  if (account.startsWith('S-1-5-')) return `SID Huérfano (${account.substring(0, 15)}...)`
  return account
}

const auditAccess = async (item, isShare) => {
  activeKebab.value = null
  const sName = encodeURIComponent(isShare ? item.name : currentShare.value.name)
  const subPath = isShare ? '' : ((currentPath.value ? currentPath.value + '/' : '') + item.name)
  
  auditingPath.value = `\\\\Server\\${isShare ? item.name : currentShare.value.name}\\${subPath}`
  auditData.value = []
  isAuditing.value = true
  showAuditDrawer.value = true
  
  try {
    const res = await fetch(`${API_BASE}/fileserver/shares/${sName}/effective-access?path=${encodeURIComponent(subPath)}`)
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail)
    }
    const data = await res.json()
    // data.data has the array of ACLs
    auditData.value = data.data || []
  } catch(err) {
    alert(`Error: ${err.message}`)
    showAuditDrawer.value = false
  } finally {
    isAuditing.value = false
  }
}

// --- SELECCIÓN MULTIPLE ---
const selectedItems = ref([])
const toggleSelection = (item) => {
  const isShare = !item.modified_at
  const id = item.name
  const index = selectedItems.value.findIndex(i => {
    const isIShare = !i.modified_at
    return (isShare && isIShare && i.name === id) || (!isShare && !isIShare && i.name === id)
  })
  if (index >= 0) {
    selectedItems.value.splice(index, 1)
  } else {
    selectedItems.value.push(item)
  }
}

const copyToClipboard = async (text) => {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    // Se podría agregar una notificación visual breve aquí si existe un componente de Toast
  } catch (err) {
    console.error('Error al copiar al portapapeles:', err)
  }
}

const toggleAll = (items) => {
  if (selectedItems.value.length === items.length) {
    selectedItems.value = []
  } else {
    selectedItems.value = [...items]
  }
}
const isSelected = (item) => {
  const isShare = !item.modified_at
  const id = item.name
  return selectedItems.value.some(i => {
    const isIShare = !i.modified_at
    return (isShare && isIShare && i.name === id) || (!isShare && !isIShare && i.name === id)
  })
}
const clearSelection = () => {
  selectedItems.value = []
}

// Watchers para limpiar selección al navegar
watch([currentShare, currentPath], () => {
  clearSelection()
})

const auditAccessBulk = async () => {
  if (selectedItems.value.length === 0) return
  const item = selectedItems.value[0]
  const isShare = !item.modified_at
  await auditAccess(item, isShare)
}

const generateCloudLinkBulk = () => {
  if (selectedItems.value.length === 0) return
  const item = selectedItems.value[0]
  const isShare = !item.modified_at
  // Si tuviéramos un generateCloudLink async, lo llamaríamos aquí
  alert(`Generar enlace M365 para: ${item.name}`)
}

const openPermissionsBulk = () => {
  if (selectedItems.value.length === 0) return
  const item = selectedItems.value[0]
  const isShare = !item.modified_at
  openPermissions(item, isShare)
}

const showCloneModal = ref(false)

onMounted(() => {
  document.addEventListener('click', closeKebab)
  fetchShares()
})

onUnmounted(() => {
  document.removeEventListener('click', closeKebab)
})
</script>

<template>
  <div class="h-full flex flex-col font-sans max-w-7xl mx-auto w-full px-4 py-6">
    <!-- Header / Title -->
    <div class="mb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-gray-400 hover:text-gray-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-gray-300">/</span>
        <span class="text-[11px] text-gray-600 font-medium">Archivos</span>
      </div>
      <h2 class="text-2xl font-semibold text-gray-900 tracking-tight flex items-center gap-2">
        <svg class="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
        </svg>
        Administrador de Archivos
      </h2>
      <p class="text-sm text-gray-500 mt-1">Navega y gestiona permisos de carpetas de red de manera segura.</p>
    </div>

    <!-- Command Bar (Global) -->
    <div class="flex flex-col md:flex-row md:items-center justify-between mb-2 border-b border-gray-200 pb-3 h-12">
      <div class="flex items-center gap-4 flex-wrap w-full">
        <button @click="openCreateFolder" class="text-[13px] font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5">
          <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
          Nueva carpeta
        </button>
        <button class="text-[13px] font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5">
          <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
          Mapear a Usuario
        </button>
        <button @click="selectedItems.length > 0 ? showCloneModal = true : null" 
                :class="selectedItems.length === 0 ? 'opacity-50 cursor-not-allowed' : 'hover:text-indigo-800 hover:bg-indigo-100'"
                class="text-[13px] font-medium text-indigo-700 bg-indigo-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5 border border-indigo-100">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" /></svg>
          Clonar Permisos (Espejo)
        </button>
        <div class="relative w-64">
          <input v-model="smartSearchQuery" @keyup.enter="handleSmartSearch" type="text" placeholder="Ruta UNC (ej. \\Server\Share)..." class="w-full pl-7 pr-8 py-1.5 bg-gray-50 border border-gray-200 rounded-md text-[12px] text-gray-900 outline-none focus:bg-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all">
          <svg class="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          <button v-if="smartSearchQuery" @click="handleSmartSearch" class="absolute right-1 top-1 text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase transition-colors">Ir</button>
        </div>
        
        <div class="w-px h-5 bg-gray-200"></div>

        <template v-if="selectedItems.length === 0">
          <button @click="isBrowsing ? browsePath(currentShare, currentPath) : fetchShares()" class="text-[13px] font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5">
            <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            Actualizar
          </button>
        </template>
        <template v-else>
          <span class="text-[13px] text-gray-500 font-medium flex items-center gap-2 bg-blue-50 px-2 py-1 rounded-md border border-blue-100">
            <span class="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] font-bold">{{ selectedItems.length }}</span>
            seleccionado(s)
            <button @click="clearSelection" class="text-blue-600 hover:underline ml-1">Desmarcar</button>
          </span>
          <button @click="openPermissionsBulk" class="text-[13px] font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5">
            <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/></svg>
            Permisos
          </button>
          <button @click="auditAccessBulk" class="text-[13px] font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5">
            <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg>
            Auditar
          </button>
          <button @click="generateCloudLinkBulk" class="text-[13px] font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 px-2 py-1.5 rounded transition-colors flex items-center gap-1.5">
            <svg class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"/></svg>
            Enlace
          </button>
        </template>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-sm my-4 flex gap-3">
      <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      {{ error }}
    </div>

    <!-- Barra de Navegación (Breadcrumbs) -->
    <div v-if="isBrowsing && !error" class="bg-gray-50 border-b border-gray-100 py-3 px-4 flex items-center gap-2 text-sm rounded-lg my-4">
      <button @click="navigateUp" class="p-1 hover:bg-gray-200 rounded-md text-gray-500 transition-colors" title="Subir un nivel">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" /></svg>
      </button>
      <div class="h-5 w-px bg-gray-300 mx-1"></div>
      
      <button @click="currentShare = null; fetchShares()" class="text-indigo-600 hover:underline font-medium flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
      </button>
      
      <span v-for="(crumb, idx) in breadcrumbs" :key="idx" class="flex items-center gap-2">
        <span class="text-gray-400">/</span>
        <button @click="navigateToCrumb(crumb.path)" class="text-gray-700 hover:text-indigo-600 hover:underline font-medium">
          {{ crumb.name }}
        </button>
      </span>
    </div>

    <!-- Content Area -->
    <div class="flex-1 flex flex-col overflow-hidden mb-6 mt-2">
      <div v-if="loading" class="flex-1 flex items-center justify-center">
        <span class="w-8 h-8 border-2 border-gray-200 border-t-indigo-600 rounded-full animate-spin"></span>
      </div>
      
      <div v-else-if="!isBrowsing && shares.length === 0 && !error" class="flex-1 flex flex-col items-center justify-center text-center p-8">
        <svg class="w-16 h-16 text-gray-200 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1"><path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
        <p class="text-[15px] font-semibold text-gray-700">No hay carpetas compartidas</p>
      </div>

      <!-- VISTA: LISTA DE SHARES -->
      <div v-else-if="!isBrowsing" class="flex-1 overflow-auto">
        <table class="w-full text-left text-sm whitespace-nowrap">
          <thead class="text-gray-500 font-bold uppercase tracking-wider text-xs border-b-2 border-gray-200">
            <tr>
              <th class="px-3 py-3 w-10 text-center"></th>
              <th class="px-2 py-3 w-1/3">Recurso Compartido</th>
              <th class="px-4 py-3 w-1/3">Ruta UNC</th>
              <th class="px-4 py-3 w-1/3">Ruta Local</th>
            </tr>
          </thead>
          <tbody class="text-gray-700">
            <tr v-for="share in shares" :key="share.name" class="hover:bg-gray-50/80 transition-colors cursor-pointer border-b border-gray-100 group" @dblclick="browsePath(share)">
              <td class="px-3 py-4 text-center" @click.stop>
                <input type="checkbox" class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 cursor-pointer" :checked="isSelected(share)" @change="toggleSelection(share)"/>
              </td>
              <td class="px-2 py-4" @click="toggleSelection(share)">
                <div class="flex items-center gap-3">
                  <svg class="w-5 h-5 text-indigo-500" fill="currentColor" viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                  <span class="font-medium text-gray-900">{{ share.name }}</span>
                </div>
              </td>
              <td class="px-4 py-4 text-gray-700 font-mono text-xs" @click="toggleSelection(share)">
                <div class="flex items-center gap-2">
                  <span>{{ share.unc_path || '\\\\' + share.name }}</span>
                  <button @click.stop="copyToClipboard(share.unc_path || '\\\\' + share.name)" title="Copiar Ruta UNC" class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-blue-600 transition-opacity">
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                  </button>
                </div>
              </td>
              <td class="px-4 py-4 font-mono text-xs text-gray-500" @click="toggleSelection(share)">{{ share.path }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- VISTA: NAVEGADOR DE CARPETA -->
      <div v-else class="flex-1 overflow-auto">
        <table class="w-full text-left text-sm">
          <thead class="text-gray-500 font-bold uppercase tracking-wider text-xs border-b-2 border-gray-200">
            <tr>
              <th class="px-5 py-3 w-12 text-center"></th>
              <th class="px-2 py-3 w-1/2">Nombre</th>
              <th class="px-5 py-3 w-1/4">Fecha Modificación</th>
              <th class="px-5 py-3 w-1/4">Tamaño</th>
            </tr>
          </thead>
          <tbody class="text-gray-700">
            <tr v-if="folderContents.length === 0" class="hover:bg-gray-50 border-b border-gray-100">
              <td colspan="5" class="px-5 py-6 text-center text-gray-500 text-sm font-medium">Esta carpeta está vacía.</td>
            </tr>
            <tr v-for="item in folderContents" :key="item.name" class="hover:bg-gray-50/80 transition-colors cursor-pointer border-b border-gray-100">
              <td class="px-5 py-3 text-center" @click.stop>
                <input type="checkbox" class="w-4 h-4 text-indigo-600 rounded border-gray-300 focus:ring-indigo-500 cursor-pointer" :checked="isSelected(item)" @change="toggleSelection(item)"/>
              </td>
              <td class="px-2 py-3" @click="toggleSelection(item)">
                <div class="flex items-center gap-3 cursor-pointer" @dblclick.stop="item.is_dir ? browsePath(currentShare, (currentPath ? currentPath + '/' : '') + item.name) : null">
                  <svg v-if="item.is_dir" class="w-5 h-5 text-indigo-400" fill="currentColor" viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                  <svg v-else class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" /></svg>
                  <span :class="['font-medium', item.is_dir ? 'text-gray-900' : 'text-gray-600']">{{ item.name }}</span>
                </div>
              </td>
              <td class="px-5 py-3 text-gray-500 text-xs" @click="toggleSelection(item)">{{ formatDate(item.modified_at) }}</td>
              <td class="px-5 py-3 text-gray-500 text-xs" @click="toggleSelection(item)">{{ formatSize(item.size) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal: Crear Carpeta -->
    <BaseModal 
      :show="showCreateFolderModal" 
      title="Crear Nueva Carpeta" 
      @close="showCreateFolderModal = false"
    >
      <template #body>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-900 mb-1">Nombre de la carpeta</label>
            <input type="text" v-model="newFolderName" class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500" placeholder="Ej. Finanzas_2023"/>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-900 mb-1">Ruta Destino</label>
            <div class="bg-gray-50 border border-gray-200 rounded-lg p-2 text-xs text-gray-600 font-mono break-all">
              \\Server\{{ currentShare?.name }}\{{ currentPath }}
            </div>
          </div>
          <div class="flex items-center gap-2 mt-4">
            <input type="checkbox" id="inheritChk" v-model="newFolderInherit" class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500" />
            <label for="inheritChk" class="text-sm text-gray-700">Heredar permisos de la carpeta padre</label>
          </div>
          <p v-if="!newFolderInherit" class="text-xs text-orange-600 bg-orange-50 border border-orange-100 p-2 rounded-md">
            Al no heredar, la carpeta se creará sin permisos explícitos. Deberás asignar permisos manualmente para que sea accesible.
          </p>
        </div>
      </template>
      <template #footer>
        <button @click="showCreateFolderModal = false" class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors">
          Cancelar
        </button>
        <button @click="confirmCreateFolder" :disabled="creatingFolder || !newFolderName" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 flex items-center gap-2 transition-colors">
          <svg v-if="creatingFolder" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          {{ creatingFolder ? 'Creando...' : 'Crear Carpeta' }}
        </button>
      </template>
    </BaseModal>

    <!-- Drawer de Seguridad NTFS (Refactored) -->
    <Teleport to="body">
      <div v-if="showPermissionsDrawer" class="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
        <!-- Background backdrop -->
        <div class="absolute inset-0 bg-gray-900/20 backdrop-blur-[2px] transition-opacity" @click="showPermissionsDrawer = false"></div>

        <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
          <!-- Drawer panel -->
          <div class="pointer-events-auto relative w-[50vw] max-w-4xl flex flex-col bg-white shadow-2xl">
            
            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-5 bg-gray-50 border-b border-gray-100 shrink-0">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 24 24"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                </div>
                <div>
                  <h2 class="text-lg font-bold text-gray-900">Permisos de Seguridad (NTFS)</h2>
                  <p class="text-xs text-gray-500 font-mono mt-0.5 break-all">\\Server\{{ selectedItemForAcl?.share_name }}\{{ selectedItemForAcl?.path }}</p>
                </div>
              </div>
              <button @click="showPermissionsDrawer = false" class="text-gray-400 hover:text-gray-600 p-2 rounded-md hover:bg-gray-100 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 overflow-y-auto bg-white p-6 flex flex-col">
              
              <div v-if="showAddPermission" class="mb-4 pb-4 border-b border-gray-100">
                <h4 class="text-[13px] font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <svg class="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" /></svg>
                  Agregar Permiso Explícito
                </h4>
                
                <label class="block text-xs font-medium text-gray-700 mb-1">Buscar Usuario / Grupo AD:</label>
                <div class="flex gap-2 mb-3">
                  <input v-model="adSearchQuery" @keydown.enter="searchAD" type="text" class="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="Escriba nombre o sAMAccountName..."/>
                  <button @click="searchAD" :disabled="searchingAD" class="border border-gray-300 bg-white hover:bg-gray-50 rounded-md px-4 py-2 text-sm text-gray-700 font-medium transition-colors shadow-sm flex items-center gap-2">
                    <svg v-if="searchingAD" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    {{ searchingAD ? 'Buscando' : 'Buscar' }}
                  </button>
                </div>
                
                <div v-if="adSearchResults.length > 0" class="border border-gray-200 bg-white rounded-md max-h-[160px] overflow-y-auto mb-4 shadow-inner">
                  <div v-for="res in adSearchResults" :key="res.ntaccount"
                    @click="selectedADAccount = res"
                    :class="['flex items-center gap-3 px-4 py-3 cursor-pointer text-sm border-b border-gray-100 last:border-0 transition-colors', selectedADAccount?.ntaccount === res.ntaccount ? 'bg-indigo-50 border-l-4 border-l-indigo-600' : 'hover:bg-gray-50']"
                  >
                    <span class="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 shrink-0">
                      <i v-if="res.type === 'Grupo'" class="fas fa-users text-sm"></i>
                      <i v-else class="fas fa-user text-sm"></i>
                    </span>
                    <div class="flex flex-col flex-1 min-w-0">
                      <span class="font-medium text-gray-900 truncate">{{ res.name }}</span>
                      <span class="text-xs text-gray-500 truncate">{{ res.ntaccount }}</span>
                    </div>
                  </div>
                </div>

                <label class="block text-xs font-medium text-gray-700 mb-1">Nivel de Acceso a Otorgar:</label>
                <select v-model="selectedPermissionLevel" class="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm mb-4 focus:outline-none focus:ring-1 focus:ring-gray-400">
                  <option value="ReadAndExecute">Lectura y Ejecución (Recomendado para visualización)</option>
                  <option value="Modify">Modificar (Lectura/Escritura/Borrado)</option>
                  <option value="FullControl">Control Total (Administración absoluta)</option>
                </select>

                <div class="flex justify-end gap-3 pt-2">
                  <button @click="showAddPermission = false" :disabled="addingPerm" class="px-3 py-1.5 text-gray-700 bg-white hover:bg-gray-50 text-[13px] font-medium transition-colors">Cancelar</button>
                  <button @click="confirmAddPermission" :disabled="!selectedADAccount || addingPerm" class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded text-[13px] disabled:opacity-50 flex items-center gap-2 transition-colors shadow-sm">
                    <svg v-if="addingPerm" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    {{ addingPerm ? 'Aplicando en servidor...' : 'Aplicar Permiso' }}
                  </button>
                </div>
              </div>

              <div class="flex items-center justify-between mb-4">
                <h3 class="text-[13px] font-bold text-gray-900">Listado de Accesos (ACL)</h3>
                <button @click="showAddPermission = true" :disabled="showAddPermission" class="text-xs text-gray-900 hover:bg-gray-100 font-medium px-3 py-1.5 rounded transition-colors flex items-center gap-1 disabled:opacity-50 border border-gray-200 shadow-sm">
                  <svg class="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                  Agregar Permiso
                </button>
              </div>
              
              <div class="flex-1 flex flex-col min-h-[300px] overflow-hidden">
                <div v-if="loadingPermissions" class="flex-1 flex flex-col justify-center items-center py-12">
                  <span class="w-8 h-8 border-2 border-gray-200 border-t-gray-600 rounded-full animate-spin mb-3"></span>
                  <p class="text-sm text-gray-500 font-medium">Leyendo ACLs del servidor...</p>
                </div>
                <div v-else class="flex-1 overflow-y-auto">
                  <table class="w-full text-left text-sm">
                    <thead class="border-b border-gray-200 text-gray-500 text-[11px] font-semibold uppercase tracking-wider sticky top-0 z-10 bg-white">
                      <tr>
                        <th class="px-4 py-2 font-semibold">Cuenta o Grupo</th>
                        <th class="px-4 py-2 font-semibold">Nivel de Acceso</th>
                        <th class="px-4 py-2 font-semibold text-center">Acciones</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                      <tr v-for="(perm, idx) in permissions" :key="idx" class="hover:bg-gray-50 transition-colors group">
                        <td class="px-4 py-1.5 font-medium text-gray-900">
                          <div class="flex items-center gap-2">
                            <span class="w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center shrink-0">
                              <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
                            </span>
                            <span class="truncate max-w-[300px] text-[13px]" :title="perm.account">{{ formatAccount(perm.account) }}</span>
                          </div>
                        </td>
                        <td class="px-4 py-1.5">
                          <div class="flex flex-col">
                            <span class="text-gray-900 font-medium text-[13px]" :title="perm.access">
                              {{ formatAccess(perm.access) }}
                            </span>
                            <span class="text-xs text-gray-500">
                              {{ perm.inherited ? 'Heredado' : 'Explícito' }}
                            </span>
                          </div>
                        </td>
                        <td class="px-4 py-1.5 text-center">
                          <button v-if="!perm.inherited" @click="removePermission(perm)" title="Quitar este permiso" class="text-gray-400 hover:text-red-500 p-1.5 rounded transition-colors opacity-0 group-hover:opacity-100">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                          </button>
                        </td>
                      </tr>
                      <tr v-if="permissions.length === 0 && !loadingPermissions">
                        <td colspan="3" class="px-4 py-6 text-center text-gray-500 text-[13px] font-medium border-b-0">No hay permisos asignados explícitamente en esta ruta.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end shrink-0">
              <button @click="showPermissionsDrawer = false" class="px-6 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors shadow-sm">
                Cerrar Panel
              </button>
            </div>
            
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modal de Confirmación de Eliminación -->
    <BaseModal 
      :show="showConfirmRemove" 
      title="Eliminar Permiso Explicito" 
      @close="cancelRemove"
    >
      <template #body>
        <div class="flex items-start gap-4 p-2">
          <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
            <svg class="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-medium text-gray-900 mb-1">¿Estás seguro de eliminar este permiso?</p>
            <p class="text-sm text-gray-600">Se revocarán los permisos explícitos para el usuario/grupo:</p>
            <p class="text-sm font-semibold text-gray-900 mt-2 bg-gray-50 p-2 rounded-md border border-gray-200">{{ pendingRemovePerm?.account }}</p>
          </div>
        </div>
      </template>
      <template #footer>
        <button @click="cancelRemove" class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors">
          Cancelar
        </button>
        <button @click="confirmRemovePermission" :disabled="removingPerm" class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg disabled:opacity-50 flex items-center gap-2 transition-colors">
          {{ removingPerm ? 'Eliminando...' : 'Sí, Eliminar' }}
        </button>
      </template>
    </BaseModal>

    <!-- Drawer de Auditoría de Accesos -->
    <Teleport to="body">
      <div v-if="showAuditDrawer" class="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
        <!-- Background backdrop -->
        <div class="absolute inset-0 bg-gray-900/20 backdrop-blur-[2px] transition-opacity" @click="showAuditDrawer = false"></div>

        <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
          <!-- Drawer panel -->
          <div class="pointer-events-auto relative w-[50vw] max-w-4xl flex flex-col bg-white shadow-2xl">
            
            <!-- Header -->
            <div class="flex items-center justify-between px-6 py-5 bg-gray-50 border-b border-gray-100 shrink-0">
              <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 2.18l7.25 3.22c-.04 4.54-2.88 8.87-7.25 10.37-4.37-1.5-7.21-5.83-7.25-10.37L12 3.18zM12 7a5 5 0 100 10 5 5 0 000-10zm0 1.5a3.5 3.5 0 110 7 3.5 3.5 0 010-7z"/></svg>
                </div>
                <div>
                  <h2 class="text-lg font-bold text-gray-900">Auditoría de Accesos Efectivos</h2>
                  <p class="text-xs text-gray-500 font-mono mt-0.5 break-all">{{ auditingPath }}</p>
                </div>
              </div>
              <button @click="showAuditDrawer = false" class="text-gray-400 hover:text-gray-600 p-2 rounded-md hover:bg-gray-100 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 overflow-y-auto bg-white p-6">
              
              <div v-if="isAuditing" class="flex flex-col items-center justify-center py-16">
                <span class="w-10 h-10 border-2 border-gray-200 border-t-indigo-600 rounded-full animate-spin mb-4"></span>
                <p class="text-sm font-medium text-gray-600">Consultando Active Directory y el servidor de archivos...</p>
                <p class="text-xs text-gray-400 mt-1">Calculando accesos heredados y explícitos</p>
              </div>

              <div v-else-if="auditData.length === 0" class="text-center py-16">
                <svg class="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                <p class="text-base font-semibold text-gray-700">No hay registros de acceso.</p>
              </div>

              <div v-else class="flex-1 flex flex-col overflow-hidden">
                <table class="w-full text-left text-sm">
                  <thead class="border-b border-gray-200 text-gray-500 text-[11px] font-semibold uppercase tracking-wider sticky top-0 z-10 bg-white">
                    <tr>
                      <th class="px-4 py-2 font-semibold">Cuenta (Usuario / Grupo)</th>
                      <th class="px-4 py-2 font-semibold">Nivel de Acceso</th>
                      <th class="px-4 py-2 font-semibold">Origen del Permiso</th>
                      <th class="px-4 py-2 font-semibold text-center">Estado</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100 text-gray-700">
                    <tr v-for="(record, idx) in auditData" :key="idx" class="hover:bg-gray-50 transition-colors">
                      <td class="px-4 py-1.5 font-medium text-gray-900">
                        <div class="flex items-center gap-2">
                          <span v-if="record.Account.startsWith('S-1-5-')" class="w-6 h-6 text-amber-600 flex items-center justify-center shrink-0">
                            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                          </span>
                          <span v-else class="w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center shrink-0">
                            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                          </span>
                          <span class="truncate max-w-[250px] text-[13px]" :title="record.Account">{{ formatAccount(record.Account) }}</span>
                        </div>
                      </td>
                      <td class="px-4 py-1.5">
                        <span class="text-gray-900 font-medium text-[13px] whitespace-nowrap" :title="record.Access">
                          {{ formatAccess(record.Access) }}
                        </span>
                      </td>
                      <td class="px-4 py-1.5 text-xs text-gray-500">
                        <span v-if="record.Inherited" class="flex items-center gap-1.5 text-gray-500">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" /></svg>
                          Heredado
                        </span>
                        <span v-else class="flex items-center gap-1.5 text-gray-500">
                          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
                          Explícito
                        </span>
                      </td>
                      <td class="px-4 py-1.5 text-center">
                        <span v-if="record.Type === 'Allow'" class="text-gray-400">
                          <svg class="w-4 h-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
                        </span>
                        <span v-else class="text-gray-400">
                          <svg class="w-4 h-4 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end shrink-0">
              <button @click="showAuditDrawer = false" class="px-6 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-sm font-medium transition-colors shadow-sm">
                Cerrar Auditoría
              </button>
            </div>
            
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Modals -->
    <ClonePermissionsModal v-if="showCloneModal" @close="showCloneModal = false" />
  </div>
</template>
