<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

defineProps(['api']);

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

</script>

<template>
    <tr class="api-row border rounded p-1 m-1 text-left">
        <td class="bold">
            <RouterLink :to="'/'+api['name']">
                <b v-text="api.name"></b>
            </RouterLink>
        </td>
        <td class="d-none d-md-table-cell" v-if="api && api.stats">
            {{ numberWithCommas(api.stats?.total) }}
        </td>
        <td v-if="api && api.biothing_type">
            <small>
                <i class="fas fa-circle" :style="{'color': color}"></i> {{ api.biothing_type }}
            </small>
        </td>
    </tr>
</template>