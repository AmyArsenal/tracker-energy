# Brightwave citation/reader architecture (verified Sep 10, 2026)

## Terminology check
Amit's phrase "bounding box attenuation" = Brightwave's "bounding boxes on PDF
pages" citation mechanism (their term: "citations that resolve"; PDF evidence
carries bounding-box objects with page number + normalized 0-1 coordinates).
Product feature names: "Citations" and "Intelligent Highlighting:
Details-on-Demand". Use "evidence-linked" / "bounding-box citations" in our
vocabulary; note the mapping if Amit repeats his phrase.

## Sources (verified)
- https://www.brightwave.io/blog/citations ("How We Built AI Citations That
  Actually Work", Thet Naing, Founding ML Engineer, Mar 18 2026; canonical URL
  after redirect from /engineering/citations)
- https://brightwave.io/blog/intelligent-highlighting-a-faster-way-to-connect-the-dots
  ("Intelligent Highlighting: Details-on-Demand", Jul 8 2025)

## Architecture (from the engineering article)
1. Position metadata attached AT INGESTION: PDF -> bounding boxes (0-1
   normalized to page), text/markdown -> absolute char offsets, spreadsheets
   -> sheet + A1 ranges, JSON/XML -> path expressions. Polymorphic evidence
   schema (discriminated union per type). Position info rides through
   retrieval into the agent's context.
2. Agents embed inline citation directives while generating:
   `claim text :cit[claim]{evidence_id=abc123}`. A parsing step strips
   directives, creates citation records mapping claim -> evidence position.
   User sees clean prose with small citation markers.
3. Resolution: frontend renders semi-transparent bbox overlays absolutely
   positioned on the PDF page; multi-page spans get "continues on next page".
   Char-offset docs: offset transformation functions map raw->rendered
   positions through the markdown pipeline.
4. Validation before display: rule-based structural checks (offsets in bounds,
   sheet exists, path resolves) + LLM check "does the cited passage actually
   support the claim". Both must pass. A structurally valid but unsupported
   citation is "worse than no citation".
5. Continuous evals: LLM-as-judge over production citation-claim pairs;
   per-format success rates (PDF bbox regressions can't hide behind text);
   citation-density drift monitoring; every production failure -> new test
   case. ~1M citation evaluations per 30 days in production.
6. Lessons: citations are a systems problem, not an LLM problem; per-format
   citation UX (no unified viewer abstraction); measure citation quality as
   rigorously as model quality.

## Intelligent Highlighting (the "tell me more" interaction)
User drags to highlight ANY passage (PDF line, chat quote, report finding) ->
menu -> "Attach to Chat" -> sourced rundown compiled from all relevant
documents in seconds. Point-at-the-thing instead of crafting prompts.

## Mapping to tracker.energy
ALREADY HAVE: annolink inline citation spans in nightly analysis -> pdf.js
overlay bounding boxes on the source PDF (split view). Same architecture.
GAPS: (a) annotations are author-chosen per article, not per-claim
systematic; (b) no citation QC/validation loop; (c) no highlight-to-ask
interaction (needs a runtime); (d) bbox evidence not stored in canonical
store for corpus-level deep links.
