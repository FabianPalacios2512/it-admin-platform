<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const props = defineProps({
  isOpen: Boolean,
})

const emit = defineEmits(['close', 'user-created'])

// Estado de pasos (1: OU, 2: Identidad, 3: Seguridad, 4: Resumen)
const currentStep = ref(1)
const isSubmitting = ref(false)
const submitStatusText = ref('')

// Datos del formulario
const formData = ref({
  accountType: 'onpremise', // 'onpremise' o 'cloud'
  ou: '',
  ouName: '',
  firstName: '',
  lastName: '',
  initials: '',
  fullName: '',
  upnPrefix: '',
  samAccountName: '',
  password: '',
  mustChangePassword: true,
  cannotChangePassword: false,
  passwordNeverExpires: false,
  accountDisabled: false,
  // Atributos opcionales
  sharedFolders: [],
  proxyAddresses: [],
  userParameters: ''
})

const activeSubView = ref(null)

const newProxyType = ref('SMTP')
const newProxyValue = ref('')
function addProxyAddress() {
  if (newProxyValue.value.trim()) {
    formData.value.proxyAddresses.push(`${newProxyType.value}:${newProxyValue.value.trim()}`)
    newProxyValue.value = ''
  }
}

const newFolderPath = ref('')
const newFolderPerm = ref('Lectura')
const availableShares = ref([])
const folderSuggestions = ref([])
let suggestTimeout = null

watch(newFolderPath, (newVal) => {
  clearTimeout(suggestTimeout)
  suggestTimeout = setTimeout(() => {
    fetchSuggestions(newVal)
  }, 200)
})

async function fetchSuggestions(query) {
  if (!query) {
    folderSuggestions.value = []
    return
  }
  
  let search = query.replace(/^\\\\/, '').replace(/^\\/, '')
  
  if (!search.includes('\\')) {
    folderSuggestions.value = availableShares.value.map(s => `\\\\${s.name}\\`)
    return
  }
  
  const parts = search.split('\\')
  const shareName = parts[0]
  parts.pop() // remove what they are currently typing to fetch the parent
  const parentPath = parts.slice(1).join('\\')
  
  try {
    const token = localStorage.getItem('access_token')
    const url = `${API_BASE}/fileserver/shares/${encodeURIComponent(shareName)}/browse?path=${encodeURIComponent(parentPath)}`
    
    const res = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      const items = await res.json()
      const dirs = items.filter(i => i.is_dir)
      const newParent = parentPath ? `${parentPath}\\` : ''
      folderSuggestions.value = dirs.map(d => `\\\\${shareName}\\${newParent}${d.name}\\`)
    }
  } catch (err) {
    // silent fail for suggestions
  }
}

function addSharedFolder() {
  if (newFolderPath.value.trim()) {
    formData.value.sharedFolders.push({
      path: newFolderPath.value.trim(),
      permission: newFolderPerm.value
    })
    newFolderPath.value = ''
  }
}

async function openSubView(view) {
  activeSubView.value = view
  if (view === 'folders' && availableShares.value.length === 0) {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/fileserver/shares`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        availableShares.value = await res.json()
      }
    } catch (err) {
      console.error('Error fetching shares for autocomplete:', err)
    }
  }
}

async function handleFolderTabComplete() {
  if (!newFolderPath.value) return
  
  let search = newFolderPath.value.replace(/^\\\\/, '').replace(/^\\/, '')
  
  // If no backslash, they are typing the share name
  if (!search.includes('\\')) {
    const match = availableShares.value.find(s => s.name.toLowerCase().startsWith(search.toLowerCase()))
    if (match) {
      newFolderPath.value = `\\\\${match.name}\\`
    }
    return
  }

  // Typing a subfolder: ShareName\ParentPath\PartialName
  const parts = search.split('\\')
  const shareName = parts[0]
  const partialName = parts.pop().toLowerCase()
  
  // No autocomplete random folders if they haven't typed an initial
  if (!partialName) {
    return
  }

  const parentPath = parts.slice(1).join('\\')

  try {
    const token = localStorage.getItem('access_token')
    const url = `${API_BASE}/fileserver/shares/${encodeURIComponent(shareName)}/browse?path=${encodeURIComponent(parentPath)}`
    
    const res = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    if (res.ok) {
      const items = await res.json()
      const dirs = items.filter(i => i.is_dir && i.name.toLowerCase().startsWith(partialName))
      
      if (dirs.length > 0) {
        const matchName = dirs[0].name
        const newParent = parentPath ? `${parentPath}\\` : ''
        newFolderPath.value = `\\\\${shareName}\\${newParent}${matchName}\\`
      }
    }
  } catch (err) {
    console.error('Error auto-completing subfolder:', err)
  }
}

function closeSubView() {
  activeSubView.value = null
}

const upnSuffix = ref('@local.code')
const preWin2000 = 'CODE\\'

// Estado de las OUs
const ous = ref([])
const loadingOus = ref(false)
const ouTree = ref([])
const expandedNodes = ref(new Set()) // Para controlar nodos expandidos

const API_BASE = '/api/v1'

// Obtener y procesar OUs
async function fetchOUs() {
  loadingOus.value = true
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/accounts/ous`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      ous.value = data
      buildOUTree(data)
    }
  } catch (err) {
    console.error('Error cargando OUs:', err)
  } finally {
    loadingOus.value = false
  }
}

