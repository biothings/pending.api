import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios';
import moment from 'moment';

export const useAPIStore = defineStore('apis', () => {
    const apiUrl = ref('');

    function setApiUrl(url) {
        apiUrl.value = url;
    }
    //list of names of APIs
    const list = ref([]);
    //list of full info of APIs
    const apis = ref([]);
    const apis_backup = ref([]);

    const biothing_types = ref([]);

    function setList(v) {
        list.value = v;
    }

    function setAPIs(v) {
        apis.value = v;
    }
    const query = ref('');

    function getAPIsFullInfo(){
        list.value.forEach(async (name) => {
            axios.get(apiUrl.value + '/' + name + '/metadata').then(res=>{
                let metadata = res.data
                metadata['name'] = name;
                if (metadata.hasOwnProperty('build_date')) {
                    metadata.build_date = moment(metadata.build_date).format("M-D-YYYY"); 
                }
                apis.value.push(metadata)
                apis_backup.value.push(metadata)
            }).catch(err=>{
                throw err;
            })
        });
    }

    function getColor(name){
        switch (name) {
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
                return '#7209b7'
        }
    }

    function getBioTypes(){
        let types = new Set();
        let final = []
        apis.value.forEach(api=>{
            if (api.hasOwnProperty('biothing_type')) {
                types.add(api.biothing_type);
            }
        });

        [...types].forEach(type=>{
            final.push({
                    'name': type,
                    'active': false,
                    'color': getColor(type)
                });
        })
        biothing_types.value = final;
    }

    return { apis, setAPIs, query, getAPIsFullInfo, list, apis_backup, getBioTypes, biothing_types, setApiUrl, setList }
});
