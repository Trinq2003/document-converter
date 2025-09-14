"""
FastAPI dependencies for dependency injection
"""

from fastapi import Depends, HTTPException, UploadFile, File
from typing import List
from pathlib import Path
import shutil
import uuid

from app.core.document_converter import DocumentConverter
from app.core.logger import logger
from app.config import settings, dir_manager
from app.models import ConversionRequest, BatchConversionRequest


def get_document_converter() -> DocumentConverter:
    """Dependency to get DocumentConverter instance"""
    return DocumentConverter()


def validate_file_upload(file: UploadFile = File(...)) -> UploadFile:
    """Validate uploaded file"""
    # Check file extension
    if not file.filename or not file.filename.endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are allowed"
        )
    
    # Check file size
    if hasattr(file, 'size') and file.size and file.size > settings.max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds maximum allowed size of {settings.max_file_size} bytes"
        )
    
    return file


def save_uploaded_file(file: UploadFile, filename: str = None) -> str:
    """Save uploaded file to docx directory"""
    if not filename:
        filename = file.filename
    
    # Ensure filename is safe
    safe_filename = Path(filename).name
    if not safe_filename.endswith('.docx'):
        safe_filename += '.docx'
    
    # Create unique filename if file already exists
    file_path = dir_manager.docx_dir / safe_filename
    counter = 1
    while file_path.exists():
        stem = Path(safe_filename).stem
        suffix = Path(safe_filename).suffix
        file_path = dir_manager.docx_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded file: {file_path}")
        return str(file_path.relative_to(dir_manager.docx_dir))
        
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {str(e)}"
        )


def validate_conversion_request(request: ConversionRequest) -> ConversionRequest:
    """Validate conversion request"""
    # Check if file exists
    file_path = dir_manager.docx_dir / request.filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {request.filename}"
        )
    
    return request


def validate_batch_conversion_request(request: BatchConversionRequest) -> BatchConversionRequest:
    """Validate batch conversion request"""
    # Check if all files exist
    missing_files = []
    for filename in request.filenames:
        file_path = dir_manager.docx_dir / filename
        if not file_path.exists():
            missing_files.append(filename)
    
    if missing_files:
        raise HTTPException(
            status_code=404,
            detail=f"Files not found: {', '.join(missing_files)}"
        )
    
    return request
