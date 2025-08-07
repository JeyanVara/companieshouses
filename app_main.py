#!/usr/bin/env python3
"""CompaniesHouses.com API - Working Version"""

import os
import sqlite3
import json
from datetime import datetime

# Flask imports
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# WORKING DATABASE PATH - EXACTLY AS TESTED
DB_PATH = '/home/jeyan/companieshouses/database/companies.db'

def get_db():
    """Get database connection - simple version that works"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    """Home endpoint with API documentation"""
    try:
        # Test database connection
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM companies')
        count = cursor.fetchone()[0]
        conn.close()
        db_status = f"{count:,} companies"
    except:
        db_status = "error"
    
    return jsonify({
        "status": "live",
        "message": "CompaniesHouses.com API",
        "database": db_status,
        "endpoints": {
            "search": "/api/search?q=tesco",
            "company": "/api/company/00445790",
            "stats": "/api/stats"
        },
        "example_queries": {
            "search_tesco": "https://companieshouses.com/api/search?q=tesco",
            "search_london": "https://companieshouses.com/api/search?q=london&limit=50",
            "get_tesco_plc": "https://companieshouses.com/api/company/00445790"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/search')
def search():
    """Search companies by name"""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)
    offset = int(request.args.get('offset', 0))
    
    if not query or len(query) < 2:
        return jsonify({
            'error': 'Query must be at least 2 characters',
            'example': '/api/search?q=tesco'
        }), 400
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Search with LIKE (case-insensitive using UPPER)
        sql = """
            SELECT 
                company_number,
                company_name,
                company_status,
                registered_office_postal_code,
                date_of_creation,
                sic_codes
            FROM companies
            WHERE UPPER(company_name) LIKE UPPER(?)
            ORDER BY 
                CASE 
                    WHEN UPPER(company_name) = UPPER(?) THEN 0
                    WHEN UPPER(company_name) LIKE UPPER(?) THEN 1
                    ELSE 2
                END,
                company_name
            LIMIT ? OFFSET ?
        """
        
        search_pattern = f'%{query}%'
        exact_match = query
        starts_with = f'{query}%'
        
        cursor.execute(sql, (search_pattern, exact_match, starts_with, limit, offset))
        results = cursor.fetchall()
        
        # Get total count
        cursor.execute(
            "SELECT COUNT(*) as total FROM companies WHERE UPPER(company_name) LIKE UPPER(?)",
            (search_pattern,)
        )
        total = cursor.fetchone()['total']
        
        # Convert results to list of dicts
        companies = []
        for row in results:
            company = {
                'company_number': row['company_number'],
                'company_name': row['company_name'],
                'company_status': row['company_status'],
                'postcode': row['registered_office_postal_code'],
                'incorporation_date': row['date_of_creation']
            }
            
            # Parse SIC codes if present
            if row['sic_codes']:
                try:
                    company['sic_codes'] = json.loads(row['sic_codes'])
                except:
                    company['sic_codes'] = []
            else:
                company['sic_codes'] = []
                
            companies.append(company)
        
        conn.close()
        
        return jsonify({
            'query': query,
            'total': total,
            'count': len(companies),
            'limit': limit,
            'offset': offset,
            'results': companies
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Database error: {str(e)}',
            'query': query
        }), 500

@app.route('/api/company/<company_number>')
def get_company(company_number):
    """Get single company details"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM companies WHERE company_number = ?",
            (company_number,)
        )
        company = cursor.fetchone()
        
        conn.close()
        
        if not company:
            return jsonify({
                'error': 'Company not found',
                'company_number': company_number
            }), 404
        
        # Convert to dict
        result = dict(company)
        
        # Parse JSON fields
        if result.get('sic_codes'):
            try:
                result['sic_codes'] = json.loads(result['sic_codes'])
            except:
                result['sic_codes'] = []
        
        if result.get('previous_names'):
            try:
                result['previous_names'] = json.loads(result['previous_names'])
            except:
                result['previous_names'] = []
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': f'Database error: {str(e)}',
            'company_number': company_number
        }), 500

@app.route('/api/stats')
def stats():
    """Get database statistics"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Total companies
        cursor.execute("SELECT COUNT(*) as total FROM companies")
        total = cursor.fetchone()['total']
        
        # Companies by status
        cursor.execute("""
            SELECT company_status, COUNT(*) as count 
            FROM companies 
            WHERE company_status IS NOT NULL
            GROUP BY company_status 
            ORDER BY count DESC 
            LIMIT 10
        """)
        status_breakdown = cursor.fetchall()
        
        # Active companies
        cursor.execute(
            "SELECT COUNT(*) as count FROM companies WHERE company_status = 'active'"
        )
        active = cursor.fetchone()['count']
        
        # Dissolved companies
        cursor.execute(
            "SELECT COUNT(*) as count FROM companies WHERE company_status LIKE '%dissolved%'"
        )
        dissolved = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'total_companies': total,
            'active_companies': active,
            'dissolved_companies': dissolved,
            'status_breakdown': [
                {
                    'status': row['company_status'],
                    'count': row['count'],
                    'percentage': round(row['count'] / total * 100, 2)
                }
                for row in status_breakdown
            ],
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Database error: {str(e)}'
        }), 500

@app.route('/api/search/autocomplete')
def autocomplete():
    """Quick autocomplete for company names"""
    query = request.args.get('q', '').strip()
    
    if not query or len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get companies that start with query
        cursor.execute("""
            SELECT company_number, company_name 
            FROM companies 
            WHERE UPPER(company_name) LIKE UPPER(?)
            ORDER BY company_name
            LIMIT 10
        """, (f'{query}%',))
        
        results = cursor.fetchall()
        conn.close()
        
        suggestions = [
            {
                'company_number': row['company_number'],
                'company_name': row['company_name']
            }
            for row in results
        ]
        
        return jsonify({'suggestions': suggestions})
        
    except Exception as e:
        return jsonify({'suggestions': [], 'error': str(e)})

if __name__ == '__main__':
    print("="*50)
    print("CompaniesHouses.com API Starting...")
    print("="*50)
    print(f"Database path: {DB_PATH}")
    
    # Test database connection
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM companies")
        count = cursor.fetchone()['count']
        conn.close()
        print(f"✅ Database connected: {count:,} companies found")
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("Please check the database path!")
    
    print("="*50)
    print("Starting Flask server...")
    print("API will be available at:")
    print("  Local: http://localhost:5000")
    print("  Network: http://0.0.0.0:5000")
    print("  Public: https://companieshouses.com")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)