function buildOUTree(flatList) {
  const rootNode = {
    name: 'code.local',
    dn: 'DC=code,DC=local',
    type: 'Domain',
    children: {},
    expanded: true
  }
  
  expandedNodes.value.add(rootNode.dn)

  flatList.forEach(item => {
    const parts = item.dn.split(',')
    const structuralParts = parts.filter(p => p.startsWith('OU=') || p.startsWith('CN='))
    structuralParts.reverse()
    
    let currentNode = rootNode
    let currentDnBuilder = []
    
    const domainDCs = parts.filter(p => p.startsWith('DC=')).join(',')
    
    structuralParts.forEach((part, index) => {
      currentDnBuilder.unshift(part)
      const currentDn = currentDnBuilder.join(',') + (domainDCs ? ',' + domainDCs : '')
      
      if (!currentNode.children[part]) {
        const originalMatch = flatList.find(f => f.dn.toLowerCase() === currentDn.toLowerCase())
        
        currentNode.children[part] = {
          name: part.split('=')[1],
          dn: currentDn,
          type: originalMatch ? originalMatch.type : (part.startsWith('OU=') ? 'OU' : 'Container'),
          children: {},
          expanded: false
        }
      }
      currentNode = currentNode.children[part]
    })
  })

  function toArray(node) {
    const childrenArray = Object.values(node.children).map(toArray)
    childrenArray.sort((a, b) => a.name.localeCompare(b.name))
    return {
      ...node,
      children: childrenArray
    }
  }

  ouTree.value = [toArray(rootNode)]
}

function toggleNode(dn) {
  const newSet = new Set(expandedNodes.value)
  if (newSet.has(dn)) {
    newSet.delete(dn)
  } else {
    newSet.add(dn)
  }
  expandedNodes.value = newSet
}

function selectOU(node) {
  formData.value.ou = node.dn
  formData.value.ouName = node.name
}

