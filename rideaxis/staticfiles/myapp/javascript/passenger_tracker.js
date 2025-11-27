// myapp/static/myapp/javascript/passenger_tracker.js

function initializePassengerMap() {
    const mapContainer = document.getElementById('map-container');
    
    // 1. Basic check to ensure the necessary elements and library are loaded
    if (!mapContainer || typeof L === 'undefined') {
        console.warn('Map container or Leaflet library missing. Cannot initialize passenger map.');
        return;
    }
    
    // 2. Get coordinates from the HTML data attributes
    const lat = parseFloat(mapContainer.dataset.lat);
    const lon = parseFloat(mapContainer.dataset.lon);

    if (isNaN(lat) || isNaN(lon)) {
        console.error('Invalid coordinates received from server. Check Django view and template.');
        // Display a simple error message to the user if the coordinates are bad
        mapContainer.innerHTML = "<p>Tracking error: Invalid location data.</p>";
        return;
    }

    // 3. Initialize the Leaflet Map
    // Set the view to the received coordinates with zoom level 13
    const map = L.map('passenger-map').setView([lat, lon], 13);

    // Add the OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // 4. Add the Marker for the Driver's Last Known Location
    L.marker([lat, lon]).addTo(map)
        .bindPopup("Driver's Last Known Location")
        .openPopup();
        
    // 5. Fix common map display issue
    // This forces Leaflet to recalculate the map size after the container is visible
    setTimeout(() => {
        map.invalidateSize();
    }, 100); 
}

// Attach the initialization function to run once the entire page content is loaded
window.addEventListener('load', initializePassengerMap);