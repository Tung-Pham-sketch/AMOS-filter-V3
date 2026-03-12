#!/usr/bin/env python3
"""
AMOS Filter - System Verification Script
Checks that all components are properly configured and working.

This script automatically detects the project root and adjusts paths.
"""

import sys
import os
from pathlib import Path


def find_project_root():
    """
    Find the AMOS-filter-main project root.
    Looks for the directory containing 'doc_validator' folder.
    """
    current = Path.cwd()

    # Check current directory
    if (current / "doc_validator").exists():
        return current

    # Check if we're inside AMOS-filter-main
    if current.name == "AMOS-filter-main":
        return current

    # Check parent directories
    for parent in current.parents:
        if (parent / "doc_validator").exists():
            return parent
        if parent.name == "AMOS-filter-main":
            return parent

    # Not found
    return None


def check_database_connection():
    """Test database connection."""
    print("\n" + "=" * 60)
    print("1. TESTING DATABASE CONNECTION")
    print("=" * 60)

    try:
        from doc_validator.validation.db_connector import DBConnector

        CONNECTION_STRING = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=DESKTOP-7BI6STN;"
            "Database=AMOS-filter-validation;"
            "Trusted_Connection=yes;"
        )

        print(f"Connection string: {CONNECTION_STRING}")
        print("Connecting...")

        db = DBConnector(CONNECTION_STRING)
        db.connect()

        print("✓ Connected successfully!")

        # Test loading some data
        print("\nTesting data queries...")
        ref_types = db.load_ref_document_types()
        print(f"✓ Loaded {len(ref_types)} reference document types")

        linking = db.load_linking_keywords()
        print(f"✓ Loaded {len(linking)} linking keywords")

        rev_patterns = db.load_revision_patterns()
        print(f"✓ Loaded {len(rev_patterns)} revision patterns")

        exec_patterns = db.load_execution_patterns()
        print(f"✓ Loaded {len(exec_patterns)} execution patterns")

        skip_rules = db.load_skip_rules()
        print(f"✓ Loaded {len(skip_rules)} skip rules")

        seq_rules = db.load_seq_rules()
        print(f"✓ Loaded {len(seq_rules)} SEQ rules")

        db.disconnect()
        print("✓ Disconnected")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_validation_engine():
    """Test validation engine initialization."""
    print("\n" + "=" * 60)
    print("2. TESTING VALIDATION ENGINE")
    print("=" * 60)

    try:
        from doc_validator.validation.init_validator import (
            initialize_validation_engine,
            get_rule_manager
        )

        CONNECTION_STRING = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=DESKTOP-7BI6STN;"
            "Database=AMOS-filter-validation;"
            "Trusted_Connection=yes;"
        )

        print("Initializing validation engine...")
        rule_manager = initialize_validation_engine(CONNECTION_STRING)

        print(f"\n✓ Validation engine initialized")
        print(f"  - {len(rule_manager.ref_keywords)} reference keywords: {rule_manager.ref_keywords[:5]}...")
        print(f"  - {len(rule_manager.iaw_keywords)} IAW keywords: {rule_manager.iaw_keywords}")
        print(f"  - {len(rule_manager.execution_patterns)} execution patterns")
        print(f"  - {len(rule_manager.revision_patterns)} revision patterns")
        print(f"  - {len(rule_manager.seq_rules)} SEQ rules")

        # Test that helpers can access it
        from doc_validator.validation.helpers import get_rule_manager
        rm = get_rule_manager()
        print(f"\n✓ Helpers module can access rule manager")

        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_validation_functions():
    """Test that validation functions work."""
    print("\n" + "=" * 60)
    print("3. TESTING VALIDATION FUNCTIONS")
    print("=" * 60)

    try:
        from doc_validator.validation.engine import check_ref_keywords

        test_cases = [
            ("IAW AMM 12-34-56 REV 10", None, None, None, "Valid"),
            ("PERFORMED STEP 1", "4.1", None, None, "Valid"),
            ("N/A", None, None, None, "N/A"),
            ("", None, None, None, ""),
            ("CHECK PANEL", None, "CLOSE UP", None, "Valid"),
        ]

        print("\nTesting validation cases...")
        passed = 0
        failed = 0

        for text, seq, header, des, expected in test_cases:
            result = check_ref_keywords(text, seq, header, des)
            if result == expected:
                status = "✓"
                passed += 1
            else:
                status = "✗"
                failed += 1
            print(f"{status} '{text[:30]}...' → {result} (expected: {expected})")

        print(f"\n✓ Validation functions working ({passed}/{len(test_cases)} passed)")
        return failed == 0

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_file_structure(project_root):
    """Verify project file structure."""
    print("\n" + "=" * 60)
    print("4. CHECKING FILE STRUCTURE")
    print("=" * 60)

    print(f"Project root: {project_root}\n")

    required_files = [
        "doc_validator/__init__.py",
        "doc_validator/config.py",
        "doc_validator/validation/__init__.py",
        "doc_validator/validation/db_connector.py",
        "doc_validator/validation/rule_manager.py",
        "doc_validator/validation/init_validator.py",
        "doc_validator/validation/helpers.py",
        "doc_validator/validation/engine.py",
        "doc_validator/core/__init__.py",
        "doc_validator/core/excel_pipeline.py",
        "doc_validator/core/excel_io.py",
        "doc_validator/interface/__init__.py",
        "doc_validator/interface/main_window.py",
        "doc_validator/interface/workers/__init__.py",
        "doc_validator/interface/workers/processing_worker.py",
    ]

    missing = []
    for file in required_files:
        path = project_root / file
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} - MISSING")
            missing.append(file)

    if missing:
        print(f"\n✗ {len(missing)} file(s) missing")
        return False
    else:
        print(f"\n✓ All required files present")
        return True


