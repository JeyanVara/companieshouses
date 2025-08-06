#!/usr/bin/env python3
"""
Final import script with all fixes applied
"""

import os
import sys
import csv
import sqlite3
import json
import time
from datetime import datetime
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')
BATCH_SIZE = 10000
PROGRESS_INTERVAL = 10000

# Column names in the CSV (with spaces!)
COLUMN_MAPPING = {
    'company_number': ' CompanyNumber',  # Note the space!
    'company_name': 'CompanyName',
    'company_status': 'CompanyStatus',
    'incorporation_date': 'IncorporationDate',
    'dissolution_date': 'DissolutionDate',
    'company_category': 'CompanyCategory',
    'country_of_origin': 'CountryOfOrigin',
    'address_line_1': 'RegAddress.AddressLine1',
    'address_line_2': ' RegAddress.AddressLine2',  # Space!
    'post_town': 'RegAddress.PostTown',
    'county': 'RegAddress.County',
    'country': 'RegAddress.Country',
    'postcode': 'RegAddress.PostCode',
    'po_box': 'RegAddress.POBox',
    'care_of': 'RegAddress.CareOf',
    'acc_ref_day': 'Accounts.AccountRefDay',
    'acc_ref_month': 'Accounts.AccountRefMonth',
    'acc_last_made_up': 'Accounts.LastMadeUpDate',
    'acc_category': 'Accounts.AccountCategory',
    'conf_stmt_last_made_up': ' ConfStmtLastMadeUpDate',  # Space!
    'mort_charges': 'Mortgages.NumMortCharges'
}

def clean_value(value):
    """Clean and normalize CSV values"""
    if not value or value.strip() == '':
        return None
    value = value.strip()
    if value.upper() in ['NULL', 'NONE', 'N/A']:
        return None
    return value

def parse_sic_codes(row):
    """Parse SIC codes from multiple columns"""
    codes = []
    for i in range(1, 5):
        sic_text = row.get(f'SICCode.SicText_{i}', '')
        if sic_text and sic_text.strip():
            parts = sic_text.strip().split(' - ')
            if parts[0].strip():
                codes.append(parts[0].strip())
    return json.dumps(codes) if codes else None

def parse_previous_names(row):
    """Parse previous company names"""
    names = []
    for i in range(1, 11):
        name = clean_value(row.get(f' PreviousName_{i}.CompanyName', ''))  # Space!
        if name:
            names.append(name)
    return json.dumps(names) if names else None

def parse_date(date_str):
    """Parse date in DD/MM/YYYY format to YYYY-MM-DD"""
    if not date_str or date_str.strip() == '':
        return None
    try:
        parts = date_str.strip().split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}"
    except:
        pass
    return date_str

def normalize_status(status):
    """Normalize company status values"""
    if not status:
        return None
    
    # Map common status values to our expected format
    status_map = {
        'Active': 'active',
        'ACTIVE': 'active',
        'Dissolved': 'dissolved',
        'DISSOLVED': 'dissolved',
        'Liquidation': 'liquidation',
        'LIQUIDATION': 'liquidation',
        'Receivership': 'receivership',
        'Administration': 'administration',
        'Voluntary Arrangement': 'voluntary-arrangement',
        'Converted/Closed': 'converted-closed',
        'Insolvency Proceedings': 'insolvency-proceedings'
    }
    
    # Return mapped value or original if not in map
    return status_map.get(status, status.lower())

