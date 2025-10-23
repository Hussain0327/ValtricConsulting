# Validation & Test Playbook

This playbook summarizes how to exercise the Valtric valuation stack end-to-end. Use it alongside automated tests before promoting changes to staging or production.

## 1. Unit & Contract Tests
Run locally with `pytest` from `backend/`:

| Test File | Coverage |
|-----------|----------|
| `tests/test_consultant.py` | Sanitizer guardrails, cache behaviour, `_should_escalate` logic. |
| `tests/test_foundry_ingest.py` | Ingest payload validation, Supabase bulk-upsert wiring. |
| `tests/test_retrieve.py` | Embedding fallbacks, Supabase retrieval, rerank ordering. |

### Commands
```bash
cd ~/Downloads/ValtricConsulting/valtric/backend
source .venv/bin/activate
pytest
```

## 2. Structured Golden Harness
The evaluation harness exercises curated prompts and validates the strict JSON contract.

1. Populate `eval/prompts.jsonl` with the scenarios you want to validate (baseline freeze, FX, multi-year, etc.).
2. Run:
   ```bash
   cd backend
   source .venv/bin/activate
   python -m scripts.run_eval --prompts ../eval/prompts.jsonl
   ```
3. The script spins up uvicorn in-process, issues each prompt, and prints a pass/fail matrix with failure details.

## 3. Scenario Walkthroughs
Manual scenarios help validate log fields and Supabase wiring.

1. **FX Stress**  
   - Ingest 3–4 EU SaaS comps (via `scripts/seed_foundry.py` or `/foundry/ingest`).  
   - Call `/analyze` with an FX-focused question.  
   - Expect `supabase_vector_search hits>0`, `cited_comps>=1`, and risk flags referencing FX.

2. **Multi-Year Modelling**  
   - Prompt for 2025–2027 projections.  
   - Check logs: `analysis_sanitized` should show `retrieval_required=True`, `cited_comps>=1`, and confidence ≥ configured threshold.  
   - Ensure `_should_escalate` triggered GPT‑5 when confidence fell below 0.55.

3. **No Evidence**  
   - Ask a basic question without comparative language.  
   - Expect `comps_used=[]`, `risk_flags` including `no_citable_evidence`, and confidence ≤ 0.5.

4. **Failure Injection**  
   - Temporarily revoke Supabase credentials or patch `_supabase_vector_search` to raise.  
   - Confirm fallback logs (`supabase_vector_search_failed`) and graceful baseline output.

## 4. Load & Latency
Use an async driver or locust to simulate realistic traffic (70% easy, 20% hard, 10% ingest). Capture:

| Metric | Source |
|--------|--------|
| P95 latency by request type | `analysis_sanitized` log + client timers |
| Cache hit rate | Add logging around `analyses_cache.get` |
| Supabase RPC latency | Wrap `_supabase_vector_search` with structured timing logs |

Sample async load driver skeleton (`scripts/load_test.py`):
```python
# Add commands to generate mixed traffic profiles and report latencies.
```

## 5. Observability Guardrails
Log fields already added in `analysis_sanitized`:
- `retrieval_required`
- `retrieval_hits`
- `cited_comps`
- `baseline_freeze`
- `confidence`

Add temporary assertions during testing:
```python
if retrieval_required and retrieval_hits > 0 and not cited_comps:
    raise RuntimeError("Retrieval produced hits but no citations.")
```

## 6. Manual QA (once Frontend is ready)
- Ingest docs through the UI and confirm status, evidence cards, and risk flags match API output.
- Spot-check Supabase tables (documents/chunks/embeddings) for newly ingested IDs that correspond to cited `chunk:*` identifiers.

## 7. Security Checklist
- `bandit -r backend` and `pip-audit` to catch Python vulnerabilities.
- Ensure `.env`/keys are excluded from VCS (`.gitignore`) and document rotation steps in the runbook.
- Verify secrets are injected via environment variables in staging/production (no hard-coded keys).

## 8. Deployment Readiness
Before promoting builds:
1. Run unit tests + structured harness.
2. Execute scenario walkthroughs with Supabase online.
3. Capture load-test summary (latency targets met).
4. Review logs for warnings/errors.
5. Update changelog and handoff notes.

Following this playbook gives confidence the agent honours the schema, cites evidence correctly, and degrades gracefully when retrieval or LLM providers misbehave.
