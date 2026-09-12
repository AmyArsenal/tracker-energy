# Smart Reader product contract

## Product thesis
tracker.energy does not win by collecting the largest pile of documents. Complete collection is table stakes. The wedge is citation depth: turn each relevant source into a trustworthy workspace where analysis, source passages and follow-up questions stay connected.

This reader depends on the page-anchored full-text engine in ROADMAP 1C. It must not fake passage navigation from guessed coordinates or summary text.

## Reference anatomy
The supplied Halcyon screens establish a useful baseline:

- cross-corpus search with a synopsis on each result and metadata filters;
- a document page with a metadata rail, executive summary and inline citation markers;
- source actions for view, download and share;
- a query action from the document;
- saved query runs with citation markers on claims and edit-and-rerun;
- user-created alerts plus suggested alert packs.

These are reference patterns, not a design to copy. tracker.energy should retain its own visual language and regulatory-workflow model.

## Core reading flow

### 1. Editorial default
Open an analysis as a full-width, full-page article. The source PDF is closed by default. Keep the title, dek, byline/date, scope, inline citations and article body visually primary. Put related/also-read material below the article rather than in a competing side rail.

### 2. Inline passage references
Each load-bearing claim carries a compact reference linked to a stable citation object:

- source document and accession;
- component/file ID and checksum;
- page number;
- extracted text span or token offsets;
- bounding rectangles when available;
- exact quoted passage;
- extraction/OCR method and confidence.

The link must still resolve after reprocessing. If a revised source breaks the checksum or passage match, show the citation as needing repair instead of silently sending the user to an approximate page.

### 3. Click-to-split source
Selecting a reference changes the workspace from article mode to split mode:

- article remains on the left and preserves reading position;
- source opens on the right;
- viewer scrolls to the cited page and passage;
- cited lines are highlighted;
- the active reference is visibly selected;
- previous/next reference navigation works without closing the document;
- close returns to the exact article position.

Expose View source, Download and Share source. Sharing an article citation should deep-link to the article plus citation state when permissions allow, with a fallback to the official source URL.

### 4. Agentic source interaction
The PDF is not a dead preview. A user can select source text and choose `Tell me more`.

The question context must explicitly contain:

- the selected passage;
- surrounding page/section text;
- the current document's metadata and extracted text;
- the current article and citation;
- optional wider-corpus retrieval, clearly separated from the document itself.

Answers label which claims come from the current document and which come from other sources. Every factual claim links to a supporting passage. When the record does not answer the question, say so. Never turn an allegation, filing position or procedural motion into an agency finding.

Follow-up actions can include: explain in plain language, define term, compare with earlier filing, show what changed, find related docket events and add to a saved query. These actions are shortcuts to bounded prompts, not privileged answer modes.

### 5. Document workspace
A source record should offer:

- official title and source;
- accession, docket, filer, filed/issued date, FERC class/type and component list;
- extraction status and freshness;
- concise source-grounded summary;
- cited key points;
- View, Download, Share and Query;
- related docket filings, earlier/later versions and related analysis below.

The metadata should explain the document without crowding the reading surface. On narrow screens, it collapses behind a details control.

### 6. Query workspace
Saved queries keep:

- user question and version;
- selected scope and filters;
- source set and retrieval time;
- answer with passage citations;
- unsupported or unresolved points;
- edit-and-rerun history.

A rerun creates a new version rather than overwriting the earlier answer.

### 7. Alerts
Alerts can begin from any stable object: docket, company/entity, topic, region/ISO, filing, calendar event or saved query. Suggested alert packs are onboarding shortcuts, not the moat. The moat is a user's accumulated, source-bounded watch logic and custom briefing context.

## Trust and evidence rules

1. Every analysis claim must cite a passage, not merely a document.
2. Search snippets and generated summaries are discovery aids, never source evidence by themselves.
3. UI distinguishes official metadata, extracted source text, deterministic classification and generated analysis.
4. Citations preserve source identity, page, passage, file checksum and extraction version.
5. OCR-derived passages show lower confidence and link to the image page.
6. Permission boundaries follow the source; share actions cannot make private material public.
7. Answers fail closed when source extraction, passage matching or provenance is missing.

## Interaction states to design and test

- article only;
- split view loading;
- active citation found and highlighted;
- multiple rectangles/continued passage;
- citation not found after source revision;
- scanned/OCR source;
- multi-component accession;
- agent answer streaming with citations;
- no answer in current document;
- wider-corpus answer with sources separated;
- mobile article and mobile source handoff;
- keyboard navigation and screen-reader labels;
- download/share error and official-source fallback.

## Measures that matter

- percentage of analysis claims with valid passage citations;
- citation click-to-correct-highlight success rate;
- full-text and OCR coverage by component;
- source-to-answer citation precision on a reviewed test set;
- time from new filing to classified, searchable text;
- article-to-source citation open rate;
- document question success and explicit no-answer rate;
- saved query, watch and return-use rates.

Raw document count is a coverage measure, not the product's moat.
