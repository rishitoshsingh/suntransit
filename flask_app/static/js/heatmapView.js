// Heatmap view functions

function initHeatmap(cities) {
    clear_map();
    console.log("Initializing Heat Map for city:", currentCity);

    addBaseMapTile(map);
    addHeatmapLegend(map);
    updateHeatmap(currentCity);
}

function updateHeatmap(city) {
    const dateInput = document.getElementById("performance-date-selector");
    if (!dateInput.value) return;
    const selectedDate = dateInput.value;

    fetch(`/stop_delays/${city}/${selectedDate}`)
        .then(res => res.json())
        .then(data => {
            // Remove existing heatmap layer if present
            if (heatmapLayer && map.hasLayer(heatmapLayer)) {
                map.removeLayer(heatmapLayer);
            }
            // Create new heatmap layer using delays data
            heatmapLayer = L.heatLayer(
                data.delays.map(d => [d.stop_lat, d.stop_lon, d.scaled_delay]),
                {
                    radius: 25,
                    blur: 15,
                    maxZoom: 13,
                    gradient: {
                        0.0: '#00ff00',
                        0.1: '#aaff00',
                        0.5: '#ffff00',
                        0.9: '#ff7f00',
                        1.0: '#ff0000'
                    }
                }
            ).addTo(map);
            mapLayers.push(heatmapLayer);
            green_stop_icon = L.icon({
                iconUrl: 'static/icons/bus-stop-green.png',
                iconSize: [48, 48],
                iconAnchor: [24, 48],
                popupAnchor: [0, -48]
            });
            red_stop_icon = L.icon({
                iconUrl: 'static/icons/bus-stop-red.png',
                iconSize: [48, 48],
                iconAnchor: [24, 48],
                popupAnchor: [0, -48]
            });

            data.top_5_stops.forEach(element => {
                console.log(element)
                const stop_layer = new L.Marker(
                    [element.stop_lat, element.stop_lon], { icon: red_stop_icon }
                ).addTo(map).bindPopup(
                    `<b>${element.stop_name}</b><br>
                    Mean Delay: ${element.mean_delay.toFixed(2)} seconds`
                )
                mapLayers.push(stop_layer);
            });
            data.bottom_5_stops.forEach(element => {
                const stop_layer = new L.Marker(
                    [element.stop_lat, element.stop_lon], { icon: green_stop_icon }
                ).addTo(map).bindPopup(
                    `<b>${element.stop_name}</b><br>
                    Mean Delay: ${element.mean_delay.toFixed(2)} seconds`
                )
                mapLayers.push(stop_layer);
            });

            // Optionally update map info with top/bottom stops
            updateMapInfoStops(
                data.top_5_stops,
                data.bottom_5_stops
            );
        });
}

function updateMapInfoStops(top, bottom) {
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

        const dateInput = document.getElementById("performance-date-selector");
        const dateCaption = `Last 7 days from ${dateInput.value} after dropping outliers`;

        if (top && top.length) {
            panel.innerHTML += createTable(top, `Top 5 Stops (${dateCaption})`);
        }
        if (bottom && bottom.length) {
            panel.innerHTML += createTable(bottom, `Bottom 5 Stops (${dateCaption})`);
        }
    }
}