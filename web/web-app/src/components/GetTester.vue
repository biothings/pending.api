<script setup>
import { ref, computed } from 'vue'
import { useAPIStore } from '@/stores/apis'
import { useLayoutStore } from '@/stores/layout'
import axios from 'axios'

const callResults = ref(null)
const apiStore = useAPIStore()
const store = useLayoutStore()
let success = ref(false)
const origin = computed(() => window.location.origin)
let finalURL = ref('')
let queryString = ref('')
let errorEncountered = ref(false)

function testQuery() {
  if (apiStore.currentAPI && apiStore.querySelected.query) {
    queryString.value = '/' + apiStore.currentAPI.toLowerCase() + apiStore.querySelected.query
    finalURL.value = origin.value + queryString.value
    callApi(queryString.value)
  }
}

function callApi(q) {
  if (!callResults.value) return // Ensure ref is available

  callResults.value.innerHTML = '' // Clear previous results
  store.setLoading(true)

  axios
    .get(apiStore.apiUrl + q)
    .then((res) => {
      store.setLoading(false)
      renderjson.set_show_to_level(7)
      callResults.value.innerHTML = '' // Clear previous results
      callResults.value.appendChild(renderjson(res.data)) // Append RenderJSON output
      success.value = true
    })
    .catch((err) => {
      store.setLoading(false)
      renderjson.set_show_to_level(7)
      callResults.value.innerHTML = ''
      callResults.value.appendChild(renderjson(err.response?.data || { error: 'Unknown error' }))
      success.value = true // Needs to be true to show error on UI
      errorEncountered.value = true
      throw err
    })
}
</script>

<template>
  <form @submit.prevent="testQuery()" class="d-flex justify-start align-items-center mt-3">
    <button
      class="btn"
      :class="[apiStore.querySelected ? 'main-btn' : 'btn-outline-secondary']"
      :disabled="!apiStore.querySelected"
      type="submit"
    >
      Send Request
    </button>
    <p class="text-left m-0 pl-4" v-if="success && queryString" style="word-break: break-all">
      <i class="fas mr-1 text-lime-400" :class="[success ? 'fa-check' : 'fa-circle']"></i>
      <a
        rel="noopener"
        target="_blank"
        :href="finalURL"
        v-text="finalURL"
        type="text"
        :style="{ color: success && !errorEncountered ? 'limegreen' : 'coral' }"
      ></a>
    </p>
  </form>
  <pre
    v-show="success"
    ref="callResults"
    class="p-2 text-left mt-1 mb-4 dark:bg-slate-900"
    style="
      font-size: 1em !important;
      max-height: 800px;
      min-height: 800px;
      overflow: scroll;
      border-style: inset;
      border: 3px #501cbe solid;
      border-radius: 5px;
    "
  ></pre>
</template>
