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

// --- APEXCHARTS CONFIGURATION (GCP / Datadog Style) ---
const corporateColors = ['#2563eb', '#059669', '#7c3aed', '#ea580c', '#0891b2'] // Azul rey, verde esmeralda, morado, naranja, cian

// Generate X-Axis timestamps (last 20 points, simulated as 5 min intervals for GCP look)
const categories = Array.from({ length: 20 }, (_, i) => {
  return new Date(Date.now() - (19 - i) * 5 * 60000).getTime()
})

const baseChartOptions = {
  chart: {
    type: 'line',
    group: 'monitoreo',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    toolbar: { show: false },
    background: 'transparent',
    animations: { enabled: false }
  },
  colors: corporateColors,
  stroke: {
    curve: 'straight',
    width: 2
  },
  grid: {
    borderColor: '#f1f5f9', // Gris extremadamente tenue
    strokeDashArray: 0, // Líneas continuas, NO punteadas
    padding: { top: 10, right: 10, bottom: 0, left: 10 },
    xaxis: { lines: { show: false } }, // GCP NO usa líneas verticales
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
      stroke: {
        color: '#94a3b8', // Gris oscuro
        width: 1.5,
        dashArray: 4
      }
    }
  },
  yaxis: {
    opposite: true, // Eje Y a la derecha (GCP Style)
    min: 0,
    max: 100,
    tickAmount: 2, // 3 valores exactos: 0, 50, 100
    labels: {
      style: { colors: '#64748b', fontSize: '10px' },
      formatter: (value) => { return value.toFixed(0) + '%' }
    }
  },
  markers: {
    size: 0,
    hover: { size: 4, sizeOffset: 2 }
  },
  tooltip: {
    shared: true,
    intersect: false,
    custom: function({ series, seriesIndex, dataPointIndex, w }) {
      const ts = w.config.xaxis.categories[dataPointIndex];
      const date = new Date(ts);
      const dateStr = new Intl.DateTimeFormat('es-ES', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: 'numeric', minute: '2-digit', second: '2-digit', hour12: true
      }).format(date).replace('.', ''); // Para evitar "a. m." con punto en algunos navegadores

      // El usuario solicitó estrictamente que el chart de CPU (izquierda) SIEMPRE muestre el tooltip a la derecha,
      // y el chart de RAM (derecha) SIEMPRE muestre el tooltip a la izquierda, sin voltearse de forma desordenada.
      const isCpuChart = w.globals.chartID === 'cpuChart';
      const positionClass = isCpuChart ? 'translate-x-[15px] -translate-y-[10px]' : '-translate-x-[calc(100%+15px)] -translate-y-[10px]';

      // Envolvemos en un div de width: 0 para engañar al detector de colisiones horizontal,
      // pero dejamos que su altura fluya naturalmente para que ApexCharts mantenga el control vertical.
      let html = `<div style="width: 0; position: relative; overflow: visible;">
        <div class="bg-white/85 backdrop-blur-md border border-slate-200/60 p-3 text-xs font-sans rounded-none shadow-sm ${positionClass}" style="width: 230px;">
          <div class="text-slate-500 mb-2 border-b border-slate-200/60 pb-1.5">${dateStr}</div>
          <div class="flex flex-col gap-1">`;
      
      w.config.series.forEach((s, index) => {
        const val = series[index][dataPointIndex];
        const color = w.globals.colors[index];
        // seriesIndex es -1 si no hay una línea específicamente resaltada
        const isHovered = seriesIndex === index || seriesIndex === -1; 
        const isFaded = seriesIndex !== -1 && seriesIndex !== index;
        
        const fontClass = isFaded ? 'text-slate-400' : 'font-bold text-slate-800';
        const dotOpacity = isFaded ? '0.3' : '1';

        html += `<div class="flex justify-between items-center">
          <div class="flex items-center gap-1.5 ${fontClass}">
            <span class="block w-2 h-2" style="background-color: ${color}; opacity: ${dotOpacity}; border-radius: 2px;"></span>
            <span>${s.name}</span>
          </div>
          <span class="${fontClass}">${val !== undefined ? val + '%' : '-'}</span>
        </div>`;
      });
      
      html += `</div></div></div>`;
      return html;
    }
  },
  states: {
    hover: { filter: { type: 'none' } },
    active: { filter: { type: 'none' } }
  },
  legend: {
    show: true,
    position: 'bottom', // Abajo
    horizontalAlign: 'left', // Alineado a la izquierda
    fontSize: '11px',
    markers: { radius: 0, width: 8, height: 8, offsetX: -2 }, // Cuadrados pequeños
    itemMargin: { horizontal: 10, vertical: 0 }
  }
}

