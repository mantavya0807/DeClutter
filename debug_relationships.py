
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv('apps/api/.env')

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(url, key)

print("Testing frontend query...")
try:
    # Mimic the frontend query exactly
    response = supabase.from_('conversations') \
        .select('*, messages(content, created_at)') \
        .order('last_message_at', desc=True) \
        .execute()
        
    data = response.data
    print(f"Query successful. Found {len(data)} conversations.")
    if len(data) > 0:
        print("First item keys:", data[0].keys())
        if 'messages' in data[0]:
            print(f"Messages in first item: {len(data[0]['messages'])}")
            
except Exception as e:
    print(f"Query FAILED: {e}")
    
    print("\nTrying simple query without join...")
    try:
        response = supabase.from_('conversations').select('*').execute()
        print(f"Simple query successful. Found {len(response.data)} conversations.")
    except Exception as e2:
        print(f"Simple query also failed: {e2}")
