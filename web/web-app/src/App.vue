<script setup>
import { RouterView } from 'vue-router'
import { useLayoutStore } from './stores/layout'
import { useAPIStore } from './stores/apis'
import { onMounted, onBeforeUnmount, ref } from 'vue'

import Nav from './components/Nav.vue'
import Footer from './components/Footer.vue'

const store = useLayoutStore()
const apiStore = useAPIStore()

onMounted(() => {
  store.checkLocalStorage()
  if (location.host.includes('pending')) {
    store.setAppVersion('pending')
  } else {
    store.setAppVersion('translator')
  }
  apiStore.fetchAPIs()

  document.addEventListener('keydown', handleKeydown)
})

const inputs = ref([])
let currentIndex = -1

function updateInputs() {
  // Grab all focusable inputs, textareas, selects, and buttons
  inputs.value = Array.from(document.querySelectorAll('input, textarea, select, button')).filter(
    (el) => !el.disabled && el.tabIndex !== -1,
  )
}

function handleKeydown(event) {
  if (event.key !== 'Tab') return

  event.preventDefault()

  updateInputs()

  if (inputs.value.length === 0) return

  const active = document.activeElement
  currentIndex = inputs.value.indexOf(active)

  // Handle Shift+Tab for reverse direction
  const direction = event.shiftKey ? -1 : 1
  const nextIndex = (currentIndex + direction + inputs.value.length) % inputs.value.length

  inputs.value[nextIndex].focus()
}

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
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
