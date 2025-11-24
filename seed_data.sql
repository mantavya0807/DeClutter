-- ==============================================
-- SEED DATA FOR DECLUTTERED.AI
-- ==============================================

-- NOTE: Replace 'YOUR_USER_ID_HERE' with your actual Supabase User ID
-- You can find this in the Authentication > Users section of your Supabase dashboard.
-- If you want to use this for the 'anonymous' user, leave as is or change to 'anonymous'.

-- Ensure messages table has created_at column
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

DO $$
DECLARE
  target_user_id text := 'anonymous'; -- CHANGE THIS TO YOUR USER ID
  photo1_id uuid := gen_random_uuid();
  photo2_id uuid := gen_random_uuid();
  photo3_id uuid := gen_random_uuid();
  photo4_id uuid := gen_random_uuid();
  photo5_id uuid := gen_random_uuid();
  
  cropped1_id uuid := gen_random_uuid();
  cropped2_id uuid := gen_random_uuid();
  cropped3_id uuid := gen_random_uuid();
  cropped4_id uuid := gen_random_uuid();
  cropped5_id uuid := gen_random_uuid();
  
  listing1_id uuid := gen_random_uuid();
  listing2_id uuid := gen_random_uuid();
  listing3_id uuid := gen_random_uuid();
  listing4_id uuid := gen_random_uuid();
  listing5_id uuid := gen_random_uuid();
  
  conv1_id uuid := gen_random_uuid();
  conv2_id uuid := gen_random_uuid();
