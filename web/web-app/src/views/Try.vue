<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAPIStore } from '@/stores/apis'
import { useLayoutStore } from '@/stores/layout'
import axios from 'axios'
import { isPlainObject, isArray, isBoolean, isNumber, isString } from 'lodash'
import { useRoute } from 'vue-router'

import SourceInfo from '@/components/SourceInfo.vue'
import mygene from '@/assets/img/mygene-text.svg'
import myvariant from '@/assets/img/myvariant-text.svg'
import mychem from '@/assets/img/mychem-text.svg'
import mydisease from '@/assets/img/mydisease-text.png'
import Icon from '@/components/Icon.vue'

let metadata = ref(null)
let numberOfDocs = ref(0)
let type = ref(null)
let querySelectionType = ref('example')
let exampleQueries = ref(['/metadata', '/metadata/fields'])
let querySelected = ref('')
let queryString = ref('')
let loadingExamplesQueries = ref(false)
let errorEncountered = ref(false)
let finalURL = ref('')
let success = ref(false)
const callResults = ref(null)

let existingEntity = false
let validAPI = true
let numberOfExamples = 8

const host = computed(() => window.location.host)
const multiSource = computed(() => (Object.keys(metadata.value.src).length > 1 ? true : false))
let sourceDetails = computed(() => {
  try {
    return metadata.value.src[getKeyName(metadata.value.src)]
  } catch (e) {
    return {}
  }
})
let author_url = computed(() => sourceDetails?.author?.url)
let description = computed(() => sourceDetails?.description)

const apiStore = useAPIStore()
const store = useLayoutStore()

let props = defineProps({
  api: String,
})

function numberWithCommas(total) {
  if (total) {
    return total.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  } else {
    return 'N/A'
  }
}

function getMetadata() {
  let safeList = ['gene', 'chemical', 'variant', 'disease']
  let url = apiStore.apiUrl + '/' + props.api + '/metadata'
  console.log(url)
  axios
    .get(url)
    .then((res) => {
      metadata.value = res.data
      numberOfDocs.value = metadata.value?.stats?.total
      if (metadata.value?.biothing_type) {
        type.value = metadata.value.biothing_type
        if (safeList.includes(metadata.value['biothing_type'])) {
          existingEntity = true
        }
      }
      generateTestQueriesStart()
    })
    .catch((err) => {
      validAPI = false
      throw err
    })
}

function randomNumber(max) {
  let number = Math.floor(Math.random() * max) + 1
  return number
}

function generateQuery(dataObject) {
  if (dataObject && dataObject.hasOwnProperty('_id')) {
    let id = dataObject['_id']
    let query = '/' + type.value + '/' + id
    exampleQueries.value.push(query)
  }
}

function randomProperty(obj) {
  if (isPlainObject(obj)) {
    var keys = Object.keys(obj)
    if (keys.includes('_id')) {
      var index = keys.indexOf('_id')
      if (index > -1) {
        keys.splice(index, 1)
      }
    }
    if (keys.includes('_score')) {
      var index = keys.indexOf('_score')
      if (index > -1) {
        keys.splice(index, 1)
      }
    }
    let rdmKeyIndex = (keys.length * Math.random()) << 0
    if (typeof obj[keys[rdmKeyIndex]] == 'string' && obj[keys[rdmKeyIndex]].includes('http')) {
      console.warn('Skipped URL value: ', obj[keys[rdmKeyIndex]])
      return false
    } else {
      return keys[rdmKeyIndex]
    }
  } else {
    return false
  }
}

function handleStringValue(string) {
  //check values to be skipped first
  if (string.length > 50) {
    // value is too long
    console.warn('Skipped long value:')
    console.warn('%c ' + string, 'color:purple')
    return false
  } else if (string.includes('>') || string.includes('<')) {
    // ES cannot escape these characters
    console.warn('Skipped unescapable ES characters:')
    console.warn('%c ' + string, 'color:pink')
    return false
  }
  //quote spaces
  else if (string.includes(' ')) {
    if (string.includes('"')) {
      console.warn('Skipped value with quotes')
      console.warn('%c ' + string, 'color:pink')
      return false
    } else {
      return `"${string}"`
    }
  }
  //escape colons
  if (string.includes(':')) {
    return string.replaceAll(':', '\\:')
  }
  //escape backslashes
  else if (string.includes('\\')) {
    return string.replaceAll('\\', '\\\\')
  } else {
    return string
  }
}

