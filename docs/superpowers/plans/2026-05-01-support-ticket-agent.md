# Support Ticket Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pipeline that reads `support_tickets/support_tickets.csv`, classifies each ticket, retrieves relevant corpus snippets from `data/`, decides reply vs. escalate, drafts a response, and writes `support_tickets/output.csv`.

**Architecture:** Deterministic keyword retrieval + rule-based escalation + optional Anthropic API for response drafting. Each stage is a focused module; LLM is only called if `ANTHROPIC_API_KEY` is set, otherwise template responses are used.

**Tech Stack:** Python stdlib only (`csv`, `re`, `os`, `pathlib`) + optional `anthropic` SDK for response drafting.

---

## File Map

| File | Responsibility |
|---|---|
| `code/schemas.py` | `Ticket`, `Chunk`, `Prediction` dataclasses |
| `code/corpus.py` | Walk `data/`, parse markdown → list of `Chunk` |
| `code/retriever.py` | Keyword scoring, return top-k `Chunk` for a ticket |
| `code/classifier.py` | Detect `request_type`, `product_area`, company |
| `code/escalation.py` | Rule-based: return `True` if ticket must be escalated |
| `code/response_builder.py` | Build `response` string from chunks or template |
| `code/llm_client.py` | Optional Anthropic call; returns `None` if no key |
| `code/validator.py` | Coerce / default output fields to allowed values |
| `code/agent.py` | Calls all modules in order, returns `Prediction` |
| `code/main.py` | CSV I/O: read tickets → run agent → write output |
| `code/tests/test_corpus.py` | Unit tests for corpus parsing |
| `code/tests/test_retriever.py` | Unit tests for keyword scoring |
| `code/tests/test_classifier.py` | Unit tests for classification logic |
| `code/tests/test_escalation.py` | Unit tests for escalation rules |
| `code/tests/test_validator.py` | Unit tests for field validation |
| `code/tests/test_agent.py` | Integration test against sample tickets |
| `code/README.md` | Setup and run instructions |

---

## Task 1: schemas.py — Data Models

**Files:**
- Create: `code/schemas.py`

- [ ] **Step 1: Write `schemas.py`**

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Ticket:
    issue: str
    subject: str
    company: Optional[str]

@dataclass
class Chunk:
    source: str   # "claude" | "hackerrank" | "visa"
    file: str
    title: str
    text: str

@dataclass
class Prediction:
    status: str         # "replied" | "escalated"
    product_area: str
    response: str
    justification: str
    request_type: str   # "product_issue" | "feature_request" | "bug" | "invalid"
```

- [ ] **Step 2: Commit**

```bash
git add code/schemas.py
git commit -m "feat: add data model schemas"
```

---

## Task 2: corpus.py — Markdown Corpus Loader

**Files:**
- Create: `code/corpus.py`
- Create: `code/tests/test_corpus.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_corpus.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from corpus import load_corpus

def test_load_corpus_returns_chunks():
    chunks = load_corpus()
    assert len(chunks) > 0

def test_chunk_has_required_fields():
    chunks = load_corpus()
    c = chunks[0]
    assert c.source in ("claude", "hackerrank", "visa")
    assert c.title
    assert c.text

def test_chunk_source_matches_path():
    chunks = load_corpus()
    claude_chunks = [c for c in chunks if c.source == "claude"]
    hackerrank_chunks = [c for c in chunks if c.source == "hackerrank"]
    assert len(claude_chunks) > 0
    assert len(hackerrank_chunks) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_corpus.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` (corpus.py doesn't exist yet)

- [ ] **Step 3: Write `corpus.py`**

```python
import re
from pathlib import Path
from schemas import Chunk

DATA_DIR = Path(__file__).parent.parent / "data"

def _source_from_path(path: Path) -> str:
    parts = path.relative_to(DATA_DIR).parts
    return parts[0]  # "claude", "hackerrank", or "visa"

