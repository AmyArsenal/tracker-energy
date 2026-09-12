# Phase 3: PUC tracker - source scouting (9 Sep 2026)
States from user: TX, VA, GA, OH (then more). Focus: large-load interconnection, data-center rates, Order 2023-related proceedings.

## Findings
- TX PUC Interchange (interchange.puc.texas.gov): real search UI exists (/search/filings?utilityType=Electric) but TIMES OUT from sandbox curl (000). Needs cloud browser or retry with different egress. Parse.bot claims an unofficial PUCT Interchange API exists - investigate.
- VA SCC docketsearch (scc.virginia.gov/docketsearch): 200, 8.8KB JS shell - data behind an API; inspect page JS next run for the endpoint.
- GA PSC (psc.ga.gov): 200 on facts-docket search; likely server-rendered, scrapeable.
- OH PUCO DIS (dis.puc.state.oh.us): 200; disclaimer interstitial then docket search; scrapeable with session cookie flow.

## Design direction
Same pattern as iso.html: nightly scrape -> docs/data/puc.json (state, docket no, title, utility, filed date, url, topic tags), page puc.html with state filter chips + topic tags. Green highlight for large-load/data-center and interconnection tags. "Coming" chips for states not yet wired.

## Status at end of run 9 Sep
- v1 battery tracker + v2 FERC newsroom + ISO meetings all live at tracker-energy.surge.sh.
- Nightly wake (05:30 UTC) covers EIA + FERC + ISO refresh, article writing, deploy, verify. Silent on success.
- Next: wire TX (cloud browser fallback), VA (find API endpoint), GA, OH scrapers into scripts/update_puc.py + puc.html page.

## Update 10 Sep (run 2)
- GA PSC: search UI calls `/search/facts-service/?q=...&type=Any&industry=Any&status=Any&date=Any&isPublic=true&pageIndex=1&pageSize=N` (Lucene-backed; found in /site/js/search.js). Returns {"resultsCount":null} for curl GET/POST even with cookies+Referer+XHR headers - needs exact param shape or session state. Document downloads are a clean public API: `https://services.psc.ga.gov/api/v1/External/Public/Get/Document/DownloadFile/<id>`. Next: drive the real search page in the cloud browser and capture the exact working XHR (params/headers), then replicate in curl for the nightly script.
- VA SCC: Durandal SPA at /DocketSearch/ (RequireJS, /DocketSearch/App/main.js). Search likely a server form POST returning HTML; viewmodels under /DocketSearch/App/viewmodels/. Not yet cracked.
- TX PUC Interchange: times out from sandbox egress entirely (000). Cloud browser likely required for scraping; nightly curl may not be viable - consider cloud-browser-based weekly scrape or Parse.bot-style unofficial API.
- OH PUCO DIS: WAF rejects plain requests ("Request Rejected" 244B page) even on the landing URL. Cloud browser required.
- Implication: 2 of 4 priority states (TX, OH) probably need browser-based scraping, which the nightly curl pipeline can't do. Options: (a) nightly cloud-browser scrape (heavier, lease per night), (b) weekly browser scrape + nightly curl for GA/VA, (c) ship PUC v1 with GA+VA only and mark TX/OH coming.
