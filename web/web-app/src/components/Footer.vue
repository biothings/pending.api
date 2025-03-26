<script setup>
    import { ref } from 'vue';

    const year = ref(new Date().getFullYear());
</script>

<template>
    <footer id="footer" class="p-4 bg-lines bg-black">
        <div class="copyright text-center">
            <ul class="noListStyle listBlock m-0 p-0">
            <li>
                <a rel="noopener"  class="link text-theme-light" href="http://twitter.com/biothingsapi" target="_blank">
                Twitter
                </a>
            </li>
            <li>
                <a rel="noopener"  class="link text-theme-light" href="https://github.com/biothings/biothings.api" target="_blank">
                Github
                </a>
            </li>
            </ul>
            <hr />
            <small class="text-theme-light">
            All content copyright <a href="http://biothings.io" class="link">BioThings.io</a> © {{ year }} <br /> All rights reserved.
            <a rel="noopener"  target="_blank" href="http://biothings.io/terms" class="link">Terms of use.</a>
            <a rel="noopener"  target="_blank" href="http://biothings.io/citation/" class="link">How To Cite</a>
            </small>
        </div>
    </footer>
</template>