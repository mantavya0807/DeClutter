
#!/usr/bin/env python3
"""
Complete Object Detection Pipeline for Decluttered.ai
- Single image processing instead of video
- YOLO object detection and cropping
- Database storage with Supabase
- Integration with recognition, scraper, and listing APIs
- Comprehensive marketplace automation
"""

import cv2
import time
import os
import glob
import json
import uuid
import base64
import requests
import statistics
from PIL import Image
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from ultralytics import YOLO
from supabase import create_client, Client
from dotenv import load_dotenv
import tempfile
from io import BytesIO

# API imports for integration
try:
    from gemini_ACCESS import process_image_and_objects_for_resale, process_text_with_gemini
    GEMINI_ACCESS_AVAILABLE = True
except ImportError:
    print("⚠️ gemini_ACCESS.py not found - using fallback object filtering")
    GEMINI_ACCESS_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configuration
CROP_BORDER_PERCENTAGE = 0.4  # Increased from 0.2 for more generous cropping
MAX_RESELLABLE_OBJECTS = 10
REPORT_FILENAME = "pipeline_analysis_report.txt"

# API endpoints
API_BASE_URL = "http://localhost"
# Unified API runs on port 5000
RECOGNITION_API_URL = f"{API_BASE_URL}:5000/api/recognition/basic"
SCRAPER_API_URL = f"{API_BASE_URL}:5000/api/scraper/prices"
FACEBOOK_LISTING_URL = f"{API_BASE_URL}:5000/api/listing/facebook"
EBAY_LISTING_URL = f"{API_BASE_URL}:5000/api/listing/ebay"

# Database configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

