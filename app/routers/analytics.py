from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud
from app.schemas import AnalyticsOverview, BrandAnalytics

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(db: Session = Depends(get_db)):
    """
    Get aggregate pitch analytics.
    
    Pure database queries — zero AI tokens used.
    Returns: total brands, total pitches, status breakdown,
    open/reply rates, weekly/monthly counts, avg open time.
    """
    return crud.get_analytics_overview(db)


@router.get("/brands/{brand_id}", response_model=BrandAnalytics)
def get_brand_analytics(brand_id: int, db: Session = Depends(get_db)):
    """
    Get pitch history and engagement stats for a specific brand.
    """
    result = crud.get_brand_analytics(db, brand_id)
    if not result:
        raise HTTPException(status_code=404, detail="Brand not found")
    return result
