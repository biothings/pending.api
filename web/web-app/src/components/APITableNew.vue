<script setup>
import { ref } from 'vue'
import { useAPIStore } from '@/stores/apis'
import Icon from './Icon.vue'

const apiStore = useAPIStore()
let nameToggle = ref(true)
let typeToggle = ref(true)
let docsToggle = ref(true)

function numberWithCommas(x) {
  if (typeof x !== 'number') return x
  return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function handleSort(field) {
  if (field == 'name') {
    nameToggle.value = !nameToggle.value
    apiStore.sortBy(field, nameToggle.value)
  } else if (field == 'biothing_type') {
    typeToggle.value = !typeToggle.value
    apiStore.sortBy(field, typeToggle.value)
  } else if (field == 'stats.total') {
    docsToggle.value = !docsToggle.value
    apiStore.sortBy(field, docsToggle.value)
  }
}
</script>
<template>
  <table class="text-left w-full bg-gray-100 dark:bg-gray-900 border-collapse">
    <thead class="cursor-pointer">
      <tr class="bg-gray-400 dark:bg-black sticky top-0 z-10">
        <th class="p-1 hover:bg-gray-300 hover:dark:bg-gray-900" @click="handleSort('name')">
          Name
        </th>
        <th class="p-1 hover:bg-gray-300 hover:dark:bg-gray-900" @click="handleSort('stats.total')">
          Documents
        </th>
        <th
          class="p-1 hover:bg-gray-300 hover:dark:bg-gray-900"
          @click="handleSort('biothing_type')"
        >
          Entity Type
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="(api, index) in apiStore.apis"
        :class="index % 2 === 0 ? 'bg-gray-200 dark:bg-gray-900' : 'bg-gray-300 dark:bg-gray-800'"
        :key="api.id"
        class="border-b-indigo-500"
      >
        <td class="p-1">
          <RouterLink class="text-decoration-none dark:text-blue-400" :to="'/' + api.name">{{
            api.name
          }}</RouterLink>
        </td>
        <td class="p-1">{{ numberWithCommas(api.stats?.total) }}</td>
        <td class="p-1">
          <Icon :biotype="api.biothing_type" :key="api.biothing_type"></Icon>
          {{ api.biothing_type }}
        </td>
      </tr>
    </tbody>
  </table>
</template>
