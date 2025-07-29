<script setup>
import GetTester from './GetTester.vue'
import PostTester from './PostTester.vue'
import PythonTester from './PythonTester.vue'
import { useAPIStore } from '@/stores/apis'

const apiStore = useAPIStore()

let props = defineProps({
  query: Object,
})
</script>

<template>
  <div v-if="apiStore.viewPythonClient">
    <PythonTester></PythonTester>
  </div>
  <div v-else>
    <div v-if="props.query.method == 'GET'">
      <GetTester></GetTester>
    </div>
    <div v-if="props.query.method == 'POST'">
      <PostTester></PostTester>
    </div>
  </div>
</template>
