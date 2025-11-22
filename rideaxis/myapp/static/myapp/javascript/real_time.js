  function updateTime() {
    const now = new Date();
    const dateOptions = { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'Asia/Manila' };
    const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Manila' };

    document.getElementById('current-time').textContent =
      `${now.toLocaleDateString('en-PH', dateOptions)} ${now.toLocaleTimeString('en-PH', timeOptions)}`;
  }

  setInterval(updateTime, 1000);
  updateTime();


  function filterRides() {
    const searchValue = document.getElementById('search-bar').value.trim().toLowerCase();
    const routeValue = document.getElementById('route-filter').value.trim().toLowerCase();
    const rides = document.querySelectorAll('.ride-card');

    rides.forEach(ride => {
      const text = ride.textContent.toLowerCase();
      const route = ride.querySelector('.ride-route')?.textContent.toLowerCase() || "";

      const matchSearch = text.includes(searchValue);
      const matchRoute = routeValue === "" || route.includes(routeValue);

      ride.style.display = (matchSearch && matchRoute) ? "block" : "none";
    });
  }

  let searchTimeout;
  document.getElementById('search-bar').addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(filterRides, 200); 
  });

  document.getElementById('route-filter').addEventListener('change', filterRides);