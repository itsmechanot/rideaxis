// ====================================================================
// RIDE TRACKER JAVASCRIPT: Handles Geolocation, Local Storage, & Sync
// ====================================================================

const RIDE_ID = document.getElementById('map-container').dataset.rideId; // Get Ride ID from HTML
const SYNC_URL = '/save-location/'; // Django URL name 'save_location'
const STORAGE_KEY = `offline_locations_ride_${RIDE_ID}`;
const TRACKING_INTERVAL = 10000; // Track location every 10 seconds (10,000 ms)
const SYNC_BATCH_SIZE = 10; // Send up to 10 points per sync attempt

let map = null;
let marker = null;
let trackingTimer = null;

// --- 1. LOCAL STORAGE MANAGEMENT ---

/**
 * Loads the array of unsynced location points from local storage.
 * @returns {Array} List of location objects.
 */
function getOfflineLocations() {
    const json = localStorage.getItem(STORAGE_KEY);
    return json ? JSON.parse(json) : [];
}

/**
 * Saves the current list of unsynced location points back to local storage.
 * @param {Array} locations 
 */
function saveOfflineLocations(locations) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(locations));
}

/**
 * Adds a new location object to the local storage queue.
 * @param {Object} location - {latitude, longitude}
 */
function queueLocation(location) {
    const locations = getOfflineLocations();
    locations.push(location);
    saveOfflineLocations(locations);
    console.log(`Location queued. Total offline points: ${locations.length}`);
}


// --- 2. MAP INITIALIZATION & UPDATE ---

/**
 * Initializes the Leaflet map centered at the initial position.
 * @param {Object} position - Geolocation position object
 */
function initializeMap(position) {
    const lat = position.coords.latitude;
    const lon = position.coords.longitude;

    map = L.map('live-map').setView([lat, lon], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    marker = L.marker([lat, lon]).addTo(map)
        .bindPopup("Driver's Current Location")
        .openPopup();
}

/**
 * Updates the map marker and view with a new position.
 * @param {Object} position - Geolocation position object
 */
function updateMap(position) {
    const lat = position.coords.latitude;
    const lon = position.coords.longitude;
    const newLatLng = new L.LatLng(lat, lon);

    // Update marker position
    if (marker) {
        marker.setLatLng(newLatLng);
    } else {
        // If marker doesn't exist (e.g., failed to init), create it.
        marker = L.marker(newLatLng).addTo(map)
            .bindPopup("Driver's Current Location")
            .openPopup();
    }
    
    // Pan map to new location
    map.panTo(newLatLng);
}


// --- 3. SYNCING AND OFFLINE HANDLING ---

/**
 * Sends a batch of location points to the server.
 * @param {Array} locations - Array of location objects to sync.
 * @param {Function} successCallback - Function to call on successful sync.
 */
async function syncLocations(locations, successCallback) {
    if (locations.length === 0) {
        return;
    }
    
    // Get CSRF token for security
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const locationData = locations.map(loc => ({
        ride_id: RIDE_ID,
        latitude: loc.latitude,
        longitude: loc.longitude,
    }));
    
    try {
        const response = await fetch(SYNC_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken,
            },
            body: JSON.stringify(locationData[0]), // Send one by one for simplicity, or the whole batch for performance
                                                   // NOTE: Since the Django view expects a single location, we send the first one in the batch.
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.status === 'success') {
                console.log(`Successfully synced location.`);
                // If successful, remove the location from the local storage queue
                successCallback();
            } else {
                console.error('Server reported sync failure:', result.message);
            }
        } else {
            console.error('HTTP Error during sync:', response.status);
            // Treat non-OK response (server error) as temporary offline and stop sync attempt
        }
    } catch (error) {
        // Network error (dead spot) - log and wait for next sync attempt
        console.warn('Network error during sync attempt. Dead spot? Waiting for connection.', error);
    }
}


/**
 * Attempts to sync all queued location points (in batches).
 */
function attemptSync() {
    let locations = getOfflineLocations();

    // Loop through the queue and sync one point at a time (simplified sync logic)
    if (locations.length > 0) {
        const locationToSync = locations[0];
        
        syncLocations([locationToSync], () => {
            // Success: Remove the synced location and update local storage
            locations = getOfflineLocations(); // Re-read in case others were added
            locations.shift(); // Remove the first element (the one just synced)
            saveOfflineLocations(locations);
            
            // Immediately try to sync the next one in the queue
            attemptSync(); 
        });
    }
}


// --- 4. MAIN TRACKING LOOP ---

/**
 * Main function run at the TRACKING_INTERVAL.
 * Gets location, updates map, queues location, and attempts sync.
 */
function trackAndSyncLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by this browser. Live tracking disabled.');
        return;
    }

    navigator.geolocation.getCurrentPosition(
        (position) => { // Success Callback
            
            // Location point to be saved/synced
            const locationPoint = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };

            // 1. Update Map (Must be done first)
            if (!map) {
                initializeMap(position);
            } else {
                updateMap(position);
            }
            
            // 2. Queue the location locally (always queue first for redundancy)
            queueLocation(locationPoint);
            
            // 3. Attempt to sync the queue immediately
            attemptSync();

        }, 
        (error) => { // Error Callback
            console.error(`Geolocation error: ${error.message}`);
            // If tracking fails, we don't queue anything, but we still try to sync old data.
            attemptSync(); 
        },
        { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
    );
}

// --- 5. INITIALIZATION ---

/**
 * Starts the tracking process if the required elements exist.
 */
function startTracking() {
    // Ensure Leaflet is loaded and we have a ride ID
    if (typeof L === 'undefined' || !RIDE_ID) {
        console.error('Leaflet or Ride ID missing. Tracking aborted.');
        return;
    }
    
    // Start the periodic location tracking and syncing
    trackingTimer = setInterval(trackAndSyncLocation, TRACKING_INTERVAL);
    console.log(`Tracking started for Ride ${RIDE_ID}. Interval: ${TRACKING_INTERVAL / 1000}s`);
    
    // Immediately attempt to sync any old, remaining offline data (e.g., from a previous crash)
    attemptSync();
}

// Run the initialization when the window loads
window.addEventListener('load', startTracking);

// Optionally stop tracking when the driver signs out or leaves the page
window.addEventListener('beforeunload', () => {
    if (trackingTimer) {
        clearInterval(trackingTimer);
        console.log('Tracking stopped.');
    }
});