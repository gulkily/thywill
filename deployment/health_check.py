#!/usr/bin/env python3
"""
Health check endpoint for ThyWill application
This creates a simple health check route that deployment scripts can use
"""

from flask import Flask, jsonify
import sqlite3
import os

def add_health_check_to_app(app):
    """Add health check endpoint to existing Flask app"""
    
    @app.route('/health')
    def health_check():
        """Health check endpoint that verifies database connectivity"""
        try:
            # Check database connectivity
            db_path = os.path.join(os.path.dirname(__file__), '..', 'thywill.db')
            if not os.path.exists(db_path):
                return jsonify({
                    'status': 'unhealthy',
                    'error': 'Database file not found'
                }), 500
            
            # Try to connect and run a simple query
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            
            return jsonify({
                'status': 'healthy',
                'database': 'connected'
            }), 200
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500

if __name__ == '__main__':
    # Standalone health check for testing
    app = Flask(__name__)
    add_health_check_to_app(app)
    app.run(host='127.0.0.1', port=8001, debug=False)