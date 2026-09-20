<template>
  <div class="flex h-screen overflow-hidden bg-white text-gray-900">
    <Sidebar />
    <div class="flex-1 overflow-auto bg-gray-50 p-6">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
</script>
