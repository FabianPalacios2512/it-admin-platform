<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const sidebarCollapsed = ref(false)
const mobileMenuOpen = ref(false)

// Auto-colapsar el sidebar en la vista de perfil de usuario
watch(
  () => route.path,
  (newPath) => {
    if (newPath.startsWith('/cuentas/usuario/')) {
      sidebarCollapsed.value = true
    }
  },
  { immediate: true }
)

const navigationGroups = ref([
  {
    title: 'MONITORING',
    items: [
      {
        name: 'Inicio',
        path: '/',
        icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1',
      },
      {
        name: 'Monitoreo',
        path: '/monitoring',
        icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
      }
    ]
  },
  {
    title: 'MANAGEMENT',
    items: [
      {
        name: 'Usuarios',
        icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
        expanded: false,
        subItems: [
          { name: 'Cuentas AD', path: '/cuentas' },
          { name: 'Equipos', path: '/devices' },
          { name: 'Seguridad', path: '/seguridad' },
          { name: 'Auditoría IT', path: '/auditoria' },
          { name: 'Licencias Inactivas', path: '/licencias-inactivas' }
        ]
      },
      {
        name: 'Servidores',
        icon: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2',
        expanded: false,
        subItems: [
          { name: 'Servidor Archivos', path: '/fileserver' },
          { name: 'Servidor Impresión', path: '/printers' },
          { name: 'Gestor RDS', path: '/rds' },
          { name: 'Gestión Wi-Fi', path: '/wifi' }
        ]
      },
      {
        name: 'Exchange',
        icon: 'M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
        expanded: false,
        subItems: [
          { name: 'Cuarentena', path: '/cuarentena' }, { name: 'Hub de Delegación', path: '/delegation' }
        ]
      }
    ]
  }
])

// Mantener compatibilidad con mobile (si la lista es plana)
const navigationItems = computed(() => {
  const items = []
  for (const group of navigationGroups.value) {
    for (const item of group.items) {
      if (item.subItems) {
        items.push(...item.subItems)
      } else {
        items.push(item)
      }
    }
  }
  return items
})

const currentTime = ref('')
function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

function isActive(item) {
  if (typeof item === 'string') {
    return route.path === item || route.path.startsWith(item + '/')
  }
  if (item.path) {
    return route.path === item.path || route.path.startsWith(item.path + '/')
  }
  if (item.subItems) {
    return item.subItems.some(sub => route.path === sub.path || route.path.startsWith(sub.path + '/'))
  }
  return false
}

const sidebarWidth = computed(() => sidebarCollapsed.value ? 'w-16' : 'w-56')

const displayName = ref(localStorage.getItem('display_name') || 'Administrador')

const userInitials = computed(() => {
  const name = displayName.value
  if (!name) return 'AD'
  const parts = name.split(' ')
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
})

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('display_name')
  router.push('/login')
}

// Buscador Global
const searchQuery = ref('')
const showSearchDropdown = ref(false)
const quickActionUser = ref(null)
const isSearchingUser = ref(false)
const apiBase = '/api/v1'

const searchOptions = [
  { name: 'Inicio (Dashboard)', path: '/', type: 'Módulo' },
  { name: 'Gestión de Cuentas AD', path: '/cuentas', type: 'Módulo' },
  { name: 'Buscar y Editar Usuarios', path: '/cuentas', type: 'Acción' },
  { name: 'Crear Usuario Nuevo', path: '/cuentas', type: 'Acción' },
  { name: 'Desbloquear Cuenta', path: '/cuentas', type: 'Acción' },
  { name: 'Resetear Contraseña', path: '/cuentas', type: 'Acción' },
  { name: 'Servidor de Archivos', path: '/fileserver', type: 'Módulo' },
  { name: 'Permisos de Carpetas NTFS', path: '/fileserver', type: 'Acción' },
  { name: 'Equipos de Red', path: '/devices', type: 'Módulo' },
  { name: 'Monitoreo de Infraestructura', path: '/monitoring', type: 'Módulo' },
  { name: 'Servidor de Impresión', path: '/printers', type: 'Módulo' },
  { name: 'Gestionar Impresoras', path: '/printers', type: 'Acción' },
  { name: 'Gestión Wi-Fi', path: '/wifi', type: 'Módulo' },
  { name: 'Bloquear/Desbloquear Cliente Wi-Fi', path: '/wifi', type: 'Acción' },
  { name: 'Reiniciar Access Point', path: '/wifi', type: 'Acción' }
]

