// self.addEventListener('push', function (event) {
//     const data = event.data ? event.data.json() : {};
//     const title = data.title || 'EstateAgent AI Alert';
//     const options = {
//         body: data.message || 'You have a new update on your property listing!',
//         icon: '/favicon.ico',
//         badge: '/favicon.ico'
//     };
//     event.waitUntil(self.registration.showNotification(title, options));
// });