from app.database import Base, engine
from app.models import Brand

Base.metadata.create_all(bind=engine)

#created tables
print("Database tables created successfully!")