# doc_validator/tools/reference_document_extractor.py
"""
Reference Document Extractor
=============================

Extracts which document type (AMM, SRM, CMM, etc.) is referenced in each work order
and adds a "Reference Document" column to the output.

Now reads document types from the database table ref_document_types.
"""

import re
import pandas as pd
from typing import List, Set, Optional


def get_ref_keywords_from_database(connection_string: str = None) -> List[str]:
    """
    Load document types from ref_document_types table in database.

    Args:
        connection_string: Optional SQL Server connection string

    Returns:
        List of document codes (e.g., ['AMM', 'SRM', 'CMM', 'DMC', ...])
    """
    # Fallback list if database is not available
    fallback_keywords = [
        'AMM', 'SRM', 'CMM', 'FIM', 'IPD', 'DMC', 'MP',
        'SB', 'EO', 'EOD', 'NDT', 'NDT02', 'SWPM', 'AIPC'
    ]

    if not connection_string:
        # Try to get from rule_manager if available
        try:
            from doc_validator.validation.helpers import get_rule_manager
            rule_manager = get_rule_manager()
            if rule_manager and hasattr(rule_manager, 'ref_keywords'):
                return rule_manager.ref_keywords
        except:
            pass
        return fallback_keywords

    # Try to load from database
    try:
        import pyodbc

        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Query active document types from database
        cursor.execute("""
            SELECT doc_code 
            FROM ref_document_types 
            WHERE is_active = 1
            ORDER BY doc_code
        """)

        rows = cursor.fetchall()
        keywords = [row[0] for row in rows]

        cursor.close()
        conn.close()

        if keywords:
            print(f"   ✓ Loaded {len(keywords)} document types from database")
            return keywords
        else:
            print("   ⚠️ No document types found in database, using fallback")
            return fallback_keywords

    except Exception as e:
        print(f"   ⚠️ Could not load from database: {e}")
        print("   Using fallback keyword list")
        return fallback_keywords


def extract_approved_documents_from_revision_status(df: pd.DataFrame) -> Set[str]:
    """
    Find the "Revision Status" work order and extract approved document types.

    Args:
        df: Input DataFrame

    Returns:
        Set of approved document types (e.g., {'AMM', 'SRM', 'FIM'})
    """
    approved_docs = set()

    # Look for revision status in DES column
    if 'DES' not in df.columns:
        print("⚠️  Warning: DES column not found, cannot extract approved documents")
        return approved_docs

    # Find rows with "REVISION STATUS" in DES
    revision_status_rows = df[df['DES'].str.contains(
        'REVISION STATUS',
        case=False,
        na=False
    )]

    if revision_status_rows.empty:
        print("⚠️  Warning: No 'Revision Status' work order found in DES column")
        return approved_docs

    # Get the DES content
    des_content = revision_status_rows.iloc[0]['DES']

    print("=" * 70)
    print("FOUND REVISION STATUS WORK ORDER")
    print("=" * 70)
    print()

    # Extract document types from lines like:
    # "AMM REV: 163 DATE: 28 FEB 2026"
    # "SRM REV: 14 DATE: 27 NOV 2021"
    # Ignore "N/A REV: N/A DATE: N/A"

    pattern = r'\b([A-Z]{2,10})\s+REV:\s*([^\s]+)'
    matches = re.findall(pattern, des_content)

    for doc_type, rev in matches:
        # Skip N/A entries
        if doc_type.upper() == 'N/A':
            continue

        approved_docs.add(doc_type)

    print(f"Approved Document Types in Revision Status:")
    for doc in sorted(approved_docs):
        print(f"  ✓ {doc}")

    print()
    print("=" * 70)
    print()

    return approved_docs


