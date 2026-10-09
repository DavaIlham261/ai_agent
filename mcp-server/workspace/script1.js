const themeToggle = document.querySelector("#theme-toggle");

if (!themeToggle) {
  throw new Error("Tombol toggle tema tidak ditemukan.");
}

const themeIcon = themeToggle.querySelector(".theme-icon");
const STORAGE_KEY = "portfolio-theme";
const validThemes = new Set(["light", "dark"]);

function getSavedTheme() {
  try {
    const savedTheme = localStorage.getItem(STORAGE_KEY);
    return validThemes.has(savedTheme) ? savedTheme : null;
  } catch {
    return null;
  }
}

function applyTheme(theme, persist = true) {
  const selectedTheme = validThemes.has(theme) ? theme : "light";

  document.documentElement.dataset.theme = selectedTheme;

  if (themeIcon) {
    themeIcon.textContent = selectedTheme === "dark" ? "☀️" : "🌙";
  }

  themeToggle.setAttribute(
    "aria-label",
    selectedTheme === "dark" ? "Aktifkan tema terang" : "Aktifkan tema gelap"
  );
  themeToggle.title = themeToggle.getAttribute("aria-label");

  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, selectedTheme);
    } catch {
      // Tema tetap dapat digunakan jika penyimpanan diblokir browser.
    }
  }
}

// Gunakan preferensi pengguna jika tersimpan; jika belum, ikuti preferensi sistem.
const savedTheme = getSavedTheme();
const systemPrefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
applyTheme(savedTheme || (systemPrefersDark ? "dark" : "light"), Boolean(savedTheme));

themeToggle.addEventListener("click", () => {
  const currentTheme = document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  applyTheme(currentTheme === "dark" ? "light" : "dark");
});

