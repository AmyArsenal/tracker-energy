# tracker.energy roadmap

## Product moat
Moat #1 is UX/workflow. Moat #2 is passage-level citation quality. The cited regulatory knowledge graph connects both: Every public FERC filing and every public stakeholder-meeting document from the seven U.S. ISO/RTOs should become a source-grounded, searchable, tagged record connected to the people, companies, projects, proceedings, committees, technologies and decisions it names. The graph makes `Tell me more` answer from relationships across the corpus rather than from one isolated PDF.

## Current scope

**Build now:** FERC eLibrary; public stakeholder meetings and their agendas, minutes, presentations, vote records and revision requests from PJM, CAISO, ERCOT, MISO, SPP, NYISO and ISO-NE; full text and passage citations; entity/relationship graph; Smart Reader; graph-bounded questions.

**Maintenance only:** existing EIA, HIFLD, power-plant, transmission-map and interconnection-queue layers remain live as free marketing surfaces. Do not delete them, but make no new product investment in them unless the user changes scope. Keep only the minimum operational checks needed to avoid publishing broken or stale-looking pages.

## Sequencing rule
GitHub migration comes first. After the initial push, ship one stage at a time. Do not begin the next stage until the current stage has a working user path, source provenance, validation, failure handling and a visible release. Free-tier engineering may proceed after the push. Any paid API, model, mail or hosting work requires current exact pricing and the user's explicit approval first.

## 1. FERC firehose and full text

### 1A. Complete filed-date firehose
Replace the `"data center"` discovery query as the corpus boundary with a fully paginated nightly pull of every new FERC eLibrary filing by `filed_date`, without keyword, class, category or docket filters. Use accession number as identity; persist a durable high-water mark plus an overlap window so delayed or corrected filings are recovered without duplicates. Crawl every transmittal/component of each accession, preserve eLibrary metadata and source links, and record partial failures explicitly.

Keep the 16 current large-load dockets as priority flags for processing, validation and product views. They are not the corpus boundary.

**Done when:** a fixture-tested multipage filed-date pull ingests every accession and component exactly once; reruns are idempotent; delayed/corrected records are reconciled; source totals and page totals balance; failures resume safely; and a daily completeness report shows discovered, inserted, updated, skipped and failed counts.

### 1B. Page-anchored full text
Mirror every retrievable filing component subject to documented safety limits, extract text page by page, preserve page numbers and stable passage anchors, and index the extracted text. Keep original PDFs immutable and checksummed. OCR scanned pages as a separate, confidence-marked path. A citation must resolve from a search result or article reference to the exact passage and source PDF.

**Done when:** text coverage and extraction failures are measurable; passages round-trip to the correct page; scanned, malformed, encrypted and oversized files fail visibly; source/PDF/text checksums are retained; and citation fixtures pass after a rebuild.

### Phase 1 execution plan
1. Separate the eLibrary client from product selection logic and capture a raw response fixture for contract tests.
2. Add a durable ingestion state with last completed filed date/page, run identity and a configurable overlap window. Never advance the checkpoint past a failed page.
3. Query one bounded filed-date slice at a time and paginate until FERC's returned total is accounted for. Split a date slice when it exceeds safe page/run bounds.
4. Normalize accession metadata and enumerate all transmittals/components, preserving FERC IDs, filenames, media type and source order.
5. Upsert accessions and components independently. Store immutable source hashes and mutable retrieval state so corrections do not erase history.
6. Queue downloads with conservative concurrency, timeout/retry/backoff and resumable status. No formal FERC request limit is assumed unless a source documents one.
7. Extract digital text per page, then route empty/image pages to OCR. Produce stable passage IDs from file checksum, page and normalized span.
8. Write daily reconciliation and coverage reports; fail publication when page totals, IDs or checksums do not balance, while retaining the last-good product output.
9. Backfill historical dates only after the incremental nightly path passes fixtures and a live bounded canary.

No paid service is needed for this phase. Storage/hosting impact must be measured before expanding the historical backfill.

## 2. Entity extraction and graph foundation
Run cheap local, non-LLM extraction over every document. Produce separate, confidence-scored entities for companies, SPVs, dockets, committees, people, technologies, projects and regions/ISO/RTOs, plus document category and substantive-versus-procedural status. Preserve raw mentions, text offsets, aliases, model/rule version and provenance.

The graph uses explicit nodes and evidence-bearing edges. Example edges include `FILED_BY`, `IN_DOCKET`, `MENTIONS`, `PRESENTED_AT`, `MEMBER_OF`, `REVISES`, `RESPONDS_TO`, `VOTED_ON`, `AFFECTS_PROJECT` and `SAME_AS`. A relationship is not accepted merely because two names are similar. Low-confidence identity resolution remains a candidate for review.

**Done when:** a labelled set reports precision/recall by entity and relationship; every edge resolves to a source passage; motions to intervene are not represented as merits positions; manual corrections survive rebuilds; and graph history is versioned rather than overwritten.

