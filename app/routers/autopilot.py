"""Auto-Pilot router — configure, monitor, and control automated brand outreach.

Endpoints:
- POST /autopilot/configure — Create or update autopilot settings
- GET  /autopilot/status    — Get current config + last run stats
- POST /autopilot/pause     — Pause autopilot
- POST /autopilot/resume    — Resume autopilot
- GET  /autopilot/history   — List past autopilot run logs
- POST /autopilot/blacklist — Add a domain to the blacklist
- POST /autopilot/run       — Manually trigger one autopilot cycle (for testing)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud
from app.schemas import (
    AutopilotConfigCreate,
    AutopilotConfigUpdate,
    AutopilotConfigResponse,
    AutopilotLogResponse,
    AutopilotStatus,
    AutopilotRunResult,
    BlacklistRequest,
)
from app.services.pitch_scheduler import run_autopilot_cycle

router = APIRouter()


@router.post("/configure", response_model=AutopilotConfigResponse)
def configure_autopilot(
    config: AutopilotConfigCreate,
    db: Session = Depends(get_db)
):
    """
    Create or update autopilot configuration.
    
    If a config already exists, it will be updated (singleton pattern).
    The autopilot starts paused — call POST /autopilot/resume to activate.
    """
    config_data = config.model_dump()
    result = crud.create_autopilot_config(db, config_data)
    return result


@router.get("/status", response_model=AutopilotStatus)
def get_autopilot_status(db: Session = Depends(get_db)):
    """
    Get current autopilot status: config + last run info.
    """
    from app.services.scheduler import scheduler
    config = crud.get_autopilot_config(db)
    last_run = crud.get_latest_autopilot_log(db)
    
    return {
        "config": config,
        "last_run": last_run,
        "is_configured": config is not None,
        "scheduler_running": scheduler.running
    }


@router.post("/pause", response_model=AutopilotConfigResponse)
def pause_autopilot(db: Session = Depends(get_db)):
    """Pause the autopilot. It will not run until resumed."""
    config = crud.get_autopilot_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Autopilot not configured yet")
    
    updated = crud.update_autopilot_config(db, {"is_active": False})
    return updated


@router.post("/resume", response_model=AutopilotConfigResponse)
def resume_autopilot(db: Session = Depends(get_db)):
    """Resume the autopilot. It will run on the next scheduled cycle."""
    config = crud.get_autopilot_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Autopilot not configured yet")
    
    # Validate that niches are set before allowing resume
    if not config.niches or len(config.niches) == 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot resume — no niches configured. Update config with at least one niche."
        )
    
    updated = crud.update_autopilot_config(db, {"is_active": True})
    return updated


@router.get("/history", response_model=List[AutopilotLogResponse])
def get_autopilot_history(
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """Get past autopilot run logs, newest first."""
    return crud.get_autopilot_logs(db, limit=limit)


@router.post("/blacklist", response_model=AutopilotConfigResponse)
def blacklist_domain(request: BlacklistRequest, db: Session = Depends(get_db)):
    """
    Add a domain to the autopilot blacklist.
    
    Brands with emails from blacklisted domains will be skipped
    during autopilot discovery. Useful for avoiding brands that
    have complained or are not a good fit.
    """
    config = crud.get_autopilot_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="Autopilot not configured yet")
    
    domain = request.domain.lower().strip()
    
    # Don't add duplicates
    current_blacklist = list(config.blacklisted_domains or [])
    if domain in [d.lower() for d in current_blacklist]:
        raise HTTPException(status_code=409, detail=f"Domain '{domain}' is already blacklisted")
    
    current_blacklist.append(domain)
    updated = crud.update_autopilot_config(db, {"blacklisted_domains": current_blacklist})
    return updated


@router.put("/configure", response_model=AutopilotConfigResponse)
def update_autopilot_config(
    config_update: AutopilotConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update specific autopilot settings without replacing the entire config."""
    existing = crud.get_autopilot_config(db)
    if not existing:
        raise HTTPException(status_code=404, detail="Autopilot not configured yet")
    
    update_data = config_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updated = crud.update_autopilot_config(db, update_data)
    return updated


@router.post("/run", response_model=AutopilotRunResult)
def trigger_autopilot_run(db: Session = Depends(get_db)):
    """
    Manually trigger one autopilot cycle (for testing).
    
    This runs the full autopilot pipeline synchronously:
    1. Discover brands via AI (1 Gemini call)
    2. De-duplicate and filter
    3. Generate pitches for new brands
    4. Send if auto_send is enabled
    
    In production, this is triggered by Heroku Scheduler / cron
    via `python -m app.tasks.autopilot_daily`.
    """
    try:
        result = run_autopilot_cycle(db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autopilot run failed: {str(e)}")
