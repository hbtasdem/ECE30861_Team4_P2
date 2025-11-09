"""Database access layer for model upload operations.

This module handles all database interactions for creating and retrieving model
records. It acts as the bridge between the API routes and the database, using
SQLAlchemy ORM for object-relational mapping.

Key operations:
- Create new model records in the database
- Retrieve models by ID or get all models
- Add and retrieve model metadata
- Manage model URL information
"""

from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from crud.upload.models import ModelCreate
from src.models import Model, ModelMetadata


class ModelRepository:
    """Repository for upload operations (Create, Read)."""

    def __init__(self, db: Session):
        self.db = db

    def create_model(
        self,
        model_data: ModelCreate,
        uploader_id: int
    ) -> Model:
        """Create a new model record in database with URL reference.

        Args:
            model_data: ModelCreate schema with model details and URL
            uploader_id: ID of the user uploading the model

        Returns:
            Created Model object
        """
        db_model = Model(
            name=model_data.name,
            description=model_data.description,
            version=model_data.version,
            model_url=model_data.model_url,
            artifact_type=model_data.artifact_type,
            uploader_id=uploader_id,
            is_sensitive=model_data.is_sensitive
        )

        self.db.add(db_model)
        self.db.commit()
        return db_model

    def get_model_by_id(self, model_id: int) -> Optional[Model]:
        """Get model by ID.

        Args:
            model_id: ID of the model

        Returns:
            Model object if found, None otherwise
        """
        return self.db.query(Model).filter(Model.id == model_id).first()

    def get_all_models(self, skip: int = 0, limit: int = 100) -> List[Model]:
        """Get all models with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Model objects
        """
        return self.db.query(Model).offset(skip).limit(limit).all()

    def add_model_metadata(
        self,
        model_id: int,
        metadata: Dict[str, str]
    ) -> bool:
        """Add metadata key-value pairs for a model.

        Args:
            model_id: ID of the model
            metadata: Dictionary of key-value pairs

        Returns:
            True if successful, False otherwise
        """
        try:
            for key, value in metadata.items():
                db_metadata = ModelMetadata(
                    model_id=model_id,
                    key=key,
                    value=str(value)
                )
                self.db.add(db_metadata)

            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
