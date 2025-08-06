#!/usr/bin/env python3
"""
Download Companies House Bulk Data Product
Handles the free BasicCompanyDataAsOneFile.zip
"""

import os
import sys
import requests
import zipfile
import time
from datetime import datetime
from tqdm import tqdm

# Companies House bulk data URL
BULK_DATA_URL = "http://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile-{date}.zip"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'bulk_data')

def get_latest_data_url():
    """
    Companies House updates bulk data on the 1st of each month
    Try current month first, then previous month
    """
    today = datetime.now()
    
    # Try current month
    current_date = today.strftime("%Y-%m-01")
    current_url = BULK_DATA_URL.format(date=current_date)
    
    # Try previous month as fallback
    if today.month == 1:
        prev_date = f"{today.year - 1}-12-01"
    else:
        prev_date = f"{today.year}-{today.month - 1:02d}-01"
    prev_url = BULK_DATA_URL.format(date=prev_date)
    
    # Check which URL is available
    print(f"Checking for data from {current_date}...")
    response = requests.head(current_url, allow_redirects=True)
    
    if response.status_code == 200:
        return current_url, current_date
    else:
        print(f"Not found. Checking {prev_date}...")
        return prev_url, prev_date

def download_with_progress(url, filepath):
    """Download file with progress bar"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    print(f"Downloading {total_size / (1024*1024*1024):.2f} GB...")
    
    with open(filepath, 'wb') as file:
        with tqdm(total=total_size, unit='B', unit_scale=True, desc='Downloading') as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                pbar.update(len(chunk))

def extract_with_progress(zip_path, extract_to):
    """Extract zip file with progress"""
    print("Extracting data...")
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.namelist()
        
        with tqdm(total=len(members), desc='Extracting') as pbar:
            for member in members:
                zip_ref.extract(member, extract_to)
                pbar.update(1)
    
    # Find the CSV file
    csv_files = [f for f in os.listdir(extract_to) if f.endswith('.csv')]
    if csv_files:
        return os.path.join(extract_to, csv_files[0])
    return None

def main():
    """Download and extract Companies House bulk data"""
    
    # Create data directory
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Check if we already have recent data
    existing_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if existing_files:
        print(f"⚠️  Found existing data: {existing_files[0]}")
        response = input("Download fresh data? (y/n): ")
        if response.lower() != 'y':
            print("Using existing data.")
            return os.path.join(DATA_DIR, existing_files[0])
    
    # Get download URL
    url, date_str = get_latest_data_url()
    print(f"\n📥 Downloading Companies House data from {date_str}")
    print(f"URL: {url}")
    
    # Download file
    zip_filename = f"BasicCompanyData-{date_str}.zip"
    zip_path = os.path.join(DATA_DIR, zip_filename)
    
    if os.path.exists(zip_path):
        print(f"✅ Zip file already exists: {zip_path}")
    else:
        start_time = time.time()
        download_with_progress(url, zip_path)
        download_time = time.time() - start_time
        print(f"✅ Downloaded in {download_time/60:.1f} minutes")
    
    # Extract file
    csv_path = extract_with_progress(zip_path, DATA_DIR)
    
    if csv_path:
        # Get file size
        size_gb = os.path.getsize(csv_path) / (1024**3)
        print(f"\n✅ Data ready!")
        print(f"📄 CSV file: {csv_path}")
        print(f"💾 Size: {size_gb:.2f} GB")
        
        # Optional: Delete zip to save space
        response = input("\nDelete zip file to save space? (y/n): ")
        if response.lower() == 'y':
            os.remove(zip_path)
            print("Zip file deleted.")
        
        return csv_path
    else:
        print("❌ Error: Could not find CSV file in extracted data")
        return None

if __name__ == "__main__":
    csv_path = main()
    if csv_path:
        print(f"\n🎯 Next step: Run import_companies.py to import this data")
