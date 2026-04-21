"""
Configuration file for the documentation validator.
Contains all constants and configuration settings.

UPDATED: Added HEADER_SKIP_KEYWORDS for wo_text_action.header filtering
UPDATED: Added "Wrong format" reason for SEQ 4.x validation
"""

# Reason dictionary for validation results (5 states)
REASONS_DICT = {
    "valid": "Valid documentation with reference and revision",
    "ref": "Missing reference documentation (includes incomplete references)",
    "rev": "Missing revision date",
    "format": "Wrong format - SEQ 4.x requires execution pattern format"
}

# Keywords for reference documentation (AMM, SRM, etc.)
# These are the PRIMARY references that count as valid
REF_KEYWORDS = [
    "AMM", "DMC", "SRM", "CMM", "EMM", "SOPM", "SWPM",
    "IPD", "FIM", "TSM", "IPC", "SB", "AD", "SOP", "NDT02",
    "NTO", "MEL", "NEF", "MME", "LMM", "NTM", "DWG", "AIPC", "AMMS",
    "DDG", "VSB", "BSI", "FIM", "FTD", "TIPF", "MNT", "EEL VNA", "EOD", "NDT Manual", "NDT Report",
    "NDTREPORT", "ATR-A"
]

# Keywords for linking words (IAW, REF, PER)
IAW_KEYWORDS = ["IAW", "REF", "PER", "I.A.W"]

# Phrases that should skip validation (valid by default)
# IMPORTANT: Only include phrases that are PURELY procedural and NEVER contain references
# Removed: "MAKE SURE", "ENSURE THAT", "CHECK THAT" (too broad, can appear with incomplete refs)
SKIP_PHRASES = [
    "GET ACCESS", "GAIN ACCESS", "GAINED ACCESS", "ACCESS GAINED",
    "SPARE ORDERED", "ORDERED SPARE",
    "OBEY ALL", "FOLLOW ALL", "COMPLY WITH", "MEASURE AND RECORD", "SET TO INACTIVE", "SEE FIGURE",
    "REFER TO FIGURE"
]

# NEW: Keywords in wo_text_action.header that should mark row as Valid automatically
# These are procedural/setup tasks that don't require documentation references
HEADER_SKIP_KEYWORDS = [
    "CLOSE UP", "CLOSEUP",
    "JOB SET UP", "JOB SETUP", "JOBSETUP", "CLOSE-UP", "CLOSE-UP:", "JOP SET-UP",
    "OPEN ACCESS", "OPENACCESS", "JOB SET-UP 1 - GENERAL",
    "CLOSE ACCESS", "CLOSEACCESS",
    "GENERAL", "JOB SET-UP", "JOB CLOSE-UP"
]

# Invalid characters for folder names
INVALID_CHARACTERS = r'[\\/:*?"<>|]'