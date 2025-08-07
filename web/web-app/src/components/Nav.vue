<script setup>
import { useLayoutStore } from '../stores/layout'
import { useAPIStore } from '../stores/apis'
import { watch, computed, ref } from 'vue'
import router from '@/router'
const layout = useLayoutStore()
const store = useAPIStore()
const localQuery = ref('')

watch(
  () => localQuery.value,
  (query) => {
    if (query && store.list.includes(query)) {
      router.push('/' + query)
    }
  },
)

let results = computed(() => {
  if (localQuery.value) {
    return store.list.filter((api) => api.toLowerCase().includes(localQuery.value.toLowerCase()))
  } else {
    return store.list
  }
})

function handleSubmit() {
  if (store.query) {
    router.push('/' + query)
  }
}

function handleClick(api) {
  localQuery.value = ''
  store.setQuery(api)
  store.setCurrentAPI(api)
  router.push('/' + api)
}
</script>
<template>
  <nav
    id="nav"
    class="navbar bg-linear-to-r from-main-medium to-main-dark dark:from-main-dark dark:to-main-medium navbar-expand-lg w-100 p-2 px-4"
  >
    <template v-if="layout.app_version == 'pending'">
      <RouterLink
        class="navbar-brand bold main-font text-theme-light d-flex align-items-center justify-center text-white"
        to="/"
      >
        <img src="@/assets/img/infinity.svg" alt="Pending" width="50px" /> Pending
      </RouterLink>
    </template>
    <template v-else>
      <RouterLink class="navbar-brand" to="/"
        ><img class="w-[50px] rounded" alt="Translator" src="@/assets/img/tr.jpg"
      /></RouterLink>
    </template>
    <div class="ml-auto">
      <form class="form-inline d-flex mr-4 relative" @submit="handleSubmit">
        <label for="api_select" class="text-white mr-2">Switch to</label>
        <input
          list="apis"
          id="api_select"
          placeholder="Enter API Name"
          name="api_select"
          class="bg-white dark:placeholder:text-main-light focus:outline-2 focus:outline-offset-2 focus:outline-violet-500 border-0 text-theme-dark pl-2 caret-pink-500"
          v-model="localQuery"
          autocomplete="off"
        />
        <ul
          v-if="localQuery && results.length"
          class="absolute top-8 left-20 bg-violet-100 dark:bg-main-dark max-h-[500px] z-400 overflow-scroll m-0 p-1 text-sm cursor-pointer shadow hidden sm:inline rounded"
        >
          <li
            v-for="api in results"
            @click="handleClick(api)"
            :key="api"
            class="p-0 hover:bg-main-medium hover:text-white"
          >
            {{ api }}
          </li>
        </ul>
      </form>
    </div>
    <button @click="layout.toggleDarkMode" class="btn btn-sm btn-outline-light">
      <i class="bi bi-sun-fill" v-if="!layout.darkMode"></i>
      <i class="bi bi-moon-stars-fill" v-else></i>
    </button>
  </nav>
</template>
