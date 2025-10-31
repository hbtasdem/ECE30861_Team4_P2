# database.py# database.py

from sqlalchemy import create_enginefrom sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, Sessionfrom sqlalchemy.orm import sessionmaker, Session

import osimport os



# Use SQLite for simplicity; configure with environment variable or default# Use SQLite for simplicity; configure with environment variable or default

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")



if DATABASE_URL.startswith("sqlite"):if DATABASE_URL.startswith("sqlite"):

    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

else:else:

    engine = create_engine(DATABASE_URL)    engine = create_engine(DATABASE_URL)



SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)





def get_db():def get_db():

    """Dependency to get database session"""    """Dependency to get database session"""

    db = SessionLocal()    db = SessionLocal()

    try:    try:

        yield db        yield db

    finally:    finally:

        db.close()        db.close()





def init_db():def init_db():

    """Initialize database tables"""    """Initialize database tables"""

    from models import Base, User, Model, ModelMetadata  # Import all models to register them    from models import (

    Base.metadata.create_all(bind=engine)        Base,

        User,
        Model,
        ModelMetadata,
    )  # Import all models to register them

    Base.metadata.create_all(bind=engine)