def _parse_markdown(text: str) -> tuple[str, str]:
    title = ""
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            front = text[3:end]
            for line in front.splitlines():
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"')
                    break
            text = text[end + 3:].strip()
    if not title:
        m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
        title = m.group(1).strip() if m else "unknown"
    body = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    body = re.sub(r"^#+\s+", "", body, flags=re.MULTILINE)
    return title, body.strip()

def load_corpus() -> list[Chunk]:
    chunks = []
    for md_file in DATA_DIR.rglob("*.md"):
        source = _source_from_path(md_file)
        raw = md_file.read_text(encoding="utf-8", errors="ignore")
        title, text = _parse_markdown(raw)
        chunks.append(Chunk(source=source, file=str(md_file), title=title, text=text))
    return chunks
```

- [ ] **Step 4: Run test to verify it passes**

```
cd code && python -m pytest tests/test_corpus.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/corpus.py code/tests/test_corpus.py
git commit -m "feat: add corpus loader with markdown parsing"
```

---

## Task 3: retriever.py — Keyword Scoring

**Files:**
- Create: `code/retriever.py`
- Create: `code/tests/test_retriever.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_retriever.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from schemas import Chunk
from retriever import retrieve

CHUNKS = [
    Chunk(source="hackerrank", file="a.md", title="Test expiration settings", text="Tests in HackerRank remain active indefinitely unless a start and end time is set."),
    Chunk(source="claude", file="b.md", title="Delete account", text="To delete your Claude account go to settings and click delete."),
    Chunk(source="visa", file="c.md", title="Lost card", text="Call Visa to report a lost or stolen card immediately."),
]

def test_retrieve_returns_most_relevant():
    results = retrieve("how long does a test stay active", CHUNKS, top_k=1)
    assert results[0].source == "hackerrank"

def test_retrieve_respects_top_k():
    results = retrieve("account delete test card", CHUNKS, top_k=2)
    assert len(results) == 2

def test_retrieve_empty_query_returns_empty():
    results = retrieve("", CHUNKS, top_k=3)
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_retriever.py -v
```

Expected: `ImportError` (retriever.py doesn't exist yet)

- [ ] **Step 3: Write `retriever.py`**

```python
import re
from schemas import Chunk

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def retrieve(query: str, chunks: list[Chunk], top_k: int = 5) -> list[Chunk]:
    if not query.strip():
        return []
    q_tokens = _tokens(query)
    scored = []
    for chunk in chunks:
        chunk_tokens = _tokens(chunk.title + " " + chunk.text)
        score = len(q_tokens & chunk_tokens)
        if score > 0:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]
```

- [ ] **Step 4: Run test to verify it passes**

```
cd code && python -m pytest tests/test_retriever.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/retriever.py code/tests/test_retriever.py
git commit -m "feat: add keyword-based retriever"
```

---

## Task 4: classifier.py — request_type, product_area, company

**Files:**
- Create: `code/classifier.py`
- Create: `code/tests/test_classifier.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_classifier.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from schemas import Ticket, Chunk
from classifier import classify_request_type, classify_product_area, detect_company

def test_bug_detection():
    assert classify_request_type("the site is down and not working") == "bug"

def test_feature_request_detection():
    assert classify_request_type("I would love a feature to export results") == "feature_request"

def test_invalid_detection():
    assert classify_request_type("who is the actor in iron man?") == "invalid"

def test_product_issue_default():
    assert classify_request_type("how do I set a test expiration?") == "product_issue"

def test_product_area_from_chunks():
    chunks = [Chunk(source="hackerrank", file="data/hackerrank/tests/foo.md", title="Test Settings", text="")]
    area = classify_product_area(chunks, "test settings expiration")
    assert area  # non-empty string

def test_detect_company_from_field():
    assert detect_company(Ticket(issue="x", subject="y", company="Visa")) == "visa"

def test_detect_company_from_text():
    assert detect_company(Ticket(issue="my claude workspace", subject="", company=None)) == "claude"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_classifier.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `classifier.py`**

