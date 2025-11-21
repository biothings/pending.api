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
import drug from '@/assets/img/drug.svg'
import food from '@/assets/img/food.svg'
import reaction from '@/assets/img/reaction.svg'
import indication from '@/assets/img/indication.svg'
import phenotype from '@/assets/img/phenotype.svg'
import cooccurrence from '@/assets/img/cooccurrence.svg'
import umls from '@/assets/img/umls.svg'
import anatomy from '@/assets/img/anatomy.svg'

import { ref } from 'vue'

let props = defineProps(['biotype'])
let icon = ref(null)

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
} else if (props.biotype === 'drug') {
  icon.value = drug
} else if (props.biotype === 'food') {
  icon.value = food
} else if (props.biotype === 'reaction') {
  icon.value = reaction
} else if (props.biotype === 'indication') {
  icon.value = indication
} else if (props.biotype === 'phenotype') {
  icon.value = phenotype
} else if (props.biotype === 'cooccurrence') {
  icon.value = cooccurrence
} else if (props.biotype === 'umls') {
  icon.value = umls
} else if (props.biotype === 'anatomy') {
  icon.value = anatomy
} else {
  icon.value = biotype
}
</script>

<template>
  <img
    :src="icon"
    alt="Icon"
    class="biotype-icon d-inline"
    style="width: 15px; vertical-align: middle"
  />
</template>
