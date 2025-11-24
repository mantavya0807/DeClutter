#!/usr/bin/env python3
"""
Scraper API Blueprint
Imports and wraps the MarketplaceScraper from scraper.py
"""

import sys
import os

# Add parent directory to path to import scraper.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify

# Import the scraper class from scraper.py
try:
    from scraper import MarketplaceScraper
    print("[OK] Imported MarketplaceScraper from scraper.py")
except ImportError as e:
    print(f"[ERROR] Failed to import from scraper.py: {e}")
    MarketplaceScraper = None

# Create blueprint
scraper_bp = Blueprint('scraper', __name__, url_prefix='/api/scraper')

# Initialize scraper instance (singleton pattern)
scraper_instance = None

def get_scraper_instance():
    """Get or create scraper instance"""
    global scraper_instance
    if scraper_instance is None and MarketplaceScraper is not None:
        scraper_instance = MarketplaceScraper()
    return scraper_instance

# Blueprint routes
@scraper_bp.route('/health', methods=['GET'])
def health():
    """Health check for scraper service"""
    return jsonify({
        'status': 'healthy',
        'service': 'Scraper API',
        'version': '1.0.0'
    })

@scraper_bp.route('/facebook/login', methods=['POST'])
def facebook_login():
    """Facebook Marketplace login"""
    try:
        scraper = get_scraper_instance()
        if not scraper:
            return jsonify({'ok': False, 'error': 'Scraper not initialized'}), 500
        
        # Get credentials from request
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'ok': False,
                'error': 'Email and password required'
            }), 400
        
        # Perform login
        result = scraper.login_to_facebook(email, password)
        
        if result:
            return jsonify({
                'ok': True,
                'message': 'Successfully logged in to Facebook'
            })
        else:
            return jsonify({
                'ok': False,
                'error': 'Login failed'
            }), 401
            
    except Exception as e:
        print(f"❌ Facebook login error: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@scraper_bp.route('/prices', methods=['POST'])
def get_prices():
    """Get prices from Facebook Marketplace and eBay"""
    try:
        scraper = get_scraper_instance()
        if not scraper:
            return jsonify({'ok': False, 'error': 'Scraper not initialized'}), 500
        
        # Get product name from request
        data = request.get_json()
        product_name = data.get('product_name')
        
        if not product_name:
            return jsonify({
                'ok': False,
                'error': 'product_name is required'
            }), 400
        
        # Scrape prices
        # Use search_all_platforms instead of scrape_prices
        result = scraper.search_all_platforms(product_name, ['facebook', 'ebay'])
        
        if 'error' in result:
            return jsonify({
                'ok': False,
                'error': result['error']
            }), 500
            
        # Format the response to match what the pipeline expects
        formatted_data = {
            'query': result.get('query'),
            'comps': result.get('listings', []),
            'summary': result.get('statistics', {}),
            'currency': 'USD',
            'total_found': result.get('total_found', 0),
            'good_matches': result.get('good_matches', 0),
            'platforms_searched': result.get('platforms_searched', []),
            'platform_results': result.get('platform_results', {})
        }
        
        return jsonify({
            'ok': True,
            'data': formatted_data
        })
        
    except Exception as e:
        print(f"❌ Price scraping error: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@scraper_bp.route('/facebook/start-realtime-monitor', methods=['POST'])
def start_realtime_monitor():
    """Start real-time Facebook Marketplace monitoring"""
    try:
        scraper = get_scraper_instance()
        if not scraper:
            return jsonify({'ok': False, 'error': 'Scraper not initialized'}), 500
        
        data = request.get_json()
        product_name = data.get('product_name')
        
        if not product_name:
            return jsonify({
                'ok': False,
                'error': 'product_name is required'
            }), 400
        
        # Start monitoring
        result = scraper.start_realtime_monitor(product_name)
        
        return jsonify({
            'ok': True,
            'data': result
        })
        
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@scraper_bp.route('/test', methods=['GET'])
def test():
    """Test endpoint"""
    return jsonify({
        'ok': True,
        'message': 'Scraper API is working',
        'service': 'Scraper API',
        'version': '1.0.0'
    })