```python
import pathlib
from schemas import Ticket, Chunk

_BUG_WORDS = {"down", "broken", "error", "crash", "not working", "cannot access", "inaccessible", "outage", "bug"}
_FEATURE_WORDS = {"feature", "would love", "suggestion", "request", "improve", "add support", "would be nice"}
_INVALID_WORDS = {"iron man", "actor", "movie", "who is", "what is the weather", "thank you", "thanks"}
_COMPANY_KEYWORDS = {
    "claude": {"claude", "anthropic", "workspace", "console", "bedrock"},
    "hackerrank": {"hackerrank", "hacker rank", "test", "assessment", "candidate", "recruiter"},
    "visa": {"visa", "card", "payment", "chargeback", "traveller", "cheque"},
}

def classify_request_type(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in _INVALID_WORDS):
        return "invalid"
    if any(w in lower for w in _BUG_WORDS):
        return "bug"
    if any(w in lower for w in _FEATURE_WORDS):
        return "feature_request"
    return "product_issue"

def classify_product_area(chunks: list[Chunk], query: str) -> str:
    if chunks:
        p = pathlib.Path(chunks[0].file)
        parts = p.parts
        try:
            idx = next(i for i, part in enumerate(parts) if part == "data")
            area_parts = parts[idx + 2: idx + 4]
            if area_parts:
                return area_parts[-1].replace("-", "_")
        except StopIteration:
            pass
        return chunks[0].title[:40]
    return "general"

def detect_company(ticket: Ticket) -> str:
    if ticket.company and ticket.company.strip().lower() not in ("none", ""):
        return ticket.company.strip().lower()
    text = (ticket.issue + " " + ticket.subject).lower()
    for company, keywords in _COMPANY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return company
    return "unknown"
```

- [ ] **Step 4: Run test to verify it passes**

```
cd code && python -m pytest tests/test_classifier.py -v
```

Expected: all 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/classifier.py code/tests/test_classifier.py
git commit -m "feat: add keyword-based classifier"
```

---

## Task 5: escalation.py — Rule-Based Escalation

**Files:**
- Create: `code/escalation.py`
- Create: `code/tests/test_escalation.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_escalation.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from escalation import should_escalate

def test_account_access_escalates():
    assert should_escalate("restore my workspace access even though I am not admin", [], "claude") is True

def test_fraud_escalates():
    assert should_escalate("there was a fraudulent charge on my visa card", [], "visa") is True

def test_no_corpus_escalates():
    assert should_escalate("how do I set test expiration", [], "hackerrank") is True

def test_normal_ticket_with_corpus_does_not_escalate():
    from schemas import Chunk
    chunks = [Chunk(source="hackerrank", file="f.md", title="Test settings", text="Tests are active until expiration is set.")]
    assert should_escalate("how long does a test stay active", chunks, "hackerrank") is False

def test_privacy_escalates():
    assert should_escalate("my personal data was exposed, this is a privacy issue", [], "claude") is True

def test_system_down_escalates():
    assert should_escalate("entire platform is down for all users", [], "hackerrank") is True
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_escalation.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `escalation.py`**

```python
from schemas import Chunk

_ESCALATION_PHRASES = [
    "not admin", "not the admin", "not the owner", "without being admin",
    "restore access", "restore my access",
    "fraud", "fraudulent", "chargeback", "dispute",
    "stolen card", "lost card", "stolen cheque",
    "privacy", "personal data", "data breach",
    "entire platform", "system wide", "all users", "site is down",
    "account suspended", "account banned",
    "security vulnerability", "unauthorized access",
    "please delete my account",
]

def should_escalate(issue: str, retrieved_chunks: list[Chunk], company: str) -> bool:
    lower = issue.lower()
    if any(phrase in lower for phrase in _ESCALATION_PHRASES):
        return True
    if not retrieved_chunks:
        return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

```
cd code && python -m pytest tests/test_escalation.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/escalation.py code/tests/test_escalation.py
git commit -m "feat: add rule-based escalation logic"
```

---

## Task 6: llm_client.py + response_builder.py

**Files:**
- Create: `code/llm_client.py`
- Create: `code/response_builder.py`
- Create: `code/tests/test_response_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_response_builder.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from schemas import Chunk
from response_builder import build_response

