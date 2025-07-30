let map = L.map("map");
let heatmap;
let mapLayers = [];
let markers = {};
let heatmapLayer;
let interval;
let currentCity = "Phoenix";
let currentAgency = "ValleyMetro";
let currentCoordinates = [33.4484, -112.0740];
map.setView(currentCoordinates, 12);
let curentView;

// Toggle between views
function init_app(cities) {
    setView(currentCoordinates, 12);
    initCityDropdown(cities, currentCity);
    initDateSelector(currentAgency);
    console.log("cities:", cities);

    const selectedView = document.querySelector('input[name="viewMode"]:checked')?.value || "viewLive";
    // const cities = window.cityData; // assuming you set this globally when you load cities
    console.log("Selected view:", selectedView);
    console.log("Current view:", curentView);
    if (selectedView === curentView === "viewLive") {
        updateLiveMap();
    } else if (selectedView === curentView === "viewStops") {
        updateHeatMap(currentCity);
    } else if (selectedView === curentView === "viewRoutes") {
        // updateRoutesMap();
    } else if (selectedView === "viewLive") {
        curentView = "viewLive";
        initLiveMap(cities);
    } else if (selectedView === "viewStops") {
        clearInterval(interval)
        curentView = "viewStops";
        initHeatmap(cities);
    } else if (selectedView === "viewRoutes") {
        clearInterval(interval)
        curentView = "viewRoutes";
        initRoutesView(cities);
    }

}

// Attach change listener for mode toggle
window.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('input[name="viewMode"]').forEach(radio => {
        radio.addEventListener("change", () => init_app(cities));
    });
});

document.getElementById("performance-date-selector").addEventListener("change", (e) => {
    console.log("Date changed:", e.target.value);
    init_app(cities)
})

function initLiveMap(cities) {
    clear_map()
    console.log("Initializing Live Map for city:", currentCity);
    const defaultCoords = cities[currentCity].coordinates;
    const defaultAgency = cities[currentCity].agency;

    // map.setView(defaultCoords, 12);

    addBaseMapTile(map);
    addVehicleCountControl(map);
    // initDateSelector(defaultAgency);
    updatePerformance(currentAgency);
    fetchAndUpdate(currentCity);
    interval = setInterval(() => fetchAndUpdate(currentCity), 10000);
    // initCityDropdown(cities, currentCity);

}

function updateLiveMap() {
    updatePerformance(currentAgency);
}

function initHeatmap(cities) {
    clear_map()
    console.log("Initializing Heat Map for city:", currentCity);
    const defaultCoords = cities[currentCity].coordinates;
    const defaultAgency = cities[currentCity].agency;

    // map = L.map("map").setView(defaultCoords, 12);
    addBaseMapTile(map);
    addHeatmapLegend(map);
    updateHeatmap(currentCity);
}

function initRoutesView(cities) {
    clear_map()
    // Placeholder for Routes Delay init logic
    console.log("Routes Delay view selected");
    // implement when ready
}

// function clear_map() {
//     if (mapLayers.length > 0) {
//         mapLayers.forEach(layer => {
//             if (map.hasLayer(layer)) {
//                 map.removeLayer(layer);
//             }
//         });
//         mapLayers = [];
//     }
// }

function initCityDropdown(cities, defaultCity) {
    const dropdownMenu = document.getElementById("cityDropdownMenu");
    const dropdownToggle = document.getElementById("navbarDropdownMenuLink");
    const agencySpan = document.getElementById("selected-city-agency");
    console.log("Initializing city dropdown with default city:", defaultCity);
    dropdownMenu.innerHTML = "";

    Object.entries(cities).forEach(([city, data]) => {
        const item = document.createElement("a");
        item.className = "dropdown-item";
        item.href = "#";
        item.textContent = city;

        item.addEventListener("click", (e) => {
            e.preventDefault();
            currentCity = city;
            currentAgency = data.agency;
            currentCoordinates = data.coordinates;
            dropdownToggle.textContent = city;
            agencySpan.textContent = `(${data.agency.replace(/([a-z])([A-Z])/g, "$1 $2")})`;

            clearInterval(interval);
            markers = {};
            setView(data.coordinates);
            init_app(cities);
        });
        dropdownMenu.appendChild(item);
    });

}

// function initDateSelector(agency) {
//     console.log("Initializing date selector for agency:", agency);
//     const dateInput = document.getElementById("performance-date-selector");
//     const now = new Date();

//     let maxDate = new Date(now);
//     maxDate.setDate(now.getDate() - (now.getHours() >= 3 ? 1 : 2));

//     fetch(`/oldest_date/${agency}`)
//         .then(res => res.json())
//         .then(data => {
//             console.log("Oldest date data:", data);
//             const minDate = new Date(data.oldest_date);
//             dateInput.min = minDate.toISOString().split('T')[0];
//             dateInput.max = maxDate.toISOString().split('T')[0];
//             dateInput.value = dateInput.max;
//         });

// }

function setView(coords) {
    map.flyTo(coords, 12);

    // for (let id in markers) {
    //     if (map) map.removeLayer(markers[id].marker);
    //     if (map) map.removeLayer(markers[id].trailLine);
    // }
    // markers = {};
}

