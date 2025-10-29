# crud/repositories/model_repository.py
from sqlalchemy.orm import Session
from models import Model, ModelMetadata
from schemas import ModelUpdate
from typing import List, Optional, Dict

class CRUDModelRepository:
    """Repository for CRUD operations on models (Read, Update, Delete only)"""
    def __init__(self, db: Session):
        self.db = db
    
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
        return db_model
    
    def delete_model(self, model_id: int) -> bool:
        """Delete model from database"""
        db_model = self.get_model_by_id(model_id)
        if not db_model:
            return False
        
        self.db.delete(db_model)
        self.db.commit()
        return True
