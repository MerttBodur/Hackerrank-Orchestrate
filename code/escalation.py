from schemas import Chunk

_ESCALATION_PHRASES = (
    "not admin",
    "not the admin",
    "not the owner",
    "without being admin",
    "restore access",
    "restore my access",
    "fraud",
    "fraudulent",
    "chargeback",
    "dispute",
    "stolen card",
    "lost card",
    "stolen cheque",
    "privacy",
    "personal data",
    "data breach",
    "entire platform",
    "system wide",
    "all users",
    "site is down",
    "account suspended",
    "account banned",
    "security vulnerability",
    "unauthorized access",
    "please delete my account",
)


def should_escalate(issue: str, retrieved_chunks: list[Chunk], company: str) -> bool:
    lower = (issue or "").lower()
    if any(phrase in lower for phrase in _ESCALATION_PHRASES):
        return True
    if not retrieved_chunks:
        return True
    return False
