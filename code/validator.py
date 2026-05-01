from dataclasses import replace
from schemas import Prediction

_VALID_STATUSES = {"replied", "escalated"}
_VALID_REQUEST_TYPES = {"product_issue", "feature_request", "bug", "invalid"}


def validate(p: Prediction) -> Prediction:
    status_candidate = (p.status or "").lower()
    request_type_candidate = (p.request_type or "").lower()
    response_candidate = (p.response or "").strip()
    product_area_candidate = (p.product_area or "").strip()
    justification_candidate = (p.justification or "").strip()

    status = status_candidate if status_candidate in _VALID_STATUSES else "escalated"
    request_type = (
        request_type_candidate
        if request_type_candidate in _VALID_REQUEST_TYPES
        else "product_issue"
    )
    response = response_candidate or "Please contact our support team for assistance."
    product_area = product_area_candidate or "general"
    justification = justification_candidate or "No justification provided."

    return replace(
        p,
        status=status,
        request_type=request_type,
        response=response,
        product_area=product_area,
        justification=justification,
    )
