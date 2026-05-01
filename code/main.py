import csv
from pathlib import Path

from agent import SupportAgent
from schemas import Ticket


ROOT_DIR = Path(__file__).resolve().parent.parent
TICKETS_CSV = ROOT_DIR / "support_tickets" / "support_tickets.csv"
OUTPUT_CSV = ROOT_DIR / "support_tickets" / "output.csv"
OUTPUT_FIELDS = [
    "Issue",
    "Subject",
    "Company",
    "status",
    "product_area",
    "response",
    "justification",
    "request_type",
]


def _first(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None:
            return value.strip()
    return ""


def main() -> None:
    agent = SupportAgent()
    rows = []

    with TICKETS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ticket = Ticket(
                issue=_first(row, "Issue", "issue"),
                subject=_first(row, "Subject", "subject"),
                company=_first(row, "Company", "company") or None,
            )
            prediction = agent.run(ticket)
            rows.append(
                {
                    "Issue": ticket.issue,
                    "Subject": ticket.subject,
                    "Company": ticket.company or "",
                    "status": prediction.status,
                    "product_area": prediction.product_area,
                    "response": prediction.response,
                    "justification": prediction.justification,
                    "request_type": prediction.request_type,
                }
            )

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
