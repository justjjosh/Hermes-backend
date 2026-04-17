from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime

# Brand pydantic validation

#Pydantic schema for Brands
class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    website: Optional[str] = Field(None, max_length=255)
    instagram: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class Brand(BrandCreate):
    id: int
    status: str
    discovered_by_ai: bool
    discovered_at: Optional[datetime]
    brand_metadata: Optional[Dict] = None
    last_pitched_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    website: Optional[str] = Field(None, max_length=255)
    instagram: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)

# Pydantic validation for creator's profile


#Pydantic schema for creators
class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    age: Optional[int] = None
    sender_email: EmailStr
    tiktok_url: str = Field(..., max_length=255)
    instagram_url: Optional[str] = Field(None, max_length=255)
    youtube_url: Optional[str] = Field(None, max_length=255)
    portfolio_url: str = Field(..., max_length=255)
    follower_count: Optional[int] = Field(None, ge=0)
    avg_views: Optional[int] = Field(None, ge=0)
    engagement_rate: Optional[float] = Field(None, ge=0, le=100)
    niches: List[str] = []
    interests: List[str] = []
    bio: Optional[str] = None
    content_style: Optional[str] = None
    unique_angle: Optional[str] = None
    top_performing_content: Optional[str] = None
    pitch_template: Optional[str] = None


#Pydantic schema for pitch
class PitchCreate(BaseModel):
    brand_id: int
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    mode: Optional[str] = Field(default='manual', max_length=50)
    auto_approved: Optional[bool] = False


class Pitch(BaseModel):
    id: int
    brand_id: int
    creator_profile_id: int
    subject: str
    body: str
    status: str
    mode: str
    auto_approved: bool
    tracking_pixel_id: Optional[str]
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    replied_at: Optional[datetime]
    reply_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PitchUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    body: Optional[str] = Field(None, min_length=1)
    status: Optional[str] = Field(None, max_length=50)
    reply_notes: Optional[str] = None


class Profile(ProfileCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    age: Optional[int] = None
    sender_email: Optional[EmailStr] = None
    tiktok_url: Optional[str] = Field(None, max_length=255)
    instagram_url: Optional[str] = Field(None, max_length=255)
    youtube_url: Optional[str] = Field(None, max_length=255)
    portfolio_url: Optional[str] = Field(None, max_length=255)
    follower_count: Optional[int] = Field(None, ge=0)
    avg_views: Optional[int] = Field(None, ge=0)
    engagement_rate: Optional[float] = Field(None, ge=0, le=100)
    niches: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    bio: Optional[str] = None
    content_style: Optional[str] = None
    unique_angle: Optional[str] = None
    top_performing_content: Optional[str] = None
    pitch_template: Optional[str] = None

#Pydantic schema for Brand Discovery

class BrandDiscoveryRequest(BaseModel):
    brand_name: str

class DiscoveredContact(BaseModel):
    email: str
    type: str
    confidence: str
    source: str

class BrandDiscoveryResponse(BaseModel):
    brand_name: str
    contacts: List[DiscoveredContact]

class SelectedContact(BaseModel):
    email: str
    type: str

class DiscoveryPitchRequest(BaseModel):
    brand_name: str
    website: Optional[str] = None
    instagram: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    selected_contacts: List[SelectedContact]

class DiscoveryPitchResult(BaseModel):
    email: str
    brand_id: Optional[int] = None
    pitch_id: Optional[int] = None
    status: str  # "sent", "failed", "duplicate"
    error: Optional[str] = None

class DiscoveryPitchResponse(BaseModel):
    brand_name: str
    results: List[DiscoveryPitchResult]


# ============ Analytics Schemas ============

class PitchStatusBreakdown(BaseModel):
    draft: int = 0
    sent: int = 0
    opened: int = 0
    clicked: int = 0
    replied: int = 0
    bounced: int = 0

class AnalyticsOverview(BaseModel):
    total_brands: int
    total_pitches: int
    status_breakdown: PitchStatusBreakdown
    open_rate: float  # percentage
    reply_rate: float  # percentage
    pitches_this_week: int
    pitches_this_month: int
    avg_open_time_hours: Optional[float]  # average hours from sent to opened

class BrandPitchSummary(BaseModel):
    pitch_id: int
    subject: str
    status: str
    mode: str
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    replied_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class BrandAnalytics(BaseModel):
    brand_id: int
    brand_name: str
    total_pitches: int
    pitches: List[BrandPitchSummary]


# ============ Autopilot Schemas ============

class AutopilotConfigCreate(BaseModel):
    daily_limit: int = Field(default=2, ge=1, le=20)
    niches: List[str] = []
    excluded_categories: List[str] = []
    blacklisted_domains: List[str] = []
    min_confidence: str = Field(default='medium', pattern='^(high|medium|low)$')
    auto_send: bool = False
    run_hour: int = Field(default=9, ge=0, le=23)  # Hour of day (0-23)

class AutopilotConfigUpdate(BaseModel):
    daily_limit: Optional[int] = Field(None, ge=1, le=20)
    niches: Optional[List[str]] = None
    excluded_categories: Optional[List[str]] = None
    blacklisted_domains: Optional[List[str]] = None
    min_confidence: Optional[str] = Field(None, pattern='^(high|medium|low)$')
    auto_send: Optional[bool] = None
    run_hour: Optional[int] = Field(None, ge=0, le=23)

class AutopilotConfigResponse(BaseModel):
    id: int
    is_active: bool
    daily_limit: int
    niches: List[str]
    excluded_categories: List[str]
    blacklisted_domains: List[str]
    min_confidence: str
    auto_send: bool
    run_hour: int
    last_run_at: Optional[datetime]
    total_sent: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AutopilotLogResponse(BaseModel):
    id: int
    run_date: datetime
    brands_discovered: int
    brands_skipped: int
    pitches_generated: int
    pitches_sent: int
    errors: Optional[List] = []
    tokens_used_estimate: int
    created_at: datetime

    class Config:
        from_attributes = True

class AutopilotStatus(BaseModel):
    config: Optional[AutopilotConfigResponse]
    last_run: Optional[AutopilotLogResponse]
    is_configured: bool
    scheduler_running: bool = False  # Whether the background scheduler is active
    next_run_time: Optional[str] = None  # When the next scheduled run will happen

class BlacklistRequest(BaseModel):
    domain: str = Field(..., min_length=3)

class AutopilotRunResult(BaseModel):
    """Returned by the manual /autopilot/run endpoint."""
    brands_discovered: int
    brands_skipped: int
    pitches_generated: int
    pitches_sent: int
    errors: List[Dict] = []