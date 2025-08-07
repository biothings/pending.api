<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAPIStore } from '@/stores/apis'
import { basicSetup, EditorView } from 'codemirror'
import { EditorState, Compartment } from '@codemirror/state'
import { python } from '@codemirror/lang-python'
import { autocompletion } from '@codemirror/autocomplete'
import { defaultHighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { history } from '@codemirror/commands'

const apiStore = useAPIStore()
const origin = computed(() => window.location.origin)
const editor = ref(null)

let language = new Compartment()
let tabSize = new Compartment()

let text = ref(`from biothings_client import get_client\n
client = get_client(url="${origin.value}/${apiStore.currentAPI}")`)

function getQParam(url) {
  const queryString = url.split('?')[1]
  if (!queryString) return null

  const params = new URLSearchParams(queryString)
  return params.get('q') || null
}

function formatPOSTQuery() {
  const { body, type } = apiStore.querySelected

  if (body?.q) {
    const qterms = Array.isArray(body.q)
      ? '[\n\t' + body.q.map((val) => `"${val}"`).join(',\n\t') + '\n]'
      : JSON.stringify(body.q)

    const scopes = body.scopes
      ? Array.isArray(body.scopes)
        ? '[\n\t' + body.scopes.map((val) => `"${val}"`).join(',\n\t') + '\n]'
        : JSON.stringify(body.scopes)
      : null

    return scopes
      ? `\nclient.querymany(\n  qterms=${qterms},\n  scopes=${scopes}\n)`
      : `\nclient.querymany(\n  qterms=${qterms}\n)`
  }

  if (body?.ids) {
    const ids = Array.isArray(body.ids)
      ? '[\n\t' + body.ids.map((id) => `"${id}"`).join(',\n\t') + '\n]'
      : JSON.stringify(body.ids)

    return `\nclient.get${type}s(${ids})`
  }

  return ''
}

function formatGETQuery() {
  // check for entity query
  if (apiStore.querySelected?.type) {
    let tq = apiStore.querySelected?.query
    console.log(tq)
    // /node/L01XY02
    return `\nclient.get${tq.split('/')[1]}("${tq.split('/')[2]}")`
  }
  let q = getQParam(apiStore.querySelected.query)
  // atc.code:C02LA07
  if (q) {
    // /C02LA07 - atc.code:
    // check if q is quoted or not
    if (q.includes('"')) {
      // atc.code:"C02LA07"
      return `\nclient.query('${q}')`
    } else {
      // atc.code:C02LA07
      return `\nclient.query("${q}")`
    }
  } else {
    return ``
  }
}

function buildQueryText() {
  if (apiStore.querySelected.query) {
    if (apiStore.querySelected.query.includes('/metadata/fields')) {
      return `\nclient.get_fields()`
    } else if (apiStore.querySelected.query.includes('/metadata')) {
      return `\nclient.metadata()`
    }
    if (apiStore.querySelected.method == 'POST') {
      return formatPOSTQuery()
    } else {
      // /query?q=atc.code:C02LA07
      return formatGETQuery()
    }
  }
  return ''
}

onMounted(() => {
  const initialText = text.value + buildQueryText()

  const state = EditorState.create({
    doc: initialText,
    extensions: [
      basicSetup,
      history(),
      autocompletion(),
      language.of(python()),
      tabSize.of(EditorState.tabSize.of(8)),
      syntaxHighlighting(defaultHighlightStyle),
    ],
  })

  editor.value = new EditorView({
    state,
    parent: document.querySelector('#CM'),
  })
})

watch(
  () => apiStore.querySelected,
  (newVal) => {
    if (editor.value) {
      const newText = text.value + buildQueryText()
      editor.value.dispatch({
        changes: {
          from: 0,
          to: editor.value.state.doc.length,
          insert: newText,
        },
      })
    }
  },
)
</script>

<template>
  <p class="mt-2">
    For more information on how to install and use the BioThings Python client click
    <a href="https://pypi.org/project/biothings-client/" target="_blank">here</a>.
  </p>
  <div id="CM" class="bg-light text-left"></div>
</template>
