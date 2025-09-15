"""
FastAPI route handlers
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Dict, Any
import asyncio
import uuid
import shutil
from datetime import datetime
from pathlib import Path

from app.api.dependencies import (
    get_document_converter, 
    validate_file_upload, 
    save_uploaded_file,
    validate_conversion_request,
    validate_batch_conversion_request
)
from app.core.document_converter import DocumentConverter
from app.core.logger import logger
from app.config import settings, dir_manager
from app.models import (
    ConversionRequest, 
    ConversionResult, 
    BatchConversionRequest,
    BatchConversionResult,
    HealthCheck,
    ErrorResponse
)

# Create router
router = APIRouter()

# In-memory task storage (in production, use Redis or database)
active_tasks: Dict[str, Dict[str, Any]] = {}


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    try:
        # Try to check dependencies without dependency injection
        converter = DocumentConverter()
        dependencies = converter.check_dependencies()
        status = "healthy" if all(dependencies.values()) else "unhealthy"
    except Exception as e:
        logger.warning(f"Health check failed to initialize converter: {e}")
        dependencies = {"error": str(e)}
        status = "unhealthy"
    
    return HealthCheck(
        status=status,
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies
    )


@router.get("/health/simple")
async def simple_health_check():
    """Simple health check endpoint without dependencies"""
    return {
        "status": "healthy",
        "message": "Service is running",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/documents", response_model=List[str])
async def list_documents(converter: DocumentConverter = Depends(get_document_converter)):
    """List available DOCX documents"""
    try:
        documents = converter.get_available_documents()
        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.post("/upload", response_model=Dict[str, str])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = Depends(validate_file_upload)
):
    """Upload a DOCX document"""
    try:
        filename = save_uploaded_file(file)
        return {
            "message": "File uploaded successfully",
            "filename": filename,
            "status": "uploaded"
        }
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.post("/convert", response_model=ConversionResult)
async def convert_document(
    request: ConversionRequest = Depends(validate_conversion_request),
    converter: DocumentConverter = Depends(get_document_converter)
):
    """Convert a single DOCX document to Markdown"""
    try:
        result = converter.process_single_document(
            docx_filename=request.filename,
            preserve_images=request.preserve_images,
            include_toc=request.include_toc,
            math_engine=request.math_engine,
            cleanup_temp=request.cleanup_temp
        )
        
        return ConversionResult(**result)
        
    except Exception as e:
        logger.error(f"Error converting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert document")


@router.post("/convert/batch", response_model=BatchConversionResult)
async def convert_documents_batch(
    request: BatchConversionRequest = Depends(validate_batch_conversion_request),
    converter: DocumentConverter = Depends(get_document_converter)
):
    """Convert multiple DOCX documents to Markdown"""
    try:
        result = converter.process_batch_documents(
            docx_filenames=request.filenames,
            preserve_images=request.preserve_images,
            include_toc=request.include_toc,
            math_engine=request.math_engine,
            cleanup_temp=request.cleanup_temp
        )
        
        return BatchConversionResult(**result)
        
    except Exception as e:
        logger.error(f"Error converting documents batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert documents")


@router.post("/convert/async", response_model=Dict[str, str])
async def convert_document_async(
    request: ConversionRequest = Depends(validate_conversion_request),
    converter: DocumentConverter = Depends(get_document_converter)
):
    """Convert a document asynchronously (returns task ID)"""
    task_id = str(uuid.uuid4())
    
    # Store task info
    active_tasks[task_id] = {
        "status": "processing",
        "filename": request.filename,
        "created_at": datetime.utcnow().isoformat(),
        "result": None
    }
    
    # Start background task
    asyncio.create_task(
        process_document_async(task_id, request, converter)
    )
    
    return {
        "task_id": task_id,
        "status": "processing",
        "message": "Document conversion started"
    }


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_task_status(task_id: str):
    """Get status of an async conversion task"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return active_tasks[task_id]


@router.get("/download/{basename}/{filename}")
async def download_file(basename: str, filename: str):
    """Download converted file from single folder structure"""
    try:
        # Both files are now in the same folder: data/md/{basename}/
        file_path = dir_manager.md_dir / basename / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.delete("/documents/{basename}")
async def delete_document(basename: str):
    """Delete a document and its converted folders"""
    try:
        # Delete DOCX file
        docx_path = dir_manager.docx_dir / f"{basename}.docx"
        if docx_path.exists():
            docx_path.unlink()

        # Delete entire document folder (contains both HTML, MD, and images)
        document_folder = dir_manager.md_dir / basename
        if document_folder.exists():
            shutil.rmtree(document_folder)

        return {"message": "Document deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


async def process_document_async(
    task_id: str, 
    request: ConversionRequest, 
    converter: DocumentConverter
):
    """Background task for async document processing"""
    try:
        result = converter.process_single_document(
            docx_filename=request.filename,
            preserve_images=request.preserve_images,
            include_toc=request.include_toc,
            math_engine=request.math_engine,
            cleanup_temp=request.cleanup_temp
        )
        
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["result"] = result
        active_tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Error in async document processing: {e}")
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error"] = str(e)
        active_tasks[task_id]["completed_at"] = datetime.utcnow().isoformat()
