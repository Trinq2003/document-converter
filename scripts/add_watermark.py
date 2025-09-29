#!/usr/bin/env python3
"""
Standalone Windows Watermark Script
Compact but fully functional Windows COM-based watermarking with parallel processing

Usage: python scripts/add_watermark.py <relative_path> [--max-retries R]
Example: python scripts/add_watermark.py test.docx
Example: python scripts/add_watermark.py folder/document.docx --max-retries 5

Note: Files are processed sequentially for safety (each file fully closed before next)
"""

import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple
import multiprocessing

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable=None, **kwargs):
        return iterable if iterable is not None else iter([])

# Windows COM imports
import pythoncom
import win32com.client as win32
from win32com.client import constants as c

WATERMARK_TAG = "AI_RACE_WATERMARK"

def rgb(r: int, g: int, b: int) -> int:
    """Convert RGB tuple to VB color integer."""
    return (b << 16) + (g << 8) + r

def clear_existing_watermarks(header_shapes):
    """Remove shapes previously added by this script."""
    for i in range(header_shapes.Count, 0, -1):
        shape = header_shapes.Item(i)
        try:
            alt_text = getattr(shape, "AlternativeText", "") or ""
            if alt_text.startswith(WATERMARK_TAG):
                shape.Delete()
        except Exception:
            continue

def add_tiled_watermarks_to_header(header, text: str):
    """Tile four watermark variants across the page."""
    shapes = header.Shapes
    clear_existing_watermarks(shapes)

    try:
        section = header.Range.Sections(1)
        page_width = float(section.PageSetup.PageWidth)
        page_height = float(section.PageSetup.PageHeight)
    except Exception:
        page_width = float(header.PageSetup.PageWidth)
        page_height = float(header.PageSetup.PageHeight)

    variants = [
        {"font_size": 40, "rotation": 315},
        {"font_size": 16, "rotation": 330},
        {"font_size": 12, "rotation": 345},
        {"font_size": 30, "rotation": 300},
    ]

    step_x = 320.0
    step_y = 240.0

    y = -120.0
    row_index = 0
    tile_index = 0

    while y <= page_height + 120.0:
        x_offset = -160.0 + (step_x / 2.0 if row_index % 2 == 1 else 0.0)
        x = x_offset
        while x <= page_width + 160.0:
            variant = variants[tile_index % len(variants)]
            font_size = variant["font_size"]
            rotation = variant["rotation"]

            msoTextEffect1 = getattr(c, "msoTextEffect1", 0)
            msoSendBehindText = getattr(c, "msoSendBehindText", 5)
            wdRelHPage = getattr(c, "wdRelativeHorizontalPositionPage", 1)
            wdRelVPage = getattr(c, "wdRelativeVerticalPositionPage", 1)

            shape = shapes.AddTextEffect(
                msoTextEffect1, text, "Arial", font_size, False, False, x, y
            )

            shape.Rotation = rotation
            shape.Line.Visible = False
            shape.Fill.Visible = True
            shape.Fill.ForeColor.RGB = rgb(180, 180, 180)
            shape.Fill.Transparency = 0.5
            shape.WrapFormat.AllowOverlap = True
            shape.RelativeHorizontalPosition = wdRelHPage
            shape.RelativeVerticalPosition = wdRelVPage

            try:
                shape.LockAspectRatio = True
            except Exception:
                pass
            try:
                shape.ZOrder(msoSendBehindText)
            except Exception:
                pass

            try:
                shape.AlternativeText = f"{WATERMARK_TAG}::{text}"
            except Exception:
                pass

            x += step_x
            tile_index += 1

        y += step_y
        row_index += 1

