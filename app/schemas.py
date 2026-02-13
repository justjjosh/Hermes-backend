from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime

#Brand pydantic validation
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

#Pydantic validation for creator's profile
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