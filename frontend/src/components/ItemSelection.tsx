'use client';

import { motion, AnimatePresence } from 'framer-motion';
import React, { useState } from 'react';
import {
  ArrowLeft,
  Check,
  X,
  DollarSign,
  Star,
  ShoppingBag,
  ArrowRight,
  Edit3,
  Eye,
  Tag
} from 'lucide-react';

interface DetectedObject {
  id: string;
  name: string;
  confidence: number;
  boundingBox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  croppedImageUrl: string;
  estimatedValue: number;
  pricingData?: any;
  jobId?: string;
  googleData?: {
    rating?: {
      rating: number;
      rating_out_of: number;
      review_count: number;
      review_count_text: string;
    } | null;
    pricing?: {
      current_prices: Array<{
        price: number;
        currency: string;
        source: string;
      }>;
      typical_price_range?: {
        min: number;
        max: number;
        currency: string;
        text: string;
      };
    } | null;
    source_url?: string | null;
    host?: string | null;
  };
}

interface ItemSelectionProps {
  detectedObjects: DetectedObject[];
  onBack: () => void;
  onItemsSelected: (selectedItems: DetectedObject[]) => void;
}

// Pipeline API configuration
const PIPELINE_API_BASE = (process.env.NEXT_PUBLIC_PIPELINE_API_URL as string) || 'http://localhost:5000';

