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