def import_companies(csv_path, resume_from=0):
    """Import companies from CSV to database"""
    
    print(f"📂 Opening database: {DATABASE_PATH}")
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=MEMORY")
    
    cursor = conn.cursor()
    
    # Count existing records
    cursor.execute("SELECT COUNT(*) FROM companies")
    existing_count = cursor.fetchone()[0]
    print(f"📊 Existing companies: {existing_count:,}")
    
    # Clear if starting fresh
    if existing_count > 0 and resume_from == 0:
        response = input("Clear existing data? (y/n): ")
        if response.lower() == 'y':
            cursor.execute("DELETE FROM companies")
            conn.commit()
            print("Cleared existing data.")
    
    # Prepare insert statement
    insert_sql = """
    INSERT OR REPLACE INTO companies (
        company_number, company_name, company_status, company_status_detail,
        date_of_creation, date_of_cessation, company_type, jurisdiction,
        registered_office_address_line_1, registered_office_address_line_2,
        registered_office_locality, registered_office_region,
        registered_office_country, registered_office_postal_code,
        registered_office_po_box, registered_office_care_of,
        sic_codes, previous_names,
        accounting_reference_date_day, accounting_reference_date_month,
        last_accounts_made_up_to, accounts_category,
        confirmation_statement_last_made_up_to,
        has_charges, has_been_liquidated, has_insolvency_history
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Statistics
    start_time = time.time()
    rows_processed = 0
    rows_inserted = 0
    rows_skipped = 0
    errors = defaultdict(int)
    status_counts = defaultdict(int)
    
    print(f"\n🚀 Starting import from row {resume_from:,}...")
    print("Press Ctrl+C to pause and resume later\n")
    
    batch_data = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Skip to resume point
            for _ in range(resume_from):
                next(reader)
            
            for row in reader:
                rows_processed += 1
                
                try:
                    # Get company number using our mapping
                    company_number = clean_value(row.get(COLUMN_MAPPING['company_number'], ''))
                    
                    if not company_number:
                        rows_skipped += 1
                        errors['missing_company_number'] += 1
                        continue
                    
                    # Get and normalize status
                    raw_status = clean_value(row.get(COLUMN_MAPPING['company_status'], ''))
                    company_status = normalize_status(raw_status)
                    if raw_status:
                        status_counts[raw_status] += 1
                    
                    # Convert account dates
                    acc_ref_day = clean_value(row.get(COLUMN_MAPPING['acc_ref_day'], ''))
                    acc_ref_month = clean_value(row.get(COLUMN_MAPPING['acc_ref_month'], ''))
                    
                    try:
                        acc_ref_day = int(acc_ref_day) if acc_ref_day else None
                        acc_ref_month = int(acc_ref_month) if acc_ref_month else None
                    except:
                        acc_ref_day = None
                        acc_ref_month = None
                    
                    company_data = (
                        company_number,
                        clean_value(row.get(COLUMN_MAPPING['company_name'], '')),
                        company_status,  # Now normalized
                        None,  # company_status_detail
                        parse_date(row.get(COLUMN_MAPPING['incorporation_date'], '')),
                        parse_date(row.get(COLUMN_MAPPING['dissolution_date'], '')),
                        clean_value(row.get(COLUMN_MAPPING['company_category'], '')),
                        clean_value(row.get(COLUMN_MAPPING['country_of_origin'], '')),
                        # Address
                        clean_value(row.get(COLUMN_MAPPING['address_line_1'], '')),
                        clean_value(row.get(COLUMN_MAPPING['address_line_2'], '')),
                        clean_value(row.get(COLUMN_MAPPING['post_town'], '')),
                        clean_value(row.get(COLUMN_MAPPING['county'], '')),
                        clean_value(row.get(COLUMN_MAPPING['country'], '')),
                        clean_value(row.get(COLUMN_MAPPING['postcode'], '')),
                        clean_value(row.get(COLUMN_MAPPING['po_box'], '')),
                        clean_value(row.get(COLUMN_MAPPING['care_of'], '')),
                        # SIC and names
                        parse_sic_codes(row),
                        parse_previous_names(row),
                        # Accounts
                        acc_ref_day,
                        acc_ref_month,
                        parse_date(row.get(COLUMN_MAPPING['acc_last_made_up'], '')),
                        clean_value(row.get(COLUMN_MAPPING['acc_category'], '')),
                        # Confirmation
                        parse_date(row.get(COLUMN_MAPPING['conf_stmt_last_made_up'], '')),
                        # Flags
                        1 if row.get(COLUMN_MAPPING['mort_charges'], '0') not in ['0', ''] else 0,
                        0,  # has_been_liquidated
                        0   # has_insolvency_history
                    )
                    
                    batch_data.append(company_data)
                    
                    # Insert batch when full
                    if len(batch_data) >= BATCH_SIZE:
                        cursor.executemany(insert_sql, batch_data)
                        conn.commit()
                        rows_inserted += len(batch_data)
                        batch_data = []
                    
                except Exception as e:
                    errors[str(type(e).__name__)] += 1
                    rows_skipped += 1
                    if rows_processed < 5:
                        print(f"Error on row {rows_processed}: {e}")
                        print(f"Company number: {row.get(COLUMN_MAPPING['company_number'], 'NOT FOUND')}")
                
                # Show progress
                if rows_processed % PROGRESS_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = rows_processed / elapsed if elapsed > 0 else 0
                    eta = (5600000 - resume_from - rows_processed) / rate / 60 if rate > 0 else 0
                    
                    print(f"Progress: {resume_from + rows_processed:,} rows | "
                          f"Rate: {rate:.0f}/sec | "
                          f"Inserted: {rows_inserted:,} | "
                          f"Skipped: {rows_skipped:,} | "
                          f"ETA: {eta:.0f} min")
    
    except KeyboardInterrupt:
        print(f"\n\n⏸️  Import paused at row {resume_from + rows_processed:,}")
        print(f"To resume, run: python scripts/import_companies_final.py --resume {resume_from + rows_processed}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Failed at row {resume_from + rows_processed:,}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Insert remaining batch
        if batch_data:
            try:
                cursor.executemany(insert_sql, batch_data)
                conn.commit()
                rows_inserted += len(batch_data)
            except Exception as e:
                print(f"Error inserting final batch: {e}")
        
        # Final statistics
        elapsed = time.time() - start_time
        print(f"\n📊 Import Statistics:")
        print(f"Duration: {elapsed/60:.1f} minutes")
        print(f"Rows processed: {rows_processed:,}")
        print(f"Rows inserted: {rows_inserted:,}")
        print(f"Rows skipped: {rows_skipped:,}")
        if elapsed > 0:
            print(f"Average rate: {rows_processed/elapsed:.0f} rows/second")
        
        if errors:
            print(f"\n⚠️  Errors encountered:")
            for error_type, count in errors.items():
                print(f"  {error_type}: {count:,}")
        
        if status_counts:
            print(f"\n📊 Status values found:")
            for status, count in list(status_counts.items())[:10]:
                print(f"  {status}: {count:,}")
        
        # Update search index only if we inserted data
        if rows_inserted > 0:
            print("\n🔄 Updating search index...")
            cursor.execute("INSERT INTO companies_fts(companies_fts) VALUES('rebuild')")
            conn.commit()
        
        # Final count
        cursor.execute("SELECT COUNT(*) FROM companies")
        final_count = cursor.fetchone()[0]
        print(f"\n✅ Total companies in database: {final_count:,}")
        
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Import Companies House data')
    parser.add_argument('--resume', type=int, default=0, help='Resume from row number')
    
    args = parser.parse_args()
    
    # Find CSV file
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'bulk_data')
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    if csv_files:
        csv_path = os.path.join(data_dir, csv_files[0])
        import_companies(csv_path, args.resume)
    else:
        print("❌ No CSV file found!")
