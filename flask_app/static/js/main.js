let map = L.map("map");
let heatmap;
let mapLayers = [];
let markers = {};
let heatmapLayer;
let routeLayer;
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

function addBaseMapTile(targetMap) {
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png", {
        attribution: "©OpenStreetMap, ©CartoDB"
    }).addTo(targetMap);
}