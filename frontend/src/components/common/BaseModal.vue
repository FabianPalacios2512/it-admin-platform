<script setup>
import { onMounted, onUnmounted } from 'vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, required: true }
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
    <transition name="modal-fade">
      <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/20 backdrop-blur-[2px] p-4" @click.self="emit('close')">
        <transition name="modal-scale" appear>
          <div class="bg-white w-full max-w-lg rounded-xl shadow-lg border border-gray-100 overflow-hidden flex flex-col max-h-[90vh] relative">
            
            <!-- Header -->
            <div class="px-6 py-4 border-b border-gray-100 flex items-center">
              <h2 class="text-lg font-semibold text-gray-900">{{ title }}</h2>
              <button @click="emit('close')" class="absolute right-6 top-4 text-gray-400 hover:text-gray-600 transition-colors p-1 rounded-full">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <!-- Body -->
            <div class="p-6 text-gray-600 text-sm overflow-y-auto">
              <slot name="body"></slot>
            </div>
            
            <!-- Footer -->
            <div v-if="$slots.footer" class="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
              <slot name="footer"></slot>
            </div>
          </div>
        </transition>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.25s ease-out;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}

.modal-scale-enter-active {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.modal-scale-leave-active {
  transition: all 0.2s ease-in;
}
.modal-scale-enter-from, .modal-scale-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}
</style>
