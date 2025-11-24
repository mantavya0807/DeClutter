
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('apps/api/.env')

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

print("Checking 'conversations' table...")
try:
    response = supabase.table('messages').select("user_id").execute()
    data = response.data
    print(f"Found {len(data)} messages.")
            
except Exception as e:
    print(f"Error: {e}")