const cpuChartOptions = { 
  ...baseChartOptions,
  chart: { ...baseChartOptions.chart, id: 'cpuChart' }
}
const ramChartOptions = { 
  ...baseChartOptions,
  chart: { ...baseChartOptions.chart, id: 'ramChart' }
}

const isHoveringCharts = ref(false)
const cpuSeries = ref([])
const ramSeries = ref([])

// Función para actualizar los gráficos. 
// Patrón UX "Analytic Freeze": Si el usuario está leyendo el tooltip, 
// pausamos el refresco visual del gráfico para que no se le desaparezca la caja.
function updateChartSeries() {
  if (isHoveringCharts.value) return; 

  const sorted = [...servers.value].sort((a, b) => a.name.localeCompare(b.name));
  cpuSeries.value = sorted.slice(0, 5).map(srv => ({
    name: srv.name,
    data: srv.history?.cpu || []
  }));
  ramSeries.value = sorted.slice(0, 5).map(srv => ({
    name: srv.name,
    data: srv.history?.ram || []
  }));
}

// En cuanto el usuario retira el mouse, el gráfico se actualiza de golpe con los datos más recientes
watch(isHoveringCharts, (hovering) => {
  if (!hovering) {
    updateChartSeries();
  }
})
// ------------------------------------------------------


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
          existingSrv.ip = incomingSrv.ip
          existingSrv.history = incomingSrv.history
        }
      })
      
      const incomingIds = data.data.map(s => s.id)
      servers.value = servers.value.filter(s => incomingIds.includes(s.id))
      
      // Actualizar gráficos solo si no están siendo inspeccionados
      updateChartSeries()
      
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
  }, 5000)
}

function stopPolling() {
  if (pollInterval) clearInterval(pollInterval)
}

function getProgressColorHex(percent) {
  if (percent >= 90) return '#dc2626'
  if (percent >= 75) return '#d97706'
  return '#2563eb'
}

function getProgressColorClass(percent) {
  if (percent >= 90) return 'bg-red-600'
  if (percent >= 75) return 'bg-amber-600'
  return 'bg-blue-600'
}

function getTextClass(percent) {
  if (percent >= 90) return 'text-red-600'
  if (percent >= 75) return 'text-amber-600'
  return 'text-slate-700'
}

function formatDecimal(val) {
  const num = parseFloat(val)
  if (isNaN(num)) return val
  return num.toFixed(2)
}

const statsSummary = computed(() => {
  const online = servers.value.filter(s => s.stats.status === 'online').length
  const offline = servers.value.filter(s => s.stats.status !== 'online').length
  const total = servers.value.length
  return { online, offline, total }
})

const sortedServers = computed(() => {
  return [...servers.value].sort((a, b) => a.name.localeCompare(b.name))
})

