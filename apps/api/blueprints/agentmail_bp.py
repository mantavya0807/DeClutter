#!/usr/bin/env python3
"""
AgentMail API Blueprint
Imports and wraps agent system classes from decluttered_api.py
"""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path to import decluttered_api.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Blueprint, request, jsonify

# Import the agent classes from decluttered_api.py
try:
    from decluttered_api import (
        DeclutteredAgentSystem,
        NegotiatorAgent,
        VoiceAssistantAgent,
        AGENTMAIL_AVAILABLE,
        LIVEKIT_AVAILABLE,
        GEMINI_AVAILABLE
    )
    print("[OK] Imported agent classes from decluttered_api.py")
except ImportError as e:
    print(f"[ERROR] Failed to import from decluttered_api.py: {e}")
    DeclutteredAgentSystem = None
    NegotiatorAgent = None
    VoiceAssistantAgent = None
    AGENTMAIL_AVAILABLE = False
    LIVEKIT_AVAILABLE = False
    GEMINI_AVAILABLE = False

# Create blueprint
agentmail_bp = Blueprint('agentmail', __name__, url_prefix='/api')

# Initialize agent system (singleton pattern)
agent_system_instance = None
negotiator_instance = None
voice_assistant_instance = None

def get_agent_system():
    """Get or create agent system instance"""
    global agent_system_instance, negotiator_instance, voice_assistant_instance
    
    if agent_system_instance is None and DeclutteredAgentSystem is not None:
        agent_system_instance = DeclutteredAgentSystem()
        
        if NegotiatorAgent is not None:
            negotiator_instance = NegotiatorAgent(agent_system_instance)
        
        if VoiceAssistantAgent is not None:
            voice_assistant_instance = VoiceAssistantAgent(agent_system_instance)
    
    return agent_system_instance, negotiator_instance, voice_assistant_instance

# Blueprint routes
@agentmail_bp.route('/health', methods=['GET'])
def health():
    """Health check with integration status"""
    try:
        agent_system, negotiator, voice_assistant = get_agent_system()
        
        if not agent_system:
            return jsonify({
                'status': 'OK',
                'service': 'decluttered_agentmail_integration',
                'timestamp': datetime.utcnow().isoformat(),
                'note': 'Instance not fully initialized',
                'version': '2.0.0-production'
            })
        
        # Test database connection
        db_status = "connected" if agent_system.supabase else "disconnected"
        
        # Test AgentMail connection
        agentmail_status = "connected" if agent_system.agentmail_client else "mock_mode"
        
        return jsonify({
            'status': 'OK',
            'service': 'decluttered_agentmail_integration',
            'timestamp': datetime.utcnow().isoformat(),
            'integrations': {
                'agentmail': {
                    'status': agentmail_status,
                    'inboxes_created': len(agent_system.agent_inboxes),
                    'sdk_available': AGENTMAIL_AVAILABLE
                },
                'livekit': {
                    'status': 'available' if LIVEKIT_AVAILABLE else 'unavailable',
                    'voice_agents': len(agent_system.livekit_agents),
                    'sdk_available': LIVEKIT_AVAILABLE
                },
                'database': {
                    'status': db_status,
                    'provider': 'supabase'
                },
                'ai': {
                    'gemini_available': GEMINI_AVAILABLE,
                    'model': 'gemini-2.0-flash-exp'
                }
            },
            'agents': {
                agent_id: {
                    'name': config.name,
                    'inbox': f"{config.username}@{config.domain}",
                    'status': 'active' if agent_id in agent_system.agent_inboxes else 'inactive'
                }
                for agent_id, config in agent_system.agents.items()
            },
            'version': '2.0.0-production'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e)
        }), 500

@agentmail_bp.route('/agentmail/webhook', methods=['POST'])
def agentmail_webhook():
    """AgentMail webhook for all incoming emails"""
    try:
        agent_system, negotiator, voice_assistant = get_agent_system()
        
        if not negotiator:
            return jsonify({'ok': False, 'error': 'Agent system not initialized'}), 500
        
        # AgentMail sends emails as JSON
        email_data = request.get_json()
        
        # Route to appropriate agent based on recipient
        recipient = email_data.get('to', '')
        
        if 'negotiations@' in recipient:
            result = asyncio.run(negotiator.process_buyer_email(email_data))
        else:
            result = {'ok': False, 'error': 'Unknown recipient'}
        
        return jsonify({'ok': True, 'result': result})
        
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@agentmail_bp.route('/voice/session', methods=['POST'])
def create_voice_session():
    """Create LiveKit voice session"""
    try:
        agent_system, negotiator, voice_assistant = get_agent_system()
        
        if not voice_assistant:
            return jsonify({'ok': False, 'error': 'Voice assistant not initialized'}), 500
        
        data = request.get_json()
        room_name = data.get('room_name', f'voice_session_{int(datetime.now().timestamp())}')
        
        result = asyncio.run(voice_assistant.create_voice_session(room_name))
        
        return jsonify({
            'ok': result.get('success', False),
            'data': result
        })
        
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@agentmail_bp.route('/voice/query', methods=['POST']) 
def voice_query():
    """Process voice query"""
    try:
        agent_system, negotiator, voice_assistant = get_agent_system()
        
        if not voice_assistant:
            return jsonify({'ok': False, 'error': 'Voice assistant not initialized'}), 500
        
        data = request.get_json()
        query = data.get('query', '')
        user_id = data.get('user_id', 'user_12345')  # Mock user
        
        result = asyncio.run(voice_assistant.process_voice_query(query, user_id))
        
        return jsonify({
            'ok': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

@agentmail_bp.route('/agents/demo-data', methods=['GET'])
def get_demo_data():
    """Get recent activity for hackathon demo"""
    try:
        agent_system, negotiator, voice_assistant = get_agent_system()
        
        if not agent_system or not agent_system.supabase:
            return jsonify({'ok': False, 'error': 'Database not connected'})
        
        # Get recent communications
        comms = agent_system.supabase.table('agent_communications').select('*').order('created_at', desc=True).limit(5).execute()
        
        # Get recent voice interactions  
        voice = agent_system.supabase.table('voice_interactions').select('*').order('created_at', desc=True).limit(5).execute()
        
        # Get market intelligence
        intel = agent_system.supabase.table('agent_market_intelligence').select('*').order('confidence_score', desc=True).limit(3).execute()
        
        return jsonify({
            'ok': True,
            'demo_data': {
                'recent_negotiations': comms.data,
                'recent_voice_queries': voice.data, 
                'market_intelligence': intel.data,
                'system_status': {
                    'total_inboxes': len(agent_system.agent_inboxes),
                    'agentmail_connected': agent_system.agentmail_client is not None,
                    'livekit_available': LIVEKIT_AVAILABLE
                }
            }
        })
        
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
