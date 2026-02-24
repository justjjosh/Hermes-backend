import uuid
import resend
from app.config import settings

#configure Resend
resend.api_key = settings.resend_api_key

def generate_tracking_pixel_id() -> str:
    """Generate unique UUID for tracking."""
    return str(uuid.uuid4())

def embed_tracking_pixel(body: str, tracking_pixel_id: str, base_url: str) -> str:
    pixel_url = f"{base_url}/track/pixel/{tracking_pixel_id}.png"

    pixel_tag = f'<img src="{pixel_url}" width="1", height="1", style="display:none;" />'

    #append to body and return
    return body + pixel_tag

def send_email_via_resend(
        to_email: str,
        subject: str,
        body_html: str,
        reply_to: str
) -> dict:
    try: 
        params = {
            "from": "josh <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": body_html,
            "reply_to": [reply_to]
        }

        response = resend.Emails.send(params)
        return response
    
    except Exception as e:
        raise Exception(f"Failed to send emial via Resend: {str(e)}")

