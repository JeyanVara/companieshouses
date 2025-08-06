#!/usr/bin/env python3
import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

print("Checking FTS5 setup...")

# Check if FTS table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='companies_fts'")
if not cursor.fetchone():
    print("Creating FTS5 table...")
    cursor.execute("""
    CREATE VIRTUAL TABLE companies_fts USING fts5(
        company_number UNINDEXED,
        company_name,
        previous_names,
        registered_office_address,
        tokenize='porter unicode61'
    )
    """)

# Populate FTS table from existing data
cursor.execute("SELECT COUNT(*) FROM companies")
company_count = cursor.fetchone()[0]
print(f"Found {company_count:,} companies to index...")

if company_count > 0:
    print("Populating FTS index...")
    cursor.execute("""
    INSERT INTO companies_fts (company_number, company_name, previous_names, registered_office_address)
    SELECT 
        company_number,
        company_name,
        COALESCE(previous_names, ''),
        COALESCE(registered_office_address_line_1, '') || ' ' || 
        COALESCE(registered_office_locality, '') || ' ' || 
        COALESCE(registered_office_postal_code, '')
    FROM companies
    """)
    
    conn.commit()
    print("✅ FTS index populated!")

conn.close()
