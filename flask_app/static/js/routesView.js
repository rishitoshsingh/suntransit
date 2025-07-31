// Routes view functions

function initRoutesView(cities) {
    clear_map();
    console.log("Routes Delay view selected");
    console.log("Initializing Routes Delay Map for city:", currentCity);

    addBaseMapTile(map);
    updateRouteMap(currentCity);
}

function updateRoutesView() {
    updateRouteMap(currentCity);
}

function updateRouteMap(city) {
    const dateInput = document.getElementById("performance-date-selector");
    if (!dateInput.value) return;
    const selectedDate = dateInput.value;

    fetch(`/route_delays/${city}/${selectedDate}`)
        .then(res => res.json())
        .then(data => {
            // Remove existing heatmap layer if present
            if (routeLayer && map.hasLayer(routeLayer)) {
                map.removeLayer(routeLayer);
            }
            console.log("Route data:", data);
            data.top_5_routes.forEach(element => {
                const route_layer = new L.Polyline(
                    element.route_path, { color: element.route_color }
                ).addTo(map).bindPopup(
                    `${element.route_id}<br>${element.mean_delay.toFixed(2)} seconds`
                )
                mapLayers.push(route_layer);
            });
            data.bottom_5_routes.forEach(element => {
                const route_layer = new L.Polyline(
                    element.route_path, { color: element.route_color }
                ).addTo(map).bindPopup(
                    `${element.route_id}<br>${element.mean_delay.toFixed(2)} seconds`
                )
                mapLayers.push(route_layer);
            });

            // Optionally update map info with top/bottom routes
            updateMapInfoRoutes(
                data.top_5_routes,
                data.bottom_5_routes
            );
        });
}

function updateMapInfoRoutes(top, bottom) {
    const panel = document.querySelector('#map-info-panel .content');
    if (panel) {
        panel.innerHTML = '';

        function createTable(routes, caption) {
            let rows = routes.map((route, idx) => `
                <tr>
                    <th scope="row">${idx + 1}</th>
                    <td style="word-break:break-word;max-width:180px;">${route.route_id}</td>
                    <td>${route.total_trips}</td>
                    <td>${route.mean_delay.toFixed(2)}</td>
                </tr>
            `).join('');
            return `
                <table class="table table-striped table-hover table-borderless table-dark">
                    <thead>
                        <tr>
                            <th scope="col">#</th>
                            <th scope="col">Route ID</th>
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
            panel.innerHTML += createTable(top, `Top 5 Routes (${dateCaption})`);
        }
        if (bottom && bottom.length) {
            panel.innerHTML += createTable(bottom, `Bottom 5 Routes (${dateCaption})`);
        }
    }
}