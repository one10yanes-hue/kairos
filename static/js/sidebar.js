(function() {
    var sidebar = document.getElementById('sidebar');
    var main = document.getElementById('mainContent');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');
    if (!sidebar) return;

    function isMob() { return window.innerWidth <= 768; }

    var manualToggle = false;
    var hoverTimer = null;

    function expand() {
        sidebar.classList.remove('collapsed');
        if (main) main.classList.remove('shifted');
        scrollToActive();
    }
    function collapse(force) {
        if (manualToggle && !force) return;
        sidebar.classList.add('collapsed');
        if (main) main.classList.add('shifted');
        scrollToActive();
    }

    function scrollToActive() {
        var nav = sidebar.querySelector('.sidebar-nav');
        var active = sidebar.querySelector('.nav-item.active');
        if (nav && active) {
            var navRect = nav.getBoundingClientRect();
            var itemRect = active.getBoundingClientRect();
            var scrollTop = nav.scrollTop + (itemRect.top - navRect.top) - (navRect.height / 2) + (itemRect.height / 2);
            nav.scrollTo({ top: scrollTop, behavior: 'smooth' });
        }
    }

    function handleToggle() {
        if (isMob()) {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('visible');
        } else {
            sidebar.classList.toggle('collapsed');
            if (main) main.classList.toggle('shifted');
            manualToggle = !sidebar.classList.contains('collapsed');
        }
        try { localStorage.setItem('kairos_sidebar_collapsed', sidebar.classList.contains('collapsed') ? '1' : '0'); } catch(e) {}
    }

    // Hover auto-expand en desktop
    sidebar.addEventListener('mouseenter', function() {
        if (isMob()) return;
        clearTimeout(hoverTimer);
        expand();
    });
    sidebar.addEventListener('mouseleave', function() {
        if (isMob()) return;
        hoverTimer = setTimeout(function() { collapse(); }, 200);
    });

    if (toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            handleToggle();
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
        if (e.ctrlKey && e.key === 'b') {
            e.preventDefault();
            handleToggle();
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

            // Indicador de item activo en el titulo
            var title = sec.querySelector('.nav-section-title');
            if (title && hasActive) {
                title.style.color = 'var(--accent)';
                title.style.fontWeight = '700';
            }

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
        // Tooltips para modo colapsado
        document.querySelectorAll('.nav-item').forEach(function(item) {
            var span = item.querySelector('span');
            if (span && !item.hasAttribute('title')) {
                item.setAttribute('title', span.textContent.trim());
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        initSections();
        scrollToActive();
    });
    document.addEventListener('turbo:load', initSections);
})();
