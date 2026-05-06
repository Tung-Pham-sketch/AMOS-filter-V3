"""
Diagnostic script to troubleshoot import errors
Run this in your AMOS-filter-main directory
"""

import sys
import os

print("=" * 70)
print("IMPORT DIAGNOSTIC")
print("=" * 70)
print()

# Check current directory
print(f"Current directory: {os.getcwd()}")
print()

# Check if file exists
pipeline_path = "doc_validator/core/excel_pipeline.py"
print(f"Checking for: {pipeline_path}")
print(f"File exists: {os.path.exists(pipeline_path)}")
print()

if os.path.exists(pipeline_path):
    # Check file size
    file_size = os.path.getsize(pipeline_path)
    print(f"File size: {file_size:,} bytes")
    print()

    # Check if process_excel function exists in file
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        content = f.read()

    has_process_excel = 'def process_excel(' in content
    print(f"Contains 'def process_excel(': {has_process_excel}")
    print()

    # Count lines
    lines = content.split('\n')
    print(f"Total lines: {len(lines)}")
    print()

    # Show first 30 lines
    print("First 30 lines of file:")
    print("-" * 70)
    for i, line in enumerate(lines[:30], 1):
        print(f"{i:3d}: {line}")
    print()

# Try to import and see what happens
print("=" * 70)
print("ATTEMPTING IMPORT")
print("=" * 70)
print()

try:
    # Clear any cached imports
    if 'doc_validator.core.excel_pipeline' in sys.modules:
        del sys.modules['doc_validator.core.excel_pipeline']
        print("✓ Cleared cached module")

    from doc_validator.core import excel_pipeline

    print("✓ Import successful!")
    print()

    # Check what's in the module
    print("Functions in module:")
    for name in dir(excel_pipeline):
        if not name.startswith('_'):
            obj = getattr(excel_pipeline, name)
            if callable(obj):
                print(f"  - {name}()")
    print()

    # Try to access process_excel
    if hasattr(excel_pipeline, 'process_excel'):
        print("✓ process_excel function found!")
    else:
        print("✗ process_excel function NOT found!")
        print()
        print("Available functions:")
        for name in dir(excel_pipeline):
            if callable(getattr(excel_pipeline, name)) and not name.startswith('_'):
                print(f"  - {name}")

except Exception as e:
    print(f"✗ Import failed: {e}")
    print()
    import traceback

    traceback.print_exc()

print()
print("=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)