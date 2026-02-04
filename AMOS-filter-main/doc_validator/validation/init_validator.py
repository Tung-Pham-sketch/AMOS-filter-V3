# doc_validator/validation/init_validator.py
"""
Validation Engine Initialization.
Loads rules from MSSQL database and initializes the validation system.

Call initialize_validation_engine() ONCE at application startup (GUI or CLI).
"""

import logging
from typing import Optional

from .db_connector import DBConnector
from .rule_manager import RuleManager
from . import helpers

logger = logging.getLogger(__name__)

# Global singleton
_rule_manager: Optional[RuleManager] = None


def initialize_validation_engine(connection_string: str) -> RuleManager:
    """
    Initialize the validation engine with database rules.
    Call this ONCE at application startup (GUI or CLI).

    Args:
        connection_string: MSSQL connection string

    Returns:
        RuleManager instance (for reloading rules if needed)

    Example:
        CONNECTION_STRING = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=DESKTOP-7BI6STN;"
            "Database=AMOS-filter-validation;"
            "Trusted_Connection=yes;"
        )

        rule_manager = initialize_validation_engine(CONNECTION_STRING)
    """
    global _rule_manager

    if _rule_manager is not None:
        logger.warning("Validation engine already initialized, reloading rules...")
        _rule_manager.load_all_rules()
        helpers.initialize_rules(_rule_manager)
        return _rule_manager

    logger.info("Initializing validation engine from database...")

    try:
        # 1. Create database connector
        db_connector = DBConnector(connection_string)

        # 2. Test connection
        db_connector.connect()
        logger.info("✓ Database connection successful")
        db_connector.disconnect()

        # 3. Create rule manager
        rule_manager = RuleManager(db_connector)

        # 4. Load all rules from database
        rule_manager.load_all_rules()

        # 5. Initialize helpers module
        helpers.initialize_rules(rule_manager)

        _rule_manager = rule_manager

        logger.info("✓ Validation engine initialized successfully")
        logger.info(f"  - {len(rule_manager.ref_keywords)} reference document types")
        logger.info(f"  - {len(rule_manager.iaw_keywords)} linking keywords")
        logger.info(f"  - {len(rule_manager.execution_patterns)} execution patterns")
        logger.info(f"  - {len(rule_manager.revision_patterns)} revision patterns")
        logger.info(f"  - {len(rule_manager.seq_rules)} SEQ rules")

        return rule_manager

    except Exception as e:
        logger.error(f"✗ Failed to initialize validation engine: {e}")
        raise


def get_rule_manager() -> Optional[RuleManager]:
    """Get the global rule manager instance (if initialized)."""
    return _rule_manager


def reload_rules() -> None:
    """
    Reload all rules from database.
    Useful for runtime rule updates without restarting the application.
    """
    if _rule_manager is None:
        raise RuntimeError("Validation engine not initialized. Call initialize_validation_engine() first.")

    logger.info("Reloading validation rules from database...")
    _rule_manager.reload_rules()
    logger.info("✓ Rules reloaded successfully")