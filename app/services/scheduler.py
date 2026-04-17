import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.services.pitch_scheduler import run_autopilot_cycle
from app.crud import get_autopilot_config
import datetime

logger = logging.getLogger(__name__)

# Global instance
scheduler = BackgroundScheduler()

def scheduled_autopilot_job():
    """Job function that runs the autopilot cycle."""
    logger.info("Scheduler: Starting scheduled autopilot micro-cycle...")
    db = SessionLocal()
    try:
        # Re-verify the config in case it changed
        config = get_autopilot_config(db)
        if not config or not config.is_active:
            logger.info("Scheduler: Autopilot is paused or unconfigured. Skipping run.")
            return

        # Perform a micro-batch targeting exactly 1 pitch per run to spread out Gemini usage
        result = run_autopilot_cycle(db, target_limit=1)
        logger.info(
            f"Scheduler: Micro-batch complete: "
            f"{result['brands_discovered']} discovered, "
            f"{result['brands_skipped']} skipped, "
            f"{result['pitches_generated']} pitches generated, "
            f"{result['pitches_sent']} sent, "
            f"{len(result['errors'])} errors"
        )
    except ValueError as e:
        logger.warning(f"Scheduler: Autopilot skipped: {str(e)}")
    except Exception as e:
        logger.error(f"Scheduler: Autopilot failed: {str(e)}")
    finally:
        db.close()

from apscheduler.triggers.interval import IntervalTrigger

def start_scheduler():
    """Initializes and starts the APScheduler."""
    if scheduler.running:
        return

    # Check every 5 minutes if it's time to trigger a micro-batch
    scheduler.add_job(
        continuous_check_job,
        IntervalTrigger(minutes=5),
        id='continuous_autopilot_check',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Autopilot continuous background scheduler started.")

def stop_scheduler():
    """Stops the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Autopilot background scheduler stopped.")

def continuous_check_job():
    """Runs continuously to perfectly space out autopilot operations without bursting."""
    from app.crud import get_autopilot_log_for_today
    db = SessionLocal()
    try:
        config = get_autopilot_config(db)
        if not config or not config.is_active or not config.daily_limit:
            return

        # 1. Have we hit today's limit?
        today_log = get_autopilot_log_for_today(db)
        pitches_today = today_log.pitches_sent if today_log else 0
        if pitches_today >= config.daily_limit:
            logger.debug(f"Autopilot Checker: Reached daily limit ({pitches_today}/{config.daily_limit}). Sleeping.")
            return

        # 2. Is it time to run the next micro-batch?
        # Target interval spaces out the daily limit perfectly across 24 hours
        target_interval_minutes = (24 * 60) / config.daily_limit
        
        if config.last_run_at:
            # We must use timezone.utc since SQLAlchemy TIMESTAMP returns naive datetime that represents UTC
            now_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
            last_run_utc = config.last_run_at.replace(tzinfo=datetime.timezone.utc) if config.last_run_at.tzinfo is None else config.last_run_at
            
            elapsed = (now_utc - last_run_utc).total_seconds() / 60
            
            if elapsed < target_interval_minutes:
                logger.debug(f"Autopilot Checker: Only {elapsed:.1f}m passed. Target: {target_interval_minutes:.1f}m. Skipping.")
                return

        logger.info(f"Autopilot Checker: Optimal pacing triggered! Target interval {target_interval_minutes:.1f}m reached. Executing micro-batch.")
        scheduled_autopilot_job()
        
    except Exception as e:
        logger.error(f"Autopilot Continuous Check Failed: {str(e)}")
    finally:
        db.close()
