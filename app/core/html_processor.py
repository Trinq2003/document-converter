"""
HTML processing and enhancement module for markdown conversion
"""

import re
import os
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup
import html2text
from app.core.logger import logger
from app.config import settings


class HTMLProcessor:
    """Handles HTML processing and enhancement for markdown conversion"""
    
    def __init__(self):
        self.h2t_config = {
            'ignore_links': settings.h2t_ignore_links,
            'ignore_images': settings.h2t_ignore_images,
            'ignore_emphasis': False,
            'body_width': settings.h2t_body_width,
            'unicode_snob': settings.h2t_unicode_snob,
            'skip_internal_links': True,
            'mark_code': True,
            'wrap_links': False,
            'wrap_list_items': False
        }
    
    def convert_html_to_markdown_enhanced(
        self, 
        html_path: Path, 
        md_path: Path, 
        images_folder: str = "images"
    ) -> Dict:
        """
        Enhanced HTML to Markdown conversion with special element preservation
        
        Args:
            html_path: Input HTML file path
            md_path: Output Markdown file path
            images_folder: Images folder name for path calculation
            
        Returns:
            Dict: Conversion result with statistics
        """
        start_time = time.time()
        logger.info(f"Converting HTML to Markdown: {html_path} -> {md_path}")
        
        if not html_path.exists():
            error_msg = f"Input HTML file not found: {html_path}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        try:
            # Read HTML content
            with open(html_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            logger.debug(f"Read HTML file: {len(html_content)} characters")
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Calculate correct image path for markdown file
            correct_image_path = self._calculate_image_path_for_markdown(html_path, md_path, images_folder)
            
            # Extract special elements with corrected image paths
            table_placeholders, math_placeholders, image_list = self._extract_special_elements(
                soup, correct_image_path
            )
            
            # Configure html2text
            h = html2text.HTML2Text()
            for key, value in self.h2t_config.items():
                setattr(h, key, value)
            
            # Convert to markdown
            logger.debug("Converting HTML to markdown...")
            markdown_content = h.handle(str(soup))
            
            # Restore special elements
            markdown_content = self._restore_special_elements(
                markdown_content, table_placeholders, math_placeholders
            )
            
            # Clean up formatting
            markdown_content = self._clean_markdown_content(markdown_content)
            
            # Add image appendix if images exist
            if settings.preserve_images and image_list:
                image_appendix = self._create_image_appendix(image_list)
                markdown_content += image_appendix
            
            # Create output directory
            md_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write markdown file
            with open(md_path, 'w', encoding='utf-8') as file:
                file.write(markdown_content)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            stats = {
                'success': True,
                'md_path': str(md_path),
                'tables_count': len(table_placeholders),
                'math_count': len(math_placeholders),
                'images_count': len(image_list),
                'output_length': len(markdown_content),
                'image_path_used': correct_image_path,
                'duration_ms': duration_ms
            }
            
            logger.info(
                f"Successfully converted HTML to Markdown in {duration_ms}ms. "
                f"Tables: {stats['tables_count']}, Math: {stats['math_count']}, "
                f"Images: {stats['images_count']}, Image path: {correct_image_path}"
            )
            
            return stats
            
        except Exception as e:
            error_msg = f"Error converting HTML to Markdown: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _calculate_image_path_for_markdown(self, html_path: Path, md_path: Path, images_folder: str) -> str:
        """
        Calculate the correct image path for markdown file
        
        Args:
            html_path: Original HTML file path
            md_path: Target markdown file path  
            images_folder: Images folder name
            
        Returns:
            str: Correct relative path to images folder for markdown
        """
        # Get the images folder path relative to HTML
        html_images_path = html_path.parent / images_folder
        
        # Calculate relative path from MD file to images folder
        try:
            rel_path = os.path.relpath(html_images_path, md_path.parent)
            # Normalize path separators for web use
            rel_path = rel_path.replace('\\', '/')
            logger.debug(f"Image path for MD file: {rel_path}")
            return rel_path
        except ValueError:
            # If paths are on different drives (Windows), use absolute path
            return str(html_images_path).replace('\\', '/')
    
    def _extract_special_elements(self, soup: BeautifulSoup, correct_image_path: str = None) -> Tuple[Dict, Dict, List]:
        """
        Extract and replace tables, math elements, and collect images
        
        Args:
            soup: Parsed HTML content
            correct_image_path: Correct relative path to images folder
            
        Returns:
            Tuple: (table_placeholders, math_placeholders, image_list)
        """
        table_placeholders = {}
        math_placeholders = {}
        image_list = []
        
        # Extract tables
        tables = soup.find_all('table')
        logger.debug(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            placeholder = f"___TABLE_PLACEHOLDER_{i}___"
            table_html = str(table)
            # Clean up table HTML while preserving structure
            table_html = re.sub(r'\n\s*\n', '\n', table_html)
            table_html = re.sub(r'>\s+<', '><', table_html)
            
            # Fix image paths within tables if needed
            if correct_image_path:
                table_html = self._fix_image_paths_in_content(table_html, correct_image_path)
            
            table_placeholders[placeholder] = table_html
            table.replace_with(placeholder)
            logger.debug(f"Extracted table {i}")
        
        # Extract math elements
        math_elements = soup.find_all(['math', 'span'], class_=lambda x: x and 'math' in str(x).lower())
        math_elements.extend(soup.find_all('math'))
        
        logger.debug(f"Found {len(math_elements)} math elements")
        
        for i, math in enumerate(math_elements):
            placeholder = f"___MATH_PLACEHOLDER_{i}___"
            math_html = str(math)
            math_placeholders[placeholder] = math_html
            math.replace_with(placeholder)
            logger.debug(f"Extracted math element {i}")
        
        # Collect and fix images
        images = soup.find_all('img')
        for img in images:
            src = img.get('src', '')
            
            # Fix image path if correct path provided
            if correct_image_path and src:
                filename = Path(src).name
                corrected_src = f"{correct_image_path}/media/{filename}"
                img['src'] = corrected_src
                src = corrected_src
                logger.debug(f"Corrected image path: {src}")
            
            img_info = {
                'src': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'filename': Path(src).name if src else '',
                'tag': str(img)
            }
            image_list.append(img_info)
            logger.debug(f"Found image: {img_info['src']}")
        
        return table_placeholders, math_placeholders, image_list
    
    def _fix_image_paths_in_content(self, content: str, correct_image_path: str) -> str:
        """
        Fix image paths within HTML content (like table cells)
        
        Args:
            content: HTML content
            correct_image_path: Correct path to images folder
            
        Returns:
            str: Content with fixed image paths
        """
        soup = BeautifulSoup(content, 'html.parser')
        images = soup.find_all('img')
        
        for img in images:
            src = img.get('src', '')
            if src:
                filename = Path(src).name
                corrected_src = f"{correct_image_path}/media/{filename}"
                img['src'] = corrected_src
        
        return str(soup)
    
    def _restore_special_elements(self, markdown_content: str, table_placeholders: Dict, 
                                math_placeholders: Dict) -> str:
        """
        Restore tables and math elements in markdown content
        
        Args:
            markdown_content: Converted markdown content
            table_placeholders: Table placeholders and HTML
            math_placeholders: Math placeholders and HTML
            
        Returns:
            str: Markdown content with restored elements
        """
        # Restore tables
        for placeholder, table_html in table_placeholders.items():
            markdown_content = markdown_content.replace(placeholder, f'\n{table_html}\n')
            logger.debug(f"Restored table: {placeholder}")
        
        # Restore math elements  
        for placeholder, math_html in math_placeholders.items():
            markdown_content = markdown_content.replace(placeholder, f'{math_html}')
            logger.debug(f"Restored math element: {placeholder}")
        
        return markdown_content
    
    def _clean_markdown_content(self, content: str) -> str:
        """
        Clean up markdown content formatting
        
        Args:
            content: Raw markdown content
            
        Returns:
            str: Cleaned markdown content
        """
        # Remove blockquote indentation ("> " at line start)
        content = re.sub(r'^>\s*', '', content, flags=re.MULTILINE)
        
        # Remove excessive tabs and indentation
        content = re.sub(r'^\t+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^    ', '', content, flags=re.MULTILINE)
        
        # Clean up excessive newlines (but keep some structure)
        content = re.sub(r'\n{4,}', '\n\n\n', content)
        content = re.sub(r'\n{3}(?=\n)', '\n\n', content)
        
        # Fix spacing around restored elements
        content = re.sub(r'\n+(<table)', r'\n\1', content)
        content = re.sub(r'(</table>)\n+', r'\1\n\n', content)
        content = re.sub(r'\n+(<math)', r'\n\1', content)
        content = re.sub(r'(</math>)\n+', r'\1\n', content)
        
        return content.strip()
    
    def _create_image_appendix(self, image_list: List[Dict]) -> str:
        """
        Create an appendix with list of images
        
        Args:
            image_list: List of image information
            
        Returns:
            str: Formatted image appendix
        """
        if not image_list:
            return ""
        
        appendix = "\n\n---\n\n## Images Used in Document\n\n"
        
        for i, img in enumerate(image_list, 1):
            appendix += f"{i}. **Image {i}:**\n"
            appendix += f"   - Source: `{img['src']}`\n"
            if img['alt']:
                appendix += f"   - Alt text: {img['alt']}\n"
            if img['title']:
                appendix += f"   - Title: {img['title']}\n"
            appendix += f"   - HTML: `{img['tag']}`\n\n"
        
        logger.info(f"Created image appendix with {len(image_list)} images")
        return appendix
