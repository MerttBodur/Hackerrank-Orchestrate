import os
from typing import Optional


def draft_response(ticket_text: str, corpus_snippets: list[str]) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        snippets_text = "\n\n".join(f"[Source]\n{s}" for s in corpus_snippets[:3])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a support agent. Answer using ONLY the provided excerpts. "
                        "If the excerpts do not contain enough information, say so clearly. "
                        "Never fabricate policies or steps. Keep your answer under 150 words."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Excerpts:\n{snippets_text}\n\nCustomer question: {ticket_text}",
                },
            ],
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception:
        return None


def draft_justification(
    ticket_text: str, status: str, retrieved_titles: list[str]
) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        titles_str = ", ".join(f'"{t}"' for t in retrieved_titles) if retrieved_titles else "none"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=80,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write a one-sentence justification for a support ticket routing decision. "
                        "Name the specific documents used. Be concise and factual."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Ticket: {ticket_text}\n"
                        f"Decision: {status}\n"
                        f"Documents retrieved: {titles_str}"
                    ),
                },
            ],
        )
        return (response.choices[0].message.content or "").strip() or None
    except Exception:
        return None
