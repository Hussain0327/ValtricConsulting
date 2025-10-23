# MVP Readiness Checklist

This document captures the remaining work required before the Valtric Consulting platform can be considered MVP-ready. The goal is to move from the current internal alpha to a deployable product with guardrails, observability, and a basic user experience.

## 1. Test Coverage
- **Unit Tests:** build minimal coverage for key services (`foundry` ingest pipeline, Supabase integration client, staged consultant logic, retrieval fallback).
- **Integration Tests:** mock OpenAI/DeepSeek/Cohere/Supabase to validate end-to-end flows without hitting live services.
- **Smoke Tests:** add `/health`, `/foundry/ingest`, `/analyze` scenarios to ensure routing and DB access stay healthy.
- **CI Harness:** wire tests into a GitHub Actions workflow (or equivalent) with linting, type checks, and secrets scanning.

## 2. Accuracy & Retrieval Quality
- **Supabase chunk validation:** confirm each chunk includes meaningful metadata (source names, sections, currency tags).
- **DeepSeek escalation tuning:** log raw DeepSeek JSON, then refine `_should_escalate` thresholds so GPT-5 triggers only when confidence/comps are thin.
- **Evidence formatting:** ensure `comps_used` references actual Supabase chunks (e.g., `chunk:<id>#<ord>`), not file placeholders like `"Example SaaS Deal"`.
- **Incremental enrichment:** add evidence caching (`evidence_packs`) to reuse high-signal chunks and avoid redundant Supabase calls.

## 3. Observability & Governance
- **Pipeline runs:** record each ingest in `pipeline_runs` with model name, dim, stats, and status.
- **Index snapshots:** log embedding snapshots (`index_snapshots`) whenever models or dims change.
- **Lineage events:** populate `lineage_events` when responding to `/analyze` so responses can cite specific chunks.
- **Structured logging:** standardize log format (JSON) with request IDs, model latencies, and Supabase timings; add log aggregation strategy.
- **Alerting:** set up baseline monitoring (Supabase availability, DB connection health, LLM error rates).

## 4. Frontend Experience
- **Foundry UI:** implement upload workflows, ingest status indicators, and error handling.
- **Analysis dashboard:** list recent deals, show cached analyses, surface retrieved evidence, and highlight risk flags.
- **Streaming UX:** surface analysis progress (DeepSeek vs GPT-5) so users aren’t staring at a blank page for 30+ seconds.
- **Authentication hook:** stub entry points for user auth/tenant selection to align with backend validation.

## 5. Validation & Security
- **Input validation:** enforce schema checks on `/foundry/ingest` (chunk length, embedding dimension, MIME allowances) and `/analyze` payloads.
- **Rate limiting / quotas:** add guardrails to prevent LLM abuse, with per-org quotas or API keys.
- **Tenancy controls:** enforce `org_id` filtering, RLS policies (if staying on Supabase), or middleware checks before exposing multi-tenant data.
- **Secrets hygiene:** pull API keys from environment/secret store; scrub `.env` of live keys before committing.
- **Error handling:** return structured error responses (HTTP 4xx/5xx) with user-friendly messages; log stack traces server-side only.

## 6. Deployment & Runbooks
- **Environment parity:** define dev/staging/prod `.env` templates with placeholders for LLM/Supabase keys.
- **Dockerization:** build images for backend + frontend; define docker-compose for local dev and Kubernetes/Render setup for staging/prod.
- **Runbook:** document start/stop scripts, database migrations, Supabase schema updates, and key rotation.
- **Backup strategy:** ensure Supabase data and Postgres have a backup policy (daily snapshots, retention window).
- **Incident response:** outline procedures for LLM outages, Supabase downtime, or data ingestion failures.

## 7. Performance Targets
- **Latency goals:** enforce <5s for simple queries, <15s for complex queries (with configuration to allow longer “deep dive” runs).
- **Caching strategy:** verify TTL cache hit rates, consider Redis/memcached for multi-process caching.
- **Timeouts:** guard external calls (`httpx` clients) with sensible timeouts/retries; surface warnings when GPT-5 >30s.
- **Supabase indexing:** create HNSW index on `embeddings.vector` and monitor query latency; consider HNSW tuning if dataset grows.

## 8. Documentation & Onboarding
- **Developer docs:** update README/runbooks to include setup (Supabase SQL, seed scripts, model provider configuration).
- **API docs:** publish OpenAPI or Markdown with `/foundry/ingest`, `/analyze`, `/deals` contracts and sample payloads.
- **Data governance:** explain how ingestion data flows into Supabase and how pipeline runs/lineage provide traceability.
- **Security posture:** note where keys should live, how to rotate them, and what auditing is available.

## 9. Optional Extensions Before MVP
- **Model routing UI controls:** allow users to toggle “deep analysis” vs “fast heuristic”.
- **Supabase -> pgvector sync automation:** jobs that keep both data stores aligned as ingestion scales.
- **Cost tracking:** log token usage for GPT-5/DeepSeek to estimate spend per analysis.
- **Feature flags:** enable/disable GPT-5, DeepSeek, or caching dynamically without redeploying.

Delivering on the items above will convert the current functional prototype into a stable, observable MVP ready for external users. Prioritize test coverage, retrieval accuracy, and frontend UX first; then layer in observability, validation, and deployment readiness.

# codex resume 0199f3a5-7d75-7133-af79-9b6d64d237a3