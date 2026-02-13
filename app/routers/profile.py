from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import Profile, ProfileCreate, ProfileUpdate
from app import crud

router = APIRouter(prefix="/profile", tags=["profile"])

@router.post("/", response_model=Profile, status_code=201)
def create_profile(profile: ProfileCreate, db: Session = Depends(get_db)):
    """Create creator profile (should only be called once)."""
    # Check if profile already exists
    existing_profile = crud.get_profile(db)
    if existing_profile:
        raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")
    
    return crud.create_profile(db, profile)

@router.get("/", response_model=Profile)
def get_profile(db: Session = Depends(get_db)):
    """Get the creator profile."""
    db_profile = crud.get_profile(db)
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return db_profile

@router.put("/", response_model=Profile)
def update_profile(profile_update: ProfileUpdate, db: Session = Depends(get_db)):
    """Update the creator profile."""
    db_profile = crud.update_profile(db, profile_update)
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return db_profile
