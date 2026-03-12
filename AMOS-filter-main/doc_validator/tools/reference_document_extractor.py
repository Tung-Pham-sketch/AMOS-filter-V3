# doc_validator/tools/reference_document_extractor.py
"""
Reference Document Extractor
=============================

Extracts which document type (AMM, SRM, CMM, etc.) is referenced in each work order
and adds a "Reference Document" column to the output.

Also cross-checks against the "Revision Status of Maintenance Data" work order.
"""

import re
import pandas as pd
from typing import List, Set, Optional


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

    # Check each reference keyword
    for keyword in ref_keywords:
        keyword_upper = keyword.upper()

        # Look for patterns like:
        # "IAW AMM 32-41-05"
        # "REF SRM B787-51"
        # "PER CMM 73-21-00"
        # "AMM REV: 163"

        # Pattern 1: Linking keyword followed by doc type
        # (IAW|REF|PER|REFER|ACCORDING TO) + AMM/SRM/etc
        pattern1 = r'\b(?:IAW|REF|REFER|PER|ACCORDING\s+TO)\s+' + re.escape(keyword_upper)
        if re.search(pattern1, text_upper):
            return keyword

        # Pattern 2: Doc type at start of line or after certain words
        # "AMM 32-41-05", "CHECK AMM 71-21"
        pattern2 = r'\b' + re.escape(keyword_upper) + r'\s+[A-Z0-9\-]'
        if re.search(pattern2, text_upper):
            return keyword

        # Pattern 3: Doc type followed by REV
        # "AMM REV: 163"
        pattern3 = r'\b' + re.escape(keyword_upper) + r'\s+REV'
        if re.search(pattern3, text_upper):
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


def add_reference_document_with_validation(
        df: pd.DataFrame,
        ref_keywords: List[str]
) -> pd.DataFrame:
    """
    Main function: Extract reference documents AND validate against revision status.

    Args:
        df: Input DataFrame
        ref_keywords: List of valid reference document types

    Returns:
        DataFrame with "Reference Document" column added
    """
    # Step 1: Extract approved documents from Revision Status WO
    approved_docs = extract_approved_documents_from_revision_status(df)

    # Step 2: Add Reference Document column
    df = add_reference_document_column(df, ref_keywords)

    # Step 3: Show summary of validation
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

    return df