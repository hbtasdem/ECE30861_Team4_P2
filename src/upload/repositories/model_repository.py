# repositories/model_repository.py
from sqlalchemy.orm import Session
from models import Model, ModelMetadata
from schemas import ModelCreate
from typing import Dict


class ModelRepository:
    """Repository for upload operations (Create only)"""

    def __init__(self, db: Session):
        self.db = db

    def create_model(
        self, model_data: ModelCreate, file_path: str, file_size: int, uploader_id: int
    ) -> Model:
        """Create a new model record in database"""
        db_model = Model(
            name=model_data.name,
            description=model_data.description,
            version=model_data.version,
            file_path=file_path,
            file_size=file_size,
            uploader_id=uploader_id,
            is_sensitive=model_data.is_sensitive,
        )

        self.db.add(db_model)
        self.db.commit()
        # Note: refresh() causes issues in testing, 
        # so we rely on the commit to populate id/timestamps
        # self.db.refresh(db_model)
        return db_model

    def add_model_metadata(self, model_id: int, metadata: Dict[str, str]) -> bool:
        """Add metadata key-value pairs for a model"""
        try:
            for key, value in metadata.items():
                db_metadata = ModelMetadata(
                    model_id=model_id, key=key, value=str(value)
                )
                self.db.add(db_metadata)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
