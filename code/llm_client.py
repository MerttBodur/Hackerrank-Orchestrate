import os
from typing import Optional


def draft_response(ticket_text: str, corpus_snippets: list[str]) -> Optional[str]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic  # Optional dependency; absent in stdlib-only mode.

        client = anthropic.Anthropic(api_key=api_key)
        snippets_text = "\n\n".join(f"[Source]\n{s}" for s in corpus_snippets[:3])
        prompt = (
            "You are a support agent. Answer using ONLY provided excerpts. "
            "If evidence is insufficient, clearly say so. Keep under 150 words.\n\n"
            f"Excerpts:\n{snippets_text}\n\n"
            f"Customer question: {ticket_text}"
        )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        if not msg.content:
            return None
        return (msg.content[0].text or "").strip() or None
    except Exception:
        return None
