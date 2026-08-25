<template>
  <transition
    enter-active-class="transition-opacity duration-300 ease-in-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition-opacity duration-200 ease-in-out"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="session" class="fixed inset-0 bg-slate-900/50 z-[95] backdrop-blur-[2px]" @click="emit('close')"></div>
  </transition>

  <transition
    enter-active-class="transform transition ease-out duration-300"
    enter-from-class="translate-x-full"
    enter-to-class="translate-x-0"
    leave-active-class="transform transition ease-in duration-200"
    leave-from-class="translate-x-0"
    leave-to-class="translate-x-full"
  >
    <aside
      v-if="session"
      class="fixed inset-y-0 right-0 z-[100] w-[75vw] max-w-[1100px] bg-slate-50 shadow-[-16px_0_40px_-12px_rgba(0,0,0,0.12)] flex flex-col"
    >
      <header class="shrink-0 bg-white p-6 flex items-start justify-between gap-4 border-b border-slate-200 shadow-sm">
        <div class="min-w-0">
          <div class="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            <span>Sesión</span>
            <span class="text-slate-300">·</span>
            <span class="normal-case tracking-normal text-slate-500">{{ hostLabel }}</span>
          </div>
          <div class="mt-1 text-2xl font-bold font-mono leading-none truncate text-slate-900">{{ session.srcIp }}</div>
          <div class="mt-2 flex items-center gap-2 min-w-0">
            <span class="text-[10px] font-mono uppercase text-slate-400">{{ protoLabel }}</span>
            <i class="fas fa-arrow-right text-[9px] text-slate-300"></i>
            <span class="font-mono text-sm text-slate-500 truncate">{{ destinationLabel }}</span>
            <span
              class="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide"
              :class="sessionData?.active ? 'text-emerald-600' : 'text-slate-400'"
            >
              <span v-if="sessionData?.active" class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              {{ sessionData?.active ? 'En vivo' : (sessionData ? 'Cerrada' : 'Leyendo') }}
            </span>
          </div>
        </div>

        <div class="flex flex-col items-end gap-1 shrink-0 pt-1">
          <div class="flex items-center gap-2">
            <button
              v-if="!readOnly"
              type="button"
              :disabled="processing"
              class="px-3 py-1.5 rounded-lg text-[12px] font-semibold bg-red-600 text-white hover:bg-red-700 disabled:opacity-40"
              :title="`Bloquea ${destinationLabel} solo para ${session.srcIp}`"
              @click="emit('request-block')"
            >Bloquear página</button>
            <button
              type="button"
              class="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
              @click="emit('close')"
            >
              <i class="fas fa-xmark"></i>
            </button>
          </div>
          <span v-if="!readOnly" class="text-[10px] text-slate-400 font-mono truncate max-w-[280px]">
            {{ destinationLabel }} · solo este host
          </span>
        </div>
      </header>

      <div v-if="confirm && !readOnly" class="shrink-0 px-6 py-3 bg-white border-b border-slate-200 flex flex-wrap items-center gap-2">
        <select
          v-if="confirm === 'limit'"
          :value="shapeIndex"
          class="text-xs font-mono rounded-lg px-2 py-1 bg-slate-50 text-slate-800 outline-none"
          @change="emit('update:shapeIndex', Number($event.target.value))"
        >
          <option v-for="(profile, idx) in shaperProfiles" :key="profile.mbps" :value="idx">{{ profile.label || (profile.mbps >= 1000 ? `${profile.mbps / 1000} Gbps` : `${profile.mbps} Mbps`) }}</option>
        </select>
        <span v-if="confirm === 'block-cascade'" class="text-xs text-slate-600">
          ¿Bloquear en cascada <span class="font-semibold text-slate-900">{{ blockPreview.service || destinationLabel }}</span> para {{ session.srcIp }}?
        </span>
        <span v-else-if="confirm === 'block'" class="text-xs text-slate-600">
          ¿Bloquear <span class="font-mono text-slate-900">{{ blockPreview.selected || destinationLabel }}</span>?
        </span>
        <span v-if="confirm === 'block-cascade' && blockPreview.domains_label" class="font-mono text-[11px] text-slate-400 truncate max-w-[420px]" :title="blockPreview.domains_label">
          {{ blockPreview.domains_label }}
        </span>
        <button type="button" class="text-xs font-medium text-slate-500 hover:text-slate-900" @click="emit('update:confirm', '')">Cancelar</button>
        <button
          v-if="confirm === 'block-cascade'"
          type="button"
          :disabled="processing"
          class="px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-600 hover:bg-slate-100 disabled:opacity-40"
          @click="emit('confirm-action', { cascade: false })"
        >No</button>
        <button
          type="button"
          :disabled="processing || (confirm === 'limit' && shapeIndex < 0)"
          class="px-3 py-1.5 text-xs font-semibold rounded-lg disabled:opacity-40"
          :class="confirm === 'block' || confirm === 'block-cascade' ? 'bg-red-600 text-white hover:bg-red-700' : confirm === 'limit' ? 'bg-orange-50 text-orange-600 hover:bg-orange-100' : 'bg-slate-100 text-slate-800 hover:bg-slate-200'"
          @click="emit('confirm-action', confirm === 'block-cascade' ? { cascade: true } : { cascade: false })"
        >{{ processing ? 'Aplicando…' : (confirm === 'block-cascade' ? 'Sí' : 'Confirmar') }}</button>
        <span v-if="actionNote" class="text-xs text-slate-400">{{ actionNote }}</span>
      </div>
      <p v-else-if="actionNote" class="shrink-0 px-6 py-2 text-xs bg-white border-b border-slate-200 text-slate-500">{{ actionNote }}</p>

      <div v-if="loading && !sessionData" class="flex-1 flex items-center justify-center text-slate-400 bg-slate-50">
        <i class="fas fa-circle-notch fa-spin text-lg"></i>
      </div>
      <div v-else-if="error && !sessionData" class="flex-1 flex items-center justify-center px-6 text-sm text-red-600 bg-slate-50">{{ error }}</div>

      <div v-else class="flex-1 min-h-0 overflow-y-auto bg-slate-50 pb-6">
        <div class="px-6 pt-6">
          <div class="bg-white border border-slate-200 rounded-xl shadow-sm flex w-full divide-x divide-slate-200 overflow-hidden">
            <div v-for="kpi in kpis" :key="kpi.label" class="flex-1 px-4 py-3 min-w-0">
              <div class="text-[11px] text-slate-400 font-bold uppercase">{{ kpi.label }}</div>
              <div class="mt-1 text-lg font-mono font-semibold text-slate-800 truncate" :title="kpi.value">{{ kpi.value }}</div>
            </div>
          </div>
        </div>

        <div v-if="successor" class="px-6 mt-4">
          <button
            type="button"
            class="w-full text-left px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm text-xs font-medium text-amber-700 hover:bg-amber-50"
            @click="emit('open-successor', successor)"
          >
            Nueva sesión {{ successor.srcIp }} → {{ successor.dstIp }}
          </button>
        </div>

        <section class="bg-white border border-slate-200 rounded-xl shadow-sm p-4 mx-6 mt-4">
          <div class="flex items-center justify-between mb-2">
            <div class="text-sm font-semibold text-slate-700">Curva de Consumo</div>
            <div class="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-wide">
              <span class="inline-flex items-center gap-1.5 text-emerald-600"><span class="w-2.5 h-0.5 rounded-full bg-emerald-500"></span> Bajada (RX)</span>
              <span class="inline-flex items-center gap-1.5 text-indigo-600"><span class="w-2.5 h-0.5 rounded-full bg-indigo-500"></span> Subida (TX)</span>
            </div>
          </div>
          <div class="h-[240px]">
            <v-chart class="h-full w-full" :option="chartOption" autoresize />
          </div>
        </section>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 px-6 py-4">
          <section
            v-for="group in factGroups"
            :key="group.title"
            class="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden"
          >
            <div class="bg-slate-50 border-b border-slate-200 px-4 py-2 text-xs font-bold text-slate-600 uppercase tracking-wide">
              {{ group.title }}
            </div>
            <div class="px-4 py-3">
              <div
                v-for="item in group.items"
                :key="item.label"
                class="flex justify-between items-center gap-3 py-1.5 border-b border-slate-100 last:border-b-0"
              >
                <span class="text-xs text-slate-500 shrink-0">{{ item.label }}</span>
                <span class="text-xs font-mono text-slate-800 text-right break-all">{{ item.value }}</span>
              </div>
            </div>
          </section>
        </div>
      </div>
    </aside>
  </transition>
