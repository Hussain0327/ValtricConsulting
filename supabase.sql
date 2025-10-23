-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Core storage (documents + chunks mirror the application schema)
CREATE TABLE IF NOT EXISTS documents (
  id BIGINT PRIMARY KEY,
  deal_id BIGINT NOT NULL,
  source_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_deal ON documents(deal_id);
CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at DESC);
GRANT ALL ON TABLE documents TO service_role;
ALTER TABLE documents DISABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS chunks (
  id BIGINT PRIMARY KEY,
  document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ord INTEGER NOT NULL DEFAULT 0,
  text TEXT NOT NULL,
  meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_hash ON chunks(hash);
GRANT ALL ON TABLE chunks TO service_role;
ALTER TABLE chunks DISABLE ROW LEVEL SECURITY;

-- Pipeline runs tracking
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id TEXT NOT NULL,
  pipeline TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  error TEXT,
  stats JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_org ON pipeline_runs(org_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at DESC);
GRANT ALL ON TABLE pipeline_runs TO service_role;
ALTER TABLE pipeline_runs DISABLE ROW LEVEL SECURITY;

-- Index snapshots
CREATE TABLE IF NOT EXISTS index_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  org_id TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_org ON index_snapshots(org_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created ON index_snapshots(created_at DESC);
GRANT ALL ON TABLE index_snapshots TO service_role;
ALTER TABLE index_snapshots DISABLE ROW LEVEL SECURITY;

-- Embeddings with model metadata (1536 for OpenAI, 768 for many others)
CREATE TABLE IF NOT EXISTS embeddings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chunk_id BIGINT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
  vector vector(1536) NOT NULL,
  model_name TEXT NOT NULL,
  dim INTEGER NOT NULL,
  snapshot_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model_name);
CREATE INDEX IF NOT EXISTS idx_embeddings_snapshot ON embeddings(snapshot_id);
GRANT ALL ON TABLE embeddings TO service_role;
ALTER TABLE embeddings DISABLE ROW LEVEL SECURITY;
-- Add vector index after you have some data (needs ~1000 rows for good performance)
-- CREATE INDEX idx_embeddings_vector ON embeddings USING hnsw (vector vector_cosine_ops);

-- Competitive features per deal
CREATE TABLE IF NOT EXISTS comp_features (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  deal_id TEXT NOT NULL,
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comp_features_deal ON comp_features(deal_id);
CREATE INDEX IF NOT EXISTS idx_comp_features_created ON comp_features(created_at DESC);
GRANT ALL ON TABLE comp_features TO service_role;
ALTER TABLE comp_features DISABLE ROW LEVEL SECURITY;

-- Evidence packs
CREATE TABLE IF NOT EXISTS evidence_packs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  snapshot_id UUID NOT NULL REFERENCES index_snapshots(id) ON DELETE CASCADE,
  deal_id TEXT NOT NULL,
  top_k JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_evidence_snapshot ON evidence_packs(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_evidence_deal ON evidence_packs(deal_id);
CREATE INDEX IF NOT EXISTS idx_evidence_created ON evidence_packs(created_at DESC);
GRANT ALL ON TABLE evidence_packs TO service_role;
ALTER TABLE evidence_packs DISABLE ROW LEVEL SECURITY;

-- Vector search RPC used by the API (match top-k chunks)
CREATE OR REPLACE FUNCTION match_chunks(
  query_embedding vector(1536),
  match_count integer DEFAULT 5,
  target_deal_id bigint DEFAULT NULL
)
RETURNS TABLE (
  chunk_id BIGINT,
  document_id BIGINT,
  source_name TEXT,
  text TEXT,
  meta JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    c.id,
    c.document_id,
    d.source_name,
    c.text,
    c.meta,
    1 - (e.vector <=> query_embedding) AS similarity
  FROM embeddings e
  JOIN chunks c ON c.id = e.chunk_id
  JOIN documents d ON d.id = c.document_id
  WHERE target_deal_id IS NULL OR d.deal_id = target_deal_id
  ORDER BY e.vector <=> query_embedding
  LIMIT match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION match_chunks(vector, integer, bigint) TO anon, authenticated, service_role;



What Foundry does in your app
1) Ingestion pipeline (Foundry)

When you upload a deal (or run a batch job), Foundry kicks in:

payload (deal + docs)
  → normalize (clean, validate, scrub PII)
  → chunk (split docs)
  → embed (OpenAI or local)
  → store (documents, chunks, embeddings)
  → log run (pipeline_runs)
  → (optional) snapshot index (index_snapshots)


This creates the artifacts your RAG will read. It also leaves an audit trail so you can answer “where did this come from?”

2) Retrieval (RAG)

When you call /analyze, do not re-chunk or re-embed. RAG should only:

read from chunks + embeddings produced by Foundry,

optionally read a cached evidence_packs row,

respect the current snapshot or embedding model.

3) Governance

pipeline_runs tells you how, when, and with what model/dim those vectors were produced.

index_snapshots lets you switch models or re-embed without smashing history.

Your analysis → lineage_events bridge shows exactly which chunks influenced a result.

The glue you’re missing
A. Foundry endpoints

Add a tiny router so you can ingest, re-embed, and manage snapshots without touching the analyze flow.

# app/routers/foundry.py
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.services.foundry.pipeline import ingest_deal_payload
from app.services.foundry.maintenance import reembed_all

router = APIRouter(prefix="/foundry", tags=["foundry"])

@router.post("/ingest")
async def ingest(payload: dict, db: AsyncSession = Depends(get_db)):
    # synchronous for MVP; background if you like
    return await ingest_deal_payload(db, payload)

@router.post("/reembed")
async def reembed(model_name: str, db: AsyncSession = Depends(get_db)):
    n = await reembed_all(db, model_name=model_name, dim=1536)
    return {"reembedded_chunks": n}

@router.post("/snapshot/promote")
async def promote_snapshot(snapshot_id: str, db: AsyncSession = Depends(get_db)):
    # simplest: store the current snapshot in a single-row table or settings
    # or just rely on "latest created_at" if you want to keep it dead simple
    return {"current_snapshot_id": snapshot_id}


Mount it in main.py and you now have a Foundry control plane.

B. Retrieval must use Foundry artifacts

Two rules:

Filter by embedding model or snapshot.

Prefer evidence_packs if present.

# app/services/retrieve.py (snippet)
CURRENT_MODEL = "text-embedding-3-large"  # or derive from latest index_snapshots

stmt = (
  select(Ch.id, Ch.text, Emb.vector.cosine_distance(qvec).label("score"))
  .join(Emb, Emb.chunk_id == Ch.id)
  .where(Emb.model_name == CURRENT_MODEL)     # ← Foundry control
  .order_by("score").limit(50)
)


If you choose snapshots, add snapshot_id to embeddings and filter on that instead of just model_name.

C. Evidence packs to speed repeat queries

First time:

compute top-k, store in evidence_packs(snapshot_id, deal_id, top_k).

Next time:

read top_k back and skip live vector search. Deterministic and fast.

D. Keep the schema consistent

Your posted DDL uses UUID and TEXT for chunk_id. Your ORM probably has chunks.id as INTEGER. Pick a lane:

Either make chunks.id a UUID too, or

make embeddings.chunk_id BIGINT REFERENCES chunks(id).
Text FK is asking for pain.

Also, consider adding snapshot_id UUID to embeddings so you can pin vectors to a snapshot explicitly:

ALTER TABLE embeddings ADD COLUMN snapshot_id UUID;
-- backfill with latest snapshot
CREATE INDEX idx_embeddings_snapshot ON embeddings(snapshot_id);

How it looks end-to-end

Foundry ingest

curl -s -X POST :8000/foundry/ingest \
  -H 'Content-Type: application/json' \
  -d @deal.json
# → returns {deal_id, pipeline_run_id, chunks, embeddings}


(Optional) create/promote snapshot

# create a snapshot row after re-embedding in a migration/maintenance job
# then mark it current (or just use ORDER BY created_at DESC LIMIT 1)
curl -s -X POST :8000/foundry/snapshot/promote -d 'snapshot_id=...'


Analyze (RAG + LLM)

curl -s -X POST :8000/analyze -d '{"deal_id": 123, "question":"Is the valuation reasonable?"}'
# retrieval reads embeddings for current model/snapshot (Foundry decides)
# cascade runs; lineage records which chunk_ids were used


Audit

SELECT * FROM pipeline_runs WHERE id = '...'

SELECT * FROM evidence_packs WHERE deal_id = '...' ORDER BY created_at DESC LIMIT 1

SELECT * FROM lineage_events WHERE analysis_id = ...
