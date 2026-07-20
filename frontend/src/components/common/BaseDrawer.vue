<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, required: true },
  width: { type: String, default: 'w-[400px]' }
})

const emit = defineEmits(['close'])

const closeOnEscape = (e) => {
  if (e.key === 'Escape' && props.show) {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('keydown', closeOnEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', closeOnEscape)
})
</script>

<template>
  <Teleport to="body">
    <transition name="drawer-fade">
      <div v-if="show" class="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
        <!-- Background backdrop -->
        <div class="absolute inset-0 bg-slate-900/20 backdrop-blur-[2px] transition-opacity" @click="emit('close')"></div>

        <div class="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
          <transition name="drawer-slide" appear>
            <!-- Drawer panel -->
            <div v-if="show" class="pointer-events-auto relative flex flex-col bg-white shadow-2xl" :class="width">
              
              <!-- Header -->
              <div class="flex items-center justify-between px-6 py-5 bg-slate-50 border-b border-slate-200 shrink-0">
                <h3 class="text-base font-semibold text-slate-800">{{ title }}</h3>
                <button @click="emit('close')" class="text-slate-400 hover:text-slate-500 bg-white hover:bg-slate-100 rounded-full p-1.5 transition-colors border border-transparent hover:border-slate-200">
                  <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <!-- Body -->
              <div class="flex-1 overflow-y-auto px-6 py-6 text-sm text-slate-600">
                <slot name="body"></slot>
              </div>

              <!-- Footer -->
              <div v-if="$slots.footer" class="flex items-center justify-end gap-3 px-6 py-4 bg-slate-50 border-t border-slate-200 shrink-0">
                <slot name="footer"></slot>
              </div>

            </div>
          </transition>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.drawer-fade-enter-active, .drawer-fade-leave-active {
  transition: opacity 0.3s ease;
}
.drawer-fade-enter-from, .drawer-fade-leave-to {
  opacity: 0;
}

.drawer-slide-enter-active, .drawer-slide-leave-active {
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.drawer-slide-enter-from, .drawer-slide-leave-to {
  transform: translateX(100%);
}
</style>
