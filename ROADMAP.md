# tracker.energy roadmap

## Product moat
The moat is the document engine plus UX and workflow: every public FERC filing should become a source-grounded, searchable, tagged record, then feed monitoring, calendar, briefing and docket workflows that are easier to use than raw dockets.

## Sequencing rule
GitHub migration comes first. After the initial push, ship one stage at a time. Do not begin the next stage until the current stage has a working user path, source provenance, validation, failure handling and a visible release. Free-tier engineering may proceed after the push. Any paid API, model, mail or hosting work requires current exact pricing and the user's explicit approval first.

## 1. FERC document engine foundation

### 1A. Complete filed-date firehose
Replace the `"data center"` discovery query as the corpus boundary with a fully paginated nightly pull of every new FERC eLibrary filing by `filed_date`, without keyword, class, category or docket filters. Use accession number as identity; persist a durable high-water mark plus an overlap window so delayed or corrected filings are recovered without duplicates. Crawl every transmittal/component of each accession, preserve eLibrary metadata and source links, and record partial failures explicitly.

Keep the 16 current large-load dockets as priority flags for processing, validation and product views. They are not the corpus boundary.

**Done when:** a fixture-tested multipage filed-date pull ingests every accession and component exactly once; reruns are idempotent; delayed/corrected records are reconciled; source totals and page totals balance; failures resume safely; and a daily completeness report shows discovered, inserted, updated, skipped and failed counts.

### 1B. Deterministic and statistical triage
Run a cheap local, non-LLM classifier over every filing. Produce separate, confidence-scored fields for document category, substantive versus procedural status, region/ISO/RTO, named companies and controlled topics. Preserve raw eLibrary labels and every rule/model version so classifications are auditable and can be rebuilt. Low-confidence output must remain unknown or enter review, never become a confident fact.

**Done when:** a labelled test set reports precision/recall by field; motions to intervene are not represented as merits positions; entity offsets point back to source text; model/rule versions are stored; and manual corrections survive rebuilds.

### 1C. Page-anchored full text
Mirror every retrievable filing component subject to documented safety limits, extract text page by page, preserve page numbers and stable passage anchors, and index the extracted text. Keep original PDFs immutable and checksummed. OCR scanned pages as a separate, confidence-marked path. A citation must resolve from a search result or article reference to the exact passage and source PDF.

**Done when:** text coverage and extraction failures are measurable; passages round-trip to the correct page; scanned, malformed, encrypted and oversized files fail visibly; source/PDF/text checksums are retained; and citation fixtures pass after a rebuild.

### 1D. Filing summaries
Create a summary record for each filing for the FERC page, with claims grounded only in extracted passages. Prioritize hot-docket and substantive filings. Procedural filings should use deterministic templates where possible rather than spend an LLM call. Store prompt/model version, source passages, generation status and cost.

**Paid gate:** do not build or run LLM summaries until current model pricing, expected filing volume, monthly cost ceiling and fallback behavior have been reported and explicitly approved.

**Done when:** every summary sentence links to supporting passages; unsupported output fails closed; substantive and procedural records are clearly distinguished; regeneration is versioned; and actual cost per filing and per month is observable.

### 1E. FERC reading experience
Replace the PDF-centered article design. The default is a full-width, full-page editorial article with inline references to exact source passages. Selecting a reference opens a split view: article on one side, source document on the other, scrolled to and highlighting the cited passage. Put related/also-read records below the article.

**Execution gate:** record and design this now; implement after the repository push and after the underlying page-anchored citation contract is stable.

**Done when:** the article is fully readable without an open PDF; every inline reference opens the correct document, page and passage; keyboard/mobile behavior is tested; closing the source restores the full article; and related reads appear below without displacing the primary reading flow.

## 2. Watch and alert plumbing
Start simple. Detect and persist changes to tracked dockets and queue records, classify additions/status changes/document changes, deduplicate alerts, and expose a watch control plus alert history. Every alert links to the changed source record and exact evidence where available. Add delivery only after change detection is reliable.

**Done when:** a user can watch a docket or queue project, a fixture-tested diff generates one alert for one real change, retries do not duplicate it, and the UI shows source, observed time, old value, new value and delivery state.

## 3. ISO/RTO stakeholder calendar
Normalize stakeholder meetings from ISO/RTO public calendars into one calendar with market, committee, topic, time zone, materials, registration link, source and freshness. Connect relevant meetings back to watched dockets and queue topics without inventing a relationship.

**Done when:** all registered ISO/RTO calendar connectors show live/partial/blocked status; users can filter and watch meetings; time zones and update/cancellation events are tested.

## 4. Custom-prompt alert briefs
Let each user write a bounded prompt describing what they care about. After a monitored change or meeting, generate a brief for that context using only cited materials. Keep the user's prompt version, input sources, generated output, citations and delivery result.

Personalized email requires a transactional sender. Expected operating cost is roughly $1-3/month, but this is planning context, not permission. Do not create an account, subscribe or incur paid usage without exact current pricing and explicit approval.

**Done when:** preview works without sending; every claim maps to source evidence; prompts are versioned; unsafe or missing-source cases fail closed; paid email delivery is separately approved and monitored.

## 5. Docket chat and timeline
Add source-bounded docket questions plus a procedural timeline. Answers must distinguish filing, allegation, party position, staff action, order and unresolved issue. Timeline events retain accession/source, date, party, document type, relationship to earlier events and confidence.

**Done when:** representative dockets pass citation and chronology tests; unanswered questions say what evidence is missing; users can move from answer to exact source passage.

## Delivery path
Feature work is delivered through the checksum-verified Feature Channel and committed by the repository's built-in GitHub Actions token. No user credential is needed after the first push.
