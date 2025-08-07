from flask import Flask, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import sqlite3

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return jsonify({
        "status": "live",
        "message": "CompaniesHouses.com - Coming Soon",
        "description": "The UK's first free company intelligence platform",
        "competitor_status": "Creditsafe charges £5000/year for this",
        "sqlite_ready": True
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "ready": True})

@app.route('/api/test')
def test_api():
    api_key = os.getenv('COMPANIES_HOUSE_API_KEY')
    return jsonify({
        "api_configured": bool(api_key),
        "key_length": len(api_key) if api_key else 0,
        "environment": os.getenv('FLASK_ENV', 'not_set')
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

@app.route('/api/search', methods=['GET'])
def search_companies():
    """Search companies by name using FTS5"""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)
    offset = int(request.args.get('offset', 0))
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # FIXED SQL - removed incorrect table alias and field reference
    sql = """
    SELECT 
        c.company_number,
        c.company_name,
        c.company_status,
        c.registered_office_postal_code,
        c.date_of_creation,
        c.sic_codes
    FROM companies_fts fts
    JOIN companies c ON c.company_number = fts.company_number
    WHERE companies_fts MATCH ?
    ORDER BY rank
    LIMIT ? OFFSET ?
    """
    
    start_time = datetime.now()
    
    try:
        # Use FTS5 match syntax
        cursor.execute(sql, (query + '*', limit, offset))
        results = cursor.fetchall()
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Get total count
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM companies_fts 
            WHERE companies_fts MATCH ?
        """, (query + '*',))
        total = cursor.fetchone()['total']
        
        conn.close()
        
        return jsonify({
            'query': query,
            'total': total,
            'limit': limit,
            'offset': offset,
            'search_time_ms': round(search_time, 2),
            'results': [dict(row) for row in results]
        })
    
    except Exception as e:
        conn.close()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/search/simple', methods=['GET'])
def search_companies_simple():
    """Simple search without FTS5"""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Direct LIKE search (slower but works)
    sql = """
    SELECT 
        company_number,
        company_name,
        company_status,
        registered_office_postal_code,
        date_of_creation
    FROM companies
    WHERE company_name LIKE ?
    ORDER BY company_name
    LIMIT ?
    """
    
    cursor.execute(sql, (f'%{query}%', limit))
    results = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'query': query,
        'results': [dict(row) for row in results]
    })
