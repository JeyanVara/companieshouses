#!/usr/bin/env python3
import sqlite3
import os

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

print("Fixing company_status constraint...")

# First, we need to drop the constraint
# SQLite doesn't support ALTER TABLE DROP CONSTRAINT directly
# So we need to recreate the table

# Create a new table without the constraint
cursor.execute("""
CREATE TABLE IF NOT EXISTS companies_new (
    company_number TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    company_status TEXT,  -- No constraint!
    company_status_detail TEXT,
    date_of_creation TEXT,
    date_of_cessation TEXT,
    company_type TEXT,
    jurisdiction TEXT,
    
    -- Address fields
    registered_office_address_line_1 TEXT,
    registered_office_address_line_2 TEXT,
    registered_office_locality TEXT,
    registered_office_region TEXT,
    registered_office_country TEXT,
    registered_office_postal_code TEXT,
    registered_office_po_box TEXT,
    registered_office_care_of TEXT,
    
    -- SIC codes (stored as JSON array)
    sic_codes TEXT,
    
    -- Previous names (stored as JSON array)
    previous_names TEXT,
    
    -- Accounts info
    accounting_reference_date_day INTEGER,
    accounting_reference_date_month INTEGER,
    last_accounts_made_up_to TEXT,
    accounts_category TEXT,
    
    -- Confirmation statement
    confirmation_statement_last_made_up_to TEXT,
    
    -- Charges and mortgages
    has_charges BOOLEAN DEFAULT 0,
    has_been_liquidated BOOLEAN DEFAULT 0,
    has_insolvency_history BOOLEAN DEFAULT 0,
    
    -- ETags for API caching
    etag TEXT,
    
    -- Our metadata
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    search_popularity INTEGER DEFAULT 0,
    risk_score INTEGER DEFAULT 50
)
""")

# Copy any existing data
cursor.execute("SELECT COUNT(*) FROM companies")
count = cursor.fetchone()[0]
if count > 0:
    print(f"Copying {count} existing records...")
    cursor.execute("INSERT INTO companies_new SELECT * FROM companies")

# Drop old table and rename new one
cursor.execute("DROP TABLE companies")
cursor.execute("ALTER TABLE companies_new RENAME TO companies")

# Recreate all indexes
print("Recreating indexes...")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company_name)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_status ON companies(company_status)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_postcode ON companies(registered_office_postal_code)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_created ON companies(date_of_creation)")
cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_popularity ON companies(search_popularity DESC)")

conn.commit()
print("✅ Schema fixed!")
conn.close()
