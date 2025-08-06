#!/usr/bin/env python3
"""
Import Companies House bulk data into SQLite - FIXED VERSION
Handles column names with spaces and current CSV format
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
    for i in range(1, 5):  # SICCode.SicText_1 through SicText_4
        sic_text = row.get(f'SICCode.SicText_{i}', '')
        if sic_text and sic_text.strip():
            # Extract numeric code from text like "01110 - Growing of cereals"
            parts = sic_text.strip().split(' - ')
            if parts[0].strip():
                codes.append(parts[0].strip())
    
    return json.dumps(codes) if codes else None

def parse_previous_names(row):
    """Parse previous company names from multiple columns"""
    names = []
    for i in range(1, 11):  # PreviousName_1 through PreviousName_10
        # Note the space in front of the column name!
        name = clean_value(row.get(f' PreviousName_{i}.CompanyName', ''))
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
    return date_str  # Return as-is if parsing fails

def import_companies(csv_path, resume_from=0):
    """Import companies from CSV to database"""
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return
    
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
    
    if existing_count > 0 and resume_from == 0:
        response = input("Database has existing data. Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
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
                    # Extract and clean data - NOTE THE SPACES IN COLUMN NAMES!
                    company_number = clean_value(row.get(' CompanyNumber', ''))  # Space before name!
                    
                    if not company_number:
                        rows_skipped += 1
                        errors['missing_company_number'] += 1
                        continue
                    
                    # Convert account dates
                    acc_ref_day = clean_value(row.get('Accounts.AccountRefDay', ''))
                    acc_ref_month = clean_value(row.get('Accounts.AccountRefMonth', ''))
                    
                    # Convert numeric fields
                    try:
                        acc_ref_day = int(acc_ref_day) if acc_ref_day else None
                        acc_ref_month = int(acc_ref_month) if acc_ref_month else None
                    except:
                        acc_ref_day = None
                        acc_ref_month = None
                    
                    company_data = (
                        company_number,
                        clean_value(row.get('CompanyName', '')),
                        clean_value(row.get('CompanyStatus', '')),
                        None,  # CompanyStatusDetail not in CSV
                        parse_date(row.get('IncorporationDate', '')),
                        parse_date(row.get('DissolutionDate', '')),
                        clean_value(row.get('CompanyCategory', '')),  # This is CompanyType
                        clean_value(row.get('CountryOfOrigin', '')),  # This is jurisdiction
                        # Address fields
                        clean_value(row.get('RegAddress.AddressLine1', '')),
                        clean_value(row.get(' RegAddress.AddressLine2', '')),  # Space!
                        clean_value(row.get('RegAddress.PostTown', '')),
                        clean_value(row.get('RegAddress.County', '')),
                        clean_value(row.get('RegAddress.Country', '')),
                        clean_value(row.get('RegAddress.PostCode', '')),
                        clean_value(row.get('RegAddress.POBox', '')),
                        clean_value(row.get('RegAddress.CareOf', '')),
                        # SIC codes and previous names
                        parse_sic_codes(row),
                        parse_previous_names(row),
                        # Accounts info
                        acc_ref_day,
                        acc_ref_month,
                        parse_date(row.get('Accounts.LastMadeUpDate', '')),
                        clean_value(row.get('Accounts.AccountCategory', '')),
                        # Confirmation statement
                        parse_date(row.get(' ConfStmtLastMadeUpDate', '')),  # Space!
                        # Flags - check if mortgage charges exist
                        1 if row.get('Mortgages.NumMortCharges', '0') not in ['0', ''] else 0,
                        0,  # HasBeenLiquidated not in this CSV
                        0   # HasInsolvencyHistory not in this CSV
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
                    if rows_processed < 10:  # Debug first few errors
                        print(f"Error on row {rows_processed}: {e}")
                
                # Show progress
                if rows_processed % PROGRESS_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = rows_processed / elapsed
                    eta = (5600000 - resume_from - rows_processed) / rate / 60
                    
                    print(f"Progress: {resume_from + rows_processed:,} rows | "
                          f"Rate: {rate:.0f}/sec | "
                          f"Inserted: {rows_inserted:,} | "
                          f"Skipped: {rows_skipped:,} | "
                          f"ETA: {eta:.0f} min")
    
    except KeyboardInterrupt:
        print(f"\n\n⏸️  Import paused at row {resume_from + rows_processed:,}")
        print(f"To resume, run: python scripts/import_companies_fixed.py --resume {resume_from + rows_processed}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"Failed at row {resume_from + rows_processed:,}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Insert remaining batch
        if batch_data:
            cursor.executemany(insert_sql, batch_data)
            conn.commit()
            rows_inserted += len(batch_data)
        
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
        
        # Update search index only if we inserted data
        if rows_inserted > 0:
            print("\n🔄 Updating search index...")
            cursor.execute("INSERT INTO companies_fts(companies_fts) VALUES('rebuild')")
            conn.commit()
            
            # Analyze for query optimization
            print("📊 Analyzing database...")
            cursor.execute("ANALYZE")
        
        # Final count
        cursor.execute("SELECT COUNT(*) FROM companies")
        final_count = cursor.fetchone()[0]
        print(f"\n✅ Total companies in database: {final_count:,}")
        
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Import Companies House data')
    parser.add_argument('--csv', help='Path to CSV file', 
                        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                           'database', 'bulk_data'))
    parser.add_argument('--resume', type=int, default=0, help='Resume from row number')
    
    args = parser.parse_args()
    
    # Find CSV file
    if os.path.isdir(args.csv):
        csv_files = [f for f in os.listdir(args.csv) if f.endswith('.csv')]
        if csv_files:
            csv_path = os.path.join(args.csv, csv_files[0])
        else:
            print(f"❌ No CSV files found in {args.csv}")
            print("Run download_bulk_data.py first!")
            sys.exit(1)
    else:
        csv_path = args.csv
    
    import_companies(csv_path, args.resume)
