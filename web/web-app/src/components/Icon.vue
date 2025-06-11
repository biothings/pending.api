<script setup>
import chemical from '@/assets/img/chemical.svg'
import disease from '@/assets/img/disease.svg'
import gene from '@/assets/img/gene.svg'
import interaction from '@/assets/img/interaction.svg'
import geneset from '@/assets/img/geneset.svg'
import trial from '@/assets/img/trial.svg'
import association from '@/assets/img/association.svg'
import cell from '@/assets/img/cell.svg'
import node from '@/assets/img/node.svg'
import biotype from '@/assets/img/biotype.svg'
import variant from '@/assets/img/variant.svg'

import { ref } from 'vue'

let props = defineProps(['biotype']);
let icon = ref(null);

if (props.biotype === 'chemical') {
  icon.value = chemical
} else if (props.biotype === 'disease') {
icon.value = disease
} else if (props.biotype === 'gene') {
icon.value = gene
} else if (props.biotype === 'interaction') {
icon.value = interaction
} else if (props.biotype === 'geneset') {
icon.value = geneset
} else if (props.biotype === 'trial') {
icon.value = trial
} else if (props.biotype === 'association') {
icon.value = association
} else if (props.biotype === 'cell') {
icon.value = cell
} else if (props.biotype === 'node') {
icon.value = node
} else if (props.biotype === 'variant') {
    icon.value = variant
} else {
icon.value = biotype
}

</script>

<template>
    <img
        :src="icon"
        alt="Icon"
        class="biotype-icon d-inline"
        style="width: 15px; vertical-align: middle;"/>
</template>