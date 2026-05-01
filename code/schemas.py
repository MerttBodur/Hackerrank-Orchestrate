from dataclasses import dataclass
from typing import Optional


@dataclass
class Ticket:
    issue: str
    subject: str
    company: Optional[str]


@dataclass
class Chunk:
    source: str
    file: str
    title: str
    text: str


@dataclass
class Prediction:
    status: str
    product_area: str
    response: str
    justification: str
    request_type: str
