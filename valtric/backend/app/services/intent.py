import re

_SMALL_TALK = re.compile(r"^(hi|hello|hey|how are you|what's up)\b", re.I)


def classify_intent(text: str) -> str:
    """Heuristic classifier to guard small-talk and guide routing."""
    t = (text or "").strip()
    if not t:
        return "valuation"
    if _SMALL_TALK.match(t):
        return "small_talk"
    if re.search(r"(value|valuation|multiple|ev/ebitda|deal|price|range)", t, re.I):
        return "valuation"
    return "valuation"
