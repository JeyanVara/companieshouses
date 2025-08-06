#!/usr/bin/env python3
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Count companies
cursor.execute("SELECT COUNT(*) FROM companies")
count = cursor.fetchone()[0]
print(f"Total companies: {count:,}")

# Sample search
cursor.execute("""
    SELECT company_number, company_name, company_status 
    FROM companies 
    WHERE company_name LIKE '%TESCO%' 
    LIMIT 5
""")

print("\nSample TESCO companies:")
for row in cursor.fetchall():
    print(f"- {row[0]}: {row[1]} ({row[2]})")

conn.close()
