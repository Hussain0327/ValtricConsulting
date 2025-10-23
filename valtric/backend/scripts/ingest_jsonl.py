"""Ingest JSONL-formatted documents via /foundry/ingest.

Each JSON line is expected to contain:

    {
        "deal_id": 1001,
        "source_name": "Q4_2024_Comps",
        "content": "...",
        "meta": { ... }
    }

The script will create a stub deal (name/industry inferred from meta) and
attach a single chunk per line. OpenAI embeddings are generated using
`text-embedding-3-small` by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx
from openai import OpenAI


DEFAULT_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")


def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def build_payload(record: dict[str, Any], client: OpenAI) -> dict[str, Any]:
    deal_id = record.get("deal_id")
    meta = record.get("meta") or {}
    sector = meta.get("sector", "General")
    region = meta.get("region", "Global")

    text = (record.get("content") or "").strip()
    if not text:
        raise ValueError("content is required on each JSONL line")

    embedding = client.embeddings.create(
        model=DEFAULT_MODEL,
        input=text,
    ).data[0].embedding

    deal_payload = {
        "name": f"Seed Deal {deal_id or 'N/A'} - {sector}",
        "industry": sector,
        "price": float(meta.get("price") or 5_000_000.0),
        "ebitda": float(meta.get("ebitda") or 500_000.0),
        "currency": meta.get("currency", "USD"),
        "description": f"Synthetic ingest derived from {record.get('source_name', 'seed.jsonl')} ({region}).",
    }

    document_payload = {
        "source_name": record.get("source_name", f"seed-{deal_id or 'unknown'}"),
        "mime_type": "text/plain",
        "chunks": [
            {
                "ord": 0,
                "text": text,
                "meta": meta,
                "hash": hash_text(text),
                "embedding_model": DEFAULT_MODEL,
                "embedding": embedding,
            }
        ],
    }

    return {"deal": deal_payload, "documents": [document_payload]}


def ingest(host: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{host.rstrip('/')}/foundry/ingest"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest JSONL documents into Foundry")
    parser.add_argument("jsonl", type=Path, help="Path to JSONL file (one record per line)")
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="FastAPI host (default: %(default)s)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Embedding model (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true", help="Print payload summaries without POSTing")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY must be set before running this script.")

    client = OpenAI(api_key=api_key)

    ingested = 0
    with args.jsonl.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            payload = build_payload(record, client)
            if args.dry_run:
                print(json.dumps(payload, indent=2)[:400] + "...\n")
                continue
            result = ingest(args.host, payload)
            ingested += 1
            print(
                f"Ingested deal {result['deal_id']} -> documents={result['documents_ingested']} "
                f"chunks={result['chunks_ingested']} embeddings={result['embeddings_ingested']}"
            )

    if args.dry_run:
        print("Dry run complete; no API calls made.")
    else:
        print(f"Completed ingest for {ingested} records from {args.jsonl}.")


if __name__ == "__main__":
    main()
