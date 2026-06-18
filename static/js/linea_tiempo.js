/* global vis */
document.addEventListener('DOMContentLoaded', function () {
    // ---- Timeline diario (actividades) ----
    var container = document.getElementById('tlTimeline');
    if (container) initDailyTimeline();

    // ---- Gantt de proyectos ----
    var containerPrj = document.getElementById('tlProyectosGantt');
    if (containerPrj) initProjectGantt();

    function initDailyTimeline() {
        var groupsEl = document.getElementById('tl-groups');
        var itemsEl = document.getElementById('tl-items');
        var windowEl = document.getElementById('tl-window');
        if (!groupsEl || !itemsEl || !windowEl) return;

        var groups = JSON.parse(groupsEl.textContent);
        var items = JSON.parse(itemsEl.textContent);
        var win = JSON.parse(windowEl.textContent);

        var tips = {};
        var tipsEl = document.getElementById('tl-tips');
        if (tipsEl) { tips = JSON.parse(tipsEl.textContent); }

        items.forEach(function (item) {
            if (!item.content) {
                var tip = tips[item.id] || '';
                item.content = tip.split('|')[0];
            }
        });

        var options = {
            start: new Date(win.start),
            end: new Date(win.end),
            min: new Date(win.min),
            max: new Date(win.max),
            zoomMin: 60000,
            zoomMax: 86400000,
            stack: true,
            stackSubgroups: false,
            showCurrentTime: true,
            verticalScroll: true,
            zoomKey: 'ctrlKey',
            horizontalScroll: true,
            orientation: { axis: 'top', item: 'top' },
            margin: { item: { vertical: 2 } },
            tooltip: { followMouse: true, overflowMethod: 'cap' },
        };

        var timeline = new vis.Timeline(container, items, groups, options);
        timeline.setWindow(new Date(win.start), new Date(win.end), { animation: false });
        setTimeout(function () { timeline.fit({ animation: { duration: 300 } }); }, 100);

        addTooltip(timeline, tips);
    }

    function initProjectGantt() {
        var groupsEl = document.getElementById('prj-groups');
        var itemsEl = document.getElementById('prj-items');
        var windowEl = document.getElementById('prj-window');
        if (!groupsEl || !itemsEl || !windowEl) return;

        var groups = JSON.parse(groupsEl.textContent);
        var items = JSON.parse(itemsEl.textContent);
        var win = JSON.parse(windowEl.textContent);

        var tips = {};
        var tipsEl = document.getElementById('prj-tips');
        if (tipsEl) { tips = JSON.parse(tipsEl.textContent); }

        var options = {
            min: new Date(win.min),
            max: new Date(win.max),
            zoomMin: 86400000,
            zoomMax: 315360000000,
            stack: true,
            showCurrentTime: true,
            verticalScroll: true,
            zoomKey: 'ctrlKey',
            horizontalScroll: true,
            orientation: { axis: 'top', item: 'top' },
            margin: { item: { vertical: 4 } },
            tooltip: { followMouse: true, overflowMethod: 'cap' },
        };

        var timeline = new vis.Timeline(containerPrj, items, groups, options);
        setTimeout(function () { timeline.fit({ animation: { duration: 300 } }); }, 100);

        addTooltip(timeline, tips);
    }

    function addTooltip(timeline, tips) {
        var tip = document.createElement('div');
        tip.style.cssText = 'position:fixed;display:none;background:#1e293b;color:#fff;padding:6px 12px;border-radius:6px;font-size:0.78rem;z-index:9999;pointer-events:none;max-width:300px;line-height:1.3;box-shadow:0 4px 12px rgba(0,0,0,0.15);';
        document.body.appendChild(tip);

        timeline.on('itemover', function (props) {
            var tipData = tips[props.item];
            if (!tipData) return;
            var parts = tipData.split('|');
            tip.innerHTML = '<div style="font-weight:600;margin-bottom:2px;">' + parts[0] + '</div>' +
                parts.slice(1).map(function (p) { return '<div style="font-size:0.72rem;opacity:0.9;">' + p + '</div>'; }).join('');
            tip.style.display = 'block';
            tip.style.left = (props.event.clientX + 15) + 'px';
            tip.style.top = (props.event.clientY - 10) + 'px';
        });

        timeline.on('itemout', function () { tip.style.display = 'none'; });
        timeline.on('show', function () { tip.style.display = 'none'; });
    }
});
