# repositories/model_repository.py
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Model, ModelMetadata
from schemas import ModelCreate, ModelUpdate  # noqa: F401


class ModelRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_model(self, model_data: ModelCreate, file_path: str, file_size: int, uploader_id: int) -> Model:
        """Create a new model record in database"""
        db_model = Model(
            name=model_data.name,
            description=model_data.description,
            version=model_data.version,
            file_path=file_path,
            file_size=file_size,
            uploader_id=uploader_id,
            is_sensitive=model_data.is_sensitive
        )

        self.db.add(db_model)
        self.db.commit()
        # Note: refresh() causes issues in testing, so we rely on the commit to populate id/timestamps
        # self.db.refresh(db_model)
        return db_model

    def get_model_by_id(self, model_id: int) -> Optional[Model]:
        """Get model by ID"""
        return self.db.query(Model).filter(Model.id == model_id).first()

    def get_models_by_uploader(self, uploader_id: int) -> List[Model]:
        """Get all models uploaded by a specific user"""
        return self.db.query(Model).filter(Model.uploader_id == uploader_id).all()

    def get_all_models(self, skip: int = 0, limit: int = 100) -> List[Model]:
        """Get all models with pagination"""
        return self.db.query(Model).offset(skip).limit(limit).all()

    def update_model(self, model_id: int, model_data: Dict) -> Optional[Model]:
        """Update model information"""
        db_model = self.get_model_by_id(model_id)
        if not db_model:
            return None

        for field, value in model_data.items():
            if value is not None:
                setattr(db_model, field, value)

        self.db.commit()
        # self.db.refresh(db_model)
        return db_model

    def delete_model(self, model_id: int) -> bool:
        """Delete model from database"""
        db_model = self.get_model_by_id(model_id)
        if not db_model:
            return False

        self.db.delete(db_model)
        self.db.commit()
        return True

    def add_model_metadata(self, model_id: int, metadata: Dict[str, str]) -> bool:
        """Add metadata key-value pairs for a model"""
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
