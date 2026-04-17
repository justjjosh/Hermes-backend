"""Resend webhook handler.

Resend sends POST requests to this endpoint when email events occur
(delivered, opened, clicked, bounced, complained).

We use these events to automatically update pitch and brand statuses,
so the dashboard stays in sync without manual checking.

Webhook events docs: https://resend.com/docs/dashboard/webhooks/introduction
"""
import hashlib
import hmac
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_resend_signature(request_body: bytes, signature: str, secret: str) -> bool:
    """Verify the Resend webhook signature (Svix format).
    
    Returns True if valid, False if tampered or invalid.
    If no secret is configured, skip verification (dev mode).
    """
    if not secret:
        return True  # No secret configured — skip in dev
    
    try:
        expected = hmac.new(
            secret.encode(), request_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def _find_pitch_by_email_id(db: Session, resend_email_id: str):
    """Look up a pitch by the Resend email ID stored in tracking metadata.
    
    For now, we fall back to matching by the 'to' email address
    since we don't currently store the Resend email ID on the pitch.
    Returns None if not found.
    """
    # Future enhancement: store resend_email_id on the Pitch model
    # for direct lookup. For now, this is a placeholder.
    return None


@router.post("/resend")
async def resend_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle incoming Resend webhook events.
    
    Supported event types:
    - email.delivered → confirms delivery
    - email.opened → records open time
    - email.clicked → records click time  
    - email.bounced → marks pitch as bounced
    - email.complained → marks pitch as complained
    """
    body = await request.body()
    
    # Verify signature if webhook secret is configured
    signature = request.headers.get("svix-signature", "")
    webhook_secret = getattr(settings, 'resend_webhook_secret', '')
    
    if webhook_secret and not _verify_resend_signature(body, signature, webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event_type = payload.get("type", "")
    data = payload.get("data", {})
    
    # Extract the recipient email to find the matching pitch
    to_email = ""
    if isinstance(data.get("to"), list) and data["to"]:
        to_email = data["to"][0]
    elif isinstance(data.get("to"), str):
        to_email = data["to"]
    
    if not to_email:
        logger.warning(f"Webhook event '{event_type}' has no recipient email, skipping")
        return {"status": "skipped", "reason": "no recipient email"}
    
    # Find the brand by email, then find their most recent sent pitch
    brand = crud.get_brand_by_email(db, to_email)
    if not brand:
        logger.info(f"Webhook: no brand found for email '{to_email}', skipping")
        return {"status": "skipped", "reason": "brand not found"}
    
    # Get the most recent sent pitch for this brand
    from app.models import Pitch as PitchModel
    pitch = db.query(PitchModel).filter(
        PitchModel.brand_id == brand.id,
        PitchModel.status.in_(["sent", "opened", "clicked"])
    ).order_by(PitchModel.sent_at.desc()).first()
    
    if not pitch:
        logger.info(f"Webhook: no active pitch found for brand '{brand.name}', skipping")
        return {"status": "skipped", "reason": "no active pitch"}
    
    # Handle events
    if event_type == "email.delivered":
        logger.info(f"Email delivered to {to_email} (pitch {pitch.id})")
        # Pitch is already marked as "sent" when we send it — this is just confirmation
    
    elif event_type == "email.opened":
        crud.record_pitch_opened(db, pitch.id)
        crud.update_brand_status(db, brand.id, "opened")
        logger.info(f"Email opened by {to_email} (pitch {pitch.id})")
    
    elif event_type == "email.clicked":
        crud.record_pitch_clicked(db, pitch.id)
        logger.info(f"Link clicked by {to_email} (pitch {pitch.id})")
    
    elif event_type == "email.bounced":
        crud.record_pitch_bounced(db, pitch.id)
        logger.warning(f"Email bounced for {to_email} (pitch {pitch.id})")
    
    elif event_type == "email.complained":
        crud.record_pitch_bounced(db, pitch.id)  # Treat complaint like bounce
        # Auto-blacklist the domain
        domain = to_email.split("@")[-1] if "@" in to_email else ""
        if domain:
            config = crud.get_autopilot_config(db)
            if config and domain not in (config.blacklisted_domains or []):
                blacklist = list(config.blacklisted_domains or [])
                blacklist.append(domain)
                crud.update_autopilot_config(db, {"blacklisted_domains": blacklist})
        logger.warning(f"Spam complaint from {to_email} — domain blacklisted (pitch {pitch.id})")
    
    else:
        logger.info(f"Unhandled webhook event type: {event_type}")
        return {"status": "skipped", "reason": f"unhandled event type: {event_type}"}
    
    return {"status": "processed", "event": event_type, "pitch_id": pitch.id}
