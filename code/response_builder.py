from schemas import Chunk
from llm_client import draft_response, draft_justification

_ESCALATION_REPLY = (
    "Thank you for reaching out. Your request requires review by our support team. "
    "A specialist will follow up with you as soon as possible."
)

_NO_MATCH_REPLY = (
    "We couldn't find a specific answer for your request. "
    "Please contact support directly."
)


def build_response(status: str, subject: str, issue: str, chunks: list[Chunk]) -> str:
    if status == "escalated":
        return _ESCALATION_REPLY
    if not chunks:
        return _NO_MATCH_REPLY
    snippets = [f"{chunk.title}: {chunk.text[:600]}" for chunk in chunks[:3]]
    llm_reply = draft_response(subject, issue, snippets)
    return llm_reply or _NO_MATCH_REPLY


def build_justification(status: str, issue: str, chunks: list[Chunk]) -> str:
    titles = [chunk.title for chunk in chunks[:3] if chunk.title]
    llm_just = draft_justification(issue, status, titles)
    if llm_just:
        return llm_just
    if status == "escalated":
        return "Escalated because the ticket is sensitive, high-risk, or lacks enough corpus evidence."
    source = chunks[0].source if chunks else "support"
    return f"Replied using retrieved {source} support documentation."
