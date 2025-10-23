import json
from openai import OpenAI

client = OpenAI()
text = "Executive summary of the Example SaaS deal. Revenue is growing 40% per year with strong retention."
embedding = client.embeddings.create(
    model="text-embedding-3-small",
    input=text,
).data[0].embedding

payload = {
    "deal": {
        "name": "Example SaaS Deal",
        "industry": "SaaS",
        "price": 1200000,
        "ebitda": 200000,
        "currency": "USD",
        "description": "Demo payload for Foundry ingest."
    },
    "documents": [
        {
            "source_name": "teaser.pdf",
            "mime_type": "application/pdf",
            "chunks": [
                {
                    "ord": 0,
                    "text": text,
                    "meta": {"section": "summary"},
                    "hash": "summary-0",
                    "embedding_model": "text-embedding-3-small",
                    "embedding": embedding
                }
            ]
        }
    ]
}

with open("payload.json", "w") as f:
    json.dump(payload, f)

print("Wrote payload.json")
