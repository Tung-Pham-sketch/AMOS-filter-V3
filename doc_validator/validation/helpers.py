# doc_validator/validation/helpers.py (DB-DRIVEN - Your Schema)

import re
from typing import Optional

from .rule_manager import RuleManager

# Global rule manager instance (initialized at startup)
_rule_manager: Optional[RuleManager] = None


def initialize_rules(rule_manager: RuleManager) -> None:
    """
    Initialize the global rule manager.
    Must be called at application startup.

    Args:
        rule_manager: RuleManager instance with loaded rules
    """
    global _rule_manager
    _rule_manager = rule_manager


def get_rule_manager() -> RuleManager:
    """Get the global rule manager instance."""
    if _rule_manager is None:
        raise RuntimeError("Rule manager not initialized. Call initialize_rules() first.")
    return _rule_manager


def has_valid_execution_response(text: str) -> bool:
    """Check if text contains valid execution-only response patterns."""
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()

    # Strip HTML tags
    cleaned = re.sub(r'<[^>]+>', ' ', text)
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    # Convert to uppercase for pattern matching
    cleaned = cleaned.upper()

    # Check against all execution patterns from DB
    for pattern in rm.execution_patterns:
        if pattern.search(cleaned):
            return True

    return False


def is_seq_auto_valid(seq_value) -> bool:
    """
    Check if SEQ should be automatically marked as Valid.
    Currently not used based on your schema - all SEQs are either STRICT_REF or EXECUTION_ONLY.
    Kept for compatibility.

    Args:
        seq_value: The SEQ field value

    Returns:
        bool: Always False (no auto-valid SEQs in your schema)
    """
    # Based on your schema, you don't have 'auto_valid' SEQs
    # SEQ 2.x, 3.x are EXECUTION_ONLY, not auto-valid
    return False


def is_seq_9x(seq_value) -> bool:
    """
    Check if SEQ requires strict validation (9.x pattern).
    Uses STRICT_REF rule type from database.

    Args:
        seq_value: The SEQ field value

    Returns:
        bool: True if SEQ is STRICT_REF type
    """
    rm = get_rule_manager()
    return rm.is_strict_ref_seq(seq_value)


def is_seq_4x(seq_value) -> bool:
    """
    Check if SEQ is 4.x (execution format required).
    Based on your schema, 4.x is EXECUTION_ONLY.

    Args:
        seq_value: The SEQ field value

    Returns:
        bool: True if SEQ is 4.x
    """
    if seq_value is None:
        return False

    seq_str = str(seq_value).strip()
    return seq_str.startswith("4.")


def contains_header_skip_keyword(header_text) -> bool:
    """
    Check if wo_text_action.header contains keywords that should skip validation.
    Uses skip_rules table where applies_to='HEADER'.

    Args:
        header_text: The wo_text_action.header field value

    Returns:
        bool: True if header contains skip keywords
    """
    if not isinstance(header_text, str):
        return False

    rm = get_rule_manager()

    # Normalize: uppercase and remove extra spaces
    normalized = " ".join(header_text.upper().split())

    # Check against all header skip keywords from DB
    for keyword in rm.header_skip_keywords:
        if keyword in normalized:
            return True

    return False


def fix_common_typos(text: str) -> str:
    """Normalize common typos in maintenance documentation."""
    if not isinstance(text, str):
        return text

    rm = get_rule_manager()

    t = text
    # Normalize "REV" formats
    t = re.sub(r"(?i)\bREV[:\.]?\s*(\d+)\b", r"REV \1", t)
    t = re.sub(r"(?i)\brev(\d+)\b", r"rev \1", t)
    t = re.sub(r"([A-Za-z0-9\)\]])rev(\d+)\b", r"\1 rev \2", t, flags=re.IGNORECASE)

    # Space after REF
    t = re.sub(r"(?i)\bREF([A-Z])", r"REF \1", t)

    # Ensure space after REF keywords when followed by a digit
    for ref in rm.ref_keywords:
        t = re.sub(fr"(?i)\b({re.escape(ref)})(\d)", r"\1 \2", t)

    # Collapse multiple spaces
    t = re.sub(r"\s{2,}", " ", t)
    return t


