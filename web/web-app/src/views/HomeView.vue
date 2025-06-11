<script setup>
import { useLayoutStore } from '@/stores/layout'
import { useAPIStore } from '@/stores/apis'
import { watch, ref, nextTick, onMounted } from 'vue'

import FeaturedType from '@/components/FeaturedType.vue'
import APITableNew from '@/components/APITableNew.vue'
import Icon from '@/components/Icon.vue'

const store = useLayoutStore()
const apiStore = useAPIStore()

const searchInput = ref(null)

const focusSearchInput = async () => {
  await nextTick()
  searchInput.value?.focus()
}

onMounted(() => {
  focusSearchInput()
})

watch(() => apiStore.query, (val) => {
  apiStore.setQuery(val)
  apiStore.filterAPIs()
})

function toggleType(type) {
  apiStore.toggleType({ name: type })
  apiStore.filterAPIs()
}
</script>

<template>
  <section>
    <div>
      <div class="container row m-auto">
        <div class="col-sm-3 d-flex justify-center align-items-center">
          <img
            v-if="store.app_version == 'pending'"
            class="hero-image"
            width="150px"
            src="@/assets/img/infinity.svg"
            alt="Pending APIs"
          />
          <img v-else class="hero-image" width="250px" src="@/assets/img/tr.jpg" alt="TRANSLATOR" />
        </div>
        <template v-if="store.app_version == 'pending'">
          <div id="home" class="jumbotron bg-none mb-0 py-5 col-sm-9 text-left">
            <h1>
              <span class="main-font">Pending</span> <br class="d-block d-md-none" />BioThings APIs
            </h1>
            <div>
              <p class=" ">
                A collection of community-contributed APIs from various biomedical data sources.
              </p>
            </div>
          </div>
        </template>
        <template v-else>
          <div class="jumbotron bg-none mb-0 text-left col-sm-9">
            <h1 class="mt-5 mb-0">Knowledge Provider (KP) APIs</h1>
            <h3 class="mb-4">
              Made for
              <a
                class="text-underline"
                href="https://ncats.nih.gov/translator"
                target="_blank"
                rel="noreferrer"
                >NCATS Biomedical Data Translator</a
              >
              Program
            </h3>
            <p class="dark:text-gray-300">
              The list of APIs here provide programatic access to the underlying knowledge sources
              they cover. They were built using
              <a
                rel="noopener"
                href="https://biothingsapi.readthedocs.io/en/latest/"
                target="_blank"
                >BioThings SDK</a
              >
              and follow the same design pattern of our official BioThings APIs (<a
                rel="noopener"
                href="https://mygene.info"
                target="_blank"
                >MyGene.info</a
              >, <a rel="noopener" href="https://myvariant.info" target="_blank">MyVariant.info</a>,
              <a rel="noopener" href="https://mychem.info" target="_blank">MyChem.info</a>,
              <a rel="noopener" href="https://mydisease.info" target="_blank">MyDisease.info</a>,
              etc). These APIs are serving as the Knowledge Providers (KPs) in the
              <a href="https://ncats.nih.gov/translator" target="_blank" rel="noreferrer"
                >NCATS Biomedical Data Translator</a
              >
              project. They were deployed to the NCATS Cloud infrastructure for production use.
            </p>
            <p class="dark:text-gray-300">
              We are continuing expanding the list of KP APIs here as new knowledge sources are
              identified. You are always welcome to
              <a
                href="https://github.com/NCATS-Tangerine/translator-api-registry/issues/new?assignees=cmungall%2C+tomconlin%2C+newgene%2C+kevinxin90&labels=data+wanted&template=a_data_source_wanted.md"
                target="_blank"
                rel="noreferrer"
                >suggest a great resource</a
              >
              to us as well.
            </p>
          </div>
        </template>
      </div>
    </div>

    <div id="pending" class="text-center">
      <div class="py-3">
        <div class="py-1">
          <h2>
            <img width="40" src="@/assets/img/featured.png" alt="Featured APIs" class="d-inline" />
            Featured APIs
          </h2>
        </div>
        <div class="d-flex justify-content-center align-items-center flex-wrap container pt-4">
          <FeaturedType biotype="association"></FeaturedType>
          <FeaturedType biotype="variant"></FeaturedType>
          <FeaturedType biotype="gene"></FeaturedType>
        </div>
      </div>
      <div class="container py-3">
        <div>
          <form class="p-2">
            <label class="mr-4" for="search"
              >(<span class="" style="font-family: sans-serif" v-text="apiStore.apis.length"></span
              >) APIs</label
            >
            <input
              v-model="apiStore.query"
              type="text"
              name="search"
              class="bg-white placeholder:text-main-light rounded caret-pink-500 focus:outline-2 focus:outline-offset-2 focus:outline-violet-500 text-main-dark w-50 px-2"
              placeholder="Filter by name"
              ref="searchInput"
              autofocus
            />
            <datalist id="api_list"></datalist>
          </form>
          <div class="d-flex justify-content-center align-items-center p-3">
            <div>
              <small class="d-block">Filter by Entity Type</small>
              <template v-for="type in apiStore.biothing_types" :key="type.name">
                <span
                  class="entity-badge badge border border-light m-1 pointer shadow"
                  :class="[type.active ? 'badge-active' : 'badge-dark']"
                  @click.prevent="toggleType(type.name)"
                >
                  <Icon :biotype="type.name" :key="type.name"></Icon> {{ type.name }}
                </span>
              </template>
            </div>
          </div>
          <div class="api-main-container">
            <template v-if="apiStore.apis.length">
              <APITableNew></APITableNew>
            </template>
          </div>
        </div>
      </div>
    </div>

    <template v-if="store.app_version == 'pending'">
      <div id="contribute" class="text-center mt-5">
        <div class="container d-flex justify-content-center align-items-start mb-4">
          <div class="mx-4 card bg-main-muted shadow">
            <div class="card-body">
              <img
                class="card-image-top m-auto"
                width="128"
                src="@/assets/img/biothings-studio-text-2.svg"
                alt="BT Studio"
              />
              <h2 class="mb-3 card-title">Built with BioThings Studio</h2>
              <a
                rel="noopener"
                class="btn btn-dark"
                target="_blank"
                href="http://docs.biothings.io/en/latest/doc/studio.html"
                title="BioThings Studio"
              >
                Learn More About BioThings Studio <i class="fas fa-external-link-square-alt"></i>
              </a>
            </div>
          </div>
          <div class="mx-4 card bg-main-muted shadow">
            <img
              class="card-image-top m-auto"
              width="100"
              src="@/assets/img/infinity.svg"
              alt="Logo"
            />
            <div class="card-body">
              <h2 class="main-font card-title">Build Your Own API</h2>
              <a
                rel="noopener"
                class="btn btn-dark"
                target="_blank"
                href="https://biothingsapi.readthedocs.io/en/latest/doc/studio.html"
              >
                Follow this guide <i class="fas fa-external-link-square-alt"></i>
              </a>
            </div>
          </div>
        </div>

        <div class="container p-2 text-center bg-bts">
          <h2 class="mb-3">BioThings APIs</h2>
          <p class="text-left">
            Pending APIs were built using
            <a rel="noopener" href="https://biothingsapi.readthedocs.io/en/latest/" target="_blank"
              >BioThings SDK</a
            >
            and follow the same design pattern of our official BioThings APIs (<a
              rel="noopener"
              href="https://mygene.info"
              target="_blank"
              >MyGene.info</a
            >, <a rel="noopener" href="https://myvariant.info" target="_blank">MyVariant.info</a>,
            <a rel="noopener" href="https://mychem.info" target="_blank">MyChem.info</a>,
            <a rel="noopener" href="https://mydisease.info" target="_blank">MyDisease.info</a> etc).
            Pending APIs are also pending to be integrated into the proper official BioThings API
            based on their entity type.
          </p>
          <div class="row w-75 m-auto">
            <div class="col-sm-12 col-md-6 p-4">
              <a rel="noopener" target="_blank" href="https://mygene.info/" title="MyGene.info">
                <img
                  alt="myGene"
                  style="border: 0px"
                  width="128"
                  src="https://biothings.io@/assets/img/mygene-logo-128.png"
                />
                <small class="d-block"> Gene annotation <br />as a service </small>
                <small class="d-block mt-2">
                  Learn More About MyGene <i class="fas fa-external-link-square-alt"></i>
                </small>
              </a>
            </div>
            <div class="col-sm-12 col-md-6 p-4">
              <a
                rel="noopener"
                target="_blank"
                href="https://myvariant.info/"
                title="MyVariant.info"
              >
                <img
                  alt="myVariant"
                  style="border: 0px"
                  width="128"
                  src="https://biothings.io@/assets/img/myvariant-logo-128.png"
                />
                <small class="d-block"> Variant annotation <br />as a service </small>
                <small class="d-block mt-2">
                  Learn More About MyVariant <i class="fas fa-external-link-square-alt"></i>
                </small>
              </a>
            </div>
            <div class="col-sm-12 col-md-6 p-4">
              <a rel="noopener" target="_blank" href="https://mychem.info/" title="MyChem.info">
                <img
                  alt="myChem"
                  style="border: 0px"
                  width="128"
                  src="https://biothings.io@/assets/img/mychem-logo-128.png"
                />
                <small class="d-block"> Chemical/Drug annotation <br />as a service </small>
                <small class="d-block mt-2">
                  Learn More About MyChem <i class="fas fa-external-link-square-alt"></i>
                </small>
              </a>
            </div>
            <div class="col-sm-12 col-md-6 p-4">
              <a
                rel="noopener"
                target="_blank"
                href="https://mydisease.info/"
                title="MyDisease.info"
              >
                <img
                  alt="myDisease"
                  style="border: 0px"
                  width="128"
                  src="https://biothings.io@/assets/img/mydisease-text-3.svg"
                />
                <small class="d-block"> Disease annotation <br />as a service </small>
                <small class="d-block mt-2">
                  Learn More About MyDisease <i class="fas fa-external-link-square-alt"></i>
                </small>
              </a>
            </div>
            <div class="col-sm-12 text-center p-5">
              <a rel="noopener" href="http://biothings.io/#access" target="_blank"
                >Other BioThings APIs in production <i class="fas fa-external-link-square-alt"></i
              ></a>
            </div>
          </div>
        </div>
      </div>

      <div id="help" class="text-center py-4 bg-med">
        <h2 class="mb-5 main-font">Need Help?</h2>
        <div class="container p-4" style="position: relative">
          <a
            rel="noopener"
            class="btn-main"
            href="mailto:biothings@googlegroups.com"
            target="_blank"
            >Contact Us</a
          >
        </div>
      </div>
    </template>
  </section>
</template>
