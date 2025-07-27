let map;
let markers = {};
let interval;
const cityCoords = {
    Phoenix: [33.4484, -112.0740],
    Boston: [42.3554, -71.0605]
};

function initMap(cities) {
    const citySelect = document.getElementById("citySelect");
    cities.forEach(c => {
        const option = document.createElement("option");
        option.value = c;
        option.text = c;
        citySelect.add(option);
    });

    citySelect.addEventListener("change", () => {
        clearInterval(interval);
        setView(citySelect.value);
        fetchAndUpdate(citySelect.value);
        interval = setInterval(() => fetchAndUpdate(citySelect.value), 10000);
    });

    map = L.map("map").setView(cityCoords[cities[0]], 12);
    // L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png', {
        attribution: '©OpenStreetMap, ©CartoDB'
    }).addTo(map);
    fetchAndUpdate(cities[0]);
    interval = setInterval(() => fetchAndUpdate(cities[0]), 10000);
}

function setView(city) {
    map.flyTo(cityCoords[city], 12);

    for (let id in markers) {
        map.removeLayer(markers[id]);
    }
    markers = {};
}

// function fetchAndUpdate(city) {
//     fetch(`/positions/${city}`)
//         .then(res => res.json())
//         .then(data => {
//             data.forEach(v => {
//                 const id = v.vehicle_id;
//                 const latlng = [v.lat, v.lon];
//                 if (markers[id]) {
//                     markers[id].setLatLng(latlng);
//                 } else {
//                     const marker = L.circleMarker(latlng, {
//                         radius: 7,
//                         color: v.route_color,
//                         fillOpacity: 0.9
//                     }).addTo(map).bindPopup(`${v.route_short_name}: ${v.trip_headsign}`);
//                     markers[id] = marker;
//                 }
//             });
//         });
// }
function fetchAndUpdate(city) {
    fetch(`/positions/${city}`)
        .then(res => res.json())
        .then(data => {
            data.forEach(v => {
                const id = v.vehicle_id;
                const latlng = [v.lat, v.lon];

                if (markers[id]) {
                    // Update existing marker position
                    markers[id].marker.setLatLng(latlng);
                    // Update polyline path
                    markers[id].trailLine.setLatLngs(v.trail);
                } else {
                    // Create polyline for trail
                    const trailLine = L.polyline(v.trail, {
                        color: v.route_color,
                        weight: 3,
                        opacity: 0.7
                    }).addTo(map);

                    // Create circle marker for latest position
                    const marker = L.circleMarker(latlng, {
                        radius: 7,
                        color: v.route_color,
                        fillOpacity: 0.9
                    }).addTo(map).bindPopup(`${v.route_short_name}: ${v.trip_headsign}`);

                    // Store both in markers object
                    markers[id] = {
                        marker: marker,
                        trailLine: trailLine
                    };
                }
            });
        });
}

