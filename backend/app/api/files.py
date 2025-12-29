import os
import uuid
import shutil
import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from app.middleware import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Local storage for uploads
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str
    size: int

@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload a document or image to be processed by Manas.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "application/pdf", "text/plain"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file.content_type} not supported. Allowed: {', '.join(allowed_types)}"
        )

    # Generate unique ID
    file_id = str(uuid.uuid4())
    extension = os.path.splitext(file.filename)[1]
    save_filename = f"{file_id}{extension}"
    file_path = os.path.join(UPLOAD_DIR, save_filename)

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        logger.info(f"File uploaded: {file.filename} -> {save_filename} ({file_size} bytes)")

        return FileUploadResponse(
            file_id=file_id,
            filename=file.filename,
            content_type=file.content_type,
            size=file_size
        )
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail="Could not save file")

def get_file_path(file_id: str) -> str:
    """Helper to find the actual file path for a given file_id"""
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            return os.path.join(UPLOAD_DIR, filename)
    return None

def delete_file(file_id: str):
    """Helper to delete a file by its ID"""
    path = get_file_path(file_id)
    if path and os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"🗑️ Deleted file after processing: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
    return False
