-- ==============================================
-- COMPLETE SUPABASE SETUP FOR DECLUTTERED.AI
-- ==============================================

-- 1. CREATE STORAGE BUCKETS
-- ==============================================

-- Delete existing buckets if they exist
-- DELETE FROM storage.buckets WHERE id IN ('used_upload', 'cropped'); -- Commented out to prevent FK violation if buckets have files

-- Create used_upload bucket for original photos
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'used_upload', 
  'used_upload', 
  true, 
  10485760, -- 10MB limit for photos
  ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
) ON CONFLICT (id) DO NOTHING;

-- Create cropped bucket for detected object images
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'cropped', 
  'cropped', 
  true, 
  5242880, -- 5MB limit for cropped images
  ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
) ON CONFLICT (id) DO NOTHING;

-- 2. CREATE STORAGE POLICIES
-- ==============================================

-- Policies for used_upload bucket
DROP POLICY IF EXISTS "Allow public uploads to used_upload" ON storage.objects;
CREATE POLICY "Allow public uploads to used_upload" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'used_upload');

DROP POLICY IF EXISTS "Allow public reads from used_upload" ON storage.objects;
CREATE POLICY "Allow public reads from used_upload" ON storage.objects
FOR SELECT USING (bucket_id = 'used_upload');

-- Policies for cropped bucket
DROP POLICY IF EXISTS "Allow public uploads to cropped" ON storage.objects;
CREATE POLICY "Allow public uploads to cropped" ON storage.objects
FOR INSERT WITH CHECK (bucket_id = 'cropped');

DROP POLICY IF EXISTS "Allow public reads from cropped" ON storage.objects;
CREATE POLICY "Allow public reads from cropped" ON storage.objects
FOR SELECT USING (bucket_id = 'cropped');

-- 3. CREATE DATABASE TABLES
-- ==============================================

