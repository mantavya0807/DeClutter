#!/usr/bin/env python3
"""
Unified Flask Application for Decluttered.AI
Consolidates all API services into a single Flask app with blueprints
"""

from flask import Flask, jsonify
from flask_cors import CORS
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config=None):
    """Application factory pattern"""
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.update(
        SECRET_KEY='your-secret-key-here',  # TODO: Move to environment variable
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
        JSON_SORT_KEYS=False,
        CORS_HEADERS='Content-Type'
    )
    
    if config:
        app.config.update(config)
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register blueprints
    try:
        from blueprints.recognition_bp import recognition_bp
        app.register_blueprint(recognition_bp)
        logger.info("[OK] Registered Recognition API blueprint")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register Recognition blueprint: {e}")
    
    try:
        from blueprints.scraper_bp import scraper_bp
        app.register_blueprint(scraper_bp)
        logger.info("[OK] Registered Scraper API blueprint")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register Scraper blueprint: {e}")
    
    try:
        from blueprints.listing_bp import listing_bp
        app.register_blueprint(listing_bp)
        logger.info("[OK] Registered Listing API blueprint")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register Listing blueprint: {e}")
    
    try:
        from blueprints.ebay_bp import ebay_bp
        app.register_blueprint(ebay_bp)
        logger.info("[OK] Registered eBay API blueprint")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register eBay blueprint: {e}")
    
    # AgentMail blueprint - skipped for now, will revisit later
    # try:
    #     from blueprints.agentmail_bp import agentmail_bp
    #     app.register_blueprint(agentmail_bp)
    #     logger.info("✅ Registered AgentMail API blueprint")
    # except Exception as e:
    #     logger.error(f"❌ Failed to register AgentMail blueprint: {e}")
    
    try:
        from blueprints.pipeline_bp import pipeline_bp
        app.register_blueprint(pipeline_bp)
        logger.info("[OK] Registered Pipeline API blueprint")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register Pipeline blueprint: {e}")
    
    try:
        from blueprints.chat_bp import chat_bp
        app.register_blueprint(chat_bp)
        logger.info("[OK] Registered Chat API blueprint")
    except Exception as e:
        logger.error(f"[ERROR] Failed to register Chat blueprint: {e}")
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Unified health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'Decluttered.AI Unified API',
            'version': '1.0.0',
            'endpoints': {
                'recognition': '/api/recognition',
                'scraper': '/api/scraper',
                'listing': '/api/listing',
                'agentmail': '/api/agentmail',
                'pipeline': '/api/pipeline',
                'chat': '/api/chat'
            }
        })
    
    # Root endpoint
    @app.route('/', methods=['GET'])
    def root():
        """API root endpoint"""
        return jsonify({
            'message': 'Decluttered.AI Unified API',
            'version': '1.0.0',
            'health': '/health',
            'documentation': '/api/docs'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested endpoint does not exist',
            'status': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status': 500
        }), 500
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'error': 'Request Entity Too Large',
            'message': 'File size exceeds maximum allowed (16MB)',
            'status': 413
        }), 413
    
    logger.info("Unified Flask app created successfully")
    
    return app

def main():
    """Main entry point"""
    app = create_app()
    
    # Always use port 5000 for backend API (frontend uses 3000)
    import os
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"Starting Decluttered.AI Unified API on port {port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
