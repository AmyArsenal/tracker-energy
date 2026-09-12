# tracker.energy

Evidence-linked US large-load interconnection intelligence. GitHub Pages site: https://amyarsenal.github.io/tracker-energy/

## Repository layout
- `scripts/` - public-source adapters, ETL, normalization, indexes and validation.
- `canonical/` - generated canonical database during builds; only checksummed manifest is committed.
- `docs/` - static product and published compact data artifacts.
- `docs/data/queue-adapters.json` - canonical source/adapter registry and WECC/SERC roadmap.
- `docs/map-data/` - map-ready EIA, ISO/RTO, HIFLD and cached OpenStreetMap layers.
- `.github/workflows/nightly.yml` - nightly refresh, validation, artifact archive and commit.
- `notes/` - product, source and security decisions.

## Data discipline
Every published record retains its source. Joins remain pending unless proven. Pipeline failures fail closed, while GitHub history and workflow artifacts retain last-good data. Large filing PDFs and raw source snapshots are not stored in ordinary git; nightly compact artifacts are checksummed in `canonical/manifest.json`, while workflow artifacts and the independent mailbox archive carry recovery copies.

## Local validation
```bash
pip install pandas openpyxl requests beautifulsoup4 lxml
python scripts/build_canonical.py
python scripts/build_search.py
python scripts/validate_articles.py
python scripts/build_manifest.py
node --check docs/grid-map.js
python -m py_compile scripts/*.py
```

No credentials belong in this repository. Deployment tokens are repository-scoped GitHub Actions secrets.

## Feature Channel
After the initial push, feature delivery does not require a user PAT or external push access. The nightly workflow reads the repository variable `FEATURE_MANIFEST_URL`, fetches the latest control-plane manifest, downloads its time-limited `bundle_url`, verifies the declared SHA-256, rejects unsafe archive entries, applies the repository-relative overlay, validates it, and commits it with the built-in `GITHUB_TOKEN`.

Manifest contract:
```json
{"version":"2026-09-12.1","bundle_url":"https://<controlled-origin>/feature-channel/bundles/<signed-token>","sha256":"<64 lowercase hex>"}
```

Channel URL shape: `https://<controlled-origin>/feature-channel/stable/manifest.json`. If the endpoint requires authentication, add the repository secret `FEATURE_BUNDLE_TOKEN`; it is not a user credential. Until `FEATURE_MANIFEST_URL` is set, the feature pull is skipped. Publishing uses GitHub Pages through `.github/workflows/pages.yml` and the built-in `GITHUB_TOKEN`; no third-party deployment secret is required.
