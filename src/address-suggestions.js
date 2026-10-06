'use strict';
// Photon only helps fill the address. Census remains the ballot geography source.
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ElectionAddressSuggestions = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const endpoint = 'https://photon.komoot.io/api/';
  function clean(value) { return typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : ''; }
  function abortError() { const error = new Error('Address suggestions canceled.'); error.name = 'AbortError'; return error; }
  function suggestionsFromResponse(response) {
    if (!response || !Array.isArray(response.features)) throw new Error('Invalid address suggestions response.');
    const seen = new Set();
    const suggestions = [];
    for (const feature of response.features) {
      const p = feature?.properties || {};
      if (clean(p.countrycode).toUpperCase() !== 'US' && !['United States', 'United States of America'].includes(clean(p.country))) continue;
      const number = clean(p.housenumber), street = clean(p.street);
      const city = clean(p.city || p.town || p.village || p.locality);
      const region = clean(p.state) === 'California' ? 'CA' : clean(p.state);
      // A road or place name alone is not an address suggestion. Never invent a number.
      if (!number || !street || !city || !region) continue;
      const label = number + ' ' + street;
      const detail = city + ', ' + region + (clean(p.postcode) ? ' ' + clean(p.postcode) : '');
      const value = label + ', ' + detail;
      const key = value.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      suggestions.push({ label, detail, value });
      if (suggestions.length === 6) break;
    }
    return suggestions;
  }
  function createClient(environment = {}) {
    const fetcher = environment.fetch || ((...args) => globalThis.fetch(...args));
    const schedule = environment.setTimeout || setTimeout;
    const cancel = environment.clearTimeout || clearTimeout;
    const clock = environment.now || Date.now;
    let retryAt = 0;
    async function lookup(input, options = {}) {
      const query = clean(input);
      if (query.length < 4 || query.length > 200) return [];
      if (options.signal?.aborted) throw abortError();
      if (clock() < retryAt) throw new Error('Address suggestions are temporarily unavailable. Enter your address manually.');
      const url = new URL(endpoint);
      url.searchParams.set('q', query);
      url.searchParams.set('limit', '8');
      url.searchParams.set('lang', 'en');
      url.searchParams.set('countrycode', 'US');
      url.searchParams.set('layer', 'house');
      // Prefer the Bay Area, but let a full US address override the location bias.
      url.searchParams.set('lat', '37.7');
      url.searchParams.set('lon', '-122.15');
      url.searchParams.set('zoom', '7');
      const controller = new AbortController();
      const abort = () => controller.abort();
      options.signal?.addEventListener('abort', abort, { once: true });
      let timedOut = false;
      const timer = schedule(() => { timedOut = true; controller.abort(); }, 6000);
      try {
        const response = await fetcher(url.toString(), { signal: controller.signal, credentials: 'omit', referrerPolicy: 'no-referrer' });
        if (response.status === 429) {
          retryAt = clock() + 60000;
          throw new Error('Address suggestions are busy. Enter your address manually.');
        }
        if (!response.ok) throw new Error('Address suggestions are temporarily unavailable.');
        const data = await response.json();
        if (options.signal?.aborted) throw abortError();
        if (timedOut) throw new Error('Address suggestions timed out.');
        return suggestionsFromResponse(data);
      } catch (error) {
        if (options.signal?.aborted) throw abortError();
        if (timedOut) throw new Error('Address suggestions timed out. Enter your address manually.');
        throw error;
      } finally {
        cancel(timer);
        options.signal?.removeEventListener('abort', abort);
      }
    }
    return { lookup };
  }
  return { endpoint, createClient, suggestionsFromResponse, lookup: createClient().lookup };
});
