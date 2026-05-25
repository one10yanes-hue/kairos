document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el);
    });

    document.querySelectorAll('.toast').forEach(function(t) {
        new bootstrap.Toast(t).show();
    });

    document.querySelectorAll('a[onclick]').forEach(function(el) {
        var originalOnClick = el.getAttribute('onclick');
        if (originalOnClick && originalOnClick.includes('confirm(')) {
            el.addEventListener('click', function(e) {
                var msg = originalOnClick.match(/confirm\('([^']*)'\)/);
                if (msg && !confirm(msg[1])) {
                    e.preventDefault();
                }
            });
            el.removeAttribute('onclick');
        }
    });
});
