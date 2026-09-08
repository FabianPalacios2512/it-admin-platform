<template>
  <div v-if="series.length > 0" class="bg-white rounded-md border border-slate-200 shadow-sm overflow-hidden mb-4">
    <!-- Header & Compact Status -->
    <div class="px-4 py-3 border-b border-slate-100 flex flex-wrap items-center justify-between bg-slate-50 gap-3">
      <div class="flex items-center gap-2">
        <i class="fas fa-route text-slate-400 text-sm"></i>
        <h3 class="text-xs font-semibold text-slate-700">SD-WAN Latency SLA</h3>
      </div>
      
      <!-- Compact Interface Status Pills -->
      <div class="flex flex-wrap items-center gap-2">
        <div 
          v-for="iface in series" 
          :key="iface.name"
          class="flex items-center gap-2 px-2.5 py-1 rounded bg-white border border-slate-200 text-[10px]"
        >
          <span class="w-1.5 h-1.5 rounded-full" :style="{ backgroundColor: getColor(iface.name) }"></span>
          <span class="font-medium text-slate-700">{{ cleanName(iface.name) }}</span>
          
          <div class="flex items-center gap-1.5 border-l border-slate-200 pl-1.5">
            <span v-if="isDown(iface)" class="text-red-500 font-bold" title="Caído">
              <i class="fas fa-arrow-down"></i> DOWN
            </span>
            <span v-else class="text-emerald-500 font-bold" title="Arriba">
              <i class="fas fa-arrow-up"></i> UP
            </span>
            <span class="font-mono text-slate-500">{{ iface.sdwan_latency != null ? iface.sdwan_latency.toFixed(1) + 'ms' : 'N/A' }}</span>
            <span class="font-mono text-slate-400" v-if="iface.sdwan_loss > 0">({{ iface.sdwan_loss.toFixed(0) }}% loss)</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Chart Area (Compact) -->
    <div class="p-2">
      <div class="h-40 w-full relative">
        <v-chart class="h-full w-full" :option="chartOptions" autoresize />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { use } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, MarkLineComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import VChart from 'vue-echarts';

use([LineChart, GridComponent, TooltipComponent, DataZoomComponent, LegendComponent, MarkLineComponent, CanvasRenderer]);

const props = defineProps({
  interfaces: {
    type: Array,
    default: () => []
  }
});

// Colores nítidos, distintos y corporativos para mejor contraste
const colors = ['#f59e0b', '#2563eb', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4'];

const series = computed(() => {
  return props.interfaces.filter(i => (i.sdwan_latency !== null || i.sdwan_loss !== null) && i.sdwan_history && i.sdwan_history.length > 0);
});

function isDown(iface) {
  return iface.sdwan_loss === 100;
}

function cleanName(rawName) {
  const match = rawName.match(/^.*?\((.*?)\)$/);
  return match ? match[1] : rawName;
}

function getColor(name) {
  const index = series.value.findIndex(i => i.name === name);
  return colors[index % colors.length];
}

const chartOptions = computed(() => {
  const activeSeries = series.value;
  if (activeSeries.length === 0) return {};

  const allClocks = new Set();
  const timeMap = {};
  
  activeSeries.forEach(iface => {
    iface.sdwan_history.forEach(pt => {
      allClocks.add(pt.clock);
      timeMap[pt.clock] = pt.time;
    });
  });

  const sortedClocks = Array.from(allClocks).sort();
  const xData = sortedClocks.map(c => timeMap[c]);

  const echartsSeries = activeSeries.map((iface, index) => {
    const data = sortedClocks.map(c => {
      const point = iface.sdwan_history.find(p => p.clock === c);
      return point ? point.latency : null;
    });

    return {
      name: cleanName(iface.name),
      type: 'line',
      data,
      smooth: true,
      showSymbol: false,
      // Líneas mucho más delgadas para mejor comparativa analítica
      lineStyle: { width: 1.2, color: colors[index % colors.length] },
      itemStyle: { color: colors[index % colors.length] },
      connectNulls: true
    };
  });

  return {
    tooltip: {
      trigger: 'axis',
      textStyle: { fontSize: 10, fontFamily: 'ui-sans-serif, system-ui, sans-serif' },
      padding: [6, 10],
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      formatter: (params) => {
        let title = `<div class="font-semibold text-slate-800 mb-1 pb-1 border-b border-slate-100">${params[0].axisValue}</div>`;
        let body = params.map(p => {
          let val = p.value != null ? `<span class="font-mono font-bold text-slate-800">${parseFloat(p.value).toFixed(1)}</span> ms` : 'N/A';
          let marker = `<span style="display:inline-block;margin-right:4px;border-radius:2px;width:8px;height:8px;background-color:${p.color};"></span>`;
          return `<div class="flex items-center gap-2 text-[10px] mb-0.5">
            <div class="flex items-center text-slate-600">${marker} ${p.seriesName}</div> 
            <div class="ml-auto">${val}</div>
          </div>`;
        }).join('');
        return title + body;
      }
    },
    legend: {
      show: false // Ocultamos la leyenda nativa porque ya tenemos los status pills en el header
    },
    grid: {
      left: 0,
      right: 15,
      top: 10,
      bottom: 0,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: false,
      axisLabel: { color: '#94a3b8', fontSize: 9, margin: 8 },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      nameTextStyle: { color: '#94a3b8', fontSize: 9 },
      max: (value) => Math.max(80, Math.ceil(value.max / 10) * 10),
      min: 0,
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { 
        color: '#64748b', 
        fontSize: 9,
        formatter: '{value} ms'
      },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: echartsSeries
  };
});
</script>
