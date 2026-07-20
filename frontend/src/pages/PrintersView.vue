<script setup>
import { ref, onMounted, computed } from 'vue'
import BaseDrawer from '@/components/common/BaseDrawer.vue'
import ConfirmActionModal from '@/components/common/ConfirmActionModal.vue'

const API_BASE = '/api/v1'

const printers = ref([])
const drivers = ref([])
const loading = ref(true)
const error = ref('')

const showAddModal = ref(false)
const showEditModal = ref(false)
const submitting = ref(false)

const newPrinter = ref({
  name: '',
  ip: '',
  driver: '',
  shared: false,
  share_name: ''
})

const editPrinter = ref({
  old_name: '',
  new_name: '',
  new_ip: '',
  shared: false,
  share_name: ''
})

const fetchPrinters = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`${API_BASE}/printers/`)
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Error al cargar impresoras')
    }
    printers.value = await res.json()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const fetchDrivers = async () => {
  try {
    const res = await fetch(`${API_BASE}/printers/drivers`)
    if (res.ok) {
      drivers.value = await res.json()
    }
  } catch (err) {
    console.error('Error cargando drivers:', err)
  }
}

const openAddModal = () => {
  newPrinter.value = { name: '', ip: '', driver: '', shared: false, share_name: '' }
  showAddModal.value = true
  if (drivers.value.length === 0) fetchDrivers()
}

const openEditModal = (printer) => {
  editPrinter.value = {
    old_name: printer.Name,
    new_name: printer.Name,
    new_ip: printer.IPAddress || printer.PortName,
    shared: printer.Shared,
    share_name: printer.ShareName || ''
  }
  showEditModal.value = true
}

const submitAddPrinter = async () => {
  if (!newPrinter.value.name || !newPrinter.value.ip || !newPrinter.value.driver) {
    alert("Nombre, IP y Driver son obligatorios.")
    return
  }
  submitting.value = true
  try {
    const res = await fetch(`${API_BASE}/printers/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newPrinter.value)
    })
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Error al crear impresora')
    }
    showAddModal.value = false
    await fetchPrinters()
  } catch (err) {
    alert(err.message)
  } finally {
    submitting.value = false
  }
}

const submitEditPrinter = async () => {
  if (!editPrinter.value.new_name || !editPrinter.value.new_ip) {
    alert("Nombre e IP son obligatorios.")
    return
  }
  submitting.value = true
  try {
    const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(editPrinter.value.old_name)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editPrinter.value)
    })
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || 'Error al editar impresora')
    }
    showEditModal.value = false
    await fetchPrinters()
  } catch (err) {
    alert(err.message)
  } finally {
    submitting.value = false
  }
}

const selectedPrinters = ref(new Set())
const hasSelection = computed(() => selectedPrinters.value.size > 0)
const hasSingleSelection = computed(() => selectedPrinters.value.size === 1)

const singleSelectedPrinter = computed(() => {
  if (!hasSingleSelection.value) return null
  const pName = Array.from(selectedPrinters.value)[0]
  return printers.value.find(p => p.Name === pName)
})

const toggleSelection = (printerName) => {
  const newSet = new Set(selectedPrinters.value)
  if (newSet.has(printerName)) {
    newSet.delete(printerName)
  } else {
    newSet.add(printerName)
  }
  selectedPrinters.value = newSet
}

const toggleAll = (e) => {
  if (e.target.checked) {
    selectedPrinters.value = new Set(printers.value.map(p => p.Name))
  } else {
    selectedPrinters.value = new Set()
  }
}

const isAllSelected = computed(() => {
  return printers.value.length > 0 && selectedPrinters.value.size === printers.value.length
})

const confirmModal = ref({
  show: false,
  title: '',
  description: '',
  confirmText: '',
  action: null
})

const openConfirmModal = (title, description, confirmText, action) => {
  confirmModal.value = { show: true, title, description, confirmText, action }
}

const handleConfirm = async () => {
  if (confirmModal.value.action) {
    submitting.value = true
    try {
      await confirmModal.value.action()
    } finally {
      submitting.value = false
      confirmModal.value.show = false
    }
  }
}

const clearSpooler = async (printer) => {
  if (!printer) return
  openConfirmModal(
    'Vaciar cola de impresión',
    `¿Está seguro que desea eliminar todos los trabajos encolados para la impresora ${printer.Name}? Esta acción no se puede deshacer.`,
    'Sí, vaciar cola',
    async () => {
      try {
        const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(printer.Name)}/clear-spooler`, {
          method: 'POST'
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Error al limpiar cola')
        }
        alert(`Cola de impresión de ${printer.Name} limpiada exitosamente.`)
      } catch (err) {
        alert(err.message)
      }
    }
  )
}