CHUNKS = [Chunk(source="hackerrank", file="f.md", title="Test expiration", text="Tests remain active unless an end date is set in settings.")]

def test_replied_returns_non_empty():
    r = build_response(status="replied", issue="how long is a test active", chunks=CHUNKS)
    assert r.strip()

def test_escalated_returns_escalation_message():
    r = build_response(status="escalated", issue="restore admin access", chunks=[])
    assert "escalat" in r.lower() or "human" in r.lower() or "team" in r.lower()

def test_replied_includes_chunk_content():
    r = build_response(status="replied", issue="how long is a test active", chunks=CHUNKS)
    assert "active" in r.lower() or "expir" in r.lower() or "date" in r.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_response_builder.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `llm_client.py`**

```python
import os
from typing import Optional

def draft_response(ticket_text: str, corpus_snippets: list[str]) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        snippets_text = "\n\n".join(f"[Source]\n{s}" for s in corpus_snippets[:3])
        prompt = (
            f"You are a support agent. Answer the customer's question using ONLY the provided excerpts. "
            f"If the excerpts do not contain enough information, say you cannot answer. "
            f"Keep the response under 150 words.\n\n"
            f"Excerpts:\n{snippets_text}\n\n"
            f"Customer question: {ticket_text}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return None
```

- [ ] **Step 4: Write `response_builder.py`**

```python
from schemas import Chunk
from llm_client import draft_response

_ESCALATION_REPLY = (
    "Thank you for reaching out. Your request requires review by our support team. "
    "A specialist will follow up with you as soon as possible."
)

def build_response(status: str, issue: str, chunks: list[Chunk]) -> str:
    if status == "escalated":
        return _ESCALATION_REPLY
    snippets = [f"{c.title}: {c.text[:400]}" for c in chunks[:3]]
    llm_reply = draft_response(issue, snippets)
    if llm_reply:
        return llm_reply
    if chunks:
        return chunks[0].text[:500]
    return "We were unable to find a relevant answer. Please contact support."
```

- [ ] **Step 5: Run test to verify it passes**

```
cd code && python -m pytest tests/test_response_builder.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add code/llm_client.py code/response_builder.py code/tests/test_response_builder.py
git commit -m "feat: add response builder with optional LLM drafting"
```

---

## Task 7: validator.py — Output Field Validation

**Files:**
- Create: `code/validator.py`
- Create: `code/tests/test_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_validator.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from schemas import Prediction
from validator import validate

def test_valid_prediction_unchanged():
    p = Prediction(status="replied", product_area="screen", response="ok", justification="found info", request_type="product_issue")
    result = validate(p)
    assert result.status == "replied"
    assert result.request_type == "product_issue"

def test_invalid_status_becomes_escalated():
    p = Prediction(status="UNKNOWN", product_area="x", response="x", justification="x", request_type="bug")
    result = validate(p)
    assert result.status == "escalated"

def test_invalid_request_type_becomes_product_issue():
    p = Prediction(status="replied", product_area="x", response="x", justification="x", request_type="garbage")
    result = validate(p)
    assert result.request_type == "product_issue"

def test_empty_response_gets_default():
    p = Prediction(status="replied", product_area="x", response="", justification="x", request_type="bug")
    result = validate(p)
    assert result.response
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_validator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `validator.py`**

```python
from dataclasses import replace
from schemas import Prediction

_VALID_STATUSES = {"replied", "escalated"}
_VALID_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}

