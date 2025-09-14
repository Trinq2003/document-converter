"""
Pandoc-based DOCX to HTML conversion module
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, Optional
from app.core.logger import logger
from app.config import settings


class PandocConverter:
    """Handles DOCX to HTML conversion using Pandoc"""
    
    def __init__(self):
        self.timeout = settings.pandoc_timeout
        self.math_engine = settings.pandoc_math_engine
        self.toc_depth = settings.pandoc_toc_depth
    
    def convert_docx_to_html(
        self, 
        docx_path: Path, 
        html_path: Path, 
        images_folder: str = "images",
        include_toc: bool = True,
        math_engine: Optional[str] = None
    ) -> Dict:
        """
        Convert DOCX to HTML using Pandoc
        
        Args:
            docx_path: Input DOCX file path
            html_path: Output HTML file path
            images_folder: Folder name for extracted images
            include_toc: Whether to include table of contents
            math_engine: Math rendering engine override
            
        Returns:
            Dict: Conversion result with status and details
        """
        start_time = time.time()
        logger.info(f"Converting DOCX to HTML: {docx_path} -> {html_path}")
        
        if not docx_path.exists():
            error_msg = f"Input DOCX file not found: {docx_path}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Create output directory
        html_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup images directory
        images_path = html_path.parent / images_folder
        images_path.mkdir(parents=True, exist_ok=True)
        
        # Build Pandoc command
        cmd = [
            'pandoc',
            str(docx_path),
            '-o', str(html_path),
            f'--extract-media={images_path}',
            '--standalone',
            f'--{math_engine or self.math_engine}',
        ]
        
        # Add table of contents if requested
        if include_toc:
            cmd.extend(['--toc', f'--toc-depth={self.toc_depth}'])
        
        # Add metadata
        cmd.extend(['--metadata', f'title={docx_path.stem}'])
        
        try:
            logger.debug(f"Running pandoc command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=self.timeout
            )
            
            # Count extracted images
            image_count = len(list(images_path.rglob('*'))) if images_path.exists() else 0
            
            # Fix image paths in HTML file
            self._fix_image_paths_in_html(html_path, images_folder)
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Successfully converted DOCX to HTML in {duration_ms}ms. Extracted {image_count} images")
            
            return {
                'success': True,
                'html_path': str(html_path),
                'images_path': str(images_path),
                'image_count': image_count,
                'images_folder': images_folder,
                'duration_ms': duration_ms
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Pandoc conversion timed out after {self.timeout} seconds"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Pandoc conversion failed: {e.stderr}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        except FileNotFoundError:
            error_msg = "Pandoc not found. Please install Pandoc first"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _fix_image_paths_in_html(self, html_path: Path, images_folder: str):
        """
        Fix image paths in HTML file to use correct relative paths
        
        Args:
            html_path: HTML file path
            images_folder: Images folder name
        """
        try:
            from bs4 import BeautifulSoup
            
            with open(html_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all img tags
            img_tags = soup.find_all('img')
            fixed_count = 0
            
            for img in img_tags:
                src = img.get('src', '')
                if src:
                    # Convert absolute paths to relative paths
                    if Path(src).is_absolute():
                        # Extract just the filename from absolute path
                        filename = Path(src).name
                        new_src = f"{images_folder}/media/{filename}"
                    else:
                        # Handle relative paths that might be incorrect
                        filename = Path(src).name
                        new_src = f"{images_folder}/media/{filename}"
                    
                    img['src'] = new_src
                    fixed_count += 1
                    logger.debug(f"Fixed image path: {src} -> {new_src}")
            
            # Write back the fixed HTML
            with open(html_path, 'w', encoding='utf-8') as file:
                file.write(str(soup))
            
            if fixed_count > 0:
                logger.info(f"Fixed {fixed_count} image paths in HTML file")
                
        except Exception as e:
            logger.warning(f"Could not fix image paths in HTML: {e}")
    
    def check_pandoc_availability(self) -> bool:
        """Check if Pandoc is available and working"""
        try:
            result = subprocess.run(
                ['pandoc', '--version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