function getQueryString(obj) {
  let string = randomProperty(obj)

  if (string) {
    if (isPlainObject(obj[string])) {
      let value = getQueryString(obj[string])
      if (value) {
        string += '.' + value
      } else {
        return false
      }
    } else if (isArray(obj[string])) {
      if (obj[string].length > 0) {
        if (typeof obj[string][0] == 'string') {
          let value = handleStringValue(obj[string][0])
          if (value) {
            string += ':' + value
          } else {
            return false
          }
        } else {
          let value = getQueryString(obj[string][0])
          if (value) {
            string += '.' + value
          } else {
            return false
          }
        }
      } else {
        console.warn("Can't generate query from empty array in field:")
        console.warn('%c ' + JSON.stringify(obj, null, 2), 'color:orange')
        return false
      }
    } else if (isBoolean(obj[string])) {
      string += ':' + obj[string]
    } else if (isNumber(obj[string])) {
      if (parseInt(obj[string]) < 0) {
        string += `:"${obj[string]}"`
      } else {
        string += ':' + obj[string]
      }
    } else if (isString(obj[string])) {
      let value = handleStringValue(obj[string])
      if (value) {
        string += ':' + value
      } else {
        return false
      }
    }
    return string
  }
}

function generateTestQueriesStart() {
  // console.log("🤖 Generate queries")
  loadingExamplesQueries.value = true
  // testing only: numberOfDocs will be null so set to 100
  let docNumberLimit = numberOfDocs.value ? numberOfDocs.value : 100
  let limit = Math.floor(Math.random() * 10000)
  let size = 100

  if (limit) {
    if (limit > docNumberLimit) {
      limit = docNumberLimit - 100
    }
    if (docNumberLimit < 100) {
      limit = 0
    }
    axios
      .get(
        apiStore.apiUrl +
          '/' +
          props.api.toLowerCase() +
          '/query?q=__all__&from=' +
          limit +
          '&size=' +
          size,
      )
      .then((result) => {
        let res = result.data.hits
        let i = 0
        let picks = []
        //make query string query
        generateQuery(res[randomNumber(size)])
        while (i < numberOfExamples) {
          let doc = res[randomNumber(size)]
          picks.push(doc)
          i++
        }
        let problematic = []
        for (var picksIndex = 0; picksIndex < picks.length; picksIndex++) {
          let value = getQueryString(picks[picksIndex])
          if (value) {
            let query = '/query?q=' + value
            //excludes duplicates and results with undefined terms
            if (!exampleQueries.value.includes(query) && !query.includes('undefined')) {
              exampleQueries.value.push(query)
            } else {
              problematic.push(query)
            }
          }
        }
        if (problematic.length) {
          console.warn('Skipped duplicate or undefined queries: ')
          console.warn('%c ' + JSON.stringify(problematic, null, 2), 'color:hotpink')
        }
      })
      .catch((err) => {
        console.log('Error loading examples')
        loadingExamplesQueries.value = false
        throw err
      })
  }

  setTimeout(function () {
    loadingExamplesQueries.value = false
  }, 1000)
}

function getKeyName(obj) {
  for (var key in obj) {
    if (key !== 'src_version') {
      return key
    }
  }
}

function refreshExamples() {
  exampleQueries.value = ['/metadata', '/metadata/fields']
  generateTestQueriesStart()
}