def contains_skip_phrase(text: str) -> bool:
    """
    Check if text contains phrases that should skip validation.
    Uses skip_rules table where applies_to='TEXT'.
    """
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    up = text.upper()

    # Check skip phrases from DB (applies_to='TEXT')
    for phrase in rm.skip_phrases:
        if phrase in up:
            return True

    # Additional hardcoded cross-reference checks
    # (Can be moved to DB if needed)

    # Cross-Workstep (WT) references
    if "REFER RESULT WT" in up or "REFER WT " in up:
        return True

    # Cross-Workorder (WO) references
    if re.search(r"\bWO\s*[:\-]\s*[0-9`' ]+", up):
        return True

    # WO together with EOD (Engineering Order)
    if "EOD" in up and re.search(r"\bWO\s*[:\-]\s*[0-9`' ]+", up):
        return True

    return False


def has_referenced_pattern(text: str) -> bool:
    """Check if text uses 'REFERENCED AMM/SRM/etc.' pattern."""
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.referenced_pattern:
        return bool(rm.referenced_pattern.search(text))
    return False


def has_ndt_report(text: str) -> bool:
    """Check for NDT REPORT pattern with document ID."""
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.ndt_report_pattern:
        return bool(rm.ndt_report_pattern.search(text))
    return False


def has_sb_full_number(text: str) -> bool:
    """Check for Service Bulletin with full number."""
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.sb_full_pattern:
        return bool(rm.sb_full_pattern.search(text))
    return False


def has_data_module_task(text: str) -> bool:
    """Check for DATA MODULE TASK pattern (with number)."""
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.data_module_task_pattern:
        return bool(rm.data_module_task_pattern.search(text))
    return False


def has_primary_reference(text: str) -> bool:
    """
    Check if text contains a primary reference keyword (AMM, SRM, CMM, etc.).
    Uses ref_document_types table.
    """
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.ref_keyword_pattern:
        return bool(rm.ref_keyword_pattern.search(text))
    return False


def has_dmc_or_doc_id(text: str) -> bool:
    """
    Check if text contains DMC, B787 doc format, or DATA MODULE TASK (without number).
    These indicate a document reference but without the type (AMM/SRM/etc.).
    """
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()

    # DMC pattern
    if rm.dmc_pattern and rm.dmc_pattern.search(text):
        return True

    # B787 document pattern
    if rm.b787_doc_pattern and rm.b787_doc_pattern.search(text):
        return True

    # "DATA MODULE TASK" text (without number)
    if rm.data_module_task_text_pattern and rm.data_module_task_text_pattern.search(text):
        return True

    return False


def has_iaw_keyword(text: str) -> bool:
    """
    Check if text contains linking words (IAW, REF, PER).
    Uses linking_keywords table.
    """
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.iaw_keyword_pattern:
        return bool(rm.iaw_keyword_pattern.search(text))
    return False


def has_ndt02_report(text: str) -> bool:
    """
    Detect NDT02 inspection report numbers such as: NDT02-251516
    """
    if not isinstance(text, str):
        return False

    return bool(re.search(r'\bNDT02-\d{4,}\b', text.upper()))


def has_revision(text: str) -> bool:
    """
    Detect whether a valid revision exists in real-world maintenance text.
    Uses revision_patterns table from database.
    """
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    up = text.upper()

    # Check against all revision patterns from DB
    for pattern in rm.revision_patterns:
        if pattern.search(up):
            return True

    return False


def has_mp_reference(text: str) -> bool:
    """
    Check for MP reference with linking keywords (IAW/REF/PER).
    MP requires linking keywords based on ref_document_types table.
    """
    if not isinstance(text, str):
        return False

    rm = get_rule_manager()
    if rm.mp_with_context_pattern:
        return bool(rm.mp_with_context_pattern.search(text))
    return False


def get_doc_id_pattern() -> Optional[re.Pattern]:
    """Get the document ID pattern from rule manager."""
    rm = get_rule_manager()
    return rm.doc_id_pattern