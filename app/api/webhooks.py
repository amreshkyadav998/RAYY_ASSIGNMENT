import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.gateway import SIGNATURE_HEADER, verify_signature
from app.models import PaymentWebhook
from app.services import payments as payments_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/payment")
async def payment_webhook(request: Request) -> dict:
    # Verify the signature over the exact bytes received, before parsing.
    raw = await request.body()
    if not verify_signature(raw, request.headers.get(SIGNATURE_HEADER)):
        raise HTTPException(status_code=401, detail="invalid signature")
    try:
        event = PaymentWebhook.model_validate(json.loads(raw))
    except (ValueError, ValidationError):
        raise HTTPException(status_code=400, detail="malformed webhook body")

    try:
        result = await payments_service.handle_payment_succeeded(event)
    except payments_service.PaymentOrderNotFound:
        raise HTTPException(status_code=404, detail="order not found")

    if result.outcome == "amount_mismatch":
        # Not acknowledged as success: the charge does not match what we
        # expected, so the order stays pending and a human has to look
        # (noted on the order).
        raise HTTPException(status_code=422, detail="charged amount does not match order total")
    return {"status": result.outcome}
