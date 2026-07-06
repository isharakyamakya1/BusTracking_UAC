const STORAGE_THEME_KEY = "uacTransportTheme";
const STORAGE_SIDEBAR_KEY = "uacSidebarCollapsed";

function toggleMenu() {
    const isDesktop = window.innerWidth >= 992;
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    if (!sidebar || !overlay) return;

    if (isDesktop) {
        const collapsed = document.body.classList.toggle("sidebar-collapsed");
        localStorage.setItem(STORAGE_SIDEBAR_KEY, collapsed ? "1" : "0");
        sidebar.classList.remove("active");
        overlay.classList.remove("active");
        return;
    }

    sidebar.classList.toggle("active");
    overlay.classList.toggle("active");
}

function closeMenu() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    if (!sidebar || !overlay) return;
    sidebar.classList.remove("active");
    overlay.classList.remove("active");
}

function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(STORAGE_THEME_KEY, theme);
}

function toggleTheme() {
    const current = document.documentElement.dataset.theme || "light";
    applyTheme(current === "dark" ? "light" : "dark");
    showToast(`Theme ${current === "dark" ? "clair" : "sombre"} active`, "info");
}

function showToast(message, type = "info", durationMs = 3000) {
    const toast = document.getElementById("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.className = `toast toast--${type}`;
    toast.setAttribute("role", "status");
    toast.style.opacity = "1";

    window.clearTimeout(toast._hideTimer);
    toast._hideTimer = window.setTimeout(() => {
        toast.style.opacity = "0";
    }, durationMs);
}

function setupPasswordToggles() {
    document.querySelectorAll(".password-field").forEach((container) => {
        const input = container.querySelector("input");
        const button = container.querySelector(".password-toggle");
        if (!input || !button) return;

        button.addEventListener("click", (event) => {
            event.preventDefault();
            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            button.textContent = isPassword ? "Masquer" : "Afficher";
        });
    });
}

function setupFormValidation() {
    document.querySelectorAll("form[data-validate]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            const required = Array.from(form.querySelectorAll("[required]"));
            const missing = required.filter((input) => !String(input.value || "").trim());
            if (missing.length) {
                event.preventDefault();
                showToast("Veuillez completer tous les champs obligatoires.", "warning");
                missing[0].focus();
            }
        });
    });
}

function setupBusMap() {
    const mapContainer = document.getElementById("bus-map");
    if (!mapContainer || typeof L === "undefined") return;

    const map = L.map(mapContainer, { zoomControl: false }).setView([0, 0], 2);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    // State for buses: { [busId]: { marker, polyline, positions: [[lat,lon], ...] } }
    const busesState = {};
    // whether the user has interacted with the map (stop auto-fitting)
    let userInteracted = false;

    map.on('dragstart zoomstart', () => { userInteracted = true; });

    function formatLabel(bus) {
        const plaque = bus.plaque || '—';
        const dest = bus.destination_name ? `\u00A0–\u00A0${bus.destination_name}` : '';
        const driver = bus.driver && bus.driver.nom ? `<br/><small>Chauffeur: ${bus.driver.nom}</small>` : '';
        return `<strong>${plaque}</strong>${dest}${driver}`;
    }

    const redBusIcon = L.divIcon({
        html: '<span style="display:block;width:14px;height:14px;border-radius:50%;background:#e74c3c;border:2px solid #ffffff;box-shadow:0 0 0 2px rgba(231, 76, 60, 0.2);"></span>',
        className: '',
        iconSize: [14, 14],
        iconAnchor: [7, 7]
    });

    async function refreshBusLocations() {
        try {
            const response = await fetch("/api/buses/locations");
            if (!response.ok) return;
            const locations = await response.json();
            if (!Array.isArray(locations)) return;

            const bounds = [];

            locations.forEach((bus) => {
                const id = bus.id;
                const lat = parseFloat(bus.current_lat);
                const lon = parseFloat(bus.current_lon);
                if (Number.isNaN(lat) || Number.isNaN(lon)) return;

                bounds.push([lat, lon]);

                if (!busesState[id]) {
                    // create marker and polyline
                    const marker = L.marker([lat, lon], { icon: redBusIcon }).addTo(map);
                    const polyline = L.polyline([[lat, lon]], { color: '#3388ff', weight: 4 }).addTo(map);
                    marker.bindPopup(formatLabel(bus));
                    busesState[id] = { marker, polyline, positions: [[lat, lon]] };
                } else {
                    const state = busesState[id];
                    // update marker position
                    state.marker.setLatLng([lat, lon]);
                    // update popup content
                    state.marker.getPopup().setContent(formatLabel(bus));
                    // append to positions and update polyline
                    const last = state.positions[state.positions.length - 1];
                    if (!last || last[0] !== lat || last[1] !== lon) {
                        state.positions.push([lat, lon]);
                        if (state.positions.length > 200) state.positions.shift();
                        state.polyline.setLatLngs(state.positions);
                    }
                }
            });

            // Optionally remove buses not returned anymore
            Object.keys(busesState).forEach((key) => {
                const found = locations.find(b => String(b.id) === String(key));
                if (!found) {
                    const s = busesState[key];
                    map.removeLayer(s.marker);
                    map.removeLayer(s.polyline);
                    delete busesState[key];
                }
            });

            // Auto-fit bounds on first load or if user hasn't interacted
            if (bounds.length && !userInteracted) {
                const leafletBounds = L.latLngBounds(bounds);
                map.fitBounds(leafletBounds.pad(0.2));
            }
        } catch (error) {
            console.warn("Impossible de charger les positions des bus", error);
        }
    }

    refreshBusLocations();
    window.setInterval(refreshBusLocations, 15000);
}