def extract_reference_document(
        text: str,
        ref_keywords: List[str]
) -> Optional[str]:
    """
    Extract the referenced document type from text.

    Args:
        text: The wo_text_action.text content
        ref_keywords: List of valid reference document types (AMM, SRM, etc.)

    Returns:
        Document type (e.g., 'AMM') or None if no reference found
    """
    if not text or not isinstance(text, str):
        return None

    text_upper = text.upper()

    # Sort keywords by length (longest first) to match specific ones first
    # e.g., "NDT02" before "NDT"
    sorted_keywords = sorted(ref_keywords, key=len, reverse=True)

    # Check each reference keyword
    for keyword in sorted_keywords:
        keyword_upper = keyword.upper()

        # Pattern 1: Linking keyword followed by doc type
        # (IAW|REF|PER|REFER|ACCORDING TO) + AMM/SRM/etc
        pattern1 = r'\b(?:IAW|I\.A\.W|REF|REFER|REFERENCE|PER|ACCORDING\s+TO)\s+' + re.escape(keyword_upper)
        if re.search(pattern1, text_upper):
            return keyword

        # Pattern 2: Doc type at start of line or after certain words
        # "AMM 32-41-05", "CHECK AMM 71-21", "REPLACE CMM 25-21-95"
        pattern2 = r'\b' + re.escape(keyword_upper) + r'\s+[A-Z0-9\-]'
        if re.search(pattern2, text_upper):
            return keyword

        # Pattern 3: Doc type followed by REV
        # "AMM REV: 163", "SRM REV 14"
        pattern3 = r'\b' + re.escape(keyword_upper) + r'\s+REV'
        if re.search(pattern3, text_upper):
            return keyword

        # Pattern 4: Doc type in common formats
        # "DMC-B787-A-44-26-11"
        pattern4 = r'\b' + re.escape(keyword_upper) + r'[\-/]'
        if re.search(pattern4, text_upper):
            return keyword

    return None


def add_reference_document_column(
        df: pd.DataFrame,
        ref_keywords: List[str]
) -> pd.DataFrame:
    """
    Add "Reference Document" column to DataFrame.

    Args:
        df: Input DataFrame
        ref_keywords: List of valid reference document types

    Returns:
        DataFrame with new "Reference Document" column
    """
    print("=" * 70)
    print("EXTRACTING REFERENCE DOCUMENTS")
    print("=" * 70)
    print()
    print(f"Looking for document types: {', '.join(sorted(ref_keywords))}")
    print()

    # Find text column
    text_col = 'wo_text_action.text'
    if text_col not in df.columns:
        print(f"⚠️  Warning: {text_col} column not found")
        df['Reference Document'] = ''
        return df

    # Extract reference document for each row
    df['Reference Document'] = df[text_col].apply(
        lambda text: extract_reference_document(text, ref_keywords) or ''
    )

    # Count how many of each type
    ref_counts = df[df['Reference Document'] != '']['Reference Document'].value_counts()

    print("Reference Documents Found:")
    if not ref_counts.empty:
        for doc_type, count in ref_counts.items():
            print(f"  {doc_type}: {count} references")
    else:
        print("  (none found)")

    print()
    print(f"Total rows with references: {(df['Reference Document'] != '').sum()}")
    print(f"Total rows without references: {(df['Reference Document'] == '').sum()}")
    print()
    print("=" * 70)
    print()

    return df


