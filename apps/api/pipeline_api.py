#!/usr/bin/env python3
"""
Pipeline API - Complete Object Detection Pipeline as Web Service
Integrates with frontend for seamless image processing
"""

import os
import sys
import json
import base64
import tempfile
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import uuid

# Add root directory to path for imports
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
print(f"[DEBUG] Added to path: {root_dir}")

try:
    from object_detection_pipeline import ObjectDetectionPipeline
    PIPELINE_AVAILABLE = True
    print("[OK] Pipeline module imported successfully")
except ImportError as e:
    PIPELINE_AVAILABLE = False
    print(f"[ERROR] Pipeline module not available: {e}")

app = Flask(__name__)
CORS(app)

# Global pipeline instance
pipeline = None
processing_status = {}
JOBS_FILE = 'jobs.json'

def load_jobs():
    """Load jobs from disk"""
    global processing_status
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r') as f:
                processing_status = json.load(f)
            print(f"[INFO] Loaded {len(processing_status)} jobs from {JOBS_FILE}")
            
            # Check for interrupted jobs
            jobs_modified = False
            for job_id, job in processing_status.items():
                if job.get('status') in ['processing', 'recognition_complete']:
                    # Job was interrupted
                    print(f"[WARN] Job {job_id} was interrupted.")
                    jobs_modified = True
                    
                    # If we have results (even partial), mark as completed so user can see them
                    if job.get('results') and job['results'].get('listings_ready_to_review'):
                         print(f"[INFO] Job {job_id} has partial results. Marking as completed.")
                         job['status'] = 'completed'
                         job['message'] = 'Analysis interrupted but partial results available.'
                    elif job.get('partial_results'):
                         # We have phase 1 results
                         print(f"[INFO] Job {job_id} has phase 1 results. Marking as completed.")
                         job['status'] = 'completed'
                         job['message'] = 'Analysis interrupted. Objects detected but pricing incomplete.'
                         job['results'] = job['partial_results']
                    else:
                         job['status'] = 'error'
                         job['message'] = 'Processing interrupted by server restart. Please try again.'
            
            if jobs_modified:
                save_jobs()
                    
        except Exception as e:
            print(f"[WARNING] Failed to load jobs file: {e}")
            processing_status = {}

def save_jobs():
    """Save jobs to disk"""
    try:
        with open(JOBS_FILE, 'w') as f:
            json.dump(processing_status, f, indent=2)
    except Exception as e:
        print(f"[WARNING] Failed to save jobs file: {e}")

# Load jobs on startup
load_jobs()

# Configuration
UPLOAD_FOLDER = 'temp_uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_pipeline():
    """Initialize the pipeline instance"""
    global pipeline
    if PIPELINE_AVAILABLE and not pipeline:
        try:
            pipeline = ObjectDetectionPipeline()
            print("[OK] Pipeline initialized successfully")
            return True
        except Exception as e:
            print(f"[ERROR] Pipeline initialization failed: {e}")
            return False
    return pipeline is not None

