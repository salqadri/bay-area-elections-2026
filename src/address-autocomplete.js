(function (root, factory) {
  'use strict';
  var api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ElectionAddressAutocomplete = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';

  // Suggestions only fill the input; the form remains responsible for submitting
  // the chosen or manually entered address to the ballot lookup service.
  function attach(options) {
    var input = options.input, listbox = options.listbox, status = options.status;
    var lookup = options.lookup, doc = input.ownerDocument || root.document;
    var timer = null, controller = null, sequence = 0, active = -1;
    var suggestions = [], composing = false, destroyed = false;
    var lastRequest = -Infinity, retryAfter = 0, listeners = [];

    function listen(target, name, handler) {
      if (!target) return;
      target.addEventListener(name, handler);
      listeners.push([target, name, handler]);
    }
    function announce(message) { status.textContent = message; }
    function clearList() {
      active = -1;
      suggestions = [];
      listbox.replaceChildren();
      listbox.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
    }
    function cancel() {
      sequence += 1;
      if (timer !== null) root.clearTimeout(timer);
      timer = null;
      if (controller) controller.abort();
      controller = null;
    }
    function close() {
      cancel();
      clearList();
      announce('');
    }
    function choose(index) {
      var choice = suggestions[index];
      if (!choice) return;
      input.value = choice.value;
      close();
      input.focus({ preventScroll: true });
      announce('Address selected. You can edit it or find your expected ballot.');
    }
    function highlight(index) {
      active = index;
      Array.from(listbox.children).forEach(function (option, i) {
        option.setAttribute('aria-selected', String(i === active));
      });
      var selected = listbox.children[active];
      if (selected) {
        input.setAttribute('aria-activedescendant', selected.id);
        if (selected.scrollIntoView) selected.scrollIntoView({ block: 'nearest' });
      } else input.removeAttribute('aria-activedescendant');
    }
    function render(results) {
      clearList();
      suggestions = (Array.isArray(results) ? results : []).filter(function (item) {
        return item && typeof item.label === 'string' && typeof item.value === 'string' && item.value.trim();
      }).slice(0, 6);
      suggestions.forEach(function (item, index) {
        var option = doc.createElement('li');
        option.id = listbox.id + '-option-' + index;
        option.setAttribute('role', 'option');
        option.setAttribute('aria-selected', 'false');
        option.dataset.suggestionIndex = String(index);
        var label = doc.createElement('span');
        label.className = 'address-suggestion-label';
        label.textContent = item.label;
        option.append(label);
        if (typeof item.detail === 'string' && item.detail) {
          var detail = doc.createElement('span');
          detail.className = 'address-suggestion-detail';
          detail.textContent = item.detail;
          option.append(detail);
        }
        listbox.append(option);
      });
      if (suggestions.length) {
        listbox.hidden = false;
        input.setAttribute('aria-expanded', 'true');
        announce(suggestions.length + ' address suggestions. Use the arrow keys to choose, then Enter. You can also enter your full address manually.');
      } else announce('No suggestions found. You can enter your full address manually.');
    }
    function schedule() {
      close();
      if (destroyed || composing) return;
      var query = input.value.trim();
      if (query.length < 4) return;
      if (Date.now() < retryAfter) {
        announce('Suggestions are temporarily unavailable. Enter your full address manually.');
        return;
      }
      var requestSequence = sequence;
      var wait = Math.max(750, 1000 - (Date.now() - lastRequest));
      timer = root.setTimeout(function () {
        timer = null;
        if (destroyed || composing || requestSequence !== sequence) return;
        controller = new root.AbortController();
        var requestController = controller;
        lastRequest = Date.now();
        announce('Finding address suggestions…');
        Promise.resolve().then(function () {
          if (requestController.signal.aborted) return [];
          return lookup(query, { signal: requestController.signal });
        }).then(function (results) {
          if (destroyed || requestSequence !== sequence || requestController.signal.aborted) return;
          controller = null;
          render(results);
        }).catch(function (error) {
          if (destroyed || requestSequence !== sequence || requestController.signal.aborted) return;
          controller = null;
          if (error && error.name === 'AbortError') return;
          retryAfter = Date.now() + 30000;
          clearList();
          announce('Suggestions are temporarily unavailable. Enter your full address manually.');
        });
      }, wait);
    }
    function keydown(event) {
      if (composing || event.isComposing || event.keyCode === 229) return;
      if (event.key === 'Escape') {
        if (!listbox.hidden) event.preventDefault();
        close();
      } else if (event.key === 'Tab') {
        close();
      } else if (!listbox.hidden && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
        event.preventDefault();
        var next = event.key === 'ArrowDown' ? (active + 1) % suggestions.length : (active < 0 ? suggestions.length - 1 : (active + suggestions.length - 1) % suggestions.length);
        highlight(next);
      } else if (event.key === 'Enter') {
        if (!listbox.hidden && active >= 0) {
          event.preventDefault();
          choose(active);
        } else close(); // An unselected Enter keeps the form's normal submit behavior.
      }
    }
    function optionAt(target) {
      var node = target;
      while (node && node !== listbox) {
        if (node.dataset && node.dataset.suggestionIndex !== undefined) return Number(node.dataset.suggestionIndex);
        node = node.parentNode;
      }
      return -1;
    }
    listen(input, 'input', schedule);
    listen(input, 'keydown', keydown);
    listen(input, 'blur', close);
    listen(input, 'compositionstart', function () { composing = true; close(); });
    listen(input, 'compositionend', function () { composing = false; schedule(); });
    listen(listbox, 'pointerdown', function (event) {
      // Keep DOM focus on the combobox so a pointer selection does not lose its
      // list to the blur handler before click is delivered.
      if (event.button === undefined || event.button === 0) event.preventDefault();
    });
    listen(listbox, 'mousedown', function (event) {
      if (event.button === undefined || event.button === 0) event.preventDefault();
    });
    listen(listbox, 'click', function (event) { choose(optionAt(event.target)); });
    listen(doc, 'pointerdown', function (event) {
      if (event.target !== input && !listbox.contains(event.target)) close();
    });
    listen(input.form, 'submit', close);
    clearList();
    return {
      close: close,
      destroy: function () {
        close();
        destroyed = true;
        listeners.forEach(function (entry) { entry[0].removeEventListener(entry[1], entry[2]); });
        listeners = [];
      }
    };
  }
  return { attach: attach };
}));
