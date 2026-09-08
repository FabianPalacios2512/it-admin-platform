<template>
  <div class="bg-white border border-slate-200 shadow-sm p-4 w-full">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 bg-slate-100 border border-slate-200 flex items-center justify-center">
          <i class="fas fa-ethernet text-slate-600 text-xs"></i>
        </div>
        <div class="flex flex-col">
          <h3 class="text-xs font-semibold text-slate-800">{{ cleanPortName }}</h3>
          <!-- SD-WAN Badge -->
          <div v-if="sdwanLatency !== null || sdwanLoss !== null" class="flex items-center gap-1.5 mt-0.5">
            <span class="text-[9px] font-mono px-1.5 py-0.5 rounded-sm"
              :class="sdwanLatency > 50 ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'">
              {{ sdwanLatency || 0 }}ms
            </span>
            <span class="text-[9px] font-mono px-1.5 py-0.5 rounded-sm"
              :class="sdwanLoss > 0 ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'">
              {{ sdwanLoss || 0 }}% loss
            </span>
          </div>
        </div>
      </div>
      <div class="text-[10px] text-slate-400">Clic en un pico o usa el zoom</div>
    </div>

    <div class="h-44 w-full relative">
      <v-chart
        class="h-full w-full"
        :option="chartOptions"
        autoresize
        @click="onChartClick"
      />
    </div>

    <div class="grid grid-cols-4 gap-2 border-t border-slate-200 pt-2.5 mt-1">
      <div>
        <div class="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">↓ In</div>
        <div class="font-mono text-xs font-semibold text-slate-800">{{ formatKbps(inKbps) }}</div>
      </div>
      <div>
        <div class="text-[10px] font-semibold uppercase tracking-wider text-slate-500">↑ Out</div>
        <div class="font-mono text-xs font-semibold text-slate-800">{{ formatKbps(outKbps) }}</div>
      </div>
      <div>
        <div class="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Max</div>
        <div class="font-mono text-xs font-semibold text-slate-800">{{ formatKbps(Math.max(stats.in.max, stats.out.max)) }}</div>
      </div>
      <div>
        <div class="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Avg</div>
        <div class="font-mono text-xs font-semibold text-slate-800">{{ formatKbps(Math.round((stats.in.avg + stats.out.avg) / 2)) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, DataZoomComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';

use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer]);

const props = defineProps({
  portName: {
    type: String,
    default: 'port1 (WAN)'
  },
  inKbps: {
    type: [Number, String],
    default: 0
  },
  outKbps: {
    type: [Number, String],
    default: 0
  },
  sdwanLatency: {
    type: Number,
    default: null
  },
  sdwanLoss: {
    type: Number,
    default: null
  },
  historyData: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(['audit-at']);

const formatKbps = (val) => {
  if (val == null || isNaN(val)) return '0 Kbps';
  const num = Number(val);
  if (num >= 1000000) return (num / 1000000).toFixed(2) + ' Gbps';
  if (num >= 1000) return (num / 1000).toFixed(2) + ' Mbps';
  if (num % 1 === 0) return num + ' Kbps';
  return num.toFixed(1) + ' Kbps';
};

const cleanPortName = computed(() => {
  return props.portName.replace('()', '').trim();
});

const stats = computed(() => {
  const inSeries = props.historyData.map(d => d.in || 0);
  const outSeries = props.historyData.map(d => d.out || 0);

  const calc = (arr) => {
    if (!arr.length) return { min: 0, max: 0, avg: 0 };
    const min = Math.min(...arr);
    const max = Math.max(...arr);
    const avg = Math.round(arr.reduce((a, b) => a + b, 0) / arr.length);
    return { min, max, avg };
  };

  return {
    in: calc(inSeries),
    out: calc(outSeries)
  };
});

const resolveClock = (point) => {
  if (!point) return null;
  if (point.clock) return Number(point.clock);
  if (!point.time) return null;
  const [hh, mm] = String(point.time).split(':').map(Number);
  if (!Number.isFinite(hh)) return null;
  const now = new Date();
  now.setHours(hh, mm || 0, 0, 0);
  return Math.floor(now.getTime() / 1000);
};

const onChartClick = (params) => {
  const idx = params?.dataIndex;
  if (idx == null || !props.historyData[idx]) return;
  const point = props.historyData[idx];
  const clock = resolveClock(point);
  emit('audit-at', {
    portName: cleanPortName.value,
    timeLabel: point.time || '',
    clock,
    start: clock ? clock - 180 : null,
    end: clock ? clock + 180 : null,
    inKbps: point.in || 0,
    outKbps: point.out || 0
  });
};

const chartOptions = computed(() => {
  const xData = props.historyData.map(d => d.time || '');
  const inSeries = props.historyData.map(d => d.in || 0);
  const outSeries = props.historyData.map(d => d.out || 0);

  return {
    tooltip: {
      trigger: 'axis',
      textStyle: { fontSize: 10 },
      padding: [6, 10],
      formatter: (params) => {
        let res = `<div class="font-bold mb-1">${params[0].name}</div>`;
        params.forEach(p => {
          const color = p.seriesName === 'Download' ? '#10b981' : '#f43f5e';
          res += `<div style="color: ${color}; font-family: monospace; font-size: 11px;">
                    ${p.seriesName}: ${formatKbps(p.value)}
                  </div>`;
        });
        res += `<div style="margin-top:4px;color:#64748b;font-size:10px;">Clic para auditar este momento</div>`;
        return res;
      }
    },
    grid: {
      top: 12,
      bottom: 36,
      left: 12,
      right: 12,
      containLabel: true
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0, filterMode: 'none' },
      {
        type: 'slider',
        height: 16,
        bottom: 4,
        borderColor: '#e2e8f0',
        fillerColor: 'rgba(16,185,129,0.12)',
        handleSize: 12,
        textStyle: { fontSize: 9, color: '#94a3b8' }
      }
    ],
    xAxis: {
      type: 'category',
      data: xData,
      show: true,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 10, margin: 8 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      show: true,
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      min: 0,
      max: (value) => {
        const curMax = Math.max(Number(props.inKbps) || 0, Number(props.outKbps) || 0);
        if (value.max === 0) {
          return curMax > 0 ? Math.ceil(curMax * 1.2) : 1;
        }
        return Math.ceil(Math.max(value.max, curMax) * 1.1);
      },
      axisLabel: { 
        color: '#64748b', 
        fontSize: 9, 
        formatter: (val) => `${val} Kbps`
      },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        name: 'Download',
        type: 'line',
        data: inSeries,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#10b981', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.35)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0)' }
            ]
          }
        }
      },
      {
        name: 'Upload',
        type: 'line',
        data: outSeries,
        smooth: false,
        showSymbol: false,
        lineStyle: { color: '#f43f5e', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(244, 63, 94, 0.28)' },
              { offset: 1, color: 'rgba(244, 63, 94, 0)' }
            ]
          }
        }
      }
    ]
  };
});
</script>
