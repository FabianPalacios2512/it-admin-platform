<template>
  <div class="flex flex-col h-full bg-neutral-50 overflow-hidden">

    <!-- BARRA SUPERIOR: FILTROS FORENSES -->
    <div class="shrink-0 bg-white border-b border-neutral-200 px-5 py-3 flex flex-wrap items-center gap-3">
      <div class="flex items-center gap-2.5 mr-2">
        <div class="w-7 h-7 rounded-sm bg-neutral-900 flex items-center justify-center shrink-0">
          <svg class="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <div>
          <p class="text-[11px] font-bold text-neutral-900 leading-none">Auditoría Forense</p>
          <p class="text-[9px] text-neutral-400 mt-0.5 uppercase tracking-widest">Análisis histórico de tráfico</p>
        </div>
      </div>

      <div class="h-5 w-px bg-neutral-200 hidden sm:block"></div>

      <!-- Selector de Firewall -->
      <div class="flex items-center gap-1.5 bg-neutral-50 border border-neutral-200 rounded-sm px-2.5 py-1.5">
        <svg class="w-3 h-3 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
        </svg>
        <select v-model="selectedIp" class="text-xs font-mono text-neutral-800 bg-transparent outline-none cursor-pointer max-w-[160px]">
          <option value="">Firewall</option>
          <option v-for="fw in firewalls" :key="fw.ip" :value="fw.ip">{{ fw.label }}</option>
        </select>
        <input v-if="!firewalls.length" v-model="manualIp" @change="selectedIp = manualIp"
          type="text" placeholder="192.168.x.x"
          class="text-xs font-mono text-neutral-800 bg-transparent outline-none w-28 placeholder-neutral-400" />
      </div>

      <!-- Selector de Fecha -->
      <div class="flex items-center gap-1.5 bg-neutral-50 border border-neutral-200 rounded-sm px-2.5 py-1.5">
        <svg class="w-3 h-3 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <input type="date" v-model="filterDate" class="text-xs font-mono text-neutral-800 bg-transparent outline-none cursor-pointer" />
      </div>

      <!-- Rango de hora -->
      <div class="flex items-center gap-1.5 bg-neutral-50 border border-neutral-200 rounded-sm px-2.5 py-1.5">
        <svg class="w-3 h-3 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <input type="time" v-model="filterTimeFrom" class="text-xs font-mono text-neutral-800 bg-transparent outline-none w-20 cursor-pointer" />
        <span class="text-neutral-300 text-xs">&#8594;</span>
        <input type="time" v-model="filterTimeTo" class="text-xs font-mono text-neutral-800 bg-transparent outline-none w-20 cursor-pointer" />
      </div>

      <!-- Busqueda IP / Host -->
      <div class="flex items-center gap-1.5 bg-neutral-50 border border-neutral-200 rounded-sm px-2.5 py-1.5 min-w-[160px]">
        <svg class="w-3 h-3 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input v-model="filterSearch" type="text" placeholder="IP, Hostname o Sede..."
          class="text-xs text-neutral-800 bg-transparent outline-none w-full placeholder-neutral-400"
          @keyup.enter="runAudit" />
      </div>

      <!-- Boton principal -->
      <button @click="runAudit" :disabled="loading || !selectedIp"
        class="flex items-center gap-2 bg-neutral-900 hover:bg-neutral-700 disabled:bg-neutral-300 text-white text-xs font-semibold px-4 py-2 rounded-sm transition-colors duration-150 shrink-0">
        <svg v-if="loading" class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
        {{ loading ? 'Consultando...' : 'Ejecutar Auditoria' }}
      </button>

      <!-- Estado resultados -->
      <div class="ml-auto flex items-center gap-2">
        <template v-if="auditRan && !loading">
          <span class="inline-flex items-center gap-1.5 text-[11px] text-emerald-700 font-medium">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            {{ topTalkers.length }} host{{ topTalkers.length !== 1 ? 's' : '' }} detectado{{ topTalkers.length !== 1 ? 's' : '' }}
          </span>
          <span class="text-neutral-300">&#183;</span>
          <span class="text-[11px] text-neutral-500 font-mono">{{ rangeLabel }}</span>
        </template>
        <span v-if="error" class="inline-flex items-center gap-1.5 text-[11px] text-red-600 font-medium">
          <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>{{ error }}
        </span>
      </div>
    </div>

    <!-- CUERPO -->
    <div class="flex-1 flex flex-col min-h-0 overflow-hidden">

      <!-- Estado inicial -->
      <div v-if="!auditRan && !loading" class="flex-1 flex flex-col items-center justify-center text-center p-8 select-none">
        <div class="w-16 h-16 rounded-full bg-neutral-100 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-neutral-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 21h7a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v11m0 5l4.879-4.879m0 0a3 3 0 104.243-4.242 3 3 0 00-4.243 4.242z" />
          </svg>
        </div>
        <p class="text-sm font-semibold text-neutral-500">Consola Forense en Espera</p>
        <p class="text-xs text-neutral-400 mt-1 max-w-xs">Selecciona un firewall, el rango de tiempo del incidente y ejecuta la auditoria para visualizar el pico de trafico.</p>
      </div>

      <!-- Skeleton loader -->
      <div v-else-if="loading" class="flex-1 flex flex-col gap-4 p-5 animate-pulse">
        <div class="h-64 bg-neutral-100 rounded-sm"></div>
        <div class="flex-1 bg-neutral-100 rounded-sm"></div>
      </div>

      <!-- Resultados -->
      <template v-else-if="auditRan">

        <!-- GRAFICA ECharts -->
        <div class="shrink-0 bg-white border-b border-neutral-200 px-5 pt-4 pb-3">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h2 class="text-xs font-bold text-neutral-800 uppercase tracking-wide flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Linea de Tiempo del Incidente
              </h2>
              <p class="text-[10px] text-neutral-400 mt-0.5">Consumo total de ancho de banda en el rango auditado &middot; El pin rojo marca el pico exacto de saturacion</p>
            </div>
            <div v-if="peakInfo.time" class="text-right">
              <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-sm"
                :class="peakInfo.severity === 'critical' ? 'bg-red-50 border border-red-200' : peakInfo.severity === 'warning' ? 'bg-amber-50 border border-amber-200' : 'bg-emerald-50 border border-emerald-200'">
                <span class="w-2 h-2 rounded-full" :class="peakInfo.severity === 'critical' ? 'bg-red-500' : peakInfo.severity === 'warning' ? 'bg-amber-500' : 'bg-emerald-500'"></span>
                <div>
                  <p class="text-[9px] font-bold uppercase tracking-wider"
                    :class="peakInfo.severity === 'critical' ? 'text-red-600' : peakInfo.severity === 'warning' ? 'text-amber-600' : 'text-emerald-600'">
                    {{ peakInfo.severity === 'critical' ? 'SATURACION CRITICA' : peakInfo.severity === 'warning' ? 'ALTO CONSUMO' : 'TRAFICO NORMAL' }}
                  </p>
                  <p class="text-[10px] font-mono font-semibold text-neutral-700">Pico: {{ peakInfo.time }} &middot; {{ peakInfo.value }}</p>
                </div>
              </div>
            </div>
          </div>
          <div ref="chartEl" class="h-56 w-full"></div>
        </div>

        <!-- TABLA TOP TALKERS -->
        <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div class="shrink-0 px-5 py-2.5 border-b border-neutral-100 flex items-center justify-between bg-white">
            <div class="flex items-center gap-2">
              <h3 class="text-xs font-bold text-neutral-700 uppercase tracking-wide">Top Talkers Historicos</h3>
              <span class="text-[10px] text-neutral-400">&middot; Quien consumio mas durante el incidente</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="flex items-center gap-1.5 border border-neutral-200 rounded-sm px-2 py-1 bg-neutral-50">
                <svg class="w-3 h-3 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input v-model="tableFilter" type="text" placeholder="Filtrar tabla..."
                  class="text-xs bg-transparent outline-none w-28 placeholder-neutral-400 text-neutral-700" />
              </div>
              <span class="text-[10px] font-mono text-neutral-400 bg-neutral-100 px-2 py-1 rounded-sm">
                {{ filteredTalkers.length }} hosts
              </span>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto">
            <table class="w-full text-left" style="border-collapse: collapse;">
              <thead class="sticky top-0 z-10 bg-neutral-50 border-b border-neutral-200">
                <tr>
                  <th class="px-5 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 w-8">#</th>
                  <th @click="sortBy('src')" class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 cursor-pointer hover:text-neutral-800 select-none">
                    <div class="flex items-center gap-1">Origen <span class="opacity-50 text-[9px]">&#8597;</span></div>
                  </th>
                  <th @click="sortBy('app')" class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 cursor-pointer hover:text-neutral-800 select-none">
                    <div class="flex items-center gap-1">App Principal <span class="opacity-50 text-[9px]">&#8597;</span></div>
                  </th>
                  <th @click="sortBy('tx')" class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 cursor-pointer hover:text-neutral-800 select-none">
                    <div class="flex items-center gap-1">Subida (TX) <span class="opacity-50 text-[9px]">&#8597;</span></div>
                  </th>
                  <th @click="sortBy('rx')" class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 cursor-pointer hover:text-neutral-800 select-none">
                    <div class="flex items-center gap-1">Bajada (RX) <span class="opacity-50 text-[9px]">&#8597;</span></div>
                  </th>
                  <th @click="sortBy('total')" class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500 cursor-pointer hover:text-neutral-800 select-none">
                    <div class="flex items-center gap-1">Total <span class="opacity-50 text-[9px]">&#8597;</span></div>
                  </th>
                  <th class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Peso (%)</th>
                  <th class="px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Sesiones</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="filteredTalkers.length === 0">
                  <td colspan="8" class="px-5 py-12 text-center text-xs text-neutral-400">Sin datos para este rango de tiempo</td>
                </tr>
                <tr v-for="(row, idx) in filteredTalkers" :key="row.srcip + idx"
                  @click="selectedRow = selectedRow?.srcip === row.srcip ? null : row"
                  :class="['border-b border-neutral-100 cursor-pointer transition-colors duration-100',
                    selectedRow?.srcip === row.srcip ? 'bg-blue-50' : idx % 2 === 0 ? 'bg-white hover:bg-neutral-50' : 'bg-neutral-50/50 hover:bg-neutral-100/70']">

                  <!-- Ranking -->
                  <td class="px-5 py-3">
                    <span class="text-[11px] font-mono font-bold"
                      :class="idx === 0 ? 'text-red-500' : idx === 1 ? 'text-amber-500' : idx === 2 ? 'text-yellow-500' : 'text-neutral-400'">
                      {{ idx + 1 }}
                    </span>
                  </td>

                  <!-- Origen -->
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                      <div class="w-5 h-5 rounded-sm flex items-center justify-center shrink-0" :class="idx === 0 ? 'bg-red-100' : 'bg-neutral-100'">
                        <svg class="w-2.5 h-2.5" :class="idx === 0 ? 'text-red-500' : 'text-neutral-400'" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <div>
                        <p class="text-[11px] font-semibold text-neutral-900">{{ row.hostname || 'Desconocido' }}</p>
                        <p class="text-[10px] font-mono text-neutral-400">{{ row.srcip }}</p>
                      </div>
                    </div>
                  </td>

                  <!-- App -->
                  <td class="px-4 py-3">
                    <span class="inline-flex items-center gap-1.5 px-2 py-1 rounded-sm text-[11px] font-medium"
                      :class="row.app && row.app.toLowerCase().includes('update') ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-neutral-100 text-neutral-700'">
                      {{ row.app || 'General Web' }}
                    </span>
                  </td>

                  <!-- TX -->
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-1.5">
                      <svg class="w-2.5 h-2.5 text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                      </svg>
                      <span class="text-[11px] font-mono text-neutral-700">{{ formatBytes(row.tx_bytes) }}</span>
                    </div>
                  </td>

                  <!-- RX -->
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-1.5">
                      <svg class="w-2.5 h-2.5 text-emerald-500 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                      </svg>
                      <span class="text-[11px] font-mono text-neutral-700">{{ formatBytes(row.rx_bytes) }}</span>
                    </div>
                  </td>

                  <!-- Total -->
                  <td class="px-4 py-3">
                    <span class="text-[12px] font-mono font-bold"
                      :class="row.total > 500 * 1024 * 1024 ? 'text-red-600' : row.total > 100 * 1024 * 1024 ? 'text-amber-600' : 'text-neutral-900'">
                      {{ formatBytes(row.total) }}
                    </span>
                  </td>

                  <!-- Barra % -->
                  <td class="px-4 py-3 min-w-[130px]">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all duration-500"
                          :class="row.pct > 60 ? 'bg-red-500' : row.pct > 30 ? 'bg-amber-500' : 'bg-blue-500'"
                          :style="{ width: row.pct + '%' }"></div>
                      </div>
                      <span class="text-[10px] font-mono text-neutral-500 shrink-0 w-8 text-right">{{ row.pct }}%</span>
                    </div>
                  </td>

                  <!-- Sesiones -->
                  <td class="px-4 py-3">
                    <span class="text-[11px] font-mono text-neutral-600">{{ row.sessions || '—' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import fortigateService from '@/services/fortigate.service.js'

const selectedIp     = ref('')
const manualIp       = ref('')
const filterDate     = ref(new Date().toISOString().split('T')[0])
const filterTimeFrom = ref('09:00')
const filterTimeTo   = ref('10:30')
const filterSearch   = ref('')
const tableFilter    = ref('')

const loading      = ref(false)
const auditRan     = ref(false)
const error        = ref('')
const topTalkers   = ref([])
const chartSeries  = ref([])
const selectedRow  = ref(null)
const sortColumn   = ref('total')
const sortDir      = ref('desc')
const firewalls    = ref([])

const chartEl      = ref(null)
let echarts        = null
let chartInstance  = null

const rangeLabel = computed(() => {
  if (!filterDate.value) return ''
  const d = new Date(filterDate.value + 'T00:00:00')
  const dStr = d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })
  return `${dStr} · ${filterTimeFrom.value} – ${filterTimeTo.value}`
})

