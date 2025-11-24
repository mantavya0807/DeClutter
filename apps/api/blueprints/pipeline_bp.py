#!/usr/bin/env python3
"""
Pipeline API Blueprint
Imports and wraps the ObjectDetectionPipeline from pipeline_api.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import pipeline_api.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify, send_file

# Import pipeline module
try:
    # Import the initialization and processing functions from pipeline_api
    import pipeline_api
    from pipeline_api import (
        initialize_pipeline,
        process_image_async,
        processing_status,
        save_jobs,
        PIPELINE_AVAILABLE,
        allowed_file,
        UPLOAD_FOLDER
    )
    print("[OK] Imported pipeline functions from pipeline_api.py")
except ImportError as e:
    print(f"[ERROR] Failed to import from pipeline_api.py: {e}")
    initialize_pipeline = None
    process_image_async = None
    processing_status = {}
    PIPELINE_AVAILABLE = False
    allowed_file = None
    UPLOAD_FOLDER = 'temp_uploads'

# Create blueprint
pipeline_bp = Blueprint('pipeline', __name__, url_prefix='/api/pipeline')

# Blueprint routes
@pipeline_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'service': 'pipeline_api',
        'timestamp': datetime.now().isoformat(),
        'pipeline_available': PIPELINE_AVAILABLE,
        'pipeline_initialized': pipeline_api.pipeline is not None if hasattr(pipeline_api, 'pipeline') else False
    })

@pipeline_bp.route('/process', methods=['POST'])
def process_image():
    """Process uploaded image through complete pipeline"""
    try:
        if not PIPELINE_AVAILABLE:
            return jsonify({
                'ok': False,
                'error_code': 'PIPELINE_NOT_AVAILABLE',
                'message': 'Pipeline module not available'
            }), 500
        
        # Initialize pipeline if needed
        if not initialize_pipeline():
            return jsonify({
                'ok': False,
                'error_code': 'PIPELINE_INIT_ERROR',
                'message': 'Failed to initialize pipeline'
            }), 500
        
        # Check for image data
        if 'image' not in request.files and 'image_data' not in request.form:
            return jsonify({
                'ok': False,
                'error_code': 'NO_IMAGE',
                'message': 'No image provided'
            }), 400
        
        # Generate job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Process image in background
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename == '':
                return jsonify({
                    'ok': False,
                    'error_code': 'NO_FILENAME',
                    'message': 'No file selected'
                }), 400
            
            if not allowed_file(image_file.filename):
                return jsonify({
                    'ok': False,
                    'error_code': 'INVALID_FILE_TYPE',
                    'message': 'Invalid file type'
                }), 400
            
            # Save file temporarily
            from werkzeug.utils import secure_filename
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, f"{job_id}_{filename}")
            image_file.save(filepath)
            
            # Set initial status
            processing_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Image uploaded, starting processing...",
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()

            # Get platforms from request
            platforms = request.form.getlist('platforms')
            if not platforms:
                platforms = ["facebook", "ebay"]

            # Start background processing
            import threading
            thread = threading.Thread(
                target=process_image_async,
                args=(filepath, job_id, platforms)
            )
            thread.daemon = True
            thread.start()
        
        elif 'image_data' in request.form:
            # Handle base64 image data
            image_data = request.form['image_data']
            
            # Save base64 to file
            import base64
            import tempfile
            
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            image_bytes = base64.b64decode(image_data)
            filepath = os.path.join(UPLOAD_FOLDER, f"{job_id}.jpg")
            
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            
            # Set initial status
            processing_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Image uploaded, starting processing...",
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()

            # Get platforms from request
            platforms = request.form.getlist('platforms')
            if not platforms:
                platforms = ["facebook", "ebay"]

            # Start background processing
            import threading
            thread = threading.Thread(
                target=process_image_async,
                args=(filepath, job_id, platforms)
            )
            thread.daemon = True
            thread.start()
        
        return jsonify({
            'ok': True,
            'job_id': job_id,
            'message': 'Processing started',
            'status_url': f'/api/pipeline/status/{job_id}'
        })
        
    except Exception as e:
        print(f"❌ Process error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'ok': False,
            'error_code': 'PROCESSING_ERROR',
            'message': str(e)
        }), 500

@pipeline_bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status for a job"""
    try:
        if job_id not in processing_status:
            return jsonify({
                'ok': False,
                'error_code': 'JOB_NOT_FOUND',
                'message': f'Job {job_id} not found'
            }), 404
        
        status = processing_status[job_id]
        
        # Return flattened status to match pipeline_api.py format
        response = {
            'ok': True,
            'job_id': job_id
        }
        response.update(status)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'STATUS_ERROR',
            'message': str(e)
        }), 500

