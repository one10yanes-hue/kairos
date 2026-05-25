(function() {
    var sidebar = document.getElementById('sidebar');
    var main = document.getElementById('mainContent');
    var overlay = document.getElementById('sidebarOverlay');
    var toggle = document.getElementById('sidebarToggle');
    if (!sidebar || !toggle) return;

    function isMob() { return window.innerWidth <= 768; }

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
})();
