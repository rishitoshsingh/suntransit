// UI controls and initialization functions

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

function initDateSelector(agency) {
    console.log("Initializing date selector for agency:", agency);
    const dateInput = document.getElementById("performance-date-selector");

    function toLocalISOString(date) {
        const offsetMs = date.getTimezoneOffset() * 60000;
        const localISOTime = new Date(date.getTime() - offsetMs).toISOString().slice(0, -1);
        return localISOTime;
    }
    const now = new Date();
    let maxDate = new Date(now);
    maxDate.setDate(now.getDate() - (now.getHours() >= 3 ? 1 : 2));
    console.log("Max date set to:", maxDate);

    fetch(`/oldest_date/${agency}`)
        .then(res => res.json())
        .then(data => {
            console.log("Oldest date data:", data);
            const minDate = new Date(data.oldest_date);
            dateInput.min = toLocalISOString(minDate).split('T')[0];
            dateInput.max = toLocalISOString(maxDate).split('T')[0];
            dateInput.value = dateInput.max;
        });
}


const panel = document.getElementById("map-info-panel");

panel.addEventListener("click", () => {
    if (panel.classList.contains("collapsed")) {
        panel.classList.remove("collapsed");
        panel.classList.add("expanded");
    } else {
        panel.classList.remove("expanded");
        panel.classList.add("collapsed");
    }
});