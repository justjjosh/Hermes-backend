from sqlalchemy.orm import Session
from app.models import Brand as BrandModel
from typing import Optional, List
from app.schemas import BrandCreate, BrandUpdate

def create_brand(db: Session, brand: BrandCreate) -> BrandModel:
    new_brand = BrandModel(**brand.model_dump())
    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)
    return new_brand

def get_brand(db: Session, brand_id: int) -> Optional[BrandModel]:
    return db.query(BrandModel).filter(BrandModel.id == brand_id).first()

def get_brands(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        category: Optional[str] = None
) -> List[BrandModel]:
    query = db.query(BrandModel)
    if status: 
        query = query.filter(BrandModel.status == status)
    if category:
        query = query.filter(BrandModel.category == category)

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

def delete_brand(db: Session, brand_id:int)-> bool:
    db_brand = get_brand(db, brand_id)

    if not db_brand:
        return None
    
    db.delete(db_brand)
    db.commit()
    return True