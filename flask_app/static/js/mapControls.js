// Map control and layer management functions

function clear_map() {
    if (mapLayers.length > 0) {
        mapLayers.forEach(layer => {
            if (map.hasLayer(layer)) {
                map.removeLayer(layer);
            }
        });
        mapLayers = [];
        markers = {};
    }
    // Remove live-status-map-div if present
    const statusDiv = document.getElementById("live-status-map-div");
    if (statusDiv && statusDiv.parentNode) {
        statusDiv.parentNode.removeChild(statusDiv);
    }

    // Remove heatmap-legend div if present
    const heatmapLegend = document.querySelector(".heatmap-legend");
    if (heatmapLegend && heatmapLegend.parentNode) {
        heatmapLegend.parentNode.removeChild(heatmapLegend);
    }

}

function setView(coords) {
    map.flyTo(coords, 12);
}

function addBaseMapTile(targetMap) {
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png", {
        attribution: "©OpenStreetMap, ©CartoDB"
    }).addTo(targetMap);
}

function addVehicleCountControl(map) {
    let statusDiv = document.getElementById("live-status-map-div");
    if (statusDiv) {
        statusDiv.innerHTML = "Connecting … 🔴";
        return;
    }

    const VehicleCount = L.Control.extend({
        options: { position: "bottomright" },
        onAdd: () => {
            const div = L.DomUtil.create("div", "live-status-control");
            div.id = "live-status-map-div";
            div.innerHTML = "Connecting … 🔴";
            return div;
        }
    });
    map.addControl(new VehicleCount());
}

function addHeatmapLegend(map) {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function () {
        const div = L.DomUtil.create('div', 'info legend heatmap-legend');
        const grades = [0.0, 0.25, 0.5, 0.75, 1.0];
        const labels = ['Very Early', 'Early', 'On Time', 'Late', 'Very Late'];
        const colors = ['#00ff00', '#aaff00', '#ffff00', '#ff7f00', '#ff0000'];

        div.innerHTML += '<strong>Delay Intensity</strong><br>';

        for (let i = 0; i < grades.length; i++) {
            div.innerHTML +=
                `<i style="background:${colors[i]}; width:18px; height:18px; display:inline-block; margin-right:8px;"></i> ${labels[i]}<br>`;
        }

        return div;
    };

    legend.addTo(map);
}