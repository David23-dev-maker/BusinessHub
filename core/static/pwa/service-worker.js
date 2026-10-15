const CACHE_NAME = "businesshub-v1";

const STATIC_ASSETS = [
    "/",
    "/static/css/base.css",
    "/static/js/base.js"
];


self.addEventListener("install", function (event) {

    event.waitUntil(

        caches.open(CACHE_NAME).then(function (cache) {

            return cache.addAll(STATIC_ASSETS);

        })

    );

    self.skipWaiting();

});


self.addEventListener("activate", function (event) {

    event.waitUntil(

        caches.keys().then(function (cacheNames) {

            return Promise.all(

                cacheNames
                    .filter(function (cacheName) {

                        return (
                            cacheName !== CACHE_NAME
                        );

                    })
                    .map(function (cacheName) {

                        return caches.delete(
                            cacheName
                        );

                    })

            );

        })

    );

    self.clients.claim();

});


self.addEventListener("fetch", function (event) {

    if (
        event.request.method !== "GET"
    ) {
        return;
    }

    event.respondWith(

        fetch(event.request)
            .then(function (response) {

                return response;

            })
            .catch(function () {

                return caches.match(
                    event.request
                );

            })

    );

});
