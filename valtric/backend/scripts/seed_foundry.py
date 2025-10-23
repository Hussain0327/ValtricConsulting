"""Seed the Foundry ingest endpoint with realistic deal documents.

Usage
-----

    export OPENAI_API_KEY=sk-...
    source .venv/bin/activate
    python scripts/seed_foundry.py --host http://127.0.0.1:8000

The script will call /foundry/ingest for each payload defined below. It is an
idempotent helper intended for local development. Supabase + Postgres must be
running and uvicorn must be serving the API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from typing import Any, Iterable

import httpx
from openai import OpenAI


EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

SEED_DATA: list[dict[str, Any]] = [
    {
        "deal": {
            "name": "NimbusHR Series B",
            "industry": "SaaS",
            "price": 54000000,
            "ebitda": 3500000,
            "currency": "USD",
            "description": (
                "NimbusHR provides mid-market HRIS and payroll. Investors are assessing "
                "growth sustainability and FX exposure from its new UK subsidiary."
            ),
        },
        "documents": [
            {
                "source_name": "nimbushr-financial-overview.md",
                "mime_type": "text/markdown",
                "chunks": [
                    {
                        "text": (
                            "FY24 revenue reached $27.3M, up 42% YoY, driven by 118% net revenue "
                            "retention. Gross margin improved to 71%. Adjusted EBITDA margin sits at "
                            "6.5% as NimbusHR keeps reinvesting in product-led growth. Churn remains "
                            "under 4% annually."
                        ),
                        "meta": {"section": "Financial snapshot"},
                    },
                    {
                        "text": (
                            "Customer base is 1,180 midsize employers (median 310 employees). Average "
                            "contract value is $23k ARR with 2.6x attach on payroll modules. Top 10 "
                            "customers contribute 9% of ARR, reducing concentration risk."
                        ),
                        "meta": {"section": "Customer metrics"},
                    },
                    {
                        "text": (
                            "Comparable public SaaS payroll comps (Paycor, Paylocity, Dayforce) trade "
                            "at 6.5x to 8.2x forward revenue with EBITDA multiples between 28x and 35x."
                        ),
                        "meta": {"section": "Market multiples"},
                    },
                ],
            },
            {
                "source_name": "nimbushr-fx-memo.txt",
                "mime_type": "text/plain",
                "chunks": [
                    {
                        "text": (
                            "NimbusHR acquired PeopleStream UK in Q1. 18% of ARR is now GBP-denominated. "
                            "Management hedges 60% of GBP exposure via rolling forward contracts. Each 10% "
                            "USD strengthening would compress EBITDA by ~90bps absent hedging."
                        ),
                        "meta": {"section": "FX risk summary"},
                    }
                ],
            },
        ],
    },
    {
        "deal": {
            "name": "Forge Industrial Robotics Buyout",
            "industry": "Manufacturing",
            "price": 88000000,
            "ebitda": 9100000,
            "currency": "USD",
            "description": (
                "Forge builds robotic welding cells for Tier 1 auto suppliers. Sponsor is diligencing "
                "cyclical resilience and backlog quality."
            ),
        },
        "documents": [
            {
                "source_name": "forge-operations-report.pdf",
                "mime_type": "application/pdf",
                "chunks": [
                    {
                        "text": (
                            "FY23 revenue $62M (+18% YoY). Backlog covers 11 months of production with "
                            "book-to-bill at 1.2x. Gross margin 34%. EBITDA margin 14.7%. Customers "
                            "primarily North American EV platform builds; top customer 12% of sales."
                        ),
                        "meta": {"section": "Operations"},
                    },
                    {
                        "text": (
                            "Comparable industrial automation targets (ATS, IPG Photonics integrators) "
                            "traded at 9.5x-11.2x EBITDA in the past 24 months. Asset-heavy peers often "
                            "include earn-out structures tied to OEM program ramps."
                        ),
                        "meta": {"section": "Comps"},
                    },
                ],
            }
        ],
    },
    {
        "deal": {
            "name": "BlueWave Logistics Expansion",
            "industry": "Logistics",
            "price": 46000000,
            "ebitda": 5200000,
            "currency": "EUR",
            "description": (
                "Pan-European cold chain operator evaluating cross-border FX exposure and debt capacity "
                "ahead of a mezzanine raise."
            ),
        },
        "documents": [
            {
                "source_name": "bluewave-europe-briefing.docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "chunks": [
                    {
                        "text": (
                            "BlueWave runs 26 refrigerated hubs across DE, FR, NL, and PL. 40% of revenue is in EUR, "
                            "35% in PLN, remainder GBP. PLN EBITDA exposure partially hedged via local borrowing. "
                            "Polish wage inflation +11% YoY compressing margins."
                        ),
                        "meta": {"section": "Network overview"},
                    },
                    {
                        "text": (
                            "FX sensitivity: a 5% EUR/PLN depreciation reduces consolidated EBITDA by €0.7M absent hedges. "
                            "Countermeasure: extend PLN term debt and add collar on projected PLN cash sweep."
                        ),
                        "meta": {"section": "FX sensitivity"},
                    },
                ],
            }
        ],
    },
]


def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def build_payload(client: OpenAI, raw: dict[str, Any]) -> dict[str, Any]:
    deal_payload = raw["deal"].copy()
    documents_payload: list[dict[str, Any]] = []

    for document in raw["documents"]:
        chunks_payload: list[dict[str, Any]] = []
        for idx, chunk in enumerate(document.get("chunks", [])):
            text = chunk["text"].strip()
            embedding = client.embeddings.create(
                model=EMBED_MODEL,
                input=text,
            ).data[0].embedding

            chunks_payload.append(
                {
                    "ord": idx,
                    "text": text,
                    "meta": chunk.get("meta", {}),
                    "hash": hash_text(text),
                    "embedding_model": EMBED_MODEL,
                    "embedding": embedding,
                }
            )

        documents_payload.append(
            {
                "source_name": document["source_name"],
                "mime_type": document.get("mime_type", "text/plain"),
                "chunks": chunks_payload,
            }
        )

    return {"deal": deal_payload, "documents": documents_payload}


def ingest_payload(host: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{host.rstrip('/')}/foundry/ingest"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Foundry ingest with sample deals")
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="FastAPI host (default: %(default)s)")
    parser.add_argument("--dry-run", action="store_true", help="Only print payload metadata")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Export it before running this script.")

    client = OpenAI(api_key=api_key)

    results: list[dict[str, Any]] = []
    for entry in SEED_DATA:
        payload = build_payload(client, entry)
        if args.dry_run:
            print(json.dumps(payload, indent=2)[:500] + "...\n")
            continue
        result = ingest_payload(args.host, payload)
        results.append(result)
        print(f"Ingested deal {result['deal_id']} -> documents={result['documents_ingested']} chunks={result['chunks_ingested']} embeddings={result['embeddings_ingested']}")

    if args.dry_run:
        print("Dry run complete; no requests sent.")
    elif not results:
        print("No payloads ingested.")


if __name__ == "__main__":
    main()
