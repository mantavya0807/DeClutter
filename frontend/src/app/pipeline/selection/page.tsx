'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ItemSelection from '@/components/ItemSelection';

interface DetectedObject {
    id: string;
    name: string;
    confidence: number;
    boundingBox: any;
    croppedImageUrl: string;
    estimatedValue: number;
    googleData?: any;
    pricingData?: any;
    jobId?: string;
}

export default function SelectionPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const jobId = searchParams?.get('jobId');

    const [objects, setObjects] = useState<DetectedObject[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!jobId) {
            router.push('/pipeline');
            return;
        }

        const fetchResults = async () => {
            try {
                const response = await fetch(`http://localhost:5000/api/pipeline/status/${jobId}`);
                const data = await response.json();

                if (data.results && data.results.detected_objects) {
                    const mappedObjects: DetectedObject[] = data.results.detected_objects.map((obj: any, index: number) => ({
                        id: obj.cropped_id || `obj-${index}`,
                        name: obj.recognition_result?.product_name || obj.label || obj.object_name || 'Unknown Item',
                        confidence: obj.confidence || 0.5,
                        boundingBox: obj.bounding_box || { x: 0, y: 0, width: 100, height: 100 },
                        croppedImageUrl: `http://localhost:5000/cropped_resellables/${obj.image_filename}`,
                        estimatedValue: obj.pricing_data?.summary?.avg || obj.recognition_result?.pricing?.typical_price_range?.min || 0,
                        googleData: obj.recognition_result,
                        pricingData: obj.pricing_data,
                        jobId: jobId
                    }));

                    setObjects(mappedObjects);
                    setLoading(false);
                }
            } catch (error) {
                console.error('Error fetching results:', error);
            }
        };

        fetchResults();
    }, [jobId, router]);

    if (loading) {
        return (
            <div className="fixed inset-0 bg-gradient-to-br from-[#F6EFD9] via-white to-[#F6EFD9] flex items-center justify-center">
                <div className="text-center">
                    <div className="w-20 h-20 mx-auto mb-6 border-4 border-[#5BAAA7] border-t-transparent rounded-full animate-spin" />
                    <h2 className="text-2xl font-bold text-black">Loading items...</h2>
                </div>
            </div>
        );
    }

    return (
        <ItemSelection
            detectedObjects={objects}
            onBack={() => router.push('/dashboard')}
            onItemsSelected={(items) => {
                console.log('Selected items:', items);
                router.push('/dashboard');
            }}
        />
    );
}
