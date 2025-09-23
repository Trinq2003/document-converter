# Scripts

## add_watermark.py

**Windows-only script** for adding complex tiled watermarks to DOCX files with parallel processing and progress tracking.

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
- `--workers, -w N`: Number of parallel workers (default: CPU count)
- `--preserve-structure, -p`: Preserve directory structure in output (default: True)

### Examples
```bash
# Single file with default settings
python scripts/add_watermark.py test.docx

# File in subdirectory with custom workers
python scripts/add_watermark.py folder/document.docx --workers 4

# Process entire directory with parallel processing
python scripts/add_watermark.py . --workers 8

# Flatten directory structure in output
python scripts/add_watermark.py folder --workers 4 --preserve-structure false
```

### Input/Output
- **Input**: `data/docx/<relative_path>`
- **Output**: `data/watermark/<relative_path>` (preserves folder structure by default)

### Features
- ✅ **Complex tiled watermarks** with multiple sizes and rotations
- ✅ **Parallel processing** with configurable worker count
- ✅ **TQDM progress bars** with real-time status updates
- ✅ **Automatic directory structure preservation**
- ✅ **Windows COM integration** for full Word functionality
- ✅ **Timestamp-based watermark text**
- ✅ **Error handling** and detailed failure reporting
