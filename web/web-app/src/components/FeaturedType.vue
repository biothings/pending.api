<script setup>
import { computed } from 'vue';

defineProps(['biotype']);

let color = computed(() => {
    switch (this.biotype) {
        case 'gene':
            return "#669BE8"
        case 'variant':
            return "#84D958"
        case 'chemical':
            return "#FF8F39"
        case 'disease':
            return "#9356bf"
        case 'association':
            return "#e91e62"
        default:
            return '#501cbe'
    }
});

function numberWithCommas(total) {
    if (total) {
        return total.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }else{
        return 'N/A'
    }
}

function toggleType(name){
    store.commit('toggleType', {'name': name, 'featured': true})
    store.dispatch('filterAPIs', {'query': self.query})
}
</script>

<template>
    <div class="card mx-2 bg-theme-dark bg-hex">
        <div class="card-body">
            <h5 class="card-title pointer" @click.prevent="toggleType(biotype)" :class="[isActive ? 'text-main-accent' : 'text-primary']">
                <i class="fas fa-circle mr-1" :style="{'color':color}"></i>
                <span v-text="list?.length && list?.length"></span> <span class="capitalize" v-text="biotype"></span> APIs
            </h5>
            <p class="card-text text-white">{{ numberWithCommas(docs) }} documents</p>
        </div>
    </div>
</template>