# Design: Output CSV Quality Improvements

**Date:** 2026-05-01
**Status:** Approved
**Scope:** Surgical fixes to classifier, escalation, retriever, and LLM client

---

## Problem Statement

The current `output.csv` has five categories of defects that hurt evaluation scores:

1. **Raw document dumps as responses** — `llm_client.py` uses Anthropic SDK (no key → returns `None`) so fallback is `chunks[0].text[:500]`, producing truncated HTML/markdown blobs.
2. **`product_area` filename artifacts** — Visa corpus files are flat (`data/visa/support.md`), so `classify_product_area()` returns `"support.md"` instead of a real category.
3. **`request_type` misclassification** — `"request"` in `_FEATURE_WORDS` matches `"all requests are failing"` → `feature_request` instead of `bug`. `"failing"` and `"stopped working"` are not in `_BUG_WORDS`.
4. **Overly aggressive escalation** — `"personal data"` phrase escalates legitimate policy questions (e.g., "how long will my data be used?") that should be answered.
5. **Generic justifications** — Every replied ticket gets `"Replied using retrieved <source> support documentation."` — not traceable to corpus per evaluation rubric.

---

## Approach: Surgical Fix + OpenAI Integration

Keep the existing architecture (retriever → classifier → escalation → response_builder). Fix each bug in its owning module. Replace Anthropic SDK with OpenAI SDK and add a `draft_justification()` function.

**Not changing:** `corpus.py`, `schemas.py`, `validator.py`, `main.py`, `retriever.py` scoring logic.

---

## Module-by-Module Design

### 1. `llm_client.py` — Full rewrite (Anthropic → OpenAI)

**Model:** `gpt-4o-mini` — sufficient quality for support responses, low cost (~100 calls total).

**Functions:**

```python
def draft_response(ticket_text: str, corpus_snippets: list[str]) -> Optional[str]:
    """Generate a user-facing support response grounded in corpus snippets."""
    # System prompt: answer using ONLY provided excerpts, max 150 words, no hallucination
    # Returns None if OPENAI_API_KEY missing or call fails

def draft_justification(ticket_text: str, status: str, retrieved_titles: list[str]) -> Optional[str]:
    """Generate a concise, corpus-traceable justification for the routing decision."""
    # Input: ticket text, status (replied/escalated), list of doc titles retrieved
    # Output: 1-2 sentence justification naming the specific docs/reason
    # Returns None on failure (fallback to existing generic string)
```

**Error handling:** All exceptions caught, return `None` to preserve fallback behavior.

**Env var:** `OPENAI_API_KEY` (read via `os.getenv`).

---

### 2. `classifier.py` — Two targeted fixes

**Fix A: `classify_request_type()`**

Remove `"request"` from `_FEATURE_WORDS` (too broad — matches "all requests are failing").
Replace with specific multi-word phrases.

```python
# Before
_FEATURE_WORDS = ("feature", "would love", "suggestion", "request", "improve", ...)

# After
_FEATURE_WORDS = ("feature request", "would love", "suggestion", "please add", "improve", "add support for", "would be nice")

# Add to _BUG_WORDS
_BUG_WORDS = (...existing..., "failing", "stopped working", "not loading", "keeps crashing")
```

**Fix B: `classify_product_area()`**

Strip `.md` extension and trailing underscores from path-derived area names. For Visa flat files where `parts[idx+2]` is a filename, fall back to company name.

```python
area = parts[idx + 2].replace("-", "_").strip()
area = area.replace(".md", "").replace(".txt", "").strip("_") or "general"
```

---

### 3. `escalation.py` — Phrase specificity

Replace overly broad phrases with more specific ones that won't catch legitimate policy questions:

```python
# Remove
"personal data",

# Add (more specific)
"data breach",
"my data was leaked",
"data stolen",
```

`"privacy"` is also removed from escalation triggers — it is a legitimate corpus topic area (Claude has a privacy_and_legal section), not an escalation signal.

---

### 4. `response_builder.py` — Add justification builder

Add a new exported function:

```python
def build_justification(status: str, issue: str, chunks: list[Chunk]) -> str:
    """Return a corpus-traceable justification string."""
    titles = [chunk.title for chunk in chunks[:3] if chunk.title]
    llm_just = draft_justification(issue, status, titles)
    if llm_just:
        return llm_just
    # Fallback: existing generic strings
    if status == "escalated":
        return "Escalated because the ticket is sensitive, high-risk, or lacks enough corpus evidence."
    source = chunks[0].source if chunks else "support"
    return f"Replied using retrieved {source} support documentation."
```

---

### 5. `agent.py` — Wire justification

Replace hardcoded justification strings with `build_justification()` call:

```python
from response_builder import build_response, build_justification  # updated import

# In run():
justification = build_justification(status=status, issue=query, chunks=retrieved)
```

---

### 6. `retriever.py` — Stopwords + empty fallback

**Extend stopwords** with high-frequency support-ticket noise words:

```python
"please", "help", "need", "want", "have", "using", "get", "use",
"our", "we", "us", "been", "this", "that", "not", "no", "any",
"some", "all", "just", "like", "also", "when", "what", "why",
```

**Empty retrieval fallback:** If no chunk scores > 0 and company is known, return first 3 chunks from that company's corpus rather than empty list (prevents unnecessary escalation of answerable tickets).

---

## Data Flow (unchanged structure)

```
ticket → detect_company → filter corpus by company
       → retrieve(query, filtered_corpus, top_k=5)
       → classify_request_type(query)         [FIXED]
       → classify_product_area(chunks, query)  [FIXED]
       → should_escalate(query, chunks)        [FIXED]
       → build_response(status, query, chunks)
       → build_justification(status, query, chunks)  [NEW]
       → Prediction(...)
```

---

## Files Changed

| File | Type | Priority |
|------|------|----------|
| `llm_client.py` | Full rewrite | Critical |
| `classifier.py` | Targeted fixes (2 functions) | Critical |
| `escalation.py` | Phrase list update | Medium |
| `response_builder.py` | Add `build_justification()` | Medium |
| `agent.py` | Import + call update | Small |
| `retriever.py` | Stopwords + fallback | Small |

## Files NOT changed

`corpus.py`, `schemas.py`, `validator.py`, `main.py`

---

## Success Criteria

- [ ] No `product_area` values ending in `.md`
- [ ] "all requests are failing" → `bug`, not `feature_request`
- [ ] "how long will my data be used" → `replied`, not `escalated`
- [ ] All `replied` responses are LLM-generated prose, not raw doc dumps
- [ ] All justifications name specific docs or concrete reasons
