# Evidence-to-publication pipeline

## Flow
`new FERC filing -> nightly reconciled crawl -> immutable raw components -> clean/page extraction -> ML classification -> passage index -> graph update -> production filing/docket/timeline -> watches/alerts -> selected News/Latest analysis -> selected LinkedIn/X adaptation`

Each stage writes a versioned status and can fail without falsely promoting later stages. Last-good public outputs remain live. Raw/source and extraction stages are never overwritten by generated outputs.

## Surface policy

### Analyst surfaces
FERC filing, docket, timeline and Query use the analyst register. They show technical posture, exact identifiers, source/derived labels, unresolved points and claim-level passages. No jokes or catchy framing.

### News/Latest
A filing becomes a story only if it passes a recorded so-what gate: changed timeline, new money/cost allocation, project advancement/death, proposed/binding rule shift, or another concrete consequence. Use the news register: precise but accessible headline, verdict/dek, cited explanation, lifecycle context, limits and related reads.

A hero image must have rights/provenance, alt text and a real editorial purpose. Prefer source charts/maps/doc details or commissioned/generated visual explainers; never add a generic stock photo that implies a place/company/event not in evidence.

### LinkedIn and X
Only selected published News stories are candidates. Social copy is a shorter explanatory adaptation of the same approved evidence, links to the published analysis, and cannot introduce new claims. No automatic posting until the user reviews recipient/account and final words or grants exact standing auto-send scope. Brand accounts are separate from personal accounts.

## Promotion gates
1. Crawl page/component totals reconcile.
2. Source bytes checksum and extraction coverage pass.
3. Classifier schema/evidence gates pass; low confidence is review.
4. Graph edges carry evidence; chronology does not become causation.
5. Every generated claim resolves to a passage and passes surface-specific editorial checks.
6. Timeline event distinguishes filing, position, agency action and effective rule.
7. Alert deduplicates and records why it fired.
8. News/social so-what decision and evidence are stored.
9. Public links are checked after deployment.