function setupDriverMap() {
    const mapEl = document.getElementById('driver-leaflet-map');
    if (!mapEl || typeof L === 'undefined') return;

    const lat = parseFloat(mapEl.dataset.lat);
    const lon = parseFloat(mapEl.dataset.lon);
    if (Number.isNaN(lat) || Number.isNaN(lon)) return;

    const plaque = mapEl.dataset.plaque || 'Bus';
    const stop = mapEl.dataset.stop || 'Dernier arrêt inconnu';

    const map = L.map(mapEl, { zoomControl: true }).setView([lat, lon], 15);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    const busIcon = L.divIcon({
        html: '<span style="display:flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:50%;background:#0d6efd;color:white;font-size:18px;box-shadow:0 0 0 12px rgba(13,110,253,0.16);border:2px solid white;"><i class="bi bi-bus-front-fill"></i></span>',
        className: '',
        iconSize: [34, 34],
        iconAnchor: [17, 17]
    });

    const marker = L.marker([lat, lon], { icon: busIcon }).addTo(map);
    marker.bindPopup(`<strong>${plaque}</strong><br>${stop}`);
    setTimeout(() => {
        if (map) {
            map.invalidateSize();
        }
    }, 200);
}

function updateSidebarActiveLink() {
    const currentPath = window.location.pathname.replace(/\/$/, "");
    const currentHash = window.location.hash || "";

    document.querySelectorAll(".sidebar-nav a").forEach((link) => {
        const rawHref = link.getAttribute("href") || "";
        const normalizedHref = rawHref.replace(/\/$/, "");
        const parts = normalizedHref.split("#");
        const linkPath = parts[0];
        const linkHash = parts[1] ? `#${parts[1]}` : "";

        const pathMatches = linkPath && (currentPath === linkPath || currentPath.startsWith(linkPath));
        const hashMatches = linkHash ? currentHash === linkHash : true;
        const isActive = normalizedHref && pathMatches && hashMatches;

        link.classList.toggle("active", Boolean(isActive));
    });
}

function setupSidebarLinks() {
    document.querySelectorAll(".sidebar-nav a").forEach((link) => {
        link.addEventListener("click", () => {
            if (window.innerWidth < 992) {
                closeMenu();
            }
        });
    });
}

function init() {
    const savedTheme = localStorage.getItem(STORAGE_THEME_KEY);
    const savedSidebarState = localStorage.getItem(STORAGE_SIDEBAR_KEY);
    if (savedTheme) {
        document.documentElement.dataset.theme = savedTheme;
    }
    if (window.innerWidth >= 992 && savedSidebarState === "1") {
        document.body.classList.add("sidebar-collapsed");
    }

    setupPasswordToggles();
    setupFormValidation();
    setupBusMap();
    setupDriverMap();
    updateSidebarActiveLink();
    setupSidebarLinks();

    window.addEventListener("hashchange", updateSidebarActiveLink);

    document.addEventListener("click", (event) => {
        const sidebar = document.getElementById("sidebar");
        if (!sidebar) return;

        if (sidebar.classList.contains("active") && !sidebar.contains(event.target) && !event.target.closest(".menu-btn")) {
            closeMenu();
        }
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth >= 992) {
            closeMenu();
            if (localStorage.getItem(STORAGE_SIDEBAR_KEY) === "1") {
                document.body.classList.add("sidebar-collapsed");
            }
        } else {
            document.body.classList.remove("sidebar-collapsed");
        }
    });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}