## 3. Smart Reader v1
Detailed interaction and evidence contract: [`design/smart-reader.md`](design/smart-reader.md). Citation architecture: [`design/citation-system.md`](design/citation-system.md). Reference-screen notes: [`design/halcyon-reference.md`](design/halcyon-reference.md).

Replace the PDF-centered article design. The default is a full-width, full-page editorial article with inline references to exact source passages. Selecting a reference opens a split view: article on one side, source document on the other, scrolled to and highlighting the cited passage. Put related/also-read records below the article. Include official metadata plus View, Download, Share and Query actions.

V1 establishes the cited reading and document workspace. Graph-powered free-form answers come after the seven stakeholder corpora and graph relationships are dependable.

**Done when:** the article is fully readable without an open PDF; every inline reference opens the correct document, page and passage; keyboard/mobile behavior is tested; closing the source restores the full article; and related reads appear below without displacing the primary reading flow.

## 4. All ISO/RTO stakeholder corpora
Build source-specific crawlers for PJM, CAISO, ERCOT, MISO, SPP, NYISO and ISO-NE. Ingest public meeting records and all linked agendas, minutes, presentations, vote records and revision requests. Preserve meeting/committee hierarchy, original URL, posted/revised timestamps, file relationships, cancellation/reschedule status and source freshness. Generic scraping is not a substitute for connector-specific completeness accounting.

**Done when:** all seven connectors expose live/partial/blocked status; each reconciles meetings and expected linked documents; revisions retain history; time zones and cancellations are tested; documents pass the same component, full-text, citation and graph pipeline as FERC; and source failures do not silently publish partial current data as complete.

## 5. Graph-powered `Tell me more`
Let a user select source text or a graph object and ask a bounded question. Retrieve the selected passage, surrounding section, document, connected entities/edges and relevant related sources. Clearly separate current-document evidence from wider-corpus evidence. Every factual answer claim links to an exact supporting passage; unresolved identity, chronology or authority is stated.

LLM generation is a paid gate. Do not build or run it until current model pricing, projected query/summary volume, monthly cost ceiling, privacy posture and fallback behavior have been reported and explicitly approved. Deterministic procedural summaries and graph navigation may ship without model spend.

**Done when:** reviewed questions pass citation precision and relationship-provenance tests; no-answer cases fail closed; filing position, allegation, staff action, vote and final order remain distinct; prompt/model/retrieval versions are recorded; and actual cost per answer is observable.

## 6. Filing summaries
Create a summary record for each filing and stakeholder document using claims grounded only in extracted passages. Prioritize substantive and high-impact records; use deterministic templates for procedural filings where possible.

**Paid gate:** do not build or run LLM summaries until exact pricing and explicit approval.

**Done when:** every summary sentence links to supporting passages; unsupported output fails closed; substantive and procedural records are distinguished; and regeneration and cost are versioned.

## 7. Watch and alert plumbing
Start simple. Detect and persist changes to tracked dockets and queue records, classify additions/status changes/document changes, deduplicate alerts, and expose a watch control plus alert history. Every alert links to the changed source record and exact evidence where available. Add delivery only after change detection is reliable.

**Done when:** a user can watch a docket or queue project, a fixture-tested diff generates one alert for one real change, retries do not duplicate it, and the UI shows source, observed time, old value, new value and delivery state.

## 8. ISO/RTO stakeholder calendar
Normalize stakeholder meetings from ISO/RTO public calendars into one calendar with market, committee, topic, time zone, materials, registration link, source and freshness. Connect relevant meetings back to watched dockets and queue topics without inventing a relationship.

**Done when:** all registered ISO/RTO calendar connectors show live/partial/blocked status; users can filter and watch meetings; time zones and update/cancellation events are tested.

## 9. Custom-prompt alert briefs
Let each user write a bounded prompt describing what they care about. After a monitored change or meeting, generate a brief for that context using only cited materials. Keep the user's prompt version, input sources, generated output, citations and delivery result.

Personalized email requires a transactional sender. Expected operating cost is roughly $1-3/month, but this is planning context, not permission. Do not create an account, subscribe or incur paid usage without exact current pricing and explicit approval.

**Done when:** preview works without sending; every claim maps to source evidence; prompts are versioned; unsafe or missing-source cases fail closed; paid email delivery is separately approved and monitored.

## 10. Docket chat and timeline
Add source-bounded docket questions plus a procedural timeline. Answers must distinguish filing, allegation, party position, staff action, order and unresolved issue. Timeline events retain accession/source, date, party, document type, relationship to earlier events and confidence.

**Done when:** representative dockets pass citation and chronology tests; unanswered questions say what evidence is missing; users can move from answer to exact source passage.

## Delivery path
Feature work is delivered through the checksum-verified Feature Channel and committed by the repository's built-in GitHub Actions token. No user credential is needed after the first push.
