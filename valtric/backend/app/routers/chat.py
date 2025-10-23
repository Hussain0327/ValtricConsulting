from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_db
from app.services import chat_agent
from app.services.chat_agent import ChatAgentError

router = APIRouter(prefix="/chat", tags=["chat"])
logger = structlog.get_logger(__name__)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    deal_id: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    metadata: dict
    model_used: str


@router.post("/", response_model=ChatResponse)
async def create_chat_message(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    try:
        result = await chat_agent.chat(
            message=request.message,
            conversation_id=request.conversation_id,
            deal_id=request.deal_id,
            session=session,
        )
    except ChatAgentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("chat_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail="chat_processing_failed") from exc
    return ChatResponse(**result)


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db),
):
    conversation = await session.get(models.Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(models.Message)
        .where(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
    )
    result = await session.execute(stmt)
    messages = list(result.scalars().all())

    return {
        "id": conversation.id,
        "title": conversation.title,
        "deal_id": conversation.deal_id,
        "created_at": _as_iso(conversation.created_at),
        "updated_at": _as_iso(conversation.updated_at),
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "model_used": msg.model_used,
                "created_at": _as_iso(msg.created_at),
                "metadata": msg.payload or {},
            }
            for msg in messages
        ],
    }


@router.get("/conversations")
async def list_conversations(
    limit: int = 20,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(models.Conversation)
        .order_by(models.Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    conversations = list(result.scalars().all())

    return {
        "conversations": [
            {
                "id": conv.id,
                "title": conv.title,
                "deal_id": conv.deal_id,
                "created_at": _as_iso(conv.created_at),
                "updated_at": _as_iso(conv.updated_at),
            }
            for conv in conversations
        ]
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db),
):
    conversation = await session.get(models.Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await session.delete(conversation)
    await session.commit()

    return {"status": "deleted", "conversation_id": conversation_id}


def _as_iso(value):
    if value is None:
        return None
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return iso()
    return value
