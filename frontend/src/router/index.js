import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import HomeView from '@/pages/HomeView.vue'
import CuentasView from '@/pages/CuentasView.vue'
import AccountRecoveryView from '@/pages/AccountRecoveryView.vue'
import LoginView from '@/pages/LoginView.vue'
import FileServerView from '@/pages/FileServerView.vue'
import EquiposView from '@/pages/EquiposView.vue'
import MonitoreoView from '@/pages/MonitoreoView.vue'
import PrintersView from '@/pages/PrintersView.vue'
import RdsView from '@/pages/RdsView.vue'
import WifiView from '@/pages/WifiView.vue'
import SettingsView from '@/pages/SettingsView.vue'
import SecurityView from '@/pages/SecurityView.vue'
import AuditoriaView from '@/pages/AuditoriaView.vue'
import TerminalView from '@/pages/TerminalView.vue'
import CuarentenaView from '@/pages/CuarentenaView.vue'
import LicenciasInactivasView from '@/pages/LicenciasInactivasView.vue'
import ZabbixMonitoringView from '@/pages/ZabbixMonitoringView.vue'
import GpoManagerView from '@/pages/GpoManagerView.vue'
import AdGroupsView from '@/pages/AdGroupsView.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Home',
        component: HomeView,
      },
      {
        path: 'delegation',
        name: 'DelegationHub',
        component: () => import('@/pages/DelegationHubView.vue')
      },
      {
        path: 'cuentas',
        name: 'Cuentas',
        component: CuentasView,
      },
      {
        path: 'cuentas/recuperacion',
        name: 'AccountRecovery',
        component: AccountRecoveryView,
      },
      {
        path: 'grupos',
        name: 'AdGroups',
        component: AdGroupsView,
      },
      {
        path: 'ous',
        name: 'AdOUs',
        component: () => import('@/pages/OusView.vue'),
      },
      {
        path: 'seguridad',
        name: 'Seguridad',
        component: SecurityView,
      },
      {
        path: 'gpo-manager',
        name: 'GpoManager',
        component: GpoManagerView,
      },
      {
        path: 'auditoria',
        name: 'Auditoria',
        component: AuditoriaView,
      },
      {
        path: 'terminal',
        name: 'Terminal',
        component: TerminalView,
      },
      {
        path: 'cuentas/usuario/:username',
        name: 'UserProfile',
        component: () => import('@/pages/UserProfileView.vue'),
      },
      {
        path: 'fileserver',
        name: 'FileServer',
        component: FileServerView,
      },
      {
        path: 'devices',
        name: 'Equipos',
        component: EquiposView,
      },
      {
        path: 'monitoring',
        name: 'Monitoreo',
        component: MonitoreoView,
      },
      {
        path: 'monitoring-zabbix',
        name: 'MonitoreoZabbix',
        component: ZabbixMonitoringView,
      },
      {
        path: 'fortigate-admin',
        name: 'FortiGateAdmin',
        component: () => import('@/pages/FortiGateAdminView.vue'),
      },
      {
        path: 'printers',
        name: 'Printers',
        component: PrintersView,
      },
      {
        path: 'rds',
        name: 'RDS',
        component: RdsView,
      },
      {
        path: 'wifi',
        name: 'Wifi',
        component: WifiView,
      },
      {
        path: 'cuarentena',
        name: 'Cuarentena',
        component: CuarentenaView,
      },
      {
        path: 'licencias-inactivas',
        name: 'LicenciasInactivas',
        component: LicenciasInactivasView,
      },
      {
        path: 'diagnostico',
        name: 'Diagnostico',
        component: () => import('@/pages/DiagnosticView.vue'),
      }
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const isAuthenticated = !!token

  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && isAuthenticated) {
    next({ name: 'MonitoreoZabbix' })
  } else {
    next()
  }
})

export default router
