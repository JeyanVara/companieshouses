#!/usr/bin/env python3
import sqlite3
import os
from collections import Counter

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

print("📊 Database Statistics\n")

# Total companies
cursor.execute("SELECT COUNT(*) FROM companies")
total = cursor.fetchone()[0]
print(f"Total companies: {total:,}")

# By status
print("\nCompanies by status:")
cursor.execute("SELECT company_status, COUNT(*) as cnt FROM companies GROUP BY company_status ORDER BY cnt DESC LIMIT 10")
for status, count in cursor.fetchall():
    print(f"  {status or 'NULL'}: {count:,}")

# By country
print("\nCompanies by country:")
cursor.execute("SELECT registered_office_country, COUNT(*) as cnt FROM companies GROUP BY registered_office_country ORDER BY cnt DESC LIMIT 5")
for country, count in cursor.fetchall():
    print(f"  {country or 'NULL'}: {count:,}")

# Sample companies
print("\nSample companies:")
cursor.execute("SELECT company_number, company_name, company_status FROM companies LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} ({row[2]})")

# Test search
print("\nTest search for 'TESCO':")
cursor.execute("SELECT company_number, company_name FROM companies WHERE company_name LIKE '%TESCO%' LIMIT 5")
results = cursor.fetchall()
for row in results:
    print(f"  {row[0]}: {row[1]}")

conn.close()
