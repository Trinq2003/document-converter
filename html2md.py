import re
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
import html2text

class DocumentConverter:
    """
    Enhanced document converter that handles DOCX -> HTML -> Markdown conversion
    with special handling for tables, math equations, and images
    """
    
    def __init__(self, base_dir: str = ".", log_level: str = "INFO"):
        """
        Initialize the converter
        
        Args:
            base_dir (str): Base directory for relative paths
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.base_dir = Path(base_dir)
        self.docx_dir = self.base_dir / "docx"
        self.html_dir = self.base_dir / "html" 
        self.md_dir = self.base_dir / "md"
        
        # Setup logging
        self._setup_logging(log_level)
        
        # Create directories
        self._create_directories()
        
        # HTML2Text configuration
        self.h2t_config = {
            'ignore_links': False,
            'ignore_images': True,  # We'll handle images separately
            'ignore_emphasis': False,
            'body_width': 0,  # Don't wrap lines
            'unicode_snob': True,
            'skip_internal_links': True,
            'mark_code': True,
            'wrap_links': False,
            'wrap_list_items': False
        }
        
        self.logger.info(f"DocumentConverter initialized with base directory: {self.base_dir}")
    
    def _setup_logging(self, log_level: str):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('document_converter.log')
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _create_directories(self):
        """Create necessary directories"""
        for directory in [self.docx_dir, self.html_dir, self.md_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created/verified directory: {directory}")
    
    def convert_docx_to_html(self, docx_path: Path, html_path: Path, images_folder: str = "images") -> Dict:
        """
        Convert DOCX to HTML using Pandoc
        
        Args:
            docx_path (Path): Input DOCX file path
            html_path (Path): Output HTML file path
            images_folder (str): Folder name for extracted images
            
        Returns:
            Dict: Conversion result with status and details
        """
        self.logger.info(f"Converting DOCX to HTML: {docx_path} -> {html_path}")
        
        if not docx_path.exists():
            error_msg = f"Input DOCX file not found: {docx_path}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        # Create output directory
        html_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Setup images directory
        images_path = html_path.parent / images_folder
        images_path.mkdir(parents=True, exist_ok=True)
        
        # Pandoc command
        cmd = [
            'pandoc',
            str(docx_path),
            '-o', str(html_path),
            f'--extract-media={images_path}',
            '--standalone',
            '--mathml',
            '--toc',
            '--toc-depth=4',
            '--metadata', f'title={docx_path.stem}'
        ]
        
        try:
            self.logger.debug(f"Running pandoc command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Count extracted images
            image_count = len(list(images_path.rglob('*'))) if images_path.exists() else 0
            
            # Fix image paths in HTML file
            self._fix_image_paths_in_html(html_path, images_folder)
            
            self.logger.info(f"Successfully converted DOCX to HTML. Extracted {image_count} images")
            
            return {
                'success': True,
                'html_path': str(html_path),
                'images_path': str(images_path),
                'image_count': image_count,
                'images_folder': images_folder
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Pandoc conversion failed: {e.stderr}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        except FileNotFoundError:
            error_msg = "Pandoc not found. Please install Pandoc first"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _fix_image_paths_in_html(self, html_path: Path, images_folder: str):
        """
        Fix image paths in HTML file to use correct relative paths
        
        Args:
            html_path (Path): HTML file path
            images_folder (str): Images folder name
        """
        try:
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
                    if os.path.isabs(src):
                        # Extract just the filename from absolute path
                        filename = Path(src).name
                        new_src = f"{images_folder}/media/{filename}"
                    else:
                        # Handle relative paths that might be incorrect
                        filename = Path(src).name
                        new_src = f"{images_folder}/media/{filename}"
                    
                    img['src'] = new_src
                    fixed_count += 1
                    self.logger.debug(f"Fixed image path: {src} -> {new_src}")
            
            # Write back the fixed HTML
            with open(html_path, 'w', encoding='utf-8') as file:
                file.write(str(soup))
            
            if fixed_count > 0:
                self.logger.info(f"Fixed {fixed_count} image paths in HTML file")
                
        except Exception as e:
            self.logger.warning(f"Could not fix image paths in HTML: {e}")
    
    def _calculate_relative_path(self, from_file: Path, to_folder: Path) -> str:
        """
        Calculate relative path from a file to a folder
        
        Args:
            from_file (Path): Source file path
            to_folder (Path): Target folder path
            
        Returns:
            str: Relative path string
        """
        try:
            # Get relative path from file's directory to target folder
            rel_path = os.path.relpath(to_folder, from_file.parent)
            # Normalize path separators for web use
            rel_path = rel_path.replace('\\', '/')
            return rel_path
        except ValueError:
            # If paths are on different drives (Windows), use absolute path
            return str(to_folder).replace('\\', '/')
    
    def _fix_image_paths_for_markdown(self, html_path: Path, md_path: Path, images_folder: str) -> str:
        """
        Calculate the correct image path for markdown file
        
        Args:
            html_path (Path): Original HTML file path
            md_path (Path): Target markdown file path  
            images_folder (str): Images folder name
            
        Returns:
            str: Correct relative path to images folder for markdown
        """
        # Get the images folder path relative to HTML
        html_images_path = html_path.parent / images_folder
        
        # Calculate relative path from MD file to images folder
        md_to_images = self._calculate_relative_path(md_path, html_images_path)
        
        self.logger.debug(f"Image path for MD file: {md_to_images}")
        return md_to_images
        """
        Extract and replace tables, math elements, and collect images
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            
        Returns:
            Tuple: (table_placeholders, math_placeholders, image_list)
        """
        table_placeholders = {}
        math_placeholders = {}
        image_list = []
        
        # Extract tables
        tables = soup.find_all('table')
        self.logger.debug(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            placeholder = f"___TABLE_PLACEHOLDER_{i}___"
            table_html = str(table)
            # Clean up table HTML while preserving structure
            table_html = re.sub(r'\n\s*\n', '\n', table_html)
            table_html = re.sub(r'>\s+<', '><', table_html)
            table_placeholders[placeholder] = table_html
            table.replace_with(placeholder)
            self.logger.debug(f"Extracted table {i}")
        
        # Extract math elements
        math_elements = soup.find_all(['math', 'span'], class_=lambda x: x and 'math' in str(x).lower())
        math_elements.extend(soup.find_all('math'))
        
        self.logger.debug(f"Found {len(math_elements)} math elements")
        
        for i, math in enumerate(math_elements):
            placeholder = f"___MATH_PLACEHOLDER_{i}___"
            math_html = str(math)
            math_placeholders[placeholder] = math_html
            math.replace_with(placeholder)
            self.logger.debug(f"Extracted math element {i}")
        
    def _extract_special_elements(self, soup: BeautifulSoup, correct_image_path: str = None) -> Tuple[Dict, Dict, List]:
        """
        Extract and replace tables, math elements, and collect images
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            correct_image_path (str): Correct relative path to images folder
            
        Returns:
            Tuple: (table_placeholders, math_placeholders, image_list)
        """
        table_placeholders = {}
        math_placeholders = {}
        image_list = []
        
        # Extract tables
        tables = soup.find_all('table')
        self.logger.debug(f"Found {len(tables)} tables")
        
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
            self.logger.debug(f"Extracted table {i}")
        
        # Extract math elements
        math_elements = soup.find_all(['math', 'span'], class_=lambda x: x and 'math' in str(x).lower())
        math_elements.extend(soup.find_all('math'))
        
        self.logger.debug(f"Found {len(math_elements)} math elements")
        
        for i, math in enumerate(math_elements):
            placeholder = f"___MATH_PLACEHOLDER_{i}___"
            math_html = str(math)
            math_placeholders[placeholder] = math_html
            math.replace_with(placeholder)
            self.logger.debug(f"Extracted math element {i}")
        
        # Collect and fix images
        images = soup.find_all('img')
        for img in images:
            src = img.get('src', '')
            
            # Fix image path if correct path provided
            if correct_image_path and src:
                filename = Path(src).name
                corrected_src = f"{correct_image_path}/{filename}"
                img['src'] = corrected_src
                src = corrected_src
                self.logger.debug(f"Corrected image path: {src}")
            
            img_info = {
                'src': src,
                'alt': img.get('alt', ''),
                'title': img.get('title', ''),
                'tag': str(img)
            }
            image_list.append(img_info)
            self.logger.debug(f"Found image: {img_info['src']}")
        
        return table_placeholders, math_placeholders, image_list
    
    def _fix_image_paths_in_content(self, content: str, correct_image_path: str) -> str:
        """
        Fix image paths within HTML content (like table cells)
        
        Args:
            content (str): HTML content
            correct_image_path (str): Correct path to images folder
            
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
                                math_placeholders: Dict) -> str:
        """
        Restore tables and math elements in markdown content
        
        Args:
            markdown_content (str): Converted markdown content
            table_placeholders (Dict): Table placeholders and HTML
            math_placeholders (Dict): Math placeholders and HTML
            
        Returns:
            str: Markdown content with restored elements
        """
        # Restore tables
        for placeholder, table_html in table_placeholders.items():
            markdown_content = markdown_content.replace(placeholder, f'\n{table_html}\n')
            self.logger.debug(f"Restored table: {placeholder}")
        
        # Restore math elements  
        for placeholder, math_html in math_placeholders.items():
            markdown_content = markdown_content.replace(placeholder, f'{math_html}')
            self.logger.debug(f"Restored math element: {placeholder}")
        
        return markdown_content
    
    def _clean_markdown_content(self, content: str) -> str:
        """
        Clean up markdown content formatting
        
        Args:
            content (str): Raw markdown content
            
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
            image_list (List[Dict]): List of image information
            
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
        
        self.logger.info(f"Created image appendix with {len(image_list)} images")
        return appendix
    
    def convert_html_to_markdown_enhanced(self, html_path: Path, md_path: Path, images_folder: str = "images") -> Dict:
        """
        Enhanced HTML to Markdown conversion with special element preservation
        
        Args:
            html_path (Path): Input HTML file path
            md_path (Path): Output Markdown file path
            images_folder (str): Images folder name for path calculation
            
        Returns:
            Dict: Conversion result with statistics
        """
        self.logger.info(f"Converting HTML to Markdown: {html_path} -> {md_path}")
        
        if not html_path.exists():
            error_msg = f"Input HTML file not found: {html_path}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        try:
            # Read HTML content
            with open(html_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            self.logger.debug(f"Read HTML file: {len(html_content)} characters")
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Calculate correct image path for markdown file
            correct_image_path = self._fix_image_paths_for_markdown(html_path, md_path, images_folder)
            
            # Extract special elements with corrected image paths
            table_placeholders, math_placeholders, image_list = self._extract_special_elements(
                soup, correct_image_path
            )
            
            # Configure html2text
            h = html2text.HTML2Text()
            for key, value in self.h2t_config.items():
                setattr(h, key, value)
            
            # Convert to markdown
            self.logger.debug("Converting HTML to markdown...")
            markdown_content = h.handle(str(soup))
            
            # Restore special elements
            markdown_content = self._restore_special_elements(
                markdown_content, table_placeholders, math_placeholders
            )
            
            # Clean up formatting
            markdown_content = self._clean_markdown_content(markdown_content)
            
            # Add image appendix
            image_appendix = self._create_image_appendix(image_list)
            markdown_content += image_appendix
            
            # Create output directory
            md_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write markdown file
            with open(md_path, 'w', encoding='utf-8') as file:
                file.write(markdown_content)
            
            stats = {
                'success': True,
                'md_path': str(md_path),
                'tables_count': len(table_placeholders),
                'math_count': len(math_placeholders),
                'images_count': len(image_list),
                'output_length': len(markdown_content),
                'image_path_used': correct_image_path
            }
            
            self.logger.info(
                f"Successfully converted HTML to Markdown. "
                f"Tables: {stats['tables_count']}, Math: {stats['math_count']}, "
                f"Images: {stats['images_count']}, Image path: {correct_image_path}"
            )
            
            return stats
            
        except Exception as e:
            error_msg = f"Error converting HTML to Markdown: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def process_single_document(self, docx_filename: str) -> Dict:
        """
        Process a single document through the complete pipeline
        
        Args:
            docx_filename (str): DOCX filename (relative to docx_dir)
            
        Returns:
            Dict: Processing result with all statistics
        """
        self.logger.info(f"Processing document: {docx_filename}")
        
        # Setup paths
        docx_path = self.docx_dir / docx_filename
        html_path = self.html_dir / f"{Path(docx_filename).stem}.html"
        md_path = self.md_dir / f"{Path(docx_filename).stem}.md"
        
        result = {
            'docx_file': docx_filename,
            'docx_path': str(docx_path),
            'html_path': str(html_path),
            'md_path': str(md_path),
            'steps': {}
        }
        
        # Step 1: DOCX to HTML
        self.logger.info(f"Step 1: Converting DOCX to HTML - {docx_filename}")
        docx_result = self.convert_docx_to_html(docx_path, html_path)
        result['steps']['docx_to_html'] = docx_result
        
        if not docx_result['success']:
            result['success'] = False
            result['error'] = f"DOCX to HTML conversion failed: {docx_result['error']}"
            return result
        
        # Step 2: HTML to Markdown
        self.logger.info(f"Step 2: Converting HTML to Markdown - {docx_filename}")
        md_result = self.convert_html_to_markdown_enhanced(
            html_path, md_path, 
            images_folder=docx_result.get('images_folder', 'images')
        )
        result['steps']['html_to_md'] = md_result
        
        if not md_result['success']:
            result['success'] = False
            result['error'] = f"HTML to Markdown conversion failed: {md_result['error']}"
            return result
        
        # Success
        result['success'] = True
        self.logger.info(f"Successfully processed document: {docx_filename}")
        
        return result
    
    def process_all_documents(self) -> List[Dict]:
        """
        Process all DOCX documents in the docx directory
        
        Returns:
            List[Dict]: Results for each processed document
        """
        self.logger.info("Starting batch processing of all documents")
        
        # Find all DOCX files
        docx_files = list(self.docx_dir.rglob('*.docx'))
        # Filter out temporary Word files
        docx_files = [f for f in docx_files if not f.name.startswith('~$')]
        
        self.logger.info(f"Found {len(docx_files)} DOCX files to process")
        
        if not docx_files:
            self.logger.warning("No DOCX files found in the docx directory")
            return []
        
        results = []
        
        for docx_file in docx_files:
            # Get relative path from docx_dir
            relative_path = docx_file.relative_to(self.docx_dir)
            
            try:
                result = self.process_single_document(str(relative_path))
                results.append(result)
                
                if result['success']:
                    self.logger.info(f"✅ Successfully processed: {relative_path}")
                else:
                    self.logger.error(f"❌ Failed to process: {relative_path} - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = f"Unexpected error processing {relative_path}: {str(e)}"
                self.logger.error(error_msg)
                results.append({
                    'docx_file': str(relative_path),
                    'success': False,
                    'error': error_msg
                })
        
        # Summary
        successful = sum(1 for r in results if r['success'])
        total = len(results)
        
        self.logger.info(f"Batch processing complete: {successful}/{total} documents processed successfully")
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """
        Print a summary of processing results
        
        Args:
            results (List[Dict]): Processing results
        """
        if not results:
            print("No documents were processed.")
            return
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        
        print("\n" + "="*60)
        print(f"DOCUMENT CONVERSION SUMMARY")
        print("="*60)
        print(f"Total documents: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print()
        
        if successful:
            print("✅ SUCCESSFUL CONVERSIONS:")
            for result in successful:
                html_step = result.get('steps', {}).get('html_to_md', {})
                print(f"  📄 {result['docx_file']}")
                print(f"     Tables: {html_step.get('tables_count', 0)}, "
                      f"Math: {html_step.get('math_count', 0)}, "
                      f"Images: {html_step.get('images_count', 0)}")
        
        if failed:
            print("\n❌ FAILED CONVERSIONS:")
            for result in failed:
                print(f"  📄 {result['docx_file']}: {result.get('error', 'Unknown error')}")
        
        print("="*60)

# Example usage and testing
if __name__ == "__main__":
    # Initialize converter
    converter = DocumentConverter(base_dir=".", log_level="INFO")
    
    # Process all documents
    results = converter.process_all_documents()
    
    # Print summary
    converter.print_summary(results)
    
    # Example of processing a single document
    # result = converter.process_single_document("example.docx")
    # print(f"Single document result: {result}")