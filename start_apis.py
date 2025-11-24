#!/usr/bin/env python3
"""
Start Unified API Server for Decluttered.AI
This script starts the unified Flask application with all services as blueprints
"""

import os
import sys
import time
import subprocess
import signal
from pathlib import Path

# Unified API server configuration
UNIFIED_SERVER = {
    'name': 'Decluttered.AI Unified API',
    'script': 'unified_app.py',
    'port': 5000,
    'description': 'All services consolidated: Recognition, Scraper, Listing, eBay, Pipeline'
}

class UnifiedServerManager:
    def __init__(self):
        self.process = None
        self.api_dir = Path(__file__).parent / 'apps' / 'api'
        
        if not self.api_dir.exists():
            self.api_dir = Path(__file__).parent / 'api'
        
        if not self.api_dir.exists():
            print("❌ Could not find API directory")
            sys.exit(1)
            
        print(f"📁 Using API directory: {self.api_dir}")
    
    def start_server(self):
        """Start the unified API server"""
        script_path = self.api_dir / UNIFIED_SERVER['script']
        
        if not script_path.exists():
            print(f"❌ Script not found: {script_path}")
            return None
        
        try:
            print(f"🚀 Starting {UNIFIED_SERVER['name']} on port {UNIFIED_SERVER['port']}...")
            
            # Start the process
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.api_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',  # Force UTF-8 encoding for output
                errors='replace'   # Replace characters that can't be decoded
            )
            
            # Monitor startup output
            print("📋 Server startup log:")
            print("-" * 50)
            startup_lines = []
            for _ in range(50):  # Read first 50 lines
                try:
                    line = process.stdout.readline()
                    if line:
                        print(f"   {line.rstrip()}")
                        startup_lines.append(line)
                        if "Debugger PIN" in line or "Running on" in line:
                            break
                except:
                    break
            
            # Give it a moment to fully start
            time.sleep(1)
            
            # Check if it's still running
            if process.poll() is None:
                print("-" * 50)
                print(f"✅ {UNIFIED_SERVER['name']} started successfully (PID: {process.pid})")
                return process
            else:
                print(f"❌ {UNIFIED_SERVER['name']} failed to start")
                return None
                
        except Exception as e:
            print(f"❌ Failed to start {UNIFIED_SERVER['name']}: {e}")
            return None
    
    def start(self):
        """Start unified server"""
        print("🔥 DECLUTTERED.AI - UNIFIED API SERVER")
        print("=" * 50)
        print("Starting unified API server with all services...")
        print()
        
        self.process = self.start_server()
        
        if self.process:
            print()
            print("✅ Unified API server is running!")
            print()
            print("📋 Available Services:")
            print(f"   • Recognition API: http://localhost:{UNIFIED_SERVER['port']}/api/recognition")
            print(f"   • Scraper API: http://localhost:{UNIFIED_SERVER['port']}/api/scraper")
            print(f"   • Listing API: http://localhost:{UNIFIED_SERVER['port']}/api/listing")
            print(f"   • eBay API: http://localhost:{UNIFIED_SERVER['port']}/api/ebay")
            print(f"   • Pipeline API: http://localhost:{UNIFIED_SERVER['port']}/api/pipeline")
            
            print()
            print("🌐 Frontend Integration:")
            print(f"   • Main health check: http://localhost:{UNIFIED_SERVER['port']}/health")
            print("   • All services accessible through single port!")
            
            print()
            print("🔍 Service Health Checks:")
            print(f"   • Recognition: http://localhost:{UNIFIED_SERVER['port']}/api/recognition/health")
            print(f"   • Scraper: http://localhost:{UNIFIED_SERVER['port']}/api/scraper/health")
            print(f"   • Listing: http://localhost:{UNIFIED_SERVER['port']}/api/listing/health")
            print(f"   • eBay: http://localhost:{UNIFIED_SERVER['port']}/api/ebay/health")
            print(f"   • Pipeline: http://localhost:{UNIFIED_SERVER['port']}/api/pipeline/health")
            
            print()
            print("🛑 To stop the server, press Ctrl+C")
            print()
            
            return True
        else:
            print("❌ Failed to start unified server")
            return False
    
    def stop(self):
        """Stop the unified server"""
        if self.process:
            print("\n🛑 Stopping unified API server...")
            
            try:
                self.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.process.wait(timeout=5)
                    print("✅ Server stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    print("⚡ Force killing server...")
                    self.process.kill()
                    self.process.wait()
                    
            except Exception as e:
                print(f"⚠️ Error stopping server: {e}")
        
        print("✅ Server stopped")
    
    def run(self):
        """Main run method"""
        try:
            # Setup signal handling
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Start server
            if not self.start():
                return 1
            
            # Keep main thread alive and stream output
            try:
                for line in self.process.stdout:
                    print(line.rstrip())
            except KeyboardInterrupt:
                pass
            
            return 0
            
        except Exception as e:
            print(f"❌ Server manager error: {e}")
            return 1
        finally:
            self.stop()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n📡 Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

def check_python_version():
    """Check if Python version is adequate"""
    if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    return True

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = {
        'flask': 'flask',
        'flask_cors': 'flask_cors', 
        'ultralytics': 'ultralytics',
        'opencv-python': 'cv2',
        'selenium': 'selenium',
        'requests': 'requests'
    }
    
    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("💡 Install with: pip install " + ' '.join(missing_packages))
        return False
    
    return True

def main():
    """Main entry point"""
    print("🔥 DECLUTTERED.AI - API SERVER STARTUP")
    print("=" * 50)
    
    # Pre-flight checks
    if not check_python_version():
        return 1
    
    if not check_dependencies():
        return 1
    
    # Create and run unified server manager
    manager = UnifiedServerManager()
    return manager.run()

if __name__ == '__main__':
    sys.exit(main())