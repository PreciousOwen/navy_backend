document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM fully loaded and parsed");

    var start_latitude = parseFloat(document.getElementById('start_latitude').value);
    var start_longitude = parseFloat(document.getElementById('start_longitude').value);
    var end_latitude = parseFloat(document.getElementById('end_latitude').value);
    var end_longitude = parseFloat(document.getElementById('end_longitude').value);

    console.log("Start Latitude:", start_latitude);
    console.log("Start Longitude:", start_longitude);
    console.log("End Latitude:", end_latitude);
    console.log("End Longitude:", end_longitude);

    // Ensure the coordinates are valid numbers
    if (!isNaN(start_latitude) && !isNaN(start_longitude) && !isNaN(end_latitude) && !isNaN(end_longitude)) {
        console.log("Valid coordinates provided");
        // Set the initial view of the map to the start coordinates
        var map = L.map('map').setView([start_latitude, start_longitude], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        var startPoint = L.marker([start_latitude, start_longitude]).addTo(map);
        var endPoint = L.marker([end_latitude, end_longitude]).addTo(map);

        var routeControl = L.Routing.control({
            waypoints: [
                L.latLng(start_latitude, start_longitude),
                L.latLng(end_latitude, end_longitude)
            ],
            router: new L.Routing.OSRMv1({
                serviceUrl: 'https://router.project-osrm.org/route/v1'
            }),
            routeWhileDragging: true,
            createMarker: function() { return null; }, // Disable default markers
            lineOptions: {
                styles: [{ color: 'blue', weight: 4 }]
            }
        }).addTo(map);

        routeControl.on('routesfound', function(e) {
            var route = e.routes[0];
            var bounds = route.bounds;
            map.fitBounds(bounds);
            console.log("Route found:", route);
        });

        routeControl.on('routingerror', function(e) {
            console.error("Routing error:", e);
            console.error("Error details:", e.error);
            // Fallback: Draw a straight line between the points if routing fails
            var polyline = L.polyline([
                [start_latitude, start_longitude],
                [end_latitude, end_longitude]
            ], { color: 'red' }).addTo(map);
            map.fitBounds(polyline.getBounds());
        });
    } else {
        console.error("Invalid coordinates provided.");
    }
});
