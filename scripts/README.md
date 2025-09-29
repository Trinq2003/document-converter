# Scripts

## add_watermark.py

**Windows-only script** for adding complex tiled watermarks to DOCX files with sequential processing for safety.

### Requirements
- Windows OS
- Microsoft Word installed
- pywin32 package (`pip install pywin32`)
- tqdm package (`pip install tqdm`)

### Usage
```bash
python scripts/add_watermark.py <relative_path> [options]
```

### Options
- `--preserve-structure, -p`: Preserve directory structure in output (default: True)
- `--max-retries, -r N`: Maximum number of retry attempts for failed files (default: 3)

### Examples
```bash
# Single file with default settings
python scripts/add_watermark.py test.docx

# File in subdirectory with custom retry settings
python scripts/add_watermark.py folder/document.docx --max-retries 5

# Process entire directory with high retry count
python scripts/add_watermark.py . --max-retries 10

# Flatten directory structure in output
python scripts/add_watermark.py folder --max-retries 3 --preserve-structure false
```

### Input/Output
- **Input**: `data/docx/<relative_path>`
- **Output**: `data/watermark/<relative_path>` (preserves folder structure by default)

### Features
- ✅ **Complex tiled watermarks** with multiple sizes and rotations
- ✅ **Sequential processing** for safety (each file fully closed before next)
- ✅ **TQDM progress bars** with real-time status updates
- ✅ **Automatic retry mechanism** for failed files (up to N attempts)
- ✅ **Round-based processing** with detailed progress tracking
- ✅ **Automatic directory structure preservation**
- ✅ **Windows COM integration** for full Word functionality
- ✅ **Timestamp-based watermark text**
- ✅ **Comprehensive error handling** and failure reporting
