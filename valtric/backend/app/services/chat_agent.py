from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.services.analyzer import analyze_core
from app.services.enforce import enforce_evidence_rule
from app.services.retrieve import get_similar_chunks

logger = structlog.get_logger(__name__)

_SMALL_TALK = re.compile(r"^(hi|hello|hey|how are you|what's up|good morning|good evening)\b", re.I)
_CODING = re.compile(r"\b(code|bug|stack trace|python|error|script|function)\b", re.I)
_COMPLEX = re.compile(r"\b(scenario|sensitivity|compare|versus|multi-year|multi year|dcf|model)\b", re.I)
_VAL_KEYWORDS = re.compile(r"\b(value|valuation|multiple|price|range|fair|cheap|rich|ev/ebitda|ebitda|deal)\b", re.I)
_DOC_KEYWORDS = re.compile(
    r"\b(documents?|deck|memo|note|section|source|evidence|files?|docs?|pdfs?)\b",
    re.I,
)


class ChatAgentError(RuntimeError):
    """Domain error for chat agent failures."""


async def chat(
    *,
    message: str,
    conversation_id: Optional[str],
    deal_id: Optional[int],
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Core conversational entry point.
    Returns a dict with conversation_id, message, metadata, model_used.
    """
    if session is None:
        raise ChatAgentError("session is required")

    conversation, created = await _get_or_create_conversation(session, conversation_id, deal_id)

    history_stmt = (
        select(models.Message)
        .where(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.created_at.asc())
    )
    history_result = await session.execute(history_stmt)
    history: List[models.Message] = list(history_result.scalars().all())

    route = _classify_route(message)
    logger.info(
        "chat_intent_routed",
        conversation_id=conversation.id,
        deal_id=conversation.deal_id,
        route=route,
        new_conversation=created,
    )

    user_msg = models.Message(
        conversation_id=conversation.id,
        role="user",
        content=message,
    )
    session.add(user_msg)
    await session.flush()

    if not conversation.title:
        conversation.title = message[:48]

    response_text: str
    metadata: Dict[str, Any]
    model_used: str

    try:
        if route == "simple_chat":
            response_text, metadata, model_used = _respond_simple_chat(conversation.deal_id)
        elif route == "coding":
            response_text, metadata, model_used = _respond_coding()
        elif route == "deal_qa":
            response_text, metadata, model_used = await _respond_deal_qa(
                session=session,
                conversation=conversation,
                question=message,
            )
        else:  # valuation or complex_reasoning
            response_text, metadata, model_used = await _respond_valuation(
                session=session,
                conversation=conversation,
                question=message,
                force_complex=(route == "complex_reasoning"),
            )
    except ChatAgentError as exc:
        logger.warning(
            "chat_agent_recoverable_error",
            conversation_id=conversation.id,
            error=str(exc),
            route=route,
        )
        response_text = str(exc)
        metadata = {"route": route, "error": str(exc)}
        model_used = "assistant"
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "chat_agent_unexpected_error",
            conversation_id=conversation.id,
            error=str(exc),
            route=route,
        )
        response_text = "I ran into an unexpected issue handling that request."
        metadata = {"route": route, "error": "unexpected_failure"}
        model_used = "assistant"

    assistant_msg = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
        payload=metadata,
        model_used=model_used,
        tokens_in=None,
        tokens_out=None,
    )
    session.add(assistant_msg)

    conversation.updated_at = datetime.now(timezone.utc)

    await session.commit()

    return {
        "conversation_id": conversation.id,
        "message": response_text,
        "metadata": metadata,
        "model_used": model_used,
    }


async def _get_or_create_conversation(
    session: AsyncSession,
    conversation_id: Optional[str],
    deal_id: Optional[int],
) -> Tuple[models.Conversation, bool]:
    if conversation_id:
        conversation = await session.get(models.Conversation, conversation_id)
        if conversation is None:
            raise ChatAgentError(f"Conversation {conversation_id} not found.")
        if deal_id and not conversation.deal_id:
            conversation.deal_id = deal_id
        return conversation, False

    new_id = str(uuid.uuid4())
    conversation = models.Conversation(id=new_id, deal_id=deal_id)
    session.add(conversation)
    await session.flush()
    return conversation, True


def _classify_route(message: str) -> str:
    text = (message or "").strip()
    lowered = text.lower()
    if not text:
        return "simple_chat"
    if _SMALL_TALK.match(text):
        return "simple_chat"
    if _CODING.search(text):
        return "coding"
    if "document" in lowered or "documents" in lowered or _DOC_KEYWORDS.search(text):
        return "deal_qa"
    if _COMPLEX.search(text):
        return "complex_reasoning"
    if _VAL_KEYWORDS.search(text):
        return "valuation"
    return "simple_chat"


def _respond_simple_chat(deal_id: Optional[int]) -> Tuple[str, Dict[str, Any], str]:
    if deal_id:
        message = (
            "Here to help with Deal "
            f"{deal_id}. Ask about its valuation, request comps, or say “run a valuation”."
        )
    else:
        message = (
            "Hi! I can keep notes, search your deal room, or run a valuation analysis. "
            "Mention a deal ID to get started."
        )
    metadata = {"route": "simple_chat"}
    return message, metadata, "assistant"


def _respond_coding() -> Tuple[str, Dict[str, Any], str]:
    message = (
        "I’m focused on deal analysis. For code or debugging help, try escalating to your "
        "engineering assistant."
    )
    metadata = {"route": "coding"}
    return message, metadata, "assistant"


async def _respond_deal_qa(
    *,
    session: AsyncSession,
    conversation: models.Conversation,
    question: str,
) -> Tuple[str, Dict[str, Any], str]:
    if not conversation.deal_id:
        raise ChatAgentError("Provide a deal_id so I can search the document set.")

    deal = await session.get(models.Deal, conversation.deal_id)
    if deal is None:
        raise ChatAgentError(f"Deal {conversation.deal_id} not found.")

    deal_payload = {
        "id": deal.id,
        "price": float(deal.price or 0.0),
        "ebitda": float(deal.ebitda or 0.0),
        "industry": deal.industry,
        "name": deal.name,
    }

    chunks = await get_similar_chunks(
        deal_payload,
        question=question,
        db=session,
        top_k=5,
    )

    if not chunks:
        message = "I could not find relevant evidence for that request in the deal room."
        metadata = {"route": "deal_qa", "hits": 0}
        return message, metadata, "retrieval-agent"

    lines = []
    metadata_hits = []
    for hit in chunks[:3]:
        source = hit.get("source") or hit.get("meta", {}).get("section") or "unknown source"
        snippet = (hit.get("text") or "").strip().replace("\n", " ")
        lines.append(f"- {source}: {snippet[:160]}{'…' if len(snippet) > 160 else ''}")
        metadata_hits.append(
            {
                "chunk_id": hit.get("chunk_id") or hit.get("id"),
                "source": source,
                "score": hit.get("score"),
            }
        )

    message = "Here’s what I found:\n" + "\n".join(lines)
    metadata = {
        "route": "deal_qa",
        "hits": len(chunks),
        "top_sources": metadata_hits,
    }
    return message, metadata, "retrieval-agent"


async def _respond_valuation(
    *,
    session: AsyncSession,
    conversation: models.Conversation,
    question: str,
    force_complex: bool,
) -> Tuple[str, Dict[str, Any], str]:
    if not conversation.deal_id:
        raise ChatAgentError("Add a deal_id to run a valuation analysis.")

    deal = await session.get(models.Deal, conversation.deal_id)
    if deal is None:
        raise ChatAgentError(f"Deal {conversation.deal_id} not found.")

    analysis, meta = await analyze_core(deal, question, session)
    try:
        enforce_evidence_rule(analysis, meta.get("retrieval_hits", 0))
    except ValueError as exc:
        raise ChatAgentError(str(exc)) from exc

    reply = (
        f"{analysis.conclusion.title()} at ~{analysis.implied_multiple:.1f}x "
        f"(range {analysis.range[0]:.1f}–{analysis.range[1]:.1f}x). "
        f"{analysis.reasoning}"
    )

    metadata: Dict[str, Any] = {
        "route": "complex_reasoning" if force_complex else "valuation",
        "analysis": analysis.model_dump(),
        "metrics": meta,
    }

    return reply, metadata, "valuation-agent"
