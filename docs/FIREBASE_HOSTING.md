# Firebase Hosting

Current editorial publication: **2026-10-29.3**, with the [v4 source-selection policy](SUMMARY_SOURCE_POLICY.md). The initial registration and deployment history below is preserved.

Deployed on October 29, 2026 from main `8a8bd3c` (publication **2026-10-29.1**),
including the owner's full v7 Jev score run, fresh Qwen explanations and current
in-reader race recommendations. The requested Web App and dedicated Hosting site
are created, associated and published.

## Destination

- Project: `tall-bay-area-voter-guide`.
- Requested Firebase Web App display name: `tall-bay-area-research-tool`.
- Dedicated Hosting site ID: `tall-bay-area-research-tool`, associated with that
  Web App when the site is created.
- Hosting target: `research-tool` in `.firebaserc`.
- Live production URLs:
  `https://tall-bay-area-research-tool.web.app/` and
  `https://tall-bay-area-research-tool.firebaseapp.com/`.

The Web App display name and Hosting site are separate Firebase resources. Reuse
an existing matching app/site in this project if present. Check ownership and
existing releases before deployment. The named site was created and associated successfully.

## One-time sign-in and registration

An account able to manage this Firebase project must sign in on this Mac:

```sh
npx --yes firebase-tools@15.34.2 login
```

No credentials belong in this repository or chat. After sign-in, inspect this
project before creating resources:

```sh
npx --yes firebase-tools@15.34.2 apps:list WEB --project tall-bay-area-voter-guide
npx --yes firebase-tools@15.34.2 hosting:sites:list --project tall-bay-area-voter-guide
# Only when the matching Web App does not already exist:
npx --yes firebase-tools@15.34.2 apps:create WEB tall-bay-area-research-tool --project tall-bay-area-voter-guide
# Use the actual returned Web App ID; only when this Hosting site is absent:
npx --yes firebase-tools@15.34.2 hosting:sites:create tall-bay-area-research-tool --app ACTUAL_WEB_APP_ID --project tall-bay-area-voter-guide
```

Registration and deployment were authorized by the owner's October 29 request.
The owner completed CLI sign-in locally. Never commit Firebase CLI auth/debug logs.

## Build and deploy

```sh
python3 scripts/build_site.py
python3 scripts/build_firebase_hosting.py
python3 scripts/build_firebase_hosting.py --check
python3 scripts/check_release.py
npx --yes firebase-tools@15.34.2 deploy --only hosting:research-tool --project tall-bay-area-voter-guide
```

`firebase.json` runs the bundle builder again before deployment. Stale reader
HTML fails the build; it must match the templates, current canonical dataset
and recommendation plan exactly. Hosting publishes `.firebase-public/`, a
regenerated allowlist containing only:

- `index.html` and `ballot.html` (self-contained public readers).
- The canonical election JSON and its schema (public downloads).
- `404.html` and `hosting-release.json` (navigation and release hashes).

Research caches, local evaluation runs, source scripts and secrets are outside
this publication boundary. The output directory, Firebase cache and debug logs
are ignored by Git. HTML and JSON request revalidation so a new publication does
not retain stale scores in browser caches. Direct `.html` links remain valid;
unknown paths return a real 404 rather than an unrelated single-page-app screen.

The Jev playground remains a local service; Firebase Hosting serves static files
and cannot run its Python server or make authenticated provider calls.

## Analytics and verification

Production analytics now allow both named Firebase Hosting domains as well as the
existing GitHub Pages origin. The existing GA measurement ID **G-QKNPZZ1CDJ** and
analytics Firebase project remain the shared reporting destination; this hosting
move does not migrate or create an analytics property. Each origin uses the
correct cookie hostname/path and canonical page URL. Search queries, addresses
and candidate-selection fragments remain excluded. Local/preview domains do not
initialize analytics.

After deployment, verify both pages, direct download URLs, unknown-path 404,
and `hosting-release.json`; compare every listed SHA-256 with the local staged
file. Check the current grade badges and expanded recommendation rationale in a
browser. The successful release is recorded below.

References: [Firebase Hosting quickstart](https://firebase.google.com/docs/hosting/quickstart)
and [Firebase CLI](https://firebase.google.com/docs/cli).

## Verified deployment

- Firebase Web App ID: `1:783159241731:web:9935885236656e1c7e7236`.
- Hosting site: `tall-bay-area-research-tool` in `tall-bay-area-voter-guide`.
- Deployed Hosting version: `3a7fbd6a84e672bd`.
- All **50/50 release checks pass** for the exact canonical dataset.
- Firebase Hosting emulator and both production domains pass exact release-file
  SHA-256, cache/header and unknown/private-route 404 checks.
- Live Chrome verifies publication **2026-10-29.1**, Sam Liccardo
  **D (2.18 / 5)**, the fresh explanation, expanded pick rationale and both
  readers, with zero uncaught page errors.

No candidate evaluations were rerun or scores changed for this hosting move.

## Editorial follow-up: 2026-10-29.3

The Samir source-policy publication updates 19 blurbs and the future summary
prompts/guards. Saved evaluations and race choices are unchanged. The matching
plan, both readers and the Firebase bundle are rebuilt and checked by the
51-check release gate. See [the audit and Hermes policy](SUMMARY_SOURCE_POLICY.md).
