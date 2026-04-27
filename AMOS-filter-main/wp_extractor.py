"""
AMM Data Extraction Tool - Python Version
Replaces VFP program with proper date/time conversion
"""

import pyodbc
import pandas as pd
from dbfread import DBF
from datetime import datetime, timedelta
import time

# ============================================================================
# Configuration
# ============================================================================
SQL_SERVER_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}',
    'server': 'xxx',
    'database': 'xxx',
    'uid': 'xxx',
    'pwd': 'xxx'
}

WP_CUR_PATH = 'D:\D\VFP_HSBD\HDBD\wp_cur.dbf'
from datetime import datetime

output_dir = r'D:\D\AMOS-filter-main-new\INPUT'
OUTPUT_FILE = f'{output_dir}/Current_Workpack_{datetime.now().strftime("%Y.%m.%d_%Hh%Mm%Ss")}.xlsx'


# ============================================================================
# Helper Functions
# ============================================================================

def amos_date_to_datetime(days_since_1971):
    """Convert AMOS integer date (days since 1971-12-31) to datetime"""
    if pd.isna(days_since_1971) or days_since_1971 == 0:
        return None
    base_date = datetime(1971, 12, 31)
    return base_date + timedelta(days=int(days_since_1971))


def amos_time_to_str(minutes):
    """Convert AMOS time (float minutes) to HH:MM string"""
    if pd.isna(minutes) or minutes == 0:
        return ''
    total_minutes = int(minutes)
    hours = total_minutes // 60
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}"


def clean_text(text):
    """Remove null chars, CR, LF from text fields"""
    if pd.isna(text):
        return ''
    return str(text).replace('\x00', '').replace('\r', '').replace('\n', ' ').strip()


# ============================================================================
# Main Extraction Logic
# ============================================================================

def read_sql_from_wpbur(record_number):
    """Read SQL query from wp_cur.dbf at specific record number"""
    print(f"Reading SQL query from wp_cur record {record_number}...")

    table = DBF(WP_CUR_PATH, encoding='cp1252')

    for idx, record in enumerate(table, start=1):
        if idx == record_number:
            # Get the remark field (memo field with SQL)
            sql = record.get('REMARK', '')

            # Clean up the SQL (remove brackets, line breaks)
            sql = sql.replace('[', '').replace(']', '').replace('\r', ' ').replace('\n', ' ')

            print(f"  SQL length: {len(sql)} characters")
            return sql.strip()

    raise ValueError(f"Record {record_number} not found in wp_cur.dbf")


def execute_with_injection(conn, sql_template, ids_to_inject=None):
    """
    Execute SQL with ID injection into IN () clause

    Args:
        conn: Database connection
        sql_template: SQL with IN () placeholder
        ids_to_inject: List of IDs to inject (None for step 1)

    Returns:
        DataFrame with results
    """
    if ids_to_inject is not None:
        # Find the IN () clause and inject IDs
        if '()' not in sql_template:
            raise ValueError("SQL template must contain IN () placeholder")

        # Convert IDs to comma-separated string
        id_str = ','.join(str(int(id_val)) for id_val in ids_to_inject)

        # Replace IN () with IN (id1,id2,...)
        sql = sql_template.replace('IN ()', f'IN ({id_str})')
    else:
        sql = sql_template

    print(f"  Executing SQL (length: {len(sql)} chars)...")

    # Execute and return DataFrame
    df = pd.read_sql(sql, conn)
    print(f"  ✓ Returned {len(df)} rows")

    return df


