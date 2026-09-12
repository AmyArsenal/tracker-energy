# Storage and serving architecture

## Principle
Use one boring relational store until measured load proves it insufficient. Keep immutable source files outside the database. Do not add a vector or graph database merely because the product has semantic retrieval or a graph-shaped domain.

## Phase 1: single-node document engine

### Immutable source bytes
Store PDFs and other original components in content-addressed object storage under SHA-256. Keep accession, FERC file ID, original filename, official URL, media type, byte count and retrieval status in the relational database. Git stores code and compact fixtures, not the filing corpus.

Development and bounded canaries may use a local filesystem/workflow artifact. Historical backfill requires an object-storage durability and cost decision first.

### Metadata, passages, evidence and graph
Use SQLite with WAL for ingestion state, normalized metadata, page text, passages, citation evidence, entities, mentions and graph edges. Add FTS5 for lexical passage search. Model the graph as ordinary node, edge and evidence tables with indexed source/target/type columns. SQLite recursive CTEs are enough for bounded one-to-three-hop retrieval.

This keeps transactions, deduplication, provenance and backups in one file. It also makes migration straightforward because IDs and relationships are not encoded in a vendor-specific graph format.

Operational planning envelope, not a SQLite hard limit: one writer, a few read processes, roughly 100,000 to 1,000,000 documents and a 10-50 GB indexed database can be reasonable on a provisioned local SSD if benchmarks meet latency and backup targets. Passage count, token/box density, write concurrency and query shape matter more than document count. Benchmark at each order of magnitude; do not promise this range without corpus measurements.

### UI and serving
Keep the static article/application shell on the existing static host. A citation-ready corpus needs a small read API for search, evidence resolution, graph neighbourhoods and signed source-file URLs. During the canary it can run against a read-only SQLite snapshot. GitHub Actions remains orchestration, validation and release control, not the production database or PDF store.

## When Postgres earns its place
Move metadata, passages, evidence and graph tables to Postgres when any of these is measured:

- multiple ingestion/API writers need safe concurrency;
- multi-user saved queries, alerts or permissions need transactional server state;
- the SQLite snapshot/update model cannot meet freshness;
- indexed DB, rebuild, backup or deploy time exceeds the operating window;
- representative search/graph API p95 misses its target after indexing/query fixes;
- horizontal API replicas or row-level access controls are needed.

Postgres' native full text or `pg_trgm` should be tried before a separate search service. Add `pgvector` only when evaluated semantic retrieval materially improves recall over FTS and graph filters. Vectors are a retrieval index, not source evidence and not the graph.

## When a graph database earns its place
Do not begin with Neo4j or another graph store. Relational edge tables are simpler for evidence, corrections and temporal history. Reconsider a graph database only when benchmarked, product-critical traversals are regularly deeper or more path-heavy than bounded relational queries, the graph reaches tens of millions of edges, and those traversals remain the bottleneck after indexes/materialized neighbourhoods. If introduced, Postgres remains the system of record and the graph store is a rebuildable projection.

## Current measured baseline, 2026-09-12

- canonical database: 1.8 MB;
- 1,644 canonical documents, including 1,157 FERC records;
- only about 128 KB of canonical `content` today because FERC remains metadata-only;
- static search shard: 1.4 MB;
- raw FERC feed: 820 KB for 1,161 rows;
- 250 selected FERC first-transmittal PDFs total about 77.14 MiB by eLibrary file sizes; median 213,384 bytes, mean 323,552 bytes, maximum 2,555,250 bytes;
- all 1,161 currently listed first transmittals total about 0.767 GiB by eLibrary metadata. That is not every component and not a historical firehose estimate.

These measurements are too small to justify Postgres, pgvector or a graph database. The first firehose canary must measure bytes per component, pages, tokens, boxes, passages, FTS growth, extraction time and daily source volume before a backfill or hosting commitment.
