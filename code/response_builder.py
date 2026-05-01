from schemas import Chunk
from llm_client import draft_response

_ESCALATION_REPLY = (
    "Thank you for reaching out. Your request requires review by our support team. "
    "A specialist will follow up with you as soon as possible."
)

_NO_MATCH_REPLY = "We were unable to find a relevant answer. Please contact support."


def build_response(status: str, issue: str, chunks: list[Chunk]) -> str:
    if status == "escalated":
        return _ESCALATION_REPLY

    snippets = [f"{chunk.title}: {chunk.text[:400]}" for chunk in chunks[:3]]
    llm_reply = draft_response(issue, snippets)
    if llm_reply:
        return llm_reply

    if chunks:
        return chunks[0].text[:500].strip() or _NO_MATCH_REPLY
    return _NO_MATCH_REPLY
