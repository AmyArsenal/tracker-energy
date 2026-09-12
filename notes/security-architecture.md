# Security & scalability architecture (Sep 10, 2026) — pre-seed plan

Amit's constraint (verbatim concern): scalable, secure, client logins,
payments, "no AI agents can hack us". This is the concrete plan for the
server/MCP phase. Today's static site holds only PUBLIC regulatory data and
no user data, so current exposure is minimal; everything below lands with
accounts, alerts, payments, and the MCP connector.

## 1. Managed auth (no passwords we own)
Recommendation: Supabase Auth (free to 50k MAU, same trust boundary as the
Postgres below) OR Clerk (best B2B org/SSO story, ~$0.02/MAU). Either way:
managed MFA, magic links + OAuth, session handling, no credential storage on
our side. B2B SSO (SAML) is an enterprise-tier feature on both — plan it as
the paid-team milestone, not day one.
Sources: apiscout.dev/guides/clerk-vs-auth0-vs-supabase-auth-2026,
designkey.studio/post/saas-auth-comparison-clerk-vs-auth0-vs-supabase

## 2. Payments — cards never touch our servers
Stripe Checkout + Customer Portal: card data enters Stripe's fields only
(SAQ-A scope for us), we store only the Stripe customer/subscription IDs.
Webhooks (signed) drive entitlement flips. No PAN ever logged or stored.

## 3. Tenant isolation — Postgres row-level security
Shared schema, every tenant-owned row carries tenant_id, RLS policies enforce
isolation inside the database engine itself (not in app code). App-level
scoping stays as defense in depth, plus migration tests that prove
cross-tenant reads fail. Watchlists and alert configs are MARKET-SENSITIVE
(they reveal what a competitor is researching) — isolation is a sales
feature, not just hygiene.
Sources: aws.amazon.com/blogs/database/multi-tenant-data-isolation-with-postgresql-row-level-security,
docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-managed-postgresql/rls.html,
makerkit.dev/blog/tutorials/multi-tenant-saas-architecture

## 4. Prompt-injection defenses for the ingestion pipeline
Threat model: filings/meeting pages are UNTRUSTED input (OWASP LLM01:2025/2026
- indirect prompt injection via retrieved documents is the prime RAG-pipeline
attack). Design rules (already partly live):
- Ingestion/summarization agents READ and CITE only: no tools, no network,
  no side effects. The only outputs are text + citation records.
- Citation validation gate before publish (live tonight):
  validate_articles.py structural checks (annolink<->annotation consistency,
  page/rect bounds); the support check ("does the passage back the claim") is
  part of the nightly writing rules.
- Provenance allowlist: fetch only from known venues (FERC eLibrary, PJM,
  CAISO, ERCOT, state commissions); every document keeps source URL +
  fetched_at; hosted PDFs are byte-verified copies.
- Corpus is public data, so the realistic risk is INTEGRITY (poisoned text
  skewing analysis), not confidentiality — countered by provenance +
  citations a reviewer can spot-check + validation errors blocking publish.
Sources: cheatsheetseries.owasp.org (LLM Prompt Injection Prevention),
github.com/GenAI-Security-Project/GenAI-LLM-Top10 (2026/LLM01),
safeprompt.dev/blog/indirect-prompt-injection

## 5. MCP / connector phase
Read-only tools at launch (search_corpus, get_document, get_citations,
list_watchlist_digests). OAuth 2.1 + PKCE for client auth, tool-scoped
permissions, per-client rate limits, full audit logging, and treat every
agent client as a confused deputy: the server never lets a tool result
re-enter as instructions. No write tools until there is an explicit
authorization model.
Sources: apiscout.dev/guides/anthropic-mcp-server-security-2026,
verifymcp.io/blog/mcp-security-best-practices,
exploreagentic.ai/insights/mcp-server-security-hardening

## 6. Scalability path
Now: static site on edge CDN (surge), 449KB search shard, 580 docs.
Next: shard stays client-side to ~25-50k docs; past that the same canonical
records push to a server-side search index (the builder is already written
against that boundary). Accounts/alerts/payments land on
Supabase(Postgres+RLS) or Clerk+Stripe as above. The validated corpus +
taxonomy + annotations are the asset; every surface (site, MCP, API) reads
the same store.