onMounted(() => {
  fetchStats()
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

    <!-- Global Metrics Section (Grid) -->
    <div v-if="servers.length > 0" 
         class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8"
         @mouseenter="isHoveringCharts = true"
         @mouseleave="isHoveringCharts = false">
      <!-- Global CPU Chart -->
      <div class="bg-white border border-slate-200 flex flex-col relative">
        <div class="px-4 py-2.5 border-b border-slate-200 bg-white relative z-10 flex justify-between items-center">
          <h2 class="text-xs font-semibold text-slate-500 uppercase tracking-wider">Uso de CPU Global (Top 5 Instancias)</h2>
          <span class="text-[10px] text-slate-400 font-mono">Última hora</span>
        </div>
        <div class="px-2 pt-4 pb-2 h-64 w-full relative z-10">
          <VueApexCharts type="line" height="100%" :options="cpuChartOptions" :series="cpuSeries" />
        </div>
      </div>
      
      <!-- Global RAM Chart -->
      <div class="bg-white border border-slate-200 flex flex-col relative">
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
    <div v-if="servers.length > 0" class="bg-white border border-slate-200">
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
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-32">Estado</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-48">CPU</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold w-48">Memoria</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold">Almacenamiento</th>
              <th class="py-2 px-4 text-xs uppercase tracking-wider text-slate-500 font-semibold text-right w-32">Uptime</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="srv in sortedServers" :key="srv.id" :class="['transition-colors group', srv.stats.status === 'online' ? 'hover:bg-slate-50' : 'bg-red-50/30']">
              
              <!-- Instancia -->
              <td class="py-2 px-4 align-middle border-r border-slate-50">
                <div class="flex flex-col">
                  <span class="font-semibold text-slate-800 text-xs">{{ srv.name }}</span>
                  <span class="text-[11px] text-slate-500 font-mono mt-0.5">{{ srv.ip }}</span>
                </div>
              </td>
              
              <!-- Estado -->
              <td class="py-2 px-4 align-middle border-r border-slate-50">
                <div v-if="srv.stats.status === 'online'" class="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-600">
                  <div class="w-1.5 h-1.5 bg-emerald-500"></div> ONLINE
                </div>
                <div v-else class="flex flex-col justify-center">
                  <div class="flex items-center gap-1.5 text-[11px] font-semibold text-red-600">
                    <div class="w-1.5 h-1.5 bg-red-600"></div> OFFLINE
                  </div>
                  <div class="text-[10px] text-red-500 mt-1 truncate max-w-[120px]" :title="srv.stats.error">
                    {{ srv.stats.error || 'Connection Timeout' }}
                  </div>
                </div>
              </td>
              
              <!-- CPU -->
              <td class="py-2 px-4 align-middle border-r border-slate-50">
                <div v-if="srv.stats.status === 'online'" class="flex items-center gap-3">
                  <span :class="['font-mono text-[11px] w-9 text-right font-medium', getTextClass(srv.stats.CPU)]">{{ srv.stats.CPU }}%</span>
                  <div class="h-6 w-24 border-l border-b border-slate-200 flex-shrink-0 relative">
                    <div class="absolute inset-0 pointer-events-none opacity-20" style="background-image: linear-gradient(to top, #cbd5e1 1px, transparent 1px); background-size: 100% 33%;"></div>
                    <Sparkline :data="srv.history?.cpu || []" :color="getProgressColorHex(srv.stats.CPU)" :min="0" :max="100" />
                  </div>
                </div>
                <div v-else class="text-xs text-slate-400 font-mono">-</div>
              </td>
              
              <!-- Memoria -->
              <td class="py-2 px-4 align-middle border-r border-slate-50">
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
                <div v-else class="text-xs text-slate-400 font-mono">-</div>
              </td>
              
              <!-- Discos -->
              <td class="py-2 px-4 align-middle whitespace-normal border-r border-slate-50">
                <div v-if="srv.stats.status === 'online'" class="flex flex-wrap gap-2.5">
                  <div v-for="disk in srv.stats.Disks" :key="disk.DeviceID" class="flex items-center gap-1.5 w-full max-w-[150px]">
                    <span class="font-mono text-[10px] text-slate-600 font-semibold w-3">{{ disk.DeviceID.replace(':', '') }}</span>
                    <div class="w-full bg-slate-100 h-1.5 border border-slate-200">
                      <div :class="['h-full transition-all duration-1000 ease-out', getProgressColorClass(((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100)]" :style="`width: ${((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100}%`"></div>
                    </div>
                    <span class="font-mono text-[10px] text-slate-500 w-6 text-right">{{ Math.round(((disk.SizeGB - disk.FreeGB) / disk.SizeGB) * 100) }}%</span>
                  </div>
                  <div v-if="!srv.stats.Disks || !srv.stats.Disks.length" class="text-[10px] text-slate-400 italic">
                    N/A
                  </div>
                </div>
                <div v-else class="text-xs text-slate-400 font-mono">-</div>
              </td>
              
              <!-- Uptime -->
              <td class="py-2 px-4 align-middle text-right">
                <div v-if="srv.stats.status === 'online'" class="text-[11px] text-slate-600 font-mono">
                  {{ srv.stats.UptimeDays }}d {{ srv.stats.UptimeHours }}h
                </div>
                <div v-else class="text-xs text-slate-400 font-mono">-</div>
              </td>
              
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style>
/* 
  Ocultar el tooltip (cuadro) del gráfico inactivo en grupos sincronizados (GCP Style)
  Solo muestra el tooltip en el gráfico donde está posicionado el ratón, 
  mientras mantiene la línea vertical (crosshair) visible en ambos.
*/
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
/* GCP Hover Style (Dimming) - CSS Nativo apuntando a los paths para forzar opacidad */
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
/* Evitar que el contenedor base del tooltip interfiera con nuestro transform */
.apexcharts-tooltip {
  overflow: visible !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
/* Forzar transparencia nativa para evitar superposición extraña de tooltip viejo */
.apexcharts-canvas .apexcharts-tooltip-series-group {
  display: none !important;
}
</style>