def check_imports():
    """Test that all modules can be imported."""
    print("\n" + "=" * 60)
    print("5. TESTING MODULE IMPORTS")
    print("=" * 60)

    modules = [
        "doc_validator.config",
        "doc_validator.validation.db_connector",
        "doc_validator.validation.rule_manager",
        "doc_validator.validation.init_validator",
        "doc_validator.validation.helpers",
        "doc_validator.validation.engine",
        "doc_validator.core.excel_pipeline",
        "doc_validator.core.excel_io",
        "doc_validator.interface.main_window",
        "doc_validator.interface.workers.processing_worker",
    ]

    failed = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module} - FAILED: {e}")
            failed.append((module, e))

    if failed:
        print(f"\n✗ {len(failed)} module(s) failed to import")
        for module, error in failed:
            print(f"   {module}: {error}")
        return False
    else:
        print(f"\n✓ All modules imported successfully")
        return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("AMOS FILTER - SYSTEM VERIFICATION")
    print("=" * 60)

    # Find project root
    project_root = find_project_root()

    if project_root is None:
        print("\n✗ ERROR: Could not find project root (AMOS-filter-main)")
        print("\nPlease run this script from:")
        print("  - Inside AMOS-filter-main directory")
        print("  - OR from a subdirectory of AMOS-filter-main")
        return 1

    print(f"\nProject root found: {project_root}")

    # Change to project root for imports to work
    original_dir = Path.cwd()
    os.chdir(project_root)

    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        results = []

        # Run checks
        results.append(("File Structure", check_file_structure(project_root)))
        results.append(("Module Imports", check_imports()))
        results.append(("Database Connection", check_database_connection()))
        results.append(("Validation Engine", check_validation_engine()))
        results.append(("Validation Functions", check_validation_functions()))

        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)

        for name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status} - {name}")

        all_passed = all(passed for _, passed in results)

        print("\n" + "=" * 60)
        if all_passed:
            print("✓ ALL CHECKS PASSED - SYSTEM READY")
            print("=" * 60)
            print("\nYou can now run the application:")
            print(f"  cd {project_root}")
            print("  python run_gui.py")
            return 0
        else:
            print("✗ SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
            print("=" * 60)
            failed_count = sum(1 for _, passed in results if not passed)
            print(f"\n{failed_count} check(s) failed. Please fix the errors and try again.")
            return 1

    finally:
        # Restore original directory
        os.chdir(original_dir)


if __name__ == "__main__":
    sys.exit(main())