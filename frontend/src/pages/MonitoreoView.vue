<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import Sparkline from '@/components/common/Sparkline.vue'
import VueApexCharts from 'vue3-apexcharts'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'
const token = localStorage.getItem('access_token')

async function authFetch(url, opts = {}) {
  return fetch(url, { ...opts, headers: { 'Authorization': `Bearer ${token}`, ...(opts.headers || {}) } })
}

const servers = ref([])
const loading = ref(false)
const error = ref('')
const lastUpdate = ref('')
let pollInterval = null

// ── PBX TELEFONÍA STATE & FETCH ──────────────────────────────────────────────
const pbxData = ref({
  llamadasActivas: 0,
  robotIvr: 0,
  rutaOpcion1: 0,
  rutaOpcion2: 0,
  troncal101: 0,
  loading: false
})

async function fetchPbxStats() {
  pbxData.value.loading = true
  try {
    // Simulación de llamada Zabbix API 'item.get' para el host Issabel
    // zabbix_api.item.get(host="Issabel-PBX", search={"key_": "pbx."})
    // const res = await authFetch(`${API_BASE}/monitoring/pbx`)
    
    // Datos simulados basados en las llaves configuradas
    pbxData.value = {
      llamadasActivas: 12,
      robotIvr: 1, // pbx.ivr_test
      rutaOpcion1: 1, // pbx.ivr_option[1]
      rutaOpcion2: 1, // pbx.ivr_option[2]
      troncal101: 1, // pbx.pjsip_status[101]
      loading: false
    }
  } catch (e) {
    console.error("Error obteniendo métricas de PBX", e)
    pbxData.value.loading = false
  }
}

// ── PROCESOS (Modal & Popover) ──────────────────────────────────────────────
const processesCache = ref({})           // Caché de la última petición
const processHistoryCache = ref({})      // Caché temporal para dibujar líneas de tiempo
const selectedServer = ref(null)

// Mock Data para el Modal GCP-style
const mockCpuSeries = ref([])
const mockRamSeries = ref([])

// Popover flotante
const popoverData = ref({
  show: false,
  x: 0,
  y: 0,
  srv: null,
  type: 'cpu'
})

function openModal(srv) {
  if (!srv || srv.stats.status !== 'online') return
  selectedServer.value = srv
  fetchProcesses(srv)
}

function closeModal() {
  selectedServer.value = null
}

// (Mock process function removed)

const selectedCpuSeries = computed(() => {
  if (!selectedServer.value) return [{ name: 'CPU', data: [] }]
  return [{ name: 'CPU', data: selectedServer.value.history?.cpu || [] }]
})

const selectedRamSeries = computed(() => {
  if (!selectedServer.value) return [{ name: 'RAM', data: [] }]
  return [{ name: 'RAM', data: selectedServer.value.history?.ram || [] }]
})

// Fetch real para el Popover rápido y el Modal
async function fetchProcesses(srv, force = false) {
  if (!srv || srv.stats.status !== 'online') return
  
  const cached = processesCache.value[srv.id]
  if (!force && cached && cached.data && !cached.loading) return

  // Si estamos haciendo polling (force=true), conservamos la data anterior para evitar parpadeos visuales
  const prevData = cached ? cached.data : null;
  processesCache.value[srv.id] = { loading: true, data: prevData, error: null }
  try {
    const res = await authFetch(`${API_BASE}/monitoring/${srv.id}/processes`)
    const json = await res.json()
    if (json.success) {
      processesCache.value[srv.id] = { loading: false, data: json.processes, error: null }
      
      // Construir histórico local para gráficas multi-línea
      if (!processHistoryCache.value[srv.id]) {
        processHistoryCache.value[srv.id] = { cpu: {}, ram: {} }
      }
      const history = processHistoryCache.value[srv.id]
      const now = Date.now()
      
      // TAREA 1 & TAREA 2: Agrupación por Nombre y Filtrado
      const ignoredProcesses = ['ps', 'top', 'bash', 'awk', 'grep', 'sed', 'wmic', 'tasklist', 'htop']
      const grouped = {}
      
      json.processes.forEach(p => {
        const baseName = p.name.toLowerCase().replace('.exe', '').trim()
        if (ignoredProcesses.includes(baseName)) return; // TAREA 2: Filtrar
        
        // Sumar recursos por nombre base (TAREA 1)
        if (!grouped[baseName]) {
          grouped[baseName] = { name: p.name, cpu: 0, ram: 0 }
        }
        grouped[baseName].cpu += p.cpu_percent
        grouped[baseName].ram += p.mem_percent
      })
      
      const currentNames = new Set(Object.keys(grouped))
      
      Object.keys(grouped).forEach(baseName => {
        const p = grouped[baseName]
        const displayName = p.name.substring(0, 20) // Nombre limpio sin PID
        
        if (!history.cpu[baseName]) {
          history.cpu[baseName] = { name: displayName, data: Array.from({length: 19}, (_, i) => [now - (19-i)*5000, 0]) }
        }
        if (!history.ram[baseName]) {
          history.ram[baseName] = { name: displayName, data: Array.from({length: 19}, (_, i) => [now - (19-i)*5000, 0]) }
        }
        
        history.cpu[baseName].data.push([now, parseFloat(p.cpu.toFixed(1))])
        history.ram[baseName].data.push([now, parseFloat(p.ram.toFixed(1))])
      })
      
      // Limpiar procesos muertos y mantener ventana de 20 puntos
      Object.keys(history.cpu).forEach(baseName => {
        if (!currentNames.has(baseName)) {
           history.cpu[baseName].data.push([now, 0])
           history.ram[baseName].data.push([now, 0])
        }
        if (history.cpu[baseName].data.length > 20) history.cpu[baseName].data.shift()
        if (history.ram[baseName].data.length > 20) history.ram[baseName].data.shift()
        
        const sumCpu = history.cpu[baseName].data.reduce((acc, curr) => acc + curr[1], 0)
        const sumRam = history.ram[baseName].data.reduce((acc, curr) => acc + curr[1], 0)
        if (sumCpu === 0 && sumRam === 0 && !currentNames.has(baseName)) {
           delete history.cpu[baseName]
           delete history.ram[baseName]
        }
      })
      
    } else {
      processesCache.value[srv.id] = { loading: false, data: [], error: json.error || json.detail || 'Sin datos' }
    }
  } catch (e) {
    processesCache.value[srv.id] = { loading: false, data: [], error: 'Error de red o timeout' }
  }
}

