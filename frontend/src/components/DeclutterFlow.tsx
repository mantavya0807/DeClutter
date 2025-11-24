import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSearchParams } from 'next/navigation';
import { Check } from 'lucide-react';
import ObjectSelection from './ObjectSelection';
import ItemSelection from './ItemSelection';
import PreparedPosts from './PreparedPosts';
import PostQueue from './PostQueue';

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
  category?: string;
  condition?: string;
  description?: string;
  tags?: string[];
  timestamp?: number;
  frameImage?: string;
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
  originalObject?: DetectedObject;
}

type FlowStep = 'camera' | 'selection' | 'item-selection' | 'prepared-posts' | 'queue' | 'complete';

interface DeclutterFlowProps {
  userId: string;
  onComplete: () => void;
  onBack: () => void;
}

const DeclutterFlow = ({ userId, onComplete, onBack }: DeclutterFlowProps) => {
  const searchParams = useSearchParams();
  const jobId = searchParams?.get('jobId');

  const [currentStep, setCurrentStep] = useState<FlowStep>(jobId ? 'item-selection' : 'selection');
  const [detectedObjects, setDetectedObjects] = useState<DetectedObject[]>([]);
  const [selectedItems, setSelectedItems] = useState<DetectedObject[]>([]);
  const [preparedPosts, setPreparedPosts] = useState<any[]>([]);
  const [queuedItems, setQueuedItems] = useState<QueuedItem[]>([]);
  const [loading, setLoading] = useState(!!jobId);

  // Fetch objects from job when jobId is present
  useEffect(() => {
    if (!jobId) return;

    const fetchJobResults = async () => {
      try {
        const response = await fetch(`http://localhost:5000/api/pipeline/status/${jobId}`);
        const data = await response.json();

        console.log('DeclutterFlow: Fetched job data:', data);

        if (data.results && data.results.detected_objects) {
          const mappedObjects: DetectedObject[] = data.results.detected_objects.map((obj: any, index: number) => ({
            id: obj.cropped_id || `obj-${index}`,
            name: obj.recognition_result?.product_name || obj.label || obj.object_name || 'Unknown Item',
            confidence: obj.confidence || 0.5,
            boundingBox: obj.bounding_box || { x: 0, y: 0, width: 100, height: 100 },
            croppedImageUrl: `http://localhost:5000/cropped_resellables/${obj.image_filename}`,
            estimatedValue: obj.recognition_result?.pricing?.typical_price_range?.min || obj.pricing_data?.summary?.avg || 0,
            googleData: obj.recognition_result,
            pricingData: obj.pricing_data,
            jobId: jobId
          }));

          console.log('DeclutterFlow: Mapped objects:', mappedObjects);
          setDetectedObjects(mappedObjects);
          setLoading(false);
        }
      } catch (error) {
        console.error('DeclutterFlow: Error fetching job results:', error);
        setLoading(false);
      }
    };

    fetchJobResults();
  }, [jobId]);

  const handleScanComplete = (objects: DetectedObject[]) => {
    console.log('DeclutterFlow: Received objects:', objects);
    setDetectedObjects(objects);
    setCurrentStep('item-selection');
  };

  const handleItemSelection = (items: DetectedObject[]) => {
    setSelectedItems(items);
    setCurrentStep('prepared-posts');
  };

  const handlePreparedPosts = (posts: any[]) => {
    setPreparedPosts(posts);

    // Convert prepared posts to queued items
    const items: QueuedItem[] = posts.map(post => ({
      id: post.id,
      name: post.item.name,
      price: post.price,
      description: post.description,
      tags: post.tags,
      status: 'ready' as const,
      platforms: [post.platform],
      croppedImageUrl: post.item.croppedImageUrl,
      timestamp: Date.now(),
      frameImage: post.item.croppedImageUrl,
      pricingData: post.item.pricingData,
      originalObject: post.item
    }));

    setQueuedItems(items);
    setCurrentStep('queue');
  };

  const handlePostComplete = () => {
    setCurrentStep('complete');
    // After a brief delay, complete the flow
    setTimeout(() => {
      onComplete();
    }, 2000);
  };

  const handleBack = () => {
    switch (currentStep) {
      case 'selection':
        onBack(); // Go back to dashboard since we're skipping camera
        break;
      case 'item-selection':
        setCurrentStep('selection');
        break;
      case 'prepared-posts':
        setCurrentStep('item-selection');
        break;
      case 'queue':
        setCurrentStep('prepared-posts');
        break;
      default:
        onBack();
    }
  };

  const steps = [
    { id: 'selection', label: 'Scan' },
    { id: 'item-selection', label: 'Select' },
    { id: 'prepared-posts', label: 'Details' },
    { id: 'queue', label: 'Post' }
  ];

  const currentStepIndex = steps.findIndex(s => s.id === (currentStep === 'complete' ? 'queue' : currentStep));

  return (
    <div className="relative w-full min-h-[calc(100vh-8rem)] flex flex-col bg-gray-50 dark:bg-[#050e16]">
      {/* Stepper */}
      <div className="w-full max-w-3xl mx-auto pt-6 pb-2 px-4">
        <div className="relative flex items-center justify-between">
          {/* Progress Bar Background */}
          <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-gray-200 dark:bg-gray-800 rounded-full -z-0" />

          {/* Active Progress Bar */}
          <motion.div
            className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-[#5BAAA7] rounded-full -z-0"
            initial={{ width: '0%' }}
            animate={{ width: `${(currentStepIndex / (steps.length - 1)) * 100}%` }}
            transition={{ duration: 0.3 }}
          />

          {steps.map((step, index) => {
            const isActive = index <= currentStepIndex;
            const isCurrent = index === currentStepIndex;

            return (
              <div key={step.id} className="relative z-10 flex flex-col items-center gap-2">
                <motion.div
                  initial={false}
                  animate={{
                    backgroundColor: isActive ? '#5BAAA7' : 'var(--bg-inactive)',
                    borderColor: isActive ? '#5BAAA7' : 'var(--border-inactive)',
                    scale: isCurrent ? 1.1 : 1
                  }}
                  style={{
                    '--bg-inactive': 'var(--color-gray-200)', // Fallback
                    '--border-inactive': 'var(--color-gray-300)'
                  } as any}
                  className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors duration-300 ${isActive
                    ? 'bg-[#5BAAA7] border-[#5BAAA7] text-white'
                    : 'bg-white dark:bg-[#112233] border-gray-300 dark:border-gray-600 text-gray-400'
                    }`}
                >
                  {isActive ? (
                    <motion.svg
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="w-4 h-4"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </motion.svg>
                  ) : (
                    <span className="text-xs font-bold">{index + 1}</span>
                  )}
                </motion.div>
                <span className={`text-xs font-medium transition-colors duration-300 ${isActive ? 'text-[#5BAAA7]' : 'text-gray-400'
                  }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden">
        <AnimatePresence mode="wait">
          {currentStep === 'selection' && (
            <motion.div
              key="selection"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 overflow-y-auto"
            >
              <ObjectSelection
                photoId="mock-photo-id"
                originalPhotoUrl="/vercel.svg"
                onObjectsSelected={handleScanComplete}
                onBack={handleBack}
              />
            </motion.div>
          )}

          {currentStep === 'item-selection' && (
            <motion.div
              key="item-selection"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 overflow-y-auto"
            >
              {loading ? (
                <div className="h-full flex flex-col items-center justify-center">
                  <div className="w-16 h-16 border-4 border-[#5BAAA7] border-t-transparent rounded-full animate-spin mb-4" />
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">Analyzing items...</h2>
                  <p className="text-gray-500 dark:text-gray-400">Identifying products and prices</p>
                </div>
              ) : (
                <ItemSelection
                  detectedObjects={detectedObjects}
                  onBack={handleBack}
                  onItemsSelected={handleItemSelection}
                />
              )}
            </motion.div>
          )}

          {currentStep === 'prepared-posts' && (
            <motion.div
              key="prepared-posts"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 overflow-y-auto"
            >
              <PreparedPosts
                selectedItems={selectedItems}
                onBack={handleBack}
                onContinue={handlePreparedPosts}
              />
            </motion.div>
          )}

          {currentStep === 'queue' && (
            <motion.div
              key="queue"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="absolute inset-0 overflow-y-auto"
            >
              <PostQueue
                userId={userId}
                items={queuedItems}
                onBack={handleBack}
                onPostComplete={handlePostComplete}
              />
            </motion.div>
          )}

          {currentStep === 'complete' && (
            <motion.div
              key="complete"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.5 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="text-center p-8 bg-white dark:bg-[#112233] rounded-3xl shadow-xl border border-gray-100 dark:border-[#1e3a52] max-w-md mx-4">
                <motion.div
                  animate={{
                    scale: [1, 1.1, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="w-20 h-20 bg-gradient-to-br from-[#5BAAA7] to-[#4a8f8c] rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-[#5BAAA7]/30"
                >
                  <Check className="w-10 h-10 text-white" />
                </motion.div>

                <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                  All Done!
                </h2>
                <p className="text-gray-500 dark:text-gray-400">
                  Your listings have been queued successfully. Redirecting to dashboard...
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default DeclutterFlow;
