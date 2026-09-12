#!/usr/bin/env python3
"""Find page + bounding box (points, top-left origin) of a phrase in a PDF."""
import subprocess, sys, re, html

def find(pdf, phrase, max_span=40):
    out = subprocess.run(['pdftotext','-bbox-layout',pdf,'-'], capture_output=True, text=True).stdout
    pages = re.split(r'<page ', out)[1:]
    words_norm = phrase.lower().split()
    for pi, p in enumerate(pages, 1):
        ws = re.findall(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)</word>', p)
        toks = [re.sub(r'[^a-z0-9]', '', html.unescape(w[4]).lower()) for w in ws]
        for i in range(len(toks)):
            # sliding window match allowing skips
            j, k = i, 0
            while k < len(toks) and j < len(words_norm) and k - i < max_span:
                if toks[k] == words_norm[j]: j += 1
                k += 1
            if j == len(words_norm) and k > i:
                box = ws[i:k]
                x0 = min(float(b[0]) for b in box); y0 = min(float(b[1]) for b in box)
                x1 = max(float(b[2]) for b in box); y1 = max(float(b[3]) for b in box)
                return {"page": pi, "rect": [round(x0-4,1), round(y0-3,1), round(x1+4,1), round(y1+3,1)]}
    return None

if __name__ == '__main__':
    import json
    pdf, phrase = sys.argv[1], sys.argv[2]
    print(json.dumps(find(pdf, phrase)))
