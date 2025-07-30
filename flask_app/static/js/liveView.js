// Live map view functions

function initLiveMap(cities) {
    clear_map();
    console.log("Initializing Live Map for city:", currentCity);

    addBaseMapTile(map);
    addVehicleCountControl(map);
    updatePerformance(currentAgency);
    fetchAndUpdate(currentCity);
    interval = setInterval(() => fetchAndUpdate(currentCity), 10000);
}

function updateLiveMap() {
    updatePerformance(currentAgency);
}

function fetchAndUpdate(city) {
    fetch(`/positions/${city}`)
        .then(res => res.json())
        .then(data => {
            updateVehicleCount(data.length);
            data.forEach(updateOrCreateMarker);
        });
}

function updateOrCreateMarker(v) {
    const id = v.vehicle_id;
    const latlng = [v.lat, v.lon];

    if (markers[id]) {
        markers[id].marker.setLatLng(latlng);
        markers[id].trailLine.setLatLngs(v.trail);
    } else {
        const trailLine = L.polyline(v.trail, {
            color: v.route_color,
            weight: 3,
            opacity: 0.7
        }).addTo(map);

        const marker = L.circleMarker(latlng, {
            radius: 7,
            color: v.route_color,
            fillOpacity: 0.9
        }).addTo(map).bindPopup(`${v.route_short_name}: ${v.trip_headsign}<br>${v.last_timestamp}`);

        markers[id] = { marker, trailLine };
        mapLayers.push(marker, trailLine);
    }
}

function updateVehicleCount(count) {
    const statusDiv = document.getElementById("live-status-map-div");
    statusDiv.innerHTML = count === 0
        ? "Fetching … 🔴"
        : "Tracking " + count + " vehicles 🟢";
}