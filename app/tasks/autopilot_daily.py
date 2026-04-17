"""Daily autopilot task — CLI entry point for Heroku Scheduler / cron.

Usage:
    python -m app.tasks.autopilot_daily

This script:
1. Creates a database session
2. Runs one complete autopilot cycle
3. Exits with code 0 (success) or 1 (failure)

Configure your Heroku Scheduler (or cron) to run this once daily.
"""
import sys
import logging
from app.database import SessionLocal
from app.services.pitch_scheduler import run_autopilot_cycle

# Set up logging for CLI usage
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Starting daily autopilot cycle...")
    
    db = SessionLocal()
    try:
        result = run_autopilot_cycle(db)
        
        logger.info(
            f"Autopilot complete: "
            f"{result['brands_discovered']} discovered, "
            f"{result['brands_skipped']} skipped, "
            f"{result['pitches_generated']} pitches generated, "
            f"{result['pitches_sent']} sent, "
            f"{len(result['errors'])} errors"
        )
        
        if result["errors"]:
            for err in result["errors"]:
                logger.warning(f"  Error: {err}")
        
        sys.exit(0)
        
    except ValueError as e:
        # Config errors (not configured, paused, no niches, etc.)
        logger.warning(f"Autopilot skipped: {str(e)}")
        sys.exit(0)  # Not a real failure — just not configured
        
    except Exception as e:
        logger.error(f"Autopilot failed: {str(e)}")
        sys.exit(1)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
