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

After this migration, feature delivery requires no user PAT, repository variable, or third-party deploy token. The nightly workflow reads owner-authored comments from the public [feature channel issue](https://github.com/AmyArsenal/tracker-energy/issues/1), ignores every other author, decodes the newest v1 manifest, verifies its declared SHA-256, rejects unsafe archive entries, applies the repository-relative overlay, validates it, and commits it with the built-in `GITHUB_TOKEN`.

A valid owner comment begins with `<!-- tracker-feature-channel:v1 -->` and contains a JSON object with `version`, `sha256`, and either `bundle_base64` or `bundle_url`. Inline bundles are capped at 40 MiB after decoding. Publishing uses GitHub Pages through `.github/workflows/pages.yml` and needs no third-party deployment secret.
