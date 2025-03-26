import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useLayoutStore = defineStore('layout', () => {
  const darkMode = ref(false)
  function toggleDarkMode() {
    darkMode.value = !darkMode.value;
  }

  const app_version = ref("");
  function setAppVersion(version) {
    app_version.value = version;
  }

  const loading = ref(false);
  function setLoading(value) {
    loading.value = value;
  }

  return { darkMode, toggleDarkMode, app_version, setAppVersion, loading, setLoading }
});
