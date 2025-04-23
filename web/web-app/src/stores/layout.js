import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useLayoutStore = defineStore('layout', () => {
  const darkMode = ref(false)
  function toggleDarkMode() {
    darkMode.value = !darkMode.value
    if (darkMode.value) {
      localStorage.setItem('darkMode', 'true')
    } else {
      localStorage.removeItem('darkMode')
    }
  }

  function checkLocalStorage() {
    if (localStorage.getItem('darkMode') === 'true') {
      darkMode.value = true
    } else {
      darkMode.value = false
    }
  }

  const app_version = ref('')
  function setAppVersion(version) {
    app_version.value = version
  }

  const loading = ref(false)
  function setLoading(value) {
    setTimeout(() => {
      loading.value = value
    }, 1000)
  }

  return { darkMode, toggleDarkMode, app_version, setAppVersion, loading, setLoading, checkLocalStorage }
})
