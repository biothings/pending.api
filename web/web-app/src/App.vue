<script setup>
import { RouterView } from 'vue-router'
import { useLayoutStore } from './stores/layout'
import { useAPIStore } from './stores/apis'
import { onMounted } from 'vue'

import Nav from './components/Nav.vue'
import Footer from './components/Footer.vue'

const store = useLayoutStore()
const apiStore = useAPIStore()

onMounted(() => {
  if (location.host.includes('pending')) {
    store.setAppVersion('pending')
  } else {
    store.setAppVersion('translator')
  }
  apiStore.fetchAPIs()
})
</script>

<template>
  <div
    :class="[store.darkMode ? 'dark' : '']"
    class="dark:bg-main-dark bg-main-muted text-main-dark dark:text-main-muted relative"
  >
    <i
      v-if="store.loading"
      class="bi bi-hexagon text-main-medium animate-spin left-1/2 top-1/2 fixed text-8xl z-100"
    ></i>
    <teleport to="head">
      <meta property="og:image" content="https://i.postimg.cc/J4gFsmx0/featured.jpg" />
      <meta
        name="description"
        :content="
          store.app_version == 'pending'
            ? 'APIs pending for integration with core BioThings API'
            : ''
        "
      />
      <title>{{ store.app_version == 'pending' ? 'Pending APIs' : 'Translator KPs' }}</title>
    </teleport>
    <header>
      <Nav />
    </header>
    <main class="min-h-[90vh]">
      <RouterView />
    </main>
    <Footer />
  </div>
</template>