def get_document_descriptions_from_database(connection_string: str = None) -> pd.DataFrame:
    """
    Get document types with descriptions from database.

    Args:
        connection_string: Optional SQL Server connection string

    Returns:
        DataFrame with columns: doc_code, description, requires_revision
    """
    if not connection_string:
        print("   ⚠️ No connection string provided for descriptions")
        # Return empty DataFrame if no connection
        return pd.DataFrame(columns=['doc_code', 'description', 'requires_revision'])

    try:
        import pyodbc

        print(f"   🔗 Connecting to database for descriptions...")
        conn = pyodbc.connect(connection_string)

        # Query document types with descriptions
        query = """
            SELECT 
                doc_code,
                description,
                requires_revision
            FROM ref_document_types 
            WHERE is_active = 1
            ORDER BY doc_code
        """

        df = pd.read_sql(query, conn)
        conn.close()

        print(f"   ✓ Loaded descriptions for {len(df)} document types")

        return df

    except Exception as e:
        print(f"   ⚠️ Could not load descriptions from database: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame(columns=['doc_code', 'description', 'requires_revision'])


def create_reference_summary_sheet(
        df: pd.DataFrame,
        approved_docs: Set[str],
        connection_string: str = None
) -> pd.DataFrame:
    """
    Create a summary sheet showing all detected document types.

    Args:
        df: Main DataFrame with Reference Document column
        approved_docs: Set of approved documents from Revision Status
        connection_string: SQL Server connection string

    Returns:
        DataFrame for Reference Summary sheet
    """
    print()
    print("=" * 70)
    print("CREATING REFERENCE SUMMARY SHEET")
    print("=" * 70)

    # Get unique referenced documents
    referenced_docs = set(df[df['Reference Document'] != '']['Reference Document'].unique())

    print(f"Found {len(referenced_docs)} unique document types")

    if not referenced_docs:
        # Return empty summary if no references found
        print("No references found, returning empty summary")
        return pd.DataFrame({
            'Document Code': [],
            'Description': [],
            'Count in Workpack': [],
            'In Revision Status': [],
            'Requires Revision': []
        })

    # Get descriptions from database
    doc_info_df = get_document_descriptions_from_database(connection_string)

    if doc_info_df.empty:
        print("⚠️ No descriptions loaded from database")
    else:
        print(f"✓ Description database has {len(doc_info_df)} entries")

    # Count references
    ref_counts = df[df['Reference Document'] != '']['Reference Document'].value_counts()

    # Build summary rows
    summary_rows = []

    for doc_code in sorted(referenced_docs):
        # Get description from database
        description = ''
        requires_rev = ''

        if not doc_info_df.empty:
            match = doc_info_df[doc_info_df['doc_code'] == doc_code]
            if not match.empty:
                description = match.iloc[0]['description']
                requires_rev = 'Yes' if match.iloc[0]['requires_revision'] else 'No'
                print(f"  ✓ {doc_code}: {description}")
            else:
                print(f"  ⚠️ {doc_code}: No description found in database")

        # Check if in revision status
        in_rev_status = 'Yes' if doc_code in approved_docs else 'No'

        # Get count
        count = ref_counts.get(doc_code, 0)

        summary_rows.append({
            'Document Code': doc_code,
            'Description': description,
            'Count in Workpack': count,
            'In Revision Status': in_rev_status,
            'Requires Revision': requires_rev
        })

    summary_df = pd.DataFrame(summary_rows)

    print(f"\n✓ Summary sheet created with {len(summary_df)} rows")
    print("=" * 70)
    print()

    return summary_df


def add_reference_document_with_validation(
        df: pd.DataFrame,
        ref_keywords: List[str] = None,
        connection_string: str = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Main function: Extract reference documents AND validate against revision status.

    Args:
        df: Input DataFrame
        ref_keywords: Optional list of document types (if None, loads from database)
        connection_string: Optional SQL Server connection string

    Returns:
        Tuple of (main_df, summary_df):
            - main_df: DataFrame with "Reference Document" column added
            - summary_df: DataFrame for Reference Summary sheet
    """
    # Load keywords from database if not provided
    if ref_keywords is None:
        ref_keywords = get_ref_keywords_from_database(connection_string)

    # Step 1: Extract approved documents from Revision Status WO
    approved_docs = extract_approved_documents_from_revision_status(df)

    # Step 2: Add Reference Document column
    df = add_reference_document_column(df, ref_keywords)

    # Step 3: Create summary sheet
    summary_df = create_reference_summary_sheet(df, approved_docs, connection_string)

    # Step 4: Show validation summary
    if approved_docs:
        print("=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print()

        # Get unique referenced documents (excluding empty)
        referenced_docs = set(df[df['Reference Document'] != '']['Reference Document'].unique())

        if referenced_docs:
            print("Documents referenced in work orders:")
            for doc in sorted(referenced_docs):
                if doc in approved_docs:
                    print(f"  ✓ {doc} - Listed in Revision Status")
                else:
                    print(f"  ⚠️  {doc} - NOT in Revision Status (missing!)")

            # Show missing from approved list
            referenced_but_not_approved = referenced_docs - approved_docs
            if referenced_but_not_approved:
                print()
                print("⚠️  WARNING: The following documents are used but NOT in Revision Status:")
                for doc in sorted(referenced_but_not_approved):
                    print(f"     • {doc}")
        else:
            print("No reference documents found in work orders")

        print()
        print("=" * 70)
        print()

    return df, summary_df