BEGIN

  -- 1. INSERT PHOTOS
  -- ==============================================
  INSERT INTO public.photos (id, filename, url, size, user_id, processed, uploaded_at) VALUES
  (photo1_id, 'vintage_camera.jpg', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=1000&q=80', 2450000, target_user_id, true, NOW() - INTERVAL '5 days'),
  (photo2_id, 'leather_jacket.jpg', 'https://images.unsplash.com/photo-1551028919-380103094e41?auto=format&fit=crop&w=1000&q=80', 3100000, target_user_id, true, NOW() - INTERVAL '3 days'),
  (photo3_id, 'mechanical_keyboard.jpg', 'https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&w=1000&q=80', 1800000, target_user_id, true, NOW() - INTERVAL '2 days'),
  (photo4_id, 'ceramic_vase.jpg', 'https://images.unsplash.com/photo-1612196808214-b7e239e5f6b7?auto=format&fit=crop&w=1000&q=80', 4200000, target_user_id, true, NOW() - INTERVAL '10 days'),
  (photo5_id, 'gaming_monitor.jpg', 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=1000&q=80', 5100000, target_user_id, true, NOW() - INTERVAL '1 day');

  -- 2. INSERT CROPPED OBJECTS
  -- ==============================================
  INSERT INTO public.cropped (id, photo_id, object_name, confidence, bounding_box, cropped_image_url, estimated_value) VALUES
  (cropped1_id, photo1_id, 'Vintage Canon AE-1 Camera', 0.98, '{"x": 100, "y": 100, "width": 800, "height": 600}', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=500&q=80', 150.00),
  (cropped2_id, photo2_id, 'Black Leather Biker Jacket', 0.95, '{"x": 50, "y": 50, "width": 900, "height": 900}', 'https://images.unsplash.com/photo-1551028919-380103094e41?auto=format&fit=crop&w=500&q=80', 85.00),
  (cropped3_id, photo3_id, 'Custom Mechanical Keyboard', 0.99, '{"x": 20, "y": 150, "width": 960, "height": 400}', 'https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&w=500&q=80', 120.00),
  (cropped4_id, photo4_id, 'Handmade Ceramic Vase', 0.92, '{"x": 300, "y": 200, "width": 400, "height": 600}', 'https://images.unsplash.com/photo-1612196808214-b7e239e5f6b7?auto=format&fit=crop&w=500&q=80', 45.00),
  (cropped5_id, photo5_id, '27-inch 144Hz Gaming Monitor', 0.97, '{"x": 50, "y": 50, "width": 900, "height": 700}', 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=500&q=80', 200.00);

  -- 3. INSERT LISTINGS
  -- ==============================================
  INSERT INTO public.listings (id, photo_id, cropped_id, title, description, price, platforms, status, user_id, posted_at, created_at) VALUES
  -- Active Listing on Facebook
  (listing1_id, photo1_id, cropped1_id, 'Vintage Canon AE-1 Program Camera - Excellent Condition', 'Classic 35mm film camera. Tested and working perfectly. Comes with 50mm f/1.8 lens. No scratches or fungus.', 150.00, ARRAY['facebook'], 'posted', target_user_id, NOW() - INTERVAL '4 days', NOW() - INTERVAL '5 days'),
  
  -- Sold Listing on eBay
  (listing2_id, photo2_id, cropped2_id, 'Genuine Leather Biker Jacket - Size M', 'Real leather jacket, barely worn. Zippers work great. Very warm and stylish.', 85.00, ARRAY['ebay'], 'sold', target_user_id, NOW() - INTERVAL '3 days', NOW() - INTERVAL '3 days'),
  
  -- Active Listing on both
  (listing3_id, photo3_id, cropped3_id, 'Custom Mechanical Keyboard - Gateron Brown Switches', '60% layout mechanical keyboard. RGB backlighting. PBT keycaps. Great for typing and gaming.', 120.00, ARRAY['facebook', 'ebay'], 'posted', target_user_id, NOW() - INTERVAL '1 day', NOW() - INTERVAL '2 days'),
  
  -- Sold Listing on Facebook
  (listing4_id, photo4_id, cropped4_id, 'Modern Minimalist Ceramic Vase', 'Beautiful handmade vase. Perfect for dried flowers or as a standalone piece. 10 inches tall.', 45.00, ARRAY['facebook'], 'sold', target_user_id, NOW() - INTERVAL '9 days', NOW() - INTERVAL '10 days'),
  
  -- Draft Listing
  (listing5_id, photo5_id, cropped5_id, 'Gaming Monitor 144Hz 1ms Response', 'High refresh rate monitor. No dead pixels. Comes with power and HDMI cables.', 200.00, ARRAY['facebook'], 'draft', target_user_id, NULL, NOW() - INTERVAL '1 day');

  -- 4. INSERT CONVERSATIONS & MESSAGES
  -- ==============================================
  
  -- Conversation 1: Active negotiation for the Camera
  INSERT INTO public.conversations (id, platform_thread_id, buyer_name, item_title, item_id, last_message_at, is_unread, status) VALUES
  (conv1_id, 'fb_thread_12345', 'Alex Johnson', 'Vintage Canon AE-1 Program Camera', listing1_id::text, NOW() - INTERVAL '2 hours', true, 'active');
  
  INSERT INTO public.messages (conversation_id, sender, content, platform_timestamp, created_at) VALUES
  (conv1_id, 'buyer', 'Hi, is this still available?', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '5 hours'),
  (conv1_id, 'me', 'Yes it is! Are you interested?', NOW() - INTERVAL '4 hours', NOW() - INTERVAL '4 hours'),
  (conv1_id, 'buyer', 'Would you take $130 for it? I can pick it up today.', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours');

  -- Conversation 2: Inquiry about the Keyboard
  INSERT INTO public.conversations (id, platform_thread_id, buyer_name, item_title, item_id, last_message_at, is_unread, status) VALUES
  (conv2_id, 'ebay_msg_67890', 'TechGuru99', 'Custom Mechanical Keyboard', listing3_id::text, NOW() - INTERVAL '1 day', false, 'active');
  
  INSERT INTO public.messages (conversation_id, sender, content, platform_timestamp, created_at) VALUES
  (conv2_id, 'buyer', 'Does this come with the original box?', NOW() - INTERVAL '1 day', NOW() - INTERVAL '1 day'),
  (conv2_id, 'me', 'No, unfortunately I threw away the box. But I will package it very securely.', NOW() - INTERVAL '23 hours', NOW() - INTERVAL '23 hours');

END $$;
