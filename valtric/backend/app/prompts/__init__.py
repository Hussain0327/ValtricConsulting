from __future__ import annotations

from pathlib import Path


def _load_prompt() -> str:
    """Load the master system prompt for the valuation agent."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        path = parent / "prompt.md"
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8").strip()
    raise FileNotFoundError("prompt.md not found in parent directories.")


SYSTEM_PROMPT = _load_prompt()
