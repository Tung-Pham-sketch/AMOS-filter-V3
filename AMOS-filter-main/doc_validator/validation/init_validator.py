# init_validator.py
import logging
from .db_connector import DBConnector
from .rule_manager import RuleManager
from . import helpers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONNECTION_STRING = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-7BI6STN;"
    "Database=AMOS-filter-validation;"
    "Trusted_Connection=yes;"
)


def initialize_validation_engine():
    """Call this ONCE at application startup."""
    logger.info("Initializing validation engine...")

    db_connector = DBConnector(CONNECTION_STRING)
    rule_manager = RuleManager(db_connector)
    rule_manager.load_all_rules()
    helpers.initialize_rules(rule_manager)

    logger.info("Validation engine ready!")
    return rule_manager


# Global instance (initialized once)
_rule_manager = None


def get_rule_manager():
    global _rule_manager
    if _rule_manager is None:
        _rule_manager = initialize_validation_engine()
    return _rule_manager