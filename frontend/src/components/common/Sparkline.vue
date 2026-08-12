<template>
  <div class="relative w-full h-full" ref="container">
    <svg class="w-full h-full overflow-visible" preserveAspectRatio="none">
      
      <!-- Line Stroke -->
      <polyline 
        :points="linePoints" 
        fill="none" 
        :stroke="color" 
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="transition-all duration-500 ease-linear drop-shadow-sm"
      />
    </svg>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  color: {
    type: String,
    default: '#10B981'
  },
  min: {
    type: Number,
    default: 0
  },
  max: {
    type: Number,
    default: 100
  }
})
const container = ref(null)
const width = ref(200) // fallback
const height = ref(50) // fallback

let resizeObserver = null

onMounted(() => {
  if (container.value) {
    width.value = container.value.clientWidth
    height.value = container.value.clientHeight
    
    resizeObserver = new ResizeObserver(entries => {
      for (let entry of entries) {
        width.value = entry.contentRect.width
        height.value = entry.contentRect.height
      }
    })
    resizeObserver.observe(container.value)
  }
})

onUnmounted(() => {
  if (resizeObserver && container.value) {
    resizeObserver.unobserve(container.value)
  }
})

const linePoints = computed(() => {
  const d = props.data
  if (!d || d.length === 0) return ''
  
  const stepX = width.value / (Math.max(1, d.length - 1))
  const rangeY = props.max - props.min
  
  return d.map((val, i) => {
    const x = i * stepX
    // Clamping just in case
    const clampedVal = Math.max(props.min, Math.min(props.max, val))
    const y = height.value - ((clampedVal - props.min) / rangeY) * height.value
    return `${x},${y}`
  }).join(' ')
})
</script>
