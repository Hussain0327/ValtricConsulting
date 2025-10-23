from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.foundry import ingest_deal_payload, IngestError

router = APIRouter(prefix="/foundry", tags=["foundry"])


@router.post("/ingest")
async def ingest_foundry_payload(payload: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await ingest_deal_payload(db, payload)
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result
