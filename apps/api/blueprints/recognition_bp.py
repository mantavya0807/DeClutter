#!/usr/bin/env python3
"""
Recognition API Blueprint
Imports and wraps the FastImageRecognitionAPI from main.py
"""

import sys
import os
import base64

# Add parent directory to path to import main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify

# Import the API class from main.py
try:
    from main import FastImageRecognitionAPI
    print("[OK] Imported FastImageRecognitionAPI from main.py")
except ImportError as e:
    print(f"[ERROR] Failed to import from main.py: {e}")
    FastImageRecognitionAPI = None

# Create blueprint
recognition_bp = Blueprint('recognition', __name__, url_prefix='/api/recognition')

# Initialize API instance (singleton pattern)
api_instance = None

def get_api_instance():
    """Get or create API instance"""
    global api_instance
    if api_instance is None and FastImageRecognitionAPI is not None:
        api_instance = FastImageRecognitionAPI()
    return api_instance

# Blueprint routes
@recognition_bp.route('/basic', methods=['POST'])
def recognize_image():
    """Image recognition endpoint"""
    try:
        api = get_api_instance()
        
        # Get image from request
        image_data = None
        if 'image' in request.files:
            image_file = request.files['image']
            image_data = image_file.read()
        elif request.json and 'image_base64' in request.json:
            base64_string = request.json['image_base64']
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            image_data = base64.b64decode(base64_string)
        
        if not image_data:
            return jsonify({
                'ok': False,
                'error_code': 'MISSING_IMAGE',
                'message': 'No image provided'
            }), 400
        
        if len(image_data) > 10 * 1024 * 1024:
            return jsonify({
                'ok': False,
                'error_code': 'IMAGE_TOO_LARGE',
                'message': 'Image must be less than 10MB'
            }), 400
        
        # Perform fast search (no login check)
        result = api.perform_google_reverse_search(image_data)
        
        if 'error' in result:
            return jsonify({
                'ok': False,
                'error_code': 'SEARCH_ERROR',
                'message': result['error']
            }), 500
        
        return jsonify({
            'ok': True,
            'data': {
                'product_name': result['product_name'],
                'source_url': result['source_url'],
                'host': result['host'],
                'pricing': result.get('pricing', {}),
                'rating': result.get('rating', {})
            },
            'diagnostics': result['diagnostics']
        })
        
    except Exception as e:
        print(f"❌ API error: {e}")
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': 'Image recognition failed'
        }), 500

@recognition_bp.route('/health', methods=['GET'])
def health():
    """Health check for recognition service"""
    return jsonify({
        'status': 'healthy',
        'service': 'Recognition API',
        'version': '1.0.0'
    })
