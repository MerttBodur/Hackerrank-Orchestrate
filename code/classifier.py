import pathlib
from schemas import Ticket, Chunk

_BUG_WORDS = (
    "down",
    "broken",
    "error",
    "crash",
    "not working",
    "cannot access",
    "inaccessible",
    "outage",
    "bug",
    "failing",
    "stopped working",
    "not loading",
    "keeps crashing",
)

_FEATURE_WORDS = (
    "feature request",
    "would love",
    "suggestion",
    "please add",
    "improve",
    "add support for",
    "would be nice",
)

_INVALID_WORDS = (
    "iron man",
    "actor",
    "movie",
    "who is",
    "what is the weather",
    "delete all files",
    "delete unnecessary files",
)

_COMPANY_KEYWORDS = {
    "claude": ("claude", "anthropic", "workspace", "console", "bedrock"),
    "hackerrank": ("hackerrank", "hacker rank", "test", "assessment", "candidate", "recruiter"),
    "visa": ("visa", "card", "payment", "chargeback", "traveller", "cheque"),
}


def classify_request_type(text: str) -> str:
    lower = (text or "").lower()
    if any(word in lower for word in _INVALID_WORDS):
        return "invalid"
    if any(word in lower for word in _BUG_WORDS):
        return "bug"
    if any(word in lower for word in _FEATURE_WORDS):
        return "feature_request"
    return "product_issue"


def classify_product_area(chunks: list[Chunk], query: str) -> str:
    if chunks:
        path = pathlib.Path(chunks[0].file)
        parts = path.parts
        if "data" in parts:
            idx = parts.index("data")
            if idx + 2 < len(parts):
                raw = parts[idx + 2]
                area = raw.replace("-", "_").replace(".md", "").replace(".txt", "").strip("_").strip()
                return area or "general"
        return (chunks[0].title or "").strip()[:40] or "general"

    # Keep deterministic fallback for empty retrieval.
    tokens = [t for t in (query or "").lower().split() if t.isalpha()]
    return tokens[0] if tokens else "general"


def detect_company(ticket: Ticket) -> str:
    company = (ticket.company or "").strip().lower()
    if company and company != "none":
        return company

    text = f"{ticket.issue} {ticket.subject}".lower()
    for name, keywords in _COMPANY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return name
    return "unknown"
