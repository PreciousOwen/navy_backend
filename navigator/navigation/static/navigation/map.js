document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM fully loaded and parsed");

    var start_latitude = parseFloat(document.getElementById('start_latitude').value);
    var start_longitude = parseFloat(document.getElementById('start_longitude').value);
    var end_latitude = parseFloat(document.getElementById('end_latitude').value);
    var end_longitude = parseFloat(document.getElementById('end_longitude').value);
    var route_coordinates = JSON.parse(document.getElementById('route_coordinates').value);

    console.log("Start Latitude:", start_latitude);
    console.log("Start Longitude:", start_longitude);
    console.log("End Latitude:", end_latitude);
    console.log("End Longitude:", end_longitude);
    console.log("Route Coordinates:", route_coordinates);

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

        if (route_coordinates.length > 0) {
            // Draw the route on the map
            var routePolyline = L.polyline(route_coordinates, { color: 'blue', weight: 4 }).addTo(map);
            map.fitBounds(routePolyline.getBounds());
        } else {
            console.error("No route found.");
        }
    } else {
        console.error("Invalid coordinates provided.");
    }
});
