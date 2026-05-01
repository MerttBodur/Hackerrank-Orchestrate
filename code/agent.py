from classifier import classify_product_area, classify_request_type, detect_company
from corpus import load_corpus
from escalation import should_escalate
from response_builder import build_response, build_justification
from retriever import retrieve
from schemas import Prediction, Ticket
from validator import validate


class SupportAgent:
    def __init__(self):
        self._corpus = load_corpus()

    def run(self, ticket: Ticket) -> Prediction:
        query = f"{ticket.subject} {ticket.issue}".strip()
        company = detect_company(ticket)
        if company == "unknown":
            candidate_chunks = self._corpus
        else:
            candidate_chunks = [chunk for chunk in self._corpus if chunk.source == company]

        retrieved = retrieve(query, candidate_chunks, top_k=5)
        request_type = classify_request_type(query)
        product_area = classify_product_area(retrieved, query)

        if request_type == "invalid":
            return validate(
                Prediction(
                    status="replied",
                    product_area=product_area,
                    response="This request is outside the supported product scope, so I cannot provide a product support answer.",
                    justification="Classified as invalid because it does not match the supported support-ticket domains.",
                    request_type=request_type,
                )
            )

        escalated = should_escalate(query, retrieved, company)
        status = "escalated" if escalated else "replied"
        response = build_response(status=status, issue=query, chunks=retrieved)
        justification = build_justification(status=status, issue=query, chunks=retrieved)

        return validate(
            Prediction(
                status=status,
                product_area=product_area,
                response=response,
                justification=justification,
                request_type=request_type,
            )
        )
