from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'companies.db')

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/search', methods=['GET'])
def search_companies():
    """Search companies by name"""
    query = request.args.get('q', '').strip()
    limit = min(int(request.args.get('limit', 20)), 100)
    offset = int(request.args.get('offset', 0))
    
    if not query:
        return jsonify({'error': 'Query parameter q is required'}), 400
    
    if len(query) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Use FTS5 for fast search
    sql = """
    SELECT 
        c.company_number,
        c.company_name,
        c.company_status,
        c.registered_office_postal_code,
        c.date_of_creation,
        c.sic_codes
    FROM companies c
    JOIN companies_fts ON c.company_number = companies_fts.company_number
    WHERE companies_fts MATCH ?
    ORDER BY rank
    LIMIT ? OFFSET ?
    """
    
    start_time = datetime.now()
    cursor.execute(sql, (f'"{query}"*', limit, offset))
    results = cursor.fetchall()
    search_time = (datetime.now() - start_time).total_seconds() * 1000
    
    # Get total count
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM companies_fts 
        WHERE companies_fts MATCH ?
    """, (f'"{query}"*',))
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

@app.route('/api/company/<company_number>', methods=['GET'])
def get_company(company_number):
    """Get single company details"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM companies 
        WHERE company_number = ?
    """, (company_number,))
    
    company = cursor.fetchone()
    conn.close()
    
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    
    return jsonify(dict(company))

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM companies")
    total = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT company_status, COUNT(*) as count 
        FROM companies 
        GROUP BY company_status 
        ORDER BY count DESC 
        LIMIT 5
    """)
    status_breakdown = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        'total_companies': total,
        'status_breakdown': [dict(row) for row in status_breakdown],
        'last_updated': datetime.now().isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
