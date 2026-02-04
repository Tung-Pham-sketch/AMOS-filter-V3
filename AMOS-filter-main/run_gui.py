#!/usr/bin/env python3
"""
Main entry point for AMOS Documentation Validator GUI.
Initializes database-driven validation before starting the GUI.
"""

import sys
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def main():
    """Main application entry point."""

    # Database connection string
    CONNECTION_STRING = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=DESKTOP-7BI6STN;"
        "Database=AMOS-filter-validation;"
        "Trusted_Connection=yes;"
    )

    # Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("AMOS Documentation Validator")
    app.setStyle("Fusion")

    # Initialize validation engine BEFORE starting GUI
    try:
        print("=" * 60)
        print("AMOS DOCUMENTATION VALIDATOR")
        print("=" * 60)
        print("\nInitializing validation engine from database...")

        from doc_validator.validation.init_validator import initialize_validation_engine

        rule_manager = initialize_validation_engine(CONNECTION_STRING)

        print("\n✓ Validation engine ready")
        print(f"  - {len(rule_manager.ref_keywords)} reference document types")
        print(f"  - {len(rule_manager.iaw_keywords)} linking keywords")
        print(f"  - {len(rule_manager.execution_patterns)} execution patterns")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n⚠️ WARNING: Could not connect to database: {e}")
        print("Application will use fallback hardcoded rules.\n")

        # Show warning dialog
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Database Connection Failed")
        msg.setText("Could not connect to validation database")
        msg.setInformativeText(
            f"Error: {str(e)}\n\n"
            "The application will continue using fallback validation rules."
        )
        msg.exec()

    # Start GUI
    from doc_validator.interface.main_window import MainWindow

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())