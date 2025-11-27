
var map = L.map('map').setView([11.5630, 124.4013], 17); 
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

L.marker([11.5630, 124.4013])
  .addTo(map)
  .bindPopup("<b>RideAxis HQ</b><br>BIPSU STCS Building, 2nd Floor")
  .openPopup();
