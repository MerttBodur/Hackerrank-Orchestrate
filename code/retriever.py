import re
from collections import Counter

from schemas import Chunk


_STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "for", "how", "i", "in", "is",
    "it", "me", "my", "of", "on", "or", "the", "to", "with", "you",
    "please", "help", "need", "want", "have", "using", "get", "use",
    "our", "we", "us", "been", "this", "that", "not", "no", "any",
    "some", "all", "just", "like", "also", "when", "what", "why",
}

MIN_SCORE = 2
_BIGRAM_BONUS = 2
_TITLE_EXACT_BONUS = 5


def _bigram_score(query_tokens: list[str], chunk: Chunk) -> int:
    if len(query_tokens) < 2:
        return 0
    body = " ".join(_tokens(chunk.text))
    title = " ".join(_tokens(chunk.title))
    score = 0
    for a, b in zip(query_tokens, query_tokens[1:]):
        bigram = f"{a} {b}"
        if bigram in body or bigram in title:
            score += _BIGRAM_BONUS
    return score


def _title_exact_bonus(query_tokens: list[str], chunk: Chunk) -> int:
    title_tokens = set(_tokens(chunk.title))
    if query_tokens and all(t in title_tokens for t in query_tokens):
        return _TITLE_EXACT_BONUS
    return 0


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if token not in _STOPWORDS and len(token) > 1
    ]


def _score(query_tokens: list[str], chunk: Chunk) -> int:
    title_counts = Counter(_tokens(chunk.title))
    body_counts = Counter(_tokens(chunk.text))
    score = 0
    for token in query_tokens:
        score += title_counts[token] * 3
        score += min(body_counts[token], 3)
    return score


def retrieve(query: str, chunks: list[Chunk], top_k: int = 5) -> list[Chunk]:
    query_tokens = _tokens(query)
    if not query_tokens or top_k <= 0:
        return []

    scored = []
    for index, chunk in enumerate(chunks):
        score = (
            _score(query_tokens, chunk)
            + _bigram_score(query_tokens, chunk)
            + _title_exact_bonus(query_tokens, chunk)
        )
        if score >= MIN_SCORE:
            scored.append((score, -index, chunk))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [chunk for _, _, chunk in scored[:top_k]]
