from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from app.models import (
    Brand as BrandModel, Profile as ProfileModel, Pitch as PitchModel,
    AutopilotConfig as AutopilotConfigModel, AutopilotLog as AutopilotLogModel
)
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

    # Check if a brand with this email already exists
    email = brand_data.get("email")
    if email:
        existing = get_brand_by_email(db, email)
        if existing:
            raise ValueError(f"A brand with email '{email}' already exists (id={existing.id}, name='{existing.name}')")

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
        limit: int = 200,
        status: Optional[str] = None,
        category: Optional[str] = None,
        sort: str = "newest"
) -> List[BrandModel]:
    query = db.query(BrandModel)
    if status:
        query = query.filter(BrandModel.status == status)
    if category:
        query = query.filter(BrandModel.category == category)

    if sort == "oldest":
        query = query.order_by(BrandModel.created_at.asc())
    else:
        query = query.order_by(BrandModel.created_at.desc())

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


def update_brand_status(db: Session, brand_id: int, status: str) -> Optional[BrandModel]:
    """Update a brand's status to reflect where it is in the pitch lifecycle.
    
    Status flow:
        not_contacted → pitched → opened → replied → partnership
                                                   → rejected
    
    Args:
        db: Database session
        brand_id: The brand to update
        status: New status string
    
    Returns:
        Updated BrandModel, or None if brand not found
    """
    brand = get_brand(db, brand_id)
    if not brand:
        return None
    
    brand.status = status
    brand.last_pitched_at = datetime.now(timezone.utc) if status == "pitched" else brand.last_pitched_at
    db.commit()
    db.refresh(brand)
    return brand


def get_discovered_brand_cache(db: Session, brand_name: str) -> Optional[dict]:
    """Check if we've already discovered this brand via AI.
    
    Searches the brands table for any entry that:
    1. Has a name containing the brand_name (case-insensitive)
    2. Was discovered by AI (discovered_by_ai = True)
    3. Has cached metadata stored in brand_metadata
    
    If found, returns the cached discovery data so we don't
    have to call the Gemini API again.
    
    Args:
        db: Database session
        brand_name: Brand name to search for (e.g., "CeraVe")
    
    Returns:
        dict: Cached discovery data matching BrandDiscoveryResponse format
        None: If brand hasn't been discovered before
    """
    # Search for any AI-discovered brand with a matching name
    # func.lower() makes it case-insensitive: "cerave" matches "CeraVe (pr)"
    # .like() with % wildcards matches partial names: "CeraVe" matches "CeraVe (pr)"
    cached_brand = db.query(BrandModel).filter(
        func.lower(BrandModel.name).like(f"%{brand_name.lower()}%"),
        BrandModel.discovered_by_ai.is_(True)
    ).first()
    
    # If no match found, or match has no cached metadata, return None
    if not cached_brand or not cached_brand.brand_metadata:
        return None
    
    # Return the cached metadata (it's already in BrandDiscoveryResponse format)
    return cached_brand.brand_metadata


