# crud/repositories/model_repository.py# crud/repositories/model_repository.py

from sqlalchemy.orm import Sessionfrom sqlalchemy.orm import Session

from models import Model, ModelMetadatafrom models import Model, ModelMetadata

from schemas import ModelUpdatefrom schemas import ModelUpdate

from typing import List, Optional, Dictfrom typing import List, Optional, Dict



class CRUDModelRepository:

    """Repository for CRUD operations on models (Read, Update, Delete only)"""class CRUDModelRepository:

    def __init__(self, db: Session):    """Repository for CRUD operations on models (Read, Update, Delete only)"""

        self.db = db

        def __init__(self, db: Session):

    def get_model_by_id(self, model_id: int) -> Optional[Model]:        self.db = db

        """Get model by ID"""

        return self.db.query(Model).filter(Model.id == model_id).first()    def get_model_by_id(self, model_id: int) -> Optional[Model]:

            """Get model by ID"""

    def get_models_by_uploader(self, uploader_id: int) -> List[Model]:        return self.db.query(Model).filter(Model.id == model_id).first()

        """Get all models uploaded by a specific user"""

        return self.db.query(Model).filter(Model.uploader_id == uploader_id).all()    def get_models_by_uploader(self, uploader_id: int) -> List[Model]:

            """Get all models uploaded by a specific user"""

    def get_all_models(self, skip: int = 0, limit: int = 100) -> List[Model]:        return self.db.query(Model).filter(Model.uploader_id == uploader_id).all()

        """Get all models with pagination"""

        return self.db.query(Model).offset(skip).limit(limit).all()    def get_all_models(self, skip: int = 0, limit: int = 100) -> List[Model]:

            """Get all models with pagination"""

    def update_model(self, model_id: int, model_data: Dict) -> Optional[Model]:        return self.db.query(Model).offset(skip).limit(limit).all()

        """Update model information"""

        db_model = self.get_model_by_id(model_id)    def update_model(self, model_id: int, model_data: Dict) -> Optional[Model]:

        if not db_model:        """Update model information"""

            return None        db_model = self.get_model_by_id(model_id)

                if not db_model:

        for field, value in model_data.items():            return None

            if value is not None:

                setattr(db_model, field, value)        for field, value in model_data.items():

                    if value is not None:

        self.db.commit()                setattr(db_model, field, value)

        return db_model

            self.db.commit()

    def delete_model(self, model_id: int) -> bool:        return db_model

        """Delete model from database"""

        db_model = self.get_model_by_id(model_id)    def delete_model(self, model_id: int) -> bool:

        if not db_model:        """Delete model from database"""

            return False        db_model = self.get_model_by_id(model_id)

                if not db_model:

        self.db.delete(db_model)            return False

        self.db.commit()

        return True        self.db.delete(db_model)

        self.db.commit()
        return True
