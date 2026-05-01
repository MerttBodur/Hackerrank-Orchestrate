# Support Ticket Agent

Terminal-based support triage agent for the HackerRank Orchestrate challenge.
It reads `support_tickets/support_tickets.csv`, retrieves relevant local corpus
documents from `data/`, decides whether to reply or escalate, and writes
`support_tickets/output.csv`.

## Run

```bash
python code/main.py
```

From inside `code/`, `python main.py` also works in a normal local shell.

## LLM Response Drafting

Set `OPENAI_API_KEY` in the environment (or a `.env` file) before running.
`llm_client.py` sends the retrieved corpus snippets plus the ticket's subject
and issue separately to `gpt-4o-mini`, which returns a concise (≤ 100 words)
ticket-specific reply. If the key is absent or the API call fails, the agent
falls back to a clean "couldn't find an answer" message — raw document text
never appears in output.

```bash
export OPENAI_API_KEY=sk-...
python code/main.py
```

## Architecture

| Module | Role |
| --- | --- |
| `schemas.py` | Dataclasses for tickets, corpus chunks, and predictions |
| `corpus.py` | Loads markdown files under `data/` into searchable chunks |
| `retriever.py` | Keyword scoring with bigram + title bonus; filters below MIN_SCORE=2 |
| `classifier.py` | Detects company, request type, and product area |
| `escalation.py` | Escalates sensitive, risky, or unsupported tickets |
| `response_builder.py` | Routes to LLM synthesis or clean fallback; never outputs raw corpus text |
| `validator.py` | Normalizes output fields to allowed values |
| `agent.py` | Coordinates the full pipeline for one ticket |
| `main.py` | CSV entry point for the evaluator |
