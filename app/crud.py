from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models import Brand as BrandModel, Profile as ProfileModel, Pitch as PitchModel
from typing import Optional, List, Union, Dict
from app.services.gemini import GeminiProvider
from app.schemas import BrandCreate, BrandUpdate, ProfileCreate, ProfileUpdate, PitchCreate, PitchUpdate
from app.config import settings


def create_brand(db: Session, brand: Union[BrandCreate, Dict]) -> BrandModel:
    """Create a new brand. Accepts BrandCreate schema or a plain dict."""
    if isinstance(brand, dict):
        brand_data = brand
    else:
        brand_data = brand.model_dump()

    new_brand = BrandModel(**brand_data)
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    return new_brand


def get_brand(db: Session, brand_id: int) -> Optional[BrandModel]:
    return db.query(BrandModel).filter(BrandModel.id == brand_id).first()


def get_brands(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        category: Optional[str] = None
) -> List[BrandModel]:
    query = db.query(BrandModel)
    if status:
        query = query.filter(BrandModel.status == status)
    if category:
        query = query.filter(BrandModel.category == category)

    return query.offset(skip).limit(limit).all()


def update_brand(db: Session, brand_id: int, brand_update: BrandUpdate) -> BrandModel:
    db_brand = get_brand(db, brand_id)

    if not db_brand:
        return None

    update_data = brand_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_brand, key, value)

    db.commit()
    db.refresh(db_brand)
    return db_brand


def delete_brand(db: Session, brand_id: int) -> bool:
    db_brand = get_brand(db, brand_id)

    if not db_brand:
        return None

    db.delete(db_brand)
    db.commit()
    return True


def get_brand_by_email(db: Session, email: str) -> Optional[BrandModel]:
    """Check if a brand with this email already exists."""
    return db.query(BrandModel).filter(BrandModel.email == email).first()


# ============ Creator Profile CRUD ============


def create_profile(db: Session, profile: ProfileCreate) -> ProfileModel:
    """Create a new creator profile (only one should exist)."""
    new_profile = ProfileModel(**profile.model_dump())
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return new_profile


def get_profile(db: Session) -> Optional[ProfileModel]:
    """Get the creator profile (returns the first/only profile)."""
    return db.query(ProfileModel).first()


def update_profile(db: Session, profile_update: ProfileUpdate) -> Optional[ProfileModel]:
    """Update the creator profile."""
    db_profile = get_profile(db)

    if not db_profile:
        return None

    update_data = profile_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile


# ============ Pitch CRUD ============

def create_pitch(db: Session, pitch: PitchCreate, creator_profile_id: int) -> PitchModel:
    """Create a new pitch."""
    pitch_data = pitch.model_dump()
    pitch_data['creator_profile_id'] = creator_profile_id
    new_pitch = PitchModel(**pitch_data)
    db.add(new_pitch)
    db.commit()
    db.refresh(new_pitch)
    return new_pitch


def get_pitch(db: Session, pitch_id: int) -> Optional[PitchModel]:
    """Get a specific pitch by ID."""
    return db.query(PitchModel).filter(PitchModel.id == pitch_id).first()


def get_pitches(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    brand_id: Optional[int] = None,
    mode: Optional[str] = None
) -> List[PitchModel]:
    """Get all pitches with optional filtering."""
    query = db.query(PitchModel)

    if status:
        query = query.filter(PitchModel.status == status)
    if brand_id:
        query = query.filter(PitchModel.brand_id == brand_id)
    if mode:
        query = query.filter(PitchModel.mode == mode)

    return query.offset(skip).limit(limit).all()


def update_pitch(db: Session, pitch_id: int, pitch_update: PitchUpdate) -> Optional[PitchModel]:
    """Update a pitch."""
    db_pitch = get_pitch(db, pitch_id)

    if not db_pitch:
        return None

    update_data = pitch_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pitch, key, value)

    db.commit()
    db.refresh(db_pitch)
    return db_pitch


def delete_pitch(db: Session, pitch_id: int) -> bool:
    """Delete a pitch."""
    db_pitch = get_pitch(db, pitch_id)

    if not db_pitch:
        return None

    db.delete(db_pitch)
    db.commit()
    return True

