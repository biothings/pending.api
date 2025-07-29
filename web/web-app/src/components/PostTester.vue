<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useAPIStore } from '@/stores/apis'
import { useLayoutStore } from '@/stores/layout'
import { basicSetup, EditorView } from 'codemirror'
import { EditorState, Compartment } from '@codemirror/state'
import { json } from '@codemirror/lang-json'
import { autocompletion } from '@codemirror/autocomplete'
import axios from 'axios'
import { defaultHighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { history } from '@codemirror/commands'
import Toastify from 'toastify-js'

const apiStore = useAPIStore()
const store = useLayoutStore()
const editor = ref(null)
const callResults = ref(null)
let success = ref(false)
let postURL = ref('')
let errorEncountered = ref(false)
const origin = computed(() => window.location.origin)
const displayURL = ref('')
let language = new Compartment()
let tabSize = new Compartment()

function generatePostURL() {
  if (apiStore.currentAPI && apiStore.querySelected) {
    postURL.value = `${apiStore.apiUrl}/${apiStore.currentAPI.toLowerCase()}${apiStore.querySelected.query}`
    displayURL.value = `${origin.value}/${apiStore.currentAPI.toLowerCase()}${apiStore.querySelected.query}`
  }
}

onMounted(() => {
  generatePostURL()

  const state = EditorState.create({
    doc: JSON.stringify(apiStore.querySelected.body, null, 2),
    extensions: [
      basicSetup,
      history(),
      autocompletion(),
      language.of(json()),
      tabSize.of(EditorState.tabSize.of(8)),
      syntaxHighlighting(defaultHighlightStyle),
    ],
  })

  editor.value = new EditorView({
    state,
    parent: document.querySelector('#CMPOST'),
  })
})

watch(
  () => apiStore.querySelected,
  (newVal) => {
    generatePostURL()
    if (editor.value) {
      editor.value.dispatch({
        changes: {
          from: 0,
          to: editor.value.state.doc.length,
          insert: JSON.stringify(apiStore.querySelected.body, null, 2),
        },
      })
    }
  },
)

function validateQuery(body) {
  const showError = (message) => {
    Toastify({
      text: message,
      duration: 3000,
      close: true,
      gravity: 'top',
      position: 'right',
      stopOnFocus: true,
      style: {
        background: 'linear-gradient(to right, #7209b6, #a50202)',
      },
      onClick: function () {},
    }).showToast()
  }

  function isUnderSizeLimit(obj) {
    const jsonString = JSON.stringify(obj)
    const byteSize = new TextEncoder().encode(jsonString).length
    return byteSize < 1300 ? 'T' : 'F'
  }

  // Check if the body is under 1300 bytes
  if (!isUnderSizeLimit(body)) {
    showError('Query body exceeds 1300 bytes limit.')
    return false
  }

  // Check if body is an object
  if (!body || typeof body !== 'object') {
    showError('Invalid query body.')
    return false
  }

  // Check body has at least one of 'q' or 'ids'
  const hasQ = 'q' in body
  const hasIds = 'ids' in body

  if (!hasQ && !hasIds) {
    showError("Request body must include either 'q' or 'ids'.")
    return false
  }

  //check if q is an array and if so it's under 100 items
  if (hasQ && Array.isArray(body.q) && body.q.length > 100) {
    showError("If 'q' is an array, it must contain 100 or fewer items.")
    return false
  }

  // check if ids is an array and if so it's under 100 items
  if (hasIds && Array.isArray(body.ids) && body.ids.length > 100) {
    showError("If 'ids' is an array, it must contain 100 or fewer items.")
    return false
  }

  // check for not allowed keys
  let invalidKeys = checkNotAllowedKeys(body)
  if (invalidKeys.length > 0) {
    showError(`Invalid keys in request body: '${JSON.stringify(invalidKeys)}'.`)
    return false
  }

  return true
}

function checkNotAllowedKeys(body) {
  const allowedKeys = [
    'q',
    'ids',
    'scopes',
    'fields',
    'species',
    'size',
    'from',
    'fetch_all',
    'scroll_id',
    'sort',
    'facets',
    'facet_size',
    'species_facet_filter',
    'callback',
    'dotfield',
    'filter',
    'limit',
    'skip',
    'email',
  ]
  let invalidKeys = []
  for (const key in body) {
    if (!allowedKeys.includes(key)) {
      invalidKeys.push(key)
    }
  }
  return invalidKeys
}

function testQuery() {
  errorEncountered.value = false
  success.value = false
  callResults.value.innerHTML = '' // Clear previous results
  if (apiStore.currentAPI && apiStore.querySelected) {
    callApi()
  }
}

function callApi() {
  if (!callResults.value) return // Ensure ref is available

  callResults.value.innerHTML = '' // Clear previous results
  store.setLoading(true)

  let requestBodyFromEditor
  try {
    const raw = editor.value.state.doc.toString()
    requestBodyFromEditor = JSON.parse(raw)
  } catch (err) {
    store.setLoading(false)
    errorEncountered.value = true
    callResults.value.innerHTML = '⚠️ Error: Invalid JSON in editor'
    return
  }

  let valid = validateQuery(requestBodyFromEditor)
  if (!valid) {
    store.setLoading(false)
    errorEncountered.value = true
    callResults.value.innerHTML = '⚠️ Error: Invalid query body'
    return
  }
  axios
    .post(postURL.value, requestBodyFromEditor, {
      headers: {
        'Content-Type': 'application/json',
      },
    })
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
  <div class="mt-2">
    <div>
      <form
        @submit.prevent="testQuery()"
        class="mt-1 d-flex justify-start align-items-center w-full"
      >
        <button
          class="btn m-1"
          :class="[apiStore.querySelected ? 'main-btn' : 'btn-outline-secondary']"
          :disabled="!apiStore.querySelected"
          type="submit"
        >
          Send Request
        </button>
        <input
          disabled
          type="text"
          :value="displayURL"
          class="col-sm-8 bg-gray-200 dark:bg-gray-900 p-1 rounded pl-4"
        />
      </form>
    </div>
    <small>Request Body:</small>
    <div
      id="CMPOST"
      class="bg-light text-left"
      style="border-style: inset; border: 3px #501cbe solid; border-radius: 5px"
    ></div>
    <small>Results:</small>
    <pre
      ref="callResults"
      class="p-2 text-left mt-1 mb-4 dark:bg-slate-900"
      style="
        font-size: 1em !important;
        max-height: 400px;
        min-height: 400px;
        overflow: scroll;
        border-style: inset;
        border: 3px #501cbe solid;
        border-radius: 5px;
      "
    ></pre>
  </div>
</template>
