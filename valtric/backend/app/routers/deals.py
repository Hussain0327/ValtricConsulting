from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app import models
from app.schemas import DealIn, DealOut

router = APIRouter(prefix="/deals", tags=["deals"])

@router.post("", response_model=DealOut, status_code=201)
async def create_deal(body: DealIn, db: AsyncSession = Depends(get_db)):
    deal = models.Deal(org_id=1, **body.model_dump())
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    return deal

@router.get("/{deal_id}", response_model=DealOut)
async def get_deal(deal_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(models.Deal).where(models.Deal.id == deal_id))
    deal = res.scalar_one_or_none()
    if not deal:
        raise HTTPException(404, "deal not found")
    return deal
