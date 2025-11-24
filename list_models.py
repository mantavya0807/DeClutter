import google.generativeai as genai
import os
from dotenv import load_dotenv

# Try loading from .env and .env.local
load_dotenv()
load_dotenv('.env.local')
load_dotenv('frontend/.env.local')

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("GEMINI_API_KEY not found in environment variables.")
else:
    genai.configure(api_key=api_key)
    print(f"API Key found: {api_key[:5]}...")
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        print(models)
    except Exception as e:
        print(f"Error listing models: {e}")
