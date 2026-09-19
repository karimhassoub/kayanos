<template>
  <div class="bg-white shadow rounded-lg">
    <div class="px-4 py-5 sm:px-6 flex justify-between items-center border-b border-gray-200">
      <h3 class="text-lg leading-6 font-medium text-gray-900">Unit Inventory</h3>
      <button class="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium">New Unit</button>
    </div>
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Unit No</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Project</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
            <th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="unit in dummyUnits" :key="unit.id">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ unit.unit_no }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ unit.project }}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ unit.type }}</td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                {{ unit.status }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">{{ unit.price }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
const dummyUnits = [
  { id: 1, unit_no: 'A-101', project: 'Oasis Residences', type: '2 BR Apartment', status: 'Available', price: '$250,000' },
  { id: 2, unit_no: 'A-102', project: 'Oasis Residences', type: '3 BR Apartment', status: 'Reserved', price: '$350,000' },
  { id: 3, unit_no: 'B-205', project: 'Palm Villas', type: '4 BR Villa', status: 'Sold', price: '$850,000' },
]
</script>
