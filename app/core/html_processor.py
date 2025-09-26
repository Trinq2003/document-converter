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
            # Since HTML and MD are in the same folder, images are in "images" subfolder
            correct_image_path = "images"
            
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
                markdown_content, table_placeholders, math_placeholders, image_list
            )
            
            # Clean up formatting
            markdown_content = self._clean_markdown_content(markdown_content)

            # Images are now inline in the markdown content, no appendix needed
            
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

    def _convert_table_to_markdown(self, table) -> Tuple[str, List[Dict]]:
        """
        Convert HTML table to markdown table format, preserving images within cells

        Args:
            table: BeautifulSoup table element

        Returns:
            Tuple[str, List[Dict]]: (Markdown table, list of images found in table)
        """
        try:
            rows = table.find_all('tr')
            if not rows:
                return "", []

            table_images = []

            # Process header row
            header_cells = []
            if rows:
                header_row = rows[0]
                for cell in header_row.find_all(['th', 'td']):
                    cell_content, cell_images = self._process_table_cell_content(cell)
                    header_cells.append(cell_content)
                    table_images.extend(cell_images)

            # Process data rows
            data_rows = []
            for row in rows[1:] if header_cells else rows:
                row_cells = []
                for cell in row.find_all(['th', 'td']):
                    cell_content, cell_images = self._process_table_cell_content(cell)
                    row_cells.append(cell_content)
                    table_images.extend(cell_images)
                if row_cells:  # Only add non-empty rows
                    data_rows.append(row_cells)

            if not header_cells and not data_rows:
                return "", []

            # Create markdown table
            markdown_lines = []

            # Add header
            if header_cells:
                markdown_lines.append("| " + " | ".join(header_cells) + " |")
                markdown_lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

            # Add data rows
            all_rows = ([header_cells] if not header_cells and data_rows else []) + data_rows
            if not header_cells and all_rows:
                # If no header, make first row the header
                markdown_lines.append("| " + " | ".join(all_rows[0]) + " |")
                markdown_lines.append("| " + " | ".join(["---"] * len(all_rows[0])) + " |")
                all_rows = all_rows[1:]

            for row in all_rows:
                if len(row) == len(header_cells if header_cells else len(all_rows[0] if all_rows else 0)):
                    markdown_lines.append("| " + " | ".join(row) + " |")

            return "\n".join(markdown_lines) + "\n\n", table_images

        except Exception as e:
            logger.warning(f"Error converting table to markdown: {e}")
            return "", []

    def _process_table_cell_content(self, cell) -> Tuple[str, List[Dict]]:
        """
        Process table cell content, converting images to markdown while preserving text

        Args:
            cell: BeautifulSoup cell element (th or td)

        Returns:
            Tuple[str, List[Dict]]: (Cell content with images converted to markdown, list of images found)
        """
        try:
            # Clone the cell to avoid modifying the original
            cell_copy = BeautifulSoup(str(cell), 'html.parser').find(['th', 'td'])

            cell_images = []

            # Find all images in this cell
            images = cell_copy.find_all('img') if cell_copy else []

            # Convert each image to markdown and collect image info
            for img in images:
                src = img.get('src', '')
                alt = img.get('alt', '')
                title = img.get('title', '')

                # Convert to markdown image syntax
                if title:
                    markdown_img = f'![{alt}]({src} "{title}")'
                else:
                    markdown_img = f'![{alt}]({src})'

                # Collect image info for the main image list
                img_info = {
                    'src': src,
                    'alt': alt,
                    'title': title,
                    'filename': Path(src).name if src else '',
                    'markdown': markdown_img,
                    'placeholder': '',  # Will be set later in the main processing
                    'in_table': True  # Mark that this image was found in a table
                }
                cell_images.append(img_info)

                # Replace img tag with markdown
                img.replace_with(markdown_img)

            # Get the processed text content
            content = cell_copy.get_text(strip=True) if cell_copy else ""

            return content, cell_images

        except Exception as e:
            logger.warning(f"Error processing table cell content: {e}")
            # Fallback to simple text extraction
            return cell.get_text(strip=True), []

    def _convert_math_to_markdown(self, math_element) -> str:
        """
        Convert HTML math element to markdown/latex format

        Args:
            math_element: BeautifulSoup math element

        Returns:
            str: Markdown math notation
        """
        try:
            # Check for LaTeX content in attributes or text
            latex_content = ""

            # Try to extract from data-latex or similar attributes
            if hasattr(math_element, 'attrs'):
                latex_attrs = ['data-latex', 'data-tex', 'latex', 'tex']
                for attr in latex_attrs:
                    if attr in math_element.attrs:
                        latex_content = math_element.attrs[attr]
                        break

            # If no latex attribute, try to extract from text content
            if not latex_content:
                text_content = math_element.get_text(strip=True)
                if text_content:
                    # Remove common HTML math delimiters and clean up
                    latex_content = re.sub(r'[\\$]+', '', text_content)
                    latex_content = latex_content.strip()

            # If still no content, try to extract from annotation or other child elements
            if not latex_content:
                # Look for mathml annotation
                annotation = math_element.find('annotation', encoding='application/x-tex')
                if annotation:
                    latex_content = annotation.get_text(strip=True)

                # Or look for semantics with annotation
                semantics = math_element.find('semantics')
                if semantics:
                    annotation = semantics.find('annotation', encoding='application/x-tex')
                    if annotation:
                        latex_content = annotation.get_text(strip=True)

            # Clean up the latex content
            if latex_content:
                # Clean up the latex content - remove extra backslashes but keep necessary ones
                latex_content = latex_content.strip()

                # Wrap in appropriate markdown math delimiters
                if latex_content.startswith('$$') or latex_content.endswith('$$'):
                    return latex_content
                elif latex_content.startswith('$') or latex_content.endswith('$'):
                    return latex_content
                elif '\n' in latex_content or len(latex_content) > 50:
                    # Multi-line or long equation -> display math
                    return f"$$\n{latex_content}\n$$"
                else:
                    # Inline math
                    return f"${latex_content}$"
            else:
                # Fallback: return the original HTML
                return str(math_element)

        except Exception as e:
            logger.warning(f"Error converting math to markdown: {e}")
            return str(math_element)

    def _extract_special_elements(self, soup: BeautifulSoup, correct_image_path: str = None) -> Tuple[Dict, Dict, List]:
        """
        Extract and convert tables, math elements, and images to markdown format

        Args:
            soup: Parsed HTML content
            correct_image_path: Correct relative path to images folder

        Returns:
            Tuple: (table_placeholders, math_placeholders, image_list)
        """
        table_placeholders = {}
        math_placeholders = {}
        image_list = []

        # Convert tables to markdown (this also handles images within tables)
        tables = soup.find_all('table')
        logger.debug(f"Found {len(tables)} tables")

        for i, table in enumerate(tables):
            placeholder = f"___TABLE_PLACEHOLDER_{i}___"
            markdown_table, table_images = self._convert_table_to_markdown(table)
            table_placeholders[placeholder] = markdown_table
            # Add images found in this table to the main image list
            image_list.extend(table_images)
            table.replace_with(placeholder)
            logger.debug(f"Converted table {i} to markdown with {len(table_images)} images")

        # Convert math elements to markdown/latex
        math_elements = soup.find_all(['math', 'span'], class_=lambda x: x and 'math' in str(x).lower())
        math_elements.extend(soup.find_all('math'))

        logger.debug(f"Found {len(math_elements)} math elements")

        for i, math in enumerate(math_elements):
            placeholder = f"___MATH_PLACEHOLDER_{i}___"
            markdown_math = self._convert_math_to_markdown(math)
            math_placeholders[placeholder] = markdown_math
            math.replace_with(placeholder)
            logger.debug(f"Converted math element {i} to markdown")

        # Convert remaining images to markdown (those not in tables)
        images = soup.find_all('img')
        for img in images:
            src = img.get('src', '')

            # Fix image path if correct path provided
            if correct_image_path and src:
                filename = Path(src).name
                corrected_src = f"{correct_image_path}/{filename}"
                src = corrected_src
                logger.debug(f"Corrected image path: {src}")

            # Convert to markdown image syntax
            alt = img.get('alt', '')
            title = img.get('title', '')

            if title:
                markdown_img = f'![{alt}]({src} "{title}")'
            else:
                markdown_img = f'![{alt}]({src})'

            # Create placeholder for the image
            placeholder = f"___IMAGE_PLACEHOLDER_{len(image_list)}___"
            img_info = {
                'src': src,
                'alt': alt,
                'title': title,
                'filename': Path(src).name if src else '',
                'markdown': markdown_img,
                'placeholder': placeholder
            }
            image_list.append(img_info)

            # Replace img tag with placeholder
            img.replace_with(placeholder)
            logger.debug(f"Converted image to markdown: {src}")

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
                corrected_src = f"{correct_image_path}/{filename}"
                img['src'] = corrected_src
        
        return str(soup)
    
    def _restore_special_elements(self, markdown_content: str, table_placeholders: Dict,
                                math_placeholders: Dict, image_list: List = None) -> str:
        """
        Restore tables, math elements, and images in markdown content

        Args:
            markdown_content: Converted markdown content
            table_placeholders: Table placeholders and markdown
            math_placeholders: Math placeholders and markdown
            image_list: List of image info with placeholders

        Returns:
            str: Markdown content with restored elements
        """
        # Restore tables
        for placeholder, table_markdown in table_placeholders.items():
            markdown_content = markdown_content.replace(placeholder, f'\n{table_markdown}')
            logger.debug(f"Restored table: {placeholder}")

        # Restore math elements
        for placeholder, math_markdown in math_placeholders.items():
            markdown_content = markdown_content.replace(placeholder, math_markdown)
            logger.debug(f"Restored math element: {placeholder}")

        # Restore images
        if image_list:
            for img_info in image_list:
                placeholder = img_info.get('placeholder', '')
                markdown_img = img_info.get('markdown', '')
                if placeholder and markdown_img:
                    markdown_content = markdown_content.replace(placeholder, markdown_img)
                    logger.debug(f"Restored image: {placeholder}")

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