def add_watermarks_to_docx(input_path: str, output_path: str):
    """Add complex tiled watermarks to DOCX file."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    pythoncom.CoInitialize()
    word = None
    doc = None

    try:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(os.path.abspath(input_path))

        watermark_text = f"{datetime.now().strftime('%Y-%m-%d %H.%M.%S')}_AI Race"

        wdHeaderFooterPrimary = getattr(c, "wdHeaderFooterPrimary", 1)
        for section in doc.Sections:
            header = section.Headers(wdHeaderFooterPrimary)
            add_tiled_watermarks_to_header(header, watermark_text)

        out_abs = os.path.abspath(output_path)
        doc.SaveAs2(out_abs)

    finally:
        if doc:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def process_single_file(args: Tuple[str, str]) -> Tuple[str, bool, str]:
    """
    Process a single file for parallel execution.

    Args:
        args: Tuple of (input_path, output_path)

    Returns:
        Tuple of (input_path, success, error_message)
    """
    input_path, output_path = args

    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        add_watermarks_to_docx(input_path, output_path)
        return input_path, True, ""
    except Exception as e:
        return input_path, False, str(e)


def add_watermarks_batch(file_pairs: List[Tuple[str, str]], max_workers: int = None, max_retries: int = 3) -> List[Tuple[str, bool, str]]:
    """
    Add watermarks to multiple files in parallel with progress tracking and retry mechanism.

    Args:
        file_pairs: List of (input_path, output_path) tuples
        max_workers: Maximum number of parallel workers (default: CPU count)
        max_retries: Maximum number of retry attempts for failed files (default: 3)

    Returns:
        List of (input_path, success, error_message) tuples
    """
    if max_workers is None:
        max_workers = min(multiprocessing.cpu_count(), len(file_pairs))

    all_results = []
    remaining_pairs = file_pairs.copy()

    print(f"🔄 Starting batch watermarking with {len(file_pairs)} files, max {max_retries} retries")

    for retry_round in range(max_retries + 1):  # +1 for initial attempt
        if not remaining_pairs:
            break

        round_desc = f"Round {retry_round + 1}" if retry_round > 0 else "Initial"
        print(f"\n📋 {round_desc}: Processing {len(remaining_pairs)} file(s)")

        # Prepare arguments for this round
        args_list = remaining_pairs

        round_results = []

        # Use ProcessPoolExecutor for CPU-bound tasks (Word COM operations)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks for this round
            future_to_args = {
                executor.submit(process_single_file, args): args
                for args in args_list
            }

            # Process results with progress bar
            with tqdm(total=len(remaining_pairs), desc=f"Round {retry_round + 1}", unit="file") as pbar:
                for future in as_completed(future_to_args):
                    args = future_to_args[future]
                    try:
                        result = future.result()
                        round_results.append(result)

                        input_path, success, error_msg = result
                        if success:
                            pbar.set_postfix_str(f"✅ {os.path.basename(input_path)}")
                        else:
                            pbar.set_postfix_str(f"❌ {os.path.basename(input_path)}: {error_msg[:50]}...")

                    except Exception as exc:
                        input_path = args[0]
                        result = (input_path, False, str(exc))
                        round_results.append(result)
                        pbar.set_postfix_str(f"❌ {os.path.basename(input_path)}: {str(exc)[:50]}...")

                    pbar.update(1)

        # Add successful results to final results
        successful_this_round = [result for result in round_results if result[1]]
        all_results.extend(successful_this_round)

        # Check for failed files in this round
        failed_this_round = [result for result in round_results if not result[1]]

        if failed_this_round:
            # Extract the file pairs that failed for retry
            failed_paths = {result[0] for result in failed_this_round}
            remaining_pairs = [pair for pair in remaining_pairs if pair[0] in failed_paths]

            print(f"⚠️  Round {retry_round + 1} completed: {len(successful_this_round)} successful, {len(failed_this_round)} failed")

            if retry_round < max_retries:
                print(f"🔄 Retrying {len(remaining_pairs)} failed file(s) in next round...")
                # Add failed results with retry information
                for result in failed_this_round:
                    input_path, success, error_msg = result
                    retry_msg = f"[Round {retry_round + 1} failed] {error_msg}"
                    all_results.append((input_path, False, retry_msg))
            else:
                print(f"❌ Maximum retries ({max_retries}) reached. {len(remaining_pairs)} files still failed.")
                # Add final failed results
                all_results.extend(failed_this_round)
        else:
            print(f"✅ Round {retry_round + 1} completed: All {len(successful_this_round)} files processed successfully!")
            break

    # Final summary
    successful_final = [result for result in all_results if result[1]]
    failed_final = [result for result in all_results if not result[1]]

    print(f"\n📊 Final Results:")
    print(f"✅ Total successful: {len(successful_final)}")
    print(f"❌ Total failed: {len(failed_final)}")
    print(f"🔄 Total rounds: {retry_round + 1}")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Add complex tiled watermarks to DOCX files with sequential processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/add_watermark.py test.docx
  python scripts/add_watermark.py folder/document.docx --max-retries 5
  python scripts/add_watermark.py . --max-retries 2

This script adds complex tiled watermarks to DOCX files using Windows COM.
Input files are read from: data/docx/<relative_path>
Output files are saved to: data/watermark/<relative_path>

Files are processed sequentially for safety - each file is fully closed and saved
before processing the next one. Failed files are automatically retried.
        """
    )
    parser.add_argument("relative_path", help="Relative path to DOCX file or folder")
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Ignored - sequential processing for safety (kept for compatibility)"
    )
    parser.add_argument(
        "--preserve-structure", "-p",
        action="store_true",
        default=True,
        help="Preserve directory structure in output (default: True)"
    )
    parser.add_argument(
        "--max-retries", "-r",
        type=int,
        default=3,
        help="Maximum number of retry attempts for failed files (default: 3)"
    )

    args = parser.parse_args()

    # Get script directory and derive project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Define base directories
    docx_dir = project_root / "data" / "docx"
    watermark_dir = project_root / "data" / "watermark"

    # Input path
    input_path = docx_dir / args.relative_path

    # Collect all docx files to process
    docx_files = []
    if input_path.is_file():
        if input_path.suffix.lower() == '.docx':
            docx_files = [input_path]
        else:
            print(f"❌ Error: {input_path} is not a .docx file")
            sys.exit(1)
    elif input_path.is_dir():
        docx_files = list(input_path.glob("**/*.docx"))
        if not docx_files:
            print(f"❌ Error: No .docx files found in {input_path}")
            sys.exit(1)
    else:
        print(f"❌ Error: Path {input_path} does not exist")
        sys.exit(1)

    total_files = len(docx_files)
    print(f"🔍 Found {total_files} file(s) to process")

    # Prepare file pairs for batch processing
    file_pairs = []
    for docx_file in docx_files:
        # Calculate relative path from docx directory
        relative_path = docx_file.relative_to(docx_dir)

        # Create output path in watermark directory
        if args.preserve_structure:
            output_file = watermark_dir / relative_path
        else:
            # Flatten structure - just use filename
            output_file = watermark_dir / docx_file.name

        file_pairs.append((str(docx_file), str(output_file)))

    print(f"📂 Input directory:  {docx_dir}")
    print(f"💾 Output directory: {watermark_dir}")
    print(f"🔒 Sequential processing: {total_files} files (each fully closed before next)")

    try:
        # Process files sequentially with progress tracking and retry mechanism
        results = add_watermarks_batch(file_pairs, max_workers=args.workers, max_retries=args.max_retries)

        # Process results
        success_count = sum(1 for _, success, _ in results if success)
        failed_count = total_files - success_count

        print(f"\n📊 Processing completed!")
        print(f"✅ Successful: {success_count}")
        print(f"❌ Failed: {failed_count}")

        if failed_count > 0:
            print("\n❌ Failed files:")
            for input_path, success, error_msg in results:
                if not success:
                    print(f"  - {Path(input_path).relative_to(docx_dir)}: {error_msg}")
            sys.exit(1)
        else:
            print("🎉 All files processed successfully!")

    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
