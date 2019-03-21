//WORKBOX

importScripts('https://storage.googleapis.com/workbox-cdn/releases/3.0.0/workbox-sw.js');

  workbox.precaching.precacheAndRoute([
    {
      "url": "/static/css/app.css",
      "revision": "fd2e1d3c4c8d43da10afe67a7d69fbd1"
    },
    {
      "url": "/",
      "revision": "39b8fb34f8be7ecf969530f1b9e69ba1"
    },
    {
      "url": "/static/js/contribute.js",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "/static/js/renderjson.js",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "/denovodb",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "/static/js/worker.js",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "https://pending.biothings.io/",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "https://pending.biothings.io/denovodb/metadata",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "https://pending.biothings.io/fire/metadata",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "https://pending.biothings.io/ccle/metadata",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "https://pending.biothings.io/biomuta/metadata",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    },
    {
      "url": "https://pending.biothings.io/kaviar/metadata",
      "revision": "03bde26b6af07cd6bb0378ec0a50e410"
    }
  ]);

  workbox.routing.registerRoute(
    new RegExp('https://pending.biothings.io/denobodb/metadata'),
    workbox.strategies.cacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('https://pending.biothings.io/biomuta/metadata'),
    workbox.strategies.cacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('https://pending.biothings.io/fire/metadata'),
    workbox.strategies.cacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('https://pending.biothings.io/kaviar/metadata'),
    workbox.strategies.cacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('https://pending.biothings.io/'),
    workbox.strategies.cacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('https://pending.biothings.io/ccle/metadata'),
    workbox.strategies.cacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('/'),
    new workbox.strategies.CacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('/denobodb'),
    new workbox.strategies.CacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('/static/js/contribute.js'),
    new workbox.strategies.CacheFirst()
  );

  workbox.routing.registerRoute(
    new RegExp('/static/js/renderjson.js'),
    new workbox.strategies.CacheFirst()
  );

  // VANILLA JS

  // console.log('SW Working');

  // self.addEventListener("install", function(event) {
  //   event.waitUntil(preLoad());
  // });
  //
  // var preLoad = function(){
  //   console.log("Installing web app");
  //   return caches.open("offline").then(function(cache) {
  //     console.log("caching index and important routes");
  //     return cache.addAll([
  //               '/',
  //               '/static/js/renderjson.js',
  //               "/static/css/app.css",
  //               '/static/js/contribute.js',
  //               "https://pending.biothings.io/denovodb/metadata",
  //               "https://pending.biothings.io/ccle/metadata",
  //               "https://pending.biothings.io/kaviar/metadata",
  //               "https://pending.biothings.io/biomuta/metadata",
  //               "https://pending.biothings.io/fire/metadata",
  //             ]);
  //   });
  // };
  //
  // self.addEventListener("fetch", function(event) {
  //   event.respondWith(checkResponse(event.request).catch(function() {
  //     return returnFromCache(event.request);
  //   }));
  //   event.waitUntil(addToCache(event.request));
  // });
  //
  // var checkResponse = function(request){
  //   return new Promise(function(fulfill, reject) {
  //     fetch(request).then(function(response){
  //       if(response.status !== 404) {
  //         fulfill(response);
  //       } else {
  //         reject();
  //       }
  //     }, reject);
  //   });
  // };
  //
  // var addToCache = function(request){
  //   return caches.open("offline").then(function (cache) {
  //     return fetch(request).then(function (response) {
  //       console.log(response.url + " was cached");
  //       return cache.put(request, response);
  //     });
  //   });
  // };
  //
  // var returnFromCache = function(request){
  //   return caches.open("offline").then(function (cache) {
  //     return cache.match(request).then(function (matching) {
  //      if(!matching || matching.status == 404) {
  //        return cache.match("offline.html");
  //      } else {
  //        return matching;
  //      }
  //     });
  //   });
  // };

  // var self = this;
  //
  // self.addEventListener('install', function (event) {
  //   console.log('SW Installed');
  //   event.waitUntil(
  //     caches.open('static')
  //       .then(function (cache) {
  //         cache.addAll([
  //           '/',
  //           '/static/js/renderjson.js',
  //           "/static/css/app.css",
  //           '/static/js/contribute.js',
  //           "https://pending.biothings.io/",
  //           "https://pending.biothings.io/denovodb/metadata",
  //           "https://pending.biothings.io/ccle/metadata",
  //           "https://pending.biothings.io/kaviar/metadata",
  //           "https://pending.biothings.io/biomuta/metadata",
  //           "https://pending.biothings.io/fire/metadata",
  //         ]);
  //       })
  //   );
  // });
  //
  // self.addEventListener('activate', function () {
  //   console.log('SW Activated');
  //   self.clients.claim();
  // });
  //
  // self.addEventListener('fetch', function(event) {
  //   console.log('FETCH',event.request);
  //   event.respondWith(
  //     caches.match(event.request)
  //       .then(function(response) {
  //         if (response) {
  //               // retrieve from cache
  //               console.log('Found ', event.request.url, ' in cache');
  //               return response;
  //           }
  //
  //           // if not found in cache, return default offline content (only if this is a navigation request)
  //           if (event.request.mode === 'navigate') {
  //               return caches.match('/');
  //           }
  //
  //           // fetch as normal
  //           console.log('Network request for ', event.request.url);
  //           return fetch(event.request);
  //       })
  //   );
  // });
