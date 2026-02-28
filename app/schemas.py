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
    parent_company: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    category: Optional[str] = None
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