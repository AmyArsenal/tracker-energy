
## Feed matrix verified 2026-09-10 (all return real RSS items)
- committees/mc (Members), mrc (Markets & Reliability), mic (Market Implementation - 489 items), pc (Planning), oc (Operating), lc (Liaison)
- subcommittees/raas (Resource Adequacy Analysis), dts (Dispatcher Training - low value)
- URL form: https://www.pjm.com/committees-and-groups/<category>/<abbr>.aspx?Committees=All&rss=1 (follow redirects; capital C works)
- NOT working: task-forces/epfstf, subcommittees/irs, site-wide meetings feed (empty)
- CIFP-RBP (large-load fast path): NO RSS. Landing page /committees-and-groups/cifp-rbp lists document PDF links directly (postings/...pdf) - weekly HTML link-parse, robots-allowed.
- Item structure: <title> = doc label (Agenda/Minutes PDF), <link> = direct PDF URL, <pubDate> = posting date, <description> = meeting note. Meeting date parseable from PDF path (yyyymmdd).
- NEXT: build update_pjm.py (weekly): committees mc/mrc/mic/pc/oc + raas + cifp-rbp page parse -> canonical store source 'pjm' -> build_search -> ISO page PJM section. Parent approved 16:45 2026-09-10.