def cache_discovered_brand(db: Session, discovery_data: dict) -> BrandModel:
    """Save Gemini discovery results to the database as a cache entry.
    
    Creates ONE brand entry specifically for caching purposes:
    - Uses the first contact email as the brand email
    - Stores the FULL discovery response in brand_metadata (JSONB)
    - Marks discovered_by_ai = True so we can find it later
    - Sets status to 'discovered' (not 'not_contacted')
    
    This cache entry exists so that future searches for the same brand
    return instantly from the database instead of calling the API.
    
    The actual brand entries for pitching are created later by the
    /discover/pitch endpoint (one per selected contact).
    
    Args:
        db: Database session
        discovery_data: Full response from gemini.discover_brand_contacts()
    
    Returns:
        BrandModel: The created cache entry
    """
    brand_name = discovery_data.get("brand_name", "Unknown")
    
    # ALWAYS use a placeholder email for cache entries.
    # Previously, we used the first contact's real email here, which caused
    # the "ghost brand" bug: when /discover/pitch later tried to create a brand
    # with that same real email, get_brand_by_email() found this cache entry
    # and marked the contact as "duplicate" — so the real brand was never created,
    # and the pitch was never generated. The cache entry would sit in the database
    # with a name like "CeraVe (discovered)" and no pitch attached.
    cache_email = f"cache-{brand_name.lower().replace(' ', '-')}@discovered.hermes"
    
    # Check if this exact cache entry already exists (avoid duplicates)
    existing = get_brand_by_email(db, cache_email)
    if existing:
        # Update the existing entry's metadata with fresh data
        existing.brand_metadata = discovery_data
        existing.discovered_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create a new cache entry
    cache_brand = BrandModel(
        name=f"{brand_name} (discovered)",
        email=cache_email,
        website=discovery_data.get("website"),
        instagram=discovery_data.get("instagram"),
        category=discovery_data.get("category"),
        notes=discovery_data.get("description"),
        status="discovered",
        discovered_by_ai=True,
        discovered_at=datetime.now(timezone.utc),
        brand_metadata=discovery_data
    )
    db.add(cache_brand)
    db.commit()
    db.refresh(cache_brand)
    
    return cache_brand


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
    mode: Optional[str] = None,
    sort: str = "newest"
) -> List[PitchModel]:
    """Get all pitches with optional filtering and sorting."""
    query = db.query(PitchModel)

    if status:
        query = query.filter(PitchModel.status == status)
    if brand_id:
        query = query.filter(PitchModel.brand_id == brand_id)
    if mode:
        query = query.filter(PitchModel.mode == mode)

    if sort == "oldest":
        query = query.order_by(PitchModel.created_at.asc())
    else:
        query = query.order_by(PitchModel.created_at.desc())

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
    
    # Update the brand's status to "pitched"
    update_brand_status(db, brand.id, "pitched")
    
    return updated_pitch


# ============ WEBHOOK EVENT CRUD ============

def record_pitch_clicked(db: Session, pitch_id: int):
    """Record that a link in the pitch email was clicked."""
    pitch = db.query(PitchModel).filter(PitchModel.id == pitch_id).first()
    if pitch and not pitch.clicked_at:
        pitch.clicked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(pitch)
    return pitch


def record_pitch_bounced(db: Session, pitch_id: int):
    """Record that the pitch email bounced."""
    pitch = db.query(PitchModel).filter(PitchModel.id == pitch_id).first()
    if pitch:
        pitch.status = "bounced"
        db.commit()
        db.refresh(pitch)
    return pitch


def record_pitch_replied(db: Session, pitch_id: int):
    """Record that the brand replied to the pitch."""
    pitch = db.query(PitchModel).filter(PitchModel.id == pitch_id).first()
    if pitch and not pitch.replied_at:
        pitch.replied_at = datetime.now(timezone.utc)
        pitch.status = "replied"
        db.commit()
        db.refresh(pitch)
        # Also update the brand status
        update_brand_status(db, pitch.brand_id, "replied")
    return pitch


# ============ ANALYTICS CRUD ============

def get_analytics_overview(db: Session) -> dict:
    """Compute aggregate pitch stats from the database.
    
    Pure SQL queries — zero AI tokens used.
    """
    from datetime import timedelta
    
    pitches = db.query(PitchModel).all()
    brands = db.query(BrandModel).all()
    
    # Use naive datetime to match PostgreSQL TIMESTAMP (no timezone info)
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Status breakdown
    status_counts = {"draft": 0, "sent": 0, "opened": 0, "clicked": 0, "replied": 0, "bounced": 0}
    for p in pitches:
        status = p.status or "draft"
        if status in status_counts:
            status_counts[status] += 1
    
    # Rates
    sent_count = sum(1 for p in pitches if p.sent_at is not None)
    opened_count = sum(1 for p in pitches if p.opened_at is not None)
    replied_count = sum(1 for p in pitches if p.replied_at is not None)
    
    open_rate = (opened_count / sent_count * 100) if sent_count > 0 else 0.0
    reply_rate = (replied_count / sent_count * 100) if sent_count > 0 else 0.0
    
    # Time-based
    pitches_this_week = sum(1 for p in pitches if p.sent_at and p.sent_at >= week_ago)
    pitches_this_month = sum(1 for p in pitches if p.sent_at and p.sent_at >= month_ago)
    
    # Average open time
    open_times = []
    for p in pitches:
        if p.sent_at and p.opened_at:
            delta = (p.opened_at - p.sent_at).total_seconds() / 3600
            if delta > 0:
                open_times.append(delta)
    avg_open_time = sum(open_times) / len(open_times) if open_times else None
    
    return {
        "total_brands": len(brands),
        "total_pitches": len(pitches),
        "status_breakdown": status_counts,
        "open_rate": round(open_rate, 1),
        "reply_rate": round(reply_rate, 1),
        "pitches_this_week": pitches_this_week,
        "pitches_this_month": pitches_this_month,
        "avg_open_time_hours": round(avg_open_time, 1) if avg_open_time else None,
    }


