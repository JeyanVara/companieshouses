#!/usr/bin/env python3
import csv
import os
import sys

# Find CSV file
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'bulk_data')
csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

if not csv_files:
    print("No CSV found!")
    sys.exit(1)

csv_path = os.path.join(data_dir, csv_files[0])
print(f"Examining: {csv_path}\n")

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    # Read first line to detect delimiter
    first_line = f.readline()
    f.seek(0)
    
    # Try to detect delimiter
    if first_line.count(',') > first_line.count('\t'):
        delimiter = ','
    else:
        delimiter = '\t'
    
    reader = csv.DictReader(f, delimiter=delimiter)
    
    # Show headers
    print("CSV Headers:")
    for i, header in enumerate(reader.fieldnames, 1):
        print(f"{i}. {header}")
    
    print(f"\nTotal columns: {len(reader.fieldnames)}")
    
    # Show first row
    print("\nFirst row sample:")
    first_row = next(reader)
    for key, value in list(first_row.items())[:10]:
        print(f"{key}: {value}")