def validate(p: Prediction) -> Prediction:
    status = p.status.lower() if p.status.lower() in _VALID_STATUSES else "escalated"
    request_type = p.request_type.lower() if p.request_type.lower() in _VALID_REQUEST_TYPES else "product_issue"
    response = p.response.strip() if p.response.strip() else "Please contact our support team for assistance."
    product_area = p.product_area.strip() if p.product_area.strip() else "general"
    justification = p.justification.strip() if p.justification.strip() else "No justification provided."
    return replace(p, status=status, request_type=request_type, response=response,
                   product_area=product_area, justification=justification)
```

- [ ] **Step 4: Run test to verify it passes**

```
cd code && python -m pytest tests/test_validator.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/validator.py code/tests/test_validator.py
git commit -m "feat: add output field validator"
```

---

## Task 8: agent.py — Pipeline Coordinator

**Files:**
- Create: `code/agent.py`
- Create: `code/tests/test_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# code/tests/test_agent.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from schemas import Ticket
from agent import SupportAgent

agent = SupportAgent()

def test_hackerrank_ticket_replies():
    t = Ticket(issue="How long do tests stay active in HackerRank?", subject="Test expiry", company="HackerRank")
    p = agent.run(t)
    assert p.status == "replied"
    assert p.request_type in ("product_issue", "bug", "feature_request", "invalid")

def test_access_ticket_escalates():
    t = Ticket(issue="Please restore my workspace access even though I am not admin", subject="Access", company="Claude")
    p = agent.run(t)
    assert p.status == "escalated"

def test_invalid_ticket():
    t = Ticket(issue="What is the name of the actor in Iron Man?", subject="Urgent help", company=None)
    p = agent.run(t)
    assert p.request_type == "invalid"

def test_out_of_scope_escalates():
    t = Ticket(issue="akldjfhakjsdhflaksjdhf completely gibberish request xyz", subject="", company=None)
    p = agent.run(t)
    assert p.status == "escalated"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd code && python -m pytest tests/test_agent.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Write `agent.py`**

```python
from schemas import Ticket, Prediction
from corpus import load_corpus
from retriever import retrieve
from classifier import classify_request_type, classify_product_area, detect_company
from escalation import should_escalate
from response_builder import build_response
from validator import validate

class SupportAgent:
    def __init__(self):
        self._corpus = load_corpus()

    def run(self, ticket: Ticket) -> Prediction:
        company = detect_company(ticket)
        company_chunks = [c for c in self._corpus if c.source == company] if company != "unknown" else self._corpus
        retrieved = retrieve(ticket.issue, company_chunks, top_k=5)
        request_type = classify_request_type(ticket.issue)
        product_area = classify_product_area(retrieved, ticket.issue)

        if request_type == "invalid":
            return validate(Prediction(
                status="replied",
                product_area=product_area,
                response="I'm sorry, this is out of scope from my capabilities.",
                justification="Ticket is not related to supported products.",
                request_type="invalid",
            ))

        escalate = should_escalate(ticket.issue, retrieved, company)
        status = "escalated" if escalate else "replied"
        response = build_response(status=status, issue=ticket.issue, chunks=retrieved)
        justification = (
            "Escalated: risk keyword detected or insufficient corpus evidence."
            if escalate else
            f"Replied using {len(retrieved)} corpus chunk(s) from {company} docs."
        )
        return validate(Prediction(
            status=status,
            product_area=product_area,
            response=response,
            justification=justification,
            request_type=request_type,
        ))
```

- [ ] **Step 4: Run test to verify it passes**

```
cd code && python -m pytest tests/test_agent.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/agent.py code/tests/test_agent.py
git commit -m "feat: add agent pipeline coordinator"
```

---

## Task 9: main.py — CSV I/O

**Files:**
- Modify: `code/main.py`

- [ ] **Step 1: Write `main.py`**