def get_brand_analytics(db: Session, brand_id: int) -> Optional[dict]:
    """Get all pitch history for a specific brand."""
    brand = get_brand(db, brand_id)
    if not brand:
        return None
    
    pitches = db.query(PitchModel).filter(
        PitchModel.brand_id == brand_id
    ).order_by(PitchModel.created_at.desc()).all()
    
    pitch_summaries = []
    for p in pitches:
        pitch_summaries.append({
            "pitch_id": p.id,
            "subject": p.subject,
            "status": p.status,
            "mode": p.mode,
            "sent_at": p.sent_at,
            "opened_at": p.opened_at,
            "replied_at": p.replied_at,
            "created_at": p.created_at,
        })
    
    return {
        "brand_id": brand.id,
        "brand_name": brand.name,
        "total_pitches": len(pitches),
        "pitches": pitch_summaries,
    }


# ============ AUTOPILOT CRUD ============

def get_autopilot_config(db: Session) -> Optional[AutopilotConfigModel]:
    """Get the autopilot config (singleton — only one row)."""
    return db.query(AutopilotConfigModel).first()


def create_autopilot_config(db: Session, config_data: dict) -> AutopilotConfigModel:
    """Create the autopilot config. Only one should ever exist."""
    existing = get_autopilot_config(db)
    if existing:
        # Update existing instead of creating duplicate
        for key, value in config_data.items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    new_config = AutopilotConfigModel(**config_data)
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    return new_config


def update_autopilot_config(db: Session, update_data: dict) -> Optional[AutopilotConfigModel]:
    """Update the autopilot config."""
    config = get_autopilot_config(db)
    if not config:
        return None
    
    for key, value in update_data.items():
        if value is not None:
            setattr(config, key, value)
    
    db.commit()
    db.refresh(config)
    return config


from datetime import date

def upsert_autopilot_log(db: Session, log_data: dict) -> 'AutopilotLogModel':
    """Update today's autopilot run log entry or create a new one."""
    run_date = log_data.get("run_date", date.today())
    
    # Try to find today's log
    existing_log = db.query(AutopilotLogModel).filter(AutopilotLogModel.run_date == run_date).first()
    
    if existing_log:
        existing_log.brands_discovered += log_data.get("brands_discovered", 0)
        existing_log.brands_skipped += log_data.get("brands_skipped", 0)
        existing_log.pitches_generated += log_data.get("pitches_generated", 0)
        existing_log.pitches_sent += log_data.get("pitches_sent", 0)
        existing_log.tokens_used_estimate += log_data.get("tokens_used_estimate", 0)
        
        # Append new errors to existing ones
        new_errors = log_data.get("errors", [])
        if new_errors:
            current_errors = list(existing_log.errors) if existing_log.errors else []
            current_errors.extend(new_errors)
            existing_log.errors = current_errors
            
        db.commit()
        db.refresh(existing_log)
        return existing_log
    else:
        new_log = AutopilotLogModel(**log_data)
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log


def get_autopilot_logs(db: Session, limit: int = 30) -> list:
    """Get recent autopilot run logs, newest first."""
    return db.query(AutopilotLogModel).order_by(
        AutopilotLogModel.created_at.desc()
    ).limit(limit).all()


def get_autopilot_log_for_today(db: Session) -> Optional['AutopilotLogModel']:
    """Get the autopilot log for the current day to check pacing stats."""
    from datetime import date
    return db.query(AutopilotLogModel).filter(
        AutopilotLogModel.run_date == date.today()
    ).first()

def get_latest_autopilot_log(db: Session) -> Optional['AutopilotLogModel']:
    """Get the most recent autopilot run log."""
    return db.query(AutopilotLogModel).order_by(
        AutopilotLogModel.created_at.desc()
    ).first()


def is_brand_blacklisted(db: Session, email: str) -> bool:
    """Check if a brand's email domain is on the blacklist."""
    config = get_autopilot_config(db)
    if not config or not config.blacklisted_domains:
        return False
    
    domain = email.split("@")[-1].lower() if "@" in email else ""
    return domain in [d.lower() for d in config.blacklisted_domains]