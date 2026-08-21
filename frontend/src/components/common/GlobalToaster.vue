<template>
  <div class="fixed bottom-5 right-5 z-50 flex flex-col gap-3 pointer-events-none">
    <TransitionGroup name="toast" tag="div" class="flex flex-col gap-3">
      <div 
        v-for="notif in notifications" 
        :key="notif.id"
        class="pointer-events-auto max-w-sm w-80 bg-white rounded-lg shadow-[0_8px_30px_rgb(0,0,0,0.12)] border border-slate-100 overflow-hidden flex items-start"
      >
        <!-- Icon Side -->
        <div 
          class="flex-shrink-0 w-12 self-stretch flex items-center justify-center"
          :class="notif.type === 'error' ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'"
        >
          <i v-if="notif.type === 'error'" class="fas fa-exclamation-circle text-lg"></i>
          <i v-else class="fas fa-check-circle text-lg"></i>
        </div>
        
        <!-- Content -->
        <div class="px-4 py-3 flex-1">
          <h4 class="text-[13px] font-bold text-slate-800 mb-0.5">{{ notif.title }}</h4>
          <p class="text-[11px] text-slate-500 leading-tight">{{ notif.message }}</p>
        </div>

        <!-- Close Button -->
        <button 
          @click="removeNotification(notif.id)" 
          class="p-3 text-slate-300 hover:text-slate-500 transition-colors"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useTasks } from '@/composables/useTasks'

const { notifications, removeNotification } = useTasks()
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}
</style>
