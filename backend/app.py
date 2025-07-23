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