const filteredSearchOptions = computed(() => {
  if (!searchQuery.value.trim()) return []
  const query = searchQuery.value.toLowerCase()
  return searchOptions.filter(opt => opt.name.toLowerCase().includes(query))
})

const handleSearchSelect = (option) => {
  router.push(option.path)
  searchQuery.value = ''
  showSearchDropdown.value = false
  quickActionUser.value = null
}

const closeSearchDropdown = () => {
  setTimeout(() => { 
    showSearchDropdown.value = false 
    quickActionUser.value = null
  }, 200)
}

const handleGlobalSearch = async () => {
  if (!searchQuery.value.trim()) return
  isSearchingUser.value = true
  showSearchDropdown.value = true
  quickActionUser.value = null
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${apiBase}/accounts/profile/${encodeURIComponent(searchQuery.value.trim())}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (res.ok) {
      quickActionUser.value = await res.json()
    }
  } catch (e) {
    console.error('Error buscando usuario para Quick Action', e)
  } finally {
    isSearchingUser.value = false
  }
}

const qaStatus = ref('')
const doQuickAction = async (actionUrl, method='POST') => {
  if (!quickActionUser.value) return
  qaStatus.value = 'Procesando...'
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch(`${apiBase}${actionUrl}`, {
      method: method,
      headers: { 
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username: quickActionUser.value.username })
    })
    const data = await res.json()
    if (res.ok && data.success) {
      qaStatus.value = `Éxito: ${data.message || 'Hecho'}`
      if (data.temp_password) {
        qaStatus.value = `Clave: ${data.temp_password}`
      }
    } else {
      qaStatus.value = `Error: ${data.detail || data.error || 'Falló la acción'}`
    }
  } catch (e) {
    qaStatus.value = 'Error de red'
  }
  setTimeout(() => { qaStatus.value = '' }, 5000)
}

// Lógica de inactividad de 3 minutos
let inactivityTimer = null
const INACTIVITY_LIMIT_MS = 3 * 60 * 1000 

const resetInactivityTimer = () => {
  if (inactivityTimer) clearTimeout(inactivityTimer)
  inactivityTimer = setTimeout(() => {
    handleLogout()
  }, INACTIVITY_LIMIT_MS)
}

onMounted(() => {
  updateClock()
  setInterval(updateClock, 30000)
  
  window.addEventListener('mousemove', resetInactivityTimer)
  window.addEventListener('keydown', resetInactivityTimer)
  window.addEventListener('scroll', resetInactivityTimer)
  window.addEventListener('click', resetInactivityTimer)
  
  resetInactivityTimer()
  // Auto expand folder if active
  navigationGroups.value.forEach(g => g.items.forEach(i => { if(i.subItems && isActive(i)) i.expanded = true }))
})

