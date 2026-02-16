from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import Pitch, PitchCreate
from app.models import Brand as BrandModel, Profile as ProfileModel
from app import crud
from app.services.gemini import GeminiProvider

router = APIRouter(prefix="/pitches", tags=["pitches"])

ai_provider = GeminiProvider()


def brand_to_dict(brand: BrandModel) -> dict:
    return {
        "name": brand.name,
        "website": brand.website,
        "category": brand.category,
        "instagram": brand.instagram,
        "notes": brand.notes
    }


def profile_to_dict(profile: ProfileModel) -> dict:
    return {
        "name": profile.name,
        "sender_email": profile.sender_email,
        "tiktok_url": profile.tiktok_url,
        "portfolio_url": profile.portfolio_url,
        "niches": profile.niches,
        "interests": profile.interests,
        "bio": profile.bio,
        "content_style": profile.content_style,
        "unique_angle": profile.unique_angle,
        "top_performing_content": profile.top_performing_content,
        "follower_count": profile.follower_count,
        "avg_views": profile.avg_views,
        "engagement_rate": float(profile.engagement_rate) if profile.engagement_rate else None
    }


@router.post("/generate", response_model=Pitch, status_code=201)
def generate_pitch(
    request: dict,
    db: Session = Depends(get_db)
):
    brand_id = request.get("brand_id")
    if not brand_id:
        raise HTTPException(status_code=400, detail="brand_id is required")
    
    brand = crud.get_brand(db, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    profile = crud.get_profile(db)
    if not profile:
        raise HTTPException(status_code=404, detail="Creator profile not found")
    
    brand_data = brand_to_dict(brand)
    profile_data = profile_to_dict(profile)
    
    ai_response = ai_provider.generate_pitch(brand_data, profile_data)
    
    pitch_create = PitchCreate(
        brand_id=brand_id,
        subject=ai_response["subject"],
        body=ai_response["body"],
        mode="manual"
    )
    
    new_pitch = crud.create_pitch(db, pitch_create, profile.id)
    
    return new_pitch


@router.get("/", response_model=List[Pitch])
def list_pitches(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    brand_id: Optional[int] = None,
    mode: Optional[str] = None,
    db: Session = Depends(get_db)
):
    return crud.get_pitches(db, skip, limit, status, brand_id, mode)
