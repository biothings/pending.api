<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { useAPIStore } from '@/stores/apis';

const apiStore = useAPIStore();

let props = defineProps(['api']);

let color = computed(() => {
    return apiStore.getColor(props.api.biothing_type);
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
        <td>
            <RouterLink :to="'/try/'+api['name']">
                {{ api.name }}
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