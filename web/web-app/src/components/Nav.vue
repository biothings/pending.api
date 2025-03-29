<script setup>
import { useLayoutStore } from '../stores/layout'
import { useAPIStore } from '../stores/apis'
import { watch } from 'vue'
import router from '@/router'
const layout = useLayoutStore()
const store = useAPIStore()

watch(
  () => store.query,
  (query) => {
    if (query && store.list.includes(query)) {
      router.push('/try/' + query)
    }
  },
)

function handleSubmit() {
  if (store.query) {
    router.push('/try/' + query)
  }
}
</script>

<template>
  <nav
    id="nav"
    class="navbar bg-linear-to-r from-main-medium to-main-dark dark:from-main-dark dark:to-main-medium navbar-expand-lg w-100 p-2 px-4"
  >
    <template v-if="layout.app_version == 'pending'">
      <RouterLink class="navbar-brand bold main-font text-theme-light" to="/">
        <img src="@/assets/img/infinity.svg" alt="Pending" width="50px" /> Pending
      </RouterLink>
    </template>
    <template v-else>
      <RouterLink class="navbar-brand border border-white" to="/"
        ><img class="w-[50px]" alt="Translator" src="@/assets/img/tr.jpg"
      /></RouterLink>
    </template>
    <div class="ml-auto">
      <form class="form-inline d-flex mr-4" @submit="handleSubmit">
        <label for="api_select" class="text-main-accent mr-2">Switch to</label>
        <input
          list="apis"
          id="api_select"
          placeholder="Enter API Name"
          name="api_select"
          class="bg-main-accent dark:placeholder:text-main-light border-0 text-theme-dark pl-2"
          v-model="store.query"
        />
        <datalist id="apis">
          <option v-for="api in store.apis" :key="api.name" :value="api.name"></option>
        </datalist>
      </form>
    </div>
    <button @click="layout.toggleDarkMode" class="btn btn-sm btn-outline-light">
      <i class="bi bi-sun-fill" v-if="!layout.darkMode"></i>
      <i class="bi bi-moon-stars-fill" v-else></i>
    </button>
  </nav>
</template>
