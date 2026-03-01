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
def search_brand(request: BrandDiscoveryRequest):
    """
    Step 1 of brand discovery: Search for a brand using AI with web search grounding.
    
    - Takes a brand name (e.g., "CeraVe")
    - Gemini searches the web in real-time for brand info + contact emails
    - Returns brand metadata + list of discovered contacts
    - NOTHING is saved to the database — user reviews first
    """
    gemini = GeminiProvider()
    result = gemini.discover_brand_contacts(request.brand_name)
    return result


@router.post("/pitch", response_model=DiscoveryPitchResponse)
def pitch_selected_contacts(
    request: DiscoveryPitchRequest,
    db: Session = Depends(get_db)
):
    """
    Step 2 of brand discovery: Pitch the contacts the user selected.
    
    After the user reviews the discovered contacts and unchecks any bad ones,
    this endpoint does the following for EACH selected contact:
    1. Check if the email already exists in our database (skip duplicates)
    2. Create a new brand entry in the database
    3. Generate a personalized AI pitch for that brand
    4. Send the pitch email via Resend with tracking pixel
    """
    # Make sure the user has a profile set up (needed for pitch generation)
    profile = crud.get_profile(db)
    if not profile:
        raise HTTPException(status_code=404, detail="Creator profile not found. Set up your profile first.")
    
    results = []
    
    for contact in request.selected_contacts:
        try:
            # 1. Check if this email already exists in our brands table
            existing = crud.get_brand_by_email(db, contact.email)
            if existing:
                results.append({
                    "email": contact.email,
                    "status": "duplicate",
                    "error": "Brand with this email already exists in database"
                })
                continue
            
            # 2. Create a new brand entry
            # The brand name includes the contact type so you can tell them apart
            # e.g., "CeraVe (pr)" vs "CeraVe (partnerships)"
            brand = crud.create_brand(db, {
                "name": f"{request.brand_name} ({contact.type})",
                "email": contact.email,
                "website": request.website,
                "instagram": request.instagram,
                "category": request.category,
                "notes": request.description
            })
            
            # 3. Generate a personalized AI pitch and save it as a draft
            pitch = crud.generate_and_create_pitch(db, brand.id, profile.id)
            
            # 4. Send the pitch email with tracking pixel
            pitch = crud.send_pitch_email(db, pitch.id)
            
            results.append({
                "email": contact.email,
                "brand_id": brand.id,
                "pitch_id": pitch.id,
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
