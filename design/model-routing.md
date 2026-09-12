# Model routing and budget contract

## Rule
Use the cheapest open-weight model that passes the evaluation gate for the specific stage. Triage, summary and `Tell me more` are separate tasks and may graduate different models. Price, popularity or one aggregate benchmark never selects a production model.

## Provider boundary
OpenRouter is the current gateway. Provider and model IDs remain versioned job settings. Structured schemas, evidence contracts, evals and stored outputs stay provider-neutral. A model can be removed or replaced without changing document/evidence identity.

## Stage bake-offs

### Classification/tagging
Inputs: bounded metadata and evidence passages. Output: strict controlled-schema predictions with per-label confidence, evidence IDs and abstention. Score per-label precision/recall/F1, calibration, schema validity, unsupported-label rate, cost and latency.

### Filing/meeting summary
Inputs: selected evidence passages and metadata, never an unconstrained whole corpus. Apply the tracker editorial contract. Score claim support, claim citation coverage, attribution/holding distinction, numeric/temporal fidelity, useful compression, style violations, cost and latency.

### Tell me more
Inputs: selected evidence, surrounding context and explicitly retrieved graph-linked passages. Score answer support/completeness, current-document versus wider-corpus separation, relationship provenance, no-answer behavior, retrieval contribution, cost and latency.

## Graduation
1. Freeze labelled/judged development and holdout sets.
2. Run deterministic/local baselines first.
3. Run candidates with identical input/evidence budgets and strict maximum output.
4. Reject malformed, uncited or unsupported responses before quality scoring.
5. For every model that passes the task's quality/safety floors, compare expected and observed cost.
6. Graduate the cheapest passing model. Keep the next passing model as a bounded fallback only when retry policy and budget permit.
7. Record model/provider version, route, prompt/schema, prices, evaluation set and scorecard.
8. Any upgrade must re-score the frozen holdout and production regression set.

## $5 hard ceiling
The OpenRouter key has a provider-side $5 limit. The application also maintains its own append-only ledger.

Before a job:
- fetch/snapshot current model pricing;
- estimate uncached/cached input and max output tokens;
- atomically reserve worst-case cost;
- refuse if lifetime reconciled usage + active reservations + proposed reserve exceeds $5;
- cap provider generation tokens.

After a job:
- record provider request/generation ID, model route, token counts and reported charge;
- reconcile and release unused reservation;
- cache output by source/evidence + task + prompt/schema/model version;
- expose lifetime spend, reservations and remaining headroom.

Do not rely on account balance as a batch scheduler. Provider price changes, retries and routing fallbacks can change cost.

## Current observed OpenRouter rates
Observed from authenticated `/api/v1/models` on 2026-09-12; refresh before use:

- `deepseek/deepseek-v4.1-flash`: $0.15/M prompt, $0.60/M completion, $0.003/M cache read.
- `deepseek/deepseek-v3.2`: $0.269/M prompt, $0.40/M completion, $0.1345/M cache read.
- `deepseek/deepseek-r1-0528`: $0.50/M prompt, $2.15/M completion, $0.35/M cache read.

Temporal/provider overrides can apply. These rates are evidence for estimates, not permanent configuration.

## Editorial prompt dependency
Every summary, article and alert-brief candidate is wrapped with `prompts/editorial-contract.md`, derived from `design/tracker-editorial-skill.md`. Editorial style never overrides evidence scope or strict structured output. Style violations and allegation/holding errors are separate eval dimensions.
