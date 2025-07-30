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