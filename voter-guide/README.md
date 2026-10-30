# The TALL Voter Guide

A separate, public, responsive voter guide at **https://tall-voter-guide.web.app**,
in Firebase project `tall-bay-area-voter-guide`. Its dedicated `voter-guide` target
does not deploy or overwrite the existing `research-tool` target.

The guide copies the published recommendations and candidate blurbs verbatim.
It makes no model calls, generates no political summaries and infers no new
recommendations. Names, official parties, verified incumbency and qualified
write-in status come from the canonical JSON. The public bundle excludes scores,
donations, raw evidence, endorsements, research archives and model prompts.

## Build and preview

From the repository root:

```sh
python3 voter-guide/build.py
python3 -m http.server 4173 --directory voter-guide/dist
```

Open http://localhost:4173. All Candidates has its own direct entry point at
`/candidates.html`. No Node dependencies or Firebase SDK are needed to run the site.
The build imports the existing canonical JSON and recommendation plan. After a
research update, refresh that project's published plan, then run the same command.
It refuses changed dataset hashes, mismatched score publications, stale rosters,
unbound candidate blurbs, missing picks and missing published rationale.

Alternative inputs are supported:

```sh
python3 voter-guide/build.py --dataset path/to/elections.json --recommendations path/to/recommendations.json
```

Both inputs must follow the current research-project format. This is an importer,
not a replacement for that project's research/recommendation pipeline.

## Google address autocomplete

In [Google Cloud Console](https://console.cloud.google.com/apis/credentials?project=tall-bay-area-voter-guide),
enable **Maps JavaScript API** and **Places API (New)**, then create a browser key.
Apply **Websites** restrictions for:

- `https://tall-voter-guide.web.app/*`
- `https://tall-voter-guide.firebaseapp.com/*`
- `http://localhost:4173/*` and `http://127.0.0.1:4173/*` for local tests, if desired.

Restrict the key to the two APIs above. A browser key is public by design; website
and API restrictions control its use. Do not reuse a server key or service-account
credential. Set it only in the build environment:

```sh
export TALL_GOOGLE_MAPS_API_KEY='your-website-restricted-key'
python3 voter-guide/build.py
```

The official accessible **PlaceAutocompleteElement** handles keyboard interaction,
Google attribution and autocomplete sessions. It uses current `gmp-select` and
`gmp-error` events, fetches only the selected formatted address, and biases toward
the Bay Area. Selection submits that address to the existing Census/TIGERweb
lookup. Google coordinates are not treated as certified election boundaries.
Manual entry remains available after widget/network failures.

Firebase Hosting supports static Spark-plan hosting. **Google Maps Platform has
separate billing and no-cost usage limits**; enabling Places requires its billing
setup. Enabling Google Maps billing in this same Firebase project upgrades its
plan to Blaze; Hosting still has no-cost usage quotas. Use a separate Google
Cloud project for the Maps key if the Hosting project must remain on Spark.
Configure API quotas and budget alerts in Cloud Console; alerts do not cap costs.
Hosting's free tier does not
guarantee that Google autocomplete traffic is free.

See [Google widget documentation](https://developers.google.com/maps/documentation/javascript/place-autocomplete-new),
[billing](https://developers.google.com/maps/documentation/places/web-service/usage-and-billing)
and [API security](https://developers.google.com/maps/api-security-best-practices).

## Publish from the Firebase-signed-in Mac

After checking out this branch/merging it into your local repository and setting
the restricted key above:

```sh
python3 voter-guide/deploy.py
```

The script builds, runs import tests, inspects Hosting sites in the exact project,
creates `tall-voter-guide` if absent, deploys only the guide target and verifies
the SHA-256 of every deployed file at both Firebase domains. It requires the key
for production publication so the requested Google autocomplete isn't silently
omitted. If necessary, first sign in on that computer:

```sh
npx --yes firebase-tools@15.34.2 login
```

The Hosting site ID must be globally available; no ownership/availability is
claimed until registration succeeds. There are no Functions, Firestore, accounts,
analytics or paid Firebase backend services. The current environment has not
registered the site or deployed it without authenticated Firebase access.

For a Firebase emulator preview (after building):

```sh
npx --yes firebase-tools@15.34.2 emulators:start --config firebase.voter-guide.json --only hosting:voter-guide --project tall-bay-area-voter-guide
```

## Matching and office order

Only **confirmed** contests in the covered counties are imported. Qualified
write-ins are labeled; provisional filers and confirmed cancellations are omitted.
The existing Census client and conservative matcher are reused unchanged.
Expected races appear first, in office order. Unresolved district alternatives
remain in a clearly labeled disclosure, with each original confidence explanation.
County browsing intentionally shows broad possibilities. Multiple address
matches can be narrowed or viewed as a union; outside-coverage and no-match
states never pretend to be an empty official ballot.

The guide follows [California Elections Code 13109](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=13109.&lawCode=ELEC):
statewide executives/BOE; U.S. Senate; U.S. House; state Senate; Assembly;
judicial; schools (including Superintendent of Public Instruction); county;
city; special districts. Local block ordering may vary by county under 13109(o).
Measures are not in the source inventory and are not displayed. The original
research explorer's different preferred display order remains unchanged.

## Privacy

Addresses and coordinates exist only in memory. No analytics, browser storage,
address URL parameters, server storage, login or user profiles are added.
Typing into Google sends requests to Google; submitted addresses go to Census;
both disclosures and provider privacy links are in the interface. Google-disabled
builds send only manually submitted addresses to Census. Printing includes no
entered address or coordinates. County/candidate filter state is not persisted.
The static host and third-party services maintain their own ordinary request logs.

## Checks

```sh
python3 -m unittest discover -s voter-guide/tests -p 'test_*.py'
node voter-guide/tests/core.cjs
node voter-guide/tests/browser.cjs
```

Browser checks require Playwright and Chromium. Use `PLAYWRIGHT_MODULE` for an
existing installation and `TALL_TEST_BASE_URL` to target a running static server.
They exercise address success, no match, ambiguous addresses, outside coverage,
cancellation, Google widget/failure behavior, county browsing, candidate filters,
disclosures, print privacy and multiple mobile/desktop widths. Provider calls are
intercepted using public civic-building fixtures; they do not certify live Google
credentials, Census availability or election boundary accuracy.

The guide workflow builds from the actual checked-out canonical dataset and
archives the deployable bundle, browser screenshots and check output. It does
not deploy or use Firebase credentials. Run a real Google autocomplete selection
and public-address lookup on the production domain after configuring the key.

### PR #21 deployment verification

The deployment verifier accepts Firebase's HTTP 404 response for the custom
`404.html` page only when its body matches the release hash. Unexpected HTTP
errors and changed response bodies still fail verification. The guide also imports
publication **2026-10-29.2** from the latest main branch without changing any
published recommendation or candidate blurb.
