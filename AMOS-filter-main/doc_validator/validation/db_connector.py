"""
Database connector for validation rules.
Handles MSSQL connections using pyodbc.
Adapted to use existing schema: ref_document_types, linking_keywords,
revision_patterns, execution_patterns, skip_rules, seq_rules, validation_flow
"""

import pyodbc
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DBConnector:
    """Manages database connections and queries for validation rules."""

    def __init__(self, connection_string: str):
        """
        Initialize database connector.

        Args:
            connection_string: MSSQL connection string
                Example: "Driver={ODBC Driver 17 for SQL Server};Server=localhost;Database=ValidationDB;UID=user;PWD=pass"
        """
        self.connection_string = connection_string
        self._connection: Optional[pyodbc.Connection] = None

    def connect(self) -> None:
        """Establish database connection."""
        try:
            self._connection = pyodbc.connect(self.connection_string)
            logger.info("Database connection established")
        except pyodbc.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results as list of dictionaries.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of dictionaries with column names as keys
        """
        if not self._connection:
            self.connect()

        try:
            cursor = self._connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [column[0] for column in cursor.description]

            # Convert rows to dictionaries
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            cursor.close()
            return results

        except pyodbc.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def load_ref_document_types(self) -> List[Dict[str, Any]]:
        """Load reference document types (AMM, SRM, MP, NDT02, etc.)."""
        query = """
            SELECT id, doc_code, requires_revision, requires_linking_keyword, 
                   description, is_active
            FROM ref_document_types
            WHERE is_active = 1
            ORDER BY doc_code
        """
        return self.execute_query(query)

    def load_linking_keywords(self) -> List[Dict[str, Any]]:
        """Load linking keywords (IAW, REF, PER, etc.)."""
        query = """
            SELECT id, keyword, description, is_active
            FROM linking_keywords
            WHERE is_active = 1
            ORDER BY keyword
        """
        return self.execute_query(query)

    def load_revision_patterns(self) -> List[Dict[str, Any]]:
        """Load revision regex patterns."""
        query = """
            SELECT id, regex_pattern, description, is_active
            FROM revision_patterns
            WHERE is_active = 1
            ORDER BY id
        """
        return self.execute_query(query)

    def load_execution_patterns(self) -> List[Dict[str, Any]]:
        """Load execution response regex patterns."""
        query = """
            SELECT id, regex_pattern, description, priority, is_active
            FROM execution_patterns
            WHERE is_active = 1
            ORDER BY priority ASC
        """
        return self.execute_query(query)

    def load_skip_rules(self) -> List[Dict[str, Any]]:
        """Load skip rules (for both HEADER and TEXT)."""
        query = """
            SELECT id, applies_to, keyword, description, is_active
            FROM skip_rules
            WHERE is_active = 1
            ORDER BY applies_to, keyword
        """
        return self.execute_query(query)

    def load_seq_rules(self) -> List[Dict[str, Any]]:
        """Load SEQ behavior rules (9.x strict, 4.x execution, etc.)."""
        query = """
            SELECT id, seq_prefix, rule_type, description, is_active
            FROM seq_rules
            WHERE is_active = 1
            ORDER BY seq_prefix
        """
        return self.execute_query(query)

    def load_validation_flow(self) -> List[Dict[str, Any]]:
        """Load validation flow steps."""
        query = """
            SELECT id, step_order, step_code, description, is_active
            FROM validation_flow
            WHERE is_active = 1
            ORDER BY step_order
        """
        return self.execute_query(query)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()