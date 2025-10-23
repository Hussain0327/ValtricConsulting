"""
Ad-hoc load test driver for the valuation API.

Usage:
    source .venv/bin/activate
    python -m scripts.load_test --duration 60 --concurrency 10
"""

from __future__ import annotations

import argparse
import asyncio
import random
import time
from statistics import mean

import httpx


EASY_PROMPTS = [
    {"deal_id": 13, "question": "Is this valuation reasonable? Strict JSON."},
    {"deal_id": 13, "question": "Provide a quick valuation verdict. Strict JSON."},
]

HARD_PROMPTS = [
    {"deal_id": 13, "question": "Compare this SaaS deal to EU comps and include FX risks. Strict JSON, cite chunks."},
    {"deal_id": 13, "question": "Build 2025-2027 EV/EBITDA scenarios with churn sensitivity. Strict JSON, cite chunk ids."},
]


async def worker(client: httpx.AsyncClient, duration: float, stats: list[float]):
    end = time.monotonic() + duration
    while time.monotonic() < end:
        roll = random.random()
        if roll < 0.7:
            payload = random.choice(EASY_PROMPTS)
        else:
            payload = random.choice(HARD_PROMPTS)
        path = "/analyze"

        start = time.perf_counter()
        try:
            resp = await client.post(path, json=payload, timeout=120.0)
            resp.raise_for_status()
        except Exception:
            pass
        finally:
            stats.append((time.perf_counter() - start) * 1000)


async def run(concurrency: int, duration: float, base_url: str) -> None:
    stats: list[float] = []
    async with httpx.AsyncClient(base_url=base_url) as client:
        tasks = [asyncio.create_task(worker(client, duration, stats)) for _ in range(concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)

    if stats:
        stats.sort()
        p95 = stats[int(0.95 * len(stats)) - 1]
        print(f"Requests: {len(stats)} | Avg {mean(stats):.2f} ms | P95 {p95:.2f} ms")
    else:
        print("No requests recorded.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple async load test driver.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    args = parser.parse_args()

    asyncio.run(run(args.concurrency, args.duration, args.base_url))


if __name__ == "__main__":
    main()
