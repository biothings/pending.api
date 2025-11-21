<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAPIStore } from '@/stores/apis'
import axios from 'axios'
import { isPlainObject, isArray, isBoolean, isNumber, isString } from 'lodash'
import { useRoute } from 'vue-router'

import SourceInfo from '@/components/SourceInfo.vue'
import MethodPicker from '@/components/MethodPicker.vue'
import mygene from '@/assets/img/mygene-text.svg'
import myvariant from '@/assets/img/myvariant-text.svg'
import mychem from '@/assets/img/mychem-text.svg'
import mydisease from '@/assets/img/mydisease-text.png'
import Icon from '@/components/Icon.vue'

let metadata = ref(null)
let numberOfDocs = ref(0)
let type = ref(null)
let querySelectionType = ref('example')
let getExampleQueries = ref([
  {
    method: 'GET',
    query: '/metadata',
  },
  {
    method: 'GET',
    query: '/metadata/fields',
  },
])
let postExampleQueries = ref([])
let querySelected = ref('')
let loadingExamplesQueries = ref(false)

let existingEntity = false
let validAPI = true
let numberOfExamples = 8

const origin = computed(() => window.location.origin)
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
      generateAllQueries()
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

function generateGETEntityQuery(dataObject) {
  if (dataObject && dataObject.hasOwnProperty('_id')) {
    let id = dataObject['_id']
    let query = '/' + type.value + '/' + id
    getExampleQueries.value.push({
      method: 'GET',
      query: query,
      type: type.value,
    })
  }
}

