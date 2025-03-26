import { ref } from 'vue'
import { defineStore } from 'pinia'
import axios from 'axios';
import moment from 'moment';
import { useLayoutStore } from './layout';

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

    function setQuery(v) {
        query.value = v;
    }

    function getBioTypes(){
        let types = new Set();
        let final = []
        apis.value.forEach(api=>{
            console.log(api)
            if (api?.biothing_type) {
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

    function addType(type){
        let found = biothing_types.value.some(el => el.name === type);
        if (!found) {
            biothing_types.value.push({
                'name': type,
                'active': false,
                'color': getColor(type)
            });
            }
    }

    function getAPIsFullInfo(){
        list.value.forEach(async (name) => {
            axios.get(apiUrl.value + '/' + name + '/metadata').then(res=>{
                let metadata = res.data
                metadata['name'] = name;
                if (metadata.hasOwnProperty('build_date')) {
                    metadata.build_date = moment(metadata.build_date).format("M-D-YYYY"); 
                }
                if(metadata.hasOwnProperty('biothing_type')){ 
                    addType(metadata.biothing_type)
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

    function saveAPIs(payload){
		apis.value = payload['apis']
	}

    function filterAPIs () {
        let active_filters = []
        biothing_types.value.forEach(type=>{
            if (type.active) {
                active_filters.push(type.name)
            }
        });
        if (active_filters.length) {
            if (query.value) {
                let filter_res = apis_backup.value.filter( api => {
                    if (api.name.includes(query.value) 
                        && active_filters.includes(api.biothing_type)) {
                        return api
                    }
                });
                saveAPIs({'apis': filter_res});
            
            } else {
                let filter_res = apis_backup.value.filter( api => {
                    if (active_filters.includes(api.biothing_type)) {
                        return api
                    }
                });
                saveAPIs({'apis': filter_res});
            }
        }else{
            if (query.value) {
                let filter_res = apis_backup.value.filter( api => {
                    if (api.name.includes(query.value)) {
                        return api
                    }
                });
                saveAPIs({'apis': filter_res});
            
            } else {
                saveAPIs({'apis': apis_backup.value});
            }
        }
        
    }

    function toggleType(payload){
        let name = payload['name'];
        if (payload['featured']) {
            biothing_types.value.forEach(type=>{
                if (type.name != name) {
                    type.active = false
                }
            });
        }
        for (let i = 0; i < biothing_types.value.length; i++) {
            if (biothing_types.value[i].name == name) {
                biothing_types.value[i].active = !biothing_types.value[i].active
            }
        }
    }

    function getColor(type){
        switch (type) {
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
    }

    async function fetchAPIs(){
        const store = useLayoutStore();
        store.setLoading(true);
        await axios.get(apiUrl.value + '/api/list').then(res => {
            setList(res.data);
            getAPIsFullInfo();
            store.setLoading(false);
        }).catch(err => {
            store.setLoading(false);
            console.error(err);
        });
    }

    return { 
        apis, setAPIs, query, getAPIsFullInfo, 
        list, apis_backup, getBioTypes, 
        biothing_types, setApiUrl, setList, 
        filterAPIs, setQuery, toggleType,
        getColor, fetchAPIs
    }
});
