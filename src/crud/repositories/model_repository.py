# crud/repositories/model_repository.py

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.api_schemas import ModelUpdate
from src.models import Model, ModelMetadata


class CRUDModelRepository:
    """Repository for CRUD operations on models (Read, Update, Delete only)"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_model_by_id(self, model_id: int) -> Optional[Model]:
        """Get model by ID"""
        result = self.db.query(Model).filter(Model.id == model_id).first()
        if result is None:
            return None
        return result

    def get_models_by_uploader(self, uploader_id: int) -> List[Model]:
        """Get all models uploaded by a specific user"""
        result: List[Model] = self.db.query(Model).filter(Model.uploader_id == uploader_id).all()
        return result

    def get_all_models(self, skip: int = 0, limit: int = 100) -> List[Model]:
        """Get all models with pagination"""
        result: List[Model] = self.db.query(Model).offset(skip).limit(limit).all()
        return result

    def update_model(self, model_id: int, model_data: Dict[str, Any]) -> Optional[Model]:
        """Update model information"""
        db_model = self.get_model_by_id(model_id)
        if not db_model:
            return None

        for field, value in model_data.items():
            if value is not None:
                setattr(db_model, field, value)

        self.db.commit()
        return db_model

    def delete_model(self, model_id: int) -> bool:
        """Delete model from database"""
        db_model = self.get_model_by_id(model_id)
        if not db_model:
            return False

        self.db.delete(db_model)
        self.db.commit()
        return True
