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
from app.models import ConversionRequest, BatchConversionRequest, WatermarkRequest


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
    # Check if path exists in docx directory
    full_path = dir_manager.docx_dir / request.relative_path

    if not full_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Path not found: {request.relative_path}"
        )

    # Check if it's a file, ensure it has .docx extension
    if full_path.is_file() and not full_path.suffix.lower() == '.docx':
        raise HTTPException(
            status_code=400,
            detail=f"File must have .docx extension: {request.relative_path}"
        )

    # If it's a directory, check if it contains any .docx files
    if full_path.is_dir():
        docx_files = list(full_path.glob("**/*.docx"))
        if not docx_files:
            raise HTTPException(
                status_code=400,
                detail=f"No .docx files found in directory: {request.relative_path}"
            )

    return request


def validate_batch_conversion_request(request: BatchConversionRequest) -> BatchConversionRequest:
    """Validate batch conversion request"""
    # Check if all paths exist
    missing_paths = []
    invalid_paths = []

    for relative_path in request.relative_paths:
        full_path = dir_manager.docx_dir / relative_path

        if not full_path.exists():
            missing_paths.append(relative_path)
            continue

        # Check if it's a file, ensure it has .docx extension
        if full_path.is_file() and not full_path.suffix.lower() == '.docx':
            invalid_paths.append(relative_path)
            continue

        # If it's a directory, check if it contains any .docx files
        if full_path.is_dir():
            docx_files = list(full_path.glob("**/*.docx"))
            if not docx_files:
                invalid_paths.append(relative_path)

    error_messages = []
    if missing_paths:
        error_messages.append(f"Paths not found: {', '.join(missing_paths)}")
    if invalid_paths:
        error_messages.append(f"Invalid paths (no .docx files): {', '.join(invalid_paths)}")

    if error_messages:
        raise HTTPException(
            status_code=400,
            detail="; ".join(error_messages)
        )

    return request


def validate_watermark_request(request: WatermarkRequest) -> WatermarkRequest:
    """Validate watermark request"""
    # Check if path exists in docx directory
    full_path = dir_manager.docx_dir / request.relative_path

    if not full_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Path not found: {request.relative_path}"
        )

    # Check if it's a file, ensure it has .docx extension
    if full_path.is_file() and not full_path.suffix.lower() == '.docx':
        raise HTTPException(
            status_code=400,
            detail=f"File must have .docx extension: {request.relative_path}"
        )

    # If it's a directory, check if it contains any .docx files
    if full_path.is_dir():
        docx_files = list(full_path.glob("**/*.docx"))
        if not docx_files:
            raise HTTPException(
                status_code=400,
                detail=f"No .docx files found in directory: {request.relative_path}"
            )

    return request
