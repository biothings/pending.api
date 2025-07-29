<script setup>
import { computed } from 'vue'
import { useAPIStore } from '@/stores/apis'
import Icon from './Icon.vue'

const apiStore = useAPIStore()

let props = defineProps(['biotype'])

let color = computed(() => {
  return apiStore.getColor(props.biotype)
})

function numberWithCommas(total) {
  if (total) {
    return total.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  } else {
    return 'N/A'
  }
}

let list = computed(() => {
  if (apiStore.apis_backup?.length) {
    return apiStore.apis_backup.filter((v) => v['biothing_type'] === props.biotype)
  } else {
    return []
  }
})

let docs = computed(() => {
  if (list.value.length) {
    return list.value.reduce((totalSum, item) => {
      // Ensure item.stats and item.stats.total exist
      const total = item?.stats?.total || 0
      return totalSum + total
    }, 0)
  } else {
    return 0
  }
})

let isActive = computed(() => {
  if (apiStore.biothing_types?.length) {
    let bt = apiStore.biothing_types.find((type) => type.name === props.biotype)
    if (bt && bt.active) {
      return true
    } else {
      return false
    }
  } else {
    return false
  }
})

function toggleType(name) {
  apiStore.toggleType({ name: name, featured: true })
  apiStore.filterAPIs()
}
</script>

<template>
  <div
    class="card m-2 bg-hex shadow"
    :style="{ border: color + ' 2px solid' }"
    :class="{ 'active-bg': isActive }"
  >
    <div class="card-body">
      <h5
        class="card-title pointer"
        @click.prevent="toggleType(biotype)"
        :style="{ color: isActive ? '#fbff12' : 'white' }"
      >
        <Icon :biotype="biotype" />
        {{ list?.length && list?.length }} <span class="capitalize">{{ biotype }}</span> APIs
      </h5>
      <p class="card-text text-white">{{ numberWithCommas(docs) }} documents</p>
    </div>
  </div>
</template>