@pipeline_bp.route('/jobs', methods=['GET'])
def get_jobs():
    """Get all jobs"""
    try:
        jobs = []
        for job_id, status in processing_status.items():
            jobs.append({
                'job_id': job_id,
                'status': status.get('status'),
                'progress': status.get('progress', 0),
                'timestamp': status.get('timestamp')
            })
        
        # Sort by timestamp (most recent first)
        jobs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({
            'ok': True,
            'jobs': jobs,
            'total': len(jobs)
        })
        
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@pipeline_bp.route('/clear-jobs', methods=['POST'])
def clear_jobs():
    """Clear completed jobs"""
    try:
        completed_jobs = [
            job_id for job_id, status in processing_status.items()
            if status.get('status') in ['completed', 'failed']
        ]
        
        for job_id in completed_jobs:
            del processing_status[job_id]
            
        save_jobs()
        
        return jsonify({
            'ok': True,
            'message': f'Cleared {len(completed_jobs)} completed jobs',
            'cleared_count': len(completed_jobs)
        })
        
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@pipeline_bp.route('/cropped-images', methods=['GET'])
def get_cropped_images():
    """Get list of cropped images"""
    try:
        cropped_dir = 'cropped_resellables'
        
        if not os.path.exists(cropped_dir):
            return jsonify({
                'ok': True,
                'images': [],
                'total': 0
            })
        
        # Get all image files
        images = []
        for filename in os.listdir(cropped_dir):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(cropped_dir, filename)
                stat = os.stat(filepath)
                
                images.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'url': f'/api/pipeline/cropped-image/{filename}'
                })
        
        # Sort by creation time (most recent first)
        images.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'ok': True,
            'images': images,
            'total': len(images)
        })
        
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@pipeline_bp.route('/cropped-image/<filename>', methods=['GET'])
def get_cropped_image(filename):
    """Serve a cropped image"""
    try:
        from werkzeug.utils import secure_filename
        filename = secure_filename(filename)
        filepath = os.path.join('cropped_resellables', filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'ok': False,
                'error': 'File not found'
            }), 404
        
        return send_file(filepath, mimetype='image/jpeg')
        
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500

@pipeline_bp.route('/test', methods=['GET'])
def test():
    """Test endpoint"""
    return jsonify({
        'ok': True,
        'message': 'Pipeline API is running',
        'pipeline_available': PIPELINE_AVAILABLE
    })