function onMouseMoveMetric(e, srv, type) {
  if (!srv || srv.stats.status !== 'online') return
  const val = type === 'cpu' ? srv.stats.CPU : srv.stats.RAM_Percent
  if (val < 85) {
    popoverData.value.show = false
    return
  }
  
  popoverData.value = {
    show: true,
    x: e.clientX,
    y: e.clientY,
    srv,
    type
  }
  fetchProcesses(srv)
}

function onMouseLeaveMetric() {
  popoverData.value.show = false
}

watch(servers, (newServers) => {
  newServers.forEach(srv => {
    if (srv.stats.status !== 'online' && selectedServer.value?.id === srv.id) {
      closeModal()
    }
  })
}, { deep: true })

// ── APEXCHARTS CONFIGURATION (AREA CHARTS & LINE CHARTS) ─────────────────────
const normalColors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899']

const categories = Array.from({ length: 20 }, (_, i) => {
  return new Date(Date.now() - (19 - i) * 5 * 60000).getTime()
})

const baseChartOptions = {
  chart: {
    type: 'line',
    group: 'monitoreo',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    toolbar: { show: false },
    zoom: { enabled: false },
    background: 'transparent',
    animations: { enabled: false }
  },
  fill: {
    type: 'solid',
    opacity: 1
  },
  dataLabels: { enabled: false },
  stroke: { curve: 'straight', width: 2 },
  grid: {
    borderColor: '#f1f5f9',
    strokeDashArray: 0,
    padding: { top: 10, right: 10, bottom: 0, left: 10 },
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } }
  },
  xaxis: {
    type: 'datetime',
    categories: categories,
    axisBorder: { show: false },
    axisTicks: { show: false },
    labels: {
      datetimeUTC: false,
      format: 'h:mm a',
      style: { colors: '#64748b', fontSize: '10px' }
    },
    tooltip: { enabled: false },
    crosshairs: {
      show: true,
      stroke: { color: '#94a3b8', width: 1.5, dashArray: 4 }
    }
  },
  yaxis: {
    opposite: true,
    min: 0,
    max: 100,
    tickAmount: 2,
    labels: {
      style: { colors: '#64748b', fontSize: '10px' },
      formatter: (value) => value.toFixed(0) + '%'
    }
  },
  markers: { size: 0, hover: { size: 4, sizeOffset: 2 } },
  tooltip: {
    shared: true,
    intersect: false,
    custom: function({ series, seriesIndex, dataPointIndex, w }) {
      // Determinar el timestamp (Soporta categories y datetime [x,y])
      let ts;
      if (w.config.xaxis.categories && w.config.xaxis.categories.length > 0) {
        ts = w.config.xaxis.categories[dataPointIndex]
      } else {
        for(let i=0; i<w.globals.seriesX.length; i++) {
          if (w.globals.seriesX[i] && w.globals.seriesX[i][dataPointIndex]) {
            ts = w.globals.seriesX[i][dataPointIndex];
            break;
          }
        }
      }
      
      const date = new Date(ts)
      const dateStr = new Intl.DateTimeFormat('es-ES', {
        day: '2-digit', month: 'short', 
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
      }).format(date).replace('.', '')

      // Lógica de posicionamiento GCP-style y unidades
      const isPercent = w.config.yaxis[0]?.max === 100
      const isDashboard = w.globals.chartID === 'cpuChart' || w.globals.chartID === 'ramChart'
      const positionClass = isDashboard 
        ? (w.globals.chartID === 'cpuChart' ? 'translate-x-[15px] -translate-y-[10px]' : '-translate-x-[calc(100%+15px)] -translate-y-[10px]') 
        : '-translate-x-1/2 -translate-y-4'

      let html = `<div style="width: 0; position: relative; overflow: visible; z-index: 9999;">
        <div class="bg-white/95 backdrop-blur-md border border-slate-200 p-3 text-xs font-sans rounded-md shadow-xl ${positionClass}" style="width: 240px; position: absolute; pointer-events: none;">
          <div class="text-slate-500 mb-2 border-b border-slate-100 pb-1.5 font-mono text-[10px] tracking-widest uppercase flex items-center justify-between">
            <span>${dateStr}</span>
          </div>
          <div class="flex flex-col gap-1.5">`

      // Ordenar items de mayor a menor consumo
      const currentPoints = w.config.series.map((s, idx) => {
         const val = (series && series[idx] && series[idx][dataPointIndex] !== undefined) ? series[idx][dataPointIndex] : 0
         return {
            name: s.name,
            val: val,
            color: w.globals.colors[idx],
            index: idx
         }
      }).sort((a,b) => b.val - a.val)

      currentPoints.forEach((pt) => {
        if (pt.val === undefined || pt.val === null) return;
        const isFaded = seriesIndex !== -1 && seriesIndex !== pt.index
        const fontClass = isFaded ? 'text-slate-400' : 'font-bold text-slate-800'
        const dotOpacity = isFaded ? '0.3' : '1'
        const unit = isPercent ? '%' : (w.globals.chartID === 'processRamChart' ? 'M' : '')
        
        html += `<div class="flex justify-between items-center">
          <div class="flex items-center gap-2 ${fontClass}">
            <span class="block w-2 h-2 shrink-0" style="background-color: ${pt.color}; opacity: ${dotOpacity}; border-radius: 50%;"></span>
            <span class="truncate w-32 font-mono text-[10px]" title="${pt.name}">${pt.name}</span>
          </div>
          <span class="${fontClass} font-mono text-[11px]">${pt.val}${unit}</span>
        </div>`
      })

      html += `</div></div></div>`
      return html
    }
  },
  states: {
    hover: { filter: { type: 'none' } },
    active: { filter: { type: 'none' } }
  },
  legend: {
    show: true,
    position: 'bottom',
    horizontalAlign: 'left',
    fontSize: '11px',
    markers: { radius: 0, width: 8, height: 8, offsetX: -2 },
    itemMargin: { horizontal: 10, vertical: 0 }
  }
}