```python
import csv
from pathlib import Path
from schemas import Ticket
from agent import SupportAgent

TICKETS_CSV = Path(__file__).parent.parent / "support_tickets" / "support_tickets.csv"
OUTPUT_CSV = Path(__file__).parent.parent / "support_tickets" / "output.csv"
OUTPUT_FIELDS = ["Issue", "Subject", "Company", "status", "product_area", "response", "justification", "request_type"]

def main():
    agent = SupportAgent()
    rows = []
    with open(TICKETS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            ticket = Ticket(
                issue=row.get("Issue", "").strip(),
                subject=row.get("Subject", "").strip(),
                company=row.get("Company", "").strip() or None,
            )
            pred = agent.run(ticket)
            rows.append({
                "Issue": ticket.issue,
                "Subject": ticket.subject,
                "Company": ticket.company or "",
                "status": pred.status,
                "product_area": pred.product_area,
                "response": pred.response,
                "justification": pred.justification,
                "request_type": pred.request_type,
            })

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run against the tickets CSV**

```
cd code && python main.py
```

Expected: `Wrote N rows to .../support_tickets/output.csv` — no errors

- [ ] **Step 3: Spot-check output.csv**

Open `support_tickets/output.csv`. Verify:
- Headers present: `Issue`, `Subject`, `Company`, `status`, `product_area`, `response`, `justification`, `request_type`
- "How long do the tests stay active" row → `status=replied`
- "site is down" row → `status=escalated`
- "Iron Man actor" row → `request_type=invalid`

- [ ] **Step 4: Run full test suite**

```
cd code && python -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add code/main.py support_tickets/output.csv
git commit -m "feat: wire CSV entry point and produce output.csv"
```

---

## Task 10: README.md

**Files:**
- Create: `code/README.md`

- [ ] **Step 1: Write `code/README.md`**

```markdown
# Support Ticket Agent

Reads `support_tickets/support_tickets.csv`, classifies each ticket, retrieves relevant corpus snippets, and writes `support_tickets/output.csv`.

## Setup

```bash
cd code
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux
pip install anthropic          # optional — only for LLM response drafting
```

## Run

```bash
python main.py
```

Output is written to `support_tickets/output.csv`.

## LLM (Optional)

Set `ANTHROPIC_API_KEY` in your environment or a `.env` file to enable LLM-drafted responses using `claude-haiku-4-5-20251001`. Without it, the agent uses the top corpus snippet directly.

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Test

```bash
cd code
python -m pytest tests/ -v
```

## Architecture

| Module | Role |
|---|---|
| `corpus.py` | Walk `data/` and parse all markdown docs into `Chunk` objects |
| `retriever.py` | Keyword scoring to find the most relevant chunks per ticket |
| `classifier.py` | Detect company, request_type, and product_area |
| `escalation.py` | Rule-based: escalate risky or unanswerable tickets |
| `response_builder.py` | Build response from corpus chunks or optional LLM |
| `validator.py` | Coerce output fields to allowed values |
| `agent.py` | Orchestrate the full pipeline per ticket |
| `main.py` | CSV entry point: read tickets, run agent, write output |
```

- [ ] **Step 2: Commit**

```bash
git add code/README.md
git commit -m "docs: add README with setup and architecture"
```

---

## Self-Review

**Spec coverage:**
- [x] Read `support_tickets.csv` → Task 9
- [x] Classify `request_type` → Task 4
- [x] Retrieve from corpus by keyword → Task 3
- [x] Escalation rules (account, fraud, privacy, no-corpus) → Task 5
- [x] Build response (template + optional LLM) → Task 6
- [x] Write `output.csv` with all 5 required fields → Task 9
- [x] Validate output fields → Task 7
- [x] Optional LLM with env-var key only → Task 6

**Placeholder scan:** None. All steps contain actual code.

**Type consistency:**
- `Chunk` used identically in corpus / retriever / escalation / response_builder / agent
- `Prediction` fields exactly match output CSV column names
- `SupportAgent.run(ticket: Ticket) -> Prediction` consistent across agent / tests / main
