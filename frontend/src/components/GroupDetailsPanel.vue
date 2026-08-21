<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  group: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const activeTab = ref('general')
const members = ref([])
const loadingMembers = ref(false)
const addingMember = ref(false)
const memberError = ref('')

// Typeahead state
const searchQuery = ref('')
const searchResults = ref([])
const isSearching = ref(false)
const showDropdown = ref(false)
const searchTimeout = ref(null)
const selectedMemberSAM = ref('')

const handleSearchInput = () => {
  selectedMemberSAM.value = ''
  showDropdown.value = true
  if (searchTimeout.value) clearTimeout(searchTimeout.value)
  
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    isSearching.value = false
    return
  }
  
  isSearching.value = true
  searchTimeout.value = setTimeout(async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/groups/ad/search?q=${encodeURIComponent(searchQuery.value.trim())}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        searchResults.value = await res.json()
      }
    } catch (e) {
      console.error(e)
    } finally {
      isSearching.value = false
    }
  }, 300)
}

const selectResult = (result) => {
  searchQuery.value = result.name || result.sAMAccountName
  selectedMemberSAM.value = result.sAMAccountName
  showDropdown.value = false
}

const closeDropdown = () => {
  setTimeout(() => showDropdown.value = false, 200)
}

const fetchMembers = async () => {
  if (!props.group?.name) return
  
  loadingMembers.value = true
  memberError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/groups/ad/${props.group.name}/members`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      members.value = await res.json()
    } else {
      throw new Error('Error al cargar miembros')
    }
  } catch (err) {
    memberError.value = err.message
  } finally {
    loadingMembers.value = false
  }
}

watch(() => props.group, () => {
  activeTab.value = 'general'
  if (props.group) {
    fetchMembers()
  }
}, { immediate: true })

const addMember = async () => {
  const memberToSave = selectedMemberSAM.value || searchQuery.value.trim()
  if (!memberToSave) return
  
  addingMember.value = true
  memberError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/groups/ad/${props.group.name}/members`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ member_name: memberToSave })
    })
    
    const data = await res.json()
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || 'Error al agregar miembro')
    }
    
    searchQuery.value = ''
    selectedMemberSAM.value = ''
    await fetchMembers() // Recargar lista
  } catch (err) {
    memberError.value = err.message
  } finally {
    addingMember.value = false
  }
}

