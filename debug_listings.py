
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in environment variables.")
    exit(1)

supabase: Client = create_client(url, key)

try:
    response = supabase.table("listings").select("*").execute()
    print(f"Found {len(response.data)} listings.")
    for listing in response.data:
        print(f"ID: {listing.get('id')}, User ID: {listing.get('user_id')}, Title: {listing.get('title')}")
except Exception as e:
    print(f"Error fetching listings: {e}")
