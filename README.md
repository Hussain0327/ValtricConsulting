````
valtric/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI init + router mounts + CORS + SSE
│   │   ├── settings.py          # Pydantic settings
│   │   ├── db.py                # Postgres + pgvector init
│   │   ├── schemas.py           # Pydantic I/O models
│   │   ├── routers/
│   │   │   ├── health.py        # /health
│   │   │   ├── deals.py         # POST /deals (JSON only), GET /deals/:id
│   │   │   └── analyze.py       # POST /analyze, GET /analyses/:id, SSE /stream
│   │   ├── services/
│   │   │   ├── chunk.py         # dumb chunking rules
│   │   │   ├── embed.py         # embed(text[]) -> vectors
│   │   │   ├── retrieve.py      # vector search + optional keyword filter
│   │   │   └── consultant.py    # calls LLM; packs context; returns JSON
│   │   ├── rag/
│   │   │   ├── rerank.py        # optional cross-encoder; stub first
│   │   │   └── pack.py          # token budgeting + citations
│   │   └── utils/
│   │       ├── logging.py       # json logs + request ids
│   │       └── ids.py
│   ├── migrations/              # Alembic (single initial migration)
│   ├── scripts/
│   │   └── seed.py              # load a few example deals
│   ├── tests/
│   │   └── test_smoke.py
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── docker-compose.yml       # postgres + pgvector
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.tsx
│   │   │   ├── DealUpload.tsx
│   │   │   └── AnalysisCard.tsx
│   │   ├── lib/
│   │   │   ├── api.ts           # fetch wrappers
│   │   │   └── sse.ts           # EventSource helper
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # list deals + analyses
│   │   │   └── Deal.tsx         # upload + run analysis + show output
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── shadcn.config.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── index.html               # if Vite; if Next, swap to /app router
│
├── eval/
│   ├── golden.jsonl             # 10 tiny cases w/ expected ranges
│   └── run_eval.md
│
├── docs/
│   ├── architecture.md          # 1 page, not a novel
│   └── demo_script.md           # the exact clicks you’ll show
├── .gitignore
├── README.md
└── LICENSE
valtric/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── settings.py
│   │   ├── db.py
│   │   ├── schemas.py
│   │   ├── routers/
│   │   │   ├── health.py
│   │   │   ├── deals.py          # POST /deals, GET /deals/:id
│   │   │   └── analyze.py        # POST /analyze, GET /analyses/:id, SSE /stream/:id
│   │   ├── services/
│   │   │   ├── chunk.py
│   │   │   ├── embed.py
│   │   │   ├── retrieve.py       # hybrid search
│   │   │   ├── rerank.py         # optional cross-encoder
│   │   │   └── consultant.py     # packs context, calls LLM, returns JSON
│   │   └── utils/
│   │       ├── logging.py
│   │       └── security.py       # simple PII scrubber
│   ├── migrations/
│   ├── tests/
│   ├── docker-compose.yml        # postgres + pgvector
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.tsx
│   │   │   ├── DealUpload.tsx
│   │   │   └── AnalysisCard.tsx
│   │   ├── lib/{api.ts,sse.ts}
│   │   ├── pages/{Dashboard.tsx,Deal.tsx}
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── package.json
├── eval/golden.jsonl
├── docs/{architecture.md,demo_script.md}
└── README.md



Recall: pgvector cosine, K=50, filter by industry and revenue range if provided.

Hybrid: add tsvector for BM25-style text search; union with embeddings; score blend.

Rerank: plug a cross-encoder (bge-reranker or hosted) to pick top 10. Quality jumps.
The “consultant” contract (keep it strict)

Ask your model to output this JSON. If it deviates, reject and retry with a terse system reminder.

{
  "conclusion": "fair / rich / cheap",
  "implied_multiple": 11.2,
  "range": [10.5, 12.0],
  "reasoning": "2–3 sentences, cite comps by id",
  "comps_used": ["chunk:doc123#7", "chunk:doc987#2"],
  "risk_flags": ["customer concentration", "declining gross margin"],
  "confidence": 0.74
}
Governance without pain

Lineage: store the chunk IDs and scores you fed the model. Show citations in UI.

Audit: log prompt, model, latency, token counts, and cost per analysis as JSON.

Multi-tenant: every table gets org_id. Use RLS if you go Supabase; otherwise enforce in queries.

codex resume 0199dfcc-bdff-7683-81de-a87e4c25adc5

````
