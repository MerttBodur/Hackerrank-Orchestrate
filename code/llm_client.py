import os
from typing import Optional


def draft_response(subject: str, issue: str, snippets: list[str]) -> Optional[str]:
    if not snippets:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        excerpts = "\n\n".join(f"[Source {i + 1}]\n{s}" for i, s in enumerate(snippets[:3]))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a concise support agent. Using ONLY the provided excerpts:\n"
                        "- Answer the specific question in the issue\n"
                        "- Stay under 100 words\n"
                        "- If steps exist, use a numbered list\n"
                        "- If excerpts don't cover the issue, say: "
                        "\"I don't have enough information to answer this.\"\n"
                        "- Never fabricate policies, prices, or steps"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Subject: {subject}\n"
                        f"Issue: {issue}\n\n"
                        f"Excerpts:\n{excerpts}"
                    ),
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
