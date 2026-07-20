<script setup>
import ModalWrapper from './BaseModal.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, required: true },
  description: { type: String, required: true },
  confirmText: { type: String, default: 'Confirmar' },
  cancelText: { type: String, default: 'Cancelar' },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'confirm'])
</script>

<template>
  <ModalWrapper :show="show" :title="title" @close="emit('close')">
    <template #body>
      <div class="flex items-start gap-4">
        <div class="flex-shrink-0 w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
          <svg class="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div class="pt-1">
          <p class="text-sm text-gray-500 leading-relaxed">{{ description }}</p>
        </div>
      </div>
    </template>
    
    <template #footer>
      <button @click="emit('close')" :disabled="loading" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors disabled:opacity-50">
        {{ cancelText }}
      </button>
      <button @click="emit('confirm')" :disabled="loading" class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors flex items-center gap-2 disabled:opacity-50">
        <span v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
        {{ confirmText }}
      </button>
    </template>
  </ModalWrapper>
</template>