const removeMember = async (memberName) => {
  if (!confirm(`¿Estás seguro de que deseas remover a ${memberName} de este grupo?`)) return
  
  memberError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${API_BASE}/groups/ad/${props.group.name}/members/${memberName}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    
    const data = await res.json()
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || 'Error al remover miembro')
    }
    
    await fetchMembers()
  } catch (err) {
    memberError.value = err.message
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
    <div class="absolute inset-0 bg-slate-900/40 transition-opacity" @click="$emit('close')"></div>

    <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-2xl w-full">
      <div class="pointer-events-auto relative w-full flex flex-col bg-white shadow-2xl">
        
        <!-- Header -->
        <div class="flex flex-col px-6 py-5 bg-slate-50 border-b border-slate-200 shrink-0">
          <div class="flex items-start justify-between mb-2">
            <div class="flex items-center gap-3">
              <div class="flex items-center justify-center w-10 h-10 rounded-lg bg-slate-100 text-slate-700 shadow-sm border border-slate-200">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>
              </div>
              <div>
                <h2 class="text-lg font-bold text-slate-800" id="slide-over-title">{{ group.name }}</h2>
                <div class="flex items-center gap-2 mt-1">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                    {{ group.scope || 'Global' }}
                  </span>
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                    {{ group.type || 'Seguridad' }}
                  </span>
                </div>
              </div>
            </div>
            <button @click="$emit('close')" class="rounded-md text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 p-1.5 transition-colors">
              <span class="sr-only">Cerrar panel</span>
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <!-- Navegación Tabs -->
        <div class="px-6 border-b border-slate-200 bg-white shrink-0 flex gap-6">
          <button 
            @click="activeTab = 'general'"
            class="pb-3 pt-4 text-[13px] font-medium transition-colors relative whitespace-nowrap" 
            :class="activeTab === 'general' ? 'text-slate-900' : 'text-slate-500 hover:text-slate-700'">
            General
            <div v-if="activeTab === 'general'" class="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600"></div>
          </button>
          <button 
            @click="activeTab = 'members'"
            class="pb-3 pt-4 text-[13px] font-medium transition-colors relative whitespace-nowrap" 
            :class="activeTab === 'members' ? 'text-slate-900' : 'text-slate-500 hover:text-slate-700'">
            Miembros
            <div v-if="activeTab === 'members'" class="absolute bottom-0 left-0 right-0 h-[2px] bg-blue-600"></div>
          </button>
        </div>

        <!-- Scrollable Content -->
        <div class="flex-1 overflow-y-auto p-6 bg-slate-50/50">
          
          <div v-if="memberError" class="mb-4 bg-red-50 border-l-4 border-red-500 p-4 rounded-md shadow-sm">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
              </div>
              <div class="ml-3">
                <p class="text-[13px] font-medium text-red-800">{{ memberError }}</p>
              </div>
            </div>
          </div>

          <!-- TAB: GENERAL -->
          <div v-if="activeTab === 'general'" class="space-y-6">
            <div class="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
              <h3 class="text-[14px] font-semibold text-slate-800 mb-4 border-b border-slate-100 pb-2">Propiedades Generales</h3>
              
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label class="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">Descripción</label>
                  <p class="text-[13px] text-slate-900 font-medium">{{ group.description || 'Sin descripción' }}</p>
                </div>
                
                <div class="md:col-span-2">
                  <label class="block text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1">Ruta Completa (DN)</label>
                  <p class="text-[12px] text-slate-600 font-mono bg-slate-50 p-2 rounded border border-slate-100 break-all">
                    {{ group.dn }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- TAB: MIEMBROS -->
          <div v-if="activeTab === 'members'" class="space-y-4">
            
            <div class="relative z-20">
              <div class="flex items-center gap-2 bg-white p-3 border border-slate-200 rounded-lg shadow-sm">
                <input 
                  v-model="searchQuery" 
                  @input="handleSearchInput"
                  @focus="handleSearchInput"
                  @blur="closeDropdown"
                  @keyup.enter="addMember"
                  type="text" 
                  placeholder="Buscar usuario o grupo (Ej: jperez)..." 
                  class="flex-1 border-0 bg-transparent px-2 py-1.5 text-[13px] focus:ring-0 outline-none"
                >
                <button 
                  @click="addMember" 
                  :disabled="(!searchQuery && !selectedMemberSAM) || addingMember"
                  class="px-4 py-2 bg-blue-600 text-white text-[12px] font-semibold rounded hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center gap-2 shrink-0"
                >
                  <span v-if="addingMember" class="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                  Añadir Miembro
                </button>
              </div>
              
              <!-- Dropdown de Typeahead -->
              <div v-if="showDropdown && (isSearching || searchResults.length > 0)" class="absolute left-0 right-0 top-full mt-2 bg-white rounded-md shadow-lg border border-slate-200 overflow-hidden z-50 max-h-60 overflow-y-auto">
                <div v-if="isSearching" class="p-4 text-center">
                  <div class="inline-block w-5 h-5 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin"></div>
                </div>
                <div v-else>
                  <div 
                    v-for="res in searchResults" 
                    :key="res.sAMAccountName"
                    @mousedown.prevent="selectResult(res)"
                    class="flex items-center justify-between px-4 py-2 hover:bg-slate-50 cursor-pointer border-b border-slate-100 last:border-0"
                  >
                    <div class="flex items-center gap-2">
                      <svg v-if="res.type === 'Group'" class="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                      <svg v-else class="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                      <span class="text-[13px] font-semibold text-slate-800">{{ res.name || res.sAMAccountName }}</span>
                    </div>
                    <span class="text-[11px] font-mono text-slate-500">{{ res.sAMAccountName }}</span>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden flex flex-col min-h-[300px]">
              
              <div v-if="loadingMembers" class="flex-1 flex flex-col items-center justify-center py-12">
                <div class="w-8 h-8 border-2 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-3"></div>
                <span class="text-[12px] font-medium text-slate-500">Cargando miembros...</span>
              </div>
              
              <div v-else-if="members.length === 0" class="flex-1 flex flex-col items-center justify-center py-12 text-slate-400">
                <svg class="w-12 h-12 mb-3 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                <p class="text-[13px]">Este grupo no tiene miembros actualmente.</p>
              </div>

              <div v-else class="overflow-auto max-h-[500px]">
                <table class="w-full text-left border-collapse">
                  <thead class="bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
                    <tr>
                      <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Nombre</th>
                      <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Usuario (sAM)</th>
                      <th class="px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-slate-100">
                    <tr v-for="member in members" :key="member.sAMAccountName" class="hover:bg-slate-50 transition-colors">
                      <td class="px-4 py-3">
                        <div class="flex items-center gap-3">
                          <div class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center" 
                               :class="member.type === 'Group' ? 'bg-slate-100 text-slate-600 border border-slate-200' : 'bg-slate-50 text-slate-500 border border-slate-200'">
                            <svg v-if="member.type === 'Group'" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                            <svg v-else class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                          </div>
                          <div>
                            <div class="text-[13px] font-semibold text-slate-900">{{ member.name }}</div>
                            <div class="text-[11px] text-slate-500">{{ member.type === 'Group' ? 'Grupo de Seguridad' : 'Cuenta de Usuario' }}</div>
                          </div>
                        </div>
                      </td>
                      <td class="px-4 py-3 text-[12px] text-slate-600 font-mono">{{ member.sAMAccountName }}</td>
                      <td class="px-4 py-3 text-right">
                        <button 
                          @click="removeMember(member.sAMAccountName)"
                          class="text-[12px] font-semibold text-red-600 hover:text-red-800 transition-colors p-1"
                        >
                          Remover
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>
          
        </div>
      </div>
    </div>
  </div>
</template>
