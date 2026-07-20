<script setup>
defineProps({
  user: {
    type: Object,
    required: true
  }
})
</script>

<template>
  <div class="user-card">
    <h3>{{ user.name }}</h3>
    <span :class="user.status">{{ user.status }}</span>
  </div>
</template>

<style scoped>
.user-card {
  border: 1px solid #ddd;
  padding: 15px;
  border-radius: 8px;
}
</style>
