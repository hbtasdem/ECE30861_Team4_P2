# repositories/model_repository.py# repositories/model_repository.py

from sqlalchemy.orm import Sessionfrom sqlalchemy.orm import Session

from models import Model, ModelMetadatafrom models import Model, ModelMetadata

from schemas import ModelCreatefrom schemas import ModelCreate

from typing import Dictfrom typing import Dict



class ModelRepository:

    """Repository for upload operations (Create only)"""class ModelRepository:

    def __init__(self, db: Session):    """Repository for upload operations (Create only)"""

        self.db = db

        def __init__(self, db: Session):

    def create_model(self, model_data: ModelCreate, file_path: str, file_size: int, uploader_id: int) -> Model:        self.db = db

        """Create a new model record in database"""

        db_model = Model(    def create_model(

            name=model_data.name,        self, model_data: ModelCreate, file_path: str, file_size: int, uploader_id: int

            description=model_data.description,    ) -> Model:

            version=model_data.version,        """Create a new model record in database"""

            file_path=file_path,        db_model = Model(

            file_size=file_size,            name=model_data.name,

            uploader_id=uploader_id,            description=model_data.description,

            is_sensitive=model_data.is_sensitive            version=model_data.version,

        )            file_path=file_path,

                    file_size=file_size,

        self.db.add(db_model)            uploader_id=uploader_id,

        self.db.commit()            is_sensitive=model_data.is_sensitive,

        # Note: refresh() causes issues in testing, so we rely on the commit to populate id/timestamps        )

        # self.db.refresh(db_model)

        return db_model        self.db.add(db_model)

            self.db.commit()

    def add_model_metadata(self, model_id: int, metadata: Dict[str, str]) -> bool:        # Note: refresh() causes issues in testing, 

        """Add metadata key-value pairs for a model"""        # so we rely on the commit to populate id/timestamps

        try:        # self.db.refresh(db_model)

            for key, value in metadata.items():        return db_model

                db_metadata = ModelMetadata(

                    model_id=model_id,    def add_model_metadata(self, model_id: int, metadata: Dict[str, str]) -> bool:

                    key=key,        """Add metadata key-value pairs for a model"""

                    value=str(value)        try:

                )            for key, value in metadata.items():

                self.db.add(db_metadata)                db_metadata = ModelMetadata(

            self.db.commit()                    model_id=model_id, key=key, value=str(value)

            return True                )

        except Exception:                self.db.add(db_metadata)

            self.db.rollback()            self.db.commit()

            return False            return True

        except Exception:
            self.db.rollback()
            return False
