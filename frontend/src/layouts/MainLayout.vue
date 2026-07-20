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

const navigationItems = [
  {
    name: 'Inicio',
    path: '/',
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1',
  },
  {
    name: 'Equipos',
    path: '/devices',
    icon: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  },
  {
    name: 'Cuentas AD',
    path: '/cuentas',
    icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  },
  {
    name: 'Servidor Archivos',
    path: '/fileserver',
    icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
  },
  {
    name: 'Monitoreo',
    path: '/monitoring',
    icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z',
  },
  {
    name: 'Servidor Impresión',
    path: '/printers',
    icon: 'M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z',
  },
  {
    name: 'Gestor RDS',
    path: '/rds',
    icon: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2',
  },
  {
    name: 'Gestión Wi-Fi',
    path: '/wifi',
    icon: 'M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0',
  },
]

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

function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}

const sidebarWidth = computed(() => sidebarCollapsed.value ? 'w-14' : 'w-56')

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
    // Usamos el endpoint de perfil para ver si hay un usuario exacto
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

// Lógica de inactividad de 3 minutos (180,000 ms)
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
        'hidden md:flex flex-col bg-slate-800 border-r border-slate-700 transition-all duration-200 ease-in-out shrink-0 z-20 shadow-xl shadow-slate-900/10',
        sidebarWidth
      ]"
    >
      <!-- Brand -->
      <div class="flex items-center h-12 px-3 border-b border-slate-700/80">
        <div class="flex items-center gap-2 overflow-hidden w-full">
          <img src="/logo.png" alt="Logo" class="w-7 h-7 object-contain shrink-0" />
          <span v-show="!sidebarCollapsed" class="text-[13px] font-semibold text-white tracking-wide whitespace-nowrap">AdInfra F2</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 py-4 space-y-1 overflow-y-auto px-2">
        <router-link
          v-for="item in navigationItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'flex items-center gap-3 py-2 rounded-sm text-[13px] font-medium transition-all duration-150',
            sidebarCollapsed ? 'justify-center px-0' : 'px-3',
            isActive(item.path)
              ? 'bg-slate-800 text-white border-l-[3px] border-blue-500 shadow-sm'
              : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-[3px] border-transparent'
          ]"
        >
          <svg
            :class="['w-[18px] h-[18px] shrink-0', isActive(item.path) ? 'text-blue-400' : 'text-slate-500']"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          <span v-show="!sidebarCollapsed">{{ item.name }}</span>
        </router-link>
      </nav>

      <!-- Collapse -->
      <div class="border-t border-slate-700/80 p-2">
        <button
          @click="toggleSidebar"
          class="flex items-center w-full py-2 rounded-sm text-slate-500 hover:text-white hover:bg-slate-800/60 transition-colors duration-200"
          :class="sidebarCollapsed ? 'justify-center px-0' : 'gap-3 px-3'"
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
      </div>
    </aside>

    <!-- Sidebar móvil -->
    <aside
      :class="[
        'fixed inset-y-0 left-0 z-40 flex flex-col w-60 bg-slate-800 border-r border-slate-700 transition-transform duration-200 ease-in-out md:hidden shadow-2xl',
        mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <div class="flex items-center justify-between h-12 px-3 border-b border-slate-800">
        <div class="flex items-center gap-2">
          <img src="/logo.png" alt="Logo" class="w-7 h-7 object-contain shrink-0" />
          <span class="text-[13px] font-semibold text-white tracking-wide">AdInfra F2</span>
        </div>
        <button @click="closeMobileMenu" class="p-1 text-slate-400 hover:text-white">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <nav class="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        <router-link
          v-for="item in navigationItems"
          :key="item.path"
          :to="item.path"
          @click="closeMobileMenu"
          :class="[
            'flex items-center gap-3 px-3 py-2.5 rounded-sm text-[13px] font-medium transition-all duration-150',
            isActive(item.path)
              ? 'bg-slate-800 text-white shadow-sm border-l-[3px] border-blue-500'
              : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-[3px] border-transparent'
          ]"
        >
          <svg
            :class="['w-[18px] h-[18px] shrink-0', isActive(item.path) ? 'text-blue-400' : 'text-slate-500']"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
          </svg>
          <span>{{ item.name }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- Contenido principal -->
    <div class="flex flex-col flex-1 overflow-hidden">

      <!-- Header (NIVEL 2) -->
      <header class="flex items-center justify-between h-12 px-4 sm:px-6 bg-white border-b border-slate-200 shrink-0 z-10 relative">
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

          <!-- System Status -->
          <div class="flex items-center gap-2 px-2 py-1 rounded bg-slate-50 border border-slate-100">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span class="text-[11px] font-semibold text-slate-700 uppercase tracking-wide">System Online</span>
          </div>
        </div>

        <!-- Buscador global Prominente -->
        <div class="hidden sm:block flex-1 max-w-lg mx-8 relative">
          <div class="relative group">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 group-focus-within:text-blue-500 transition-colors pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              v-model="searchQuery"
              @focus="showSearchDropdown = true"
              @blur="closeSearchDropdown"
              @keydown.enter="handleGlobalSearch"
              placeholder="Buscar nombre o sAMAccountName y presiona Enter..."
              class="w-full pl-9 pr-12 py-1.5 text-[12px] bg-slate-50 border border-slate-200 rounded-md text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 focus:bg-white transition-all shadow-inner"
            />
            <div class="absolute right-2 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded border border-slate-200 bg-white text-[9px] font-mono text-slate-400 pointer-events-none">
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
              <p class="text-[11px] text-slate-500">Buscando cuenta...</p>
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

        <div class="flex items-center gap-4">
          <!-- Time -->
          <span class="text-[11px] text-slate-500 font-mono tabular-nums hidden sm:inline">{{ currentTime }}</span>
          <div class="w-px h-5 bg-slate-200 hidden sm:block"></div>
          
          <div class="flex items-center gap-3">
            <!-- Notifications (Mock) -->
            <button class="relative p-1.5 text-slate-400 hover:text-slate-600 transition-colors rounded hover:bg-slate-50">
              <span class="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full border border-white"></span>
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>

            <!-- Perfil de Usuario -->
            <div class="flex items-center gap-2 pl-2 border-l border-slate-200">
              <div class="hidden sm:flex flex-col justify-center text-right">
                <p class="text-[11.5px] font-semibold text-slate-800 leading-none">{{ displayName }}</p>
                <p class="text-[10px] font-medium text-slate-500 mt-0.5 uppercase tracking-wide">IT Admin</p>
              </div>
              <div class="w-8 h-8 rounded bg-slate-100 flex items-center justify-center text-slate-600 border border-slate-200 cursor-pointer hover:bg-slate-200 transition-colors" @click="handleLogout" title="Cerrar sesión">
                <span class="text-[11px] font-bold">{{ userInitials }}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <!-- Área de contenido (NIVEL 3) -->
      <main class="flex-1 overflow-y-auto p-4 sm:p-6 bg-gradient-to-br from-orange-50/40 via-slate-50 to-blue-50/40">
        <router-view />
      </main>
    </div>
  </div>
</template>
