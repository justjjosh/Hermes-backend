"""Pitch Scheduler — Orchestrates the daily autopilot cycle.

This is the core engine of autopilot mode. It:
1. Loads config from the database
2. Calls Gemini ONCE to discover multiple brands (token-efficient)
3. De-duplicates against existing brands
4. Filters blacklisted domains
5. Generates pitches for new brands only
6. Optionally sends them (if auto_send=True)
7. Logs everything for audit

Can be triggered by:
- POST /autopilot/run (manual testing)
- python -m app.tasks.autopilot_daily (Heroku Scheduler / cron)
"""
import logging
import time
from datetime import datetime, timezone, date
from sqlalchemy.orm import Session
from app import crud
from app.services.gemini import GeminiProvider
from app.config import settings

logger = logging.getLogger(__name__)

# Seconds to wait between consecutive Gemini calls in the autopilot loop.
# This prevents rate-limit (429) errors when generating pitches for
# multiple brands back-to-back. The free tier allows ~15 RPM, so
# 10s between calls keeps us safely under the limit.
AUTOPILOT_COOLDOWN_SECONDS = 10


def run_autopilot_cycle(db: Session, target_limit: int = None) -> dict:
    """Execute one complete autopilot cycle or micro-batch.
    
    Token usage:
    - 1 Gemini call for batch brand discovery
    - N Gemini calls for pitch generation (N = new brands only)
    - 0 Gemini calls for de-duplication, blacklist filtering, email sending
    
    Returns:
        dict with run results (brands_discovered, pitches_generated, etc.)
    """
    # Step 1: Load and validate config
    config = crud.get_autopilot_config(db)
    if not config:
        raise ValueError("Autopilot not configured. Call POST /autopilot/configure first.")
    
    if not config.is_active:
        raise ValueError("Autopilot is paused. Call POST /autopilot/resume to activate.")
    
    if not config.niches or len(config.niches) == 0:
        raise ValueError("No niches configured. Update autopilot config with at least one niche.")
    
    # Step 2: Check creator profile exists (needed for pitch generation)
    profile = crud.get_profile(db)
    if not profile:
        raise ValueError("Creator profile not found. Set up your profile first.")
    
    # Track results
    results = {
        "brands_discovered": 0,
        "brands_skipped": 0,
        "pitches_generated": 0,
        "pitches_sent": 0,
        "errors": [],
    }
    
    # Step 3: Batch discover brands
    # If using micro-batches (target_limit), ask for a few extra to account for skipped brands
    discovery_limit = min(target_limit * 3 if target_limit else config.daily_limit, 20)
    logger.info(f"Autopilot: Discovering up to {discovery_limit} brands in niches: {config.niches}")
    
    try:
        gemini = GeminiProvider()
        discovered = gemini.discover_brands(
            niches=config.niches,
            limit=discovery_limit
        )
    except Exception as e:
        error_msg = f"Brand discovery failed: {str(e)}"
        logger.error(f"Autopilot: {error_msg}")
        results["errors"].append({"step": "discovery", "error": error_msg})
        _log_run(db, config, results)
        return results
    
    # Cooldown after batch discovery before starting pitch generation.
    # The discovery call uses search grounding which is heavier on quota.
    logger.info(f"Autopilot: Waiting {AUTOPILOT_COOLDOWN_SECONDS}s after discovery before generating pitches...")
    time.sleep(AUTOPILOT_COOLDOWN_SECONDS)
    
    results["brands_discovered"] = len(discovered)
    logger.info(f"Autopilot: Discovered {len(discovered)} brands")
    
    # Step 4: Process each discovered brand
    for brand_data in discovered:
        brand_email = brand_data.get("email", "")
        brand_name = brand_data.get("name", "Unknown")
        
        try:
            # 4a: Check confidence threshold
            confidence = brand_data.get("confidence", "low")
            confidence_levels = {"high": 3, "medium": 2, "low": 1}
            min_level = confidence_levels.get(config.min_confidence, 2)
            brand_level = confidence_levels.get(confidence, 1)
            
            if brand_level < min_level:
                logger.info(f"Autopilot: Skipping '{brand_name}' — confidence too low ({confidence})")
                results["brands_skipped"] += 1
                continue
            
            # 4b: Check blacklist (0 tokens — pure DB check)
            if crud.is_brand_blacklisted(db, brand_email):
                logger.info(f"Autopilot: Skipping '{brand_name}' — domain blacklisted")
                results["brands_skipped"] += 1
                continue
            
            # 4c: Check if brand email already exists (0 tokens — pure DB check)
            existing = crud.get_brand_by_email(db, brand_email)
            if existing:
                logger.info(f"Autopilot: Skipping '{brand_name}' — already in database (id={existing.id})")
                results["brands_skipped"] += 1
                continue
            
            # 4d: Check excluded categories
            category = brand_data.get("category", "")
            if category and config.excluded_categories:
                if category.lower() in [c.lower() for c in config.excluded_categories]:
                    logger.info(f"Autopilot: Skipping '{brand_name}' — category '{category}' excluded")
                    results["brands_skipped"] += 1
                    continue
            
            # 4e: Create brand in database
            brand = crud.create_brand(db, {
                "name": brand_name,
                "email": brand_email,
                "category": category,
                "discovered_by_ai": True,
                "discovered_at": datetime.now(timezone.utc),
            })
            logger.info(f"Autopilot: Created brand '{brand_name}' (id={brand.id})")
            
            # 4f: Generate pitch (1 Gemini call per brand — only for NEW brands)
            pitch = crud.generate_and_create_pitch(db, brand.id, profile.id)
            
            # Mark pitch as autopilot mode
            pitch.mode = "autopilot"
            if config.auto_send:
                pitch.auto_approved = True
            db.commit()
            
            results["pitches_generated"] += 1
            logger.info(f"Autopilot: Generated pitch for '{brand_name}' (pitch_id={pitch.id})")
            
            # 4g: Send if auto_send is enabled
            if config.auto_send:
                try:
                    crud.send_pitch_email(db, pitch.id)
                    results["pitches_sent"] += 1
                    logger.info(f"Autopilot: Sent pitch to '{brand_name}'")
                except Exception as send_err:
                    error_msg = f"Failed to send pitch to '{brand_name}': {str(send_err)}"
                    logger.error(f"Autopilot: {error_msg}")
                    results["errors"].append({"brand": brand_name, "error": error_msg})
            
            # 4h: Break if we reached the micro-batch target limit
            if target_limit and results["pitches_generated"] >= target_limit:
                logger.info(f"Autopilot: Reached micro-batch target limit ({target_limit}). Stopping loop.")
                break
                
            # Cooldown between brands to avoid rate-limiting
            logger.info(f"Autopilot: Cooldown {AUTOPILOT_COOLDOWN_SECONDS}s before next brand...")
            time.sleep(AUTOPILOT_COOLDOWN_SECONDS)
            
        except Exception as e:
            error_msg = f"Failed to process '{brand_name}': {str(e)}"
            logger.error(f"Autopilot: {error_msg}")
            results["errors"].append({"brand": brand_name, "error": error_msg})
    
    # Step 5: Log the run and update config
    _log_run(db, config, results)
    
    logger.info(
        f"Autopilot cycle complete: "
        f"{results['brands_discovered']} discovered, "
        f"{results['brands_skipped']} skipped, "
        f"{results['pitches_generated']} pitches generated, "
        f"{results['pitches_sent']} sent"
    )
    
    return results


def _log_run(db: Session, config, results: dict):
    """Save the autopilot run results to the log table and update config."""
    # Rough token estimate:
    # ~500 tokens for batch discovery prompt + response
    # ~800 tokens per pitch generation
    token_estimate = 500 + (results["pitches_generated"] * 800)
    
    crud.upsert_autopilot_log(db, {
        "run_date": date.today(),
        "brands_discovered": results["brands_discovered"],
        "brands_skipped": results["brands_skipped"],
        "pitches_generated": results["pitches_generated"],
        "pitches_sent": results["pitches_sent"],
        "errors": results["errors"],
        "tokens_used_estimate": token_estimate,
    })
    
    # Update config with last run time and total sent count
    config.last_run_at = datetime.now(timezone.utc)
    config.total_sent = (config.total_sent or 0) + results["pitches_sent"]
    db.commit()