</template>

<script setup>
import { computed } from 'vue';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';

echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

const KB = 1024;
const MB = 1024 ** 2;
const GB = 1024 ** 3;

const props = defineProps({
  session: { type: Object, default: null },
  sessionData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  chartPoints: { type: Array, default: () => [] },
  successor: { type: Object, default: null },
  processing: { type: Boolean, default: false },
  actionNote: { type: String, default: '' },
  confirm: { type: String, default: '' },
  shapeIndex: { type: Number, default: -1 },
  shaperProfiles: { type: Array, default: () => [] },
  durationSeconds: { type: Number, default: 0 },
  blockPreview: { type: Object, default: () => ({}) },
  readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'update:confirm', 'update:shapeIndex', 'confirm-action', 'open-successor', 'request-block']);

const destinationLabel = computed(() => props.sessionData?.dst_host || props.session?.dstIp || props.session?.destIpRaw || '—');
const destPort = computed(() => props.sessionData?.dport || props.session?.dport || '—');
const protoLabel = computed(() => props.sessionData?.proto || props.session?.proto || 'tcp');
const canCut = computed(() => Boolean(props.sessionData?.dstip || props.session?.destIpRaw));
const hostLabel = computed(() => props.sessionData?.hostname || props.session?.srcHost || props.session?.srcUser || 'Host');

