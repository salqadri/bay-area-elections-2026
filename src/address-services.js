/* Public Census JSONP client. No key, browser storage, or address persistence. */
(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ElectionAddressService = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';

  const ENDPOINT = 'https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress';
  const BENCHMARK = 'Public_AR_Current';
  const VINTAGE = 'Current_Current';
  const LAYERS = Object.freeze([14, 16, 18, 28, 30, 54, 56, 58, 80, 82]);
  let clientSequence = 0;

  function failure(code, message) {
    const error = new Error(message);
    error.name = code === 'ABORTED' ? 'AbortError' : 'AddressLookupError';
    error.code = code;
    return error;
  }

  function record(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function normalizeResponse(payload, now) {
    if (record(payload) && (payload.errors || payload.error ||
        (record(payload.result) && (payload.result.errors || payload.result.error)))) {
      throw failure('SERVICE_ERROR', 'The Census address service could not process this address. Check the street address, city, and ZIP code, then try again.');
    }
    const matches = payload && payload.result && payload.result.addressMatches;
    if (!Array.isArray(matches)) {
      throw failure('INVALID_RESPONSE', 'The Census address service returned an incomplete response. Please try again.');
    }
    const normalized = matches.map(function (match) {
      const coordinates = match && match.coordinates;
      if (!record(match) || typeof match.matchedAddress !== 'string' || !match.matchedAddress.trim() ||
          !record(coordinates) || !Number.isFinite(coordinates.x) || !Number.isFinite(coordinates.y) ||
          coordinates.x < -180 || coordinates.x > 180 || coordinates.y < -90 || coordinates.y > 90 ||
          !record(match.addressComponents) || !record(match.geographies) ||
          Object.values(match.geographies).some(function (items) {
            return !Array.isArray(items) || items.some(function (item) { return !record(item); });
          })) {
        throw failure('INVALID_RESPONSE', 'The Census address service returned an incomplete address match. Please try again.');
      }
      return {
        matchedAddress: match.matchedAddress,
        coordinates: {x: coordinates.x, y: coordinates.y},
        addressComponents: match.addressComponents,
        geographies: match.geographies
      };
    });
    return {
      matches: normalized,
      provider: 'U.S. Census Bureau',
      benchmark: BENCHMARK,
      vintage: VINTAGE,
      layers: LAYERS.slice(),
      queriedAt: now().toISOString()
    };
  }

  // Environment injection keeps the real browser transport covered by isolated tests.
  // Each client has its own callback namespace; each lookup owns all its resources.
  function createClient(environment) {
    environment = environment || {};
    const host = environment.globalObject || root;
    const doc = environment.document || host.document;
    const schedule = environment.setTimeout || host.setTimeout.bind(host);
    const cancel = environment.clearTimeout || host.clearTimeout.bind(host);
    const now = environment.now || function () { return new Date(); };
    const namespace = '__electionCensus_' + Date.now().toString(36) + '_' + (++clientSequence) + '_';
    let requestSequence = 0;

    function lookup(address, options) {
      options = options || {};
      const signal = options.signal;
      const timeoutMs = options.timeoutMs === undefined ? 20000 : options.timeoutMs;
      return new Promise(function (resolve, reject) {
        if (typeof address !== 'string' || !address.trim()) {
          reject(failure('INVALID_ADDRESS', 'Enter a street address, city, and state or ZIP code.'));
          return;
        }
        if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
          reject(failure('INVALID_OPTIONS', 'The address lookup timeout must be a positive number.'));
          return;
        }
        if (signal && signal.aborted) {
          reject(failure('ABORTED', 'Address lookup canceled.'));
          return;
        }
        if (!doc || typeof doc.createElement !== 'function' || !(doc.head || doc.body || doc.documentElement)) {
          reject(failure('UNSUPPORTED_ENVIRONMENT', 'Address lookup is available in a web browser.'));
          return;
        }
        let callbackName;
        do { callbackName = namespace + (++requestSequence); }
        while (Object.prototype.hasOwnProperty.call(host, callbackName));
        let script;
        let timer;
        let settled = false;
        let listeningForAbort = false;

        function cleanup() {
          if (timer !== undefined) cancel(timer);
          if (listeningForAbort) signal.removeEventListener('abort', onAbort);
          delete host[callbackName];
          if (script) {
            script.onerror = null;
            if (script.parentNode) script.parentNode.removeChild(script);
          }
        }

        function finish(error, result) {
          // A queued response may arrive after an abort, timeout, or another callback.
          if (settled) return;
          settled = true;
          cleanup();
          if (error) reject(error);
          else resolve(result);
        }

        function onAbort() {
          finish(failure('ABORTED', 'Address lookup canceled.'));
        }

        host[callbackName] = function (payload) {
          if (settled) return;
          try { finish(null, normalizeResponse(payload, now)); }
          catch (error) { finish(error); }
        };

        try {
          const url = new URL(ENDPOINT);
          url.search = new URLSearchParams({
            address: address.trim(),
            benchmark: BENCHMARK,
            vintage: VINTAGE,
            layers: LAYERS.join(','),
            format: 'jsonp',
            callback: callbackName
          }).toString();
          script = doc.createElement('script');
          script.async = true;
          script.referrerPolicy = 'no-referrer';
          script.src = url.toString();
          script.onerror = function () {
            finish(failure('NETWORK', 'Could not reach the Census address service. Check your connection and try again.'));
          };
          if (signal) {
            signal.addEventListener('abort', onAbort, {once: true});
            listeningForAbort = true;
          }
          // Recheck after registering the listener for custom or already-changing signals.
          if (signal && signal.aborted) { onAbort(); return; }
          timer = schedule(function () {
            finish(failure('TIMEOUT', 'The Census address service took too long to respond. Please try again.'));
          }, timeoutMs);
          (doc.head || doc.body || doc.documentElement).appendChild(script);
        } catch (_) {
          finish(failure('NETWORK', 'Could not start the Census address lookup. Please try again.'));
        }
      });
    }

    return {lookup: lookup};
  }

  const defaultClient = createClient();
  return {
    lookup: defaultClient.lookup,
    createClient: createClient,
    ENDPOINT: ENDPOINT,
    BENCHMARK: BENCHMARK,
    VINTAGE: VINTAGE,
    LAYERS: LAYERS
  };
});
