// Check that service workers are registered
if ('serviceWorker' in navigator) {
  // Use the window load event to keep the page load performant
  window.addEventListener('load', () => {
    try{
      navigator.serviceWorker.register('/static/html/worker.js',{
        'scope':"/static/html/"
      }).then(function(ServiceWorkerRegistration) {
        console.log('Service Worker registered');
      }).catch(err=>{
        console.log('Service Worker registration failed');
      });
    }catch(err){
      console.log('failed');
    }
  });
}

// console.log(caches)
