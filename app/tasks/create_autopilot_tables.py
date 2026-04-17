"""Add autopilot_config and autopilot_log tables

Run with: python -m app.tasks.create_autopilot_tables
"""
from app.database import engine
from app.models import Base, AutopilotConfig, AutopilotLog

def create_tables():
    """Create the autopilot tables if they don't exist.
    
    Uses SQLAlchemy's create_all which is idempotent —
    safe to run multiple times, only creates tables that don't exist.
    """
    # This only creates tables that don't already exist
    Base.metadata.create_all(bind=engine, tables=[
        AutopilotConfig.__table__,
        AutopilotLog.__table__,
    ])
    print("✓ autopilot_config table ready")
    print("✓ autopilot_log table ready")

if __name__ == "__main__":
    create_tables()
