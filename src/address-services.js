/* Public Census JSONP client. No key, browser storage, or address persistence. */
(function (root, factory) {
  'use strict';
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ElectionAddressService = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';

  const ENDPOINT = 'https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress';
  const LOCATIONS_ENDPOINT = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress';
  const TIGER_ENDPOINT = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/identify';
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

  // Census's combined geography endpoint can fail while its address geocoder
  // and direct TIGERweb service remain available. Both paths use Census matches.
  function geographyResponse(payload) {
    if (record(payload) && payload.error) throw failure('SERVICE_ERROR', 'The Census geography service could not process this lookup.');
    if (!record(payload) || !Array.isArray(payload.results)) throw failure('INVALID_RESPONSE', 'The Census geography service returned an incomplete response.');
    const geographies = {};
    const names = /^(States|Counties|Incorporated Places|Census Designated Places|Unified School Districts|Secondary School Districts|Elementary School Districts|\d+(?:st|nd|rd|th) Congressional Districts|\d{4} State Legislative Districts\s*-\s*(?:Upper|Lower))$/i;
    for (const item of payload.results) {
      if (!record(item) || !LAYERS.includes(item.layerId) || typeof item.layerName !== 'string' || !names.test(item.layerName)) continue;
      if (!record(item.attributes)) throw failure('INVALID_RESPONSE', 'The Census geography service returned an incomplete response.');
      (geographies[item.layerName] ||= []).push(item.attributes);
    }
    // No mailing-city or coordinate guess substitutes for an actual county polygon.
    if (!(geographies.Counties || []).some(row => /^\d{2}$/.test(row.STATE) && /^\d{3}$/.test(row.COUNTY))) {
      throw failure('INVALID_RESPONSE', 'The Census geography service did not identify a county. Please try again or browse counties.');
    }
    return geographies;
  }

  function createClient(environment) {
    environment = environment || {};
    const host = environment.globalObject || root;
    const doc = environment.document || host.document;
    const schedule = environment.setTimeout || host.setTimeout.bind(host);
    const cancel = environment.clearTimeout || host.clearTimeout.bind(host);
    const now = environment.now || function () { return new Date(); };
    const clock = environment.clock || Date.now;
    const fallbackEnabled = environment.fallbackEnabled !== false;
    const namespace = '__electionCensus_' + Date.now().toString(36) + '_' + (++clientSequence) + '_';
    let requestSequence = 0;

    function jsonp(endpoint, parameters, timeoutMs, signal) {
      return new Promise(function (resolve, reject) {
        if (signal && signal.aborted) { reject(failure('ABORTED', 'Address lookup canceled.')); return; }
        if (!doc || typeof doc.createElement !== 'function' || !(doc.head || doc.body || doc.documentElement)) {
          reject(failure('UNSUPPORTED_ENVIRONMENT', 'Address lookup is available in a web browser.')); return;
        }
        let callbackName;
        do { callbackName = namespace + (++requestSequence); }
        while (Object.prototype.hasOwnProperty.call(host, callbackName));
        let script, timer, settled = false, listeningForAbort = false;
        function cleanup() {
          if (timer !== undefined) cancel(timer);
          if (listeningForAbort) signal.removeEventListener('abort', onAbort);
          delete host[callbackName];
          if (script) { script.onerror = null; if (script.parentNode) script.parentNode.removeChild(script); }
        }
        function finish(error, result) {
          if (settled) return;
          settled = true; cleanup();
          if (error) reject(error); else resolve(result);
        }
        function onAbort() { finish(failure('ABORTED', 'Address lookup canceled.')); }
        host[callbackName] = function (payload) { finish(null, payload); };
        try {
          const url = new URL(endpoint);
          url.search = new URLSearchParams({...parameters, callback: callbackName}).toString();
          script = doc.createElement('script'); script.async = true; script.referrerPolicy = 'no-referrer'; script.src = url.toString();
          script.onerror = function () { finish(failure('NETWORK', 'Could not reach the Census address service. Check your connection and try again.')); };
          if (signal) { signal.addEventListener('abort', onAbort, {once: true}); listeningForAbort = true; }
          if (signal && signal.aborted) { onAbort(); return; }
          timer = schedule(function () { finish(failure('TIMEOUT', 'The Census address lookup took too long to respond. Please try again.')); }, timeoutMs);
          (doc.head || doc.body || doc.documentElement).appendChild(script);
        } catch (_) { finish(failure('NETWORK', 'Could not start the Census address lookup. Please try again.')); }
      });
    }

    async function lookup(address, options) {
      options = options || {};
      const signal = options.signal, timeoutMs = options.timeoutMs === undefined ? 20000 : options.timeoutMs;
      if (typeof address !== 'string' || !address.trim()) throw failure('INVALID_ADDRESS', 'Enter a street address, city, and state or ZIP code.');
      if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) throw failure('INVALID_OPTIONS', 'The address lookup timeout must be a positive number.');
      if (signal && signal.aborted) throw failure('ABORTED', 'Address lookup canceled.');
      const deadline = clock() + timeoutMs;
      function remaining() {
        if (signal && signal.aborted) throw failure('ABORTED', 'Address lookup canceled.');
        const value = deadline - clock();
        if (value <= 0) throw failure('TIMEOUT', 'The Census address lookup took too long to respond. Please try again.');
        return value;
      }
      try {
        const payload = await jsonp(ENDPOINT, {address: address.trim(), benchmark: BENCHMARK, vintage: VINTAGE,
          layers: LAYERS.join(','), format: 'jsonp'}, fallbackEnabled ? Math.min(8000, timeoutMs * .4) : timeoutMs, signal);
        return normalizeResponse(payload, now);
      } catch (error) {
        if (!fallbackEnabled || !['NETWORK','TIMEOUT'].includes(error.code)) throw error;
      }
      const located = await jsonp(LOCATIONS_ENDPOINT, {address: address.trim(), benchmark: BENCHMARK, format: 'jsonp'}, remaining(), signal);
      // Reuse strict address/coordinate validation before sending a point to TIGERweb.
      if (record(located) && (located.error || located.errors)) return normalizeResponse(located, now);
      const addressMatches = located && located.result && located.result.addressMatches;
      if (!Array.isArray(addressMatches)) throw failure('INVALID_RESPONSE', 'The Census address service returned an incomplete response.');
      const result = normalizeResponse({result: {addressMatches: addressMatches.map(match => ({...match, geographies: {}}))}}, now);
      for (const match of result.matches) {
        const x = match.coordinates.x, y = match.coordinates.y;
        const payload = await jsonp(TIGER_ENDPOINT, {geometry: x + ',' + y, geometryType: 'esriGeometryPoint', sr: '4326',
          layers: 'all:' + LAYERS.join(','), tolerance: '0', mapExtent: [x-.01,y-.01,x+.01,y+.01].join(','),
          imageDisplay: '100,100,96', returnGeometry: 'false', f: 'json'}, remaining(), signal);
        // Keep the returned layer's actual name/year. The matcher rejects old maps.
        match.geographies = geographyResponse(payload);
      }
      result.provider = 'U.S. Census Bureau · TIGERweb backup';
      result.vintage = 'TIGERweb_Current';
      result.queriedAt = now().toISOString();
      return result;
    }
    return {lookup: lookup};
  }

  const defaultClient = createClient();
  return {
    lookup: defaultClient.lookup,
    createClient: createClient,
    ENDPOINT: ENDPOINT,
    LOCATIONS_ENDPOINT: LOCATIONS_ENDPOINT,
    TIGER_ENDPOINT: TIGER_ENDPOINT,
    BENCHMARK: BENCHMARK,
    VINTAGE: VINTAGE,
    LAYERS: LAYERS
  };
});
