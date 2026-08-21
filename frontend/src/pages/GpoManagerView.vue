<script setup>
import { ref, computed, watch, h, resolveComponent, onMounted, nextTick } from 'vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const activeTab = ref('gpo')
const showNewGpoPanel = ref(false)
const currentStep = ref(1)

// Datos de GPOs Reales
const gpos = ref([])
const loadingGpos = ref(false)

async function fetchGpos() {
  loadingGpos.value = true
  try {
    const res = await fetch(`${API_BASE}/gpo/list`)
    if (res.ok) {
      gpos.value = await res.json()
    }
  } catch (err) {
    console.error('Error cargando GPOs:', err)
  } finally {
    loadingGpos.value = false
  }
}

onMounted(() => {
  fetchGpos()
})


// Formulario de Nueva GPO
const newGpo = ref({
  name: '',
  targetOu: 'DC=code,DC=local',
  targetOuName: 'code.local',
  templateType: 'wallpaper',
  configParams: '',
  isActive: true
})

const templateOptions = [
  { value: 'wallpaper', label: 'Fondo de Pantalla' },
  { value: 'network_drive', label: 'Mapear Unidad de Red' },
  { value: 'screen_lock', label: 'Bloqueo de Pantalla' },
  { value: 'printer', label: 'Desplegar Impresora' }
]

// Auto-selección sugerida para GPOs globales (ej. Wallpaper)
watch(() => newGpo.value.templateType, (newType) => {
  if (newType === 'wallpaper') {
    newGpo.value.targetOu = 'DC=code,DC=local'
    newGpo.value.targetOuName = 'code.local'
  }
})


// --- Lógica del Árbol de OUs ---
const loadingOus = ref(false)
const ouTree = ref([])
const expandedNodes = ref(new Set())

