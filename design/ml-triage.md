# Filing classification and tagging system

## Goal
"Best in class" is a measured property, not a model name. The system must classify every document, show why and with what confidence, and prove each version is better on a fixed human-labelled regulatory set before promotion.

## Output contract
Each filing/component can emit independent predictions for:

- source document category: order, application, tariff, protest, comment, answer, intervention, notice, report, meeting material, minutes, presentation, vote/action, revision request, other;
- procedural versus substantive, with `mixed` and `unknown` allowed;
- topics: interconnection, large load/data centres, capacity/resource adequacy, transmission/planning, rates/tariffs, markets, reliability/operations, enforcement/compliance, certificates/siting, environmental, storage, governance;
- region and ISO/RTO;
- organizations, people, committees, projects/facilities, technologies and docket/initiative identifiers;
- stance or action only when the passage explicitly supports it.

A prediction stores value, confidence, supporting evidence IDs, tagger/version, observed time, review state and any human correction. Confidence is per prediction, not per document.

## Ensemble

### Layer 1: deterministic baseline
Use source metadata, docket mapping and high-precision textual rules. This is the floor and fallback. Rules are individually named and fixture-tested. They may abstain. A docket creates context but never a merits stance.

### Layer 2: local statistical models
Train/evaluate cheap CPU models where enough labels exist: sparse TF-IDF word/character features with calibrated logistic regression or linear SVM for multi-label topics and procedural/substantive class. Use dictionaries plus token/span models for entities. This layer is deterministic by artefact checksum, cheap to run corpus-wide and useful for comparison against the LLM.

### Layer 3: model-swappable structured-output tagger via OpenRouter
Send only the bounded filing metadata and selected full-text passages needed for classification. Require a strict JSON schema with per-label confidence, evidence passage IDs and abstention. Reject unknown labels, missing evidence, malformed output and claims unsupported by cited passages.

DeepSeek models can be evaluated through OpenRouter, but provider/model is a versioned setting and no model is the authority. Its predictions are candidates that must pass schema/evidence gates and the version's evaluated confidence thresholds. Paid calls are blocked until the key, current official pricing, projected per-filing cost and $5 hard-budget controls are in place.

### Resolution policy
- deterministic high-precision labels can be accepted directly;
- agreement among evaluated taggers can raise review priority, not invent evidence;
- disagreement or confidence below the label-specific threshold becomes `needs_review`;
- high-risk fields such as stance, ownership and `SAME_AS` require explicit passage support and stricter thresholds;
- human corrections override model output and remain first-class/versioned through rebuilds.

## Human-labelled evaluation set
Begin with a stratified set of 300-500 filings, not a random newest sample:

- all major FERC libraries/classes;
- procedural and substantive records;
- the 16 known large-load dockets plus unrelated electric, gas, hydro and enforcement examples;
- short and long filings, scanned/OCR and digital text;
- multi-component accessions;
- hard negatives that mention a term without being about it;
- related ISO/RTO meeting-document types when connectors arrive.

Two-pass labelling is preferred for ambiguous records. The label guide must define each class, overlap rules, unknown/mixed states and what passage proves the label. Store annotator, time, source checksum, evidence span and adjudication.

## Scorecard and promotion gate
For every tagger/version report per-label precision, recall and F1, micro/macro aggregates, support count, calibration/error curves, abstention/review rate, cost and latency. Stance/entity-linking also reports false-positive cases by severity. Split by source class, OCR/digital, document length and hot/non-hot dockets.

No tagger is promoted because aggregate F1 rises. Proposed initial gates, to be revised from baseline measurements:

- no material precision regression on any safety-critical label;
- substantive/procedural precision >= 0.97 on supported labels;
- filing category macro F1 >= 0.90 where label support is sufficient;
- high-risk relationship/stance precision >= 0.98, otherwise abstain;
- expected calibration error and review rate published with the scorecard;
- every production error added to the regression set.

Small-support labels are reported as insufficient evidence, not a flattering percentage.

## Versioning and audit
A tagger version identifies code commit, rules/model/prompt/schema checksum, training set version, evaluation set version and dependency versions. Every accepted/rejected prediction remains reconstructible. Re-scoring writes a new version; it does not overwrite the earlier decision. Promotion and rollback are explicit.

## Cost controls
Before any paid OpenRouter call, estimate uncached/cached input and maximum output tokens using current official prices. Maintain an append-only usage ledger by job, provider and model. Reserve projected cost atomically; refuse the job if it could cross the user's $5 lifetime ceiling. Set the OpenRouter key's own credit limit to the same ceiling so provider and application controls are independent. Reconcile reservation to provider-reported usage. Cache by source checksum + prompt/schema/version. Procedural templates and local models consume no API budget.
