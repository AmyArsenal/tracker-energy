# Evidence-first regulatory search

## Product contract
Search is the router into the regulatory corpus. It must let a domain expert narrow the universe exactly, recover relevant language despite wording variation, understand why each result matched, and move from a result to the supporting passage in one click.

Primary competitor references:
- https://halcyon.io/blog/machine-readable/search-everything-old-is-new-again
- https://halcyon.io/blog/machine-readable/building-the-stack

The public posts describe product principles and some operating characteristics, not enough detail to reproduce Halcyon's ranking algorithm. Do not invent an undisclosed vendor, lexical engine, vector database, embedding model, fusion formula or reranker.

## What Halcyon publicly describes

1. **Precision/recall framing.** Exact keywords are precise but brittle to misspellings and related language. Semantic similarity recovers concepts but can drift.
2. **Constraints before fuzziness.** `data centers in Wisconsin` should mean a hard Wisconsin universe plus a semantic/text concept, not a global fuzzy search that happens to return Minnesota.
3. **Visible domain filters.** Source/jurisdiction, date, docket, keyword, filing type and topic are first-class controls rather than hidden prompt interpretation.
4. **Semantic retrieval.** They explicitly discuss transformer embeddings and matching conceptual similarity.
5. **Metadata-aware scale.** Their stack post says vector search over billions of embeddings must compose with high-cardinality metadata filters while balancing recall and latency.
6. **Specialized reranking.** Their stack post says an authorship graph contributes document-authority features; metadata augments LLM query rewriting and answer generation.
7. **Fast index mutation.** The search post says new metadata can appear almost instantly, all document metadata can rebuild in minutes, and the searchable corpus in a couple of hours. The later stack post says document and embedding metadata can reindex in minutes or hours.

Not publicly specified: exact lexical engine, spelling correction, embedding model, vector store, whether lexical and semantic scores are fused and how, reranker type, query-rewrite model/prompt, freshness SLA, benchmark set, nDCG/recall/latency numbers or per-source completeness.

## tracker.energy query model
Keep hard scope, textual intent and answer generation separate.

```json
{
  "scope": {
    "sources": ["ferc"],
    "regions": ["PJM"],
    "dockets": [],
    "filed_from": "2026-01-01",
    "filed_to": null,
    "filing_types": ["order", "protest"],
    "substance": ["substantive"],
    "entities": [],
    "committees": []
  },
  "text": {
    "exact": [],
    "all_terms": [],
    "any_terms": ["co-location", "behind the meter"],
    "semantic": "rules for serving a data centre directly from a generator"
  },
  "sort": "relevance",
  "as_of": "..."
}
```

- Scope values are controlled IDs resolved visibly. They never become embedding text.
- The UI shows active constraints as removable chips and reports the count after each filter.
- Natural language may propose a parsed scope, but the user sees and can correct it before it becomes a saved query/alert.
- `as_of` pins repeatability and shows corpus freshness.

## Retrieval pipeline

### Stage 0: candidate eligibility
Apply permissions, source health, source/date/jurisdiction/docket/type/topic/entity/committee and procedural-substantive filters. Unknown or unclassified values are not silently treated as negatives; the UI exposes excluded unknown counts.

### Stage 1: lexical passage retrieval
Use SQLite FTS5 during the single-node phase; migrate the same passage IDs and filters to Postgres full text/trigram when needed. Support phrases, required/optional/excluded terms, prefix matching and carefully bounded spelling/alias expansion. Return passage evidence IDs, BM25-like score and exact matched spans.

### Stage 2: semantic passage retrieval
Add only after a labelled retrieval benchmark exists. Embed passages, not whole filings. Apply the hard metadata scope during candidate selection rather than retrieving globally and discarding later. Cache vectors by source checksum + passage + model version. Semantic results return evidence IDs and similarity, never anonymous chunks.

### Stage 3: graph expansion
For entity/docket/meeting questions, add a bounded candidate set through evidence-bearing graph edges. Record the path that admitted each candidate. A graph path is a relevance feature, not proof of an answer.

### Stage 4: fusion and reranking
Fuse independent ranked lists using rank-based fusion rather than incomparable raw scores. Rerank the top bounded set using auditable features:

- lexical and semantic rank;
- exact phrase/title/docket match;
- source and filed-date freshness;
- source document class and substantive/procedural state;
- authority appropriate to the question, e.g. final order over a party filing when asking what FERC decided;
- graph distance/path type;
- citation-ready extraction state;
- duplication/version status.

Never use a universal “authority” score. The right authority depends on intent: a protest is authoritative for that party's position, not for the Commission's holding.

A paid cross-encoder/LLM reranker is optional and must beat the free baseline on the same benchmark within the $5 ceiling before promotion.

### Stage 5: presentation
Each result shows:

- official title, source, accession/docket, filer, date, source class and derived type/topic visibly distinguished;
- the smallest matching passage with highlights;
- why it matched: exact term, semantic concept, graph relationship and active filters;
- extraction/citation state and source freshness;
- View passage, View document, Download, Share, Query and Watch actions;
- related versions/components collapsed under the accession rather than flooding results.

Clicking the passage opens Smart Reader at the exact page/boxes. Search does not ask users to trust a generated synopsis.

## Query rewriting
A rewrite is a transparent candidate generator, not hidden intent replacement.

- deterministic normalization handles case, punctuation, docket syntax, known aliases, singular/plural and spelling variants;
- the graph expands reviewed aliases such as corporate names and committee acronyms;
- an LLM may later propose concepts, filters and alternates, each shown separately from the user's original words;
- exact quoted text is never semantically broadened;
- saved queries keep the original, parsed scope, expansions and version so alerts are reproducible.

## Freshness and indexing

1. Firehose commits an accession/component only after page reconciliation.
2. Metadata becomes filterable immediately after commit.
3. Extracted pages create FTS passages transactionally.
4. Entities/edges and vectors are asynchronous derived indexes with explicit status/version.
5. A result can appear metadata-only, but the UI must say citation text is pending.
6. Reindex by immutable source checksum and changed version; do not rebuild unchanged passages.
7. Maintain index watermarks per connector and stage: discovered, metadata, downloaded, extracted, classified, embedded and searchable.
8. Last-good indexes remain active if a derived rebuild fails.

## Search evaluation
Create a judged domain benchmark containing real information needs, exact expected passages and acceptable alternates. Include typo, alias, temporal, docket, party-position, Commission-decision, hard-negative and cross-document relationship cases.

Track by query class and connector:

- Recall@10/50 and nDCG@10;
- passage precision@5;
- zero-result correctness and unknown-class exclusions;
- filter correctness;
- click-to-correct-passage rate;
- citation resolution rate;
- index freshness lag;
- p50/p95 latency;
- duplicate/version collapse accuracy;
- semantic-only wins and semantic-drift failures.

Promotion requires evidence that hybrid beats lexical alone without a material precision regression. Every bad production result becomes a judged regression case.

## Why this can beat Halcyon
We match the part they describe correctly: visible hard constraints, source normalization, hybrid retrieval, fast incremental indexing and domain reranking. The wedge is evidence:

- rank passages, not merely documents;
- explain every admission and score feature;
- click directly to immutable page-level proof;
- distinguish source metadata from our classification;
- make source/index completeness visible;
- use regulatory authority by question intent;
- let saved queries and alerts inherit reproducible evidence-bearing search plans.

The search result is not the end product. It is a reliable entry point into the cited reader, graph and workflow.