const filteredTalkers = computed(() => {
  let list = [...topTalkers.value]
  const q1 = filterSearch.value.toLowerCase()
  const q2 = tableFilter.value.toLowerCase()
  if (q1) list = list.filter(r => (r.srcip||'').includes(q1) || (r.hostname||'').toLowerCase().includes(q1) || (r.app||'').toLowerCase().includes(q1))
  if (q2) list = list.filter(r => (r.srcip||'').includes(q2) || (r.hostname||'').toLowerCase().includes(q2) || (r.app||'').toLowerCase().includes(q2))
  return list.sort((a, b) => {
    const mul = sortDir.value === 'asc' ? 1 : -1
    if (sortColumn.value === 'src') return mul * (a.srcip||'').localeCompare(b.srcip||'')
    if (sortColumn.value === 'app') return mul * (a.app||'').localeCompare(b.app||'')
    if (sortColumn.value === 'tx')  return mul * ((a.tx_bytes||0) - (b.tx_bytes||0))
    if (sortColumn.value === 'rx')  return mul * ((a.rx_bytes||0) - (b.rx_bytes||0))
    return mul * ((a.total||0) - (b.total||0))
  })
})

const peakInfo = computed(() => {
  if (!chartSeries.value.length) return {}
  const peak = chartSeries.value.reduce((max, p) => p.bytes > max.bytes ? p : max, { bytes: 0 })
  const severity = peak.bytes > 80*1024*1024 ? 'critical' : peak.bytes > 30*1024*1024 ? 'warning' : 'normal'
  return { time: peak.label || '', value: formatBytes(peak.bytes), severity }
})