@pipeline_bp.route('/create-listings', methods=['POST'])
def create_listings():
    """Create listings for selected items"""
    try:
        print("[DEBUG] Received request to /api/pipeline/create-listings")
        if not PIPELINE_AVAILABLE:
            print("[ERROR] Pipeline not available")
            return jsonify({
                'ok': False,
                'error_code': 'PIPELINE_NOT_AVAILABLE',
                'message': 'Pipeline module not available'
            }), 500
            
        # Initialize pipeline if needed
        if not initialize_pipeline():
            print("[ERROR] Pipeline initialization failed")
            return jsonify({
                'ok': False,
                'error_code': 'PIPELINE_INIT_FAILED',
                'message': 'Pipeline initialization failed'
            }), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'message': 'No data provided'}), 400
            
        items = data.get('items', [])
        platforms = data.get('platforms', ["facebook", "ebay"])
        
        print(f"[DEBUG] Processing {len(items)} items for platforms: {platforms}")
        
        if not items:
            return jsonify({'ok': False, 'message': 'No items selected'}), 400
            
        user_id = data.get('user_id', 'anonymous')
        results = []
        
        # Access the pipeline instance from the imported module
        pipeline_instance = pipeline_api.pipeline
        
        for item in items:
            # Ensure we have pricing data
            pricing_data = item.get('pricing_data', {})
            
            # Get cropped image path if available
            image_path = None
            cropped_id = item.get('cropped_id')
            
            # Define root cropped folder
            # pipeline_bp.py is in apps/api/blueprints/
            # We want root/cropped_resellables/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            cropped_folder = os.path.join(root_dir, 'cropped_resellables')
            
            if 'cropped_path' in item and item['cropped_path']:
                image_path = item['cropped_path']
            elif 'image_url' in item and item['image_url']:
                image_path = item['image_url']
                
            # If image_path is a URL, try to resolve it to a local file
            if image_path and (image_path.startswith('http') or image_path.startswith('//')):
                print(f"[DEBUG] Resolving image URL: {image_path}")
                # Extract filename
                filename = image_path.split('/')[-1]
                # Remove query parameters if any
                if '?' in filename:
                    filename = filename.split('?')[0]
                    
                local_candidate = os.path.join(cropped_folder, filename)
                
                if os.path.exists(local_candidate):
                    print(f"[DEBUG] Found local file for URL: {local_candidate}")
                    image_path = local_candidate
                else:
                    print(f"[DEBUG] Local file not found at {local_candidate}, downloading...")
                    try:
                        import requests
                        response = requests.get(image_path, timeout=10)
                        if response.status_code == 200:
                            # Ensure directory exists
                            os.makedirs(cropped_folder, exist_ok=True)
                            with open(local_candidate, 'wb') as f:
                                f.write(response.content)
                            print(f"[DEBUG] Downloaded image to: {local_candidate}")
                            image_path = local_candidate
                        else:
                            print(f"[WARNING] Failed to download image: {response.status_code}")
                    except Exception as e:
                        print(f"[WARNING] Error downloading image: {e}")
            
            # Call listing APIs
            print(f"[DEBUG] Creating listing for {item.get('object_name')} on {platforms}")
            print(f"[DEBUG] Item data keys: {item.keys()}")
            print(f"[DEBUG] Price in item: {item.get('price')}, Estimated Value: {item.get('estimated_value')}")
            print(f"[DEBUG] Using image path: {image_path}")
            
            listing_result = pipeline_instance.call_listing_apis(
                item, 
                pricing_data, 
                platforms,
                image_path=image_path
            )
            print(f"[DEBUG] Listing result: {listing_result}")
            
            # Save to database if we have a cropped_id
            if cropped_id:
                try:
                    # Prepare listing data for DB
                    # Try to get title/price from item or pricing_data
                    title = item.get('recognition_result', {}).get('product_name') or item.get('object_name')
                    # Fix: Check 'price' first, then 'estimated_value'
                    price = item.get('price') or item.get('estimated_value') or 0.0
                    
                    # Aggressive fallback if price is 0
                    if price <= 0:
                        print("[WARNING] Price is 0, attempting to extract from pricing_data")
                        pricing_data = item.get('pricing_data', {})
                        if pricing_data:
                            summary = pricing_data.get('summary', {})
                            if summary.get('avg'):
                                try:
                                    price = float(summary.get('avg'))
                                except:
                                    pass
                            elif summary.get('median'):
                                try:
                                    price = float(summary.get('median'))
                                except:
                                    pass
                    
                    # Final fallback to avoid $0 listings
                    if price <= 0:
                        print("[WARNING] Price still 0, using default fallback of $25.0")
                        price = 25.0
                    
                    listing_db_data = {
                        "title": title,
                        "description": f"{title} in good used condition.",
                        "price": float(price)
                    }
                    
                    print(f"[DEBUG] Saving listing to database for cropped_id: {cropped_id}")
                    print(f"[DEBUG] DB Data: {listing_db_data}")
                    listing_id = pipeline_instance.save_listing_to_database(
                        cropped_id, 
                        listing_db_data, 
                        listing_result,
                        user_id=user_id
                    )
                    print(f"[DEBUG] Saved listing ID: {listing_id}")
                except Exception as e:
                    print(f"[ERROR] Failed to save listing to database: {e}")
            
            results.append({
                "object_name": item.get('object_name'),
                "listing_result": listing_result
            })
            
        return jsonify({
            'ok': True,
            'message': f'Processed {len(results)} items',
            'results': results
        })
        
    except Exception as e:
        print(f"❌ Listing creation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Listing creation failed: {str(e)}'
        }), 500