const restartSpooler = async () => {
  openConfirmModal(
    'Reiniciar Spooler',
    '¿Estás seguro de reiniciar el servicio de Print Spooler en el servidor? Esto interrumpirÃ¡ temporalmente todas las impresiones en curso.',
    'Sí, reiniciar',
    async () => {
      try {
        const res = await fetch(`${API_BASE}/printers/restart-spooler`, {
          method: 'POST'
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Error al reiniciar Spooler')
        }
        alert('Spooler reiniciado exitosamente.')
        await fetchPrinters()
      } catch (err) {
        alert(err.message)
      }
    }
  )
}

const generateMappingScript = async (printer) => {
  if (!printer) return
  try {
    const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(printer.Name)}/mapping-script`)
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error generando script de mapeo')
    }
    const data = await res.json()
    prompt("Script de mapeo generado. Cópielo (Ctrl+C):", data.script)
  } catch (err) {
    alert(err.message)
  }
}

const testPage = async (printer) => {
  if (!printer) return
  try {
    const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(printer.Name)}/test-page`, {
      method: 'POST'
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Error enviando página de prueba')
    }
    alert(`PÃ¡gina de prueba enviada a ${printer.Name}.`)
  } catch (err) {
    alert(err.message)
  }
}

const deletePrinter = async (printer) => {
  if (!printer) return
  openConfirmModal(
    'Eliminar impresora',
    `¿Estás seguro de eliminar la impresora '${printer.Name}'?`,
    'Eliminar',
    async () => {
      try {
        const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(printer.Name)}`, {
          method: 'DELETE'
        })
        if (!res.ok) {
          const err = await res.json()
          throw new Error(err.detail || 'Error al eliminar impresora')
        }
        selectedPrinters.value = new Set()
        await fetchPrinters()
      } catch (err) {
        alert(err.message)
      }
    }
  )
}

onMounted(() => {
  fetchPrinters()
})
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-4 sm:py-6 font-sans flex flex-col h-full">
    
    <!-- Breadcrumb & Header -->
    <div class="mb-4">
      <div class="flex items-center gap-1.5 mb-1">
        <router-link to="/" class="text-[11px] text-gray-400 hover:text-gray-600 transition-colors">Panel de control</router-link>
        <span class="text-[11px] text-gray-300">/</span>
        <span class="text-[11px] text-gray-600 font-medium">Impresoras</span>
      </div>  
      <h2 class="text-2xl font-semibold text-gray-900 tracking-tight">Servidor de Impresión</h2>
    </div>

    <!-- Command Bar -->
    <div class="flex flex-col md:flex-row md:items-center justify-between mb-4 border-b border-gray-200 pb-3 gap-3">
      <div class="flex items-center gap-2 flex-wrap">
        <button @click="openAddModal" class="flex items-center gap-1.5 px-3 py-1.5 text-blue-600 hover:text-blue-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-blue-50 rounded">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg>
          Nueva impresora
        </button>
        <button @click="restartSpooler" class="flex items-center gap-1.5 px-3 py-1.5 text-gray-500 hover:text-gray-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-gray-100 rounded border-l border-gray-200 pl-4 ml-1">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Reiniciar Spooler
        </button>

        <!-- Contextual actions -->
        <template v-if="hasSelection">
          <div class="h-4 border-r border-gray-200 mx-1"></div>
          
          <button v-if="hasSingleSelection" @click="testPage(singleSelectedPrinter)" class="flex items-center gap-1.5 px-3 py-1.5 text-gray-500 hover:text-gray-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-gray-100 rounded">
            Pág. de prueba
          </button>
          <button v-if="hasSingleSelection" @click="clearSpooler(singleSelectedPrinter)" class="flex items-center gap-1.5 px-3 py-1.5 text-gray-500 hover:text-gray-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-gray-100 rounded">
            Limpiar cola
          </button>
          <button v-if="hasSingleSelection && singleSelectedPrinter?.Shared" @click="generateMappingScript(singleSelectedPrinter)" class="flex items-center gap-1.5 px-3 py-1.5 text-gray-500 hover:text-gray-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-gray-100 rounded">
            Script de mapeo
          </button>
          <button v-if="hasSingleSelection" @click="openEditModal(singleSelectedPrinter)" class="flex items-center gap-1.5 px-3 py-1.5 text-gray-500 hover:text-gray-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-gray-100 rounded">
            Editar
          </button>
          <button v-if="hasSingleSelection" @click="deletePrinter(singleSelectedPrinter)" class="flex items-center gap-1.5 px-3 py-1.5 text-red-500 hover:text-red-700 font-semibold text-[13px] transition-colors bg-transparent hover:bg-red-50 rounded">
            Eliminar
          </button>
        </template>
      </div>
      
      <div class="flex items-center gap-2">
        <button @click="fetchPrinters" title="Actualizar lista" class="p-1.5 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
        </button>
      </div>
    </div>

    <!-- Data Table (Borderless) -->
    <div class="flex flex-col">
      
      <!-- Estado de Carga -->
      <div v-if="loading" class="py-16 flex flex-col items-center justify-center">
        <div class="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mb-3"></div>
        <span class="text-sm text-gray-500 font-medium">Conectando al servidor...</span>
      </div>

      <!-- Error -->
      <div v-if="error && !loading" class="p-4 my-4 bg-red-50 border border-red-200 rounded-sm flex items-start gap-3">
        <svg class="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <div>
          <h3 class="text-red-800 text-[13px] font-medium">Error de conexión</h3>
          <p class="text-red-600 text-[12px] mt-0.5">{{ error }}</p>
        </div>
      </div>

      <!-- Tabla de Impresoras -->
      <div v-if="!loading && !error" class="overflow-x-auto">
        <table class="w-full text-left min-w-[800px]">
          <thead class="border-b border-gray-200">
            <tr>
              <th class="w-10 px-4 py-3 text-center">
                <input type="checkbox" class="rounded border-gray-300 text-blue-600 focus:ring-blue-500" :checked="isAllSelected" @change="toggleAll">
              </th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">Impresora</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">IP / Puerto</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">Driver</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">Compartido</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="printers.length === 0">
              <td colspan="5" class="px-2 py-16 text-center text-[13px] text-gray-500">
                No se encontraron impresoras en el servidor.
              </td>
            </tr>
            <tr v-for="p in printers" :key="p.Name" @click="toggleSelection(p.Name)" class="border-b border-slate-100 transition-colors duration-150 cursor-pointer group hover:bg-slate-50" :class="{ 'bg-blue-50/30': selectedPrinters.has(p.Name) }">
              <td class="w-10 px-4 py-3 text-center">
                <input type="checkbox" :checked="selectedPrinters.has(p.Name)" @change="toggleSelection(p.Name)" @click.stop class="rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer">
              </td>
              <td class="px-4 py-2.5 whitespace-nowrap">
                <div class="flex items-center gap-3">
                  <div class="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-slate-100 text-slate-500 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                    </svg>
                  </div>
                  <div>
                    <span class="text-[13px] font-medium text-slate-800 group-hover:text-blue-600 transition-colors">{{ p.Name }}</span>
                  </div>
                </div>
              </td>
              <td class="px-4 py-2.5 whitespace-nowrap text-[12px] font-mono text-gray-600">
                {{ p.IPAddress || p.PortName }}
              </td>
              <td class="px-4 py-2.5 whitespace-nowrap text-[12px] text-gray-600 truncate max-w-[200px]" :title="p.DriverName">
                {{ p.DriverName }}
              </td>
              <td class="px-4 py-2.5 whitespace-nowrap">
                <span v-if="p.Shared" class="text-[12px] font-medium text-gray-900" :title="p.ShareName">
                  En Red ({{ p.ShareName }})
                </span>
                <span v-else class="text-[12px] font-medium text-gray-500">
                  Local
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Agregar Impresora -->
    <BaseDrawer :show="showAddModal" title="Agregar Nueva Impresora" @close="showAddModal = false">
      <template #body>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nombre de Impresora</label>
            <input v-model="newPrinter.name" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white" placeholder="Ej. PRN-SISTEMAS-01">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Dirección IP</label>
            <input v-model="newPrinter.ip" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white font-mono" placeholder="Ej. 192.168.1.50">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Controlador (Driver)</label>
            <select v-model="newPrinter.driver" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white">
              <option disabled value="">Seleccione un driver instalado</option>
              <option v-for="d in drivers" :key="d" :value="d">{{ d }}</option>
            </select>
          </div>
          
          <div class="pt-2 border-t border-slate-100 dark:border-slate-700">
            <label class="flex items-center gap-3 cursor-pointer">
              <div class="relative">
                <input v-model="newPrinter.shared" type="checkbox" class="sr-only peer">
                <div class="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-blue-600"></div>
              </div>
              <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Compartir en red</span>
            </label>
          </div>
          <div v-if="newPrinter.shared" class="animate-fade-in">
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nombre de Recurso Compartido</label>
            <input v-model="newPrinter.share_name" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white" placeholder="Ej. PRN-SISTEMAS">
          </div>
        </div>
      </template>
      <template #footer>
        <button @click="showAddModal = false" class="px-4 py-2 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
          Cancelar
        </button>
        <button @click="submitAddPrinter" :disabled="submitting" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50 flex items-center gap-2">
          <span v-if="submitting" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          Crear Impresora
        </button>
      </template>
    </BaseDrawer>

    <!-- Modal Editar Impresora -->
    <BaseDrawer :show="showEditModal" title="Editar / Re-enrutar Impresora" @close="showEditModal = false">
      <template #body>
        <div class="space-y-4">
          <div class="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30 rounded-lg text-sm text-blue-800 dark:text-blue-300">
            Al cambiar la IP, el sistema crearÃ¡ un nuevo puerto TCP/IP y lo reasignarÃ¡ de forma transparente.
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nombre de Impresora</label>
            <input v-model="editPrinter.new_name" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Dirección IP (Puerto)</label>
            <input v-model="editPrinter.new_ip" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white font-mono">
          </div>
          
          <div class="pt-2 border-t border-slate-100 dark:border-slate-700">
            <label class="flex items-center gap-3 cursor-pointer">
              <div class="relative">
                <input v-model="editPrinter.shared" type="checkbox" class="sr-only peer">
                <div class="w-11 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-blue-600"></div>
              </div>
              <span class="text-sm font-medium text-slate-700 dark:text-slate-300">Compartir en red</span>
            </label>
          </div>
          <div v-if="editPrinter.shared" class="animate-fade-in">
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nombre de Recurso Compartido</label>
            <input v-model="editPrinter.share_name" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white">
          </div>
        </div>
      </template>
      <template #footer>
        <button @click="showEditModal = false" class="px-4 py-2 text-slate-600 dark:text-slate-300 font-medium hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
          Cancelar
        </button>
        <button @click="submitEditPrinter" :disabled="submitting" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50 flex items-center gap-2">
          <span v-if="submitting" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
          Guardar Cambios
        </button>
      </template>
    </BaseDrawer>

    <!-- Confirm Modal -->
    <ConfirmActionModal
      :show="confirmModal.show"
      :title="confirmModal.title"
      :description="confirmModal.description"
      :confirm-text="confirmModal.confirmText"
      :loading="submitting"
      @close="confirmModal.show = false"
      @confirm="handleConfirm"
    />

  </div>
</template>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
