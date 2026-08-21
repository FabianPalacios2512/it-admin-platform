<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['close', 'group-created'])
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const formData = ref({
  name: '',
  description: '',
  scope: 'Global',
  type: 'Security',
  path: '' // DistinguishedName of the selected OU
})

const loadingOus = ref(true)
const isSubmitting = ref(false)
const error = ref('')

const ous = ref([])
const ouTree = ref([])
const expandedNodes = ref(new Set())

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

const toggleNode = (dn) => {
  if (expandedNodes.value.has(dn)) {
    expandedNodes.value.delete(dn)
  } else {
    expandedNodes.value.add(dn)
  }
}

const selectOU = (node) => {
  formData.value.path = node.dn
}

onMounted(() => {
  fetchOUs()
})

const submitForm = async () => {
  if (!formData.value.name || !formData.value.path) {
    error.value = 'El nombre y la ubicación (OU) son obligatorios.'
    return
  }

  isSubmitting.value = true
  error.value = ''

  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/groups/ad`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData.value)
    })

    const data = await res.json()
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || 'Error al crear el grupo')
    }

    emit('group-created')
    emit('close')
  } catch (e) {
    error.value = e.message
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
    <!-- Background backdrop -->
    <div class="absolute inset-0 bg-slate-900/40 transition-opacity" @click="$emit('close')"></div>

    <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
      <!-- Drawer panel -->
      <div class="pointer-events-auto relative w-[50vw] flex flex-col bg-white shadow-2xl">
        
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-5 bg-slate-50 border-b border-slate-200 shrink-0">
          <div class="flex items-center gap-3">
            <div class="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            </div>
            <div>
              <h2 class="text-sm font-bold text-slate-800" id="slide-over-title">Asistente de aprovisionamiento de AD</h2>
              <p class="text-[11px] text-slate-500 font-medium">Creación de grupo de Active Directory</p>
            </div>
          </div>
          <button @click="$emit('close')" class="rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 p-1.5 transition-colors">
            <span class="sr-only">Cerrar panel</span>
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <!-- Scrollable Content -->
        <div class="flex-1 overflow-y-auto p-6 space-y-8">
          
          <div v-if="error" class="bg-red-50 border-l-4 border-red-500 p-4 rounded-md shadow-sm">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
              </div>
              <div class="ml-3">
                <p class="text-[13px] font-medium text-red-800">{{ error }}</p>
              </div>
            </div>
          </div>

          <!-- SECCIÓN: DATOS BÁSICOS -->
          <div>
            <h3 class="text-base font-semibold text-slate-900 mb-1">Identidad del Grupo</h3>
            <p class="text-[13px] text-slate-600 mb-4">Ingresa el nombre y descripción para este grupo.</p>
            
            <div class="grid grid-cols-1 gap-y-5">
              <div>
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Nombre del Grupo <span class="text-red-500">*</span></label>
                <input v-model="formData.name" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors" placeholder="Ej. GG_Ventas_Lectura">
              </div>
              <div>
                <label class="block text-[12px] font-medium text-slate-700 mb-1">Descripción</label>
                <input v-model="formData.description" type="text" class="w-full text-[13px] border-0 border-b border-slate-300 bg-transparent px-0 py-1.5 focus:ring-0 focus:border-blue-600 transition-colors" placeholder="Propósito o rol de los miembros de este grupo">
              </div>
            </div>
          </div>

          <hr class="border-slate-100">

          <!-- SECCIÓN: CONFIGURACIÓN COMPACTA -->
          <div>
            <h3 class="text-base font-semibold text-slate-900 mb-1">Configuración y Ámbito</h3>
            <p class="text-[13px] text-slate-600 mb-4">Selecciona cómo funcionará este grupo en Active Directory.</p>
            
            <div class="grid grid-cols-2 gap-6">
              <!-- Tipo (Pills) -->
              <div>
                <label class="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Tipo de Grupo</label>
                <div class="flex bg-slate-100 p-1 rounded-md">
                  <button type="button" @click="formData.type = 'Security'" class="flex-1 text-[12px] font-medium py-1.5 rounded-sm transition-colors text-center" :class="formData.type === 'Security' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'">Seguridad</button>
                  <button type="button" @click="formData.type = 'Distribution'" class="flex-1 text-[12px] font-medium py-1.5 rounded-sm transition-colors text-center" :class="formData.type === 'Distribution' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'">Distribución</button>
                </div>
                <p class="text-[11px] text-slate-400 mt-2">
                  {{ formData.type === 'Security' ? 'Para asignar permisos a recursos.' : 'Solo para listas de correo, sin seguridad.' }}
                </p>
              </div>

              <!-- Ámbito (Pills) -->
              <div>
                <label class="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-2">Ámbito</label>
                <div class="flex bg-slate-100 p-1 rounded-md">
                  <button type="button" @click="formData.scope = 'DomainLocal'" class="flex-1 text-[12px] font-medium py-1.5 rounded-sm transition-colors text-center" :class="formData.scope === 'DomainLocal' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'">Local</button>
                  <button type="button" @click="formData.scope = 'Global'" class="flex-1 text-[12px] font-medium py-1.5 rounded-sm transition-colors text-center" :class="formData.scope === 'Global' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'">Global</button>
                  <button type="button" @click="formData.scope = 'Universal'" class="flex-1 text-[12px] font-medium py-1.5 rounded-sm transition-colors text-center" :class="formData.scope === 'Universal' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'">Universal</button>
                </div>
              </div>
            </div>
          </div>

          <hr class="border-slate-100">

          <!-- SECCIÓN: UBICACIÓN -->
          <div>
            <h3 class="text-base font-semibold text-slate-900 mb-1">Destino del objeto</h3>
            <p class="text-[13px] text-slate-600 mb-4">Selecciona la Unidad Organizativa o Contenedor donde se creará el grupo.</p>
            
            <div v-if="loadingOus" class="flex flex-col items-center justify-center py-8">
              <div class="w-6 h-6 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-3"></div>
              <span class="text-[11px] font-medium text-slate-500">Cargando árbol de AD...</span>
            </div>
            
            <div v-else class="border border-slate-200 rounded-md bg-white shadow-sm overflow-hidden flex flex-col h-[300px]">
              <!-- Árbol Header -->
              <div class="bg-slate-50 border-b border-slate-200 px-4 py-2 flex items-center gap-2 shrink-0">
                <svg class="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>
                <span class="text-[11px] font-bold text-slate-600">Usuarios y equipos de Active Directory</span>
              </div>
              
              <!-- Árbol Body -->
              <div class="flex-1 overflow-auto p-2">
                <div class="text-[12px] font-medium text-slate-700">
                  <template v-for="node in ouTree" :key="node.dn">
                    <TreeNode :node="node" :level="0" :expandedNodes="expandedNodes" :selectedDn="formData.path" @toggle="toggleNode" @select="selectOU" />
                  </template>
                </div>
              </div>

              <!-- Seguridad Resumen -->
              <div class="bg-slate-50 border-t border-slate-200 p-3 shrink-0">
                <p class="text-[11px] font-semibold text-slate-700 mb-1">Ubicación seleccionada</p>
                <div class="text-[12px] font-mono text-slate-600 break-all leading-relaxed">
                  {{ formData.path || 'Ninguna seleccionada' }}
                </div>
              </div>
            </div>
          </div>
          
        </div>

        <!-- Footer Actions -->
        <div class="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3 shrink-0">
          <button @click="$emit('close')" class="text-[13px] font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-300 px-5 py-2.5 rounded-md shadow-sm transition-colors">Cancelar</button>
          
          <button @click="submitForm" :disabled="isSubmitting || !formData.name || !formData.path" class="bg-slate-800 text-white px-6 py-2.5 rounded-md text-[13px] font-bold hover:bg-slate-900 disabled:opacity-50 transition-colors flex items-center gap-2">
            <span v-if="isSubmitting" class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            {{ isSubmitting ? 'Creando Grupo...' : 'Crear Grupo' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
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
      
      let iconColor = 'text-amber-400'
      let iconPath = 'M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z' 
      
      if (node.type === 'Domain') {
        iconColor = 'text-slate-400'
        iconPath = 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10'
      } else if (node.type === 'Container') {
        iconColor = 'text-blue-500'
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
          h('div', { 
            class: ['w-5 h-5 flex items-center justify-center shrink-0 cursor-pointer rounded-sm hover:bg-slate-200/50', !hasChildren ? 'opacity-0' : ''],
            onClick: (e) => { e.stopPropagation(); if (hasChildren) emit('toggle', node.dn) }
          }, [
            h('svg', { class: ['w-3 h-3 text-slate-500 transition-transform', isExpanded ? 'rotate-90' : ''], viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5 }, [
              h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', d: 'M9 5l7 7-7 7' })
            ])
          ]),
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
