<script setup>
import { ref, onMounted, computed } from 'vue'
import BaseDrawer from '@/components/common/BaseDrawer.vue'
import BaseModal from '@/components/common/BaseModal.vue'
import ConfirmActionModal from '@/components/common/ConfirmActionModal.vue'

const API_BASE = '/api/v1'

const printers = ref([])
const drivers = ref([])
const loading = ref(true)
const error = ref('')

const showAddModal = ref(false)
const showEditModal = ref(false)
const showDetailsDrawer = ref(false)
const activeTab = ref('jobs')
const submitting = ref(false)

const toastMessage = ref('')
const toastType = ref('success')

const showToast = (msg, type = 'success') => {
  toastMessage.value = msg
  toastType.value = type
  setTimeout(() => {
    toastMessage.value = ''
  }, 4000)
}

const selectedPrinter = ref(null)

const printerJobs = ref([])
const loadingJobs = ref(false)

const printerHistory = ref([])
const loadingHistory = ref(false)

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
  new_driver: '',
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
    new_driver: printer.DriverName || '',
    shared: printer.Shared,
    share_name: printer.ShareName || ''
  }
  showDetailsDrawer.value = false // Cerrar el panel de detalles para evitar sobreposición
  if (drivers.value.length === 0) fetchDrivers()
  setTimeout(() => {
    showEditModal.value = true
  }, 150)
}

const submitAddPrinter = async () => {
  if (!newPrinter.value.name || !newPrinter.value.ip || !newPrinter.value.driver) {
    showToast("Nombre, IP y Driver son obligatorios.", "error")
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
    showToast(`Impresora agregada exitosamente.`)
    await fetchPrinters()
  } catch (err) {
    showToast(err.message, 'error')
  } finally {
    submitting.value = false
  }
}

const submitEditPrinter = async () => {
  if (!editPrinter.value.new_name || !editPrinter.value.new_ip) {
    showToast("Nombre e IP son obligatorios.", "error")
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
    showToast('Impresora actualizada exitosamente.')
    await fetchPrinters()
  } catch (err) {
    showToast(err.message, 'error')
  } finally {
    submitting.value = false
  }
}

// Removing unused selection logic

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
        showToast(`Cola de impresión de ${printer.Name} limpiada.`)
        if (activeTab.value === 'jobs') loadJobs()
      } catch (err) {
        showToast(err.message, 'error')
      }
    }
  )
}

const restartSpooler = async () => {
  openConfirmModal(
    'Reiniciar Spooler',
    '¿Estás seguro de reiniciar el servicio de Print Spooler en el servidor? Esto interrumpirá temporalmente todas las impresiones en curso.',
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
        showToast('Spooler reiniciado exitosamente.')
        await fetchPrinters()
      } catch (err) {
        showToast(err.message, 'error')
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
    showToast(err.message, 'error')
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
    showToast(`Página de prueba enviada a ${printer.Name}.`)
  } catch (err) {
    showToast(err.message, 'error')
  }
}

const pingPrinter = async (printer, event) => {
  if (event) event.stopPropagation()
  if (!printer) return
  
  const ip = printer.IPAddress || printer.PortName
  if (ip.startsWith('WSD-') || ip.startsWith('PORT')) {
    showToast('Los puertos WSD o Locales no responden a Ping directo.', 'error')
    return
  }

  showToast(`Haciendo ping a ${ip}...`)
  try {
    const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(printer.Name)}/ping?ip=${encodeURIComponent(ip)}`)
    const data = await res.json()
    if (data.success) {
      showToast(data.message, 'success')
    } else {
      showToast(data.message, 'error')
    }
  } catch (err) {
    showToast('Error de red haciendo ping', 'error')
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
        showDetailsDrawer.value = false
        selectedPrinter.value = null
        showToast('Impresora eliminada exitosamente.')
        await fetchPrinters()
      } catch (err) {
        showToast(err.message, 'error')
      }
    }
  )
}

const loadJobs = async () => {
  if (!selectedPrinter.value) return
  printerJobs.value = []
  loadingJobs.value = true
  try {
    const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(selectedPrinter.value.Name)}/jobs`)
    if (!res.ok) throw new Error('Error al cargar cola')
    printerJobs.value = await res.json()
  } catch (err) {
    console.error(err)
  } finally {
    loadingJobs.value = false
  }
}