// Configs para los charts superiores del dashboard
const cpuChartOptions = ref({
  ...baseChartOptions,
  chart: { ...baseChartOptions.chart, id: 'cpuChart' }
})
const ramChartOptions = ref({
  ...baseChartOptions,
  chart: { ...baseChartOptions.chart, id: 'ramChart' }
})

// Configs para los charts del Modal del Servidor (Single-line)
const modalChartOptions = {
  ...baseChartOptions,
  chart: {
    ...baseChartOptions.chart,
    type: 'area',
    animations: { enabled: true, dynamicAnimation: { speed: 500 } }
  },
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05, stops: [0, 100] }
  },
  colors: ['#3b82f6'],
  stroke: { curve: 'smooth', width: 2.5 },
  xaxis: {
    ...baseChartOptions.xaxis,
    type: 'datetime',
    categories: categories
  }
}

const modalCpuChartOptions = ref({
  ...modalChartOptions,
  chart: { ...modalChartOptions.chart, id: 'modalCpuChart' },
  yaxis: { ...modalChartOptions.yaxis, max: 100 }
})

const modalRamChartOptions = ref({
  ...modalChartOptions,
  colors: ['#8b5cf6'],
  chart: { ...modalChartOptions.chart, id: 'modalRamChart' },
  yaxis: { ...modalChartOptions.yaxis, max: 100 }
})

// (Mock process chart options removed)

// Configuración base para Gráficas Multi-línea de Procesos
const processChartOptions = {
  ...baseChartOptions,
  chart: {
    ...baseChartOptions.chart,
    type: 'line',
    animations: { enabled: true, dynamicAnimation: { speed: 500 } }
  },
  colors: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
  stroke: { curve: 'smooth', width: 2.5 },
  fill: { type: 'solid', opacity: 1 },
  grid: {
    ...baseChartOptions.grid,
    padding: { top: 5, right: 10, bottom: -5, left: 10 }
  },
  legend: {
    show: true,
    position: 'bottom',
    horizontalAlign: 'center',
    fontSize: '10px',
    fontFamily: 'ui-sans-serif, system-ui, sans-serif',
    offsetY: 5,
    markers: { radius: 2, width: 8, height: 8, offsetX: -2 },
    itemMargin: { horizontal: 6, vertical: 0 }
  },
  xaxis: {
    ...baseChartOptions.xaxis,
    type: 'datetime',
    categories: undefined, // Obligatorio quitar categories para arrays de timestamps
    labels: {
      ...baseChartOptions.xaxis.labels,
      format: 'HH:mm:ss'
    }
  },
  yaxis: {
    ...baseChartOptions.yaxis,
    max: 100 // TAREA 3: Escala fija del 0 al 100%
  }
}

const processCpuSeries = computed(() => {
  const history = processHistoryCache.value[selectedServer.value?.id]?.cpu
  if (!history || Object.keys(history).length === 0) return [{ name: 'Sin datos', data: [] }]
  return Object.values(history)
    .filter(item => item && item.data && item.data.length > 0)
    .sort((a,b) => {
      const valB = b.data[b.data.length-1]?.[1] || 0
      const valA = a.data[a.data.length-1]?.[1] || 0
      return valB - valA
    })
    .slice(0, 5)
})

const processCpuOptions = computed(() => ({
  ...processChartOptions,
  chart: { ...processChartOptions.chart, id: 'processCpuChart' }
}))

const processRamSeries = computed(() => {
  const history = processHistoryCache.value[selectedServer.value?.id]?.ram
  if (!history || Object.keys(history).length === 0) return [{ name: 'Sin datos', data: [] }]
  return Object.values(history)
    .filter(item => item && item.data && item.data.length > 0)
    .sort((a,b) => {
      const valB = b.data[b.data.length-1]?.[1] || 0
      const valA = a.data[a.data.length-1]?.[1] || 0
      return valB - valA
    })
    .slice(0, 5)
})

