# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Use SQLite for simplicity; configure with environment variable or default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from models import Base, User, Model, ModelMetadata  # Import all models to register them
    Base.metadata.create_all(bind=engine)
