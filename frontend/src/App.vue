<template>
  <router-view />
  <GlobalToaster />
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import GlobalToaster from '@/components/common/GlobalToaster.vue'
import { useTasks } from '@/composables/useTasks'

const { startPolling, stopPolling } = useTasks()

onMounted(() => {
  const adminUsername = localStorage.getItem('display_name') || 'Sistema'
  startPolling(adminUsername)
})

onUnmounted(() => {
  stopPolling()
})
</script>