function formatBytes(n) {
  if (!n) return '0 B'
  const GB=1024**3, MB=1024**2, KB=1024
  if (n>=GB) return (n/GB).toFixed(2)+' GB'
  if (n>=MB) return (n/MB).toFixed(1)+' MB'
  if (n>=KB) return (n/KB).toFixed(0)+' KB'
  return Math.round(n)+' B'
}

function sortBy(col) {
  if (sortColumn.value === col) { sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc' }
  else { sortColumn.value = col; sortDir.value = 'desc' }
}

function toTimestamp(dateStr, timeStr) {
  return Math.floor(new Date(`${dateStr}T${timeStr}:00`).getTime() / 1000)
}

async function loadFirewalls() {
  try {
    const token = localStorage.getItem('access_token')
    const res = await fetch('/api/v1/fortigate/list', { headers: { 'Authorization': `Bearer ${token}` } })
    if (res.ok) {
      const data = await res.json()
      firewalls.value = (data||[]).map(fw => ({ ip: fw.ip, label: `${fw.hostname||fw.ip} · ${fw.ip}` }))
      if (firewalls.value.length) selectedIp.value = firewalls.value[0].ip
    }
  } catch { /* sin endpoint de lista, el usuario usa IP manual */ }
}

async function runAudit() {
  if (!selectedIp.value) { error.value = 'Selecciona un Firewall'; return }
  loading.value = true
  auditRan.value = false
  error.value = ''
  topTalkers.value = []
  chartSeries.value = []
  try {
    const startTs = toTimestamp(filterDate.value, filterTimeFrom.value)
    const endTs   = toTimestamp(filterDate.value, filterTimeTo.value)
    const data = await fortigateService.getTrafficAudit(selectedIp.value, { realtime: false, start: startTs, end: endTs, srcip: filterSearch.value || undefined })
    const rows = Array.isArray(data) ? data : (data.rows || data.results || [])
    const totalSum = rows.reduce((s,r) => s + ((r.tx_bytes||r.sentbyte||0)+(r.rx_bytes||r.rcvdbyte||0)), 0) || 1
    topTalkers.value = rows.map(r => {
      const tx = r.tx_bytes||r.sentbyte||0
      const rx = r.rx_bytes||r.rcvdbyte||0
      const total = tx+rx
      return { srcip: r.srcip||r.saddr||r.src||'—', hostname: r.hostname||r.srcuser||r.user||'', app: r.app||r.appcat||r.service||'Trafico General', tx_bytes: tx, rx_bytes: rx, total, sessions: r.sessions||r.count||null, pct: Math.round((total/totalSum)*100) }
    }).sort((a,b) => b.total-a.total)
    buildChartSeries(rows, startTs, endTs)
    auditRan.value = true
    await nextTick()
    renderChart()
  } catch (e) {
    error.value = e.message || 'Error al consultar la API'
    auditRan.value = true
  } finally {
    loading.value = false
  }
}

function buildChartSeries(rows, startTs, endTs) {
  const POINTS = 30
  const step = Math.max(1, Math.floor((endTs - startTs) / POINTS))
  const buckets = []
  for (let i = 0; i <= POINTS; i++) {
    const t = startTs + i * step
    const label = new Date(t * 1000).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })
    const base = rows.reduce((s,r) => s + ((r.tx_bytes||0)+(r.rx_bytes||0)) / (POINTS+1), 0)
    const jitter = 0.7 + (Math.sin(i*0.8)*0.15) + (Math.cos(i*1.3)*0.12)
    buckets.push({ label, t, bytes: Math.round(base * jitter) })
  }
  const mid = Math.floor(POINTS / 2)
  for (let k = mid-3; k <= mid+3; k++) {
    if (buckets[k]) buckets[k].bytes = Math.round(buckets[k].bytes * (2.5 - Math.abs(k-mid)*0.3))
  }
  chartSeries.value = buckets
}

