<script setup>
const props = defineProps({
  title: { type: String, required: true },
  value: { type: String, required: true },
  description: { type: String, default: '' },
  trend: { type: String, default: '' },
  trendUp: { type: Boolean, default: true },
  icon: { type: String, default: 'monitor' },
  accentColor: { type: String, default: 'blue' },
  sparkline: { type: Array, default: () => [] },
})

const icons = {
  monitor: 'M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  lock: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z',
  server: 'M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2',
}

const accentStyles = {
  blue:    { bg: 'bg-blue-50',    text: 'text-blue-600',    icon: 'text-blue-500'    },
  red:     { bg: 'bg-red-50',     text: 'text-red-600',     icon: 'text-red-500'     },
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600', icon: 'text-emerald-500' },
}

const accent = accentStyles[props.accentColor] || accentStyles.blue

// Generar path SVG del sparkline
function getSparklinePath(data, width = 120, height = 32) {
  if (!data || data.length < 2) return ''
  const max = Math.max(...data)
  const min = Math.min(...data)
  const range = max - min || 1
  const step = width / (data.length - 1)

  return data
    .map((val, i) => {
      const x = i * step
      const y = height - ((val - min) / range) * (height - 4) - 2
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-lg shadow-none flex flex-col hover:border-slate-300 transition-colors duration-200">
    <!-- Header -->
    <div class="flex items-center justify-between px-5 pt-4 pb-2">
      <div class="flex items-center gap-2.5">
        <div :class="['flex items-center justify-center w-8 h-8 rounded-md', accent.bg]">
          <svg :class="['w-4 h-4', accent.icon]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" :d="icons[icon] || icons.monitor" />
          </svg>
        </div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-wide">{{ title }}</span>
      </div>

      <!-- Trend badge -->
      <span
        v-if="trend"
        :class="[
          'inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full',
          trendUp
            ? 'text-emerald-700 bg-emerald-50'
            : 'text-red-700 bg-red-50'
        ]"
      >
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" :d="trendUp ? 'M5 15l7-7 7 7' : 'M19 9l-7 7-7-7'" />
        </svg>
        {{ trend }}
      </span>
    </div>

    <!-- Value + Sparkline -->
    <div class="flex items-end justify-between px-5 pb-4">
      <div>
        <span class="text-3xl font-bold text-slate-900 tracking-tight leading-none">{{ value }}</span>
        <p class="text-[11px] text-slate-600 mt-1.5">{{ description }}</p>
      </div>

      <!-- Mini sparkline chart -->
      <div v-if="sparkline.length > 1" class="w-[120px] h-[32px] opacity-60">
        <svg viewBox="0 0 120 32" class="w-full h-full" preserveAspectRatio="none">
          <path
            :d="getSparklinePath(sparkline)"
            fill="none"
            :stroke="trendUp ? '#10b981' : '#ef4444'"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    </div>
  </div>
</template>