const startedLabel = computed(() => {
  const epoch = Number(props.sessionData?.started_at || 0);
  if (!epoch) return '—';
  return new Date(epoch * 1000).toLocaleTimeString('es-CO', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
});

const durationLabel = computed(() => {
  const s = Math.max(0, Math.floor(Number(props.durationSeconds) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
});

const kpis = computed(() => ([
  { label: 'Hora de inicio', value: startedLabel.value },
  { label: 'Duración', value: durationLabel.value },
  { label: 'Puertos', value: `${String(protoLabel.value).toUpperCase()} / ${destPort.value}` },
  { label: 'Subida / TX', value: formatBytes(props.sessionData?.tx_bytes ?? props.session?.txBytes) },
  { label: 'Bajada / RX', value: formatBytes(props.sessionData?.rx_bytes ?? props.session?.rxBytes) },
  { label: 'Aplicación', value: props.sessionData?.app || props.session?.app || '—' },
]));

function formatBytes(bytes) {
  const n = Number(bytes) || 0;
  if (n >= GB) return `${(n / GB).toFixed(2)} GB`;
  if (n >= MB) return `${(n / MB).toFixed(1)} MB`;
  if (n >= KB) return `${(n / KB).toFixed(0)} KB`;
  return `${Math.round(n)} B`;
}

function formatAxisBytes(bytes) {
  const n = Math.round(Number(bytes) || 0);
  if (n >= GB) return `${Math.round(n / GB)} GB`;
  if (n >= MB) return `${Math.round(n / MB)} MB`;
  if (n >= KB) return `${Math.round(n / KB)} KB`;
  return `${n} B`;
}

function display(value) {
  if (value === 0 || value === '0') return '0';
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function formatRate(bps) {
  const n = Number(bps) || 0;
  if (!n) return '—';
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)} Mbps`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)} Kbps`;
  return `${n} bps`;
}

const factGroups = computed(() => {
  const data = props.sessionData || {};
  const row = props.session || {};
  const groups = [
    {
      title: 'Identidad',
      items: [
        { label: 'Equipo', value: display(data.hostname || row.srcHost || row.srcUser) },
        { label: 'Página', value: display(data.dst_host || row.destDomain || row.dstIp) },
        { label: 'Destino IP', value: display(data.dstip || row.destIpRaw) },
        { label: 'País', value: display(data.country || row.country) },
      ],
    },
    {
      title: 'Ruta',
      items: [
        { label: 'Origen → destino', value: `${display(data.sport || row.sport)} → ${display(data.dport || row.dport)}` },
        { label: 'Interfaces', value: (data.srcintf || data.dstintf) ? `${display(data.srcintf)} → ${display(data.dstintf)}` : '—' },
        { label: 'NAT', value: display(data.nat_ip || row.natIp) },
        { label: 'Política', value: display(data.policy || row.policy) },
      ],
    },
    {
      title: 'Volumen',
      items: [
        { label: 'Paquetes TX / RX', value: `${display(data.tx_packets ?? row.txPackets)} / ${display(data.rx_packets ?? row.rxPackets)}` },
        { label: 'Total', value: formatBytes(data.bytes ?? ((data.tx_bytes || 0) + (data.rx_bytes || 0) || (row.txBytes || 0) + (row.rxBytes || 0))) },
        { label: 'Ritmo medio', value: formatRate(data.rate_bps) },
        { label: 'Sesiones en flujo', value: display(data.session_count) },
      ],
    },
  ];
  if (Number(data.tx_bandwidth) || Number(data.rx_bandwidth)) {
    groups[2].items.push({
      label: 'FortiView',
      value: `↑ ${formatRate(data.tx_bandwidth)} · ↓ ${formatRate(data.rx_bandwidth)}`,
    });
  }
  return groups;
});

function startLimit() {
  if (props.shapeIndex < 0 && props.shaperProfiles.length) {
    emit('update:shapeIndex', Math.min(5, props.shaperProfiles.length - 1));
  }
  emit('update:confirm', props.confirm === 'limit' ? '' : 'limit');
}

function niceCeiling(value) {
  const padded = Math.max(Number(value) || 0, 8 * KB) * 1.8;
  const mag = 10 ** Math.floor(Math.log10(padded));
  const step = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10].find((n) => n * mag >= padded) || 10;
  return step * mag;
}

function stablePoints(points) {
  const rows = [];
  for (const point of points) {
    const tx = Number(point.tx || 0);
    const rx = Number(point.rx || 0);
    const prev = rows[rows.length - 1];
    if (prev) {
      const prevTotal = Number(prev.tx || 0) + Number(prev.rx || 0);
      const nextTotal = tx + rx;
      if (prevTotal > 4 * KB && nextTotal < prevTotal * 0.35) continue;
    }
    rows.push(point);
  }
  return rows;
}

const RX_COLOR = '#10b981';
const TX_COLOR = '#6366f1';

const chartOption = computed(() => {
  const points = stablePoints(Array.isArray(props.chartPoints) ? props.chartPoints : []);
  const peak = points.reduce((max, point) => Math.max(max, Number(point.rx || 0), Number(point.tx || 0)), 0);
  const yMax = niceCeiling(peak);
  const interval = yMax / 6;
  const spanMs = Math.max(
    (Number(props.durationSeconds) || 0) * 1000,
    points.length >= 2
      ? (Number(points[points.length - 1].t) - Number(points[0].t)) * 1000
      : 60 * 1000,
  );
  const xMaxInterval = Math.max(Math.floor(spanMs / 12), 5 * 1000);
  return {
    animation: false,
    backgroundColor: 'transparent',
    grid: { top: 30, right: 20, bottom: 30, left: 50 },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        lineStyle: { color: '#94a3b8', width: 1, type: 'dashed' },
        crossStyle: { color: '#94a3b8' },
        label: {
          formatter: (params) => {
            if (params.axisDimension === 'y') return formatAxisBytes(params.value);
            const ts = Number(params.value);
            if (!Number.isFinite(ts)) return '';
            return new Date(ts).toLocaleTimeString('es-CO', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
          },
        },
      },
      backgroundColor: 'rgba(15, 23, 42, 0.92)',
      borderWidth: 0,
      padding: [8, 12],
      textStyle: { color: '#f8fafc', fontSize: 12 },
      valueFormatter: (val) => formatAxisBytes(val),
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      splitNumber: 12,
      maxInterval: xMaxInterval,
      axisLabel: {
        fontSize: 10,
        color: '#94a3b8',
        hideOverlap: false,
        showMinLabel: true,
        showMaxLabel: true,
        formatter: '{HH}:{mm}:{ss}',
      },
      axisLine: { show: false },
      axisTick: { show: true, alignWithLabel: true },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: yMax,
      interval,
      splitNumber: 6,
      axisLabel: {
        fontSize: 10,
        color: '#94a3b8',
        formatter: (val) => formatAxisBytes(val),
      },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } },
    },
    series: [
      {
        name: 'Bajada (RX)',
        type: 'line',
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 3, color: RX_COLOR },
        itemStyle: { color: RX_COLOR },
        emphasis: { focus: 'series' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.35)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0)' },
          ]),
        },
        data: points.map((p) => [Number(p.t) * 1000, Number(p.rx || 0)]),
      },
      {
        name: 'Subida (TX)',
        type: 'line',
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 3, color: TX_COLOR },
        itemStyle: { color: TX_COLOR },
        emphasis: { focus: 'series' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99, 102, 241, 0.28)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0)' },
          ]),
        },
        data: points.map((p) => [Number(p.t) * 1000, Number(p.tx || 0)]),
      },
    ],
  };
});
</script>