def main():
    """Main extraction pipeline"""
    start_time = time.time()

    print("=" * 80)
    print("AMM Data Extraction - Python Version")
    print("=" * 80)

    # Connect to SQL Server
    conn_str = (
        f"DRIVER={SQL_SERVER_CONFIG['driver']};"
        f"SERVER={SQL_SERVER_CONFIG['server']};"
        f"DATABASE={SQL_SERVER_CONFIG['database']};"
        f"UID={SQL_SERVER_CONFIG['uid']};"
        f"PWD={SQL_SERVER_CONFIG['pwd']}"
    )

    print("\nConnecting to SQL Server...")
    conn = pyodbc.connect(conn_str)
    print("✓ Connected")

    # ========================================================================
    # Step 1: WP_HEADER
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: Fetching WP_HEADER")
    print("=" * 80)

    sql_1 = read_sql_from_wpbur(1)
    wp_header = execute_with_injection(conn, sql_1)

    if len(wp_header) == 0:
        print("⚠ No WP_HEADER records found. Check filters.")
        return

    # ========================================================================
    # Step 2: WP_SEQUENCE
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: Fetching WP_SEQUENCE")
    print("=" * 80)

    wpno_ids = wp_header['WPNO_I'].dropna().unique()
    print(f"  Injecting {len(wpno_ids)} WPNO_I values")

    sql_2 = read_sql_from_wpbur(2)
    wp_sequence = execute_with_injection(conn, sql_2, wpno_ids)

    # ========================================================================
    # Step 3: WO_HEADER
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: Fetching WO_HEADER")
    print("=" * 80)

    wo_ids = wp_sequence['WO'].dropna().unique()
    print(f"  Injecting {len(wo_ids)} WO values")

    sql_3 = read_sql_from_wpbur(3)
    wo_header = execute_with_injection(conn, sql_3, wo_ids)

    # ========================================================================
    # Step 4: WORKSTEP_LINK
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: Fetching WORKSTEP_LINK")
    print("=" * 80)

    sql_4 = read_sql_from_wpbur(4)
    workstep_link = execute_with_injection(conn, sql_4, wo_ids)

    # ========================================================================
    # Step 5: WO_TEXT_DESCRIPTION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 5: Fetching WO_TEXT_DESCRIPTION")
    print("=" * 80)

    descno_ids = workstep_link['DESCNO_I'].dropna().unique()
    print(f"  Injecting {len(descno_ids)} DESCNO_I values")

    sql_5 = read_sql_from_wpbur(5)
    wo_text_description = execute_with_injection(conn, sql_5, descno_ids)

    # ========================================================================
    # Step 6: WO_TEXT_ACTION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 6: Fetching WO_TEXT_ACTION")
    print("=" * 80)

    workstep_link_ids = workstep_link['WORKSTEP_LINKNO_I'].dropna().unique()
    print(f"  Injecting {len(workstep_link_ids)} WORKSTEP_LINKNO_I values")

    sql_6 = read_sql_from_wpbur(6)
    wo_text_action = execute_with_injection(conn, sql_6, workstep_link_ids)

    # ========================================================================
    # Step 7: TIME_CAPTURED_ADDITIONAL
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 7: Fetching TIME_CAPTURED_ADDITIONAL")
    print("=" * 80)

    actionno_ids = wo_text_action['ACTIONNO_I'].dropna().unique()
    print(f"  Injecting {len(actionno_ids)} ACTIONNO_I values")

    sql_7 = read_sql_from_wpbur(7)
    time_captured_additional = execute_with_injection(conn, sql_7, actionno_ids)

    # ========================================================================
    # Step 8: TIME_CAPTURED
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 8: Fetching TIME_CAPTURED")
    print("=" * 80)

    bookingno_ids = time_captured_additional['BOOKINGNO_I'].dropna().unique()
    print(f"  Injecting {len(bookingno_ids)} BOOKINGNO_I values")

    sql_8 = read_sql_from_wpbur(8)
    time_captured = execute_with_injection(conn, sql_8, bookingno_ids)

    # ========================================================================
    # Step 9: Join all tables (Python equivalent of VFP final query)
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 9: Joining all tables")
    print("=" * 80)

    # Join sequence: wp_header -> wp_sequence -> wo_header -> workstep_link
    # -> wo_text_description -> wo_text_action -> time_captured_additional -> time_captured

    print("  Joining WP_HEADER + WP_SEQUENCE...")
    result = wp_header.merge(wp_sequence, on='WPNO_I', how='inner')
    print(f"    Result: {len(result)} rows")

    print("  Joining + WO_HEADER...")
    result = result.merge(wo_header, left_on='WO', right_on='EVENT_PERFNO_I', how='inner')
    print(f"    Result: {len(result)} rows")

    print("  Joining + WORKSTEP_LINK...")
    result = result.merge(workstep_link, on='EVENT_PERFNO_I', how='inner', suffixes=('', '_wsl'))
    print(f"    Result: {len(result)} rows")

    '''print("  Joining + WO_TEXT_DESCRIPTION...")
    result = result.merge(wo_text_description, on='DESCNO_I', how='left', suffixes=('', '_desc'))
    print(f"    Result: {len(result)} rows")

    print("  Joining + WO_TEXT_ACTION...")
    result = result.merge(wo_text_action, on='WORKSTEP_LINKNO_I', how='left', suffixes=('', '_action'))
    print(f"    Result: {len(result)} rows")'''

    print("  Joining + WO_TEXT_DESCRIPTION...")
    # Rename TEXT to WO_TEXT and HEADER to WO_HEADER before merging to avoid conflicts
    wo_text_description_renamed = wo_text_description.rename(columns={
        'TEXT': 'WO_TEXT',
        'HEADER': 'WO_HEADER'
    })
    result = result.merge(wo_text_description_renamed, on='DESCNO_I', how='left')
    print(f"    Result: {len(result)} rows")

    print("  Joining + WO_TEXT_ACTION...")
    # WO_TEXT_ACTION keeps its TEXT and HEADER columns as-is
    result = result.merge(wo_text_action, on='WORKSTEP_LINKNO_I', how='left', suffixes=('', '_action'))
    print(f"    Result: {len(result)} rows")

    print("  Joining + TIME_CAPTURED_ADDITIONAL...")
    result = result.merge(time_captured_additional, left_on='ACTIONNO_I', right_on='ITEMNO_I', how='left',
                          suffixes=('', '_tca'))
    print(f"    Result: {len(result)} rows")

    print("  Joining + TIME_CAPTURED...")
    result = result.merge(time_captured, on='BOOKINGNO_I', how='left', suffixes=('', '_tc'))
    print(f"    Result: {len(result)} rows")

    # ========================================================================
    # Step 10: Date/Time Conversions & Transformations
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 10: Converting dates and times")
    print("=" * 80)

    # Convert AMOS dates to readable format (YYYY-MM-DD)
    print("  Converting START_DATE, END_DATE...")
    result['START_DATE'] = result['START_DATE'].apply(
        lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
    )
    result['END_DATE'] = result['END_DATE'].apply(
        lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
    )

    if 'ACT_START_DATE' in result.columns:
        result['ACT_START_DATE'] = result['ACT_START_DATE'].apply(
            lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
        )

    if 'ACT_END_DATE' in result.columns:
        result['ACT_END_DATE'] = result['ACT_END_DATE'].apply(
            lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
        )

    if 'ACTION_DATE' in result.columns:
        print("  Converting ACTION_DATE...")
        result['ACTION_DATE'] = result['ACTION_DATE'].apply(
            lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
        )

    if 'CLOSING_DATE' in result.columns:
        result['CLOSING_DATE'] = result['CLOSING_DATE'].apply(
            lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
        )

    if 'WORKSTEP_DATE' in result.columns:
        result['WORKSTEP_DATE'] = result['WORKSTEP_DATE'].apply(
            lambda x: amos_date_to_datetime(x).strftime('%Y-%m-%d') if amos_date_to_datetime(x) else ''
        )

    # Convert AMOS times (minutes) to HH:MM
    print("  Converting ACTION_TIME, WORKSTEP_TIME...")
    if 'ACTION_TIME' in result.columns:
        result['ACTION_TIME'] = result['ACTION_TIME'].apply(amos_time_to_str)

    if 'WORKSTEP_TIME' in result.columns:
        result['WORKSTEP_TIME'] = result['WORKSTEP_TIME'].apply(amos_time_to_str)

    if 'DURATION' in result.columns:
        print("  Converting DURATION...")
        result['DURATION'] = result['DURATION'].apply(amos_time_to_str)

    # HOUR and EST_MH are already converted in SQL query step 8

    # ========================================================================
    # Step 11: Build composite fields
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 11: Building composite fields")
    print("=" * 80)

    # SEQ = 'prefix.seqno'
    #result['SEQ'] = "'" + result['SEQNO_PREFIX_I'].astype(str) + '.' + result['SEQNO'].astype(str)
    result['SEQ'] = result['SEQNO_PREFIX_I'].fillna(0).astype(int).astype(str) + '.' + result['SEQNO'].fillna(0).astype(int).astype(str)
    # WOWSTEP = WPNO_I-WO-WORKSTEP-BOOKINGNO_I
    result['WORKSTEP_STR'] = result['SEQUENCENO'].apply(
        lambda x: f"{int(x):02d}" if pd.notna(x) else ''
    )
    result['WOWSTEP'] = (
            result['WPNO_I'].astype(str) + '-' +
            result['WO'].astype(str) + '-' +
            result['WORKSTEP_STR'] + '-' +
            result['BOOKINGNO_I'].fillna('').astype(str)
    )
    result['WOWSTEP'] = result['WOWSTEP'].str.rstrip('-')

    # ========================================================================
    # Step 12: Clean text fields
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 12: Cleaning text fields")
    print("=" * 80)

    text_columns = ['TEXT', 'TEXT_HTML', 'HEADER', 'WO_TEXT']
    for col in text_columns:
        if col in result.columns:
            print(f"  Cleaning {col}...")
            result[col] = result[col].apply(clean_text)

    # Rename TEXT_HTML to DES for consistency
    if 'TEXT_HTML' in result.columns:
        result.rename(columns={'TEXT_HTML': 'DES'}, inplace=True)

    # ========================================================================
    # Step 13: Deduplication (keep first occurrence of each WOWSTEP)
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 13: Deduplicating by WOWSTEP")
    print("=" * 80)

    print(f"  Before deduplication: {len(result)} rows")
    result = result.drop_duplicates(subset=['WOWSTEP'], keep='first')
    print(f"  After deduplication: {len(result)} rows")

    # ========================================================================
    # Step 14: Rename columns and select for output
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 14: Renaming columns and selecting output")
    print("=" * 80)

    # Rename columns to match desired output names
    column_renames = {
        'WPNO': 'WP',
        'STATE': 'WO_state',
        'SEQUENCENO': 'Workstep',
        'HEADER': 'wo_text_action.header',
        'TEXT': 'wo_text_action.text'
    }

    print("  Renaming columns...")
    result.rename(columns=column_renames, inplace=True)

    # Define desired column order (adjust as needed)
    '''output_columns = [
        'STATION', 'AC_REGISTR', 'AC_TYP', 'WPNO_I',
        'START_DATE', 'END_DATE', 'PROJECTNO', 'WPNO',
        'SEQNO_PREFIX_I', 'SEQNO', 'SEQ',
        'WO', 'WOWSTEP', 'STATE', 'WO_TEXT', 'DES',
        'WORKSTEP_LINKNO_I', 'SEQUENCENO',
        'HEADER', 'TEXT', 'ACTION_DATE', 'ACTION_TIME',
        'SIGN_PERFORMED', 'USER_DEPARTMENT', 'USER_SIGN',
        'DURATION', 'USER_JOB', 'SCOPE', 'HOUR', 'EST_MH',
        'BOOKINGNO_I'
    ]'''

    output_columns = [
        'STATION', 'AC_REGISTR', 'AC_TYP', 'WPNO_I',
        'START_DATE', 'END_DATE', 'WP',
        'SEQNO_PREFIX_I', 'SEQNO', 'SEQ',
        'WO', 'WO_state', 'WO_TEXT', 'DES',
        'WORKSTEP_LINKNO_I', 'Workstep',
        'wo_text_action.header', 'wo_text_action.text', 'ACTION_DATE', 'ACTION_TIME',
        'SIGN_PERFORMED', 'USER_DEPARTMENT', 'USER_SIGN',
        'DURATION', 'USER_JOB', 'SCOPE', 'HOUR', 'EST_MH',
        'BOOKINGNO_I'
    ]

    # Keep only columns that exist
    output_columns = [col for col in output_columns if col in result.columns]

    result_final = result[output_columns].copy()

    print(f"  Selected {len(output_columns)} columns")

    # ========================================================================
    # Step 15: Export to Excel
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 15: Exporting to Excel")
    print("=" * 80)

    print(f"  Writing to {OUTPUT_FILE}...")
    result_final.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')

    end_time = time.time()
    elapsed = end_time - start_time

    print("\n" + "=" * 80)
    print("✓ EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"  Output file: {OUTPUT_FILE}")
    print(f"  Total rows: {len(result_final)}")
    print(f"  Total time: {elapsed:.2f} seconds")
    print("=" * 80)

    conn.close()


if __name__ == '__main__':
    main()