const processRamOptions = computed(() => ({
  ...processChartOptions,
  colors: ['#8b5cf6', '#d946ef', '#f43f5e', '#f59e0b', '#10b981'],
  chart: { ...processChartOptions.chart, id: 'processRamChart' }
}))

const isHoveringCharts = ref(false)
const cpuSeries = ref([])
const ramSeries = ref([])

function updateChartSeries() {
  if (isHoveringCharts.value) return
  const sorted = [...servers.value].sort((a, b) => a.name.localeCompare(b.name))
  const top5 = sorted.slice(0, 5)

  cpuSeries.value = top5.map(srv => ({
    name: srv.name,
    data: srv.history?.cpu || []
  }))
  ramSeries.value = top5.map(srv => ({
    name: srv.name,
    data: srv.history?.ram || []
  }))

  const getDynamicColor = (srv, idx, type) => {
    const history = type === 'cpu' ? srv.history?.cpu : srv.history?.ram;
    const latest = history ? history[history.length - 1] : 0;
    if (latest >= 80) return '#ef4444'; 
    return normalColors[idx % normalColors.length];
  }

  cpuChartOptions.value = { 
    ...cpuChartOptions.value, 
    colors: top5.map((srv, idx) => getDynamicColor(srv, idx, 'cpu')) 
  }
  
  ramChartOptions.value = { 
    ...ramChartOptions.value, 
    colors: top5.map((srv, idx) => getDynamicColor(srv, idx, 'ram')) 
  }
}

watch(isHoveringCharts, (hovering) => {
  if (!hovering) updateChartSeries()
})