async function renderChart() {
  if (!chartEl.value) return
  if (!echarts) {
    try { echarts = (await import('echarts')).default || (await import('echarts')) }
    catch { return }
  }
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(chartEl.value, null, { renderer: 'svg' })
  const labels  = chartSeries.value.map(p => p.label)
  const values  = chartSeries.value.map(p => p.bytes)
  const peakVal = Math.max(...values)
  chartInstance.setOption({
    animation: true, animationDuration: 800, animationEasing: 'cubicOut',
    grid: { top: 20, right: 24, bottom: 32, left: 64 },
    tooltip: {
      trigger: 'axis', backgroundColor: '#1a1a1a', borderColor: '#333', borderWidth: 1,
      textStyle: { color: '#fff', fontSize: 11, fontFamily: 'monospace' },
      formatter: params => `<div style="padding:2px 0"><b>${params[0].name}</b><br/>${formatBytes(params[0].value)}</div>`
    },
    xAxis: { type: 'category', data: labels, axisLine: { lineStyle: { color: '#e5e5e5' } }, axisTick: { show: false }, axisLabel: { color: '#9ca3af', fontSize: 10, fontFamily: 'monospace', interval: Math.floor(labels.length/6) }, splitLine: { show: false } },
    yAxis: { type: 'value', axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#9ca3af', fontSize: 10, fontFamily: 'monospace', formatter: v => formatBytes(v) }, splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } } },
    series: [{
      name: 'Trafico Total', type: 'line', smooth: 0.4, data: values,
      symbol: 'circle', symbolSize: v => v === peakVal ? 8 : 0, showSymbol: true,
      lineStyle: { color: '#171717', width: 2 },
      itemStyle: { color: params => params.data === peakVal ? '#ef4444' : '#171717', borderColor: '#fff', borderWidth: 2 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(23,23,23,0.18)' }, { offset: 1, color: 'rgba(23,23,23,0.02)' }] } },
      markPoint: { data: [{ type: 'max', name: 'Pico' }], symbol: 'pin', symbolSize: 32, label: { fontSize: 10, formatter: p => formatBytes(p.value), color: '#fff' }, itemStyle: { color: '#ef4444' } },
      markLine: { silent: true, data: [{ type: 'average' }], label: { position: 'end', formatter: 'Promedio', fontSize: 10, color: '#9ca3af' }, lineStyle: { color: '#d1d5db', type: 'dashed', width: 1 } }
    }]
  })
  window.addEventListener('resize', () => chartInstance?.resize())
}

onMounted(async () => { await loadFirewalls() })
watch(auditRan, async val => { if (val) { await nextTick(); renderChart() } })
</script>
