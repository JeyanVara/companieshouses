#!/usr/bin/env python3
"""
CompaniesHouseAI Database Schema
Optimized for 5.6M companies on Raspberry Pi
"""

import sqlite3
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')

def create_schema():
    """Create optimized SQLite schema for Companies House data"""
    
    # Ensure database directory exists
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    print(f"Creating database at: {DATABASE_PATH}")
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for performance
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
    conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
    conn.execute("PRAGMA synchronous=NORMAL")  # Balance speed/safety
    
    cursor = conn.cursor()
    
    # Main companies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        company_number TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        company_status TEXT,
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
        risk_score INTEGER DEFAULT 50,
        
        -- Indexing for common queries
        CHECK (company_status IN ('active', 'dissolved', 'liquidation', 'receivership', 'administration', 'voluntary-arrangement', 'converted-closed', 'insolvency-proceedings'))
    )
    """)
    
    # Directors table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS directors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_number TEXT NOT NULL,
        officer_id TEXT NOT NULL,
        name TEXT NOT NULL,
        appointed_on TEXT,
        resigned_on TEXT,
        officer_role TEXT,
        date_of_birth_year INTEGER,
        date_of_birth_month INTEGER,
        nationality TEXT,
        country_of_residence TEXT,
        occupation TEXT,
        
        -- Address (stored normalized)
        address_line_1 TEXT,
        address_line_2 TEXT,
        locality TEXT,
        region TEXT,
        country TEXT,
        postal_code TEXT,
        
        -- Metadata
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (company_number) REFERENCES companies(company_number),
        UNIQUE(company_number, officer_id, appointed_on)
    )
    """)
    
    # Filings history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS filings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_number TEXT NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        description TEXT,
        paper_filed BOOLEAN DEFAULT 0,
        type TEXT,
        
        -- Barcode for document retrieval
        barcode TEXT,
        
        -- Metadata
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (company_number) REFERENCES companies(company_number)
    )
    """)
    
    # Search analytics table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS search_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        result_count INTEGER DEFAULT 0,
        clicked_company_number TEXT,
        search_type TEXT CHECK(search_type IN ('name', 'number', 'postcode', 'director', 'sic')),
        user_id TEXT,
        session_id TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Company changes tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_changes (
        company_number TEXT PRIMARY KEY,
        last_modified INTEGER,
        change_hash TEXT,
        priority INTEGER DEFAULT 5,
        next_check TIMESTAMP,
        
        FOREIGN KEY (company_number) REFERENCES companies(company_number)
    )
    """)
    
    # Create indexes for performance
    print("Creating indexes...")
    
    # Company searches
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_name ON companies(company_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_status ON companies(company_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_postcode ON companies(registered_office_postal_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_created ON companies(date_of_creation)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_popularity ON companies(search_popularity DESC)")
    
    # Director searches
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_director_name ON directors(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_director_company ON directors(company_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_director_officer ON directors(officer_id)")
    
    # Filing searches
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_filing_company ON filings(company_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_filing_date ON filings(date DESC)")
    
    # Create Full Text Search table
    print("Creating FTS5 table...")
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
        company_number UNINDEXED,
        company_name,
        previous_names,
        registered_office_address,
        sic_code_descriptions,
        content=companies,
        tokenize='porter unicode61'
    )
    """)
    
    # Create triggers to keep FTS in sync
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS companies_ai AFTER INSERT ON companies BEGIN
        INSERT INTO companies_fts(
            company_number, 
            company_name, 
            previous_names,
            registered_office_address,
            sic_code_descriptions
        ) VALUES (
            new.company_number,
            new.company_name,
            new.previous_names,
            new.registered_office_address_line_1 || ' ' || 
            new.registered_office_locality || ' ' || 
            new.registered_office_postal_code,
            ''
        );
    END
    """)
    
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS companies_au AFTER UPDATE ON companies BEGIN
        UPDATE companies_fts SET
            company_name = new.company_name,
            previous_names = new.previous_names,
            registered_office_address = new.registered_office_address_line_1 || ' ' || 
                new.registered_office_locality || ' ' || 
                new.registered_office_postal_code
        WHERE company_number = new.company_number;
    END
    """)
    
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS companies_ad AFTER DELETE ON companies BEGIN
        DELETE FROM companies_fts WHERE company_number = old.company_number;
    END
    """)
    
    # Create materialized view for popular companies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS popular_companies AS
    SELECT 
        company_number,
        company_name,
        company_status,
        registered_office_postal_code,
        search_popularity
    FROM companies
    WHERE search_popularity > 0
    ORDER BY search_popularity DESC
    LIMIT 10000
    """)
    
    # Create SIC code lookup table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sic_codes (
        code TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        category TEXT
    )
    """)
    
    # Insert common SIC codes
    common_sic_codes = [
        ('01110', 'Growing of cereals (except rice), leguminous crops and oil seeds', 'Agriculture'),
        ('47110', 'Retail sale in non-specialised stores with food, beverages or tobacco predominating', 'Retail'),
        ('68100', 'Buying and selling of own real estate', 'Real Estate'),
        ('68201', 'Renting and operating of Housing Association real estate', 'Real Estate'),
        ('68209', 'Other letting and operating of own or leased real estate', 'Real Estate'),
        ('70229', 'Management consultancy activities other than financial management', 'Professional'),
        ('82990', 'Other business support service activities n.e.c.', 'Business Support'),
    ]
    
    cursor.executemany("INSERT OR IGNORE INTO sic_codes VALUES (?, ?, ?)", common_sic_codes)
    
    conn.commit()
    
    # Analyze database for query planner
    cursor.execute("ANALYZE")
    
    # Get database stats
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
    table_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
    index_count = cursor.fetchone()[0]
    
    print(f"\n✅ Database created successfully!")
    print(f"📊 Stats: {table_count} tables, {index_count} indexes")
    print(f"💾 Location: {DATABASE_PATH}")
    print(f"🚀 Ready for 5.6M companies!")
    
    conn.close()

if __name__ == "__main__":
    create_schema()
