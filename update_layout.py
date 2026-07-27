import re

file_path = "frontend/src/layouts/MainLayout.vue"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace navigationGroups array
old_nav_start = "const navigationGroups = ["
old_nav_end = "]\n\n// Mantener compatibilidad con mobile"

nav_groups_regex = re.compile(r"const navigationGroups = \[\n(.*?)\n\]\n\n// Mantener compatibilidad con mobile", re.DOTALL)

new_nav_groups = """const navigationGroups = ref([
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
          { name: 'Licencias Inactivas', path: '/licencias-inactivas' },
          { name: 'Cuarentena', path: '/cuarentena' }
        ]
      },
      {
        name: 'Servidor Archivos',
        path: '/fileserver',
        icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
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
      }
    ]
  }
])

// Mantener compatibilidad con mobile"""

content = nav_groups_regex.sub(new_nav_groups, content)


# 2. Modify `navigationItems` computation to handle nested items
old_nav_items = """const navigationItems = computed(() => {
  return navigationGroups.flatMap(group => group.items)
})"""

new_nav_items = """const navigationItems = computed(() => {
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
})"""
content = content.replace(old_nav_items, new_nav_items)


# 3. Modify isActive to handle parent matching
old_is_active = """function isActive(path) {
  return route.path === path || route.path.startsWith(path + '/')
}"""
new_is_active = """function isActive(item) {
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
}"""
content = content.replace(old_is_active, new_is_active)

# Ensure auto-expand on load
content = content.replace("resetInactivityTimer()", "resetInactivityTimer()\n  // Auto expand folder if active\n  navigationGroups.value.forEach(g => g.items.forEach(i => { if(i.subItems && isActive(i)) i.expanded = true }))")


# 4. Modify desktop sidebar template
old_desktop_ul = """<ul class="space-y-0.5">
            <li v-for="item in group.items" :key="item.path">
              <router-link
                :to="item.path"
                :class="[
                  'flex items-center gap-3 py-2.5 transition-all duration-150',
                  sidebarCollapsed ? 'justify-center px-0' : 'px-4',
                  isActive(item.path)
                    ? 'border-l-4 border-blue-500 bg-gradient-to-r from-blue-900/40 to-transparent text-white'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-4 border-transparent'
                ]"
              >
                <svg
                  :class="['w-5 h-5 shrink-0', isActive(item.path) ? 'text-white' : 'text-slate-500']"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                </svg>
                <span v-show="!sidebarCollapsed" class="text-[13px] font-medium truncate">{{ item.name }}</span>
              </router-link>
            </li>
          </ul>"""

new_desktop_ul = """<ul class="space-y-0.5">
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
          </ul>"""

content = content.replace(old_desktop_ul, new_desktop_ul)


# 5. Modify mobile sidebar template
old_mobile_ul = """<ul class="space-y-1">
            <li v-for="item in group.items" :key="item.path">
              <router-link
                :to="item.path"
                @click="closeMobileMenu"
                :class="[
                  'flex items-center gap-3 px-5 py-2.5 transition-all duration-150',
                  isActive(item.path)
                    ? 'bg-gradient-to-r from-blue-900/40 to-transparent text-white border-l-4 border-blue-500'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-white border-l-4 border-transparent'
                ]"
              >
                <svg
                  :class="['w-5 h-5 shrink-0', isActive(item.path) ? 'text-white' : 'text-slate-500']"
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
                </svg>
                <span class="text-[13px] font-medium">{{ item.name }}</span>
              </router-link>
            </li>
          </ul>"""

new_mobile_ul = """<ul class="space-y-1">
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
          </ul>"""

content = content.replace(old_mobile_ul, new_mobile_ul)


with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("File successfully modified.")
