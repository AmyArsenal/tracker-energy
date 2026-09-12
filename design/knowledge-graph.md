# Regulatory knowledge graph contract

## Purpose
The graph is the retrieval and provenance backbone for FERC and stakeholder-meeting intelligence. It connects evidence-bearing mentions and events so a question can move from a cited passage to the wider regulatory record without confusing inference with fact.

## Corpus boundary
- Every newly filed FERC eLibrary accession and every retrievable component.
- Public meetings and linked agendas, minutes, presentations, vote records and revision requests from PJM, CAISO, ERCOT, MISO, SPP, NYISO and ISO-NE.
- Existing map, EIA, HIFLD, plant, transmission and interconnection-queue data are outside active graph investment for now.

## Node types
- document, component, passage;
- FERC docket and ISO/RTO initiative/workstream;
- meeting, committee and vote/action;
- company, SPV and organization;
- person and role;
- project/facility;
- technology and topic;
- region, market and ISO/RTO.

## Evidence model
Every extracted entity mention stores document/component, passage, offsets, surface text, extractor/version and confidence. Every accepted relationship stores its supporting passage or official metadata field, extraction rule/model, confidence and review state. Derived relationships keep the derivation path.

`SAME_AS` is a reviewed identity assertion, not a fuzzy-name convenience. Shared addresses, lawyers or parent-like names become candidates until evidence proves the relationship.

## Event and relationship vocabulary
Initial edges: `HAS_COMPONENT`, `IN_DOCKET`, `FILED_BY`, `AUTHORED_BY`, `MENTIONS`, `PRESENTED_AT`, `MEMBER_OF`, `REVISES`, `RESPONDS_TO`, `SUPERSEDES`, `VOTED_ON`, `ADOPTED_BY`, `AFFECTS_PROJECT`, `OPERATES_IN`, `OWNED_BY`, `SAME_AS`.

A procedural filing creates participation and chronology edges. It does not create support/opposition or agency-decision edges unless its text supplies that evidence.

## Version and correction rules
- Source documents and components are immutable by checksum; revisions create new versions and explicit revision edges.
- Extraction outputs name the code/model version.
- Reprocessing creates a new extraction version before promotion.
- Manual corrections are first-class assertions with author/time and survive rebuilds.
- Removed or rejected edges remain in audit history.

## Retrieval contract for `Tell me more`
Start with selected text and the current document. Expand through only evidence-bearing edges under a bounded depth and source/date scope. Return the path that caused each related document to be selected. Answer citations point to passages; graph paths explain relevance but are not substitutes for textual support.
