<template>
  <div class="min-h-screen flex w-full bg-gray-50">
    <!-- Sidebar -->
    <aside class="w-64 bg-white border-r flex flex-col hidden md:flex">
      <div class="h-16 flex items-center px-6 border-b">
        <h1 class="font-bold text-xl text-gray-900">KayanOS</h1>
      </div>
      <nav class="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        <router-link to="/" class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-900 hover:bg-gray-100" active-class="bg-gray-100 font-semibold">
          Dashboard
        </router-link>
        <router-link to="/units" class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900" active-class="bg-gray-100 font-semibold">
          Units
        </router-link>
        <router-link to="/projects" class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900">
          Projects
        </router-link>
        <router-link to="/sales" class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900">
          Sales
        </router-link>
        <router-link to="/customers" class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900">
          Customers
        </router-link>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col min-w-0">
      <header class="h-16 bg-white border-b flex items-center justify-between px-6">
        <div class="text-sm text-gray-500">Workspace</div>
        <div class="flex items-center space-x-4">
          <div class="w-8 h-8 rounded-full bg-gray-200"></div>
        </div>
      </header>
      <div class="flex-1 overflow-y-auto p-6">
        <router-view />
      </div>
    </main>
  </div>
</template>