function randomProperty(obj) {
  if (!isPlainObject(obj)) return null

  // Filter out unwanted keys and values
  const keys = Object.keys(obj).filter((key) => {
    if (['_id', '_score'].includes(key)) return false
    const val = obj[key]
    return !(typeof val === 'string' && val.includes('http'))
  })

  if (keys.length === 0) return null

  // Pick a random key
  const randomKey = keys[Math.floor(Math.random() * keys.length)]
  return randomKey
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

function generatePOSTQueryByIDs(hits, size, numberOfExamples) {
  let ids = []
  if (hits && hits.length > 0 && size > 0) {
    let i = 0
    while (i < numberOfExamples) {
      let doc = hits[randomNumber(size)]
      if (doc && doc.hasOwnProperty('_id')) {
        ids.push(doc['_id'])
      }
      i++
    }
    if (ids.length > 0) {
      // type query
      let type_query = '/' + type.value
      //limit to 10 unique IDs
      ids = [...new Set(ids)].slice(0, 10)
      let type_body = {
        ids: ids,
      }
      postExampleQueries.value.push({
        method: 'POST',
        query: type_query,
        text: `Batch query ${type.value}s by IDs`,
        body: type_body,
        type: type.value,
      })
    } else {
      console.warn('No valid IDs found to generate POST queries')
    }
  } else {
    console.warn('No hits found to generate POST queries')
  }
}

function generatePOSTQueriesAgainstSingleField(results, numberOfExamples) {
  if (!results || results.length === 0) {
    console.warn('No results provided for generating POST queries against a single field.')
    return
  }

  let firstFieldValuePair
  let found = false
  let attempts = 0
  const maxAttempts = 10
  let attemptIndex = 0

  while (!found && attemptIndex < maxAttempts) {
    const candidate = results[attemptIndex]
    firstFieldValuePair = getQueryString(candidate)
    if (
      firstFieldValuePair &&
      !firstFieldValuePair.includes('name') &&
      !firstFieldValuePair.includes('description')
    ) {
      found = true
    }
    attemptIndex++
    attempts++
  }

  if (attempts === maxAttempts) {
    console.warn('Could not find a valid field:value pair after 10 attempts.')
  }

  if (!firstFieldValuePair) {
    console.warn('No valid field:value pair found in the first result.')
    return
  }

  let field = firstFieldValuePair.split(':')[0]

  let fieldValues = extractFieldValues(field, results.slice(0, numberOfExamples))

  if (fieldValues.length === 0) {
    console.warn(`No values found for the field "${field}" in the provided results.`)
    return
  }

  // check if values are arrays then flatten them
  fieldValues = fieldValues.flatMap((value) => {
    if (Array.isArray(value)) {
      return value.map((v) => v).filter((v) => v !== false)
    } else {
      return value
    }
  })

  fieldValues = [...new Set(fieldValues)].slice(0, 10)

  // check q value is greater than 1
  if (fieldValues.length < 2) {
    console.warn(`❌ Not enough values for field ${field}`)
    return
  }

  let query = '/query'
  let body = {
    q: fieldValues,
    scopes: field,
  }

  postExampleQueries.value.push({
    method: 'POST',
    query: query,
    text: `Batch query against a single field`,
    body: body,
  })
}

function extractFieldValues(fieldPath, docs) {
  const pathParts = fieldPath.split('.')

  return docs
    .map((doc) => {
      let value = doc
      for (const part of pathParts) {
        if (value && part in value) {
          value = value[part]
        } else {
          return undefined
        }
      }
      return value
    })
    .filter((value) => value !== undefined)
}

function extractQValue(input) {
  // Get just the query part after '?'
  const queryString = input.split('?')[1]
  if (!queryString) return null

  const params = new URLSearchParams(queryString)
  return params.get('q')
}

function extractFieldAndValue(rawInput) {
  // Unescape any escaped colons
  const unescaped = rawInput.replace(/\\:/g, ':')

  // Split on the first colon to get the dotted field and value
  const firstColonIndex = unescaped.indexOf(':')
  if (firstColonIndex === -1) return null

  const field = unescaped.slice(0, firstColonIndex)
  const value = unescaped.slice(firstColonIndex + 1)

  return { field, value }
}

function createPOSTScopeQuery(results, size) {
  const body = {
    q: new Set(),
    scopes: new Set(),
  }

  let index = 0
  while (index < size) {
    const q = getQueryString(results[index])

    if (!q || typeof q !== 'string' || q.includes('undefined')) {
      index++
      continue
    }

    const fullQueryString = '/query?q=' + q
    const rawQValue = extractQValue(fullQueryString)
    if (!rawQValue) {
      index++
      continue
    }

    const cleanedQValue = rawQValue.replace(/['"]/g, '')
    const fieldValue = extractFieldAndValue(cleanedQValue)
    if (!fieldValue || !fieldValue.field || !fieldValue.value) {
      index++
      continue
    }

    body.q.add(fieldValue.value)
    body.scopes.add(fieldValue.field)

    index++
  }

  if (body.q.size > 0 && body.scopes.size > 0) {
    postExampleQueries.value.push({
      method: 'POST',
      query: '/query',
      text: `Batch query against multiple fields`,
      body: {
        q: [...body.q],
        scopes: [...body.scopes],
      },
    })
  } else {
    console.warn('No valid scope queries generated.')
  }
}

function generateAllQueries() {
  let uniqueFieldsQueried = new Set()
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
        generateGETEntityQuery(res[randomNumber(size)])
        generatePOSTQueryByIDs(res, size, 30)
        generatePOSTQueriesAgainstSingleField(res, 30)
        // generate scope query
        if (res.length > 5) {
          try {
            createPOSTScopeQuery(res, 5)
          } catch (error) {
            console.error('Error creating scope query:', error)
          }
        }
        while (i < numberOfExamples) {
          let doc = res[randomNumber(size)]
          picks.push(doc)
          i++
        }
        let problematic = []
        for (var picksIndex = 0; picksIndex < picks.length; picksIndex++) {
          let value = getQueryString(picks[picksIndex])
          let dottedField = value.split(':')[0]
          if (value) {
            let query = '/query?q=' + value
            //excludes duplicates and results with undefined terms
            if (!uniqueFieldsQueried.has(dottedField) && !query.includes('undefined')) {
              uniqueFieldsQueried.add(dottedField)
              getExampleQueries.value.push({
                method: 'GET',
                query: query,
              })
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
        console.log('Error loading examples', err)
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
  getExampleQueries.value = [
    {
      method: 'GET',
      query: '/metadata',
    },
    {
      method: 'GET',
      query: '/metadata/fields',
    },
  ]
  postExampleQueries.value = []
  generateAllQueries()
}

onMounted(() => {
  apiStore.setQuerySelected(null)
  apiStore.setCurrentAPI(route.params.api)
  getMetadata()
})

const route = useRoute()

watch(
  () => route.params.api,
  () => {
    apiStore.setQuery('')
    refreshExamples()
    getMetadata()
  },
)

watch(
  () => querySelected.value,
  (v) => {
    apiStore.setQuerySelected(v)
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
      >
        {{ api.split('_').join(' ') }}
      </h2>
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
                <Icon :biotype="metadata?.biothing_type" /> {{ metadata.biothing_type }}</strong
              >
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
          <div
            v-if="metadata.biothing_type"
            class="badge bg-gray-200 dark:bg-gray-800 d-block p-1 m-2"
          >
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
        <div class="d-flex justify-content-start flex-wrap align-items-center col-sm-12">
          <h5 class="mr-1">{{ origin + '/' + api }}</h5>
          <div class="d-flex justify-content-start flex-wrap align-items-center">
            <template v-if="querySelectionType === 'example'">
              <select
                v-model="querySelected"
                class="form-control example-input"
                id="exampleFormControlSelect1"
              >
                <option value="" disabled>Select an example query...</option>
                <hr />
                <option disabled>GET</option>
                <option v-for="item in getExampleQueries" :key="item.query" :value="item">
                  {{ item.query.length > 100 ? item.query.slice(0, 100) + '...' : item.query }}
                </option>
                <hr />
                <option disabled>POST</option>
                <option v-for="item in postExampleQueries" :key="item.query" :value="item">
                  {{ item.query.length > 100 ? item.query.slice(0, 100) + '...' : item.query }} -
                  {{ item.text }}
                </option>
              </select>
            </template>
            <template v-if="querySelectionType === 'own'">
              <input
                v-model="querySelected.query"
                type="text"
                class="form-control example-input"
                id="exampleFormControlInput1"
                placeholder="Enter query here"
              />
            </template>
          </div>

          <label
            class="d-flex items-center cursor-pointer m-3"
            v-if="apiStore.querySelected?.query"
          >
            <input
              type="checkbox"
              value=""
              class="sr-only peer"
              @click="apiStore.togglePythonMode"
            />
            <div
              class="relative w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-700 peer-focus:ring-4 peer-focus:ring-purple-300 dark:peer-focus:ring-purple-800 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-purple-600 dark:peer-checked:bg-purple-600"
            ></div>
            <span class="ms-3 text-sm font-medium text-gray-900 dark:text-gray-300"
              >Python Client Code</span
            >
          </label>
        </div>
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
                class="btn btn-sm btn-dark ml-1 rounded"
                type="button"
                style="zoom: 0.8"
              >
                Generate New <i v-if="loadingExamplesQueries" class="fas fa-spinner fa-pulse"></i>
              </button>
            </label>
          </div>
          <div class="form-check text-left m-1 ml-5" v-if="querySelected.method !== 'POST'">
            <input
              v-model="querySelectionType"
              class="form-check-input"
              type="radio"
              name="exampleRadios"
              id="exampleRadios2"
              value="own"
              :disabled="querySelected.method === 'POST'"
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
        <MethodPicker :query="querySelected" :api="api" :key="api"></MethodPicker>
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
