#!/usr/bin/env python3
"""
eBay API Blueprint
Imports and wraps the EbayAutomatorImproved from ebay_improved.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import ebay_improved.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify

# Import the eBay class from ebay_improved.py
try:
    from ebay_improved import EbayAutomatorImproved
    print("[OK] Imported EbayAutomatorImproved from ebay_improved.py")
except ImportError as e:
    print(f"[ERROR] Failed to import from ebay_improved.py: {e}")
    EbayAutomatorImproved = None

# Create blueprint
ebay_bp = Blueprint('ebay', __name__, url_prefix='/api/ebay')

# Initialize eBay instance (singleton pattern)
ebay_instance = None

def get_ebay_instance():
    """Get or create eBay instance"""
    global ebay_instance
    if ebay_instance is None and EbayAutomatorImproved is not None:
        ebay_instance = EbayAutomatorImproved()
    return ebay_instance

# Blueprint routes
@ebay_bp.route('/health', methods=['GET'])
def health():
    """Health check for eBay service"""
    try:
        automator = get_ebay_instance()
        return jsonify({
            'status': 'OK',
            'service': 'ebay_listing_automation_improved',
            'timestamp': datetime.now().isoformat(),
            'browser_ready': automator.driver is not None if automator else False,
            'ebay_logged_in': automator.ebay_logged_in if automator else False,
            'gemini_available': automator.gemini_model is not None if automator else False,
            'version': '2.0.0 - IMPROVED'
        })
    except Exception as e:
        return jsonify({
            'status': 'OK',
            'service': 'ebay_listing_automation_improved',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0 - IMPROVED',
            'note': 'Instance not fully initialized'
        })

@ebay_bp.route('/listing', methods=['POST'])
def create_ebay_listing():
    """Create eBay listing using improved method"""
    try:
        automator = get_ebay_instance()
        if not automator:
            return jsonify({'ok': False, 'error': 'eBay API not initialized'}), 500
        
        if not request.is_json:
            return jsonify({
                'ok': False,
                'error_code': 'INVALID_REQUEST',
                'message': 'JSON request body required'
            }), 400
        
        data = request.get_json()
        
        if 'product' not in data or 'pricing_data' not in data:
            return jsonify({
                'ok': False,
                'error_code': 'MISSING_DATA',
                'message': 'Product and pricing data required'
            }), 400
        
        product_data = data['product']
        pricing_data = data['pricing_data']
        
        # Calculate optimal price
        def calculate_optimal_price(pricing_data: dict, condition: str = "used") -> float:
            try:
                comps = pricing_data.get('comps', [])
                if not comps:
                    return 50.0
                
                condition_comps = [comp for comp in comps if comp['condition'] == condition]
                if not condition_comps:
                    condition_comps = comps
                
                prices = [float(comp['price']) for comp in condition_comps if comp.get('price')]
                if not prices:
                    return 50.0
                
                from statistics import median
                return round(median(prices), 2)
            except Exception as e:
                print(f"❌ Price calculation error: {e}")
                return 50.0
        
        # Prepare listing data
        listing_data = {
            'title': product_data.get('name', 'Item for Sale'),
            'category': product_data.get('category', 'Other'),
            'condition': product_data.get('condition', 'used'),
            'price': calculate_optimal_price(pricing_data, product_data.get('condition', 'used')),
            'quantity': 1,
            'description': product_data.get('description', ''),
            'images': data.get('images', [])
        }
        
        # Create the listing
        result = automator.create_listing(listing_data)
        
        return jsonify({
            'ok': True,
            'data': result,
            'message': 'eBay listing created successfully'
        })
        
    except Exception as e:
        print(f"❌ eBay listing error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'ok': False,
            'error_code': 'LISTING_ERROR',
            'message': str(e)
        }), 500
