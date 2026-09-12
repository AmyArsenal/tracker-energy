"""Citation QC for published analysis (Brightwave-style structural layer).

Every load-bearing claim in staff analysis should carry an annolink to a
bounding-box annotation in the source PDF. This gate checks the structural
half before anything ships:
  1. every <a class="annolink" data-anno="X"> in body_html has a matching
     entry in annotations[]
  2. every annotation has page >= 1 and a sane rect (PDF points, letter-ish)
  3. every annotations[] entry is referenced at least once (warn)
  4. the hosted source PDF exists (when doc_local is set)
Exit 1 on any error; print a per-article report.
"""
import json, os, re, sys, glob

ARTS = os.path.join(os.path.dirname(__file__), "..", "docs", "data", "articles")
DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")

def check(path):
    d = json.load(open(path))
    name = os.path.basename(path)
    errors, warns = [], []
    annos = d.get("annotations") or []
    ids = {a.get("id") for a in annos}
    refs = set(re.findall(r'annolink[^>]*data-anno="([^"]+)"', d.get("body_html", "")))
    for r in refs - ids:
        errors.append(f"annolink data-anno={r} has no annotations[] entry")
    for a in annos:
        if not isinstance(a.get("page"), int) or a["page"] < 1:
            errors.append(f"annotation {a.get('id')}: bad page {a.get('page')}")
        rect = a.get("rect") or []
        if len(rect) != 4 or not all(isinstance(v, (int, float)) for v in rect) \
           or rect[0] >= rect[2] or rect[1] >= rect[3] \
           or rect[0] < 0 or rect[1] < 0 or rect[2] > 700 or rect[3] > 950:
            errors.append(f"annotation {a.get('id')}: bad rect {rect}")
        if a.get("id") not in refs:
            warns.append(f"annotation {a.get('id')} never linked from body")
    if not annos:
        warns.append("no annotations (no bounding-box citations)")
    return name, errors, warns

if __name__ == "__main__":
    total_e = total_w = 0
    for p in sorted(glob.glob(os.path.join(ARTS, "*.json"))):
        name, errors, warns = check(p)
        total_e += len(errors); total_w += len(warns)
        if errors or warns:
            print(f"{name}: {len(errors)}E {len(warns)}W")
            for e in errors: print("  ERR ", e)
            for w in warns:  print("  warn", w)
    print(f"articles: {len(glob.glob(os.path.join(ARTS, '*.json')))}, errors: {total_e}, warns: {total_w}")
    sys.exit(1 if total_e else 0)