onUnmounted(() => {
  window.removeEventListener('mousemove', resetInactivityTimer)
  window.removeEventListener('keydown', resetInactivityTimer)
  window.removeEventListener('scroll', resetInactivityTimer)
  window.removeEventListener('click', resetInactivityTimer)
  if (inactivityTimer) clearTimeout(inactivityTimer)
})
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-white">

    <!-- Overlay móvil -->
    <div
      v-if="mobileMenuOpen"
      @click="closeMobileMenu"
      class="fixed inset-0 bg-slate-900/50 z-30 md:hidden"
    ></div>

    <!-- Sidebar desktop (NIVEL 1) -->
    <aside
      :class="[
        'hidden md:flex flex-col bg-slate-800 border-r border-slate-700 transition-all duration-200 ease-in-out shrink-0 z-20 shadow-xl',
        sidebarWidth
      ]"
    >
      <!-- Brand -->
      <div class="flex items-center h-12 px-4 border-b border-slate-700/80">
        <div class="flex items-center gap-3 overflow-hidden w-full">
          <img src="/logo.png" alt="Logo" class="w-7 h-7 object-contain shrink-0" />
          <span v-show="!sidebarCollapsed" class="text-sm font-semibold text-white tracking-wide whitespace-nowrap">AdInfra F2</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-4 overflow-y-auto overflow-x-hidden">
        <template v-for="(group, gIdx) in navigationGroups" :key="gIdx">
          <div v-show="!sidebarCollapsed" class="px-4 mt-6 mb-2">
            <h3 class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{{ group.title }}</h3>
          </div>
          <div v-show="sidebarCollapsed && gIdx > 0" class="my-4 border-t border-slate-700/50 mx-4"></div>
          
          <ul class="space-y-0.5">
            <li v-for="item in group.items" :key="item.name">
              <template v-if="!item.subItems">
                <router-link
                  :to="item.path"
                  :class="[
                    'flex items-center gap-3 py-2.5 transition-all duration-150 cursor-pointer',
                    sidebarCollapsed ? 'justify-center px-0' : 'px-4',
                    isActive(item)
                      ? 'border-l-4 border-blue-500 bg-gradient-to-r from-blue-900/40 to-transparent text-white'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-4 border-transparent'
                  ]"
                >
                  <svg
                    :class="['w-5 h-5 shrink-0', isActive(item) ? 'text-white' : 'text-slate-500']"
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                  </svg>
                  <span v-show="!sidebarCollapsed" class="text-[13px] font-medium truncate">{{ item.name }}</span>
                </router-link>
              </template>
              
              <template v-else>
                <div
                  @click="item.expanded = !item.expanded; if(sidebarCollapsed) sidebarCollapsed = false"
                  :class="[
                    'flex items-center justify-between py-2.5 transition-all duration-150 cursor-pointer group',
                    sidebarCollapsed ? 'justify-center px-0' : 'px-4',
                    isActive(item)
                      ? 'border-l-4 border-transparent text-white bg-slate-800/40'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-4 border-transparent'
                  ]"
                >
                  <div class="flex items-center gap-3">
                    <svg
                      :class="['w-5 h-5 shrink-0', isActive(item) ? 'text-white' : 'text-slate-500 group-hover:text-white']"
                      fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                    </svg>
                    <span v-show="!sidebarCollapsed" class="text-[13px] font-medium truncate">{{ item.name }}</span>
                  </div>
                  <svg v-show="!sidebarCollapsed" :class="['w-4 h-4 transition-transform duration-200', item.expanded ? 'rotate-180' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                
                <ul v-show="item.expanded && !sidebarCollapsed" class="mt-1 space-y-0.5 relative before:content-[''] before:absolute before:left-[23px] before:top-2 before:bottom-2 before:w-px before:bg-slate-700">
                  <li v-for="subItem in item.subItems" :key="subItem.path">
                    <router-link
                      :to="subItem.path"
                      :class="[
                        'flex items-center py-2 pl-[42px] pr-4 transition-all duration-150 relative text-[12.5px]',
                        isActive(subItem)
                          ? 'text-blue-400 font-medium'
                          : 'text-slate-400 hover:text-slate-200'
                      ]"
                    >
                      <span v-if="isActive(subItem)" class="absolute left-[21.5px] w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                      <span v-else class="absolute left-[21.5px] w-1.5 h-1.5 rounded-full bg-slate-600 transition-colors"></span>
                      {{ subItem.name }}
                    </router-link>
                  </li>
                </ul>
              </template>
            </li>
          </ul>
        </template>
      </nav>

      <!-- Collapse / Footer -->
      <div class="border-t border-slate-700/80 p-3">
        <div class="flex items-center justify-between">
          <button
            @click="toggleSidebar"
            class="flex items-center py-2 text-slate-500 hover:text-white transition-colors duration-200"
            :class="sidebarCollapsed ? 'justify-center w-full' : 'gap-3 px-1'"
          >
            <svg
              v-if="!sidebarCollapsed"
              class="w-[18px] h-[18px] shrink-0"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            <svg
              v-else
              class="w-[18px] h-[18px] shrink-0"
              fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            <span v-show="!sidebarCollapsed" class="text-[13px] font-medium">Contraer menú</span>
          </button>
          
          <span v-show="!sidebarCollapsed" class="text-[10px] text-slate-600 font-mono">v2.4.1 - PROD</span>
        </div>
      </div>
    </aside>

    <!-- Sidebar móvil -->
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-40 flex flex-col w-56 bg-slate-800 border-r border-slate-700 transition-transform duration-200 ease-in-out md:hidden shadow-2xl',
        mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <div class="flex items-center justify-between h-12 px-4 border-b border-slate-800">
        <div class="flex items-center gap-3">
          <img src="/logo.png" alt="Logo" class="w-7 h-7 object-contain shrink-0" />
          <span class="text-sm font-semibold text-white tracking-wide">AdInfra F2</span>
        </div>
        <button @click="closeMobileMenu" class="p-1 text-slate-400 hover:text-white">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <nav class="flex-1 overflow-y-auto py-2">
        <template v-for="(group, gIdx) in navigationGroups" :key="gIdx">
          <div class="px-5 mt-5 mb-2">
            <h3 class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{{ group.title }}</h3>
          </div>
          <ul class="space-y-1">
            <li v-for="item in group.items" :key="item.name">
              <template v-if="!item.subItems">
                <router-link
                  :to="item.path"
                  @click="closeMobileMenu"
                  :class="[
                    'flex items-center gap-3 px-5 py-2.5 transition-all duration-150',
                    isActive(item)
                      ? 'bg-gradient-to-r from-blue-900/40 to-transparent text-white border-l-4 border-blue-500'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-4 border-transparent'
                  ]"
                >
                  <svg
                    :class="['w-5 h-5 shrink-0', isActive(item) ? 'text-white' : 'text-slate-500']"
                    fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                  </svg>
                  <span class="text-[13px] font-medium">{{ item.name }}</span>
                </router-link>
              </template>
              <template v-else>
                <div
                  @click="item.expanded = !item.expanded"
                  :class="[
                    'flex items-center justify-between px-5 py-2.5 transition-all duration-150 cursor-pointer group',
                    isActive(item)
                      ? 'border-l-4 border-transparent text-white bg-slate-800/40'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-4 border-transparent'
                  ]"
                >
                  <div class="flex items-center gap-3">
                    <svg
                      :class="['w-5 h-5 shrink-0', isActive(item) ? 'text-white' : 'text-slate-500']"
                      fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                    </svg>
                    <span class="text-[13px] font-medium truncate">{{ item.name }}</span>
                  </div>
                  <svg :class="['w-4 h-4 transition-transform duration-200', item.expanded ? 'rotate-180' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                
                <ul v-show="item.expanded" class="mt-1 space-y-0.5 relative before:content-[''] before:absolute before:left-[27px] before:top-2 before:bottom-2 before:w-px before:bg-slate-700">
                  <li v-for="subItem in item.subItems" :key="subItem.path">
                    <router-link
                      :to="subItem.path"
                      @click="closeMobileMenu"
                      :class="[
                        'flex items-center py-2 pl-[46px] pr-5 transition-all duration-150 relative text-[12.5px]',
                        isActive(subItem)
                          ? 'text-blue-400 font-medium'
                          : 'text-slate-400 hover:text-slate-200'
                      ]"
                    >
                      <span v-if="isActive(subItem)" class="absolute left-[25.5px] w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                      <span v-else class="absolute left-[25.5px] w-1.5 h-1.5 rounded-full bg-slate-600 transition-colors"></span>
                      {{ subItem.name }}
                    </router-link>
                  </li>
                </ul>
              </template>
            </li>
          </ul>
        </template>
      </nav>
    </aside>

    <!-- Contenido principal -->
    <div class="flex flex-col flex-1 overflow-hidden">

      <!-- Header (NIVEL 2) -->
      <header class="flex items-center justify-between h-12 px-4 sm:px-6 bg-white border-b border-gray-200 shadow-sm shrink-0 z-10 relative">
        <div class="flex items-center gap-4">
          <!-- Hamburguesa móvil -->
          <button
            @click="toggleMobileMenu"
            class="p-1 text-slate-500 hover:text-slate-700 md:hidden"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        <!-- Buscador Estilo CLI (Command Palette) -->
        <div class="hidden sm:block flex-1 max-w-lg mx-8 relative">
          <div class="relative group flex items-center">
            <span class="absolute left-3 text-slate-500 font-mono text-sm pointer-events-none">></span>
            <input
              type="text"
              v-model="searchQuery"
              @focus="showSearchDropdown = true"
              @blur="closeSearchDropdown"
              @keydown.enter="handleGlobalSearch"
              placeholder="Buscar nombre o sAMAccountName y presiona Enter..."
              class="w-full pl-7 pr-14 py-1.5 font-mono text-sm bg-white shadow-sm border border-gray-300 rounded text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
            />
            <div class="absolute right-2 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded border border-gray-300 bg-white text-[10px] font-mono text-gray-500 pointer-events-none shadow-sm">
              Ctrl+K
            </div>
          </div>
          
          <!-- Dropdown de resultados -->
          <div 
            v-if="showSearchDropdown && searchQuery.trim()" 
            class="absolute top-full left-0 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-xl overflow-hidden z-50 divide-y divide-slate-100"
            @mousedown.stop
          >
            <!-- Quick Action Card -->
            <div v-if="isSearchingUser" class="p-4 text-center">
              <div class="inline-block w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div>
              <p class="text-[11px] text-slate-500 font-mono">Buscando cuenta...</p>
            </div>
            <div v-else-if="quickActionUser" class="p-4 bg-slate-50/50">
              <div class="flex justify-between items-start mb-3">
                <div>
                  <h4 class="text-[13px] font-bold text-slate-800">{{ quickActionUser.displayName }}</h4>
                  <p class="text-[11px] text-slate-500 font-mono mt-0.5">{{ quickActionUser.userPrincipalName || quickActionUser.username }}</p>
                  <p class="text-[11px] text-slate-500 mt-0.5">{{ quickActionUser.title || 'Sin cargo' }}</p>
                </div>
                <span :class="['px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider', quickActionUser.status === 'active' ? 'bg-emerald-100 text-emerald-700' : (quickActionUser.status === 'locked' ? 'bg-red-100 text-red-700' : 'bg-slate-200 text-slate-600')]">
                  {{ quickActionUser.status }}
                </span>
              </div>
              <div class="grid grid-cols-3 gap-2 mt-4">
                <button @click="doQuickAction('/accounts/quick-reset-password')" class="px-2 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-[11px] font-semibold rounded shadow-sm transition-colors">
                  Resetear Clave
                </button>
                <button @click="doQuickAction('/accounts/unlock')" class="px-2 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-[11px] font-semibold rounded shadow-sm transition-colors">
                  Desbloquear
                </button>
                <button @click="doQuickAction(`/graph/users/${quickActionUser.username}/revoke-sessions`)" class="px-2 py-1.5 bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 text-[11px] font-semibold rounded shadow-sm transition-colors">
                  Revocar Sesiones
                </button>
              </div>
              <div v-if="qaStatus" class="mt-3 p-2 bg-blue-50 text-blue-800 text-[11px] font-medium rounded border border-blue-100">
                {{ qaStatus }}
              </div>
            </div>
            
            <div class="p-1.5 bg-slate-100 text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
              Resultados de Sistema
            </div>
            <ul v-if="filteredSearchOptions.length > 0" class="max-h-40 overflow-y-auto">
              <li 
                v-for="(option, index) in filteredSearchOptions" 
                :key="index"
                @mousedown.prevent="handleSearchSelect(option)"
                class="px-3 py-2 hover:bg-blue-50 cursor-pointer flex items-center justify-between group"
              >
                <span class="text-[11.5px] font-medium text-slate-700 group-hover:text-blue-700 transition-colors">{{ option.name }}</span>
                <span class="text-[9px] uppercase tracking-wider font-semibold text-slate-400 group-hover:text-blue-500">{{ option.type }}</span>
              </li>
            </ul>
            <div v-else-if="!quickActionUser && !isSearchingUser" class="px-3 py-4 text-center">
              <p class="text-[11px] text-slate-500">Presiona Enter para buscar usuario exacto o intenta otra palabra.</p>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          
          <!-- Environment Indicator -->
          <div class="hidden md:flex items-center gap-1.5">
            <span class="text-[10px] text-gray-500 font-mono uppercase tracking-wider">Connected to: DC-01</span>
            <span class="animate-pulse bg-green-500 rounded-full w-2 h-2"></span>
          </div>

          <!-- Vertical separator -->
          <div class="w-px h-5 bg-gray-200 hidden sm:block mx-1"></div>

          <!-- Terminal PTY -->
          <button @click="router.push('/terminal')" class="relative p-1 text-gray-400 hover:text-blue-600 transition-colors rounded hover:bg-gray-50" title="Consola PowerShell">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>

          <!-- Notifications -->
          <button class="relative p-1 text-gray-400 hover:text-gray-600 transition-colors rounded hover:bg-gray-50">
            <span class="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-red-500 rounded-full"></span>
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </button>

          <!-- Vertical separator -->
          <div class="w-px h-5 bg-gray-200 hidden sm:block mx-1"></div>

          <!-- Perfil de Usuario -->
          <div class="flex items-center gap-2">
            <div class="hidden sm:flex flex-col justify-center text-right">
              <p class="text-[11px] font-semibold text-gray-800 leading-none">{{ displayName }}</p>
              <p class="text-[9px] font-medium text-gray-400 mt-0.5 uppercase tracking-widest">IT Admin</p>
            </div>
            <div class="w-7 h-7 rounded bg-gray-100 flex items-center justify-center text-gray-600 border border-gray-200 cursor-pointer hover:bg-gray-200 transition-colors" @click="handleLogout" title="Cerrar sesión">
              <span class="text-[10px] font-bold">{{ userInitials }}</span>
            </div>
          </div>
          
        </div>
      </header>

      <!-- Área de contenido (NIVEL 3) -->
      <main class="flex-1 overflow-y-auto p-4 sm:p-6 bg-gray-50/50">
        <router-view />
      </main>
    </div>
  </div>
</template>