const loadHistory = async () => {
  if (!selectedPrinter.value) return
  printerHistory.value = []
  loadingHistory.value = true
  try {
    const res = await fetch(`${API_BASE}/printers/${encodeURIComponent(selectedPrinter.value.Name)}/history`)
    if (!res.ok) throw new Error('Error al cargar historial')
    printerHistory.value = await res.json()
  } catch (err) {
    console.error(err)
  } finally {
    loadingHistory.value = false
  }
}

const openDetails = (printer) => {
  selectedPrinter.value = printer
  activeTab.value = 'jobs'
  showDetailsDrawer.value = true
  loadJobs()
  loadHistory()
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

        <!-- Actions removed, now in Drawer -->
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
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">Impresora</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">IP / Puerto</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">Driver</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors">Compartido</th>
              <th class="px-4 py-3 text-[11px] font-semibold text-gray-500 hover:text-gray-800 cursor-pointer transition-colors text-right">Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="printers.length === 0">
              <td colspan="5" class="px-2 py-16 text-center text-[13px] text-gray-500">
                No se encontraron impresoras en el servidor.
              </td>
            </tr>
            <tr v-for="p in printers" :key="p.Name" @click="openDetails(p)" class="border-b border-slate-100 transition-colors duration-150 cursor-pointer group hover:bg-slate-50">
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
              <td class="px-4 py-2.5 whitespace-nowrap">
                <div class="flex items-center gap-2">
                  <span class="text-[12px] font-mono text-gray-600">{{ p.IPAddress || p.PortName }}</span>
                  <button @click="pingPrinter(p, $event)" title="Probar conexión (Ping)" class="p-1 hover:bg-gray-200 rounded text-gray-400 hover:text-gray-700 transition-colors">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                  </button>
                </div>
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
              <td class="px-4 py-2.5 whitespace-nowrap text-right">
                <button class="text-blue-600 hover:text-blue-800 text-[12px] font-medium transition-colors">Detalles &rarr;</button>
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
            Al cambiar la IP, el sistema creará un nuevo puerto TCP/IP y lo reasignará de forma transparente.
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Nombre de Impresora</label>
            <input v-model="editPrinter.new_name" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Dirección IP (Puerto)</label>
            <input v-model="editPrinter.new_ip" type="text" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white font-mono">
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Controlador (Driver)</label>
            <select v-model="editPrinter.new_driver" class="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:text-white">
              <option disabled value="">Seleccione un driver instalado</option>
              <option v-for="drv in drivers" :key="drv" :value="drv">{{ drv }}</option>
            </select>
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

    <!-- Drawer Detalles Impresora -->
    <BaseDrawer :show="showDetailsDrawer" :title="selectedPrinter?.Name || 'Detalles'" width="w-[600px]" @close="showDetailsDrawer = false">
      <template #body>
        <div class="flex flex-col h-full space-y-4">
          
          <!-- Acciones Rápidas -->
          <div class="flex items-center justify-end gap-2 -mt-2">
            <button @click="openEditModal(selectedPrinter)" class="text-[12px] text-blue-600 font-medium hover:text-blue-800 px-2.5 py-1.5 rounded hover:bg-blue-50 transition-colors flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
              Editar Impresora
            </button>
            <button @click="deletePrinter(selectedPrinter)" class="text-[12px] text-red-600 font-medium hover:text-red-800 px-2.5 py-1.5 rounded hover:bg-red-50 transition-colors flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              Eliminar
            </button>
          </div>

          <!-- Info básica -->
          <div class="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <span class="block text-[11px] text-slate-500 uppercase tracking-wider font-semibold">IP / Puerto</span>
                <span class="text-[13px] text-slate-900 font-mono">{{ selectedPrinter?.IPAddress || selectedPrinter?.PortName }}</span>
              </div>
              <div>
                <span class="block text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Driver</span>
                <span class="text-[13px] text-slate-900">{{ selectedPrinter?.DriverName }}</span>
              </div>
              <div>
                <span class="block text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Uso Compartido</span>
                <span class="text-[13px] text-slate-900">{{ selectedPrinter?.Shared ? `Sí (${selectedPrinter.ShareName})` : 'No' }}</span>
              </div>
              <div>
                <span class="block text-[11px] text-slate-500 uppercase tracking-wider font-semibold">Estado de Red</span>
                <span class="text-[13px] text-green-600 font-medium">Online</span>
              </div>
            </div>
          </div>

          <!-- Tabs -->
          <div class="border-b border-slate-200">
            <nav class="-mb-px flex space-x-6">
              <button @click="activeTab = 'jobs'" :class="[activeTab === 'jobs' ? 'border-blue-500 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300', 'whitespace-nowrap pb-3 border-b-2 font-medium text-[13px] transition-colors']">
                Cola Actual
              </button>
              <button @click="activeTab = 'history'" :class="[activeTab === 'history' ? 'border-blue-500 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300', 'whitespace-nowrap pb-3 border-b-2 font-medium text-[13px] transition-colors']">
                Auditoría
              </button>
              <button @click="activeTab = 'actions'" :class="[activeTab === 'actions' ? 'border-blue-500 text-blue-600' : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300', 'whitespace-nowrap pb-3 border-b-2 font-medium text-[13px] transition-colors']">
                Administración
              </button>
            </nav>
          </div>

          <!-- Tab: Jobs -->
          <div v-if="activeTab === 'jobs'" class="flex-1 overflow-y-auto min-h-[250px] border border-slate-100 rounded-lg relative">
            <div class="bg-slate-50 border-b border-slate-100 px-3 py-2 flex justify-between items-center sticky top-0">
              <span class="text-[11px] font-semibold text-slate-500 uppercase">Documentos en cola</span>
              <button @click="loadJobs" class="text-[11px] font-semibold text-blue-600 hover:text-blue-800 transition-colors flex items-center gap-1 bg-blue-50 px-2 py-1 rounded">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                Actualizar
              </button>
            </div>
            
            <div v-if="loadingJobs" class="flex flex-col items-center justify-center py-10">
              <div class="w-6 h-6 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin mb-2"></div>
              <span class="text-xs text-slate-500">Cargando cola...</span>
            </div>
            <table v-else class="w-full text-left">
              <thead class="bg-white border-b border-slate-100">
                <tr>
                  <th class="px-3 py-2 text-[11px] font-semibold text-slate-500">Doc / Usuario</th>
                  <th class="px-3 py-2 text-[11px] font-semibold text-slate-500 text-right">Págs</th>
                  <th class="px-3 py-2 text-[11px] font-semibold text-slate-500 text-right">Estado</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="printerJobs.length === 0">
                  <td colspan="3" class="px-3 py-8 text-center text-[12px] text-slate-500">
                    No hay documentos en cola.
                  </td>
                </tr>
                <tr v-for="job in printerJobs" :key="job.JobId" class="border-b border-slate-50 hover:bg-slate-50">
                  <td class="px-3 py-2">
                    <div class="text-[12px] text-slate-800 font-medium truncate max-w-[200px]" :title="job.Document">{{ job.Document }}</div>
                    <div class="text-[11px] text-slate-500">{{ job.User }}</div>
                  </td>
                  <td class="px-3 py-2 text-[12px] text-slate-600 text-right">{{ job.Pages }}</td>
                  <td class="px-3 py-2 text-[12px] text-right">
                    <span class="px-1.5 py-0.5 rounded text-[10px] font-medium" :class="job.Status === 'En cola' ? 'bg-slate-100 text-slate-600' : 'bg-blue-50 text-blue-700'">
                      {{ job.Status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Tab: History -->
          <div v-if="activeTab === 'history'" class="flex-1 overflow-y-auto min-h-[250px] border border-slate-100 rounded-lg">
            <div v-if="loadingHistory" class="flex flex-col items-center justify-center py-10">
              <div class="w-6 h-6 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin mb-2"></div>
              <span class="text-xs text-slate-500">Consultando eventos...</span>
            </div>
            <table v-else class="w-full text-left">
              <thead class="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th class="px-3 py-2 text-[11px] font-semibold text-slate-500">Fecha/Hora</th>
                  <th class="px-3 py-2 text-[11px] font-semibold text-slate-500">Usuario</th>
                  <th class="px-3 py-2 text-[11px] font-semibold text-slate-500 text-right">Págs</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="printerHistory.length === 0">
                  <td colspan="3" class="px-3 py-8 text-center text-[12px] text-slate-500">
                    No hay historial registrado aún.
                  </td>
                </tr>
                <tr v-for="(job, i) in printerHistory" :key="i" class="border-b border-slate-50 hover:bg-slate-50">
                  <td class="px-3 py-2 text-[11px] text-slate-500">{{ job.Time }}</td>
                  <td class="px-3 py-2">
                    <div class="text-[12px] text-slate-800 font-medium">{{ job.User }}</div>
                    <div class="text-[11px] text-slate-500 truncate max-w-[150px]" :title="job.Document">{{ job.Document }}</div>
                  </td>
                  <td class="px-3 py-2 text-[12px] text-slate-600 text-right">{{ job.Pages }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Tab: Actions -->
          <div v-if="activeTab === 'actions'" class="flex-1 min-h-[250px]">
            <div class="space-y-2">
              <button @click="testPage(selectedPrinter)" class="w-full flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all group">
                <div class="flex items-center gap-3">
                  <div class="p-2 bg-blue-50 text-blue-600 rounded-md group-hover:bg-blue-100 transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  </div>
                  <div class="text-left">
                    <div class="text-[13px] font-semibold text-slate-800">Imprimir Página de Prueba</div>
                    <div class="text-[11px] text-slate-500">Envía un documento de prueba al spooler.</div>
                  </div>
                </div>
                <span class="text-slate-400 group-hover:text-blue-500">&rarr;</span>
              </button>

              <button @click="clearSpooler(selectedPrinter)" class="w-full flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-lg hover:border-amber-300 hover:shadow-sm transition-all group">
                <div class="flex items-center gap-3">
                  <div class="p-2 bg-amber-50 text-amber-600 rounded-md group-hover:bg-amber-100 transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </div>
                  <div class="text-left">
                    <div class="text-[13px] font-semibold text-slate-800">Limpiar Cola (Vaciar Spooler)</div>
                    <div class="text-[11px] text-slate-500">Cancela y borra todos los documentos atascados.</div>
                  </div>
                </div>
                <span class="text-slate-400 group-hover:text-amber-500">&rarr;</span>
              </button>

              <button v-if="selectedPrinter?.Shared" @click="generateMappingScript(selectedPrinter)" class="w-full flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-lg hover:border-slate-400 hover:shadow-sm transition-all group">
                <div class="flex items-center gap-3">
                  <div class="p-2 bg-slate-100 text-slate-600 rounded-md group-hover:bg-slate-200 transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
                  </div>
                  <div class="text-left">
                    <div class="text-[13px] font-semibold text-slate-800">Generar Script de Mapeo</div>
                    <div class="text-[11px] text-slate-500">Copia un código PowerShell para instalar a usuarios.</div>
                  </div>
                </div>
                <span class="text-slate-400">&rarr;</span>
              </button>
            </div>
          </div>
        </div>
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

    <!-- Elegant Toast Notification -->
    <div v-if="toastMessage" 
         class="fixed bottom-6 right-6 z-[60] animate-fade-in flex items-center gap-3 px-5 py-3.5 rounded-xl shadow-xl transition-all" 
         :class="toastType === 'error' ? 'bg-red-600 text-white shadow-red-900/20' : 'bg-slate-800 text-white shadow-slate-900/20'">
      <svg v-if="toastType === 'success'" class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
      <svg v-if="toastType === 'error'" class="w-5 h-5 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="text-[13px] font-medium tracking-wide">{{ toastMessage }}</span>
    </div>

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
