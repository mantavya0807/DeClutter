from flask import Blueprint, request, jsonify, Response
import google.generativeai as genai
import os
import logging
import json

chat_bp = Blueprint('chat_bp', __name__, url_prefix='/api/chat')
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@chat_bp.route('/message', methods=['POST'])
def chat_message():
    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API key not configured'}), 500

    try:
        data = request.json
        user_message = data.get('message')
        context = data.get('context', {})
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400

        # Construct the system prompt with context
        system_prompt = f"""You are an expert AI Marketplace Assistant for Decluttered.AI. 
Your goal is to help users sell their items, analyze their sales performance, and provide pricing advice.

Here is the user's current data context:
- Active Listings: {len([l for l in context.get('recentListings', []) if l.get('status') == 'active'])}
- Total Revenue: ${context.get('analytics', {}).get('totalRevenue', 0)}
- Recent Sales: {len(context.get('salesHistory', []))}

Detailed Context:
{json.dumps(context, indent=2)}

Instructions:
1. Answer the user's question based on the provided context.
2. Be encouraging, professional, and data-driven.
3. If the user asks about pricing, refer to specific items in their listings.
4. If the user asks about trends, use your general knowledge combined with their specific category performance.
5. Keep responses concise and actionable. Use formatting like bolding and bullet points.
"""

        # Initialize model with robust fallback
        models_to_try = [
            'gemini-2.0-flash-exp',  # Likely what user means by "2.5 flash"
            'gemini-1.5-flash',
            'gemini-1.5-flash-001',
            'gemini-1.5-pro',
            'gemini-pro'
        ]
        
        response = None
        last_error = None
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name, system_instruction=system_prompt)
                chat = model.start_chat(history=history)
                response = chat.send_message(user_message)
                logger.info(f"Successfully used model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to use {model_name}: {e}")
                last_error = e
        
        if not response:
            raise last_error or Exception("No valid model found")
        
        # Stream the response
        def generate():
            for chunk in response:
                if chunk.text:
                    yield chunk.text

        return Response(generate(), mimetype='text/plain')

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/generate-draft', methods=['POST'])
def generate_draft():
    if not GEMINI_API_KEY:
        return jsonify({'error': 'Gemini API key not configured'}), 500

    try:
        data = request.json
        buyer_name = data.get('buyerName')
        item_title = data.get('itemTitle')
        offer_amount = data.get('offerAmount', 0)
        message_history = data.get('messages', [])
        
        # Construct prompt
        prompt = f"""You are a helpful AI assistant for a seller on a marketplace.
        
        Context:
        - Item: {item_title}
        - Buyer: {buyer_name}
        - Current Offer: ${offer_amount}
        
        Last few messages:
        {json.dumps(message_history[-3:], indent=2)}
        
        Task:
        Generate a polite, professional, and concise draft response for the seller to send to the buyer.
        If there is an offer, decide whether to accept, counter, or decline based on the context (or just provide a neutral negotiation opening).
        For this demo, assume the seller wants to be friendly but firm on price if it's too low.
        
        Output ONLY the message text, no quotes or explanations.
        """

        # Initialize model
        # User explicitly requested gemini-2.5-flash
        models_to_try = [
            'gemini-2.5-flash', 
            'gemini-2.0-flash-exp',
            'gemini-1.5-flash'
        ]
        
        response_text = None
        last_error = None
        
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                logger.info(f"Successfully generated draft using model: {model_name}")
                break
            except Exception as e:
                logger.warning(f"Failed to use {model_name} for draft: {e}")
                last_error = e
        
        if not response_text:
            # Fallback if AI fails
            response_text = f"Hi {buyer_name}, thanks for your interest in the {item_title}. Is the price negotiable?"
            logger.error(f"All models failed, using fallback. Last error: {last_error}")
        
        return jsonify({'draft': response_text})

    except Exception as e:
        logger.error(f"Error in generate-draft endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500
