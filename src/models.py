# models.py

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase
else:
    DeclarativeBase = object

Base = declarative_base()


class User(Base):  # type: ignore[misc,valid-type]
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)

    models = relationship("Model", back_populates="uploader")


class Model(Base):  # type: ignore[misc,valid-type]
    """Model registry entry"""

    __tablename__ = "models"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(50), default="1.0.0")
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = relationship("User", back_populates="models")
    model_metadata = relationship(
        "ModelMetadata", back_populates="model", cascade="all, delete-orphan"
    )


class ModelMetadata(Base):  # type: ignore[misc,valid-type]
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
