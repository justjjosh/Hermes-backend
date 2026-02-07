from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime

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