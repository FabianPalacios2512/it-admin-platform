import re

file_path = "frontend/src/layouts/MainLayout.vue"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

old_nav_groups = """const navigationGroups = ref([
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
])"""

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
          { name: 'Cuarentena', path: '/cuarentena' }
        ]
      }
    ]
  }
])"""

content = content.replace(old_nav_groups, new_nav_groups)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("File successfully modified.")
