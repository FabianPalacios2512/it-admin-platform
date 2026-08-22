<template>
  <div class="bg-white border border-slate-100 rounded-xl p-4 shadow-sm w-full">
    <!-- Header -->
    <div class="flex justify-between items-center mb-3">
      <h3 class="text-xs font-bold text-slate-800">{{ portName }}</h3>
      <div class="flex items-center gap-3">
        <span class="text-xs font-mono font-medium text-emerald-500 flex items-center">
          <i class="fas fa-arrow-down mr-1 text-[9px]"></i>{{ inKbps }} Kbps
        </span>
        <span class="text-xs font-mono font-medium text-rose-500 flex items-center">
          <i class="fas fa-arrow-up mr-1 text-[9px]"></i>{{ outKbps }} Kbps
        </span>
      </div>
    </div>

    <!-- ECharts Sparkline -->
    <div class="h-32 w-full relative mb-3">
      <v-chart class="h-full w-full" :option="chartOptions" autoresize />
    </div>

    <!-- Stats Footer -->
    <div class="flex items-center justify-between border-t border-slate-50 pt-3 text-[11px]">
      <!-- Download Stats -->
      <div class="flex items-center gap-4 text-emerald-600">
        <span class="font-bold uppercase tracking-wider text-[10px] hidden sm:inline">Download</span>
        <span title="Mínimo"><span class="text-slate-400 mr-1">Min:</span>{{ stats.in.min }} Kbps</span>
        <span title="Máximo"><span class="text-slate-400 mr-1">Max:</span>{{ stats.in.max }} Kbps</span>
        <span title="Promedio"><span class="text-slate-400 mr-1">Avg:</span>{{ stats.in.avg }} Kbps</span>
      </div>
      <!-- Upload Stats -->
      <div class="flex items-center gap-4 text-rose-600">
        <span class="font-bold uppercase tracking-wider text-[10px] hidden sm:inline">Upload</span>
        <span title="Mínimo"><span class="text-slate-400 mr-1">Min:</span>{{ stats.out.min }} Kbps</span>
        <span title="Máximo"><span class="text-slate-400 mr-1">Max:</span>{{ stats.out.max }} Kbps</span>
        <span title="Promedio"><span class="text-slate-400 mr-1">Avg:</span>{{ stats.out.avg }} Kbps</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';

// Register necessary ECharts modules
use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);

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
  // Array of data points: [ { time: '10:00', in: 15, out: 20 }, ... ]
  historyData: {
    type: Array,
    default: () => []
  }
});

// Computed Stats (Min, Max, Avg)
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

// Configure the Sparkline chart
const chartOptions = computed(() => {
  // Extract times and data arrays for ECharts
  const xData = props.historyData.map(d => d.time || '');
  const inSeries = props.historyData.map(d => d.in || 0);
  const outSeries = props.historyData.map(d => d.out || 0);

  return {
    tooltip: {
      trigger: 'axis',
      textStyle: { fontSize: 10 },
      padding: [4, 8],
      formatter: (params) => {
        let res = `<div class="font-bold mb-1">${params[0].name}</div>`;
        params.forEach(p => {
          const color = p.seriesName === 'Download' ? '#10b981' : '#f43f5e';
          res += `<div style="color: ${color}; font-family: monospace; font-size: 11px;">
                    ${p.seriesName}: ${p.value} Kbps
                  </div>`;
        });
        return res;
      }
    },
    grid: {
      top: 15,
      bottom: 25,
      left: 10,
      right: 15,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      show: true,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 10, margin: 12 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      show: true,
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 10, formatter: '{value} K' },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        name: 'Download',
        type: 'line',
        data: inSeries,
        smooth: false, // Changed from true to false for raw network look
        showSymbol: false,
        lineStyle: {
          color: '#10b981', // Emerald 500
          width: 1.5
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(16, 185, 129, 0.4)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0)' }
            ]
          }
        }
      },
      {
        name: 'Upload',
        type: 'line',
        data: outSeries,
        smooth: false, // Changed from true to false
        showSymbol: false,
        lineStyle: {
          color: '#f43f5e', // Rose 500
          width: 1.5
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(244, 63, 94, 0.4)' },
              { offset: 1, color: 'rgba(244, 63, 94, 0)' }
            ]
          }
        }
      }
    ]
  };
});
</script>
