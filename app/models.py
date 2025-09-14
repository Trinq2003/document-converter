"""
Pydantic models for API request/response schemas
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from pathlib import Path
from enum import Enum


class ConversionStatus(str, Enum):
    """Conversion status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionRequest(BaseModel):
    """Request model for document conversion"""
    filename: str = Field(..., description="Name of the DOCX file to convert")
    preserve_images: bool = Field(default=True, description="Whether to preserve images in output")
    include_toc: bool = Field(default=True, description="Whether to include table of contents")
    math_engine: str = Field(default="mathml", description="Math rendering engine")
    cleanup_temp: bool = Field(default=True, description="Whether to cleanup temporary files")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        if not v.endswith('.docx'):
            raise ValueError('Filename must have .docx extension')
        return v
    
    @field_validator('math_engine')
    @classmethod
    def validate_math_engine(cls, v):
        allowed_engines = ['mathml', 'latex', 'mathjax']
        if v not in allowed_engines:
            raise ValueError(f'Math engine must be one of: {allowed_engines}')
        return v


class ConversionStep(BaseModel):
    """Model for individual conversion step results"""
    step_name: str = Field(..., description="Name of the conversion step")
    success: bool = Field(..., description="Whether the step was successful")
    duration_ms: Optional[int] = Field(None, description="Step duration in milliseconds")
    details: Optional[Dict[str, Any]] = Field(None, description="Step-specific details")
    error: Optional[str] = Field(None, description="Error message if step failed")


class ImageInfo(BaseModel):
    """Model for image information"""
    src: str = Field(..., description="Image source path")
    alt: str = Field(default="", description="Image alt text")
    title: str = Field(default="", description="Image title")
    filename: str = Field(..., description="Image filename")


class ConversionResult(BaseModel):
    """Response model for document conversion"""
    task_id: str = Field(..., description="Unique task identifier")
    status: ConversionStatus = Field(..., description="Current conversion status")
    filename: str = Field(..., description="Original filename")
    output_files: Dict[str, str] = Field(default_factory=dict, description="Generated output files")
    statistics: Dict[str, int] = Field(default_factory=dict, description="Conversion statistics")
    steps: List[ConversionStep] = Field(default_factory=list, description="Conversion steps")
    images: List[ImageInfo] = Field(default_factory=list, description="Extracted images")
    error: Optional[str] = Field(None, description="Error message if conversion failed")
    created_at: str = Field(..., description="Task creation timestamp")
    completed_at: Optional[str] = Field(None, description="Task completion timestamp")


class BatchConversionRequest(BaseModel):
    """Request model for batch document conversion"""
    filenames: List[str] = Field(..., description="List of DOCX filenames to convert")
    preserve_images: bool = Field(default=True, description="Whether to preserve images in output")
    include_toc: bool = Field(default=True, description="Whether to include table of contents")
    math_engine: str = Field(default="mathml", description="Math rendering engine")
    cleanup_temp: bool = Field(default=True, description="Whether to cleanup temporary files")
    
    @field_validator('filenames')
    @classmethod
    def validate_filenames(cls, v):
        if not v:
            raise ValueError('At least one filename must be provided')
        for filename in v:
            if not filename.endswith('.docx'):
                raise ValueError(f'All filenames must have .docx extension: {filename}')
        return v


class BatchConversionResult(BaseModel):
    """Response model for batch document conversion"""
    batch_id: str = Field(..., description="Unique batch identifier")
    total_files: int = Field(..., description="Total number of files to process")
    completed_files: int = Field(default=0, description="Number of completed files")
    failed_files: int = Field(default=0, description="Number of failed files")
    results: List[ConversionResult] = Field(default_factory=list, description="Individual conversion results")
    status: ConversionStatus = Field(..., description="Overall batch status")
    created_at: str = Field(..., description="Batch creation timestamp")
    completed_at: Optional[str] = Field(None, description="Batch completion timestamp")


class HealthCheck(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Health check timestamp")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")
