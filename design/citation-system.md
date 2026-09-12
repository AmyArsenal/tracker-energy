# Citation system architecture

## Product role
Citation quality is moat #2 after UX/workflow. The aim is not to show that an answer used a document. It is to let a user verify each load-bearing claim against the smallest supporting passage in the original source, then continue working from that evidence.

Brightwave's public architecture write-up is the primary reference: https://www.brightwave.io/blog/citations (observed 2026-09-12). Its useful lesson is that citations are a systems problem: positions have to survive ingestion, retrieval, generation, validation and format-specific rendering.

## What the Brightwave write-up reveals

### Evidence is positioned during ingestion
Position data travels with retrieved evidence rather than being reconstructed after an answer is generated:

- text/Markdown: absolute character start/end offsets, transformed through the rendering pipeline;
- PDF/Word/PowerPoint: page plus normalized 0-1 bounding boxes;
- spreadsheets: sheet identity plus A1 cell range;
- JSON/XML: path expression plus serialized value.

The evidence model is polymorphic. The UI has a format-specific resolver rather than pretending every format is highlighted prose.

### Citations are inline and claim-linked
The agent emits an inline directive containing an evidence ID. A parser removes the directive from visible prose and records which response range points to which evidence. The reader sees a small citation marker directly beside the supported claim.

### Click means exact verification
A valid citation opens the source, navigates to the exact page/range/node/cells and highlights the evidence. Multi-page rich-document evidence has an explicit continuation interaction.

### Validation has two independent layers
- structural: does the offset/range/path/page exist and resolve?
- semantic: does the passage actually support the generated claim?

Brightwave says it uses rule-based structural checks and an LLM-based support check. It treats a plausible-looking unsupported citation as worse than no citation.

### Citation quality is monitored continuously
The reported measures include claim support, citation coverage for substantive claims, evidence minimality/specificity, resolution failure rate, citation density and success by format. Production failures become regression cases.

## tracker.energy evidence schema
Use immutable evidence objects. Do not store only a page number or a CSS coordinate.

```json
{
  "evidence_id": "ev:<sha256>",
  "document_id": "ferc:<accession>",
  "component_id": "fercfile:<file_id>",
  "source_sha256": "...",
  "extraction_version": "...",
  "kind": "pdf_bbox",
  "page": 47,
  "boxes": [[0.11, 0.42, 0.83, 0.48]],
  "text_start": 3812,
  "text_end": 3970,
  "quote": "...",
  "method": "digital_text",
  "confidence": 1.0
}
```

`kind` is a discriminated union. Initial types:

- `pdf_bbox`: page, normalized boxes, page-text offsets and quote;
- `text_range`: raw-file character offsets plus quote;
- `table_cells`: table/sheet identity and cell range;
- `structured_path`: JSON path/XPath and serialized value;
- later, `image_region` and `media_time_range` only when those formats enter scope.

FERC and ISO/RTO PDFs should store both bounding boxes and text offsets. Boxes drive visual highlighting. Text offsets support search, quote comparison and fallback recovery.

## Passage identity and rebuild safety

1. Store original component bytes under their SHA-256. A changed source is a new component version, not an in-place rewrite.
2. Normalize bounding boxes to page width/height, but retain source page dimensions and extraction coordinates for diagnostics.
3. Passage IDs derive from source checksum, page and normalized quoted span. They must not depend on mutable database row numbers.
4. Citation points to a specific extraction version. A newer extractor can produce a new evidence object without erasing the old one.
5. On open, verify source checksum and exact quote. If the primary range fails, attempt a constrained same-page quote recovery and label it repaired. Never silently jump to a fuzzy match elsewhere.
6. A source revision creates `REVISES`/`SUPERSEDES` relationships and a citation-repair queue.

## Automation path from the current eight articles
The current `find_bbox.py` is a useful authoring proof: it runs `pdftotext -bbox-layout`, matches a phrase, and returns a page and rectangle. Corpus-wide automation needs to replace phrase hunting with ingestion-time position preservation:

1. parse every page into ordered tokens with text, page and word boxes;
2. persist page text plus a token-to-box map;
3. create passage windows along sentence/paragraph boundaries while retaining token offsets;
4. index passage text with evidence IDs attached;
5. retrieval returns evidence IDs, not copied text alone;
6. generated or deterministic analysis attaches an evidence ID to each claim;
7. parser writes claim-to-evidence records;
8. structural validator resolves every object against immutable source bytes;
9. semantic validator tests claim entailment and evidence minimality;
10. viewer renders one or several boxes, scrolls to the first and supports continuation.

This avoids fragile post-generation string matching. `find_bbox.py` remains a migration/repair tool for existing article quotes.

## Validation gates

### Structural, free and deterministic
- document, component and checksum exist;
- page and coordinates are in bounds;
- text offsets are in bounds;
- quote equals normalized source span;
- boxes overlap the tokens in the cited span;
- response citation resolves to an evidence object;
- every load-bearing claim has at least one citation;
- evidence object is actually referenced;
- multi-page evidence has an ordered continuation.

### Semantic
A reviewed labelled set should score:

- support: passage entails the claim at its stated strength;
- completeness: every material part of a compound claim is supported;
- minimality: citation is a passage, not an unnecessary full page;
- attribution: party allegation/position is not rendered as a FERC/ISO finding;
- numeric fidelity: value, unit, period and comparison basis match;
- temporal fidelity: proposal, effective date, revision and final action are distinct.

An LLM judge may help scale semantic QC only after exact pricing and user approval. It cannot be the only gate. Human-reviewed regression fixtures and deterministic checks remain the authority.

## Confidence and user-facing states
Do not show a decorative confidence score as if it proved truth. Show actionable states:

- **Verified position:** structural resolution passed against the stored source.
- **OCR source:** highlight is based on OCR and displays extraction confidence.
- **Support reviewed:** semantic support passed the current review gate, with gate version recorded.
- **Needs review:** structural citation resolves but support is uncertain or the claim is compound.
- **Broken/revised:** source checksum/range no longer matches; do not present normal citation affordance.

Confidence belongs to a specific stage: extraction confidence, entity-resolution confidence or semantic-support confidence. Never collapse them into one number.

## Smart Reader interactions

- Inline citation marker sits immediately after the claim.
- Hover/focus gives source title, page, minimal quote and evidence state without leaving the article.
- Click opens split view, preserves article position, scrolls the PDF to the first box and highlights all boxes.
- Continued evidence exposes next/previous passage controls.
- Selecting text in the PDF starts `Tell me more` with the exact evidence object, surrounding section and document identity.
- Current-document evidence is visually separated from wider-graph evidence.
- Copy/share can preserve a citation deep link; download always offers the original source and official URL.
- Keyboard and screen-reader users can open a citation, hear the quote/source/page, traverse continuations and return to the claim.

## Health metrics
Track by source connector and document format:

- extraction coverage and OCR rate;
- citation resolution success;
- click-to-correct-highlight success;
- unsupported-claim and missing-citation rate on reviewed samples;
- citation precision, completeness and minimality;
- citation density by answer/article type;
- repair rate after source/extractor revisions;
- time from source discovery to citation-ready passages.

Every production failure becomes a fixture. A green aggregate must not hide a failing connector or format.
