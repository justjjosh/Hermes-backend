from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, JSON, ARRAY, Numeric, ForeignKey
from app.database import Base
from datetime import datetime
from sqlalchemy.sql import func


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    website = Column(String(255))
    instagram = Column(String(255))
    category = Column(String(100))
    notes = Column(Text)
    status = Column(String(50), default='not_contacted')
    discovered_by_ai = Column(Boolean, default=False)
    discovered_at = Column(TIMESTAMP)
    brand_metadata = Column(JSON)
    last_pitched_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Profile(Base):
    __tablename__ = "creator_profile"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    age = Column(Integer)
    sender_email = Column(String(255), nullable=False)
    tiktok_url = Column(String(255), nullable=False)
    instagram_url = Column(String(255))
    youtube_url = Column(String(255))
    portfolio_url = Column(String(255), nullable=False)
    follower_count = Column(Integer, default=0)
    avg_views = Column(Integer, default=0)
    engagement_rate = Column(Numeric(5, 2))
    niches = Column(ARRAY(String), server_default='{}')
    interests = Column(ARRAY(String), server_default='{}')
    bio = Column(Text)
    content_style = Column(Text)
    unique_angle = Column(Text)
    top_performing_content = Column(Text)
    pitch_template = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())


class Pitch(Base):
    __tablename__ = "pitches"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey(
        'brands.id', ondelete='CASCADE'), nullable=False)
    creator_profile_id = Column(Integer, ForeignKey(
        'creator_profile.id', ondelete='CASCADE'), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), default='draft')
    mode = Column(String(50), default='manual')
    auto_approved = Column(Boolean, default=False)
    tracking_pixel_id = Column(String(255), unique=True)
    sent_at = Column(TIMESTAMP)
    opened_at = Column(TIMESTAMP)
    clicked_at = Column(TIMESTAMP)
    replied_at = Column(TIMESTAMP)
    reply_notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())
