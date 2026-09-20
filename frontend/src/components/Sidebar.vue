<template>
  <div class="w-64 h-screen bg-gray-50 border-r flex flex-col p-4">
    <div class="text-xl font-bold mb-6 text-gray-800">KayanOS</div>
    <nav class="space-y-2 flex-1">
      <router-link to="/" class="block p-2 rounded hover:bg-gray-200 text-gray-700">Home</router-link>
      <router-link to="/account/login" class="block p-2 rounded hover:bg-gray-200 text-gray-700">Login</router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
</script>
