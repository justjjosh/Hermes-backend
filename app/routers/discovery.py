from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud
from app.database import get_db
from app.services.gemini import GeminiProvider
from app.schemas import (
    BrandDiscoveryRequest,
    BrandDiscoveryResponse,
    DiscoveryPitchRequest,
    DiscoveryPitchResponse
)

router = APIRouter()


@router.post("/search", response_model=BrandDiscoveryResponse)
def search_brand(request: BrandDiscoveryRequest, db: Session = Depends(get_db)):
    """
    Step 1 of brand discovery: Search for a brand using AI with web search grounding.
    
    Cache-first strategy:
    1. Check if this brand was already discovered (saved in database)
    2. If cached → return instantly from database (no API call, no tokens used)
    3. If not cached → call Gemini API → save results to database → return
    
    This saves API tokens by only searching each brand once.
    """
    # Step 1: Check the cache first
    cached_data = crud.get_discovered_brand_cache(db, request.brand_name)
    
    if cached_data:
        # Cache hit — return immediately without calling Gemini
        return cached_data
    
    # Step 2: Cache miss — call Gemini API with web search
    try:
        gemini = GeminiProvider()
        result = gemini.discover_brand_contacts(request.brand_name)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI search failed for '{request.brand_name}': {str(e)}"
        )
    
    # Step 3: Validate and sanitize the result before saving/returning
    # Gemini sometimes returns null or missing fields — fill in safe defaults
    # so Pydantic validation doesn't blow up
    result.setdefault("brand_name", request.brand_name)
    result.setdefault("parent_company", None)
    result.setdefault("website", None)
    result.setdefault("instagram", None)
    result.setdefault("category", None)
    result.setdefault("description", None)
    result.setdefault("contacts", [])
    
    # Sanitize each contact — make sure all required fields exist
    cleaned_contacts = []
    for contact in result.get("contacts", []):
        if isinstance(contact, dict) and contact.get("email"):
            cleaned_contacts.append({
                "email": contact["email"],
                "type": contact.get("type", "general"),
                "confidence": contact.get("confidence", "low"),
                "source": contact.get("source", "AI discovery")
            })
    result["contacts"] = cleaned_contacts
    
    # Step 4: Save to database so next search is instant
    crud.cache_discovered_brand(db, result)
    
    return result


@router.post("/pitch", response_model=DiscoveryPitchResponse)
def pitch_selected_contacts(
    request: DiscoveryPitchRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2 of brand discovery: Create brands, generate pitches, and send them.
    
    After the user reviews the discovered contacts and unchecks any bad ones,
    this endpoint does the following for EACH selected contact:
    1. Check if the email already exists and was already pitched (skip duplicates)
    2. Create a new brand entry in the database (or reuse existing)
    3. Generate a personalized AI pitch using Gemini
    4. Send the pitch email immediately via Resend
    """
    # Make sure the user has a profile set up 
    profile = crud.get_profile(db)
    if not profile:
        raise HTTPException(status_code=404, detail="Creator profile not found. Set up your profile first.")
    
    results = []
    
    for contact in request.selected_contacts:
        try:
            # 1. Check if this email already exists in our brands table
            existing = crud.get_brand_by_email(db, contact.email)
            if existing:
                # If the existing brand has already been pitched or has a pitch,
                # skip to avoid sending duplicate emails
                if existing.status in ("pitched", "replied", "partnership"):
                    results.append({
                        "email": contact.email,
                        "status": "duplicate",
                        "error": f"Already {existing.status} — skipping to avoid duplicate emails"
                    })
                    continue
                
                # If the existing brand is just a cache entry (discovered) or
                # hasn't been contacted yet, reuse it instead of creating a new one
                brand = existing
                # Update the name to the proper format (remove "(discovered)" suffix)
                brand.name = f"{request.brand_name} ({contact.type})"
                brand.website = request.website or brand.website
                brand.instagram = request.instagram or brand.instagram
                brand.category = request.category or brand.category
                brand.notes = request.description or brand.notes
                db.commit()
                db.refresh(brand)
            else:
                # 2. Create a new brand entry
                brand = crud.create_brand(db, {
                    "name": f"{request.brand_name} ({contact.type})",
                    "email": contact.email,
                    "website": request.website,
                    "instagram": request.instagram,
                    "category": request.category,
                    "notes": request.description
                })
            
            # 3. Generate a personalized AI pitch using Gemini
            pitch = crud.generate_and_create_pitch(db, brand.id, profile.id)
            
            # 4. Send the pitch email immediately via Resend
            sent_pitch = crud.send_pitch_email(db, pitch.id)
            
            results.append({
                "email": contact.email,
                "brand_id": brand.id,
                "pitch_id": sent_pitch.id,
                "status": "sent"
            })
            
        except Exception as e:
            results.append({
                "email": contact.email,
                "status": "failed",
                "error": str(e)
            })
    
    return {
        "brand_name": request.brand_name,
        "results": results
    }
