'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Check,
  X,
  Edit3,
  Trash2,
  DollarSign,
  Tag,
  Upload,
  Globe,
  CheckCircle,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import { createClient } from '@/utils/supabase/client';

interface QueuedItem {
  id: string;
  name: string;
  price: number;
  description: string;
  tags: string[];
  status: 'ready' | 'posting' | 'posted' | 'error';
  platforms: string[];
  croppedImageUrl: string;
  timestamp: number;
  frameImage: string;
  pricingData?: any;
  originalObject?: any;
}

interface PostQueueProps {
  userId: string;
  items: QueuedItem[];
  onBack: () => void;
  onPostComplete: () => void;
}

const PostQueue = ({ userId, items, onBack, onPostComplete }: PostQueueProps) => {
  const [postingItems, setPostingItems] = useState<Set<string>>(new Set());
  const [postedItems, setPostedItems] = useState<Set<string>>(new Set());
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  const handlePostItem = async (itemId: string) => {
    const itemToPost = items.find(i => i.id === itemId);
    if (!itemToPost) return;

    console.log('Posting item:', itemToPost);
    console.log('Price being sent:', itemToPost.price);

    setPostingItems(prev => new Set([...prev, itemId]));

    try {
      const response = await fetch('http://localhost:5000/api/pipeline/create-listings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          items: [{
            object_name: itemToPost.name,
            pricing_data: itemToPost.pricingData,
            price: itemToPost.price,
            image_url: itemToPost.croppedImageUrl,
            cropped_path: itemToPost.croppedImageUrl,
            cropped_id: itemToPost.originalObject?.id || itemToPost.id
          }],
          platforms: itemToPost.platforms
        }),
      });

      const result = await response.json();

      if (result.ok) {
        setPostedItems(prev => new Set([...prev, itemId]));
      } else {
        console.error('Failed to post item:', result.message);
        // Handle error state if needed
      }
    } catch (error) {
      console.error('Error posting item:', error);
    } finally {
      setPostingItems(prev => {
        const newSet = new Set(prev);
        newSet.delete(itemId);
        return newSet;
      });
    }
  };

  const handlePostAll = async () => {
    const readyItems = items.filter(item => item.status === 'ready');
    setPostingItems(new Set(readyItems.map(item => item.id)));

    try {
      // Post items sequentially or in parallel depending on backend capability
      // Here we send them all in one batch if the API supports it, 
      // but the current API implementation iterates through them.

      const response = await fetch('http://localhost:5000/api/pipeline/create-listings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: userId,
          items: readyItems.map(item => ({
            object_name: item.name,
            pricing_data: item.pricingData,
            price: item.price,
            image_url: item.croppedImageUrl,
            cropped_path: item.croppedImageUrl,
            cropped_id: item.originalObject?.id || item.id
          })),
          platforms: readyItems[0]?.platforms || ['facebook', 'ebay'] // Assuming same platforms for batch
        }),
      });

      const result = await response.json();

      if (result.ok) {
        setPostedItems(new Set(readyItems.map(item => item.id)));
        setShowSuccessModal(true);
      } else {
        console.error('Failed to post items:', result.message);
      }
    } catch (error) {
      console.error('Error posting items:', error);
    } finally {
      setPostingItems(new Set());
    }
  };

  const handleRemoveItem = (itemId: string) => {
    // Remove item from queue
  };

  const totalValue = items.reduce((sum, item) => sum + item.price, 0);
  const postedCount = postedItems.size;
  const postingCount = postingItems.size;

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onBack}
          className="flex items-center gap-2 text-[#5BAAA7] hover:text-[#4a9b98] transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back
        </motion.button>

        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Ready to Post</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Review and post your listings</p>
        </div>

        <div className="w-20" /> {/* Spacer */}
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto">
        {/* Summary Stats */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 mb-6 sm:mb-8"
        >
          <div className="bg-white dark:bg-[#112233] rounded-2xl p-4 sm:p-6 border border-gray-100 dark:border-[#1e3a52] shadow-sm">
            <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-[#5BAAA7]/10 rounded-xl flex items-center justify-center">
                <Tag className="w-4 h-4 sm:w-5 sm:h-5 text-[#5BAAA7]" />
              </div>
              <h3 className="text-sm sm:text-lg font-semibold text-gray-900 dark:text-white">Total Items</h3>
            </div>
            <div className="text-2xl sm:text-3xl font-bold text-[#5BAAA7]">{items.length}</div>
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Ready to post</div>
          </div>

          <div className="bg-white dark:bg-[#112233] rounded-2xl p-4 sm:p-6 border border-gray-100 dark:border-[#1e3a52] shadow-sm">
            <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-[#5BAAA7]/10 rounded-xl flex items-center justify-center">
                <DollarSign className="w-4 h-4 sm:w-5 sm:h-5 text-[#5BAAA7]" />
              </div>
              <h3 className="text-sm sm:text-lg font-semibold text-gray-900 dark:text-white">Total Value</h3>
            </div>
            <div className="text-2xl sm:text-3xl font-bold text-[#5BAAA7]">${totalValue}</div>
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Potential earnings</div>
          </div>

          <div className="bg-white dark:bg-[#112233] rounded-2xl p-4 sm:p-6 border border-gray-100 dark:border-[#1e3a52] shadow-sm">
            <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-green-500/10 rounded-xl flex items-center justify-center">
                <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5 text-green-500" />
              </div>
              <h3 className="text-sm sm:text-lg font-semibold text-gray-900 dark:text-white">Posted</h3>
            </div>
            <div className="text-2xl sm:text-3xl font-bold text-green-500">{postedCount}</div>
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">Successfully posted</div>
          </div>

          <div className="bg-white dark:bg-[#112233] rounded-2xl p-4 sm:p-6 border border-gray-100 dark:border-[#1e3a52] shadow-sm">
            <div className="flex items-center gap-2 sm:gap-3 mb-2 sm:mb-3">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-yellow-500/10 rounded-xl flex items-center justify-center">
                <AlertCircle className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-500" />
              </div>
              <h3 className="text-sm sm:text-lg font-semibold text-gray-900 dark:text-white">Posting</h3>
            </div>
            <div className="text-2xl sm:text-3xl font-bold text-yellow-500">{postingCount}</div>
            <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">In progress</div>
          </div>
        </motion.div>

        {/* Post All Button */}
        {items.filter(item => item.status === 'ready').length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handlePostAll}
              className="w-full px-8 py-4 bg-[#5BAAA7] hover:bg-[#4a9b98] text-white font-semibold rounded-xl shadow-lg transition-all flex items-center justify-center gap-3"
            >
              <Upload className="w-6 h-6" />
              Post All {items.filter(item => item.status === 'ready').length} Items
            </motion.button>
          </motion.div>
        )}

        {/* Items Queue */}
        <div className="space-y-4">
          {items.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
              className="bg-white dark:bg-[#112233] rounded-2xl p-6 border border-gray-100 dark:border-[#1e3a52] shadow-sm hover:shadow-md transition-all duration-300"
            >
              <div className="flex items-center gap-6">
                {/* Item Image */}
                <div className="relative w-20 h-20 bg-gray-50 dark:bg-[#0a1b2a] rounded-xl overflow-hidden flex-shrink-0">
                  <img
                    src={item.croppedImageUrl}
                    alt={item.name}
                    className="w-full h-full object-cover"
                  />
                </div>

                {/* Item Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="text-lg font-bold text-gray-900 dark:text-white truncate">
                      {item.name}
                    </h3>
                    <div className="text-2xl font-bold text-[#5BAAA7]">
                      ${item.price}
                    </div>
                  </div>

                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 line-clamp-2">
                    {item.description}
                  </p>

                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {item.platforms.join(', ')}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {item.tags.slice(0, 2).map((tag, tagIndex) => (
                        <span key={tagIndex} className="px-2 py-1 bg-gray-100 dark:bg-[#1e3a52] text-gray-600 dark:text-gray-300 rounded-full text-xs">
                          {tag}
                        </span>
                      ))}
                      {item.tags.length > 2 && (
                        <span className="px-2 py-1 bg-gray-100 dark:bg-[#1e3a52] text-gray-600 dark:text-gray-300 rounded-full text-xs">
                          +{item.tags.length - 2}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Status & Actions */}
                <div className="flex items-center gap-3">
                  {postingItems.has(item.id) ? (
                    <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-500">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        className="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full"
                      />
                      <span className="text-sm font-medium">Posting...</span>
                    </div>
                  ) : postedItems.has(item.id) ? (
                    <div className="flex items-center gap-2 text-green-600 dark:text-green-500">
                      <CheckCircle className="w-5 h-5" />
                      <span className="text-sm font-medium">Posted</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => handlePostItem(item.id)}
                        className="px-4 py-2 bg-[#5BAAA7] text-white font-semibold rounded-lg hover:bg-[#4a9b98] transition-all flex items-center gap-2"
                      >
                        <Upload className="w-4 h-4" />
                        Post Now
                      </motion.button>

                      <button
                        onClick={() => handleRemoveItem(item.id)}
                        className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Success Modal */}
      <AnimatePresence>
        {showSuccessModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => {
              setShowSuccessModal(false);
              onPostComplete();
            }}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white dark:bg-[#112233] rounded-2xl p-8 max-w-md w-full text-center border border-gray-100 dark:border-[#1e3a52]"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Confetti Animation */}
              <div className="relative mb-6">
                <motion.div
                  animate={{
                    scale: [1, 1.2, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ duration: 0.6 }}
                  className="w-20 h-20 bg-[#5BAAA7] rounded-full flex items-center justify-center mx-auto mb-4"
                >
                  <Sparkles className="w-10 h-10 text-white" />
                </motion.div>

                {/* Confetti particles */}
                {[...Array(6)].map((_, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{
                      opacity: [0, 1, 0],
                      scale: [0, 1, 0],
                      x: [0, (Math.random() - 0.5) * 200],
                      y: [0, (Math.random() - 0.5) * 200]
                    }}
                    transition={{
                      duration: 1.5,
                      delay: i * 0.1,
                      ease: "easeOut"
                    }}
                    className="absolute w-2 h-2 bg-[#5BAAA7] rounded-full"
                    style={{
                      left: '50%',
                      top: '50%',
                    }}
                  />
                ))}
              </div>

              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Successfully Posted!
              </h2>

              <div className="space-y-4 mb-6">
                <div className="text-3xl font-bold text-[#5BAAA7]">
                  Posted {postedCount} items
                </div>
                <div className="text-lg text-gray-500 dark:text-gray-400">
                  Estimated Earnings: <span className="font-bold text-[#5BAAA7]">${totalValue}</span>
                </div>
              </div>

              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setShowSuccessModal(false);
                  onPostComplete();
                }}
                className="w-full px-6 py-3 bg-[#5BAAA7] hover:bg-[#4a9b98] text-white font-semibold rounded-xl shadow-lg transition-all"
              >
                View Active Listings
              </motion.button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PostQueue;
