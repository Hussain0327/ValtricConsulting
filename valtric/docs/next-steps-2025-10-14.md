# Supabase Integration Checklist

Work through these steps locally (not in the sandbox) so the new Supabase-backed retrieval pipeline comes alive. When you’re finished, feel free to delete the contents of this file and reuse it for the next work session.

## 1. Apply `supabase.sql`
- Open the Supabase dashboard → SQL Editor.
- Paste the contents of `supabase.sql` from the repo and run it.
  - This creates `documents`, `chunks`, `embeddings`, supporting tables, and the `match_chunks` RPC.
  - Verify `embeddings.chunk_id` is `BIGINT` so it matches your API database IDs.

## 2. Backfill existing data
```bash
cd ~/Downloads/ValtricConsulting/valtric/backend
source .venv/bin/activate
python scripts/sync_supabase.py
```
- The script reads your local Postgres `documents/chunks/embeddings` and upserts them into Supabase using the service-role key in `.env`.
- If the script complains about missing env vars, double-check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

## 3. Ingest a sample payload
- Craft a JSON payload with the shape expected by `/foundry/ingest`:
  ```json
  {
    "deal": {
      "name": "Sample Deal",
      "industry": "SaaS",
      "price": 1250000,
      "ebitda": 200000,
      "currency": "USD"
    },
    "documents": [
      {
        "source_name": "teaser.pdf",
        "mime_type": "application/pdf",
        "chunks": [
          {
            "ord": 0,
            "text": "First chunk text...",
            "meta": {"section": "summary"},
            "hash": "optional-hash",
            "embedding_model": "text-embedding-3-large",
            "embedding": [0.01, 0.02, ...]  // 1536 floats
          }
        ]
      }
    ]
  }
  ```
- Send it (in a second terminal while uvicorn is running):
  ```bash
  curl -X POST http://127.0.0.1:8000/foundry/ingest \
    -H "Content-Type: application/json" \
    -d @payload.json
  ```
- Confirm the response shows counts for `documents_ingested`, `chunks_ingested`, `embeddings_ingested`.
- Check Supabase tables (Table Editor → public → documents/chunks/embeddings) to ensure the new rows exist with matching IDs.

## 4. Test `/analyze`
- With data synced, run:
  ```bash
  curl -s -X POST http://127.0.0.1:8000/analyze \
    -H "Content-Type: application/json" \
    -d '{"deal_id": 1, "question": "Compare the SaaS deal with our manufacturing targets and highlight FX risks."}'
  ```
- In the uvicorn console you should now see:
  - `analysis_classification complexity=...`
  - `supabase_vector_search` log (no fallback warnings).
  - Rerank timings when Cohere/BGE is configured.
- Inspect the JSON response; `comps_used` and `reasoning` should reference the retrieved chunks.

## 5. Follow-up
- Rotate the Supabase service-role key if you ever suspect it leaked; update `.env` locally only (never commit it).
- Add tests that mock Supabase responses so you can validate retrieval without hitting the network.
- Expand the ingest pipeline to log `pipeline_runs`, `index_snapshots`, and cache evidence packs once your Foundry flow supports them.