async function fetchOUs() {
  if (ouTree.value.length > 0) return // Ya cargados
  
  loadingOus.value = true
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/accounts/ous`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
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
  newGpo.value.targetOu = node.dn
  newGpo.value.targetOuName = node.name
}

// --- Lógica del Panel ---
const openPanel = () => {
  showNewGpoPanel.value = true
  currentStep.value = 1
  fetchOUs()
}

const resetForm = () => {
  newGpo.value = {
    name: '',
    targetOu: 'DC=code,DC=local', // Defaulting since default type is wallpaper
    targetOuName: 'code.local',
    templateType: 'wallpaper',
    configParams: '',
    isActive: true
  }
  currentStep.value = 1
}

const closePanel = () => {
  showNewGpoPanel.value = false
  resetForm()
}

const nextStep = () => {
  if (currentStep.value < 3) currentStep.value++
}

const prevStep = () => {
  if (currentStep.value > 1) currentStep.value--
}

const isSubmitting = ref(false)
const imageError = ref(false)

const handleImageError = () => {
  imageError.value = true
}

// Reset image error when path changes
watch(() => newGpo.value.configParams, () => {
  imageError.value = false
})

const generateAndReview = async () => {
  isSubmitting.value = true
  try {
    const token = localStorage.getItem('access_token')
    
    // 1. Generar el script de creación y vinculación
    const params = newGpo.value.templateType === 'wallpaper' ? { path: newGpo.value.configParams } : {}
    
    const generateRes = await fetch(`${API_BASE}/gpo/generate/template`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        template_type: newGpo.value.templateType,
        name: newGpo.value.name,
        target_ou: newGpo.value.targetOu,
        is_active: newGpo.value.isActive,
        params: params
      })
    })

    if (!generateRes.ok) throw new Error('Error al generar la plantilla de GPO')
    const { script } = await generateRes.json()

    // 2. Ejecutar el script generado en el DC
    const executeRes = await fetch(`${API_BASE}/gpo/execute`, {
      method: 'POST',
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ script: script })
    })

    if (!executeRes.ok) throw new Error('Error ejecutando la directiva en el servidor')
    
    alert(`¡Directiva de Grupo '${newGpo.value.name}' creada y vinculada correctamente!`)
    closePanel()
    fetchGpos()
  } catch (error) {
    console.error('Error creando GPO:', error)
    alert('Ocurrió un error al crear la GPO: ' + error.message)
  } finally {
    isSubmitting.value = false
  }
}

const showAiPanel = ref(false)
const aiInput = ref('')
const aiBusy = ref(false)
const aiError = ref('')
const aiMessages = ref([])
const lastProposal = ref(null)
const applyingProposal = ref(false)
const chatEnd = ref(null)

const aiSuggestions = [
  'Quiero un fondo de pantalla corporativo',
  'Que todos vean una carpeta compartida como unidad',
  'Bloquear puertos USB en los equipos',
  'Bloqueo de pantalla a los 15 minutos'
]

const proposalTypeLabel = (type) => ({
  wallpaper: 'Fondo de pantalla',
  network_drive: 'Unidad de red',
  screen_lock: 'Bloqueo de pantalla',
  printer: 'Impresora',
  custom: 'Personalizada'
}[type] || 'GPO')

const proposalReady = computed(() =>
  Boolean(lastProposal.value && lastProposal.value.viable && lastProposal.value.ready)
)

const proposalRows = computed(() => {
  const p = lastProposal.value
  if (!p) return []
  const params = p.params || {}
  const rows = [
    ['Tipo', proposalTypeLabel(p.template_type)]
  ]
  if (params.path) rows.push(['Ruta', params.path])
  if (params.letter) rows.push(['Letra', params.letter])
  if (params.minutes) rows.push(['Minutos', String(params.minutes)])
  rows.push(['Alcance', p.target_ou || 'Sin vincular todavía (se confirma al crear)'])
  return rows
})

const openAiPanel = () => {
  showNewGpoPanel.value = false
  showAiPanel.value = true
}

const closeAiPanel = () => {
  showAiPanel.value = false
}

const toggleAiPanel = () => {
  if (showAiPanel.value) closeAiPanel()
  else openAiPanel()
}

const escapeHtml = (value) =>
  String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

const formatAiHtml = (text) => {
  let html = escapeHtml(text)
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
  html = html.replace(/`([^`]+)`/g, '<code class="font-mono text-[12px] bg-slate-100 px-1 py-0.5 text-slate-800">$1</code>')
  html = html.replace(/^[-•]\s+(.+)$/gm, '<div class="pl-3 border-l border-slate-200 my-0.5">$1</div>')
  html = html.replace(/\n/g, '<br>')
  return html
}

const scrollChat = async () => {
  await nextTick()
  chatEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
}

const sendAi = async (preset) => {
  const content = (typeof preset === 'string' ? preset : aiInput.value).trim()
  if (!content || aiBusy.value) return
  aiInput.value = ''
  aiError.value = ''
  lastProposal.value = null
  aiMessages.value.push({ role: 'user', content })
  aiBusy.value = true
  await scrollChat()
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/gpo/chat`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: aiMessages.value.map((m) => ({ role: m.role, content: m.content }))
      })
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      const detail = data.detail
      throw new Error(typeof detail === 'string' ? detail : 'El asistente no respondió')
    }
    aiMessages.value.push({ role: 'assistant', content: data.reply || 'Sin respuesta' })
    lastProposal.value = data.proposal || null
  } catch (err) {
    aiError.value = err.message || 'Error de red'
  } finally {
    aiBusy.value = false
    await scrollChat()
  }
}

const useProposalInWizard = () => {
  const p = lastProposal.value
  if (!p) return
  if (p.name) newGpo.value.name = p.name
  const t = p.template_type
  if (['wallpaper', 'network_drive', 'screen_lock', 'printer'].includes(t)) {
    newGpo.value.templateType = t
  }
  const params = p.params || {}
  if (t === 'wallpaper') newGpo.value.configParams = params.path || ''
  else if (t === 'network_drive') newGpo.value.configParams = [params.letter, params.path].filter(Boolean).join(' ')
  else if (t === 'screen_lock') newGpo.value.configParams = params.minutes ? String(params.minutes) : ''
  else if (t === 'printer') newGpo.value.configParams = params.path || ''
  else newGpo.value.configParams = params.path || ''
  if (p.target_ou) {
    newGpo.value.targetOu = p.target_ou
    newGpo.value.targetOuName = p.target_ou
  }
  showAiPanel.value = false
  openPanel()
}

const applyProposal = async () => {
  const p = lastProposal.value
  if (!p || p.viable === false || !p.ready) return
  applyingProposal.value = true
  try {
    const token = localStorage.getItem('access_token')
    const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    let script = p.script
    if (!script && p.template_type && p.template_type !== 'custom') {
      const gen = await fetch(`${API_BASE}/gpo/generate/template`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          template_type: p.template_type,
          name: p.name,
          target_ou: p.target_ou || '',
          is_active: true,
          params: p.params || {}
        })
      })
      if (!gen.ok) throw new Error('No se pudo generar la plantilla')
      script = (await gen.json()).script
    }
    if (!script) throw new Error('Todavía faltan datos para crear la GPO')
    const exec = await fetch(`${API_BASE}/gpo/execute`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ script })
    })
    if (!exec.ok) {
      const err = await exec.json().catch(() => ({}))
      throw new Error(typeof err.detail === 'string' ? err.detail : 'Error ejecutando en el DC')
    }
    
    // GPO Creada con éxito. Añadir al chat para que la IA sepa que ya terminamos.
    aiMessages.value.push({
      role: 'assistant',
      content: `✅ **¡Listo Fabián!** He enviado la instrucción a tu servidor (192.168.20.100) y la directiva **${p.name}** se ha creado exitosamente en el Active Directory.`
    })
    
    // Simular que el usuario le avisa a la IA que ya la creó, para que no la vuelva a proponer
    aiMessages.value.push({
      role: 'user',
      content: `(Nota interna del sistema: El usuario acaba de confirmar la creación de la GPO ${p.name}. Ya no debes proponerla de nuevo).`
    })

    lastProposal.value = null
    fetchGpos()
    
    // Hacer scroll abajo
    setTimeout(() => {
      if (chatEnd.value) {
        chatEnd.value.scrollIntoView({ behavior: 'smooth' })
      }
    }, 100)
    
  } catch (err) {
    alert(err.message)
  } finally {
    applyingProposal.value = false
  }
}
</script>

<script>
// Componente recursivo para el árbol
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
      
      // Icono según tipo
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
          class: ['flex items-center py-1.5 px-2 rounded cursor-pointer transition-colors border border-transparent', isSelected ? 'bg-blue-50 border-blue-200' : 'hover:bg-slate-50'],
          style: { paddingLeft }
        }, [
          // Chevron
          h('div', { 
            class: ['w-5 h-5 flex items-center justify-center shrink-0 cursor-pointer rounded hover:bg-slate-200/50', !hasChildren ? 'opacity-0' : ''],
            onClick: (e) => { e.stopPropagation(); if (hasChildren) emit('toggle', node.dn) }
          }, [
            h('svg', { class: ['w-3.5 h-3.5 text-slate-500 transition-transform', isExpanded ? 'rotate-90' : ''], viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5 }, [
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
            h('span', { class: ['text-[13px] truncate', isSelected ? 'font-bold text-blue-700' : 'text-slate-700'] }, node.name)
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

<template>
  <div class="flex flex-col h-[calc(100vh-64px)] w-full overflow-hidden bg-gray-50">
    
    <!-- Header y Barra de Herramientas -->
    <div class="bg-white px-6 py-4 border-b border-gray-200 shrink-0">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <h1 class="text-xl font-bold text-gray-900">Gestor de Políticas y Tareas</h1>
          <p class="text-[13px] text-gray-500 mt-1">Administra y despliega directivas de grupo (GPO) y tareas programadas en el dominio.</p>
        </div>
        <div class="flex items-center space-x-3">
        <button
          @click="toggleAiPanel"
          :class="[
            'px-3 py-2 text-sm font-medium flex items-center transition-colors border',
            showAiPanel
              ? 'bg-slate-900 text-white border-slate-900'
              : 'bg-white text-slate-700 border-gray-200 hover:bg-slate-50'
          ]"
          :title="showAiPanel ? 'Cerrar asistente' : 'Abrir asistente IA'"
        >
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.75" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/></svg>
          {{ showAiPanel ? 'Cerrar asistente' : 'Asistente IA' }}
        </button>
        <button @click="openPanel" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium flex items-center transition-colors">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
          Nueva Política
        </button>
        <button class="px-4 py-2 border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium flex items-center transition-colors">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
          Nueva Tarea
        </button>
        
        <!-- Botón Recargar -->
        <button @click="fetchGpos" class="p-2 border border-gray-200 text-gray-500 rounded-lg hover:bg-gray-50 transition-colors" title="Actualizar">
          <svg class="w-5 h-5" :class="{'animate-spin': loadingGpos}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
        </button>
          <button class="flex items-center justify-center p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors" title="Exportar">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          </button>
        </div>
      </div>
      
      <!-- Pestañas -->
      <nav class="flex items-center gap-6 mt-2">
        <button @click="activeTab = 'gpo'" :class="['pb-2 text-[13px] font-semibold transition-colors border-b-2', activeTab === 'gpo' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300']">
          Directivas (GPO)
        </button>
        <button @click="activeTab = 'tasks'" :class="['pb-2 text-[13px] font-semibold transition-colors border-b-2', activeTab === 'tasks' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300']">
          Tareas Programadas
        </button>
        <button @click="activeTab = 'history'" :class="['pb-2 text-[13px] font-semibold transition-colors border-b-2', activeTab === 'history' ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300']">
          Historial de Ejecución
        </button>
      </nav>
    </div>

    <!-- Área de contenido + chat: el chat empuja la tabla, no la tapa -->
    <div class="flex-1 min-h-0 flex">
    <div class="flex-1 min-w-0 overflow-auto p-6">
      
      <!-- Pestaña GPOs Activas -->
      <div v-if="activeTab === 'gpo'" class="bg-white border border-gray-200 rounded-md shadow-sm overflow-hidden">
        
        <!-- Loading State -->
        <div v-if="loadingGpos" class="p-12 text-center">
          <svg class="animate-spin h-8 w-8 text-blue-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p class="text-gray-500 text-sm">Buscando políticas en el Directorio Activo...</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-sm text-gray-600">
            <thead class="bg-gray-50 border-b border-gray-200 text-xs font-bold text-gray-500 uppercase tracking-wider">
              <tr>
                <th class="px-4 py-3">Nombre de Política</th>
                <th class="px-4 py-3">Tipo</th>
                <th class="px-4 py-3">Alcance (OU Target)</th>
                <th class="px-4 py-3">Estado</th>
                <th class="px-4 py-3 text-right">Última Modificación</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="gpo in gpos" :key="gpo.id" class="hover:bg-gray-50/80 transition-colors">
                <td class="px-4 py-3 font-semibold text-gray-900">{{ gpo.name }}</td>
                <td class="px-4 py-3 text-gray-500">{{ gpo.type }}</td>
                <td class="px-4 py-3 font-mono text-[12px] text-blue-700">{{ gpo.target }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-1.5">
                    <span :class="['w-2 h-2 rounded-full', gpo.status === 'Activo' ? 'bg-emerald-500' : 'bg-gray-400']"></span>
                    <span :class="['text-[12px] font-medium', gpo.status === 'Activo' ? 'text-emerald-700' : 'text-gray-600']">{{ gpo.status }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-right text-gray-500 font-mono text-[12px]">{{ gpo.last_modified }}</td>
              </tr>
              <tr v-if="gpos.length === 0">
                <td colspan="5" class="px-4 py-8 text-center text-gray-500">
                  No se encontraron Políticas de Grupo (GPO) en el dominio.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Otras Pestañas (En Construcción) -->
      <div v-else class="flex flex-col items-center justify-center py-20 text-center">
        <svg class="w-16 h-16 text-gray-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
        <h2 class="text-lg font-bold text-gray-700">Módulo en Desarrollo</h2>
        <p class="text-[13px] text-gray-500 mt-2 max-w-sm">Esta sección está siendo rediseñada para ofrecerte un mejor control y trazabilidad de los despliegues.</p>
      </div>
    </div>

    <aside v-if="showAiPanel" class="w-[400px] xl:w-[440px] shrink-0 border-l border-slate-200 bg-white flex flex-col min-h-0">
      <div class="h-12 px-4 border-b border-slate-200 flex items-center justify-between shrink-0">
        <div>
          <div class="text-[13px] font-semibold text-slate-900">Asistente de GPO</div>
          <div class="text-[11px] text-slate-500">Razona antes de crear · code.local</div>
        </div>
        <button type="button" @click="closeAiPanel" class="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100" title="Cerrar y devolver el espacio">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-4 py-4 space-y-6 min-h-0 bg-slate-50">
        <div v-if="aiMessages.length === 0" class="pt-2">
          <div class="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm">
            <p class="text-[13px] text-slate-700 leading-relaxed">¡Hola Fabián! Soy tu Ingeniero de GPO experto. Cuéntame tu idea, aunque esté incompleta. Primero analizaré si es viable, cómo funcionaría y qué datos nos faltan.</p>
          </div>
          <div class="mt-4 flex flex-col gap-2">
            <button
              v-for="s in aiSuggestions"
              :key="s"
              type="button"
              class="w-full text-left text-[12px] px-4 py-2.5 text-blue-700 bg-blue-50/50 hover:bg-blue-100/80 rounded-xl border border-blue-100 transition-colors"
              @click="sendAi(s)"
            >{{ s }}</button>
          </div>
        </div>

        <div v-for="(msg, idx) in aiMessages" :key="idx" class="flex flex-col">
          <template v-if="!msg.content.startsWith('(Nota interna')">
            <div v-if="msg.role === 'user'" class="self-end max-w-[85%] bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm shadow-sm text-[13px] leading-relaxed">
              {{ msg.content }}
            </div>
            <div v-else class="self-start max-w-[90%] bg-white border border-slate-200 text-slate-800 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm text-[13px] leading-relaxed prose prose-sm prose-slate">
              <div v-html="formatAiHtml(msg.content)"></div>
            </div>
          </template>
        </div>

        <div v-if="aiBusy" class="self-start max-w-[80%] bg-white border border-slate-200 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm text-[13px] text-slate-500 flex items-center gap-3">
          <span class="flex gap-1">
            <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
            <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></span>
            <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
          </span>
          Analizando dominio...
        </div>
        <p v-if="aiError" class="text-[12px] text-red-600 bg-red-50 p-3 rounded-xl border border-red-100">{{ aiError }}</p>

        <div v-if="proposalReady" class="mt-4 bg-white border border-blue-200 rounded-2xl overflow-hidden shadow-md">
          <div class="flex items-center justify-between gap-2 px-3 py-2 bg-white border-b border-slate-200">
            <div class="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Especificación</div>
            <span class="text-[10px] font-semibold uppercase tracking-wide text-blue-700 bg-blue-50 border border-blue-100 px-1.5 py-0.5">{{ proposalTypeLabel(lastProposal.template_type) }}</span>
          </div>
          <div class="px-3 py-3 bg-white">
            <div class="text-[14px] font-semibold text-slate-900 leading-snug">{{ lastProposal.name || 'GPO sin nombre' }}</div>
            <p v-if="lastProposal.summary" class="text-[12px] text-slate-600 mt-1 leading-relaxed">{{ lastProposal.summary }}</p>
          </div>
          <dl class="border-t border-slate-200 divide-y divide-slate-100 bg-white">
            <div v-for="row in proposalRows" :key="row[0]" class="grid grid-cols-[88px_1fr] gap-2 px-3 py-2">
              <dt class="text-[11px] text-slate-500">{{ row[0] }}</dt>
              <dd class="text-[12px] text-slate-900 font-medium break-all">{{ row[1] }}</dd>
            </div>
          </dl>
          <div v-if="lastProposal.warnings?.length" class="px-3 py-2 text-[11px] text-amber-800 bg-amber-50 border-t border-amber-100">
            {{ lastProposal.warnings.join(' · ') }}
          </div>
          <div class="flex items-center gap-2 px-3 py-3 bg-white border-t border-slate-200">
            <button type="button" class="px-3 py-1.5 text-[12px] font-medium border border-slate-300 bg-white hover:bg-slate-50" @click="useProposalInWizard">Usar en el formulario</button>
            <button type="button" :disabled="applyingProposal" class="px-3 py-1.5 text-[12px] font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50" @click="applyProposal">
              {{ applyingProposal ? 'Creando...' : 'Crear en el DC' }}
            </button>
          </div>
        </div>
        <div ref="chatEnd"></div>
      </div>

      <form class="p-3 border-t border-slate-200 shrink-0" @submit.prevent="sendAi()">
        <textarea
          v-model="aiInput"
          rows="2"
          :disabled="aiBusy"
          @keydown.enter.exact.prevent="sendAi()"
          placeholder="Cuéntame la idea. No hace falta que esté completa..."
          class="w-full border border-slate-300 px-3 py-2 text-[13px] text-slate-900 resize-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        ></textarea>
        <div class="flex justify-end mt-2">
          <button type="submit" :disabled="aiBusy || !aiInput.trim()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-[12px] font-semibold disabled:opacity-40">
            Enviar
          </button>
        </div>
      </form>
    </aside>
    </div>

    <!-- Panel Lateral (Slide-over) para Nueva GPO -->
    <div v-if="showNewGpoPanel" class="fixed inset-0 bg-gray-900/30 backdrop-blur-sm z-40" @click="closePanel"></div>
    
    <!-- Panel derecho: w-[600px] -->
    <div :class="['fixed inset-y-0 right-0 z-50 w-[600px] bg-white shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col', showNewGpoPanel ? 'translate-x-0' : 'translate-x-full']">
      
      <!-- Cabecera Panel -->
      <div class="px-6 pt-4 border-b border-gray-200 bg-gray-50 shrink-0">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-base font-bold text-gray-900 flex items-center gap-2">
            <svg class="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            Nueva Directiva de Grupo (GPO)
          </h2>
          <button @click="closePanel" class="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-200 transition-colors">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          </button>
        </div>

        <!-- Wizard Tabs -->
        <div class="flex items-center text-[12px] font-bold uppercase tracking-wider">
          <div :class="['flex-1 text-center pb-2 border-b-2 transition-colors duration-300', currentStep >= 1 ? 'border-blue-600 text-blue-700' : 'border-gray-200 text-gray-400']">1. Definición</div>
          <div :class="['flex-1 text-center pb-2 border-b-2 transition-colors duration-300', currentStep >= 2 ? 'border-blue-600 text-blue-700' : 'border-gray-200 text-gray-400']">2. Alcance (OU)</div>
          <div :class="['flex-1 text-center pb-2 border-b-2 transition-colors duration-300', currentStep === 3 ? 'border-blue-600 text-blue-700' : 'border-gray-200 text-gray-400']">3. Confirmar</div>
        </div>
      </div>

      <!-- Contenido Panel (Wizard) -->
      <div class="flex-1 overflow-y-auto p-6">
        
        <!-- PASO 1: Definición -->
        <div v-show="currentStep === 1" class="space-y-6">
          <div>
            <label class="block text-[12px] font-bold text-gray-700 uppercase tracking-wider mb-1.5">Nombre de la Política <span class="text-red-500">*</span></label>
            <input type="text" v-model="newGpo.name" placeholder="Ej. Bloqueo USB, Wallpaper Corporativo" class="w-full border border-gray-300 rounded-sm px-3 py-2 text-[13px] text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
          </div>

          <div>
            <label class="block text-[12px] font-bold text-gray-700 uppercase tracking-wider mb-3">Tipo de Configuración <span class="text-red-500">*</span></label>
            <div class="grid grid-cols-2 gap-3">
              <label v-for="opt in templateOptions" :key="opt.value" :class="['border rounded-sm p-3 cursor-pointer transition-colors', newGpo.templateType === opt.value ? 'bg-blue-50 border-blue-500 ring-1 ring-blue-500' : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300']">
                <div class="flex items-center gap-2">
                  <input type="radio" :value="opt.value" v-model="newGpo.templateType" class="text-blue-600 focus:ring-blue-500" />
                  <span class="text-[13px] font-semibold text-gray-800">{{ opt.label }}</span>
                </div>
              </label>
            </div>
          </div>
          
          <!-- Configuración dinámica según el tipo de plantilla -->
          <div v-if="newGpo.templateType === 'wallpaper'" class="bg-slate-50 border border-slate-200 p-4 rounded-sm space-y-4">
            <h3 class="text-[13px] font-bold text-slate-800 border-b border-slate-200 pb-2">Configuración del Fondo de Pantalla</h3>
            <div>
              <label class="block text-[12px] font-bold text-slate-700 uppercase tracking-wider mb-1.5">Ruta de Red (UNC) de la Imagen <span class="text-red-500">*</span></label>
              <input type="text" v-model="newGpo.configParams" placeholder="Ej. \\servidor\compartido\fondos\wallpaper.jpg" class="w-full border border-slate-300 rounded-sm px-3 py-2 text-[12px] font-mono text-slate-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
              <p class="text-[11px] text-slate-500 mt-1">La ruta debe estar compartida y ser accesible (modo lectura) por todos los usuarios del dominio.</p>
            </div>
            
            <!-- Vista Previa Real desde Backend -->
            <div v-if="newGpo.configParams.includes('\\')" class="mt-4">
              <span class="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Vista Previa del Archivo</span>
              <div class="w-full h-40 bg-slate-200 border border-slate-300 rounded flex items-center justify-center relative overflow-hidden group">
                
                <template v-if="imageError">
                  <div class="flex flex-col items-center justify-center text-slate-400">
                    <svg class="w-8 h-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                    <span class="text-[11px] font-medium">Archivo no encontrado o acceso denegado</span>
                  </div>
                </template>
                
                <template v-else>
                  <img :src="`${API_BASE}/gpo/preview-image?path=${encodeURIComponent(newGpo.configParams)}`" @error="handleImageError" class="object-cover w-full h-full opacity-90 transition-opacity hover:opacity-100" />
                  <div class="absolute inset-0 bg-gradient-to-t from-slate-900/60 to-transparent flex items-end p-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                     <span class="bg-black/80 text-white text-[11px] px-2 py-1 rounded font-mono truncate max-w-full backdrop-blur-sm border border-white/20 shadow-sm">
                       {{ newGpo.configParams.split('\\').pop() || 'imagen.jpg' }}
                     </span>
                  </div>
                </template>

              </div>
            </div>
          </div>
          
          <div v-else>
            <label class="block text-[12px] font-bold text-gray-700 uppercase tracking-wider mb-1.5">Configuración Específica</label>
            <textarea v-model="newGpo.configParams" rows="3" placeholder="Parámetros opcionales (rutas, variables, etc)" class="w-full border border-gray-300 rounded-sm px-3 py-2 text-[12px] font-mono text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"></textarea>
          </div>
        </div>

        <!-- PASO 2: Alcance (Tree View) -->
        <div v-show="currentStep === 2" class="space-y-4 h-full flex flex-col">
          <div>
            <h3 class="text-[14px] font-bold text-gray-900 mb-1">Seleccione la Unidad Organizativa Destino</h3>
            <p class="text-[12px] text-gray-500 mb-4">Seleccione la OU exacta donde se aplicará esta directiva. Expandir la estructura para localizar OUs secundarias.</p>
          </div>
          
          <div class="flex-1 bg-white border border-gray-200 rounded-sm overflow-y-auto p-2">
            <div v-if="loadingOus" class="flex flex-col items-center justify-center h-40 text-blue-600">
              <span class="w-6 h-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-2"></span>
              <span class="text-[12px] font-bold">Cargando estructura...</span>
            </div>
            <div v-else class="text-sm">
              <template v-for="node in ouTree" :key="node.dn">
                <TreeNode :node="node" :level="0" :expandedNodes="expandedNodes" :selectedDn="newGpo.targetOu" @toggle="toggleNode" @select="selectOU" />
              </template>
            </div>
          </div>

          <div class="bg-blue-50 border border-blue-200 rounded-sm p-3 mt-4 shrink-0 flex flex-col gap-1">
            <span class="text-[11px] font-bold text-blue-800 uppercase tracking-widest">Ubicación Seleccionada</span>
            <span v-if="newGpo.targetOuName" class="text-[13px] font-medium text-gray-900">{{ newGpo.targetOuName }}</span>
            <span v-if="newGpo.targetOu" class="text-[11px] font-mono text-blue-600 break-all">{{ newGpo.targetOu }}</span>
            <span v-if="!newGpo.targetOu" class="text-[12px] text-gray-500 italic">Ninguna OU seleccionada</span>
          </div>
        </div>

        <!-- PASO 3: Confirmar -->
        <div v-show="currentStep === 3" class="space-y-6">
          <div class="bg-white border border-gray-200 rounded-sm p-4 space-y-4 shadow-sm">
            <h3 class="text-[14px] font-bold text-gray-900 border-b border-gray-100 pb-2 mb-4">Resumen de Directiva</h3>
            
            <div class="grid grid-cols-3 gap-2">
              <div class="text-[11px] font-bold text-gray-500 uppercase">Nombre</div>
              <div class="col-span-2 text-[13px] font-semibold text-gray-900">{{ newGpo.name }}</div>
            </div>
            
            <div class="grid grid-cols-3 gap-2">
              <div class="text-[11px] font-bold text-gray-500 uppercase">Tipo</div>
              <div class="col-span-2 text-[13px] font-semibold text-gray-900">{{ templateOptions.find(t => t.value === newGpo.templateType)?.label }}</div>
            </div>
            
            <div class="grid grid-cols-3 gap-2">
              <div class="text-[11px] font-bold text-gray-500 uppercase">Destino</div>
              <div class="col-span-2 text-[12px] font-mono text-blue-700">{{ newGpo.targetOu }}</div>
            </div>
          </div>

          <div>
            <h3 class="text-[12px] font-bold text-gray-700 uppercase tracking-wider mb-3">Estado Inicial</h3>
            <label class="flex items-center gap-3 cursor-pointer group">
              <button 
                type="button"
                role="switch"
                :aria-checked="newGpo.isActive"
                @click="newGpo.isActive = !newGpo.isActive"
                :class="[
                  newGpo.isActive ? 'bg-blue-600' : 'bg-gray-200',
                  'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
                ]"
              >
                <span 
                  aria-hidden="true" 
                  :class="[
                    newGpo.isActive ? 'translate-x-4' : 'translate-x-0',
                    'pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out'
                  ]"
                />
              </button>
              <span class="text-[13px] font-medium text-gray-900">Crear GPO como {{ newGpo.isActive ? 'Activa' : 'Inactiva' }}</span>
            </label>
            <p class="text-[11px] text-gray-500 mt-2">Si la crea inactiva, la configuración no se aplicará a los clientes hasta que sea habilitada manualmente.</p>
          </div>
        </div>

      </div>

      <!-- Footer Panel (Botones) -->
      <div class="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between shrink-0">
        <button 
          @click="currentStep === 1 ? closePanel() : prevStep()" 
          class="text-[13px] font-medium text-gray-600 hover:text-gray-900 px-4 py-2 border border-gray-300 rounded-sm hover:bg-gray-100 transition-colors bg-white shadow-sm"
        >
          {{ currentStep === 1 ? 'Cancelar' : 'Atrás' }}
        </button>
        
        <button 
          v-if="currentStep < 3"
          @click="nextStep" 
          :disabled="(currentStep === 1 && !newGpo.name) || (currentStep === 2 && !newGpo.targetOu)" 
          class="bg-slate-900 hover:bg-slate-800 text-white text-[13px] font-bold px-6 py-2 rounded-sm shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Siguiente
        </button>
        
        <button 
          v-if="currentStep === 3"
          @click="generateAndReview" 
          :disabled="isSubmitting"
          class="bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-bold px-6 py-2 rounded-sm shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="isSubmitting" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          {{ isSubmitting ? 'Creando GPO...' : 'Crear GPO' }}
        </button>
      </div>

    </div>

  </div>
</template>
