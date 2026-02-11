
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional 
from app import crud
from app.database import get_db
from app.schemas import Brand, BrandCreate, BrandUpdate
from app.models import Brand as BrandModel

router = APIRouter(
    prefix="/brands",
    tags=["brands"]
)

@router.post("/", response_model=Brand)
def create_brand(brand: BrandCreate, db: Session = Depends(get_db)):
    return crud.create_brand(db=db, brand=brand)

@router.get("/{brand_id}", response_model=Brand)
def get_brand(brand_id: int, db: Session = Depends(get_db)):
    db_brand = crud.get_brand(db, brand_id)
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return db_brand

@router.get("/", response_model=List[Brand])
def get_brands(skip: int = 0, limit: int = 10, status: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    return crud.get_brands(db, skip, limit, status, category)

@router.put("/{brand_id}", response_model = Brand)
def update_brand(brand_id: int, brand_update: BrandUpdate, db: Session = Depends(get_db)):
    db_brand = crud.update_brand(db, brand_id, brand_update)
    if not db_brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return db_brand

@router.delete("/{brand_id}")
def delete_brand(brand_id: int, db: Session = Depends(get_db)):
    success = crud.delete_brand(db, brand_id)
    if not success:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    return {"message": "Brand deleted successfully"}