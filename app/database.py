from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings

#create engine - connects to Postgresql
engine = create_engine(settings.database_url)

#create database Sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#Base class that all models will inherit from
Base = declarative_base()

#Fastapi dependency that provides DB session to routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()