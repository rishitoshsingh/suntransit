// API calls and data management

// function updateMapInfo(map_view, agency, city) {
//     const dateInput = document.getElementById("performance-date-selector");
//     const selectedDate = dateInput.value;

//     if (!selectedDate) {
//         console.warn("No date selected for performance data.");
//         setTimeout(() => {
//             updatePerformance(agency);
//         }, 2000);
//         return;
//     }

//     if (map_view === "viewLive") updatePerformance(agency, selectedDate);
//     else if (map_view === "viewHeatmap") getStopsDelayDetailed(city, selectedDate);
//     else if (map_view === "viewRoutes") getRoutesDelayDetailed(city, selectedDate);
// }


function updatePerformance(agency) {
    const dateInput = document.getElementById("performance-date-selector");
    const selectedDate = dateInput.value;

    if (!selectedDate) {
        console.warn("No date selected for performance data.");
        setTimeout(() => {
            updatePerformance(agency);
        }, 2000);
        return;
    }

    fetch(`/agency_delays/${agency}/${selectedDate}`)
        .then(res => res.json())
        .then(data => {
            console.log("Performance Data:", data);
            document.getElementById("meanDelay").textContent = data[0].mean_delay !== undefined
                ? (data[0].mean_delay / 60).toFixed(2)
                : "-";
            if (data[0].std_delay !== undefined) {
                document.getElementById("meanDelay").textContent += " ±" + (data[0].std_delay / 60).toFixed(2);
            }
            document.getElementById("totalTrips").textContent = data[0].total_trips || "-";
        });
}
