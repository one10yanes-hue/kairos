(function() {
    var sidebar = document.getElementById('sidebar');
    var main = document.getElementById('mainContent');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');
    if (!sidebar) return;

    function isMob() { return window.innerWidth <= 768; }

    if (toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            if (isMob()) {
                sidebar.classList.toggle('open');
                overlay.classList.toggle('visible');
            } else {
                sidebar.classList.toggle('collapsed');
                if (main) main.classList.toggle('shifted');
            }
        });
    }

    if (overlay) overlay.addEventListener('click', function() {
        if (isMob()) { sidebar.classList.remove('open'); overlay.classList.remove('visible'); }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isMob() && sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            overlay.classList.remove('visible');
        }
    });

    var wasMob = isMob();
    window.addEventListener('resize', function() {
        var nowMob = isMob();
        if (nowMob !== wasMob) {
            sidebar.classList.remove('collapsed', 'open');
            if (main) main.classList.remove('shifted');
            overlay.classList.remove('visible');
            wasMob = nowMob;
        }
    });

    // Collapsible nav sections
    var STORAGE_KEY = 'kairos_sidebar_sections';
    function getState() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch(e) { return {}; }
    }
    function setState(state) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch(e) {}
    }

    function initSections() {
        var sections = document.querySelectorAll('.nav-section');
        if (!sections.length) return;
        var state = getState();
        sections.forEach(function(sec, i) {
            var key = sec.dataset.section || 'sec-' + i;
            sec.dataset.section = key;

            // Por defecto colapsado, expandir solo si tiene link activo
            var hasActive = sec.querySelector('.nav-item.active, .nav-item-sublink.active');
            var savedState = state[key];

            if (hasActive) {
                sec.classList.remove('collapsed');
                state[key] = 'open';
            } else if (savedState === 'open') {
                sec.classList.remove('collapsed');
            } else {
                sec.classList.add('collapsed');
            }

            var title = sec.querySelector('.nav-section-title');
            if (title && !title.dataset.bound) {
                title.dataset.bound = '1';
                title.addEventListener('click', function() {
                    sec.classList.toggle('collapsed');
                    var st = getState();
                    st[key] = sec.classList.contains('collapsed') ? 'closed' : 'open';
                    setState(st);
                });
            }
        });
        setState(state);
    }

    document.addEventListener('DOMContentLoaded', initSections);
    document.addEventListener('turbo:load', initSections);
})();
