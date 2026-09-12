# Halcyon public-stack lessons

Primary reference: https://halcyon.io/blog/machine-readable/building-the-stack, observed 2026-09-12. These are competitor-reported architecture statements, not independently verified implementation facts.

## Match
- Complete acquisition comes before relevance selection.
- Preserve source-native metadata, then map it into controlled cross-source docket, filing-type and topic concepts.
- Apply hard metadata constraints before fuzzy retrieval.
- Keep lexical and semantic retrieval complementary; embeddings never replace filters.
- Make document and embedding metadata incrementally rebuildable.
- Model alerts as reusable window + filter + query specifications with idempotent consumers.
- Support typed structured query outputs, not only prose.

## Differentiate
- Evidence position and citation validation are ingestion contracts, not answer decoration.
- Publish connector-level completeness/reconciliation and extraction/citation health.
- Infer missing FERC/ISO filing types from full text only through evaluated, evidence-backed taggers with abstention.
- Build passage-backed graph edges for companies, people, committees, proceedings, projects, revisions and decisions, not only authorship authority.
- Keep party position, allegation, staff action, vote and final order distinct.
- Put the cited reader at the center of the workflow; graph paths choose relevant sources but passages prove answers.

## Architecture implication
The existing FERC engine's relational metadata and FTS layer stays correct. Semantic retrieval is a challenger added only after the labelled retrieval/evaluation set exists. Alert state should later use normalized `window_spec`, `filter_spec`, `query_spec`, `consumer`, version and run tables so docket grouping, custom prompts and typed subscription cells share one execution primitive.