// Lógica del Wizard
function nextStep() {
  if (currentStep.value === 1 && !formData.value.ou && formData.value.accountType !== 'cloud') {
    alert("Debes seleccionar una Unidad Organizativa para continuar.")
    return
  }
  if (currentStep.value === 2) {
    if (!formData.value.firstName || !formData.value.lastName || !formData.value.upnPrefix) {
      alert("Por favor completa los campos obligatorios de identidad.")
      return
    }
  }
  if (currentStep.value === 3) {
    if (!formData.value.password) {
      alert("Debes establecer una contraseña inicial.")
      return
    }
  }
  if (currentStep.value < 4) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

// Autocompletado del nombre
watch([() => formData.value.firstName, () => formData.value.lastName], ([first, last]) => {
  if (first || last) {
    formData.value.fullName = `${first} ${last}`.trim()
    if (first && last) {
      const sam = (first.charAt(0) + last.split(' ')[0]).toLowerCase().replace(/[^a-z0-9]/g, '')
      formData.value.samAccountName = sam
      formData.value.upnPrefix = sam
    }
  }
})

function generatePassword() {
  const u = 'ABCDEFGHJKLMNPQRSTUVWXYZ', l = 'abcdefghjkmnpqrstuvwxyz', d = '23456789', s = '!@#$%&*'
  let pwd = u[~~(Math.random()*u.length)] + l[~~(Math.random()*l.length)] + d[~~(Math.random()*d.length)] + s[~~(Math.random()*s.length)]
  const all = u+l+d+s
  for (let i=0;i<10;i++) pwd += all[~~(Math.random()*all.length)]
  formData.value.password = pwd.split('').sort(()=>Math.random()-.5).join('')
}

function resetForm() {
  currentStep.value = 1
  formData.value = {
    accountType: 'onpremise', ou: '', ouName: '', firstName: '', lastName: '', initials: '', fullName: '', upnPrefix: '', samAccountName: '',
    password: '', mustChangePassword: true, cannotChangePassword: false, passwordNeverExpires: false, accountDisabled: false,
    sharedFolders: [], proxyAddresses: [], userParameters: ''
  }
  expandedNodes.value = new Set([ouTree.value[0]?.dn])
}

function handleClose() {
  resetForm()
  emit('close')
}

async function submitUser() {
  isSubmitting.value = true
  submitStatusText.value = 'Creando cuenta AD...'
  
  const payload = {
    firstName: formData.value.firstName,
    lastName: formData.value.lastName,
    initials: formData.value.initials,
    fullName: formData.value.fullName,
    upn: `${formData.value.upnPrefix}${upnSuffix.value}`,
    samAccountName: formData.value.samAccountName,
    accountType: formData.value.accountType,
    ou: formData.value.ou,
    password: formData.value.password,
    mustChangePassword: formData.value.mustChangePassword,
    cannotChangePassword: formData.value.cannotChangePassword,
    passwordNeverExpires: formData.value.passwordNeverExpires,
    accountDisabled: formData.value.accountDisabled,
    admin_user: localStorage.getItem('display_name') || 'Admin'
  }

  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/accounts/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    })
    
    const data = await res.json()
    if (res.ok && data.success) {
      
      // 1. Asignar atributos adicionales (proxyAddresses / userParameters)
      const updates = {}
      if (formData.value.proxyAddresses && formData.value.proxyAddresses.length > 0) {
        updates.proxyAddresses = formData.value.proxyAddresses.map(p => `${p.type}:${p.value}`)
      }
      if (formData.value.userParameters) {
        updates.userParameters = formData.value.userParameters
      }
      
      if (Object.keys(updates).length > 0) {
        submitStatusText.value = 'Guardando atributos...'
        try {
          await fetch(`${API_BASE}/accounts/profile/bulk-edit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ username: formData.value.samAccountName, updates: updates })
          })
        } catch (e) { console.error('Error guardando atributos:', e) }
      }

      // 2. Asignar carpetas compartidas
      if (formData.value.sharedFolders && formData.value.sharedFolders.length > 0) {
        for (const f of formData.value.sharedFolders) {
          submitStatusText.value = `Asignando permisos: ${f.path}...`
          try {
            const cleanPath = f.path.replace(/^\\\\/, '').replace(/^\\/, '')
            const parts = cleanPath.split('\\')
            if (parts.length < 1 || !parts[0]) continue
            const shareName = parts[0]
            const subpath = parts.slice(1).join('\\')
            
            let permStr = 'ReadAndExecute'
            if (f.permission === 'Modificar') permStr = 'Modify'
            if (f.permission === 'Control Total') permStr = 'FullControl'

            await fetch(`${API_BASE}/fileserver/shares/${encodeURIComponent(shareName)}/acl/add`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
              body: JSON.stringify({
                account: formData.value.samAccountName,
                subpath: subpath,
                permission: permStr
              })
            })
          } catch(e) { console.error('Error asignando carpeta:', e) }
        }
      }

      emit('user-created')
      handleClose()
    } else {
      alert(`Error creando usuario: ${data.error || 'Error desconocido'}`)
    }
  } catch (err) {
    alert(`Error de red: ${err.message}`)
  } finally {
    isSubmitting.value = false
  }
}

watch(() => formData.value.accountType, (newType) => {
  if (newType === 'cloud' && currentStep.value === 1) {
    // Si cambia a cloud y está en el paso 1, puede que quiera avanzar o ignorar
  }
})

watch(() => props.isOpen, (val) => {
  if (val) {
    fetchOUs()
    formData.value.accountType = 'onpremise'
    currentStep.value = 1
  }
})
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
    <!-- Background backdrop -->
    <div 
      class="absolute inset-0 bg-slate-900/10 transition-opacity" 
      @click="handleClose"
    ></div>

    <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
      <!-- Drawer panel -->
      <div class="pointer-events-auto relative w-[50vw] flex flex-col bg-white shadow-2xl">
        
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-5 bg-slate-50 border-b border-slate-200 shrink-0">
          <div class="flex items-center gap-3">
            <div class="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/></svg>
            </div>
            <div>
              <h2 class="text-sm font-bold text-slate-800" id="slide-over-title">Asistente de aprovisionamiento de AD/Cloud</h2>
              <p class="text-[11px] text-slate-500 font-medium">Creación de usuario</p>
            </div>
          </div>
          <button @click="handleClose" class="rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 p-1.5 transition-colors">
            <span class="sr-only">Cerrar panel</span>
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <!-- Progress Steps (Microsoft Style Tabs) -->
        <div v-show="!activeSubView" class="px-6 pt-4 border-b border-slate-200 bg-white shrink-0 flex gap-8">
          <button class="pb-3 text-[13px] font-medium transition-colors relative cursor-default" :class="currentStep === 1 ? 'text-slate-900' : 'text-slate-500'">
            Ubicación
            <div v-if="currentStep === 1" class="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600"></div>
          </button>
          <button class="pb-3 text-[13px] font-medium transition-colors relative cursor-default" :class="currentStep === 2 ? 'text-slate-900' : 'text-slate-500'">
            Identidad
            <div v-if="currentStep === 2" class="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600"></div>
          </button>
          <button class="pb-3 text-[13px] font-medium transition-colors relative cursor-default" :class="currentStep === 3 ? 'text-slate-900' : 'text-slate-500'">
            Seguridad
            <div v-if="currentStep === 3" class="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600"></div>
          </button>
          <button class="pb-3 text-[13px] font-medium transition-colors relative cursor-default" :class="currentStep === 4 ? 'text-slate-900' : 'text-slate-500'">
            Confirmar
            <div v-if="currentStep === 4" class="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600"></div>
          </button>
        </div>

        <!-- Scrollable Content -->
        <div class="flex-1 overflow-y-auto p-6">
          
          <div v-show="!activeSubView">
            
            <!-- Account Type Toggle (Siempre visible al principio del paso 1) -->
            <div v-show="currentStep === 1" class="mb-8 p-4 bg-slate-50 border border-slate-200 rounded-lg">
              <label class="text-[12px] font-semibold text-slate-700 block mb-3 uppercase tracking-wider">Tipo de Cuenta a Crear</label>
              <div class="flex gap-4">
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="radio" v-model="formData.accountType" value="onpremise" class="text-blue-600 focus:ring-blue-600">
                  <span class="text-[13px] font-medium text-slate-800">Sincronizada (Active Directory Local)</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                  <input type="radio" v-model="formData.accountType" value="cloud" class="text-blue-600 focus:ring-blue-600">
                  <span class="text-[13px] font-medium text-slate-800">Solo Nube (Microsoft 365 / Entra ID)</span>
                </label>
              </div>
            </div>

            <!-- STEP 1: UBICACIÓN -->
          <div v-show="currentStep === 1" class="space-y-4">
            
            <div v-if="formData.accountType === 'cloud'" class="flex flex-col items-center justify-center py-12 text-center bg-blue-50/50 rounded-lg border border-blue-100">
              <svg class="w-12 h-12 text-blue-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" /></svg>
              <h3 class="text-[14px] font-semibold text-blue-900 mb-1">Entorno de Nube Seleccionado</h3>
              <p class="text-[12px] text-blue-700 max-w-sm">Las cuentas "Solo Nube" se crean directamente en Microsoft Entra ID. No utilizan Unidades Organizativas (OU) locales. Puedes avanzar al siguiente paso.</p>
            </div>
            
            <div v-else>
              <h3 class="text-base font-semibold text-slate-900 mb-1">Destino del objeto</h3>
              <p class="text-[13px] text-slate-600 mb-6">Selecciona la Unidad Organizativa o Contenedor donde se creará el nuevo usuario.</p>
            </div>
            
            <div v-if="loadingOus && formData.accountType !== 'cloud'" class="flex flex-col items-center justify-center py-12">
              <div class="w-6 h-6 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-3"></div>
              <span class="text-[11px] font-medium text-slate-500">Cargando árbol de AD...</span>
            </div>
            
            <div v-else-if="formData.accountType !== 'cloud'" class="border border-slate-200 rounded-md bg-white shadow-sm overflow-hidden flex flex-col h-[400px]">
              <!-- Árbol Header -->
              <div class="bg-slate-50 border-b border-slate-200 px-4 py-2 flex items-center gap-2 shrink-0">
                <svg class="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                <span class="text-[11px] font-bold text-slate-600">Usuarios y equipos de Active Directory</span>
              </div>
              
              <!-- Árbol Body -->
              <div class="flex-1 overflow-auto p-2">
                <!-- Recursive Tree Component Inline (Since it's simple enough) -->
                <div class="text-[12px] font-medium text-slate-700">
                  <template v-for="node in ouTree" :key="node.dn">
                    <TreeNode :node="node" :level="0" :expandedNodes="expandedNodes" :selectedDn="formData.ou" @toggle="toggleNode" @select="selectOU" />
                  </template>
                </div>
              </div>

              <!-- Selección Actual -->
              <div class="bg-slate-50 border-t border-slate-200 p-3 shrink-0">
                <p class="text-[11px] font-semibold text-slate-700 mb-1">Ubicación seleccionada</p>
                <div class="text-[12px] font-mono text-slate-600 break-all leading-relaxed">
                  {{ formData.ou || 'Ninguna seleccionada' }}
                </div>
              </div>
            </div>
          </div>

          <!-- STEP 2: IDENTIDAD -->
          <div v-show="currentStep === 2" class="space-y-8 px-2">
            <div>
              <h3 class="text-base font-semibold text-slate-900 mb-1">Identidad del usuario</h3>
              <p class="text-[13px] text-slate-600 mb-6">Ingresa los datos personales y de inicio de sesión.</p>
            </div>

            <div class="grid grid-cols-6 gap-x-6 gap-y-8">
              <div class="col-span-6 sm:col-span-2">
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Nombre</label>
                <input v-model="formData.firstName" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors" placeholder="Ej. Juan">
              </div>
              <div class="col-span-6 sm:col-span-1">
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Iniciales</label>
                <input v-model="formData.initials" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors">
              </div>
              <div class="col-span-6 sm:col-span-3">
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Apellidos</label>
                <input v-model="formData.lastName" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors" placeholder="Ej. Pérez">
              </div>

              <!-- Nombre completo a media pantalla para que no sea tan grande -->
              <div class="col-span-6 sm:col-span-4">
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Nombre completo para mostrar</label>
                <input v-model="formData.fullName" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors">
              </div>
            </div>

            <hr class="border-slate-100 my-8">

            <div class="grid grid-cols-6 gap-x-6 gap-y-8">
              <div class="col-span-6 sm:col-span-3">
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Nombre de inicio de sesión (UPN)</label>
                <div class="flex items-center border-b border-slate-300 focus-within:border-blue-600 transition-colors">
                  <input v-model="formData.upnPrefix" type="text" class="w-full text-[13px] border-0 bg-transparent px-0 py-1.5 focus:ring-0 transition-colors font-mono">
                  <select v-model="upnSuffix" class="text-slate-500 text-[13px] font-mono border-0 bg-transparent py-1.5 pl-2 pr-6 focus:ring-0 cursor-pointer">
                    <option value="@local.code" v-if="formData.accountType !== 'cloud'">@local.code</option>
                    <option value="@hogarymoda.com.co">@hogarymoda.com.co</option>
                    <option value="@105code.cloud">@105code.cloud</option>
                  </select>
                </div>
              </div>

              <div class="col-span-6 sm:col-span-3" v-if="formData.accountType !== 'cloud'">
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Nombre inicio de sesión (antiguo)</label>
                <div class="flex items-center border-b border-slate-300 focus-within:border-blue-600 transition-colors">
                  <span class="text-slate-500 text-[13px] font-mono pr-2 select-none">
                    {{ preWin2000 }}
                  </span>
                  <input v-model="formData.samAccountName" type="text" class="w-full text-[13px] border-0 bg-transparent px-0 py-1.5 focus:ring-0 transition-colors font-mono">
                </div>
              </div>
            </div>
          </div>

          <!-- STEP 3: SEGURIDAD -->
          <div v-show="currentStep === 3" class="space-y-8 px-2">
            <div>
              <h3 class="text-base font-semibold text-slate-900 mb-1">Seguridad de la cuenta</h3>
              <p class="text-[13px] text-slate-600 mb-6">Establece la contraseña inicial y las políticas de la cuenta.</p>
            </div>

            <div class="max-w-md">
              <div class="flex items-center justify-between mb-1">
                <label class="block text-[12px] font-medium text-slate-700">Contraseña temporal</label>
                <button @click="generatePassword" class="text-[12px] font-medium text-blue-600 hover:text-blue-800 transition-colors">Generar contraseña</button>
              </div>
              <input v-model="formData.password" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors font-mono" placeholder="Ingresa una contraseña...">
            </div>

            <div class="space-y-4 max-w-md pt-2">
              <label class="flex items-start gap-3 cursor-pointer group">
                <input v-model="formData.mustChangePassword" type="checkbox" class="mt-0.5 rounded-none text-blue-600 focus:ring-0 focus:ring-offset-0 border-slate-300 cursor-pointer">
                <span class="text-[13px] text-slate-700 font-medium group-hover:text-blue-700 transition-colors">El usuario debe cambiar la contraseña en el siguiente inicio de sesión</span>
              </label>
              
              <label class="flex items-start gap-3 cursor-pointer group">
                <input v-model="formData.cannotChangePassword" :disabled="formData.mustChangePassword" type="checkbox" class="mt-0.5 rounded-none text-blue-600 focus:ring-0 focus:ring-offset-0 border-slate-300 disabled:opacity-50 cursor-pointer">
                <span class="text-[13px] text-slate-700 font-medium group-hover:text-blue-700 transition-colors" :class="{'opacity-50': formData.mustChangePassword}">El usuario no puede cambiar la contraseña</span>
              </label>
              
              <label class="flex items-start gap-3 cursor-pointer group">
                <input v-model="formData.passwordNeverExpires" :disabled="formData.mustChangePassword" type="checkbox" class="mt-0.5 rounded-none text-blue-600 focus:ring-0 focus:ring-offset-0 border-slate-300 disabled:opacity-50 cursor-pointer">
                <span class="text-[13px] text-slate-700 font-medium group-hover:text-blue-700 transition-colors" :class="{'opacity-50': formData.mustChangePassword}">La contraseña nunca expira</span>
              </label>
              
              <div class="pt-2 border-t border-slate-200">
                <label class="flex items-start gap-3 cursor-pointer group">
                  <input v-model="formData.accountDisabled" type="checkbox" class="mt-0.5 rounded-none text-red-600 focus:ring-0 focus:ring-offset-0 border-slate-300 cursor-pointer">
                  <span class="text-[13px] text-slate-700 font-medium group-hover:text-red-700 transition-colors">La cuenta está deshabilitada</span>
                </label>
              </div>
            </div>
            
            <div class="mt-4 p-3 bg-blue-50/50 border border-blue-100 flex items-start gap-3 rounded-md" v-if="formData.mustChangePassword">
              <svg class="w-4 h-4 text-blue-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              <p class="text-[11px] text-blue-700 leading-relaxed">
                Al obligar al cambio de contraseña, las políticas restrictivas de contraseña se desactivan automáticamente en el servidor.
              </p>
            </div>
          </div>

          <!-- STEP 4: RESUMEN -->
          <div v-show="currentStep === 4" class="space-y-4">
            <div>
              <h3 class="text-[13px] font-bold text-slate-800 uppercase tracking-widest mb-1">Confirmar CreaciÃ³n</h3>
              <p class="text-[12px] text-slate-500">Revisa los datos antes de ejecutar la acciÃ³n en el Directorio Activo.</p>
            </div>

            <div class="border border-slate-200 rounded-md overflow-hidden text-sm">
              <div class="grid grid-cols-3 border-b border-slate-100">
                <div class="col-span-1 bg-slate-50 px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Display Name</div>
                <div class="col-span-2 px-4 py-3 text-slate-800 font-medium">{{ formData.fullName }}</div>
              </div>
              <div class="grid grid-cols-3 border-b border-slate-100">
                <div class="col-span-1 bg-slate-50 px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Logon Name</div>
                <div class="col-span-2 px-4 py-3 text-slate-800 font-mono text-[13px]">{{ formData.upnPrefix }}{{ upnSuffix }}</div>
              </div>
              <div class="grid grid-cols-3 border-b border-slate-100">
                <div class="col-span-1 bg-slate-50 px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">sAMAccountName</div>
                <div class="col-span-2 px-4 py-3 text-slate-800 font-mono text-[13px]">{{ preWin2000 }}{{ formData.samAccountName }}</div>
              </div>
              <div class="grid grid-cols-3 border-b border-slate-100">
                <div class="col-span-1 bg-slate-50 px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">UbicaciÃ³n (OU)</div>
                <div class="col-span-2 px-4 py-3 text-slate-800 font-mono text-[11px] break-all">{{ formData.ou }}</div>
              </div>
              <div class="grid grid-cols-3">
                <div class="col-span-1 bg-slate-50 px-4 py-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Flags</div>
                <div class="col-span-2 px-4 py-3">
                  <div class="flex flex-wrap gap-1.5">
                    <span v-if="formData.mustChangePassword" class="px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-200 rounded-sm text-[10px] font-bold">Cambio al iniciar</span>
                    <span v-if="formData.accountDisabled" class="px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-sm text-[10px] font-bold">Cuenta Inactiva</span>
                    <span v-if="formData.passwordNeverExpires && !formData.mustChangePassword" class="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-sm text-[10px] font-bold">Pwd no expira</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Sugerencias Opcionales -->
            <div class="mt-8 pt-6 border-t border-slate-200">
              <h3 class="text-[13px] font-semibold text-slate-900 mb-3">Acciones opcionales antes de guardar</h3>
              <ul class="space-y-4">
                <li>
                  <a @click="openSubView('folders')" class="text-[13px] font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer flex items-center gap-2 transition-colors">
                    <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
                    Añadir carpetas compartidas
                    <span v-if="formData.sharedFolders.length" class="ml-auto bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-[11px] font-bold">{{ formData.sharedFolders.length }} agregadas</span>
                  </a>
                </li>
                <li>
                  <a @click="openSubView('attributes')" class="text-[13px] font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer flex items-center gap-2 transition-colors">
                    <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
                    Configurar atributos avanzados (ProxyAddresses, UserParameters)
                    <span v-if="formData.proxyAddresses.length || formData.userParameters" class="ml-auto bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-[11px] font-bold">Configurado</span>
                  </a>
                </li>
              </ul>
            </div>
          </div>
          </div> <!-- Cierre de MAIN WIZARD STEPS -->

          <!-- SUBVIEWS (Carpetas) -->
          <div v-if="activeSubView === 'folders'" class="space-y-8 animate-in fade-in duration-200">
            <div class="flex items-center gap-3 border-b border-slate-200 pb-4">
              <button @click="closeSubView" class="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
              <div>
                <h3 class="text-base font-semibold text-slate-900 mb-0.5">Carpetas compartidas</h3>
                <p class="text-[12px] text-slate-500">Asigna permisos NTFS al usuario antes de crearlo.</p>
              </div>
            </div>

            <div class="space-y-6">
              <div>
                <div class="space-y-2 mb-4">
                  <div v-for="(folder, i) in formData.sharedFolders" :key="i" class="flex items-center justify-between p-3 border border-slate-200 bg-slate-50">
                    <div class="flex flex-col">
                      <span class="text-[13px] font-mono text-slate-800">{{ folder.path }}</span>
                      <span class="text-[11px] font-bold text-slate-500 uppercase mt-0.5">{{ folder.permission }}</span>
                    </div>
                    <button @click="formData.sharedFolders.splice(i, 1)" class="text-slate-400 hover:text-red-600 transition-colors p-1">
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                  <p v-if="formData.sharedFolders.length === 0" class="text-[13px] text-slate-500 italic py-4 text-center border border-dashed border-slate-300">No hay carpetas en cola de asignación.</p>
                </div>
                
                <div class="bg-white border border-slate-200 p-4 shadow-sm flex flex-col gap-4">
                  <h4 class="text-[12px] font-semibold text-slate-800">Añadir nueva asignación</h4>
                  <div class="flex flex-col sm:flex-row gap-3">
                    <input 
                      v-model="newFolderPath" 
                      type="text" 
                      list="available-shares-list"
                      @keydown.tab.prevent="handleFolderTabComplete"
                      placeholder="\\Empresa_Files\Gerencia" 
                      class="flex-1 text-[13px] border-0 border-b border-slate-300 bg-transparent px-1 py-1.5 focus:ring-0 focus:border-blue-600 font-mono"
                    </input>
                    <datalist id="available-shares-list">
                      <option v-for="suggestion in folderSuggestions" :key="suggestion" :value="suggestion"></option>
                    </datalist>
                    
                    <div class="flex gap-2">
                      <select v-model="newFolderPerm" class="text-[13px] border border-slate-300 bg-white px-2 py-1.5 focus:ring-0 focus:border-blue-600 outline-none w-32">
                        <option value="Lectura">Lectura</option>
                        <option value="Modificar">Modificar</option>
                        <option value="Control Total">Control Total</option>
                      </select>
                      <button @click="addSharedFolder" class="px-4 py-1.5 bg-slate-800 text-white text-[12px] font-semibold hover:bg-slate-900 transition-colors">Añadir</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="pt-6 border-t border-slate-200 flex justify-end">
               <button @click="closeSubView" class="px-5 py-2.5 bg-white border border-slate-300 text-slate-700 text-[13px] font-medium shadow-sm hover:bg-slate-50 transition-colors">Volver al resumen</button>
            </div>
          </div>

          <!-- SUBVIEWS (Atributos) -->
          <div v-if="activeSubView === 'attributes'" class="space-y-8 animate-in fade-in duration-200">
            <div class="flex items-center gap-3 border-b border-slate-200 pb-4">
              <button @click="closeSubView" class="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
              <div>
                <h3 class="text-base font-semibold text-slate-900 mb-0.5">Atributos Avanzados</h3>
                <p class="text-[12px] text-slate-500">Configura direcciones proxy y parámetros adicionales.</p>
              </div>
            </div>

            <div class="space-y-8">
              <!-- Proxy Addresses -->
              <div>
                <h4 class="text-[13px] font-semibold text-slate-800 mb-4">ProxyAddresses</h4>
                <div class="space-y-2 mb-4">
                  <div v-for="(addr, i) in formData.proxyAddresses" :key="i" class="flex items-center justify-between p-2 border border-slate-200 bg-slate-50">
                    <span class="text-[13px] font-mono text-slate-800 px-2">{{ addr }}</span>
                    <button @click="formData.proxyAddresses.splice(i, 1)" class="text-slate-400 hover:text-red-600 transition-colors p-1">
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                  </div>
                  <p v-if="formData.proxyAddresses.length === 0" class="text-[13px] text-slate-500 italic py-3 text-center border border-dashed border-slate-300">Sin direcciones proxy (SMTP/SIP).</p>
                </div>
                
                <div class="bg-white border border-slate-200 p-4 shadow-sm flex flex-col gap-4">
                  <h4 class="text-[12px] font-semibold text-slate-800">Añadir dirección</h4>
                  <div class="flex flex-col sm:flex-row gap-3">
                    <select v-model="newProxyType" class="text-[13px] border border-slate-300 bg-white px-2 py-1.5 focus:ring-0 focus:border-blue-600 outline-none w-32 font-mono">
                      <option value="SMTP">SMTP</option>
                      <option value="smtp">smtp</option>
                      <option value="SIP">SIP</option>
                    </select>
                    <div class="flex-1 flex gap-2">
                      <input v-model="newProxyValue" type="text" placeholder="usuario@dominio.com" class="flex-1 text-[13px] border-0 border-b border-slate-300 bg-transparent px-1 py-1.5 focus:ring-0 focus:border-blue-600 outline-none font-mono">
                      <button @click="addProxyAddress" class="px-4 py-1.5 bg-slate-800 text-white text-[12px] font-semibold hover:bg-slate-900 transition-colors">Añadir</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- UserParameters -->
              <div class="pt-6 border-t border-slate-100">
                <h4 class="text-[13px] font-semibold text-slate-800 mb-2">UserParameters</h4>
                <p class="text-[12px] text-slate-500 mb-4">Usado comúnmente para parámetros de Terminal Services u otros metadatos.</p>
                <textarea v-model="formData.userParameters" rows="3" placeholder="CtxCfgPresent..." class="w-full text-[13px] border border-slate-300 bg-white px-3 py-2 shadow-sm focus:ring-0 focus:border-blue-600 outline-none resize-y font-mono"></textarea>
              </div>
            </div>
            
            <div class="pt-6 border-t border-slate-200 flex justify-end">
               <button @click="closeSubView" class="px-5 py-2.5 bg-white border border-slate-300 text-slate-700 text-[13px] font-medium shadow-sm hover:bg-slate-50 transition-colors">Volver al resumen</button>
            </div>
          </div>
          
        </div>

        <!-- Footer Actions -->
        <div v-show="!activeSubView" class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between shrink-0">
          <button @click="handleClose" class="text-sm font-medium text-slate-500 hover:text-slate-800 transition-colors">Cancelar</button>
          <div class="flex gap-2">
            <button v-show="currentStep > 1" @click="prevStep" class="px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-sm hover:bg-slate-50 transition-colors shadow-sm">
              Anterior
            </button>
            <button v-show="currentStep < 4" @click="nextStep" class="px-6 py-2 text-sm font-medium text-white bg-slate-800 rounded-sm hover:bg-slate-900 transition-colors shadow-sm">
              Siguiente
            </button>
            <button v-show="currentStep === 4" @click="submitUser" :disabled="isSubmitting" class="px-6 py-2 text-sm font-bold text-white bg-blue-600 rounded-sm hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm flex items-center gap-2">
              <span v-if="isSubmitting" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              {{ isSubmitting ? submitStatusText : 'Crear Usuario' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
// Componente recursivo para el Ã¡rbol
import { h, resolveComponent } from 'vue'

const TreeNode = {
  name: 'TreeNode',
  props: ['node', 'level', 'expandedNodes', 'selectedDn'],
  emits: ['toggle', 'select'],
  setup(props, { emit }) {
    return () => {
      const node = props.node
      const hasChildren = node.children && node.children.length > 0
      const isExpanded = props.expandedNodes.has(node.dn)
      const isSelected = props.selectedDn === node.dn
      
      // Icono segÃºn tipo
      let iconColor = 'text-amber-400'
      let iconPath = 'M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z' // Folder
      
      if (node.type === 'Domain') {
        iconColor = 'text-slate-400'
        iconPath = 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' // Server/Domain
      } else if (node.type === 'Container') {
        iconColor = 'text-blue-500' // Contenedor azul
      }

      const paddingLeft = (props.level * 16) + 'px'

      const renderChildren = () => {
        if (hasChildren && isExpanded) {
          return node.children.map(child => {
            return h(resolveComponent('TreeNode'), {
              node: child,
              level: props.level + 1,
              expandedNodes: props.expandedNodes,
              selectedDn: props.selectedDn,
              onToggle: (dn) => emit('toggle', dn),
              onSelect: (n) => emit('select', n)
            })
          })
        }
        return null
      }

      return h('div', { class: 'select-none' }, [
        h('div', { 
          class: ['flex items-center py-1 px-1 rounded-sm cursor-pointer transition-colors', isSelected ? 'bg-blue-50' : 'hover:bg-slate-50'],
          style: { paddingLeft }
        }, [
          // Chevron
          h('div', { 
            class: ['w-5 h-5 flex items-center justify-center shrink-0 cursor-pointer rounded-sm hover:bg-slate-200/50', !hasChildren ? 'opacity-0' : ''],
            onClick: (e) => { e.stopPropagation(); if (hasChildren) emit('toggle', node.dn) }
          }, [
            h('svg', { class: ['w-3 h-3 text-slate-500 transition-transform', isExpanded ? 'rotate-90' : ''], viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5 }, [
              h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9 5l7 7-7 7' })
            ])
          ]),
          // Icon and Text
          h('div', {
            class: 'flex items-center gap-2 w-full ml-1',
            onClick: () => emit('select', node)
          }, [
            h('svg', { class: ['w-4 h-4 shrink-0', iconColor], viewBox: '0 0 24 24', fill: 'currentColor' }, [
              h('path', { d: iconPath })
            ]),
            h('span', { class: ['text-[12px] truncate', isSelected ? 'font-bold text-blue-700' : 'text-slate-700'] }, node.name)
          ])
        ]),
        renderChildren()
      ])
    }
  }
}

export default {
  components: { TreeNode }
}
</script>