function addBaseMapTile(targetMap) {
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png", {
        attribution: "©OpenStreetMap, ©CartoDB"
    }).addTo(targetMap);
}

// function addVehicleCountControl(map) {
//     // Check if the status div already exists
//     let statusDiv = document.getElementById("live-status-map-div");
//     if (statusDiv) {
//         statusDiv.innerHTML = "Connecting … 🔴";
//         return;
//     }

//     const VehicleCount = L.Control.extend({
//         options: { position: "bottomright" },
//         onAdd: () => {
//             const div = L.DomUtil.create("div", "live-status-control");
//             div.id = "live-status-map-div";
//             div.innerHTML = "Connecting … 🔴";
//             return div;
//         }
//     });
//     map.addControl(new VehicleCount());
// }

// function fetchAndUpdate(city) {
//     fetch(`/positions/${city}`)
//         .then(res => res.json())
//         .then(data => {
//             updateVehicleCount(data.length);
//             data.forEach(updateOrCreateMarker);
//         });
// }

// function updateOrCreateMarker(v) {
//     const id = v.vehicle_id;
//     const latlng = [v.lat, v.lon];

//     if (markers[id]) {
//         markers[id].marker.setLatLng(latlng);
//         markers[id].trailLine.setLatLngs(v.trail);
//     } else {
//         const trailLine = L.polyline(v.trail, {
//             color: v.route_color,
//             weight: 3,
//             opacity: 0.7
//         }).addTo(map);

//         const marker = L.circleMarker(latlng, {
//             radius: 7,
//             color: v.route_color,
//             fillOpacity: 0.9
//         }).addTo(map).bindPopup(`${v.route_short_name}: ${v.trip_headsign}<br>${v.last_timestamp}`);
//         markers[id] = { marker, trailLine };
//         mapLayers.push(marker, trailLine);
//     }

// }

// function updateVehicleCount(count) {
//     const statusDiv = document.getElementById("live-status-map-div");
//     statusDiv.innerHTML = count === 0
//         ? "Fetching … 🔴"
//         : "Tracking " + count + " vehicles 🟢";
// }

// function updatePerformance(agency) {
//     const dateInput = document.getElementById("performance-date-selector");
//     const selectedDate = dateInput.value;

//     if (!selectedDate) {
//         console.warn("No date selected for performance data.");
//         setTimeout(() => {
//             updatePerformance(agency);
//         }, 2000);
//         return;
//     }

//     fetch(`/agency_delays/${agency}/${selectedDate}`)
//         .then(res => res.json())
//         .then(data => {
//             console.log("Performance Data:", data);
//             document.getElementById("meanDelay").textContent = data[0].mean_delay !== undefined
//                 ? (data[0].mean_delay / 60).toFixed(2)
//                 : "-";
//             if (data[0].std_delay !== undefined) {
//                 document.getElementById("meanDelay").textContent += " ±" + (data[0].std_delay / 60).toFixed(2);
//             }
//             document.getElementById("totalTrips").textContent = data[0].total_trips || "-";
//         });
// }

// function updateHeatmap(city) {
//     const dateInput = document.getElementById("performance-date-selector");
//     // Wait until the date input has a value (user has selected a date)
//     if (!dateInput.value) return;
//     const selectedDate = dateInput.value;

//     fetch(`/stop_delays/${city}/${selectedDate}`)
//         .then(res => res.json())
//         .then(data => {
//             if (heatmapLayer && map.hasLayer(heatmapLayer)) {
//                 heatmap.removeLayer(heatmapLayer);
//             }
//             heatmapLayer = L.heatLayer(data.map(d => [d.stop_lat, d.stop_lon, d.scaled_delay]), {
//                 radius: 25,
//                 blur: 15,
//                 maxZoom: 13,
//                 gradient: {
//                     0.0: '#00ff00',   // bright green (very early)
//                     0.25: '#aaff00',  // yellow-green
//                     0.5: '#ffff00',   // yellow (on time)
//                     0.75: '#ff7f00',  // orange
//                     1.0: '#ff0000'    // red (very late)
//                 }
//             }).addTo(map);
//             mapLayers.push(heatmapLayer);
//         });
// }

// function addHeatmapLegend(map) {
//     const legend = L.control({ position: 'bottomright' });

//     legend.onAdd = function () {
//         const div = L.DomUtil.create('div', 'info legend');
//         const grades = [0.0, 0.25, 0.5, 0.75, 1.0];
//         const labels = ['Very Early', 'Early', 'On Time', 'Late', 'Very Late'];
//         const colors = ['#00ff00', '#aaff00', '#ffff00', '#ff7f00', '#ff0000'];

//         div.innerHTML += '<strong>Delay Intensity</strong><br>';

//         for (let i = 0; i < grades.length; i++) {
//             div.innerHTML +=
//                 `<i style="background:${colors[i]}; width:18px; height:18px; display:inline-block; margin-right:8px;"></i> ${labels[i]}<br>`;
//         }

//         return div;
//     };

//     legend.addTo(map);
// }
