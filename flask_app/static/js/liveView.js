// Live map view functions

function initLiveMap(cities) {
    clear_map();
    console.log("Initializing Live Map for city:", currentCity);

    addBaseMapTile(map);
    addVehicleCountControl(map);
    updateMapInfoLive(currentAgency);
    // updatePerformance(currentAgency);
    fetchAndUpdate(currentCity);
    interval = setInterval(() => fetchAndUpdate(currentCity), 10000);
}

function updateLiveMap() {
    updateMapInfoLive(currentAgency);
    // updatePerformance(currentAgency);
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

function updateMapInfoLive(agency) {
    const dateInput = document.getElementById("performance-date-selector");
    const selectedDate = dateInput.value;

    if (!selectedDate) {
        console.warn("No date selected for performance data.");
        setTimeout(() => {
            updateMapInfoLive(agency);
        }, 2000);
        return;
    }

    function createTable(data, caption) {
        let rows = data.map((row, idx) => `
                <tr>
                    <th scope="row">${row.date}</th>
                    <td>${row.total_trips}</td>
                    <td>${row.mean_delay.toFixed(2)} ± ${row.std_delay.toFixed(2)}</td>
                </tr>
            `).join('');
        return `
                <table class="table table-striped table-hover table-borderless table-dark">
                    <thead>
                        <tr>
                            <th scope="col">Date</th>
                            <th scope="col">Total Trips</th>
                            <th scope="col">Mean Delay</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                    <caption>${caption}</caption>
                </table>
            `;
    }


    fetch(`/agency_delays/${agency}/${selectedDate}`)
        .then(res => res.json())
        .then(data => {
            const panel = document.querySelector('#map-info-panel .content');
            panel.innerHTML = '';
            panel.innerHTML += createTable(data, "Last 7 days performance data for " + agency);
        });

}


function makeAgencyPerformanceTable(data, caption) {
    const panel = document.querySelector('#map-info-panel .content');
    if (panel) {
        panel.innerHTML = '';

        function createTable(stops, caption) {
            let rows = stops.map((stop, idx) => `
                <tr>
                    <th scope="row">${idx + 1}</th>
                    <td style="word-break:break-word;max-width:180px;">${stop.stop_name}</td>
                    <td>${stop.total_trips}</td>
                    <td>${stop.mean_delay.toFixed(2)}</td>
                </tr>
            `).join('');
            return `
                <table class="table table-striped table-hover table-borderless table-dark">
                    <thead>
                        <tr>
                            <th scope="col">#</th>
                            <th scope="col">Stop Name</th>
                            <th scope="col">Total Trips</th>
                            <th scope="col">Mean Delay</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                    <caption>${caption}</caption>
                </table>
            `;
        }

        const dateCaption = `Last 7 days from ${dateInput.value} after dropping outliers`;

        if (top && top.length) {
            panel.innerHTML += createTable(top, `Top 5 Stops (${dateCaption})`);
        }
        if (bottom && bottom.length) {
            panel.innerHTML += createTable(bottom, `Bottom 5 Stops (${dateCaption})`);
        }
    }
}