function testQuery() {
  if (props.api && querySelected.value) {
    queryString.value = '/' + props.api.toLowerCase() + querySelected.value
    finalURL.value = queryString.value
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

onMounted(() => {
  getMetadata()
})

const route = useRoute()

watch(
  () => route.params.api,
  () => {
    console.log('API changed')
    apiStore.setQuery('')
    refreshExamples()
    getMetadata()
  },
)
</script>

<template>
  <section id="try-app" class="min-height-100">
    <div v-if="validAPI" class="p-2 text-left bg-gray-200 dark:bg-gray-900">
      <h2
        class="main-font ml-5 text-main-dark dark:text-white"
        style="overflow-wrap: break-word"
        :data-text="api"
        v-text="api.split('_').join(' ')"
      ></h2>
    </div>
    <div
      v-if="validAPI"
      class="m-0 min-height-100 d-flex justify-content-start align-items-stretch"
    >
      <div
        v-if="metadata && metadata.src"
        class="shadow bg-gray-300 dark:bg-main-medium p-4 col-sm-12 col-md-3 col-lg-2"
      >
        <div class="text-left">
          <p v-if="!existingEntity" class="m-0">
            <small>Entity Type: </small>
            <template v-if="metadata?.biothing_type">
              <strong>
              <Icon :biotype="metadata?.biothing_type" /> {{ metadata.biothing_type }}</strong>
            </template>
          </p>
          <small class="mt-1" v-if="numberOfDocs">
            {{ numberWithCommas(numberOfDocs) + ' documents' }}
          </small>
        </div>
        <template v-if="author_url">
          <small class="d-block mt-2">
            Developed by
            <a rel="noopener" :href="author_url" target="_blank">
              <i class="fab fa-github"></i>
              <span v-text="metadata.src[getKeyName(metadata.src)]['author']['name']"></span>
              <i class="fas fa-external-link-square-alt"></i>
            </a>
          </small>
        </template>
        <small class="m-0 mt-3" v-if="multiSource">Data Sources:</small>
        <div class="d-flex justify-content-center align-items-start flex-wrap">
          <SourceInfo
            v-for="(info, name) in metadata.src"
            :key="name"
            :class="[multiSource ? 'source-box p-2' : 'p-0']"
            class="my-1 col-sm-12"
            :info="info"
            :name="name"
            :multiSource="multiSource"
          ></SourceInfo>
        </div>
        <div class="p-1" v-if="description && !multiSource">
          <small class="d-block mt-2" v-html="description"></small>
        </div>
        <div v-if="existingEntity" class="text-left mt-5">
          <small>Pending for integration with:</small>
          <div v-if="metadata.biothing_type" class="badge bg-gray-200 dark:bg-gray-800 d-block p-1 m-2">
            <a
              v-if="metadata.biothing_type === 'gene'"
              href="https://mygene.info/"
              target="_blank"
              rel="noopener"
            >
              <img :src="mygene" alt="myGene" height="20px" />
            </a>
            <a
              v-if="metadata.biothing_type === 'variant'"
              href="https://myvariant.info"
              target="_blank"
              rel="noopener"
            >
              <img :src="myvariant" alt="myVariant" height="20px" />
            </a>
            <a
              v-if="metadata.biothing_type === 'chemical'"
              href="https://mychem.info"
              target="_blank"
              rel="noopener"
            >
              <img :src="mychem" alt="myChem" height="20px" />
            </a>
            <a
              v-if="metadata.biothing_type === 'disease'"
              href="http://mydisease.info/"
              target="_blank"
              rel="noopener"
            >
              <img :src="mydisease" alt="myDisease" height="20px" />
            </a>
          </div>
        </div>

        <!-- SmartAPI -->
        <div v-if="metadata.smartapi?.id" class="smartapi-box p-2 mt-5">
          <div class="text-xs list-none">
            <div class="mb-2">
              <i class="fas text-green-700 dark:text-lime-500 fa-registered"></i> Registered on
              <a
                rel="noopener"
                :href="'https://smart-api.info/registry?q=' + metadata.smartapi.id"
                target="_blank"
              >
                SmartAPI
                <i class="fas fa-external-link-square-alt"></i>
              </a>
            </div>
            <div>
              <a
                class="ml-6"
                rel="noopener"
                :href="'https://smart-api.info/ui/' + metadata.smartapi.id"
                target="_blank"
              >
                Documentation
                <i class="fas fa-external-link-square-alt"></i>
              </a>
            </div>
            <div>
              <a
                class="ml-6"
                rel="noopener"
                :href="
                  'https://smart-api.info/portal/translator/metakg?q=api.smartapi.id:' +
                  metadata.smartapi.id
                "
                target="_blank"
              >
                MetaKG
                <i class="fas fa-external-link-square-alt"></i>
              </a>
            </div>
          </div>
        </div>
      </div>

      <div class="col-sm-12 col-md-9 col-lg-10 p-4 pt-4 bg-slate-50 dark:bg-main-dark">
        <form
          class="d-flex justify-content-start flex-wrap align-items-center col-sm-12"
          @submit.prevent="testQuery()"
        >
          <h5 class="mr-1" v-text="host + '/' + api"></h5>
          <div class="d-flex justify-content-start flex-wrap align-items-center">
            <template v-if="querySelectionType === 'example'">
              <select
                v-model="querySelected"
                class="form-control example-input"
                id="exampleFormControlSelect1"
              >
                <option value="" disabled>Select an example query...</option>
                <template v-for="item in exampleQueries">
                  <option
                    :value="item"
                    v-text="item.length > 100 ? item.slice(0, 100) + '...' : item"
                  ></option>
                </template>
              </select>
            </template>
            <template v-if="querySelectionType === 'own'">
              <input
                v-model="querySelected"
                type="text"
                class="form-control example-input"
                id="exampleFormControlInput1"
                placeholder="Enter query here"
              />
            </template>
          </div>
          <button
            class="btn m-2"
            :class="[querySelected ? 'btn-success' : 'btn-outline-secondary']"
            :disabled="!querySelected"
            type="submit"
          >
            Submit
          </button>
        </form>
        <div class="d-flex justify-content-start align-items-center">
          <div class="form-check text-left m-1">
            <input
              v-model="querySelectionType"
              class="form-check-input"
              type="radio"
              name="exampleRadios"
              id="exampleRadios1"
              value="example"
              checked
            />
            <label
              class="form-check-label"
              for="exampleRadios1"
              :class="[querySelectionType == 'example' ? '' : 'text-mute']"
            >
              Example Queries
              <button
                @click="refreshExamples()"
                class="btn btn-sm btn-dark ml-1"
                type="button"
                style="zoom: 0.8"
              >
                Generate New <i v-if="loadingExamplesQueries" class="fas fa-spinner fa-pulse"></i>
              </button>
            </label>
          </div>
          <div class="form-check text-left m-1 ml-5">
            <input
              v-model="querySelectionType"
              class="form-check-input"
              type="radio"
              name="exampleRadios"
              id="exampleRadios2"
              value="own"
            />
            <label
              class="form-check-label"
              for="exampleRadios2"
              :class="[querySelectionType == 'own' ? '' : 'text-mute']"
            >
              Write My Own Query
            </label>
          </div>
        </div>
        <p class="text-left" v-if="success && queryString" style="word-break: break-all">
          <i class="fas mr-1 text-lime-400" :class="[success ? 'fa-check' : 'fa-circle']"></i>
          <a
            rel="noopener"
            target="_blank"
            :href="finalURL"
            v-text="host + finalURL"
            type="text"
            :style="{ color: success && !errorEncountered ? 'limegreen' : 'coral' }"
          ></a>
        </p>
        <pre
          v-show="success"
          ref="callResults"
          class="p-2 text-left mt-4 mb-4 dark:bg-slate-900"
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
      </div>
    </div>
    <div v-else>
      <div class="jumbotron text-center mt-5">
        <h1>Nothing to see here...</h1>
        <h5><span v-text="api"></span> is not a pending API</h5>
      </div>
    </div>
    <div v-if="validAPI" class="p-3 text-left bg-main-medium">
      <a
        rel="noopener"
        target="_blank"
        class="btn btm-sm btn-dark"
        :href="'https://github.com/biothings/pending.api/labels/' + api"
        ><i class="fab fa-github"></i> Give Feedback</a
      >
    </div>
  </section>
</template>
