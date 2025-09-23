"""
FastAPI route handlers
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Dict, Any, Union
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
    validate_batch_conversion_request,
    validate_watermark_request
)
from app.core.document_converter import DocumentConverter
from app.core.logger import logger
from app.config import settings, dir_manager
from app.watermark import add_watermarks_to_docx
from app.models import (
    ConversionRequest,
    ConversionResult,
    BatchConversionRequest,
    BatchConversionResult,
    WatermarkRequest,
    WatermarkResult,
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


@router.post("/convert", response_model=Union[ConversionResult, BatchConversionResult])
async def convert_document(
    request: ConversionRequest = Depends(validate_conversion_request),
    converter: DocumentConverter = Depends(get_document_converter)
):
    """Convert DOCX document(s) to Markdown - accepts single file or folder path"""
    try:
        # Get input path
        input_path = dir_manager.docx_dir / request.relative_path

        # Collect all docx files to process
        docx_files = []
        if input_path.is_file():
            docx_files = [input_path]
        else:
            # It's a directory, find all .docx files recursively
            docx_files = list(input_path.glob("**/*.docx"))

        # Get relative filenames for processing
        docx_filenames = [str(f.relative_to(dir_manager.docx_dir)) for f in docx_files]

        if len(docx_files) == 1:
            # Single file - use single document processing
            result = converter.process_single_document(
                docx_filename=docx_filenames[0],
                preserve_images=request.preserve_images,
                include_toc=request.include_toc,
                math_engine=request.math_engine,
                cleanup_temp=request.cleanup_temp
            )
            return ConversionResult(**result)
        else:
            # Multiple files - use batch processing
            result = converter.process_batch_documents(
                docx_filenames=docx_filenames,
                preserve_images=request.preserve_images,
                include_toc=request.include_toc,
                math_engine=request.math_engine,
                cleanup_temp=request.cleanup_temp
            )
            return BatchConversionResult(**result)

    except Exception as e:
        logger.error(f"Error converting document: {e}")
        raise HTTPException(status_code=500, detail="Failed to convert document")


@router.post("/convert/batch", response_model=BatchConversionResult)
async def convert_documents_batch(
    request: BatchConversionRequest = Depends(validate_batch_conversion_request),
    converter: DocumentConverter = Depends(get_document_converter)
):
    """Convert multiple DOCX documents/folders to Markdown"""
    try:
        # Collect all docx files from all relative paths
        all_docx_files = []

        for relative_path in request.relative_paths:
            input_path = dir_manager.docx_dir / relative_path

            if input_path.is_file():
                all_docx_files.append(input_path)
            else:
                # It's a directory, find all .docx files recursively
                docx_files = list(input_path.glob("**/*.docx"))
                all_docx_files.extend(docx_files)

        # Get relative filenames for processing
        docx_filenames = [str(f.relative_to(dir_manager.docx_dir)) for f in all_docx_files]

        result = converter.process_batch_documents(
            docx_filenames=docx_filenames,
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
        "relative_path": request.relative_path,
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


@router.post("/watermark", response_model=WatermarkResult)
async def add_watermark(
    request: WatermarkRequest = Depends(validate_watermark_request)
):
    """Add watermarks to DOCX documents"""
    try:
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        # Get input path
        input_path = dir_manager.docx_dir / request.relative_path

        # Collect all docx files to process
        docx_files = []
        if input_path.is_file():
            docx_files = [input_path]
        else:
            # It's a directory, find all .docx files recursively
            docx_files = list(input_path.glob("**/*.docx"))

        total_files = len(docx_files)
        success_count = 0
        failed_files = []
        output_files = []

        for docx_file in docx_files:
            try:
                # Calculate relative path from docx directory
                relative_path = docx_file.relative_to(dir_manager.docx_dir)

                # Create output path in watermark directory
                if request.preserve_structure:
                    output_file = dir_manager.watermark_dir / relative_path
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                else:
                    # Flatten structure - just use filename
                    output_file = dir_manager.watermark_dir / docx_file.name

                # Add watermark
                add_watermarks_to_docx(str(docx_file), str(output_file))

                output_files.append(str(relative_path))
                success_count += 1
                logger.info(f"Successfully watermarked: {relative_path}")

            except Exception as e:
                failed_files.append(str(docx_file.relative_to(dir_manager.docx_dir)))
                logger.error(f"Failed to watermark {docx_file}: {e}")

        status = "completed" if success_count > 0 else "failed"
        error = None
        if failed_files and success_count == 0:
            error = "All files failed to watermark"
        elif failed_files:
            error = f"Some files failed: {', '.join(failed_files)}"

        result = WatermarkResult(
            task_id=task_id,
            status=status,
            input_path=request.relative_path,
            output_files=output_files,
            total_files=total_files,
            success_count=success_count,
            failed_files=failed_files,
            error=error,
            created_at=created_at,
            completed_at=datetime.utcnow().isoformat()
        )

        return result

    except Exception as e:
        logger.error(f"Error in watermark operation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add watermarks: {str(e)}")


async def process_document_async(
    task_id: str,
    request: ConversionRequest,
    converter: DocumentConverter
):
    """Background task for async document processing"""
    try:
        # Get input path
        input_path = dir_manager.docx_dir / request.relative_path

        # Collect all docx files to process
        docx_files = []
        if input_path.is_file():
            docx_files = [input_path]
        else:
            # It's a directory, find all .docx files recursively
            docx_files = list(input_path.glob("**/*.docx"))

        # Get relative filenames for processing
        docx_filenames = [str(f.relative_to(dir_manager.docx_dir)) for f in docx_files]

        if len(docx_files) == 1:
            # Single file - use single document processing
            result = converter.process_single_document(
                docx_filename=docx_filenames[0],
                preserve_images=request.preserve_images,
                include_toc=request.include_toc,
                math_engine=request.math_engine,
                cleanup_temp=request.cleanup_temp
            )
        else:
            # Multiple files - use batch processing
            result = converter.process_batch_documents(
                docx_filenames=docx_filenames,
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
