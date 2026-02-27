from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
import base64
from app.database import get_db
from app import crud

router = APIRouter()

TRANSPARENT_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)

@router.get("/pixel/{tracking_pixel_id}.png")
def track_pixel_open(tracking_pixel_id: str, db: Session = Depends(get_db)):
    pitch = crud.get_pitch_by_tracking_id(db, tracking_pixel_id)

    if pitch and not pitch.opened_at:
        crud.record_pitch_opened(db, pitch.id)
    
    return Response(content=TRANSPARENT_PNG, media_type="image/png")

