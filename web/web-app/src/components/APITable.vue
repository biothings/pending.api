<script setup>
import { onMounted, watch, ref, onBeforeUnmount } from 'vue'
import { TabulatorFull as Tabulator } from 'tabulator-tables'
import { useAPIStore } from '@/stores/apis'
import { useRouter } from 'vue-router'

const apiStore = useAPIStore()
const router = useRouter()

let table

function numberWithCommas(total) {
  if (total) {
    return total.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  } else {
    return 'N/A'
  }
}

onMounted(() => {
  //initialize table
  if (table) {
    table.destroy() // Destroy any existing instance
  }

  table = new Tabulator('#example-table', {
    data: [], //assign data to table
    layout: 'fitColumns', //fit columns to width of table
    responsiveLayout: 'hide', //hide columns that don't fit on the table
    addRowPos: 'top', //when adding a new row, add it to the top of the table
    history: true, //allow undo and redo actions on the table
    // pagination:"local",       //paginate the data
    // paginationSize:7,         //allow 7 rows per page of data
    // paginationCounter:"rows", //display count of paginated rows in footer
    movableColumns: true, //allow column order to be changed
    initialSort: [
      //set the initial sort order of the data
      { column: 'name', dir: 'asc' },
    ],
    // columnDefaults:{
    //     tooltip:true,         //show tool tips on cells
    // },
    // autoColumns:true, //create columns from data field names
    columns: [
      {
        title: 'Name',
        field: 'name',
        sorter: 'string',
        hozAlign: 'left',
        formatter: function (cell) {
          return `<span class="text-primary">${cell.getValue()}</span>`
        },
        cellClick: function (e, cell) {
          router.push(`/${cell.getValue()}`) // Use router instance
        },
      },
      {
        title: 'Documents',
        field: 'documents',
        sorter: 'number',
        formatter: function (cell) {
          return `${numberWithCommas(cell.getValue())}`
        },
      },
      {
        title: 'Entity Type',
        field: 'entity_type',
        hozAlign: 'left',
        formatter: function (cell) {
          return `<i class="fas fa-circle" style="color: ${apiStore.getColor(cell.getValue())}"></i> ${cell.getValue()}`
        },
      },
    ],
  })

  setTimeout(() => {
    table.clearData()
    table.setData(makeTableRows(apiStore.apis))
  }, 1000)
})

// Cleanup when component unmounts
onBeforeUnmount(() => {
  if (table) {
    table.destroy()
    table = null
  }
})

let rows = ref([])

let makeTableRows = () => {
  return apiStore.apis.map((api) => {
    return {
      name: api.name,
      entity_type: api.biothing_type,
      documents: api?.stats?.total,
      color: apiStore.getColor(api.biothing_type),
    }
  })
}

watch(
  () => apiStore.apis,
  (newVal, oldVal) => {
    table.clearData()
    rows.value = makeTableRows(newVal)
    table.replaceData(rows.value)
  },
)
</script>

<template>
  <div id="example-table"></div>
</template>

<style>
@import 'tabulator-tables/dist/css/tabulator.css';
</style>
