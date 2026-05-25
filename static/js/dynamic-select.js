(function() {
    function initDynamicSelects() {
        document.querySelectorAll('.dynamic-select').forEach(function(el) {
            if (el.dataset.dsInitialized) return;
            el.dataset.dsInitialized = '1';

            var apiUrl = el.dataset.api || '/master/api/buscar/';
            var model = el.dataset.model;
            var placeholder = el.dataset.placeholder || 'Escriba para buscar...';
            var filters = el.dataset.filters || '';
            var parentId = el.id || 'ds-' + Math.random().toString(36).substr(2, 9);

            var wrapper = document.createElement('div');
            wrapper.className = 'dynamic-select-wrapper';
            wrapper.style.position = 'relative';

            var hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = el.name;
            hiddenInput.id = parentId;

            var textInput = document.createElement('input');
            textInput.type = 'text';
            textInput.className = 'form-control dynamic-select-input';
            textInput.placeholder = placeholder;
            textInput.autocomplete = 'off';

            var dropdown = document.createElement('div');
            dropdown.className = 'dynamic-select-dropdown';
            dropdown.style.cssText = 'position:absolute;top:100%;left:0;right:0;z-index:1050;max-height:260px;overflow-y:auto;background:#fff;border:1px solid #e2e8f0;border-radius:0.5rem;box-shadow:0 4px 16px rgba(0,0,0,0.06);display:none;';

            var clearBtn = document.createElement('button');
            clearBtn.type = 'button';
            clearBtn.className = 'dynamic-select-clear';
            clearBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
            clearBtn.title = 'Limpiar seleccion';
            clearBtn.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;color:#94a3b8;cursor:pointer;padding:4px;display:none;';
            clearBtn.addEventListener('click', function(e) {
                e.preventDefault();
                textInput.value = '';
                hiddenInput.value = '';
                clearBtn.style.display = 'none';
                dropdown.style.display = 'none';
            });

            textInput.addEventListener('input', function() {
                var val = this.value.trim();
                if (val.length < 1) {
                    hiddenInput.value = '';
                    dropdown.style.display = 'none';
                    clearBtn.style.display = 'none';
                    return;
                }
                var url = apiUrl + model + '/?q=' + encodeURIComponent(val);
                if (filters) url += '&' + filters;
                fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        dropdown.innerHTML = '';
                        if (data.length === 0) {
                            var emptyMsg = document.createElement('div');
                            emptyMsg.className = 'dynamic-select-empty';
                            emptyMsg.textContent = 'Sin resultados';
                            emptyMsg.style.cssText = 'padding:0.625rem 0.875rem;color:#94a3b8;font-size:0.85rem;text-align:center;';
                            dropdown.appendChild(emptyMsg);
                        } else {
                            data.forEach(function(item) {
                                var opt = document.createElement('div');
                                opt.className = 'dynamic-select-option';
                                opt.textContent = item.text;
                                opt.dataset.id = item.id;
                                opt.dataset.label = item.label || item.text;
                                opt.style.cssText = 'padding:0.5rem 0.75rem;cursor:pointer;font-size:0.85rem;color:#475569;border-bottom:1px solid #f1f5f9;transition:background 0.1s;';
                                opt.addEventListener('mouseenter', function() { this.style.background = '#f8fafc'; });
                                opt.addEventListener('mouseleave', function() { this.style.background = ''; });
                                opt.addEventListener('click', function() {
                                    hiddenInput.value = this.dataset.id;
                                    textInput.value = this.dataset.label;
                                    dropdown.style.display = 'none';
                                    clearBtn.style.display = 'block';
                                });
                                dropdown.appendChild(opt);
                            });
                        }
                        dropdown.style.display = 'block';
                    });
            });

            textInput.addEventListener('focus', function() {
                if (this.value.trim().length >= 1 && hiddenInput.value) {
                    dropdown.style.display = 'block';
                }
            });

            textInput.addEventListener('blur', function() {
                setTimeout(function() { dropdown.style.display = 'none'; }, 200);
            });

            if (el.tagName === 'SELECT') {
                var selectedOption = el.options[el.selectedIndex];
                if (selectedOption && selectedOption.value) {
                    var label = selectedOption.getAttribute('data-label') || selectedOption.textContent;
                    textInput.value = label;
                    hiddenInput.value = selectedOption.value;
                    clearBtn.style.display = 'block';
                }
                el.parentNode.replaceChild(wrapper, el);
            } else {
                el.parentNode.replaceChild(wrapper, el);
            }

            wrapper.appendChild(hiddenInput);
            wrapper.appendChild(textInput);
            wrapper.appendChild(dropdown);
            wrapper.appendChild(clearBtn);
        });
    }

    document.addEventListener('DOMContentLoaded', initDynamicSelects);
    document.addEventListener('turbo:load', initDynamicSelects);
})();
