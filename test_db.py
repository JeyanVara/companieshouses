#!/usr/bin/env python3
import sqlite3
from flask import Flask, jsonify

app = Flask(__name__)

DB_PATH = '/home/jeyan/companieshouses/database/companies.db'

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM companies')
        count = cursor.fetchone()[0]
        conn.close()
        return jsonify({"status": "success", "companies": count})
    except Exception as e:
        return jsonify({"error": str(e), "path": DB_PATH})

@app.route('/search/<query>')
def search(query):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT company_number, company_name FROM companies WHERE company_name LIKE ? LIMIT 10', (f'%{query}%',))
        results = cursor.fetchall()
        conn.close()
        return jsonify([dict(row) for row in results])
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    print(f"Testing database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM companies')
        count = cursor.fetchone()[0]
        conn.close()
        print(f"✅ Database OK: {count:,} companies")
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    app.run(port=5001, debug=True)
