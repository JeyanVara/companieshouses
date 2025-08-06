#!/usr/bin/env python3
import csv
import os
from collections import Counter

data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'bulk_data')
csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
csv_path = os.path.join(data_dir, csv_files[0])

print("Checking first 10 rows...\n")

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    # Check column names
    print("Column names (showing spaces):")
    for col in reader.fieldnames[:10]:
        print(f"'{col}'")
    
    print("\n" + "="*50 + "\n")
    
    # Check first few rows
    status_counter = Counter()
    
    for i, row in enumerate(reader):
        if i < 5:
            # Show company number column attempts
            print(f"Row {i+1}:")
            print(f"  'CompanyNumber': '{row.get('CompanyNumber', 'NOT FOUND')}'")
            print(f"  ' CompanyNumber': '{row.get(' CompanyNumber', 'NOT FOUND')}'")
            print(f"  'CompanyStatus': '{row.get('CompanyStatus', 'NOT FOUND')}'")
            print()
        
        # Count status values
        status = row.get('CompanyStatus', '')
        if status:
            status_counter[status] += 1
            
        if i >= 1000:
            break
    
    print("\nCompany Status values found:")
    for status, count in status_counter.most_common():
        print(f"  '{status}': {count}")
