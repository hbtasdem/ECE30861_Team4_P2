# models.py# models.py

from sqlalchemy import Column, Integer, String, Text, BigInteger, Boolean, DateTime, ForeignKeyfrom sqlalchemy import (

from sqlalchemy.orm import declarative_base, relationship    Column,

from datetime import datetime    Integer,

    String,

Base = declarative_base()    Text,

    BigInteger,

class User(Base):    Boolean,

    """User model for authentication"""    DateTime,

    __tablename__ = "users"    ForeignKey,

    )

    id = Column(Integer, primary_key=True)from sqlalchemy.orm import declarative_base, relationship

    username = Column(String(255), unique=True, nullable=False)from datetime import datetime

    email = Column(String(255), unique=True, nullable=False)

    is_admin = Column(Boolean, default=False)Base = declarative_base()

    

    models = relationship("Model", back_populates="uploader")

class User(Base):

class Model(Base):    """User model for authentication"""

    """Model registry entry"""

    __tablename__ = "models"    __tablename__ = "users"

    

    id = Column(Integer, primary_key=True)    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)    username = Column(String(255), unique=True, nullable=False)

    description = Column(Text)    email = Column(String(255), unique=True, nullable=False)

    version = Column(String(50), default="1.0.0")    is_admin = Column(Boolean, default=False)

    file_path = Column(String(500), nullable=False)

    file_size = Column(BigInteger)    models = relationship("Model", back_populates="uploader")

    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    is_sensitive = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)class Model(Base):

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)    """Model registry entry"""

    

    uploader = relationship("User", back_populates="models")    __tablename__ = "models"

    model_metadata = relationship("ModelMetadata", back_populates="model", cascade="all, delete-orphan")

    id = Column(Integer, primary_key=True)

class ModelMetadata(Base):    name = Column(String(255), nullable=False)

    """Additional metadata for models"""    description = Column(Text)

    __tablename__ = "model_metadata"    version = Column(String(50), default="1.0.0")

        file_path = Column(String(500), nullable=False)

    id = Column(Integer, primary_key=True)    file_size = Column(BigInteger)

    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False)    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    key = Column(String(255), nullable=False)    is_sensitive = Column(Boolean, default=False)

    value = Column(Text)    created_at = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    

    model = relationship("Model", back_populates="model_metadata")    uploader = relationship("User", back_populates="models")

    model_metadata = relationship(
        "ModelMetadata", back_populates="model", cascade="all, delete-orphan"
    )


class ModelMetadata(Base):
    """Additional metadata for models"""

    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True)
    model_id = Column(
        Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    key = Column(String(255), nullable=False)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("Model", back_populates="model_metadata")
