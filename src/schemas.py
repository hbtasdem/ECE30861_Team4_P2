# schemas.py# schemas.py

from pydantic import BaseModel, ConfigDictfrom pydantic import BaseModel, ConfigDict

from typing import Optionalfrom typing import Optional

from datetime import datetimefrom datetime import datetime



# Request/Response schemas (Pydantic)# Request/Response schemas (Pydantic)



class ModelCreate(BaseModel):

    name: strclass ModelCreate(BaseModel):

    description: Optional[str] = None    name: str

    version: str = "1.0.0"    description: Optional[str] = None

    is_sensitive: bool = False    version: str = "1.0.0"

    is_sensitive: bool = False

class ModelUpdate(BaseModel):

    name: Optional[str] = None

    description: Optional[str] = Noneclass ModelUpdate(BaseModel):

    version: Optional[str] = None    name: Optional[str] = None

    is_sensitive: Optional[bool] = None    description: Optional[str] = None

    version: Optional[str] = None

class ModelResponse(BaseModel):    is_sensitive: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

    

    id: intclass ModelResponse(BaseModel):

    name: str    model_config = ConfigDict(from_attributes=True)

    description: Optional[str]

    version: str    id: int

    file_path: str    name: str

    file_size: int    description: Optional[str]

    uploader_id: int    version: str

    is_sensitive: bool    file_path: str

    created_at: datetime    file_size: int

    updated_at: datetime    uploader_id: int

    is_sensitive: bool

class UploadResponse(BaseModel):    created_at: datetime

    message: str    updated_at: datetime

    model_id: int

    file_path: str

    file_size: intclass UploadResponse(BaseModel):

    message: str
    model_id: int
    file_path: str
    file_size: int
