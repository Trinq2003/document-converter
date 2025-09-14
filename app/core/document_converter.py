"""
Main document converter orchestrating the conversion pipeline
"""

import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from app.core.logger import logger
from app.core.pandoc_converter import PandocConverter
from app.core.html_processor import HTMLProcessor
from app.config import settings, dir_manager
from app.models import ConversionStatus, ConversionStep, ImageInfo


class DocumentConverter:
    """
    Enhanced document converter that handles DOCX -> HTML -> Markdown conversion
    with special handling for tables, math equations, and images
    """
    
    def __init__(self):
        self.pandoc_converter = PandocConverter()
        self.html_processor = HTMLProcessor()
        self.dir_manager = dir_manager
        
        # Ensure directories exist
        self.dir_manager.create_directories()
        
        logger.info(f"DocumentConverter initialized with base directory: {settings.base_dir}")
    
    def process_single_document(
        self, 
        docx_filename: str,
        task_id: Optional[str] = None,
        preserve_images: bool = True,
        include_toc: bool = True,
        math_engine: Optional[str] = None,
        cleanup_temp: bool = True
    ) -> Dict:
        """
        Process a single document through the complete pipeline
        
        Args:
            docx_filename: DOCX filename (relative to docx_dir)
            task_id: Optional task identifier
            preserve_images: Whether to preserve images
            include_toc: Whether to include table of contents
            math_engine: Math rendering engine
            cleanup_temp: Whether to cleanup temporary files
            
        Returns:
            Dict: Processing result with all statistics
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        logger.info(f"Processing document: {docx_filename} (Task ID: {task_id})")
        
        # Setup paths
        docx_path = self.dir_manager.docx_dir / docx_filename
        html_path = self.dir_manager.html_dir / f"{Path(docx_filename).stem}.html"
        md_path = self.dir_manager.md_dir / f"{Path(docx_filename).stem}.md"
        
        result = {
            'task_id': task_id,
            'status': ConversionStatus.PROCESSING,
            'docx_file': docx_filename,
            'docx_path': str(docx_path),
            'html_path': str(html_path),
            'md_path': str(md_path),
            'steps': [],
            'images': [],
            'statistics': {},
            'created_at': datetime.utcnow().isoformat(),
            'completed_at': None
        }
        
        try:
            # Step 1: DOCX to HTML
            logger.info(f"Step 1: Converting DOCX to HTML - {docx_filename}")
            step_start = time.time()
            
            docx_result = self.pandoc_converter.convert_docx_to_html(
                docx_path, html_path, 
                include_toc=include_toc,
                math_engine=math_engine
            )
            
            step_duration = int((time.time() - step_start) * 1000)
            step = ConversionStep(
                step_name="docx_to_html",
                success=docx_result['success'],
                duration_ms=step_duration,
                details=docx_result if docx_result['success'] else None,
                error=docx_result.get('error') if not docx_result['success'] else None
            )
            result['steps'].append(step)
            
            if not docx_result['success']:
                result['status'] = ConversionStatus.FAILED
                result['error'] = f"DOCX to HTML conversion failed: {docx_result['error']}"
                result['completed_at'] = datetime.utcnow().isoformat()
                return result
            
            # Step 2: HTML to Markdown
            logger.info(f"Step 2: Converting HTML to Markdown - {docx_filename}")
            step_start = time.time()
            
            md_result = self.html_processor.convert_html_to_markdown_enhanced(
                html_path, md_path, 
                images_folder=docx_result.get('images_folder', 'images')
            )
            
            step_duration = int((time.time() - step_start) * 1000)
            step = ConversionStep(
                step_name="html_to_markdown",
                success=md_result['success'],
                duration_ms=step_duration,
                details=md_result if md_result['success'] else None,
                error=md_result.get('error') if not md_result['success'] else None
            )
            result['steps'].append(step)
            
            if not md_result['success']:
                result['status'] = ConversionStatus.FAILED
                result['error'] = f"HTML to Markdown conversion failed: {md_result['error']}"
                result['completed_at'] = datetime.utcnow().isoformat()
                return result
            
            # Extract images information
            if preserve_images and 'images' in md_result:
                result['images'] = [
                    ImageInfo(**img) for img in md_result.get('images', [])
                ]
            
            # Compile statistics
            result['statistics'] = {
                'tables_count': md_result.get('tables_count', 0),
                'math_count': md_result.get('math_count', 0),
                'images_count': md_result.get('images_count', 0),
                'output_length': md_result.get('output_length', 0),
                'total_duration_ms': sum(step.duration_ms or 0 for step in result['steps'])
            }
            
            # Set output files
            result['output_files'] = {
                'html': str(html_path),
                'markdown': str(md_path)
            }
            
            # Cleanup temporary files if requested
            if cleanup_temp and settings.cleanup_temp_files:
                self._cleanup_temp_files(html_path)
            
            # Success
            result['status'] = ConversionStatus.COMPLETED
            result['completed_at'] = datetime.utcnow().isoformat()
            logger.info(f"Successfully processed document: {docx_filename} (Task ID: {task_id})")
            
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error processing {docx_filename}: {str(e)}"
            logger.error(error_msg)
            result['status'] = ConversionStatus.FAILED
            result['error'] = error_msg
            result['completed_at'] = datetime.utcnow().isoformat()
            return result
    
    def process_batch_documents(
        self, 
        docx_filenames: List[str],
        batch_id: Optional[str] = None,
        preserve_images: bool = True,
        include_toc: bool = True,
        math_engine: Optional[str] = None,
        cleanup_temp: bool = True
    ) -> Dict:
        """
        Process multiple documents through the complete pipeline
        
        Args:
            docx_filenames: List of DOCX filenames
            batch_id: Optional batch identifier
            preserve_images: Whether to preserve images
            include_toc: Whether to include table of contents
            math_engine: Math rendering engine
            cleanup_temp: Whether to cleanup temporary files
            
        Returns:
            Dict: Batch processing result
        """
        if not batch_id:
            batch_id = str(uuid.uuid4())
        
        logger.info(f"Starting batch processing: {len(docx_filenames)} documents (Batch ID: {batch_id})")
        
        batch_result = {
            'batch_id': batch_id,
            'total_files': len(docx_filenames),
            'completed_files': 0,
            'failed_files': 0,
            'results': [],
            'status': ConversionStatus.PROCESSING,
            'created_at': datetime.utcnow().isoformat(),
            'completed_at': None
        }
        
        for docx_filename in docx_filenames:
            try:
                result = self.process_single_document(
                    docx_filename=docx_filename,
                    preserve_images=preserve_images,
                    include_toc=include_toc,
                    math_engine=math_engine,
                    cleanup_temp=cleanup_temp
                )
                
                batch_result['results'].append(result)
                
                if result['status'] == ConversionStatus.COMPLETED:
                    batch_result['completed_files'] += 1
                    logger.info(f"✅ Successfully processed: {docx_filename}")
                else:
                    batch_result['failed_files'] += 1
                    logger.error(f"❌ Failed to process: {docx_filename} - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = f"Unexpected error processing {docx_filename}: {str(e)}"
                logger.error(error_msg)
                batch_result['failed_files'] += 1
                batch_result['results'].append({
                    'task_id': str(uuid.uuid4()),
                    'status': ConversionStatus.FAILED,
                    'docx_file': docx_filename,
                    'error': error_msg,
                    'created_at': datetime.utcnow().isoformat(),
                    'completed_at': datetime.utcnow().isoformat()
                })
        
        # Determine overall batch status
        if batch_result['failed_files'] == 0:
            batch_result['status'] = ConversionStatus.COMPLETED
        elif batch_result['completed_files'] == 0:
            batch_result['status'] = ConversionStatus.FAILED
        else:
            batch_result['status'] = ConversionStatus.COMPLETED  # Partial success
        
        batch_result['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(
            f"Batch processing complete: {batch_result['completed_files']}/{batch_result['total_files']} "
            f"documents processed successfully (Batch ID: {batch_id})"
        )
        
        return batch_result
    
    def _cleanup_temp_files(self, html_path: Path):
        """Clean up temporary HTML files if cleanup is enabled"""
        try:
            if html_path.exists() and settings.cleanup_temp_files:
                html_path.unlink()
                logger.debug(f"Cleaned up temporary HTML file: {html_path}")
        except Exception as e:
            logger.warning(f"Could not cleanup temporary file {html_path}: {e}")
    
    def get_available_documents(self) -> List[str]:
        """Get list of available DOCX documents"""
        docx_files = list(self.dir_manager.docx_dir.rglob('*.docx'))
        # Filter out temporary Word files
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        
        # Return relative paths from docx_dir
        return [str(f.relative_to(self.dir_manager.docx_dir)) for f in docx_files]
    
    def check_dependencies(self) -> Dict[str, bool]:
        """Check if all required dependencies are available"""
        return {
            'pandoc': self.pandoc_converter.check_pandoc_availability(),
            'directories': all([
                self.dir_manager.docx_dir.exists(),
                self.dir_manager.html_dir.exists(),
                self.dir_manager.md_dir.exists()
            ])
        }
