/**
 * FinanzasApp — Modo oscuro/claro con persistencia en localStorage.
 */
(function () {
    const STORAGE_KEY = 'theme';

    function prefersDark() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    function isDark() {
        return document.documentElement.classList.contains('dark');
    }

    function applyTheme(theme) {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }
        localStorage.setItem(STORAGE_KEY, theme);
        updateToggleIcons();
        updateThemeColorMeta(theme);
    }

    function updateThemeColorMeta(theme) {
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute('content', theme === 'dark' ? '#0f172a' : '#4f46e5');
        }
    }

    function updateToggleIcons() {
        document.querySelectorAll('[data-theme-icon="sun"]').forEach((el) => {
            el.classList.toggle('hidden', !isDark());
        });
        document.querySelectorAll('[data-theme-icon="moon"]').forEach((el) => {
            el.classList.toggle('hidden', isDark());
        });
    }

    function initTheme() {
        const saved = localStorage.getItem(STORAGE_KEY);
        const theme = saved || (prefersDark() ? 'dark' : 'light');
        applyTheme(theme);
    }

    function toggleTheme() {
        applyTheme(isDark() ? 'light' : 'dark');
    }

    window.toggleTheme = toggleTheme;
    window.initThemeControls = function () {
        updateToggleIcons();
        document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
            btn.addEventListener('click', toggleTheme);
        });
    };

    initTheme();
})();
