//WORKBOX

// importScripts('https://storage.googleapis.com/workbox-cdn/releases/3.0.0/workbox-sw.js');

  // workbox.precaching.precacheAndRoute([
  //   {
  //     "url": "/static/css/app.css",
  //     "revision": "fd2e1d3c4c8d43da10afe67a7d69fbd1"
  //   },
  //   {
  //     "url": "/",
  //     "revision": "39b8fb34f8be7ecf969530f1b9e69ba1"
  //   },
  //   {
  //     "url": "/static/js/contribute.js",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "/static/js/renderjson.js",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "/denovodb",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "/static/js/worker.js",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "http://pending.biothings.io/denovodb/metadata",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "http://pending.biothings.io/fire/metadata",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "http://pending.biothings.io/ccle/metadata",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "http://pending.biothings.io/biomuta/metadata",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   },
  //   {
  //     "url": "http://pending.biothings.io/kaviar/metadata",
  //     "revision": "03bde26b6af07cd6bb0378ec0a50e410"
  //   }
  // ]);
  //
  // workbox.routing.registerRoute(
  //   new RegExp('http://pending.biothings.io/denobodb/metadata'),
  //   workbox.strategies.cacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('http://pending.biothings.io/biomuta/metadata'),
  //   workbox.strategies.cacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('http://pending.biothings.io/fire/metadata'),
  //   workbox.strategies.cacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('http://pending.biothings.io/kaviar/metadata'),
  //   workbox.strategies.cacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('http://pending.biothings.io/ccle/metadata'),
  //   workbox.strategies.cacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('/'),
  //   new workbox.strategies.CacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('/denobodb'),
  //   new workbox.strategies.CacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('/static/js/contribute.js'),
  //   new workbox.strategies.CacheFirst()
  // );
  //
  // workbox.routing.registerRoute(
  //   new RegExp('/static/js/renderjson.js'),
  //   new workbox.strategies.CacheFirst()
  // );

  // VANILLA JS

  console.log('SW Working');

  var self = this;

  self.addEventListener('install', function (event) {
    console.log('SW Installed');
    event.waitUntil(
      caches.open('static')
        .then(function (cache) {
          cache.addAll([
            '/',
            '/static/js/renderjson.js',
            "/static/css/app.css",
            '/static/js/contribute.js',
            "http://pending.biothings.io/denovodb/metadata",
            "http://pending.biothings.io/ccle/metadata",
            "http://pending.biothings.io/kaviar/metadata",
            "http://pending.biothings.io/biomuta/metadata",
            "http://pending.biothings.io/fire/metadata",
          ]);
        })
    );
  });

  self.addEventListener('activate', function () {
    console.log('SW Activated');
    self.clients.claim();
  });

  self.addEventListener('fetch', function(event) {
    console.log('FETCH',event.request);
    event.respondWith(
      caches.match(event.request)
        .then(function(response) {
          if (response) {
                // retrieve from cache
                console.log('Found ', event.request.url, ' in cache');
                return response;
            }

            // if not found in cache, return default offline content (only if this is a navigation request)
            if (event.request.mode === 'navigate') {
                return caches.match('/');
            }

            // fetch as normal
            console.log('Network request for ', event.request.url);
            return fetch(event.request);
        })
    );
  });

  // Alternative FETCH solution

  // self.addEventListener('fetch', function(event) {
  //   event.respondWith(
  //     caches.match(event.request)
  //       .then(function(response) {
  //         // Cache hit - return response
  //         if (response) {
  //           return response;
  //         }
  //
  //         // IMPORTANT: Clone the request. A request is a stream and
  //         // can only be consumed once. Since we are consuming this
  //         // once by cache and once by the browser for fetch, we need
  //         // to clone the response
  //         var fetchRequest = event.request.clone();
  //
  //         return fetch(fetchRequest).then(
  //           function(response) {
  //             // Check if we received a valid response
  //             if(!response || response.status !== 200 || response.type !== 'basic') {
  //               return response;
  //             }
  //
  //             // IMPORTANT: Clone the response. A response is a stream
  //             // and because we want the browser to consume the response
  //             // as well as the cache consuming the response, we need
  //             // to clone it so we have 2 stream.
  //             var responseToCache = response.clone();
  //
  //             caches.open(CACHE_NAME)
  //               .then(function(cache) {
  //                 cache.put(event.request, responseToCache);
  //               });
  //
  //             return response;
  //           }
  //         );
  //       })
  //     );
  // });
