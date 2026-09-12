# ISO/RTO regulatory lifecycle and version-diff contract

## Product job
Unify a process that is scattered across committee calendars, meeting packets, revision systems, FERC eLibrary and published tariffs/manuals:

`stakeholder discussion -> proposal/revision request -> vote -> FERC filing -> FERC action -> effective tariff/manual/rule`

The chain is a hypothesis until each relationship has source evidence. Chronology alone does not establish that a meeting caused a filing or that a filing changed a specific section.

## Source registry per ISO/RTO
Each connector for PJM, CAISO, ERCOT, MISO, SPP, NYISO and ISO-NE keeps separate registered endpoints and completeness rules for:

- committees, calendars and meeting instances;
- agendas, minutes, presentations, transcripts/recordings where public;
- voting/action records;
- proposal and revision-request systems;
- FERC filing references/accessions;
- eTariff records, tariff sheets and effective versions;
- business-practice, market, planning and interconnection manuals;
- revision logs, redlines and clean published editions.

Every endpoint exposes last attempted/successful check, newest observed source timestamp, expected versus retrieved linked items, status and error. A landing page without an expected-item contract is not a complete connector.

## Immutable versions
A logical manual/tariff has stable identity; each fetched edition is a version with source URL, retrieved/published/effective timestamps, source checksum, media type and extraction version. Changed bytes never overwrite an earlier version. Identical bytes under a new URL/time become an observed publication event without duplicating content.

## Section identity
Prefer publisher-stable article/section identifiers. Otherwise derive candidates from normalized heading path, numbering and nearby text, then reconcile across versions. Store confidence and evidence for renumbering/moves. A section's display number is an attribute, not its identity.

## Diff pipeline
1. verify and extract both immutable versions page by page;
2. recover heading hierarchy and block order;
3. align sections using stable IDs, heading paths and constrained similarity;
4. within aligned sections, compute word/sentence-level additions and deletions;
5. classify unchanged, wording change, added, deleted, moved or renumbered;
6. create old and new evidence objects for every changed span;
7. run deterministic noise suppression for headers, page numbers and formatting;
8. leave legal/operational implication as `unreviewed` until evidence-backed analysis is available.

The UI always permits side-by-side old/new verification. A generated implication cannot replace the actual diff.

## Graph events and edges
Nodes: meeting, committee, proposal/revision request, vote/action, FERC filing, FERC order, logical manual/tariff, version, section and passage.

Initial relationships: `DISCUSSED_AT`, `PROPOSES`, `REVISES`, `VOTED_ON`, `RESULTED_IN_FILING`, `IN_DOCKET`, `RESPONDS_TO`, `ACCEPTED_BY_ORDER`, `REJECTED_BY_ORDER`, `AMENDS_SECTION`, `IMPLEMENTS`, `EFFECTIVE_AS_OF`, `SUPERSEDES`.

Each edge records source evidence, extraction/version, confidence and review state. `RESULTED_IN_FILING`, `ACCEPTED_BY_ORDER`, `AMENDS_SECTION` and `IMPLEMENTS` require explicit references, matching proposal identifiers or reviewed evidence. They are not inferred from dates alone.

## Watch behavior
A watch may target any node or bounded lifecycle chain. On a new event/version:

- show what changed with old/new passage citations;
- show which stage of the lifecycle changed;
- show new evidence-backed links and candidate links needing review;
- distinguish proposed, filed, accepted, effective and superseded;
- deduplicate repeated publications by checksum/event identity;
- preserve watch prompt/version and alert-run evidence.

The first free alert is a deterministic change record. LLM implications/custom briefs remain paid, cost-metered and citation-gated.