class ObjectDetectionPipeline:
    def __init__(self):
        self.yolo_model = None
        self.supabase_client = None
        self.processed_objects = []
        self.current_photo_id = None
        self.setup_yolo()
        self.setup_database()
        print("🔥 Object Detection Pipeline initialized")
    
    def setup_yolo(self):
        """Initialize YOLO model"""
        try:
            self.yolo_model = YOLO("yolov9c.pt")
            print("✅ YOLOv9 model loaded successfully")
        except Exception as e:
            print(f"❌ Could not load YOLO model: {e}")
            self.yolo_model = None
    
    def setup_database(self):
        """Initialize Supabase client"""
        try:
            if SUPABASE_URL and SUPABASE_ANON_KEY:
                self.supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
                print("✅ Supabase client initialized")
            else:
                print("⚠️ Supabase credentials not found - database features disabled")
        except Exception as e:
            print(f"❌ Could not initialize Supabase client: {e}")
    
    def upload_to_storage(self, file_path: str, bucket: str, object_name: str) -> Optional[str]:
        """Upload file to Supabase storage"""
        try:
            if not self.supabase_client:
                print("⚠️ Database not available - skipping storage upload")
                return None
            
            print(f"[DEBUG] Uploading {os.path.basename(file_path)} to bucket '{bucket}'...")
            
            # Check if bucket exists, if not try to create it or use fallback
            try:
                with open(file_path, 'rb') as file:
                    response = self.supabase_client.storage.from_(bucket).upload(
                        path=object_name,
                        file=file,
                        file_options={"content-type": "image/jpeg"}
                    )
            except Exception as e:
                # If bucket not found, try to use 'images' bucket as fallback
                if "Bucket not found" in str(e) or "404" in str(e):
                    print(f"⚠️ Bucket '{bucket}' not found. Trying fallback 'images' bucket...")
                    bucket = "images"
                    with open(file_path, 'rb') as file:
                        response = self.supabase_client.storage.from_(bucket).upload(
                            path=object_name,
                            file=file,
                            file_options={"content-type": "image/jpeg"}
                        )
                else:
                    raise e

            print(f"[DEBUG] Upload response received")
            
            if response:
                # Get public URL
                print(f"[DEBUG] Getting public URL for {object_name}...")
                public_url = self.supabase_client.storage.from_(bucket).get_public_url(object_name)
                print(f"✅ Uploaded to storage: {public_url}")
                return public_url
            else:
                print(f"[WARNING] Upload response was empty/falsy")
                    
        except Exception as e:
            print(f"❌ Storage upload failed: {type(e).__name__}: {e}")
            # Don't print traceback to avoid encoding errors in some consoles
            # import traceback
            # traceback.print_exc()
        
        return None
    
    def save_photo_to_database(self, image_path: str, storage_url: Optional[str] = None) -> Optional[str]:
        """Save photo metadata to database"""
        try:
            if not self.supabase_client:
                return str(uuid.uuid4()) # Return fake ID if no client
            
            file_stats = os.stat(image_path)
            photo_data = {
                "filename": os.path.basename(image_path),
                "url": storage_url or "", # Ensure not None
                "size": file_stats.st_size,
                "user_id": "anonymous",
                "processed": False
            }
            
            response = self.supabase_client.table("photos").insert(photo_data).execute()
            
            if response.data:
                photo_id = response.data[0]["id"]
                print(f"✅ Photo saved to database with ID: {photo_id}")
                return photo_id
                
        except Exception as e:
            print(f"❌ Database photo save failed: {e}")
            # Return a fake ID so the pipeline can continue even if DB save fails
            return str(uuid.uuid4())
        
        return None
    
    def save_cropped_object_to_database(self, photo_id: str, object_data: Dict) -> Optional[str]:
        """Save cropped object metadata to database"""
        try:
            if not self.supabase_client or not photo_id:
                return None
            
            cropped_data = {
                "photo_id": photo_id,
                "object_name": object_data["object_name"],
                "confidence": float(object_data["confidence"]),
                "bounding_box": object_data["bounding_box"],
                "cropped_image_url": object_data.get("storage_url", ""),
                "estimated_value": object_data.get("estimated_value")
            }
            
            response = self.supabase_client.table("cropped").insert(cropped_data).execute()
            
            if response.data:
                cropped_id = response.data[0]["id"]
                print(f"✅ Cropped object saved to database with ID: {cropped_id}")
                return cropped_id
                
        except Exception as e:
            print(f"❌ Database cropped object save failed: {e}")
            # Return a fake ID so the pipeline can continue even if DB save fails
            return str(uuid.uuid4())
        
        return None
    
    def process_single_image(self, image_path: str) -> List[Dict]:
        """Process a single image for object detection and cropping"""
        if not self.yolo_model:
            print("❌ YOLO model not available")
            return []
        
        print(f"🔍 Processing image: {os.path.basename(image_path)}")
        
        try:
            # Upload original image to storage and save to database
            print("[DEBUG] Starting storage upload...")
            timestamp = int(time.time())
            original_storage_name = f"original_{timestamp}_{os.path.basename(image_path)}"
            storage_url = self.upload_to_storage(image_path, "used_upload", original_storage_name)
            print(f"[DEBUG] Storage upload complete, URL: {storage_url}")
            
            print("[DEBUG] Saving photo to database...")
            self.current_photo_id = self.save_photo_to_database(image_path, storage_url)
            print(f"[DEBUG] Photo saved to database, ID: {self.current_photo_id}")
            
            # Run YOLO detection
            print(f"[DEBUG] Running YOLO detection on {image_path}...")
            
            # Verify image exists and is readable
            if not os.path.exists(image_path):
                print(f"❌ Image file does not exist: {image_path}")
                return []
                
            try:
                img_check = Image.open(image_path)
                print(f"[DEBUG] Image opened successfully. Size: {img_check.size}, Mode: {img_check.mode}")
            except Exception as e:
                print(f"❌ Failed to open image with PIL: {e}")
            
            # Run inference with lower threshold for debugging
            results = self.yolo_model.predict(source=image_path, conf=0.1, save=False, verbose=True)
            print(f"[DEBUG] YOLO detection complete. Results object: {results}")
            
            if len(results) > 0:
                print(f"[DEBUG] Raw boxes found: {len(results[0].boxes)}")
                for box in results[0].boxes:
                    print(f"[DEBUG] Box: cls={box.cls.item()}, conf={box.conf.item()}")
            
            all_detections = {}
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0].item())
                    class_name = self.yolo_model.names[class_id]
                    
                    # Map 'clock' to 'watch' since YOLOv9 (COCO) doesn't have 'watch'
                    if class_name == 'clock':
                        class_name = 'watch'
                        
                    coords = tuple(int(c) for c in box.xyxy[0].tolist())
                    confidence = float(box.conf[0].item())
                    
                    all_detections[coords] = {
                        "class_name": class_name,
                        "confidence": confidence
                    }
            
            if not all_detections:
                print("⚠️ No objects detected by YOLO")
                # Fallback: If no objects detected, treat the whole image as one object
                print("🔄 FALLBACK: Treating entire image as one object")
                
                img = Image.open(image_path)
                w, h = img.size
                
                # Create a fake detection for the whole image
                all_detections[(0, 0, w, h)] = {
                    "class_name": "item",
                    "confidence": 1.0
                }
            
            # Filter for largest instances of each object type
            filtered_detections = self.select_largest_instances(all_detections)
            unique_objects = list(set(det["class_name"] for det in filtered_detections.values()))
            
            print(f"🎯 Detected unique objects: {unique_objects}")
            
            # Filter for resellable objects using Gemini or fallback
            resellable_objects = self.filter_resellable_objects(image_path, unique_objects)
            
            if not resellable_objects:
                print("❌ No resellable objects found")
                return []
            
            print(f"💰 Processing all detected objects: {resellable_objects}")
            
            # Crop and process resellable objects
            processed_objects = []
            crop_index = 0
            
            for coords, detection in filtered_detections.items():
                # Case-insensitive check
                if detection["class_name"].lower() in [obj.lower() for obj in resellable_objects]:
                    crop_index += 1
                    
                    # Crop the object with generous border
                    cropped_path = self.crop_and_save_object(
                        image_path, coords, detection["class_name"], timestamp, crop_index
                    )
                    
                    if cropped_path:
                        # Ensure absolute path
                        cropped_path = os.path.abspath(cropped_path)
                        # Upload cropped image to storage
                        cropped_storage_name = f"cropped_{timestamp}_{crop_index}_{detection['class_name']}.png"
                        
                        # Determine content type based on extension
                        content_type = "image/png" if cropped_path.lower().endswith(".png") else "image/jpeg"
                        
                        # Upload with correct content type
                        try:
                            with open(cropped_path, 'rb') as file:
                                response = self.supabase_client.storage.from_("cropped").upload(
                                    path=cropped_storage_name,
                                    file=file,
                                    file_options={"content-type": content_type}
                                )
                            
                            if response:
                                cropped_storage_url = self.supabase_client.storage.from_("cropped").get_public_url(cropped_storage_name)
                            else:
                                cropped_storage_url = ""
                        except Exception as e:
                            print(f"⚠️ Storage upload failed: {e}")
                            cropped_storage_url = ""
                        
                        # Prepare object data
                        object_data = {
                            "object_name": detection["class_name"],
                            "confidence": detection["confidence"],
                            "bounding_box": {
                                "x": coords[0],
                                "y": coords[1],
                                "width": coords[2] - coords[0],
                                "height": coords[3] - coords[1]
                            },
                            "cropped_path": cropped_path,
                            # Use local path as fallback if storage upload fails
                            "storage_url": cropped_storage_url or "", 
                            "coordinates": coords
                        }
                        
                        # Save to database
                        cropped_id = self.save_cropped_object_to_database(self.current_photo_id, object_data)
                        object_data["cropped_id"] = cropped_id
                        
                        processed_objects.append(object_data)
                        print(f"✅ Cropped: {detection['class_name']} (confidence: {detection['confidence']:.2f}) with generous border")
            
            # Update photo as processed
            if self.supabase_client and self.current_photo_id:
                try:
                    self.supabase_client.table("photos").update({"processed": True}).eq("id", self.current_photo_id).execute()
                except Exception as e:
                    print(f"⚠️ Could not update photo status: {e}")
            
            return processed_objects
            
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            return []
    
    def select_largest_instances(self, all_detections: Dict) -> Dict:
        """Select only the largest instance of each object type"""
        class_largest = {}
        
        for coords, detection in all_detections.items():
            class_name = detection["class_name"]
            area = self.calculate_bbox_area(coords)
            
            if class_name not in class_largest:
                class_largest[class_name] = (coords, detection, area)
            else:
                current_coords, current_detection, current_area = class_largest[class_name]
                if area > current_area:
                    class_largest[class_name] = (coords, detection, area)
        
        # Convert back to original format
        filtered_detections = {}
        for class_name, (coords, detection, area) in class_largest.items():
            filtered_detections[coords] = detection
        
        return filtered_detections
    
    def calculate_bbox_area(self, coords: Tuple[int, int, int, int]) -> int:
        """Calculate bounding box area"""
        x_min, y_min, x_max, y_max = coords
        return (x_max - x_min) * (y_max - y_min)
    
    def filter_resellable_objects(self, image_path: str, detected_objects: List[str]) -> List[str]:
        """Return all detected objects - skip Gemini filtering, let main.py API decide resellability"""
        print("🎯 Skipping Gemini filtering - processing ALL detected objects")
        print(f"📝 Will analyze objects: {detected_objects}")
        
        # Return all detected objects - let the main.py recognition API decide what's resellable
        return detected_objects
    
    def crop_and_save_object(self, original_image_path: str, coords: Tuple, 
                           object_name: str, timestamp: int, index: int) -> Optional[str]:
        """Crop object from original image and save it"""
        try:
            img = Image.open(original_image_path)
            img_width, img_height = img.size
            
            x_min, y_min, x_max, y_max = coords
            
            # Add border
            object_width = x_max - x_min
            object_height = y_max - y_min
            border_x = int(object_width * CROP_BORDER_PERCENTAGE)
            border_y = int(object_height * CROP_BORDER_PERCENTAGE)
            
            # Expand coordinates with border
            new_x_min = max(0, x_min - border_x)
            new_y_min = max(0, y_min - border_y)
            new_x_max = min(img_width, x_max + border_x)
            new_y_max = min(img_height, y_max + border_y)
            
            # Crop image
            cropped_img = img.crop((new_x_min, new_y_min, new_x_max, new_y_max))
            
            # Create cropped directory if it doesn't exist
            os.makedirs("cropped_resellables", exist_ok=True)
            
            # Save cropped image as PNG to preserve quality and avoid JPEG artifacts/mode issues
            safe_object_name = object_name.replace(" ", "_").replace("/", "_")
            crop_filename = f"{timestamp}_{index}_{safe_object_name}.png"
            crop_path = os.path.join("cropped_resellables", crop_filename)
            
            # Save as PNG (supports RGBA, so no need for complex conversion)
            cropped_img.save(crop_path, "PNG")
            
            # Verify the file was saved correctly
            if os.path.exists(crop_path) and os.path.getsize(crop_path) > 0:
                print(f"📸 Cropped and saved: {crop_filename} ({os.path.getsize(crop_path)} bytes)")
                
                # Double check if we can open it back
                try:
                    with Image.open(crop_path) as check_img:
                        check_img.verify()
                    print(f"✅ Verified image integrity: {crop_filename}")
                except Exception as e:
                    print(f"❌ Saved image is corrupt: {e}")
                    return None
            else:
                print(f"❌ Failed to save image: {crop_filename}")
                return None
            
            return crop_path
            
        except Exception as e:
            print(f"❌ Error cropping object {object_name}: {e}")
            return None
    
    def call_recognition_api(self, image_path: str) -> Optional[Dict]:
        """Call the recognition API for product identification"""
        try:
            print(f"🔍 Calling recognition API at {RECOGNITION_API_URL}...")
            print(f"📁 Image path: {image_path}")
            
            # Check if image file exists
            if not os.path.exists(image_path):
                print(f"❌ Image file not found: {image_path}")
                return None
            
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                print(f"📷 Image encoded, size: {len(image_data)} bytes")
            
            # Determine mime type
            mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
            
            payload = {
                "image_base64": f"data:{mime_type};base64,{base64_image}"
            }
            
            print(f"🌐 Sending POST request to {RECOGNITION_API_URL}")
            response = requests.post(RECOGNITION_API_URL, json=payload, timeout=30)
            print(f"📡 Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"📋 Response data: {result}")
                if result.get("ok"):
                    data = result.get("data", {})
                    product_name = data.get("product_name")
                    if product_name:
                        print(f"✅ Product identified: {product_name}")
                        return data
                else:
                    print(f"⚠️ API returned ok=False: {result.get('message', 'Unknown error')}")
            else:
                print(f"❌ API returned status {response.status_code}: {response.text}")
            
            print("⚠️ Recognition API did not identify product")
            return None
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error - is recognition API running on port 3001? {e}")
            return None
        except Exception as e:
            print(f"❌ Recognition API call failed: {e}")
            return None
    
    def call_scraper_api(self, product_name: str) -> Optional[Dict]:
        """Call the scraper API for market prices"""
        try:
            print(f"💰 Getting market prices for: {product_name}")
            
            payload = {
                "product_name": product_name,
                "platforms": ["facebook", "ebay"],
                "condition_filter": "all"
            }
            
            response = requests.post(SCRAPER_API_URL, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    data = result.get("data", {})
                    comps = data.get("comps", [])
                    summary = data.get("summary", {})
                    
                    print(f"📊 Found {len(comps)} comparable listings")
                    if summary.get("avg"):
                        print(f"💵 Average price: ${summary['avg']}")
                    
                    return data
            
            print("⚠️ Scraper API did not find prices")
            return None
            
        except Exception as e:
            print(f"❌ Scraper API call failed: {e}")
            return None
    
    def calculate_optimal_price(self, pricing_data: Dict, condition: str = "used") -> float:
        """Calculate optimal listing price"""
        try:
            comps = pricing_data.get("comps", [])
            if not comps:
                return 50.0
            
            # Filter by condition
            condition_comps = [comp for comp in comps if comp.get("condition") == condition]
            if not condition_comps:
                condition_comps = comps
            
            prices = [comp["price"] for comp in condition_comps]
            
            if len(prices) >= 2:
                median_price = statistics.median(prices)
                optimal_price = median_price * 0.95  # Slightly competitive
            else:
                optimal_price = statistics.mean(prices) * 0.92
            
            return round(max(5.0, optimal_price), 2)
            
        except Exception:
            return 50.0
    
    def call_listing_apis(self, product_data: Dict, pricing_data: Dict, platforms: List[str], image_path: str = None) -> Dict:
        """Call listing APIs for marketplace posting"""
        results = {}
        
        try:
            # Normalize platforms to lowercase
            platforms = [p.lower() for p in platforms]
            print(f"[DEBUG] Normalized platforms: {platforms}")

            # Ensure product_data has the right structure
            # If it comes from recognition_result, it might be nested
            if "product_name" in product_data:
                name = product_data["product_name"]
            elif "object_name" in product_data:
                name = product_data["object_name"]
            else:
                name = product_data.get("name", "Unknown Item")
            
            # Prepare image data if path provided
            images = []
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as img_file:
                        b64_data = base64.b64encode(img_file.read()).decode('utf-8')
                        images.append(b64_data)
                    print(f"[DEBUG] Encoded image for listing: {image_path}")
                except Exception as e:
                    print(f"[WARNING] Failed to encode image for listing: {e}")

            # Construct clean payload for listing API
            listing_payload = {
                "product": {
                    "name": name,
                    "condition": "used",
                    "category": "Electronics", # Default, will be refined by listing API
                    "price": product_data.get("price") # Pass explicit price if available
                },
                "pricing_data": pricing_data,
                "platforms": platforms,
                "images": images
            }
            
            print(f"[DEBUG] Calling Listing API with payload: {json.dumps({k:v for k,v in listing_payload.items() if k != 'images'}, indent=2)}")
            
            # Facebook Marketplace listing
            if "facebook" in platforms or "facebook marketplace" in platforms:
                try:
                    print("📘 Creating Facebook Marketplace listing...")
                    # Call the specific Facebook endpoint directly for better control
                    response = requests.post(FACEBOOK_LISTING_URL, json=listing_payload, timeout=300)
                    
                    if response.status_code == 200:
                        result = response.json()
                        results["facebook"] = result
                        print(f"✅ Facebook listing API success: {result}")
                    else:
                        results["facebook"] = {"error": f"API returned {response.status_code}", "details": response.text}
                        print(f"❌ Facebook listing API failed: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    results["facebook"] = {"error": str(e)}
                    print(f"❌ Facebook listing failed: {e}")
            
            # eBay listing
            if "ebay" in platforms:
                try:
                    print("🔨 Creating eBay listing...")
                    response = requests.post(EBAY_LISTING_URL, json=listing_payload, timeout=180)
                    
                    if response.status_code == 200:
                        result = response.json()
                        results["ebay"] = result
                        print("✅ eBay listing API called successfully")
                    else:
                        results["ebay"] = {"error": f"API returned {response.status_code}"}
                        print(f"❌ eBay listing API failed: {response.status_code}")
                        
                except Exception as e:
                    results["ebay"] = {"error": str(e)}
                    print(f"❌ eBay listing failed: {e}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error calling listing APIs: {e}")
            return {"error": str(e)}
    
    def save_listing_to_database(self, cropped_id: str, listing_data: Dict, 
                               listing_results: Dict, user_id: str = "anonymous") -> Optional[str]:
        """Save listing information to database"""
        try:
            if not self.supabase_client or not cropped_id:
                return None
            
            # Try to get photo_id if current_photo_id is missing
            photo_id = self.current_photo_id
            if not photo_id:
                try:
                    # Fetch photo_id from cropped table
                    cropped_data = self.supabase_client.table("cropped").select("photo_id").eq("id", cropped_id).execute()
                    if cropped_data.data and len(cropped_data.data) > 0:
                        photo_id = cropped_data.data[0]["photo_id"]
                        print(f"[DEBUG] Recovered photo_id {photo_id} from cropped_id {cropped_id}")
                except Exception as e:
                    print(f"[WARNING] Could not recover photo_id: {e}")

            platforms = []
            facebook_post_id = None
            ebay_listing_id = None
            status = "draft"
            
            # Process listing results
            if listing_results.get("facebook", {}).get("ok"):
                platforms.append("facebook")
                facebook_result = listing_results["facebook"].get("data", {})
                if facebook_result.get("success"):
                    status = "posted"
                    # Extract Facebook post ID if available
                    
            if listing_results.get("ebay", {}).get("ok"):
                platforms.append("ebay")
                ebay_result = listing_results["ebay"].get("data", {})
                if ebay_result.get("success"):
                    status = "posted"
                    # Extract eBay listing ID if available
            
            listing_db_data = {
                "photo_id": photo_id,
                "cropped_id": cropped_id,
                "title": listing_data["title"],
                "description": listing_data["description"],
                "price": float(listing_data["price"]),
                "platforms": platforms,
                "status": status,
                "facebook_post_id": facebook_post_id,
                "ebay_listing_id": ebay_listing_id,
                "user_id": user_id
            }
            
            if status == "posted":
                listing_db_data["posted_at"] = datetime.now().isoformat()
            
            response = self.supabase_client.table("listings").insert(listing_db_data).execute()
            
            if response.data:
                listing_id = response.data[0]["id"]
                print(f"✅ Listing saved to database with ID: {listing_id}")
                return listing_id
                
        except Exception as e:
            print(f"❌ Database listing save failed: {e}")
        
        return None
    
    def run_complete_pipeline(self, image_path: str, platforms: List[str] = ["facebook", "ebay"]) -> Dict:
        """Run the complete pipeline on a single image"""
        try:
            print(f"🚀 Starting complete pipeline for: {os.path.basename(image_path)}")
            print("=" * 60)
            
            pipeline_results = {
                "image_path": image_path,
                "timestamp": datetime.now().isoformat(),
                "detected_objects": [],
                "processed_objects": [],
                "listings_created": [],
                "total_estimated_value": 0.0
            }
            
            # Step 1: Object Detection and Cropping
            print("1️⃣ OBJECT DETECTION AND CROPPING")
            processed_objects = self.process_single_image(image_path)
            
            if not processed_objects:
                print("❌ No resellable objects found")
                return pipeline_results
            
            pipeline_results["detected_objects"] = len(processed_objects)
            pipeline_results["processed_objects"] = processed_objects
            
            print(f"✅ Successfully processed {len(processed_objects)} resellable objects")
            
            # Debug: Show what objects we got
            print("🔍 DEBUG: Processed objects:")
            for i, obj in enumerate(processed_objects):
                print(f"  {i+1}. {obj.get('object_name', 'UNKNOWN')} - Path: {obj.get('cropped_path', 'NO_PATH')}")
            
            # Step 2: Process Each Object Through Recognition → Scraping → Listing
            print(f"\n🚀 Starting Step 2: Processing {len(processed_objects)} objects...")
            for i, obj_data in enumerate(processed_objects):
                print(f"\n2️⃣ PROCESSING OBJECT {i+1}/{len(processed_objects)}: {obj_data['object_name']}")
                print("-" * 40)
                
                obj_result = {
                    "object_name": obj_data["object_name"],
                    "cropped_id": obj_data.get("cropped_id"),
                    "recognition_result": None,
                    "pricing_result": None,
                    "listing_result": None,
                    "estimated_value": None
                }
                
                # Step 2a: Recognition API to determine if object is actually resellable
                recognition_result = self.call_recognition_api(obj_data["cropped_path"])
                obj_result["recognition_result"] = recognition_result
                
                # Check if recognition API found a valid product (indicating resellability)
                if not recognition_result or not recognition_result.get("product_name"):
                    print(f"⚠️ {obj_data['object_name']} not recognized as resellable product - skipping")
                    obj_result["skip_reason"] = "not_recognized_as_product"
                    pipeline_results["listings_created"].append(obj_result)
                    continue
                    
                product_name = recognition_result["product_name"]
                print(f"✅ {obj_data['object_name']} identified as resellable: {product_name}")
                
                # Step 2b: Scraper API for pricing
                pricing_result = self.call_scraper_api(product_name)
                obj_result["pricing_result"] = pricing_result
                
                if not pricing_result:
                    print(f"⚠️ Could not get market prices for {product_name}")
                    continue
                
                # Calculate optimal price
                optimal_price = self.calculate_optimal_price(pricing_result, "used")
                obj_result["estimated_value"] = optimal_price
                pipeline_results["total_estimated_value"] += optimal_price
                
                print(f"💰 Estimated value: ${optimal_price}")
                
                # Step 2c: Create marketplace listings
                product_data = {
                    "name": product_name,
                    "condition": "used",
                    "category": "Electronics"
                }
                
                print(f"🚀 Triggering listing APIs for {product_name}...")
                listing_results = self.call_listing_apis(
                    product_data, 
                    pricing_result, 
                    platforms,
                    image_path=obj_data.get("cropped_path")
                )
                print(f"🏁 Listing API results: {listing_results}")
                
                obj_result["listing_result"] = listing_results
                
                # Save listing to database
                listing_data = {
                    "title": product_name[:75],
                    "description": f"{product_name} in good used condition. Great value!",
                    "price": optimal_price
                }
                
                listing_id = None
                if obj_data.get("cropped_id"):
                    listing_id = self.save_listing_to_database(
                        obj_data["cropped_id"], listing_data, listing_results
                    )
                    obj_result["listing_id"] = listing_id
                
                pipeline_results["listings_created"].append(obj_result)
                
                print(f"✅ Completed processing {obj_data['object_name']}")
            
            # Step 3: Generate Summary Report
            print("\n3️⃣ PIPELINE SUMMARY")
            print("=" * 60)
            print(f"📸 Original image: {os.path.basename(image_path)}")
            print(f"🎯 Objects detected: {len(processed_objects)}")
            
            # Count only items that were recognized as products (actually resellable)
            resellable_count = sum(1 for item in pipeline_results["listings_created"] 
                                 if item.get("recognition_result") and item.get("recognition_result", {}).get("product_name"))
            
            print(f"💰 Resellable products found: {resellable_count}")
            print(f"💵 Total estimated value: ${pipeline_results['total_estimated_value']:.2f}")
            print(f"📋 Listings attempted: {resellable_count}")
            
            successful_listings = 0
            for listing in pipeline_results["listings_created"]:
                if listing.get("skip_reason"):
                    continue
                listing_result = listing.get("listing_result", {})
                if (listing_result.get("facebook", {}).get("ok") or 
                    listing_result.get("ebay", {}).get("ok")):
                    successful_listings += 1
            
            print(f"✅ Successful listings: {successful_listings}")
            
            # Write detailed report to file
            self.write_pipeline_report(pipeline_results)
            
            return pipeline_results
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            return {"error": str(e), "image_path": image_path}
    
    def write_pipeline_report(self, results: Dict):
        """Write detailed pipeline report to file"""
        try:
            report_lines = []
            report_lines.append("DECLUTTERED.AI - COMPLETE PIPELINE REPORT")
            report_lines.append("=" * 50)
            report_lines.append(f"Timestamp: {results['timestamp']}")
            report_lines.append(f"Image: {os.path.basename(results['image_path'])}")
            report_lines.append(f"Objects detected: {results['detected_objects']}")
            report_lines.append(f"Total estimated value: ${results['total_estimated_value']:.2f}")
            report_lines.append("")
            
            for i, obj in enumerate(results["listings_created"]):
                report_lines.append(f"OBJECT {i+1}: {obj['object_name']}")
                report_lines.append("-" * 30)
                
                # Check if object was skipped
                if obj.get("skip_reason"):
                    report_lines.append(f"  Status: SKIPPED - {obj['skip_reason']}")
                    report_lines.append("")
                    continue
                
                if obj["recognition_result"]:
                    product_name = obj["recognition_result"].get("product_name", "Unknown")
                    report_lines.append(f"  Identified as: {product_name}")
                
                if obj["pricing_result"]:
                    summary = obj["pricing_result"].get("summary", {})
                    comps_count = len(obj["pricing_result"].get("comps", []))
                    avg_price = summary.get("avg")
                    report_lines.append(f"  Market research: {comps_count} comparables")
                    if avg_price:
                        report_lines.append(f"  Average market price: ${avg_price}")
                
                if obj["estimated_value"]:
                    report_lines.append(f"  Estimated value: ${obj['estimated_value']}")
                
                # Listing results
                listing_result = obj.get("listing_result", {})
                if listing_result.get("facebook"):
                    fb_result = listing_result["facebook"]
                    status = "Success" if fb_result.get("ok") else "Failed"
                    report_lines.append(f"  Facebook listing: {status}")
                
                if listing_result.get("ebay"):
                    ebay_result = listing_result["ebay"]
                    status = "Success" if ebay_result.get("ok") else "Failed"
                    report_lines.append(f"  eBay listing: {status}")
                
                report_lines.append("")
            
            # Write report to file
            with open(REPORT_FILENAME, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            
            print(f"📄 Detailed report saved to: {REPORT_FILENAME}")
            
        except Exception as e:
            print(f"⚠️ Could not write report: {e}")

def main():
    """Main function to run the pipeline"""
    print("🔥 DECLUTTERED.AI - COMPLETE OBJECT DETECTION PIPELINE")
    print("=" * 60)
    
    pipeline = ObjectDetectionPipeline()
    
    if not pipeline.yolo_model:
        print("❌ YOLO model not available - cannot proceed")
        return
    
    # Get image from user
    print("📸 Please provide an image to process:")
    print("1. Place image in the current directory")
    print("2. Or provide full path to image")
    print()
    
    # Try to find images in current directory
    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
    found_images = []
    
    for ext in image_extensions:
        found_images.extend(glob.glob(ext))
        found_images.extend(glob.glob(ext.upper()))
    
    if found_images:
        print("📋 Found images in current directory:")
        for i, img in enumerate(found_images, 1):
            print(f"  {i}. {img}")
        print()
        
        try:
            choice = input("Enter image number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return
            
            image_index = int(choice) - 1
            if 0 <= image_index < len(found_images):
                selected_image = found_images[image_index]
            else:
                print("❌ Invalid selection")
                return
                
        except ValueError:
            print("❌ Invalid input")
            return
    else:
        # No images found, ask for path
        image_path = input("Enter full path to image file: ").strip()
        if not os.path.exists(image_path):
            print("❌ Image file not found")
            return
        selected_image = image_path
    
    # Ask for platforms
    print("\n📋 Select marketplace platforms:")
    print("1. Facebook Marketplace only")
    print("2. eBay only") 
    print("3. Both platforms (recommended)")
    
    try:
        platform_choice = input("Enter choice (1-3): ").strip()
        if platform_choice == "1":
            platforms = ["facebook"]
        elif platform_choice == "2":
            platforms = ["ebay"]
        else:
            platforms = ["facebook", "ebay"]
    except:
        platforms = ["facebook", "ebay"]
    
    print(f"\n🚀 Starting pipeline with platforms: {platforms}")
    
    # Run the complete pipeline
    results = pipeline.run_complete_pipeline(selected_image, platforms)
    
    if "error" not in results:
        print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"💰 Total estimated value: ${results.get('total_estimated_value', 0):.2f}")
        print(f"📄 See detailed report: {REPORT_FILENAME}")
    else:
        print(f"\n❌ Pipeline failed: {results['error']}")

if __name__ == "__main__":
    main()