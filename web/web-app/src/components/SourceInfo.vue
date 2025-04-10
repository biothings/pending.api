<script setup>
import { computed } from 'vue'

let props = defineProps({
  name: String,
  multiSource: Boolean,
  info: Object,
})

let version = props.info?.version
let source_url = props.info?.source_url
let source_code = props.info?.code?.url
let license_url = props.info?.license_url

function formatString(input) {
  return input
    .split('_') // Split the string by underscores
    .map((word) => {
      if (word.length <= 3) {
        return word.toUpperCase() // Capitalize short words (3 letters or fewer)
      } else {
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase() // Capitalize first letter of longer words
      }
    })
    .join(' ') // Join the words back into a sentence
}

function trimString(str) {
  if (str.length > 10) {
    return str.slice(0, 10) + '...' // Get the first 4 characters and append "..."
  }
  return str // If the string is 4 characters or less, return it as is
}
</script>

<template>
  <div>
    <h6 v-if="multiSource" :title="info?.description">
      {{ formatString(name) }}
    </h6>
    <small v-if="version" :title="version" class="d-block">
      {{ 'Version ' + trimString(version) }}
    </small>
    <ul class="link-list m-0">
      <li class="d-inline" v-if="source_url">
        <small>
          <a rel="noopener" :href="source_url" target="_blank">
            Source <i class="fas fa-external-link-square-alt"></i>
          </a>
        </small>
      </li>
      <li class="d-inline" v-if="source_code">
        <small>
          <a rel="noopener" :href="source_code" target="_blank">
            Code <i class="fas fa-external-link-square-alt"></i>
          </a>
        </small>
      </li>
      <li class="d-inline" v-if="license_url">
        <small>
          <a rel="noopener" :href="license_url" target="_blank">
            License <i class="fas fa-external-link-square-alt"></i>
          </a>
        </small>
      </li>
    </ul>
  </div>
</template>
