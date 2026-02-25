from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models import Brand as BrandModel, Profile as ProfileModel, Pitch as PitchModel
from typing import Optional, List
from app.schemas import BrandCreate, BrandUpdate, ProfileCreate, ProfileUpdate, PitchCreate, PitchUpdate


def create_brand(db: Session, brand: BrandCreate) -> BrandModel:
    new_brand = BrandModel(**brand.model_dump())
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