-- Photos table for original uploaded photos
CREATE TABLE IF NOT EXISTS public.photos (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  filename TEXT NOT NULL,
  url TEXT NOT NULL,
  size BIGINT NOT NULL,
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  user_id TEXT DEFAULT 'anonymous',
  processed BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure columns exist (in case table existed from previous schema)
ALTER TABLE public.photos ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE public.photos ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT false;

-- Cropped objects table for detected resellable items
CREATE TABLE IF NOT EXISTS public.cropped (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  photo_id UUID REFERENCES public.photos(id) ON DELETE CASCADE,
  object_name TEXT NOT NULL,
  confidence DECIMAL(3,2) NOT NULL,
  bounding_box JSONB NOT NULL, -- {x, y, width, height}
  cropped_image_url TEXT NOT NULL,
  estimated_value DECIMAL(10,2),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Listings table for posted items
CREATE TABLE IF NOT EXISTS public.listings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  photo_id UUID REFERENCES public.photos(id) ON DELETE CASCADE,
  cropped_id UUID REFERENCES public.cropped(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  platforms TEXT[] NOT NULL, -- Array of platforms: ['facebook', 'ebay', 'both']
  status TEXT DEFAULT 'draft', -- 'draft', 'posted', 'sold', 'removed'
  facebook_post_id TEXT,
  ebay_listing_id TEXT,
  posted_at TIMESTAMP WITH TIME ZONE,
  user_id TEXT DEFAULT 'anonymous',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations table
CREATE TABLE IF NOT EXISTS public.conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    platform_thread_id TEXT UNIQUE NOT NULL, -- The unique ID from Facebook URL or composite key
    buyer_name TEXT NOT NULL,
    item_title TEXT,
    item_id TEXT, -- Optional, if we can link to our listings
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    is_unread BOOLEAN DEFAULT false,
    status TEXT DEFAULT 'active', -- active, archived, blocked
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure columns exist (in case table existed from previous schema)
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS platform_thread_id TEXT;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS buyer_name TEXT;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS item_title TEXT;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS is_unread BOOLEAN DEFAULT false;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

-- Messages table
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE,
    sender TEXT NOT NULL, -- 'buyer' or 'me'
    content TEXT,
    platform_timestamp TIMESTAMPTZ, -- When it was sent on FB
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ensure columns exist (in case table existed from previous schema)
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS conversation_id UUID REFERENCES public.conversations(id) ON DELETE CASCADE;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS sender TEXT;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS content TEXT;
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS platform_timestamp TIMESTAMPTZ;

-- 4. CREATE INDEXES
-- ==============================================

-- Photos indexes
CREATE INDEX IF NOT EXISTS idx_photos_uploaded_at ON public.photos(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_photos_user_id ON public.photos(user_id);
CREATE INDEX IF NOT EXISTS idx_photos_processed ON public.photos(processed);

-- Cropped indexes
CREATE INDEX IF NOT EXISTS idx_cropped_photo_id ON public.cropped(photo_id);
CREATE INDEX IF NOT EXISTS idx_cropped_object_name ON public.cropped(object_name);
CREATE INDEX IF NOT EXISTS idx_cropped_confidence ON public.cropped(confidence DESC);

-- Listings indexes
CREATE INDEX IF NOT EXISTS idx_listings_photo_id ON public.listings(photo_id);
CREATE INDEX IF NOT EXISTS idx_listings_cropped_id ON public.listings(cropped_id);
CREATE INDEX IF NOT EXISTS idx_listings_user_id ON public.listings(user_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON public.listings(status);
CREATE INDEX IF NOT EXISTS idx_listings_created_at ON public.listings(created_at DESC);

-- Indexes for messaging
CREATE INDEX IF NOT EXISTS idx_conversations_thread_id ON public.conversations(platform_thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON public.messages(conversation_id);

-- 5. ENABLE ROW LEVEL SECURITY
-- ==============================================

ALTER TABLE public.photos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cropped ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- 6. CREATE RLS POLICIES
-- ==============================================

-- Photos policies
DROP POLICY IF EXISTS "Allow public photo uploads" ON public.photos;
CREATE POLICY "Allow public photo uploads" ON public.photos FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "Allow public photo reads" ON public.photos;
CREATE POLICY "Allow public photo reads" ON public.photos FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public photo updates" ON public.photos;
CREATE POLICY "Allow public photo updates" ON public.photos FOR UPDATE USING (true);

-- Cropped policies
DROP POLICY IF EXISTS "Allow public cropped uploads" ON public.cropped;
CREATE POLICY "Allow public cropped uploads" ON public.cropped FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "Allow public cropped reads" ON public.cropped;
CREATE POLICY "Allow public cropped reads" ON public.cropped FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public cropped updates" ON public.cropped;
CREATE POLICY "Allow public cropped updates" ON public.cropped FOR UPDATE USING (true);

-- Listings policies
DROP POLICY IF EXISTS "Allow public listing uploads" ON public.listings;
CREATE POLICY "Allow public listing uploads" ON public.listings FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS "Allow public listing reads" ON public.listings;
CREATE POLICY "Allow public listing reads" ON public.listings FOR SELECT USING (true);
DROP POLICY IF EXISTS "Allow public listing updates" ON public.listings;
CREATE POLICY "Allow public listing updates" ON public.listings FOR UPDATE USING (true);

-- Conversations policies
DROP POLICY IF EXISTS "Allow public conversation access" ON public.conversations;
CREATE POLICY "Allow public conversation access" ON public.conversations FOR ALL USING (true);

DROP POLICY IF EXISTS "Allow public message access" ON public.messages;
CREATE POLICY "Allow public message access" ON public.messages FOR ALL USING (true);

-- 7. CREATE UPDATE TRIGGERS
-- ==============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for all tables
CREATE TRIGGER update_photos_updated_at 
  BEFORE UPDATE ON public.photos 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_cropped_updated_at 
  BEFORE UPDATE ON public.cropped 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_listings_updated_at 
  BEFORE UPDATE ON public.listings 
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 8. VERIFY SETUP
-- ==============================================

-- Check buckets
SELECT 'Buckets created:' as status, id, name, public FROM storage.buckets WHERE id IN ('used_upload', 'cropped');

-- Check tables
SELECT 'Tables created:' as status, table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('photos', 'cropped', 'listings');

-- Check policies
SELECT 'Policies created:' as status, schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public' AND tablename IN ('photos', 'cropped', 'listings');
