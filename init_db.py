from app.database import Base, engine
from app.models import Brand, Profile, Pitch, AutopilotConfig, AutopilotLog

Base.metadata.create_all(bind=engine)

#created tables
print("Database tables created successfully!")