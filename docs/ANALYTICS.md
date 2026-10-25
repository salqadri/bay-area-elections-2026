# Public site analytics

Both public readers (`index.html` and `ballot.html`) use Firebase Analytics for project `bay-area-elections-research`, web app `1:693468629214:web:04e5a5f66ac3d549e39a4f`, measurement ID **G-QKNPZZ1CDJ**. Visits and the Google tag’s configured automatic interactions appear in the linked Google Analytics property. The pages disclose analytics cookies and link to Google’s privacy policy.

## Implementation and scope

Edit `src/analytics.js`, then run `python3 scripts/build_site.py`. The builder embeds the same module once in each page. It dynamically imports only Firebase App and Analytics, pinned to **13.1.0** on Google’s CDN using the [official CDN setup](https://firebase.google.com/docs/web/alt-setup). No npm install, server, new hosting service or deployment secret is required. Firebase’s supplied web configuration identifies the public app; it is not an administrative credential.

Initialization runs only on HTTPS at `salqadri.github.io`, for `/bay-area-elections-2026/`, `/bay-area-elections-2026/index.html` and `/bay-area-elections-2026/ballot.html`. Other paths, local servers, file previews and the local Jev playground do not even import the SDK. A support check precedes initialization, and loading/initialization failures are caught so blocked analytics cannot break research or address lookup.

## Data handling

The analytics configuration uses a fixed canonical page URL with no query string or fragment, and an empty referrer. `/index.html` and `/` share one reporting URL. The app does not send custom candidate, research, search, address or Jev events, and does not supply form input values or voter geography to Firebase. Existing address processing remains separate: suggestions go to Photon; submitted addresses go to Census. Google Analytics still receives ordinary visit/device information and uses cookies. Advertising personalization and Google signals are disabled in the client configuration. Analytics cookies use a project-specific prefix and the repository’s URL path so other GitHub Pages projects do not share these analytics cookies.

Automatic interaction collection is controlled by the linked GA4 web stream’s **Enhanced measurement** settings. Review those settings before adding new forms, URLs containing personal data, or any custom events; do not attach address values, search text or candidate research to analytics. This integration does not modify the property’s administrative settings.

## Verification and publication

`node scripts/check_analytics.cjs` is part of the **39-check** offline release gate. It covers the production allowlist, one-time initialization, canonical URLs, omitted referrers, unsupported browsers, loader failures and embedding in both generated pages. It does not contact Google or establish that the property received events.

For browser verification, load each page at its production URL (a browser route override can serve a pending build), intercept Google `/g/collect` requests without forwarding test traffic, and inspect the measurement ID and page location. Exercise the explorer search and address form with test values; verify none appear in captured analytics payloads. Also block the Firebase CDN and confirm both readers still function, and open a local preview to confirm it makes no Firebase/Analytics requests. The GitHub Pages deployment must match the committed HTML. Maintainers with property access can confirm incoming visits under Google Analytics **Realtime**; dashboard visibility is not verified by the offline gate.
