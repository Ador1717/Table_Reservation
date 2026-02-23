(function () {
  function ensureTarget(target) {
    if (!target) throw new Error('ReservationWidget: `target` is required.');
    if (typeof target === 'string') {
      var el = document.querySelector(target);
      if (!el) throw new Error('ReservationWidget: target selector not found: ' + target);
      return el;
    }
    return target;
  }

  function detectPluginOrigin() {
    if (document.currentScript && document.currentScript.src) {
      return new URL(document.currentScript.src, window.location.href).origin;
    }

    var scripts = document.getElementsByTagName('script');
    for (var i = scripts.length - 1; i >= 0; i--) {
      var src = scripts[i].src || '';
      if (src.indexOf('/web/plugin.js') !== -1) {
        return new URL(src, window.location.href).origin;
      }
    }

    return window.location.origin;
  }

  function resolveWidgetBase(opts) {
    if (opts.widgetUrl) {
      return opts.widgetUrl;
    }

    if (opts.apiBaseUrl) {
      return new URL('/web/', opts.apiBaseUrl).toString();
    }

    return detectPluginOrigin() + '/web/';
  }

  function buildIframeSrc(opts) {
    var base = resolveWidgetBase(opts);
    var url = new URL(base, window.location.href);

    if (opts.restaurantId) url.searchParams.set('restaurantId', opts.restaurantId);
    if (opts.partySize) url.searchParams.set('partySize', String(opts.partySize));
    if (opts.date) url.searchParams.set('date', opts.date);

    return url.toString();
  }

  function mount(options) {
    var opts = options || {};
    var target = ensureTarget(opts.target);

    var iframe = document.createElement('iframe');
    iframe.src = buildIframeSrc(opts);
    iframe.title = opts.title || 'Reservation Widget';
    iframe.width = opts.width || '100%';
    iframe.height = opts.height || '760';
    iframe.loading = 'lazy';
    iframe.style.border = opts.border || '0';
    iframe.style.borderRadius = opts.borderRadius || '12px';

    target.innerHTML = '';
    target.appendChild(iframe);

    return {
      iframe: iframe,
      destroy: function () {
        iframe.remove();
      },
      update: function (next) {
        iframe.src = buildIframeSrc(Object.assign({}, opts, next || {}));
      },
    };
  }

  window.ReservationWidget = {
    mount: mount,
  };
})();
