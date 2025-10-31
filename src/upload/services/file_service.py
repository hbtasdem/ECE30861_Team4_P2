# services/file_service.py# services/file_service.py

import osimport os

import uuidimport uuid

import shutilimport shutil

from fastapi import UploadFile, HTTPExceptionfrom fastapi import UploadFile, HTTPException

from typing import Optional, Tuplefrom typing import Optional, Tuple



class FileStorageService:

    def __init__(self, upload_dir: str = "uploads/models"):class FileStorageService:

        self.upload_dir = upload_dir    def __init__(self, upload_dir: str = "uploads/models"):

        os.makedirs(upload_dir, exist_ok=True)        self.upload_dir = upload_dir

            os.makedirs(upload_dir, exist_ok=True)

    async def save_upload_file(self, file: UploadFile) -> Tuple[str, int]:

        """Save uploaded file and return (file_path, file_size)"""    async def save_upload_file(self, file: UploadFile) -> Tuple[str, int]:

        try:        """Save uploaded file and return (file_path, file_size)"""

            # Generate unique filename        try:

            file_extension = os.path.splitext(file.filename)[1] if file.filename else '.zip'            # Generate unique filename

            unique_filename = f"{uuid.uuid4()}{file_extension}"            file_extension = (

            file_path = os.path.join(self.upload_dir, unique_filename)                os.path.splitext(file.filename)[1] if file.filename else ".zip"

                        )

            # Save file and calculate size            unique_filename = f"{uuid.uuid4()}{file_extension}"

            file_size = 0            file_path = os.path.join(self.upload_dir, unique_filename)

            with open(file_path, "wb") as buffer:

                while content := await file.read(1024 * 1024):  # Read in 1MB chunks            # Save file and calculate size

                    file_size += len(content)            file_size = 0

                    buffer.write(content)            with open(file_path, "wb") as buffer:

                            while content := await file.read(1024 * 1024):  # Read in 1MB chunks

            return file_path, file_size                    file_size += len(content)

                                buffer.write(content)

        except Exception as e:

            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")            return file_path, file_size

    

    def delete_file(self, file_path: str) -> bool:        except Exception as e:

        """Delete file from storage"""            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

        try:

            if os.path.exists(file_path):    def delete_file(self, file_path: str) -> bool:

                os.remove(file_path)        """Delete file from storage"""

                return True        try:

            return False            if os.path.exists(file_path):

        except Exception:                os.remove(file_path)

            return False                return True

                return False

    def get_file_size(self, file_path: str) -> Optional[int]:        except Exception:

        """Get file size in bytes"""            return False

        try:

            return os.path.getsize(file_path)    def get_file_size(self, file_path: str) -> Optional[int]:

        except OSError:        """Get file size in bytes"""

            return None        try:

            return os.path.getsize(file_path)
        except OSError:
            return None
