# Address lookup recovery — October 28, 2026

Publication **2026-10-28.3** fixes address estimates during an outage of Census's
combined address/geography service. No candidate research, grades, saved Jev
requests or recommendation summaries change.

## Diagnosis

The published page's generic error was reproduced in Chrome using a public city
hall address. Census's `geographies/onelineaddress` and `geographies/coordinates`
returned HTTP 502, including reduced-layer requests. The separate
`locations/onelineaddress` address geocoder and direct Census TIGERweb point query
remained available. This was not an address-entry requirement or a need to wait
for a site deployment to propagate.

## Recovery

`src/address-services.js` tries the existing combined Census endpoint, reserving
part of the lookup deadline for recovery. On a network failure or timeout it:

1. Gets every matching address and its coordinates from Census's location-only
   geocoder. Empty matches remain empty; no city centroid substitutes for a house.
2. Identifies those points against the current Census TIGERweb polygon service,
   requesting county, state, city/CDP, school and legislative layers.
3. Preserves the actual layer names and years. The existing matcher narrows
   legislative contests only for 120th-Congress / 2026-state layers; older or
   unresolved boundaries remain broader possibilities.

The query uses point intersection with zero screen-pixel tolerance. A fallback
response must identify a county polygon with valid state/county codes. Missing
geography, invalid coordinates and service errors fail without fabricating data.
Multiple address matches retain their own separate geography and the existing
match-selection UI.

The entire sequence shares one deadline: the primary attempt uses up to eight
seconds (or 40% of a shorter budget), leaving the remainder for recovery. Every
stage cleans its script, callback, timer and abort listener; cancellation and a
new lookup cannot leak a stale result into the current page.

Both paths use U.S. Census Bureau services. Photon continues to provide typing
suggestions only. No additional provider receives the submitted address, and no
address is added to site URLs, browser storage, analytics or estimate downloads.

`src/ballot-page.js` also distinguishes timeout, unprocessable address and
incomplete geography from a general service failure, using fixed local messages
rather than exposing raw provider responses or private input.

## Verification

- Live Chrome: San Jose City Hall resolved through the backup in about **9.3 s**,
  with Santa Clara County, San Jose, CD-18, AD-25, SD-15 and San Jose Unified.
- Live Chrome: San Francisco City Hall resolved through the backup in about
  **8.8 s**, with San Francisco County, CD-11, AD-17, SD-11 and its unified district.
- A public Oakland civic-address query returned no Census match and correctly
  displayed the existing no-match message, with no invented location.
- Twenty deterministic service tests cover both transports, ambiguous matches,
  historical labels, incomplete polygons, invalid points, no matches, one total
  deadline, cancellation and resource cleanup. Reader checks cover sanitized,
  cause-specific error messages.

These are live transport checks at known public addresses, not validation of
all electorate IDs or voter eligibility. `address_lookup.api_validated` remains
false for dataset-wide electorate/API validation. No simulated result is used
by the published application.

All **48 offline release checks pass**, including the 20 service tests and the
reader's cause-specific error/privacy checks. Candidate research, scores and
explanations are identical to the preceding publication.