// ── DATA FETCHING ─────────────────────────────────────────────────────────────
async function fetchStats() {
  loading.value = true
  error.value = ''
  try {
    const res = await authFetch(`${API_BASE}/monitoring/`)
    const data = await res.json()
    if (res.ok && data.success) {
      const now = new Date()
      lastUpdate.value = now.toLocaleTimeString('es-CO')

      data.data.forEach(incomingSrv => {
        let existingSrv = servers.value.find(s => s.id === incomingSrv.id)
        if (!incomingSrv.history) {
          incomingSrv.history = { cpu: Array(20).fill(0), ram: Array(20).fill(0) }
        }
        if (!existingSrv) {
          servers.value.push(incomingSrv)
        } else {
          existingSrv.stats = incomingSrv.stats
          existingSrv.name = incomingSrv.name
          existingSrv.type = incomingSrv.type
          existingSrv.os_type = incomingSrv.os_type
          existingSrv.ip = incomingSrv.ip
          existingSrv.history = incomingSrv.history
        }
      })

      const incomingIds = data.data.map(s => s.id)
      servers.value = servers.value.filter(s => incomingIds.includes(s.id))

      updateChartSeries()
      
      // Auto-refrescar los procesos si el modal de algún servidor está abierto (polling silencioso)
      if (selectedServer.value) {
        fetchProcesses(selectedServer.value, true)
      }
    } else {
      error.value = data.detail || 'Error al obtener estadísticas.'
    }
  } catch (e) {
    error.value = 'Fallo de red al conectar con el backend.'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  if (pollInterval) clearInterval(pollInterval)
  pollInterval = setInterval(() => {
    fetchStats()
    fetchPbxStats()
  }, 5000)
}

function stopPolling() {
  if (pollInterval) clearInterval(pollInterval)
}

// ── HELPERS DE COLOR Y FORMATO ───────────────────────────────────────────────
function getProgressColorHex(percent) {
  if (percent >= 80) return '#ef4444'
  return '#2563eb'
}

function getProgressColorClass(percent) {
  if (percent >= 80) return 'bg-red-500'
  return 'bg-blue-600'
}

function getTextClass(percent) {
  if (percent >= 80) return 'text-red-500'
  return 'text-slate-700'
}

function formatDecimal(val) {
  const num = parseFloat(val)
  if (isNaN(num)) return val
  return num.toFixed(2)
}

// ── COMPUTED ──────────────────────────────────────────────────────────────────
const statsSummary = computed(() => {
  const online = servers.value.filter(s => s.stats.status === 'online').length
  const offline = servers.value.filter(s => s.stats.status !== 'online').length
  const total = servers.value.length
  return { online, offline, total }
})

const sortedServers = computed(() =>
  [...servers.value].sort((a, b) => a.name.localeCompare(b.name))
)

// Servidor en estado crítico (>= 80%)
function isCritical(srv) {
  if (srv.stats.status !== 'online') return false
  return srv.stats.CPU >= 80 || srv.stats.RAM_Percent >= 80
}

onMounted(() => {
  fetchStats()
  fetchPbxStats()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="max-w-[1600px] mx-auto w-full pb-10">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold text-slate-900">Centro de Monitoreo</h1>
      <div class="flex items-center gap-4">
        <span v-if="lastUpdate" class="text-xs font-mono text-slate-500">Última act: {{ lastUpdate }}</span>
        <button @click="fetchStats" :disabled="loading" class="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors disabled:opacity-50">
          <svg :class="['h-3.5 w-3.5 text-slate-500', loading ? 'animate-spin' : '']" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
          Sincronizar
        </button>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-6 bg-red-50/50 border border-red-200 text-red-700 p-3 text-sm flex gap-2">
      <svg class="h-4 w-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-if="servers.length === 0 && !loading" class="bg-white border border-slate-200 p-12 text-center">
      <h3 class="text-sm font-semibold text-slate-900">No hay instancias registradas</h3>
    </div>

    <!-- KPI Widgets Row -->
    <div v-if="servers.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
      <!-- Widget Telefonía PBX -->
      <div class="bg-white border border-slate-200 flex flex-col shadow-sm">
        <div class="px-4 py-2 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <h2 class="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
            Telefonía PBX (Issabel)
            <span :class="['relative flex h-2 w-2 ml-1', pbxData.troncal101 === 1 ? '' : 'animate-pulse']" :title="pbxData.troncal101 === 1 ? 'Troncal SIP 101 OK' : 'Troncal SIP 101 CAÍDA'">
              <span :class="['relative inline-flex rounded-full h-2 w-2', pbxData.troncal101 === 1 ? 'bg-emerald-500' : 'bg-red-500']"></span>
            </span>
          </h2>
        </div>
        <div class="p-4 flex items-center justify-between">
          <div class="flex flex-col">
            <span class="text-[10px] text-slate-400 font-mono uppercase tracking-widest mb-1">Llamadas Activas</span>
            <div class="flex items-baseline gap-2">
              <span class="text-3xl font-light text-slate-800 leading-none">{{ pbxData.llamadasActivas }}</span>
            </div>
          </div>
          <div class="flex flex-col gap-2 border-l border-slate-100 pl-4">
            <!-- Robot IVR -->
            <div class="flex items-center gap-2" title="pbx.ivr_test">
              <span :class="['w-1.5 h-1.5 rounded-full shrink-0', pbxData.robotIvr === 1 ? 'bg-emerald-500' : 'bg-red-500']"></span>
              <span class="text-[10px] text-slate-600 font-mono">Robot IVR (Motor)</span>
            </div>
            <!-- Opciones de Menú -->
            <div class="flex items-center gap-2" title="pbx.ivr_option[1] y [2]">
              <span :class="['w-1.5 h-1.5 rounded-full shrink-0', (pbxData.rutaOpcion1 === 1 && pbxData.rutaOpcion2 === 1) ? 'bg-emerald-500' : 'bg-red-500']"></span>
              <span class="text-[10px] text-slate-600 font-mono">
                {{ (pbxData.rutaOpcion1 === 1 && pbxData.rutaOpcion2 === 1) ? 'Rutas OK' : 'Falla en Rutas' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Global Metrics Charts (Area Charts) -->
    <div v-if="servers.length > 0"
         class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8"
         @mouseenter="isHoveringCharts = true"
         @mouseleave="isHoveringCharts = false">
      <div class="bg-white border border-slate-200 flex flex-col relative shadow-sm">
        <div class="px-4 py-2.5 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center">
          <h2 class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Uso de CPU Global (Top 5 Instancias)</h2>
          <span class="text-[10px] text-slate-400 font-mono">Última hora</span>
        </div>
        <div class="px-2 pt-4 pb-2 h-64 w-full relative z-10">
          <VueApexCharts type="line" height="100%" :options="cpuChartOptions" :series="cpuSeries" />
        </div>
      </div>
      <div class="bg-white border border-slate-200 flex flex-col relative shadow-sm">
        <div class="px-4 py-2.5 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center">
          <h2 class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Uso de Memoria (RAM)</h2>
          <span class="text-[10px] text-slate-400 font-mono">Top 5 Instancias</span>
        </div>
        <div class="px-2 pt-4 pb-2 h-64 w-full relative z-10">
          <VueApexCharts type="line" height="100%" :options="ramChartOptions" :series="ramSeries" />
        </div>
      </div>
    </div>

    <!-- Data Grid (Nodes Table) -->
    <div v-if="servers.length > 0" class="bg-white border border-slate-200 shadow-sm">
      <div class="px-4 py-2 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
        <h2 class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Métricas de Instancias</h2>
        <div class="flex gap-4 font-mono text-[11px] text-slate-500">
          <span>Total: {{ statsSummary.total }}</span>
          <span class="text-emerald-600">Online: {{ statsSummary.online }}</span>
          <span class="text-red-600">Offline: {{ statsSummary.offline }}</span>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse whitespace-nowrap">
          <thead>
            <tr class="border-b border-slate-200 bg-white">
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-64">Instancia</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-12 text-center">Estatus</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-48">CPU</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-48">Memoria</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold">Almacenamiento</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold text-right w-32">Uptime</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold text-center w-10"></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="srv in sortedServers" :key="srv.id">
              <!-- FILA PRINCIPAL -->
              <tr
                :class="[
                  'transition-colors group border-b border-slate-50',
                  srv.stats.status === 'online' 
                    ? (isCritical(srv) ? 'bg-red-500/[0.04] hover:bg-red-500/[0.08] cursor-pointer' : 'hover:bg-slate-50 cursor-pointer') 
                    : 'bg-slate-50/50 cursor-not-allowed text-slate-400'
                ]"
                @click="openModal(srv)"
              >
                <!-- Instancia -->
                <td class="py-2 px-4 align-middle border-r border-slate-50">
                  <div class="flex flex-col">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold text-slate-800 text-xs">{{ srv.name }}</span>
                      <!-- Badge OS -->
                      <span :class="['text-[9px] font-bold uppercase tracking-wider px-1 py-px rounded-sm shrink-0', srv.os_type === 'linux' ? 'bg-slate-100 text-slate-500' : 'bg-slate-100 text-slate-400']">
                        {{ srv.os_type === 'linux' ? 'LNX' : 'WIN' }}
                      </span>
                    </div>
                    <span class="text-[11px] text-slate-500 font-mono mt-0.5">{{ srv.ip }}</span>
                  </div>
                </td>

                <!-- Estado (Pulsing Dot) -->
                <td class="py-2 px-4 align-middle border-r border-slate-50">
                  <div v-if="srv.stats.status === 'online'" class="flex justify-center items-center h-full" title="ONLINE">
                    <span class="relative flex h-2.5 w-2.5">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                    </span>
                  </div>
                  <div v-else class="flex justify-center items-center h-full" :title="'OFFLINE: ' + (srv.stats.error || 'Connection Timeout')">
                    <span class="relative flex h-2.5 w-2.5">
                      <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-slate-300"></span>
                    </span>
                  </div>
                </td>

                <!-- CPU -->
                <td class="py-2 px-4 align-middle border-r border-slate-50"
                    @mousemove="onMouseMoveMetric($event, srv, 'cpu')"
                    @mouseleave="onMouseLeaveMetric">
                  <div v-if="srv.stats.status === 'online'" class="flex items-center gap-3">
                    <span :class="['font-mono text-[11px] w-9 text-right font-medium', getTextClass(srv.stats.CPU)]">{{ srv.stats.CPU }}%</span>
                    <div class="h-6 w-24 border-l border-b border-slate-200 flex-shrink-0 relative">
                      <div class="absolute inset-0 pointer-events-none opacity-20" style="background-image: linear-gradient(to top, #cbd5e1 1px, transparent 1px); background-size: 100% 33%;"></div>
                      <Sparkline :data="srv.history?.cpu || []" :color="getProgressColorHex(srv.stats.CPU)" :min="0" :max="100" />
                    </div>
                  </div>
                  <div v-else class="text-xs font-mono">-</div>
                </td>

                <!-- Memoria -->
                <td class="py-2 px-4 align-middle border-r border-slate-50"
                    @mousemove="onMouseMoveMetric($event, srv, 'ram')"
                    @mouseleave="onMouseLeaveMetric">
                  <div v-if="srv.stats.status === 'online'" class="flex items-center gap-3">
                    <div class="flex flex-col text-right w-12">
                      <span :class="['font-mono text-[11px] font-medium', getTextClass(srv.stats.RAM_Percent)]">{{ srv.stats.RAM_Percent }}%</span>
                      <span class="font-mono text-[9px] text-slate-400">{{ formatDecimal(srv.stats.RAM_Used) }}G</span>
                    </div>
                    <div class="h-6 w-24 border-l border-b border-slate-200 flex-shrink-0 relative">
                      <div class="absolute inset-0 pointer-events-none opacity-20" style="background-image: linear-gradient(to top, #cbd5e1 1px, transparent 1px); background-size: 100% 33%;"></div>
                      <Sparkline :data="srv.history?.ram || []" :color="getProgressColorHex(srv.stats.RAM_Percent)" :min="0" :max="100" />
                    </div>
                  </div>
                  <div v-else class="text-xs font-mono">-</div>
                </td>

                <!-- Discos -->
                <td class="py-2 px-4 align-middle whitespace-normal border-r border-slate-50">
                  <div v-if="srv.stats.status === 'online'" class="flex flex-wrap gap-2.5">
                    <div v-for="disk in (srv.os_type === 'linux' ? srv.stats.Disks.filter(d => d.DeviceID === '/') : srv.stats.Disks)" :key="disk.DeviceID" class="flex items-center gap-1.5 w-full max-w-[150px]">
                      <span class="font-mono text-[10px] text-slate-600 font-semibold w-3">{{ disk.DeviceID.replace(':', '') }}</span>
                      <div class="w-full bg-slate-100 h-1.5 border border-slate-200">
                        <div :class="['h-full transition-all duration-1000 ease-out', getProgressColorClass(((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100)]" :style="`width: ${((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100}%`"></div>
                      </div>
                      <span class="font-mono text-[10px] text-slate-500 w-6 text-right">{{ Math.round(((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100) }}%</span>
                    </div>
                    <div v-if="!srv.stats.Disks || !srv.stats.Disks.length" class="text-[10px] text-slate-400 italic">N/A</div>
                  </div>
                  <div v-else class="text-xs font-mono">-</div>
                </td>

                <!-- Uptime -->
                <td class="py-2 px-4 align-middle text-right border-r border-slate-50">
                  <div v-if="srv.stats.status === 'online'" class="text-[11px] text-slate-600 font-mono">
                    {{ srv.stats.UptimeDays }}d {{ srv.stats.UptimeHours }}h
                  </div>
                  <div v-else class="text-xs font-mono">-</div>
                </td>

                <!-- Action / Arrow -->
                <td class="py-2 px-3 align-middle text-center">
                  <button
                    v-if="srv.stats.status === 'online'"
                    type="button"
                    title="Ver Detalles"
                    class="w-6 h-6 flex items-center justify-center text-slate-300 group-hover:text-slate-600 transition-colors rounded-sm"
                  >
                    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
                    </svg>
                  </button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- POPOVER FLOTANTE (TOOLTIP TOP 3 PROCESOS) -->
    <Teleport to="body">
      <div v-if="popoverData.show" 
           class="fixed z-[100] pointer-events-none bg-slate-900 text-white rounded-md shadow-2xl p-3 w-56 transform -translate-x-1/2 -translate-y-[calc(100%+15px)] transition-opacity"
           :style="{ left: popoverData.x + 'px', top: popoverData.y + 'px' }">
        
        <div class="text-[10px] uppercase font-bold text-slate-400 mb-2 border-b border-slate-700 pb-1 flex justify-between">
          <span>Top Procesos</span>
          <span :class="popoverData.type === 'cpu' ? 'text-blue-400' : 'text-purple-400'">{{ popoverData.type === 'cpu' ? 'CPU' : 'RAM' }}</span>
        </div>
        
        <div v-if="processesCache[popoverData.srv.id]?.loading" class="flex justify-center py-2">
          <span class="w-4 h-4 border-2 border-slate-600 border-t-white rounded-full animate-spin"></span>
        </div>
        <div v-else-if="!processesCache[popoverData.srv.id]?.data?.length" class="text-[10px] text-slate-500 text-center py-1">
          No hay datos
        </div>
        <div v-else class="space-y-1.5">
          <div v-for="proc in processesCache[popoverData.srv.id].data.slice(0, 3)" :key="proc.pid" class="flex justify-between text-[11px] font-mono">
            <span class="truncate w-32 font-sans" :title="proc.name">{{ proc.name }}</span>
            <span :class="popoverData.type === 'cpu' ? 'text-red-400' : 'text-amber-400'">
              {{ (popoverData.type === 'cpu' ? proc.cpu_percent : proc.mem_percent).toFixed(1) }}%
            </span>
          </div>
        </div>
        
        <!-- Flecha inferior -->
        <div class="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 transform rotate-45"></div>
      </div>
    </Teleport>

    <!-- MODAL DETALLE DE SERVIDOR (GCP Style) -->
    <Teleport to="body">
      <div v-if="selectedServer" class="fixed inset-0 z-[60] flex items-center justify-center p-4 sm:p-6">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity" @click="closeModal"></div>
        
        <!-- Modal Content -->
        <div class="relative bg-slate-50 w-full max-w-6xl max-h-[95vh] shadow-2xl flex flex-col rounded-md overflow-hidden animate-fade-in-up border border-slate-200">
          
          <!-- Header GCP Style -->
          <div class="px-4 py-2 border-b border-slate-200 bg-white flex items-center justify-between shrink-0">
            <div class="flex items-center gap-3">
              <!-- Pulsing Dot -->
              <div class="flex justify-center items-center h-full" :title="selectedServer.stats.status">
                <span v-if="selectedServer.stats.status === 'online'" class="relative flex h-2.5 w-2.5">
                  <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </span>
                <span v-else class="relative flex h-2.5 w-2.5">
                  <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
                </span>
              </div>

              <!-- Titulo e Info -->
              <div class="flex items-center gap-3">
                <h2 class="text-sm font-bold text-slate-800 flex items-center gap-2">
                  {{ selectedServer.name }}
                  <span :class="['text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-sm shrink-0', selectedServer.os_type === 'linux' ? 'bg-slate-100 text-slate-500' : 'bg-slate-100 text-slate-400']">
                    {{ selectedServer.os_type === 'linux' ? 'LNX' : 'WIN' }}
                  </span>
                </h2>
                <div class="h-3 w-px bg-slate-200"></div>
                <div class="flex items-center gap-3 text-[11px] font-mono text-slate-500">
                  <span>{{ selectedServer.ip }}</span>
                  <span class="text-slate-300">|</span>
                  <span>Uptime: {{ selectedServer.stats.UptimeDays }}d {{ selectedServer.stats.UptimeHours }}h</span>
                </div>
              </div>
            </div>
            
            <button @click="closeModal" class="text-slate-400 hover:text-slate-600 p-1.5 rounded-sm transition-colors hover:bg-slate-100">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <!-- Body -->
          <div class="flex-1 overflow-y-auto bg-slate-50 p-6">
            <div class="mb-6">
              <h3 class="text-sm font-bold text-slate-800 mb-1">Visor de Rendimiento</h3>
              <p class="text-xs text-slate-500">Evolución de recursos de la instancia en tiempo real</p>
            </div>

            <div v-if="selectedServer.history?.cpu?.length > 0" class="grid grid-cols-1 xl:grid-cols-2 gap-6">
              
              <!-- CPU Chart -->
              <div class="bg-white border border-slate-200 flex flex-col shadow-sm rounded-sm">
                <div class="px-4 py-2 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center rounded-t-sm">
                  <h2 class="text-[11px] font-bold text-slate-600 tracking-wider">Uso de CPU</h2>
                  <span class="text-[9px] text-slate-400 font-mono">Histórico %</span>
                </div>
                <div class="p-2 h-56 w-full relative z-10">
                  <VueApexCharts type="area" height="100%" :options="modalCpuChartOptions" :series="selectedCpuSeries" />
                </div>
              </div>

              <!-- RAM Chart -->
              <div class="bg-white border border-slate-200 flex flex-col shadow-sm rounded-sm">
                <div class="px-4 py-2 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center rounded-t-sm">
                  <h2 class="text-[11px] font-bold text-slate-600 tracking-wider">Uso de Memoria</h2>
                  <span class="text-[9px] text-slate-400 font-mono">Histórico %</span>
                </div>
                <div class="p-2 h-56 w-full relative z-10">
                  <VueApexCharts type="area" height="100%" :options="modalRamChartOptions" :series="selectedRamSeries" />
                </div>
              </div>
              
              <!-- Process CPU List -->
              <div class="bg-white border border-slate-200 flex flex-col shadow-sm rounded-sm">
                <div class="px-4 py-2 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center rounded-t-sm">
                  <h2 class="text-[11px] font-bold text-slate-600 tracking-wider">Top Procesos — CPU</h2>
                  <span class="text-[9px] text-emerald-600 font-mono font-semibold flex items-center gap-1">
                    <span class="relative flex h-1.5 w-1.5"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span></span>
                    Tiempo Real
                  </span>
                </div>
                <div class="p-1 h-56 overflow-y-hidden relative z-10">
                  <div v-if="processesCache[selectedServer.id]?.loading && !processesCache[selectedServer.id]?.data" class="flex justify-center h-full items-center">
                     <span class="w-6 h-6 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin"></span>
                  </div>
                  <div v-else-if="!processesCache[selectedServer.id]?.data || processesCache[selectedServer.id].data.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 p-6 text-center">
                    <svg class="w-8 h-8 mb-2 opacity-50 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" v-if="processesCache[selectedServer.id]?.error"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    <svg class="w-8 h-8 mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" v-else><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    
                    <span class="text-xs font-medium text-slate-500">{{ processesCache[selectedServer.id]?.error ? 'Error al obtener procesos' : 'No hay datos de procesos' }}</span>
                    <span class="text-[10px] text-slate-400 mt-1 max-w-[250px] leading-relaxed">{{ processesCache[selectedServer.id]?.error || 'El agente no ha reportado procesos aún' }}</span>
                  </div>
                  <div v-else class="h-full w-full p-2">
                    <VueApexCharts type="line" height="100%" :options="processCpuOptions" :series="processCpuSeries" />
                  </div>
                </div>
              </div>

              <!-- Process RAM List -->
              <div class="bg-white border border-slate-200 flex flex-col shadow-sm rounded-sm">
                <div class="px-4 py-2 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center rounded-t-sm">
                  <h2 class="text-[11px] font-bold text-slate-600 tracking-wider">Top Procesos — RAM</h2>
                  <span class="text-[9px] text-emerald-600 font-mono font-semibold flex items-center gap-1">
                    <span class="relative flex h-1.5 w-1.5"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span></span>
                    Tiempo Real
                  </span>
                </div>
                <div class="p-1 h-56 overflow-y-hidden relative z-10">
                  <div v-if="processesCache[selectedServer.id]?.loading && !processesCache[selectedServer.id]?.data" class="flex justify-center h-full items-center">
                     <span class="w-6 h-6 border-2 border-slate-300 border-t-purple-600 rounded-full animate-spin"></span>
                  </div>
                  <div v-else-if="!processesCache[selectedServer.id]?.data || processesCache[selectedServer.id].data.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 p-6 text-center">
                    <svg class="w-8 h-8 mb-2 opacity-50 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" v-if="processesCache[selectedServer.id]?.error"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    <svg class="w-8 h-8 mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" v-else><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    
                    <span class="text-xs font-medium text-slate-500">{{ processesCache[selectedServer.id]?.error ? 'Error al obtener procesos' : 'No hay datos de procesos' }}</span>
                    <span class="text-[10px] text-slate-400 mt-1 max-w-[250px] leading-relaxed">{{ processesCache[selectedServer.id]?.error || 'El agente no ha reportado procesos aún' }}</span>
                  </div>
                  <div v-else class="h-full w-full p-2">
                    <VueApexCharts type="line" height="100%" :options="processRamOptions" :series="processRamSeries" />
                  </div>
                </div>
              </div>

            </div>
            <div v-else class="flex justify-center items-center h-48 bg-white border border-slate-200 border-dashed rounded-sm shadow-sm">
              <span class="text-xs text-slate-400 font-medium">Recopilando datos iniciales...</span>
            </div>
          </div>
          
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style>
/* Animaciones */
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in-up {
  animation: fade-in-up 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* Ocultar el tooltip del gráfico inactivo en grupos sincronizados */
.apexcharts-canvas .apexcharts-tooltip {
  opacity: 0 !important;
  pointer-events: none;
  transition: opacity 0.1s ease;
  box-shadow: none !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 0 !important;
}
.apexcharts-canvas:hover .apexcharts-tooltip.apexcharts-active {
  opacity: 1 !important;
}
.apexcharts-svg:has(.apexcharts-series.apexcharts-active) .apexcharts-series path {
  opacity: 0.1 !important;
  stroke-width: 1px !important;
  transition: all 0.2s ease;
}
.apexcharts-svg:has(.apexcharts-series.apexcharts-active) .apexcharts-series.apexcharts-active path {
  opacity: 1 !important;
  stroke-width: 2.5px !important;
  filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.1));
}
.apexcharts-series path {
  transition: all 0.2s ease;
}
.apexcharts-tooltip {
  overflow: visible !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.apexcharts-canvas .apexcharts-tooltip-series-group {
  display: none !important;
}
</style>
