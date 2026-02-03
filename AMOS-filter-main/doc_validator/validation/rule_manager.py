"""
Rule Manager - loads and caches validation rules from database.
Adapted to work with existing schema: ref_document_types, linking_keywords,
revision_patterns, execution_patterns, skip_rules, seq_rules, validation_flow
"""

import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
import logging

from .db_connector import DBConnector

logger = logging.getLogger(__name__)


@dataclass
class DocumentTypeRule:
    """Document type behavior rule."""
    code: str
    requires_revision: bool
    requires_linking_keyword: bool
    description: Optional[str] = None


@dataclass
class SeqRule:
    """SEQ prefix behavior rule."""
    prefix: str
    rule_type: str  # 'STRICT_REF', 'EXECUTION_ONLY', etc.
    description: Optional[str] = None


class RuleManager:
    """
    Manages validation rules loaded from database.
    Caches rules in memory for performance.
    """

    def __init__(self, db_connector: DBConnector):
        """
        Initialize rule manager.

        Args:
            db_connector: Database connector instance
        """
        self.db = db_connector

        # Cached rules (loaded on initialization)
        self.ref_keywords: List[str] = []  # AMM, SRM, CMM, etc.
        self.iaw_keywords: List[str] = []  # IAW, REF, PER
        self.skip_phrases: List[str] = []  # TEXT skip rules
        self.header_skip_keywords: List[str] = []  # HEADER skip rules

        # Execution patterns (compiled regex)
        self.execution_patterns: List[re.Pattern] = []

        # Revision patterns (compiled regex)
        self.revision_patterns: List[re.Pattern] = []

        # Document type rules
        self.document_types: Dict[str, DocumentTypeRule] = {}

        # SEQ behavior rules
        self.seq_rules: Dict[str, SeqRule] = {}

        # Precompiled keyword patterns (for performance)
        self.ref_keyword_pattern: Optional[re.Pattern] = None
        self.iaw_keyword_pattern: Optional[re.Pattern] = None
        self.mp_with_context_pattern: Optional[re.Pattern] = None

        # Special patterns (built from document types + linking keywords)
        self.referenced_pattern: Optional[re.Pattern] = None
        self.ndt_report_pattern: Optional[re.Pattern] = None
        self.sb_full_pattern: Optional[re.Pattern] = None
        self.data_module_task_pattern: Optional[re.Pattern] = None
        self.dmc_pattern: Optional[re.Pattern] = None
        self.b787_doc_pattern: Optional[re.Pattern] = None
        self.data_module_task_text_pattern: Optional[re.Pattern] = None
        self.doc_id_pattern: Optional[re.Pattern] = None

    def load_all_rules(self) -> None:
        """Load all rules from database and cache in memory."""
        logger.info("Loading validation rules from database...")

        self._load_document_types()
        self._load_linking_keywords()
        self._load_revision_patterns()
        self._load_execution_patterns()
        self._load_skip_rules()
        self._load_seq_rules()
        self._compile_keyword_patterns()
        self._build_special_patterns()

        logger.info("All validation rules loaded successfully")

    def _load_document_types(self) -> None:
        """Load reference document types from database."""
        doc_types_data = self.db.load_ref_document_types()

        self.ref_keywords = []
        self.document_types = {}

        for row in doc_types_data:
            doc_code = row['doc_code']

            # Add to ref_keywords list
            self.ref_keywords.append(doc_code)

            # Store detailed rule
            doc_type = DocumentTypeRule(
                code=doc_code,
                requires_revision=bool(row['requires_revision']),
                requires_linking_keyword=bool(row['requires_linking_keyword']),
                description=row.get('description')
            )
            self.document_types[doc_code] = doc_type

        logger.info(f"Loaded {len(self.ref_keywords)} reference document types")

    def _load_linking_keywords(self) -> None:
        """Load linking keywords from database."""
        linking_data = self.db.load_linking_keywords()

        self.iaw_keywords = [row['keyword'] for row in linking_data]

        logger.info(f"Loaded {len(self.iaw_keywords)} linking keywords")

    def _load_revision_patterns(self) -> None:
        """Load and compile revision regex patterns from database."""
        revision_data = self.db.load_revision_patterns()

        self.revision_patterns = []

        for row in revision_data:
            pattern_str = row['regex_pattern']
            try:
                compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                self.revision_patterns.append(compiled_pattern)
            except re.error as e:
                logger.warning(f"Invalid revision regex '{pattern_str}': {e}")

        logger.info(f"Loaded {len(self.revision_patterns)} revision patterns")

    def _load_execution_patterns(self) -> None:
        """Load and compile execution regex patterns from database."""
        execution_data = self.db.load_execution_patterns()

        self.execution_patterns = []

        for row in execution_data:
            pattern_str = row['regex_pattern']
            try:
                compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
                self.execution_patterns.append(compiled_pattern)
            except re.error as e:
                logger.warning(f"Invalid execution regex '{pattern_str}': {e}")

        logger.info(f"Loaded {len(self.execution_patterns)} execution patterns")

    def _load_skip_rules(self) -> None:
        """Load skip rules from database (HEADER and TEXT)."""
        skip_data = self.db.load_skip_rules()

        self.skip_phrases = []
        self.header_skip_keywords = []

        for row in skip_data:
            keyword = row['keyword']
            applies_to = row['applies_to']

            if applies_to == 'HEADER':
                self.header_skip_keywords.append(keyword)
            elif applies_to == 'TEXT':
                self.skip_phrases.append(keyword)

        logger.info(f"Loaded {len(self.header_skip_keywords)} header skip keywords")
        logger.info(f"Loaded {len(self.skip_phrases)} text skip phrases")

    def _load_seq_rules(self) -> None:
        """Load SEQ behavior rules from database."""
        seq_data = self.db.load_seq_rules()

        self.seq_rules = {}

        for row in seq_data:
            seq_rule = SeqRule(
                prefix=row['seq_prefix'],
                rule_type=row['rule_type'],
                description=row.get('description')
            )
            self.seq_rules[seq_rule.prefix] = seq_rule

        logger.info(f"Loaded {len(self.seq_rules)} SEQ rules")

    def _compile_keyword_patterns(self) -> None:
        """Compile keyword-based patterns for performance."""
        # REF keyword pattern (AMM, SRM, CMM, etc.)
        if self.ref_keywords:
            ref_pattern_str = r'\b(?:' + '|'.join(re.escape(k) for k in self.ref_keywords) + r')\b'
            self.ref_keyword_pattern = re.compile(ref_pattern_str, re.IGNORECASE)

        # IAW keyword pattern (IAW, REF, PER)
        if self.iaw_keywords:
            iaw_pattern_str = r'\b(?:' + '|'.join(re.escape(k) for k in self.iaw_keywords) + r')\b'
            self.iaw_keyword_pattern = re.compile(iaw_pattern_str, re.IGNORECASE)

        # MP with context pattern (special case for MP)
        if self.iaw_keywords:
            mp_pattern_str = r'\b(?:' + '|'.join(re.escape(k) for k in self.iaw_keywords) + r')\s+MP\b'
            self.mp_with_context_pattern = re.compile(mp_pattern_str, re.IGNORECASE)

        logger.info("Keyword patterns compiled")

    def _build_special_patterns(self) -> None:
        """Build special hardcoded patterns (not in DB yet)."""
        # REFERENCED pattern (e.g., "REFERENCED AMM")
        if self.ref_keywords:
            referenced_str = r'\bREFERENCED\s+(?:' + '|'.join(re.escape(k) for k in self.ref_keywords) + r')\b'
            self.referenced_pattern = re.compile(referenced_str, re.IGNORECASE)

        # Hardcoded special patterns (can be moved to DB later if needed)
        self.ndt_report_pattern = re.compile(r'\bNDT\s+REPORT\s+[A-Z0-9\-]+\b', re.IGNORECASE)
        self.sb_full_pattern = re.compile(r'\bSB\s+[A-Z0-9]{1,5}-[A-Z0-9\-]+\b', re.IGNORECASE)
        self.data_module_task_pattern = re.compile(r'\bDATA\s+MODULE\s+TASK\s+\d+\b', re.IGNORECASE)
        self.dmc_pattern = re.compile(r'\bDMC-?[A-Z0-9\-]+\b', re.IGNORECASE)
        self.b787_doc_pattern = re.compile(r'\bB787-[A-Z0-9\-]+\b', re.IGNORECASE)
        self.data_module_task_text_pattern = re.compile(r'\bDATA\s+MODULE\s+TASK\b', re.IGNORECASE)
        self.doc_id_pattern = re.compile(r'\b[A-Z0-9]{1,4}[0-9A-Z\-]{0,}\d+\b', re.IGNORECASE)

        logger.info("Special patterns built")

    def get_seq_rule(self, seq_value) -> Optional[SeqRule]:
        """
        Get SEQ behavior rule for a given SEQ value.

        Args:
            seq_value: SEQ field value (can be string, float, or int)

        Returns:
            SeqRule if found, None otherwise
        """
        if seq_value is None:
            return None

        seq_str = str(seq_value).strip()

        # Check for exact match first
        if seq_str in self.seq_rules:
            return self.seq_rules[seq_str]

        # Check for prefix match (e.g., "4." matches "4.28")
        for prefix, rule in self.seq_rules.items():
            if seq_str.startswith(prefix):
                return rule

        return None

    def is_strict_ref_seq(self, seq_value) -> bool:
        """Check if SEQ requires strict reference+revision (like 9.x)."""
        rule = self.get_seq_rule(seq_value)
        return rule is not None and rule.rule_type == 'STRICT_REF'

    def is_execution_only_seq(self, seq_value) -> bool:
        """Check if SEQ is execution-only format (like 2.x, 3.x, 4.x, 5.x)."""
        rule = self.get_seq_rule(seq_value)
        return rule is not None and rule.rule_type == 'EXECUTION_ONLY'

    def reload_rules(self) -> None:
        """Reload all rules from database (for runtime updates)."""
        logger.info("Reloading validation rules...")
        self.load_all_rules()