#!/usr/bin/env python3
"""
Listing API Blueprint
Imports and wraps the MarketplaceLister from listing.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import listing.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify

# Import the listing class from listing.py
try:
    from listing import MarketplaceLister
    print("[OK] Imported MarketplaceLister from listing.py")
except ImportError as e:
    print(f"[ERROR] Failed to import from listing.py: {e}")
    MarketplaceLister = None

# Create blueprint
listing_bp = Blueprint('listing', __name__, url_prefix='/api/listing')

# Initialize listing instance (singleton pattern)
listing_instance = None

def get_listing_instance():
    """Get or create listing instance"""
    global listing_instance
    if listing_instance is None and MarketplaceLister is not None:
        listing_instance = MarketplaceLister()
    return listing_instance

# Blueprint routes
@listing_bp.route('/health', methods=['GET'])
def health():
    """Health check for listing service"""
    try:
        lister = get_listing_instance()
        return jsonify({
            'status': 'OK',
            'service': 'marketplace_listing_api',
            'timestamp': datetime.now().isoformat(),
            'browser_ready': lister.driver is not None if lister else False,
            'facebook_logged_in': lister.facebook_logged_in if lister else False,
            'gemini_available': lister.gemini_model is not None if lister else False,
            'ebay_configured': bool(lister.ebay_config['app_id']) if lister else False,
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'OK',
            'service': 'marketplace_listing_api',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'note': 'Instance not fully initialized'
        })

@listing_bp.route('/facebook/login', methods=['POST'])
def facebook_login():
    """Trigger Facebook login process"""
    try:
        lister = get_listing_instance()
        if not lister:
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
        
        success = lister.ensure_facebook_access()
        
        if success:
            return jsonify({
                'ok': True,
                'message': 'Facebook login successful',
                'logged_in': True
            })
        else:
            return jsonify({
                'ok': False,
                'error_code': 'LOGIN_FAILED',
                'message': 'Facebook login process failed'
            }), 400
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'LOGIN_ERROR',
            'message': f'Login error: {str(e)}'
        }), 500

@listing_bp.route('/create', methods=['POST'])
def create_listings():
    """
    Create marketplace listings
    
    Body:
    {
        "product": {"name": "...", "condition": "used", "category": "..."},
        "pricing_data": {pricing data from price scraper},
        "platforms": ["facebook", "ebay"],
        "images": ["base64_image_data"] // optional
    }
    """
    try:
        lister = get_listing_instance()
        if not lister:
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
        
        if not request.is_json:
            return jsonify({
                'ok': False,
                'error_code': 'INVALID_REQUEST',
                'message': 'JSON request body required'
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'product' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'MISSING_PRODUCT_DATA',
                'message': 'Product data is required'
            }), 400
        
        if 'pricing_data' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'MISSING_PRICING_DATA',
                'message': 'Pricing data is required'
            }), 400
        
        # Extract parameters
        product_data = data['product']
        pricing_data = data['pricing_data']
        platforms = data.get('platforms', ['facebook', 'ebay'])
        images = data.get('images', [])
        
        # Validate platforms
        valid_platforms = ['facebook', 'ebay']
        platforms = [p for p in platforms if p in valid_platforms]
        
        if not platforms:
            return jsonify({
                'ok': False,
                'error_code': 'NO_VALID_PLATFORMS',
                'message': f'Valid platforms are: {valid_platforms}'
            }), 400
        
        result = lister.create_listings(product_data, pricing_data, platforms, images)
        
        return jsonify({
            'ok': True,
            'data': result
        })
        
    except Exception as e:
        print(f"❌ Create listings error: {e}")
        return jsonify({
            'ok': False,
            'error_code': 'CREATE_ERROR',
            'message': str(e)
        }), 500

@listing_bp.route('/facebook', methods=['POST'])
def create_facebook_listing():
    """Create Facebook Marketplace listing directly"""
    try:
        print("[DEBUG] Received request to /api/listing/facebook")
        lister = get_listing_instance()
        if not lister:
            print("[ERROR] Listing API not initialized")
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
        
        data = request.get_json()
        print(f"[DEBUG] Request data keys: {data.keys() if data else 'None'}")
        
        # Check if this is a full pipeline payload (product + pricing_data)
        if 'product' in data and 'pricing_data' in data:
            print("[DEBUG] Received full pipeline payload for Facebook listing")
            result = lister.create_listings(
                data['product'], 
                data['pricing_data'], 
                ['facebook'],
                data.get('images', [])
            )
            # Extract just the facebook result
            fb_result = result['listings'].get('facebook', {})
            return jsonify({'ok': True, 'data': fb_result})
            
        # Otherwise assume it's a direct listing payload (title, price, etc.)
        print("[DEBUG] Received direct listing payload for Facebook")
        result = lister.create_facebook_listing(data)
        
        return jsonify({'ok': True, 'data': result})
        
    except Exception as e:
        print(f"❌ Facebook listing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500

@listing_bp.route('/ebay', methods=['POST'])
def create_ebay_listing():
    """Create eBay listing directly"""
    try:
        lister = get_listing_instance()
        if not lister:
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
        
        data = request.get_json()
        
        # Check if this is a full pipeline payload (product + pricing_data)
        if 'product' in data and 'pricing_data' in data:
            print("[DEBUG] Received full pipeline payload for eBay listing")
            result = lister.create_listings(
                data['product'], 
                data['pricing_data'], 
                ['ebay']
            )
            # Extract just the ebay result
            ebay_result = result['listings'].get('ebay', {})
            return jsonify({'ok': True, 'data': ebay_result})
            
        # Otherwise assume it's a direct listing payload
        result = lister.create_ebay_listing(data)
        
        return jsonify({'ok': True, 'data': result})
        
    except Exception as e:
        print(f"❌ eBay listing error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@listing_bp.route('/facebook/start-monitoring', methods=['POST'])
def start_monitoring():
    """Start monitoring Facebook Marketplace messages"""
    try:
        lister = get_listing_instance()
        if not lister:
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
        
        result = lister.start_facebook_message_monitoring()
        
        return jsonify({'ok': True, 'data': result, 'message': 'Monitoring started'})
        
    except Exception as e:
        print(f"❌ Monitoring error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@listing_bp.route('/facebook/monitor-status', methods=['GET'])
def monitor_status():
    """Get Facebook Marketplace monitoring status"""
    try:
        lister = get_listing_instance()
        if not lister:
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
        
        # Return monitoring state info
        status = {
            'browser_active': lister.driver is not None,
            'facebook_logged_in': lister.facebook_logged_in,
            'monitoring_active': hasattr(lister, 'monitor') and lister.monitor is not None and lister.monitor.running
        }
        
        return jsonify({'ok': True, 'data': status})
        
    except Exception as e:
        print(f"❌ Status check error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@listing_bp.route('/facebook/reply', methods=['POST'])
def reply_to_message():
    """Reply to a Facebook Marketplace message"""
    try:
        lister = get_listing_instance()
        if not lister:
            return jsonify({'ok': False, 'error': 'Listing API not initialized'}), 500
            
        data = request.get_json()
        if not data or 'buyer_name' not in data or 'message' not in data:
            return jsonify({'ok': False, 'error': 'Missing buyer_name or message'}), 400
            
        buyer_name = data['buyer_name']
        message = data['message']
        
        success = lister.send_facebook_message(buyer_name, message)
        
        if success:
            return jsonify({'ok': True, 'message': f'Message sent to {buyer_name}'})
        else:
            return jsonify({'ok': False, 'error': 'Failed to send message'}), 500
            
    except Exception as e:
        print(f"❌ Reply error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500