const ItemSelection = ({ detectedObjects, onBack, onItemsSelected }: ItemSelectionProps) => {
  const [items, setItems] = useState<DetectedObject[]>(detectedObjects);
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showDetailModal, setShowDetailModal] = useState<string | null>(null);

  // Poll for updates if we have a jobId
  React.useEffect(() => {
    const jobId = items[0]?.jobId;
    if (!jobId) return;

    console.log('ItemSelection: Setting up polling for job', jobId);

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${PIPELINE_API_BASE}/api/pipeline/status/${jobId}`);
        if (!response.ok) return;

        const data = await response.json();

        // Update items if we have results
        if (data.results || (data.status === 'completed' && data.results)) {
          const resultData = data.results || {};
          const resultItems = resultData.listings_ready_to_review || [];

          setItems(prevItems => {
            const newItems = prevItems.map(item => {
              // Find corresponding item in results
              const updatedItem = resultItems.find((r: any) => {
                // Try exact ID match first
                if (r.cropped_id && r.cropped_id === item.id) return true;
                // Try exact name match
                if (r.object_name === item.name) return true;
                if (r.recognition_result?.product_name === item.name) return true;
                // Try loose name match
                const itemName = item.name?.toLowerCase().trim();
                if (r.object_name?.toLowerCase().trim() === itemName) return true;
                if (r.recognition_result?.product_name?.toLowerCase().trim() === itemName) return true;
                return false;
              });

              if (updatedItem && updatedItem.pricing_data) {
                let newValue = item.estimatedValue;
                const pricing = updatedItem.pricing_data;

                // Check for summary average first (new structure)
                if (pricing.summary?.avg) {
                  newValue = pricing.summary.avg;
                } else if (pricing.summary?.median) {
                  newValue = pricing.summary.median;
                }
                // Check for comps average (fallback)
                else if (pricing.comps && pricing.comps.length > 0) {
                  const prices = pricing.comps.map((c: any) => c.price).filter((p: any) => p);
                  if (prices.length > 0) {
                    newValue = prices.reduce((a: number, b: number) => a + b, 0) / prices.length;
                  }
                }
                // Legacy structure checks
                else if (pricing.facebook_prices?.length > 0) {
                  newValue = pricing.facebook_prices.reduce((a: number, b: number) => a + b, 0) / pricing.facebook_prices.length;
                } else if (pricing.ebay_prices?.length > 0) {
                  newValue = pricing.ebay_prices.reduce((a: number, b: number) => a + b, 0) / pricing.ebay_prices.length;
                }

                // Only update if we have a valid new value and it's different
                if (newValue > 0 && Math.round(newValue) !== item.estimatedValue) {
                  console.log(`ItemSelection: Updating price for ${item.name} from ${item.estimatedValue} to ${Math.round(newValue)}`);
                  return {
                    ...item,
                    estimatedValue: Math.round(newValue),
                    pricingData: updatedItem.pricing_data
                  };
                }
              }
              return item;
            });

            // Check if anything actually changed to avoid re-renders
            if (JSON.stringify(newItems) !== JSON.stringify(prevItems)) {
              return newItems;
            }
            return prevItems;
          });
        }

        if (data.status === 'completed' || data.status === 'error') {
          console.log('ItemSelection: Job finished, stopping polling');
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000);

    return () => {
      console.log('ItemSelection: Cleaning up polling');
      clearInterval(interval);
    };
  }, [items[0]?.jobId]); // Only re-run if the job ID changes

  const toggleItemSelection = (itemId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const handleContinue = () => {
    const selected = items.filter(item => selectedItems.has(item.id));
    onItemsSelected(selected);
  };

  const totalValue = Array.from(selectedItems).reduce((sum, itemId) => {
    const item = items.find(obj => obj.id === itemId);
    return sum + (item?.estimatedValue || 0);
  }, 0);

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onBack}
          className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </motion.button>

        <div className="text-center">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">Select Items to Sell</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-base mt-1">
            {selectedItems.size} of {items.length} items selected
          </p>
        </div>

        <div className="w-10" /> {/* Spacer */}
      </div>

      {/* Instructions */}
      <div className="mb-8">
        <div className="bg-white dark:bg-[#112233] rounded-2xl p-6 border border-gray-100 dark:border-[#1e3a52] shadow-sm">
          <div className="text-center">
            <h2 className="text-gray-900 dark:text-white text-xl font-semibold mb-2">Choose Items to Sell</h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Items have been identified with Google data! Select which ones to sell while we analyze marketplace prices.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-4 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-1">
                <Check className="w-4 h-4 text-green-500" />
                <span>Google Identified</span>
              </div>
              <div className="flex items-center gap-1">
                <Star className="w-4 h-4 text-yellow-500" />
                <span>Ratings Available</span>
              </div>
              <div className="flex items-center gap-1">
                <DollarSign className="w-4 h-4 text-green-500" />
                <span>Price Estimated</span>
              </div>
              <div className="flex items-center gap-1">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="w-4 h-4 border-2 border-[#5BAAA7] border-t-transparent rounded-full"
                />
                <span>Analyzing Markets</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Items Grid */}
      <div className="mb-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <AnimatePresence>
            {items.map((item, index) => {
              const isSelected = selectedItems.has(item.id);
              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.1 }}
                  className={`relative bg-white dark:bg-[#112233] rounded-2xl p-6 border-2 transition-all duration-300 cursor-pointer shadow-sm ${isSelected
                      ? 'border-[#5BAAA7] ring-1 ring-[#5BAAA7] shadow-md'
                      : 'border-gray-100 dark:border-[#1e3a52] hover:border-[#5BAAA7]/50 dark:hover:border-[#5BAAA7]/50'
                    }`}
                  onClick={() => toggleItemSelection(item.id)}
                >
                  {/* Selection Indicator */}
                  <div className={`absolute top-4 right-4 w-8 h-8 rounded-full border-2 flex items-center justify-center transition-all ${isSelected
                      ? 'bg-[#5BAAA7] border-[#5BAAA7] shadow-lg'
                      : 'border-gray-200 dark:border-gray-600'
                    }`}>
                    {isSelected && <Check className="w-5 h-5 text-white" />}
                  </div>

                  {/* Item Image */}
                  <div className="aspect-square bg-gray-50 dark:bg-[#0a1b2a] rounded-xl mb-4 flex items-center justify-center overflow-hidden">
                    <img
                      src={item.croppedImageUrl}
                      alt={item.name}
                      className="w-full h-full object-cover rounded-xl"
                    />
                  </div>

                  {/* Item Info */}
                  <div className="space-y-3">
                    <h3 className="text-gray-900 dark:text-white font-semibold text-lg truncate">
                      {item.name}
                    </h3>

                    {/* Google Rating */}
                    {item.googleData?.rating && (
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 text-yellow-500 fill-current" />
                          <span className="text-gray-600 dark:text-gray-300 text-sm">
                            {item.googleData.rating.rating.toFixed(1)}/{item.googleData.rating.rating_out_of}
                          </span>
                          {item.googleData.rating.review_count && (
                            <span className="text-gray-400 dark:text-gray-500 text-xs">
                              ({item.googleData.rating.review_count_text || `${item.googleData.rating.review_count} reviews`})
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Detection Confidence */}
                    {!item.googleData?.rating && (
                      <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1">
                          <Star className="w-4 h-4 text-yellow-500 fill-current" />
                          <span className="text-gray-600 dark:text-gray-300 text-sm">
                            {(item.confidence * 100).toFixed(0)}% confidence
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Price Information */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-5 h-5 text-green-500" />
                        <div className="flex flex-col">
                          <span className="text-green-500 font-bold text-xl">
                            ${item.estimatedValue}
                          </span>
                          {/* Google Typical Price Range */}
                          {item.googleData?.pricing?.typical_price_range && (
                            <span className="text-gray-400 dark:text-gray-500 text-xs">
                              Typically ${item.googleData.pricing.typical_price_range.min}-${item.googleData.pricing.typical_price_range.max}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Source Info */}
                    {item.googleData?.host && (
                      <div className="text-gray-400 dark:text-gray-500 text-xs truncate">
                        Found on {item.googleData.host}
                      </div>
                    )}

                    {/* Action Buttons */}
                    <div className="flex gap-2 pt-2">
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setShowDetailModal(item.id);
                        }}
                        className="flex-1 px-3 py-2 bg-gray-100 dark:bg-[#1e3a52] text-gray-700 dark:text-gray-200 text-sm rounded-lg hover:bg-gray-200 dark:hover:bg-[#2a4b66] transition-all flex items-center justify-center gap-1"
                      >
                        <Eye className="w-4 h-4" />
                        Preview
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          // Edit functionality
                        }}
                        className="flex-1 px-3 py-2 bg-gray-100 dark:bg-[#1e3a52] text-gray-700 dark:text-gray-200 text-sm rounded-lg hover:bg-gray-200 dark:hover:bg-[#2a4b66] transition-all flex items-center justify-center gap-1"
                      >
                        <Edit3 className="w-4 h-4" />
                        Edit
                      </motion.button>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>

      {/* Selection Summary */}
      {selectedItems.size > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed bottom-6 left-1/2 transform -translate-x-1/2 w-full max-w-xl px-4 z-30"
        >
          <div className="bg-[#112233] text-white rounded-2xl p-4 shadow-xl border border-[#1e3a52] flex items-center justify-between">
            <div>
              <h3 className="text-white text-lg font-semibold mb-1">
                {selectedItems.size} items selected
              </h3>
              <p className="text-gray-400 text-sm">
                Estimated total value: <span className="text-green-400 font-semibold">${totalValue}</span>
              </p>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleContinue}
              className="px-6 py-3 bg-[#5BAAA7] hover:bg-[#4a9b98] text-white font-semibold rounded-xl shadow-lg transition-all flex items-center gap-2"
            >
              <ShoppingBag className="w-5 h-5" />
              Prepare Listings
              <ArrowRight className="w-4 h-4" />
            </motion.button>
          </div>
        </motion.div>
      )}

      {/* Empty State */}
      {selectedItems.size === 0 && (
        <div className="text-center py-12">
          <div className="w-20 h-20 bg-gray-100 dark:bg-[#1e3a52] rounded-full flex items-center justify-center mx-auto mb-4">
            <ShoppingBag className="w-10 h-10 text-gray-400 dark:text-gray-500" />
          </div>
          <h3 className="text-gray-900 dark:text-white text-lg font-semibold mb-2">No items selected</h3>
          <p className="text-gray-500 dark:text-gray-400 text-sm">
            Select items above to create your listings
          </p>
        </div>
      )}

      {/* Detail Modal */}
      <AnimatePresence>
        {showDetailModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={() => setShowDetailModal(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white dark:bg-[#112233] rounded-2xl p-6 max-w-md w-full border border-gray-100 dark:border-[#1e3a52] shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-gray-900 dark:text-white text-lg font-semibold">Item Preview</h3>
                <button
                  onClick={() => setShowDetailModal(null)}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-[#1e3a52] rounded-lg transition-all"
                >
                  <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div className="aspect-square bg-gray-50 dark:bg-[#0a1b2a] rounded-xl overflow-hidden">
                  <img
                    src={items.find(item => item.id === showDetailModal)?.croppedImageUrl}
                    alt="Item preview"
                    className="w-full h-full object-cover"
                  />
                </div>

                <div className="text-center space-y-3">
                  <h4 className="text-gray-900 dark:text-white font-semibold text-lg mb-2">
                    {items.find(item => item.id === showDetailModal)?.name}
                  </h4>

                  {/* Price */}
                  <p className="text-green-500 font-bold text-xl">
                    ${items.find(item => item.id === showDetailModal)?.estimatedValue}
                  </p>

                  {/* Google Data */}
                  {(() => {
                    const item = items.find(item => item.id === showDetailModal);
                    const googleData = item?.googleData;

                    return (
                      <div className="space-y-2 text-sm">
                        {/* Rating */}
                        {googleData?.rating && (
                          <div className="flex items-center justify-center gap-1">
                            <Star className="w-4 h-4 text-yellow-400 fill-current" />
                            <span className="text-gray-700 dark:text-gray-200">
                              {googleData.rating.rating.toFixed(1)}/{googleData.rating.rating_out_of}
                            </span>
                            {googleData.rating.review_count && (
                              <span className="text-gray-500 dark:text-gray-400">
                                ({googleData.rating.review_count_text || `${googleData.rating.review_count} reviews`})
                              </span>
                            )}
                          </div>
                        )}

                        {/* Typical Price Range */}
                        {googleData?.pricing?.typical_price_range && (
                          <div className="text-gray-500 dark:text-gray-400">
                            Typically ${googleData.pricing.typical_price_range.min}-${googleData.pricing.typical_price_range.max}
                          </div>
                        )}

                        {/* Source */}
                        {googleData?.host && (
                          <div className="text-gray-400 dark:text-gray-500 text-xs">
                            Found on {googleData.host}
                          </div>
                        )}

                        {/* View Source Link */}
                        {googleData?.source_url && (
                          <div className="mt-3">
                            <a
                              href={googleData.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 dark:bg-[#1e3a52] text-gray-700 dark:text-gray-200 text-xs rounded-lg hover:bg-gray-200 dark:hover:bg-[#2a4b66] transition-all"
                            >
                              View Source
                            </a>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ItemSelection;
