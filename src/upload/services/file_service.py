# services/file_service.py
import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from typing import Optional, Tuple

class FileStorageService:
    def __init__(self, upload_dir: str = "uploads/models"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
    
    async def save_upload_file(self, file: UploadFile) -> Tuple[str, int]:
        """Save uploaded file and return (file_path, file_size)"""
        try:
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1] if file.filename else '.zip'
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Save file and calculate size
            file_size = 0
            with open(file_path, "wb") as buffer:
                while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                    file_size += len(content)
                    buffer.write(content)
            
            return file_path, file_size
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    def get_file_size(self, file_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            return None
