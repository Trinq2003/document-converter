#!/usr/bin/env python3
"""
DOCX → PDF converter (Windows, Word COM)

Usage:
  python scripts/convert_docx_to_pdf.py <relative_path>

Where <relative_path> points inside data/docx. It can be a file or a folder.
The script mirrors the directory structure under data/pdf and writes .pdf files.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Tuple

# Optional progress bar
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


def export_docx_to_pdf(input_path: str, output_path: str) -> None:
    """
    Convert a single DOCX to PDF using Word COM automation.
    Overwrites the output file if it exists.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        doc = word.Documents.Open(os.path.abspath(input_path))

        out_abs = os.path.abspath(output_path)
        # 17 == wdFormatPDF
        doc.SaveAs2(out_abs, FileFormat=17)
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


def collect_docx_files(root_docx_dir: Path, target: Path) -> List[Path]:
    """Return a list of .docx files under target (file or directory)."""
    if target.is_file():
        return [target] if target.suffix.lower() == ".docx" and not target.name.startswith("~$") else []
    if target.is_dir():
        return [p for p in target.rglob("*.docx") if not p.name.startswith("~$")]
    return []


def build_output_path(pdf_dir: Path, docx_dir: Path, docx_file: Path) -> Path:
    """Map data/docx/<relpath>.docx → data/pdf/<relpath>.pdf"""
    rel = docx_file.relative_to(docx_dir)
    return (pdf_dir / rel).with_suffix(".pdf")


def main():
    parser = argparse.ArgumentParser(
        description="Recursively convert DOCX to PDF, mirroring data/docx → data/pdf"
    )
    parser.add_argument("relative_path", help="Relative path under data/docx (file or folder)")
    parser.add_argument(
        "--skip-existing", action="store_true", default=False,
        help="Skip conversion if output PDF already exists"
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    docx_dir = project_root / "data" / "docx"
    pdf_dir = project_root / "data" / "pdf"

    input_path = docx_dir / args.relative_path

    if not input_path.exists():
        print(f"❌ Error: Path {input_path} does not exist")
        sys.exit(1)

    files = collect_docx_files(docx_dir, input_path)
    if not files:
        print(f"❌ Error: No .docx files found in {input_path}")
        sys.exit(1)

    total = len(files)
    print(f"🔍 Found {total} DOCX file(s)")
    print(f"📂 Input base:  {docx_dir}")
    print(f"💾 Output base: {pdf_dir}")

    successes = 0
    failures: List[Tuple[Path, str]] = []

    iterator = tqdm(files, desc="Converting", unit="file") if TQDM_AVAILABLE else files
    for docx_file in iterator:
        try:
            out_path = build_output_path(pdf_dir, docx_dir, docx_file)
            if args.skip_existing and out_path.exists():
                continue
            export_docx_to_pdf(str(docx_file), str(out_path))
            successes += 1
        except Exception as e:
            failures.append((docx_file, str(e)))

    print("\n📊 Done")
    print(f"✅ Converted: {successes}")
    print(f"❌ Failed:    {len(failures)}")

    if failures:
        print("\nFailed files:")
        for f, err in failures:
            try:
                rel = f.relative_to(docx_dir)
            except Exception:
                rel = f
            print(f" - {rel}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()


