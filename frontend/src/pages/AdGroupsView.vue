<script setup>
import { ref, computed, onMounted } from 'vue'
import CreateGroupModal from '../components/CreateGroupModal.vue'
import GroupDetailsPanel from '../components/GroupDetailsPanel.vue'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const searchQuery = ref('')
const activeFilter = ref('todos')
const selectedGroups = ref(new Set())

// State
const groups = ref([])
const isLoading = ref(true)
const showCreateModal = ref(false)
const selectedGroupDetails = ref(null)

const fetchGroups = async () => {
  isLoading.value = true
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/groups/ad`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      groups.value = await res.json()
    }
  } catch (e) {
    console.error('Error fetching AD groups:', e)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchGroups()
})

const filteredGroups = computed(() => {
  let result = groups.value
  
  if (activeFilter.value === 'seguridad') {
    result = result.filter(g => g.type === 'Seguridad')
  } else if (activeFilter.value === 'distribucion') {
    result = result.filter(g => g.type === 'Distribución')
  }
  
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(g => g.name.toLowerCase().includes(q))
  }
  
  return result
})

const hasSelection = computed(() => selectedGroups.value.size > 0)
const selectAll = computed({
  get: () => filteredGroups.value.length > 0 && selectedGroups.value.size === filteredGroups.value.length,
  set: (val) => {
    if (val) {
      filteredGroups.value.forEach(g => selectedGroups.value.add(g.id))
    } else {
      selectedGroups.value.clear()
    }
  }
})

const toggleSelectAll = () => {
  selectAll.value = !selectAll.value
}

const toggleGroup = (id) => {
  if (selectedGroups.value.has(id)) {
    selectedGroups.value.delete(id)
  } else {
    selectedGroups.value.add(id)
  }
}

const setFilter = (filter) => {
  activeFilter.value = filter
  selectedGroups.value.clear()
}

const getInitials = (name) => {
  if (!name) return '?'
  const parts = name.split('_').filter(p => p.length > 0)
  if (parts.length > 1) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.substring(0, 2).toUpperCase()
}

const getAvatarColor = (name) => {
  const colors = [
    'bg-blue-500', 'bg-emerald-500', 'bg-violet-500', 
    'bg-amber-500', 'bg-rose-500', 'bg-cyan-500', 
    'bg-indigo-500', 'bg-fuchsia-500'
  ]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

const refreshData = () => {
  fetchGroups()
}

const exportData = () => {
  // Lógica para exportar
}

</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6">
    <!-- Breadcrumb & Header -->
    <div class="mb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-slate-400 hover:text-slate-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-slate-300">/</span>
        <span class="text-[11px] text-slate-600 font-medium">Grupos AD</span>
      </div>
      <h2 class="text-2xl font-semibold text-slate-900 tracking-tight">Directorio de Grupos</h2>
    </div>

    <!-- Command Bar (Global) -->
    <div class="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-slate-200 pb-3 gap-3">
      <div class="flex items-center gap-1 flex-wrap">
        <button class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"/></svg>
          Diagnóstico Express
        </button>
        <div class="w-px h-4 bg-gray-300 mx-1"></div>
        <button @click="showCreateModal = true" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
          Nuevo Grupo
        </button>
        <button @click="refreshData" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2">
          <svg class="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Actualizar
        </button>
        <button @click="exportData" :disabled="!hasSelection" class="text-sm font-medium text-gray-900 hover:bg-gray-100 px-2 py-1 rounded-md transition-colors flex items-center gap-2 disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer disabled:cursor-default">
          <svg class="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          Exportar
        </button>
      </div>
      <!-- Selección -->
      <div class="flex items-center justify-end gap-3">
        <transition name="modal">
          <span v-if="hasSelection" class="text-[12px] text-slate-500 font-semibold transition-opacity duration-300">
            {{ selectedGroups.size }} seleccionado{{ selectedGroups.size > 1 ? 's' : '' }}
          </span>
        </transition>
      </div>
    </div>

    <!-- Filters & Search -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
      <div class="flex items-center gap-1 overflow-x-auto hide-scrollbar">
        <button @click="setFilter('todos')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='todos' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Todos</button>
        <button @click="setFilter('seguridad')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='seguridad' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Seguridad</button>
        <button @click="setFilter('distribucion')" :class="['px-3 py-1 text-sm transition-colors whitespace-nowrap', activeFilter==='distribucion' ? 'text-gray-900 border-b-2 border-gray-900 font-semibold' : 'text-gray-500 hover:text-gray-700']">Distribución</button>
      </div>
      <div class="relative w-full md:w-[280px]">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
        <input v-model="searchQuery" type="text" placeholder="Buscar grupos..." class="w-full pl-9 pr-3 py-1.5 text-sm bg-white border border-gray-300 rounded text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors" />
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
              <th class="w-1/4 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Nombre del Grupo</th>
              <th class="w-1/6 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Ámbito</th>
              <th class="w-1/6 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Tipo</th>
              <th class="px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Descripción</th>
              <th class="w-1/6 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors">Ubicación (OU)</th>
              <th class="w-24 px-3 py-2 text-[11px] font-bold text-gray-700 uppercase tracking-wider cursor-pointer transition-colors text-right">Miembros</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="isLoading">
              <td colspan="7" class="px-2 py-16 text-center">
                <div class="inline-block w-6 h-6 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin mb-3"></div>
                <p class="text-[13px] text-slate-500">Cargando grupos...</p>
              </td>
            </tr>
            <tr v-else-if="filteredGroups.length === 0">
              <td colspan="7" class="px-2 py-16 text-center">
                <p class="text-[13px] text-slate-500">No se encontraron grupos que coincidan con la búsqueda o el filtro.</p>
              </td>
            </tr>
            <tr 
              v-else
              v-for="group in filteredGroups" 
              :key="group.id"
              @click="selectedGroupDetails = group"
              :class="['border-b border-gray-200 transition-colors duration-150 cursor-pointer group/row', selectedGroups.has(group.id) ? 'bg-blue-50' : 'hover:bg-gray-50']"
            >
              <td class="pl-2 py-1.5 w-10" @click.stop>
                <input type="checkbox" :checked="selectedGroups.has(group.id)" @change="toggleGroup(group.id)" class="w-3.5 h-3.5 border-gray-300 rounded focus:ring-blue-500 cursor-pointer text-blue-600 transition-colors">
              </td>
              <td class="px-3 py-1.5">
                <div class="flex items-center gap-2.5">
                  <div :class="['w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-white text-[9px] font-medium', getAvatarColor(group.name)]">
                    {{ getInitials(group.name) }}
                  </div>
                  <span class="text-[13px] font-medium text-gray-900 group-hover/row:text-blue-600 transition-colors">{{ group.name }}</span>
                </div>
              </td>
              <td class="px-3 py-1.5">
                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium"
                      :class="{
                        'bg-blue-50 text-blue-700 ring-1 ring-inset ring-blue-600/20': group.scope === 'Global',
                        'bg-purple-50 text-purple-700 ring-1 ring-inset ring-purple-600/20': group.scope === 'Universal',
                        'bg-amber-50 text-amber-700 ring-1 ring-inset ring-amber-600/20': group.scope === 'Local'
                      }">
                  {{ group.scope }}
                </span>
              </td>
              <td class="px-3 py-1.5">
                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium"
                      :class="{
                        'bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-600/20': group.type === 'Seguridad',
                        'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20': group.type === 'Distribución'
                      }">
                  {{ group.type }}
                </span>
              </td>
              <td class="px-3 py-1.5">
                <div class="text-[13px] text-gray-600 truncate max-w-[200px] xl:max-w-[300px]" :title="group.description">{{ group.description || '—' }}</div>
              </td>
              <td class="px-3 py-1.5">
                <div class="flex items-center gap-1.5 text-[12px] text-gray-500 truncate max-w-[150px] xl:max-w-[200px]" :title="group.dn">
                  <svg class="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span class="truncate">{{ group.path }}</span>
                </div>
              </td>
              <td class="px-3 py-1.5 text-right">
                <div class="text-[13px] font-mono text-slate-700 mr-2">{{ group.membersCount }}</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- Footer (Paginación) -->
      <div class="mt-4 flex items-center justify-between text-xs text-gray-500">
        <div>
          Mostrando {{ filteredGroups.length }} grupo(s)
        </div>
        <div class="flex items-center gap-1 text-gray-400">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/></svg>
          <span class="px-2 py-0.5 rounded bg-gray-100 text-gray-600 font-medium">1</span>
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateGroupModal 
      v-if="showCreateModal" 
      @close="showCreateModal = false" 
      @group-created="fetchGroups" 
    />

    <!-- Details Panel -->
    <GroupDetailsPanel
      v-if="selectedGroupDetails"
      :group="selectedGroupDetails"
      @close="selectedGroupDetails = null"
    />
  </div>
</template>

<style scoped>
.hide-scrollbar::-webkit-scrollbar {
  display: none;
}
.hide-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