def update_pitch_after_send(db: Session, pitch_id: int, tracking_pixel_id: str) -> PitchModel:
    pitch = db.query(PitchModel).filter(PitchModel.id == pitch_id).first()
    if pitch:
        pitch.status = "sent"
        pitch.tracking_pixel_id = tracking_pixel_id
        pitch.sent_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(pitch)
    return pitch

# ============ TRACKING PIXEL CRUD ============

def get_pitch_by_tracking_id(db: Session, tracking_pixel_id: str):
    pitch = db.query(PitchModel).filter(PitchModel.tracking_pixel_id == tracking_pixel_id).first()
    return pitch
    
def record_pitch_opened(db: Session, pitch_id: int):
    pitch = db.query(PitchModel).filter(PitchModel.id == pitch_id).first()
    if pitch and not pitch.opened_at:
        pitch.opened_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(pitch)
    return pitch


# ============ BRAND DISCOVERY CRUD ============

def generate_and_create_pitch(db: Session, brand_id: int, creator_profile_id: int) -> PitchModel:
    """Generate a pitch using AI and save it to database.
    
    This is a reusable function called by:
    - The discovery router (POST /discover/pitch)
    - Could also be used by the autopilot system later
    
    It does three things:
    1. Fetches brand + profile data from the database
    2. Calls Gemini to generate a personalized pitch
    3. Saves the pitch to the database as a draft
    """
    # Fetch the brand and profile from the database
    brand = get_brand(db, brand_id)
    profile = get_profile(db)
    
    # Generate pitch using Gemini AI
    gemini = GeminiProvider()
    ai_response = gemini.generate_pitch(
        brand_data={
            "name": brand.name,
            "website": brand.website,
            "category": brand.category,
            "notes": brand.notes,
            "instagram": brand.instagram
        },
        profile_data={
            "name": profile.name,
            "bio": profile.bio,
            "niches": profile.niches,
            "interests": profile.interests,
            "content_style": profile.content_style,
            "unique_angle": profile.unique_angle,
            "top_performing_content": profile.top_performing_content,
            "tiktok_url": profile.tiktok_url,
            "portfolio_url": profile.portfolio_url,
            "sender_email": profile.sender_email,
            "follower_count": profile.follower_count,
            "avg_views": profile.avg_views,
            "engagement_rate": float(profile.engagement_rate) if profile.engagement_rate else None
        }
    )
    
    # Create a PitchCreate schema object (same as what the /pitches/generate endpoint does)
    pitch_create = PitchCreate(
        brand_id=brand_id,
        subject=ai_response["subject"],
        body=ai_response["body"],
        mode="manual"
    )
    
    # Save to database using the existing create_pitch function
    new_pitch = create_pitch(db, pitch_create, creator_profile_id)
    
    return new_pitch


def send_pitch_email(db: Session, pitch_id: int) -> PitchModel:
    """Send a pitch email and update its status.
    
    This is a reusable function called by:
    - The discovery router (POST /discover/pitch)
    - Could also be used by the autopilot system later
    
    It does four things:
    1. Fetches the pitch, brand, and profile from the database
    2. Generates a tracking pixel and embeds it in the HTML body
    3. Sends the email via Resend
    4. Updates the pitch status to "sent" with the tracking pixel ID
    
    It reuses the same email helper functions that the /pitches/{id}/send endpoint uses.
    """
    from app.services.email import send_email_via_resend, generate_tracking_pixel_id, embed_tracking_pixel
    
    # Fetch pitch, brand, and profile
    pitch = get_pitch(db, pitch_id)
    brand = get_brand(db, pitch.brand_id)
    profile = get_profile(db)
    
    # Generate tracking pixel ID and embed it in the HTML body
    # Uses the SAME functions as the /pitches/{id}/send endpoint
    tracking_pixel_id = generate_tracking_pixel_id()
    body_with_pixel = embed_tracking_pixel(
        body=pitch.body,
        tracking_pixel_id=tracking_pixel_id,
        base_url=settings.api_base_url
    )
    
    # Send the email via Resend
    send_email_via_resend(
        to_email=brand.email,
        subject=pitch.subject,
        body_html=body_with_pixel,
        reply_to=profile.sender_email
    )
    
    # Update pitch status using the existing function
    updated_pitch = update_pitch_after_send(db, pitch_id, tracking_pixel_id)
    
    return updated_pitch