def process_image_async(image_path: str, job_id: str, platforms: List[str] = None):
    """Process image in background thread with two-phase results"""
    global processing_status
    
    print(f"[DEBUG] process_image_async STARTED for job_id={job_id}, image_path={image_path}, platforms={platforms}")
    sys.stdout.flush()
    
    if platforms is None:
        platforms = ["facebook", "ebay"]
    
    try:
        print(f"[DEBUG] Setting initial processing status for job {job_id}")
        sys.stdout.flush()
        processing_status[job_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting object detection...",
            "timestamp": datetime.now().isoformat()
        }
        save_jobs()
        
        if not pipeline:
            processing_status[job_id] = {
                "status": "error",
                "progress": 0,
                "message": "Pipeline not initialized",
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()
            return
        
        # Phase 1: Object Detection and Recognition
        processing_status[job_id].update({
            "progress": 10,
            "message": "Running YOLO object detection..."
        })
        save_jobs()
        
        print(f"[DEBUG] Starting YOLO processing for job {job_id}, image: {image_path}")
        
        # Step 1: Process objects and get recognition results
        processed_objects = pipeline.process_single_image(image_path)
        
        print(f"[DEBUG] YOLO processing complete for job {job_id}, found {len(processed_objects) if processed_objects else 0} objects")
        sys.stdout.flush()
        
        if not processed_objects:
            processing_status[job_id] = {
                "status": "completed",
                "progress": 100,
                "message": "No resellable objects found",
                "results": {
                    "image_path": image_path,
                    "timestamp": datetime.now().isoformat(),
                    "detected_objects": 0,
                    "processed_objects": [],
                    "listings_created": [],
                    "total_estimated_value": 0.0
                },
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()
            return
            
        processing_status[job_id].update({
            "progress": 40,
            "message": f"Found {len(processed_objects)} objects, running recognition..."
        })
        save_jobs()
        
        # Step 2: Run recognition on each object to get product names
        recognition_results = []
        for i, obj_data in enumerate(processed_objects):
            processing_status[job_id].update({
                "progress": 40 + (i * 20 // len(processed_objects)),
                "message": f"Identifying object {i+1}/{len(processed_objects)}: {obj_data['object_name']}..."
            })
            save_jobs()
            
            print(f"[DEBUG] Calling recognition API for object {i+1}/{len(processed_objects)}: {obj_data['object_name']}")
            
            # Call recognition API
            recognition_result = pipeline.call_recognition_api(obj_data['cropped_path'])
            
            print(f"[DEBUG] Recognition API returned for object {i+1}: {recognition_result}")
            # Handle None response from recognition API
            obj_data['recognition_result'] = recognition_result if recognition_result is not None else {}
            recognition_results.append(obj_data)
        
        # Phase 1 Complete: Return partial results with object names
        partial_results = {
            "image_path": image_path,
            "timestamp": datetime.now().isoformat(),
            "detected_objects": len(processed_objects),
            "processed_objects": recognition_results,
            "phase": "recognition_complete",
            "listings_created": [],  # Will be filled in phase 2
            "total_estimated_value": 0.0  # Will be calculated in phase 2
        }
        
        processing_status[job_id] = {
            "status": "recognition_complete",
            "progress": 60,
            "message": f"Recognition complete! Found {len([r for r in recognition_results if r.get('recognition_result', {}) and r.get('recognition_result', {}).get('product_name')])} identifiable products. Starting price analysis...",
            "partial_results": partial_results,
            "timestamp": datetime.now().isoformat()
        }
        save_jobs()
        
        # Phase 2: Continue with price scraping and listing creation (in background)
        try:
            # Process each object through scraping and listing
            listings_created = []
            total_value = 0.0
            
            for i, obj_data in enumerate(recognition_results):
                processing_status[job_id].update({
                    "progress": 60 + (i * 30 // len(recognition_results)),
                    "message": f"Researching prices for {obj_data.get('recognition_result', {}).get('product_name', obj_data['object_name'])}..."
                })
                save_jobs()
                
                # Skip if no product name found
                recognition_result = obj_data.get('recognition_result', {})
                if not recognition_result or not recognition_result.get('product_name'):
                    listings_created.append({
                        "object_name": obj_data['object_name'],
                        "cropped_id": obj_data['cropped_id'],
                        "skip_reason": "Product not identified",
                        "recognition_result": recognition_result or {}
                    })
                    continue
                
                # Call scraping API for pricing
                product_name = recognition_result.get('product_name')
                print(f"[DEBUG] Calling scraper API for product: {product_name}")
                sys.stdout.flush()
                
                pricing_data = pipeline.call_scraper_api(product_name)
                print(f"[DEBUG] Scraper API returned for {product_name}: {pricing_data}")
                sys.stdout.flush()
                
                # Handle None response from scraper API
                if pricing_data is None:
                    pricing_data = {}
                obj_data['pricing_data'] = pricing_data
                
                # Calculate estimated value
                estimated_value = 0.0
                
                # Try to get average from summary
                if pricing_data.get('summary') and pricing_data['summary'].get('avg'):
                    estimated_value = float(pricing_data['summary']['avg'])
                
                # Fallback to calculating from comps if summary missing
                elif pricing_data.get('comps'):
                    prices = [c.get('price', 0) for c in pricing_data['comps'] if c.get('price')]
                    if prices:
                        estimated_value = sum(prices) / len(prices)
                
                # Fallback to legacy structure (just in case)
                elif pricing_data.get('facebook_prices'):
                    avg_facebook = sum(pricing_data['facebook_prices']) / len(pricing_data['facebook_prices'])
                    estimated_value = max(estimated_value, avg_facebook)
                elif pricing_data.get('ebay_prices'):
                    avg_ebay = sum(pricing_data['ebay_prices']) / len(pricing_data['ebay_prices'])
                    estimated_value = max(estimated_value, avg_ebay)
                
                total_value += estimated_value
                obj_data['estimated_value'] = estimated_value
                
                print(f"[DEBUG] Estimated value for {product_name}: ${estimated_value}")
                sys.stdout.flush()
                
                # Create listing data
                listing_data = {
                    "object_name": obj_data['object_name'],
                    "cropped_id": obj_data['cropped_id'],
                    "recognition_result": recognition_result,
                    "pricing_data": pricing_data,
                    "estimated_value": estimated_value,
                    "cropped_path": obj_data.get('cropped_path')
                }
                
                # SKIP AUTOMATIC LISTING - Wait for user confirmation
                # We just prepare the data for the frontend
                listings_created.append(listing_data)
                
                # Save intermediate results so they aren't lost if server crashes
                current_results = {
                    "image_path": image_path,
                    "timestamp": datetime.now().isoformat(),
                    "detected_objects": len(processed_objects),
                    "processed_objects": recognition_results,
                    "listings_ready_to_review": listings_created,
                    "total_estimated_value": total_value
                }
                
                processing_status[job_id].update({
                    "results": current_results
                })
                save_jobs()
            
            # Phase 2 Complete: Final results (Analysis Only)
            final_results = {
                "image_path": image_path,
                "timestamp": datetime.now().isoformat(),
                "detected_objects": len(processed_objects),
                "processed_objects": recognition_results,
                "listings_ready_to_review": listings_created, # Renamed from listings_created to avoid confusion
                "total_estimated_value": total_value
            }
            
            processing_status[job_id] = {
                "status": "completed", # Keep as completed so frontend stops polling
                "progress": 100,
                "message": "Analysis complete! Please review items and select platforms.",
                "results": final_results,
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()
            
        except Exception as e:
            print(f"Error in Phase 2 processing: {e}")
            # Even if Phase 2 fails, we still have Phase 1 results
            processing_status[job_id] = {
                "status": "completed",
                "progress": 100,
                "message": "Recognition completed, price analysis failed",
                "results": partial_results,
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()
            
        # Clean up temporary file
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except:
            pass
            
    except Exception as e:
        print(f"[ERROR] Exception in process_image_async for job {job_id}: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        
        processing_status[job_id] = {
            "status": "error",
            "progress": 0,
            "message": f"Processing failed: {str(e)}",
            "error_details": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        save_jobs()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'OK',
        'service': 'pipeline_api',
        'timestamp': datetime.now().isoformat(),
        'pipeline_available': PIPELINE_AVAILABLE,
        'pipeline_initialized': pipeline is not None
    })

@app.route('/api/pipeline/process', methods=['POST'])
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
                'error_code': 'PIPELINE_INIT_FAILED',
                'message': 'Pipeline initialization failed'
            }), 500
        
        # Check for file in request
        if 'image' not in request.files:
            return jsonify({
                'ok': False,
                'error_code': 'NO_FILE',
                'message': 'No image file provided'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'ok': False,
                'error_code': 'NO_FILENAME',
                'message': 'No file selected'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'ok': False,
                'error_code': 'INVALID_FILE_TYPE',
                'message': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Get processing options
        platforms = request.form.getlist('platforms') or ["facebook", "ebay"]
        sync_mode = request.form.get('sync', 'false').lower() == 'true'
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        timestamp = int(datetime.now().timestamp())
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        if sync_mode:
            # Synchronous processing (wait for completion)
            try:
                results = pipeline.run_complete_pipeline(file_path, platforms)
                
                # Clean up file
                try:
                    os.remove(file_path)
                except:
                    pass
                
                return jsonify({
                    'ok': True,
                    'job_id': job_id,
                    'status': 'completed',
                    'results': results
                })
                
            except Exception as e:
                try:
                    os.remove(file_path)
                except:
                    pass
                
                return jsonify({
                    'ok': False,
                    'error_code': 'PROCESSING_FAILED',
                    'message': f'Processing failed: {str(e)}'
                }), 500
        else:
            # Asynchronous processing (return immediately)
            processing_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "Image uploaded, starting processing...",
                "timestamp": datetime.now().isoformat()
            }
            save_jobs()
            
            # Start processing in background thread
            print(f"[DEBUG] Creating background thread for job {job_id}, file: {file_path}")
            sys.stdout.flush()
            
            thread = threading.Thread(
                target=process_image_async,
                args=(file_path, job_id, platforms)
            )
            thread.daemon = True
            
            print(f"[DEBUG] Starting background thread for job {job_id}")
            sys.stdout.flush()
            
            thread.start()
            
            print(f"[DEBUG] Background thread started for job {job_id}")
            sys.stdout.flush()
            
            return jsonify({
                'ok': True,
                'job_id': job_id,
                'status': 'queued',
                'message': 'Image uploaded successfully. Processing started.',
                'platforms': platforms
            })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/api/pipeline/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get processing status for a job"""
    try:
        if job_id not in processing_status:
            return jsonify({
                'ok': False,
                'error_code': 'JOB_NOT_FOUND',
                'message': 'Job ID not found'
            }), 404
        
        status = processing_status[job_id]
        return jsonify({
            'ok': True,
            'job_id': job_id,
            **status
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Error retrieving status: {str(e)}'
        }), 500

@app.route('/api/pipeline/jobs', methods=['GET'])
def list_jobs():
    """List all processing jobs"""
    try:
        return jsonify({
            'ok': True,
            'jobs': [
                {'job_id': job_id, **status}
                for job_id, status in processing_status.items()
            ],
            'total_jobs': len(processing_status)
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Error retrieving jobs: {str(e)}'
        }), 500

@app.route('/api/pipeline/clear-jobs', methods=['POST'])
def clear_completed_jobs():
    """Clear completed or failed jobs"""
    try:
        global processing_status
        
        completed_statuses = ['completed', 'error']
        cleared_jobs = []
        
        for job_id, status in list(processing_status.items()):
            if status['status'] in completed_statuses:
                cleared_jobs.append(job_id)
                del processing_status[job_id]
        
        save_jobs()
        
        return jsonify({
            'ok': True,
            'message': f'Cleared {len(cleared_jobs)} completed jobs',
            'cleared_jobs': cleared_jobs
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Error clearing jobs: {str(e)}'
        }), 500

@app.route('/api/pipeline/cropped-images', methods=['GET'])
def list_cropped_images():
    """List available cropped images"""
    try:
        cropped_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cropped_resellables')
        
        if not os.path.exists(cropped_folder):
            return jsonify({
                'ok': True,
                'images': [],
                'total': 0
            })
        
        images = []
        for filename in os.listdir(cropped_folder):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.webp')):
                file_path = os.path.join(cropped_folder, filename)
                file_stats = os.stat(file_path)
                images.append({
                    'filename': filename,
                    'size': file_stats.st_size,
                    'created': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
                    'url': f'/api/pipeline/cropped-image/{filename}'
                })
        
        # Sort by creation time (newest first)
        images.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({
            'ok': True,
            'images': images,
            'total': len(images)
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Error listing images: {str(e)}'
        }), 500

@app.route('/api/pipeline/cropped-image/<filename>', methods=['GET'])
def serve_cropped_image(filename):
    """Serve cropped image file"""
    try:
        cropped_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cropped_resellables')
        file_path = os.path.join(cropped_folder, secure_filename(filename))
        
        if not os.path.exists(file_path):
            return jsonify({
                'ok': False,
                'error_code': 'FILE_NOT_FOUND',
                'message': 'Image file not found'
            }), 404
        
        return send_file(file_path)
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Error serving image: {str(e)}'
        }), 500

@app.route('/api/pipeline/test', methods=['GET'])
def test_pipeline():
    """Test pipeline with sample image"""
    try:
        if not initialize_pipeline():
            return jsonify({
                'ok': False,
                'error_code': 'PIPELINE_INIT_FAILED',
                'message': 'Pipeline initialization failed'
            })
        
        # Look for sample images
        sample_folders = ['captures', '.']
        sample_image = None
        
        for folder in sample_folders:
            folder_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), folder)
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        sample_image = os.path.join(folder_path, filename)
                        break
                if sample_image:
                    break
        
        if not sample_image:
            return jsonify({
                'ok': False,
                'error_code': 'NO_SAMPLE_IMAGE',
                'message': 'No sample image found for testing'
            })
        
        # Test with synchronous processing
        results = pipeline.run_complete_pipeline(sample_image, ["facebook"])
        
        return jsonify({
            'ok': True,
            'message': 'Test completed successfully',
            'sample_image': os.path.basename(sample_image),
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'ok': False,
            'error_code': 'TEST_FAILED',
            'message': f'Test failed: {str(e)}'
        }), 500

@app.route('/api/pipeline/create-listings', methods=['POST'])
def create_listings():
    """Create listings for selected items"""
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
                'error_code': 'PIPELINE_INIT_FAILED',
                'message': 'Pipeline initialization failed'
            }), 500
            
        data = request.get_json()
        if not data:
            return jsonify({'ok': False, 'message': 'No data provided'}), 400
            
        items = data.get('items', [])
        platforms = data.get('platforms', ["facebook", "ebay"])
        user_id = data.get('user_id', 'anonymous')
        
        if not items:
            return jsonify({'ok': False, 'message': 'No items selected'}), 400
            
        results = []
        
        print(f"[DEBUG] Processing {len(items)} items for user {user_id}")
        
        for item in items:
            # Extract necessary data from the item object
            # The frontend should pass back the object structure we sent in 'listings_ready_to_review'
            
            # Ensure we have pricing data
            pricing_data = item.get('pricing_data', {})
            
            # Call listing APIs
            print(f"[DEBUG] Creating listing for {item.get('object_name')} on {platforms}")
            
            # Get cropped image path if available
            cropped_id = item.get('cropped_id')
            print(f"[DEBUG] Item cropped_id: {cropped_id}")
            
            image_path = None
            
            # Try to find the image file
            if cropped_id:
                # Look in cropped_resellables folder
                cropped_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cropped_resellables')
                # We need to find the file that corresponds to this ID or object
                # Since we don't have the exact filename in the item dict usually, we might need to search or pass it from frontend
                # But wait, the item dict comes from 'listings_ready_to_review' which comes from 'processed_objects'
                # processed_objects has 'cropped_path'
                
                if 'cropped_path' in item:
                    image_path = item['cropped_path']
                elif 'image_url' in item and 'cropped-image/' in item['image_url']:
                    # Extract filename from URL
                    filename = item['image_url'].split('/')[-1]
                    image_path = os.path.join(cropped_folder, filename)
            
            print(f"[DEBUG] Using image path for listing: {image_path}")
            
            listing_result = pipeline.call_listing_apis(
                item, 
                pricing_data, 
                platforms,
                image_path=image_path
            )
            
            # Save to database if we have a cropped_id
            if cropped_id:
                try:
                    # Prepare listing data for DB
                    # Try to get title/price from item or pricing_data
                    title = item.get('recognition_result', {}).get('product_name') or item.get('object_name')
                    price = item.get('estimated_value') or 0.0
                    
                    listing_db_data = {
                        "title": title,
                        "description": f"{title} in good used condition.",
                        "price": float(price)
                    }
                    
                    print(f"[DEBUG] Saving listing to database for cropped_id: {cropped_id}")
                    listing_id = pipeline.save_listing_to_database(
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
        return jsonify({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'message': f'Listing creation failed: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("[FIRE] DECLUTTERED.AI - PIPELINE API")
    print("=" * 50)
    print("[GLOBE] Server: http://localhost:3005")
    print("📸 Process Image: POST /api/pipeline/process")
    print("[CHART] Job Status: GET /api/pipeline/status/<job_id>")
    print("📋 List Jobs: GET /api/pipeline/jobs")
    print("🖼️ Cropped Images: GET /api/pipeline/cropped-images")
    print("🧪 Test Pipeline: GET /api/pipeline/test")
    print("❤️ Health: GET /health")
    print()
    print("[SPARKLES] Features:")
    print("  - Complete pipeline processing via web API")
    print("  - Async and sync processing modes")
    print("  - Job status tracking with progress updates")
    print("  - Cropped image serving")
    print("  - Frontend integration ready")
    print()
    
    # Initialize pipeline on startup
    if initialize_pipeline():
        print("[OK] Pipeline ready for processing!")
    else:
        print("[WARNING] Pipeline initialization failed - some features may not work")
    
    print("[ROCKET] Starting server...")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=3005, threaded=True)
    except Exception as e:
        print(f"[ERROR] Server failed to start: {e}")