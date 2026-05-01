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

## Optional LLM Drafting

The default path is deterministic and uses the retrieved corpus text directly.
If `ANTHROPIC_API_KEY` is present in the environment and the optional
`anthropic` package is installed, `llm_client.py` can draft shorter replies from
the retrieved snippets. Secrets are read only from environment variables.

## Architecture

| Module | Role |
| --- | --- |
| `schemas.py` | Dataclasses for tickets, corpus chunks, and predictions |
| `corpus.py` | Loads markdown files under `data/` into searchable chunks |
| `retriever.py` | Scores chunks with deterministic keyword matching |
| `classifier.py` | Detects company, request type, and product area |
| `escalation.py` | Escalates sensitive, risky, or unsupported tickets |
| `response_builder.py` | Builds grounded responses from retrieved corpus snippets |
| `validator.py` | Normalizes output fields to allowed values |
| `agent.py` | Coordinates the full pipeline for one ticket |
| `main.py` | CSV entry point for the evaluator |
