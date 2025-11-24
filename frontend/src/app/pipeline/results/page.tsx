'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { DollarSign, Package, Star, Facebook, ShoppingCart, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface DetectedProduct {
    id: string;
    name: string;
    image_url: string;
    estimated_value: number;
    google_data: any;
    market_data: any;
    pricing_status: 'pending' | 'loading' | 'complete';
}

export default function ResultsPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const jobId = searchParams?.get('jobId');

    const [products, setProducts] = useState<DetectedProduct[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!jobId) {
            router.push('/pipeline');
            return;
        }

        const fetchJobResults = async () => {
            try {
                const response = await fetch(`http://localhost:5000/api/pipeline/status/${jobId}`);
                const data = await response.json();

                if (data.results && data.results.detected_objects) {
                    const detectedProducts: DetectedProduct[] = data.results.detected_objects.map((obj: any) => ({
                        id: obj.id || Math.random().toString(),
                        name: obj.google_data?.product_name || obj.label || 'Unknown Item',
                        image_url: `http://localhost:5000/cropped_resellables/${obj.image_filename}`,
                        estimated_value: obj.market_data?.summary?.avg || obj.google_data?.pricing?.typical_price_range?.min || 0,
                        google_data: obj.google_data,
                        market_data: obj.market_data,
                        pricing_status: obj.market_data ? 'complete' : 'pending'
                    }));

                    setProducts(detectedProducts);
                    setLoading(false);
                }
            } catch (error) {
                console.error('Error fetching results:', error);
            }
        };

        fetchJobResults();
        const interval = setInterval(fetchJobResults, 3000);

        return () => clearInterval(interval);
    }, [jobId, router]);

    if (loading && products.length === 0) {
        return (
            <div className="fixed inset-0 bg-gradient-to-br from-[#0a1b2a] to-[#1e3a52] flex items-center justify-center">
                <div className="text-center">
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        className="w-20 h-20 mx-auto mb-6 border-4 border-[#5BAAA7] border-t-transparent rounded-full"
                    />
                    <h2 className="text-2xl font-bold text-white">Loading Results...</h2>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#0a1b2a] to-[#1e3a52]">
            <div className="flex items-center justify-between p-6 bg-black/20 backdrop-blur-sm">
                <Link href="/dashboard">
                    <button className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-md rounded-xl text-white hover:bg-white/20 transition-all">
                        <ArrowLeft className="w-5 h-5" />
                        <span>Dashboard</span>
                    </button>
                </Link>
                <h1 className="text-2xl font-bold text-white">
                    Detected Products
                </h1>
                <div className="w-32" />
            </div>

            <div className="p-6 max-w-7xl mx-auto">
                <div className="text-center mb-8">
                    <h2 className="text-4xl font-bold text-white mb-2">
                        Found {products.length} Item{products.length !== 1 ? 's' : ''}
                    </h2>
                    <p className="text-gray-300">Review prices and select platforms to list on</p>
                </div>

                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {products.map((product, index) => (
                        <motion.div
                            key={product.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border-2 border-white/20 hover:border-[#5BAAA7] transition-all"
                        >
                            <div className="aspect-square bg-white/5 rounded-xl mb-4 overflow-hidden">
                                <img
                                    src={product.image_url}
                                    alt={product.name}
                                    className="w-full h-full object-cover"
                                    onError={(e) => {
                                        e.currentTarget.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3ENo Image%3C/text%3E%3C/svg%3E';
                                    }}
                                />
                            </div>

                            <div className="space-y-3">
                                <h3 className="text-white font-bold text-lg line-clamp-2">
                                    {product.name}
                                </h3>

                                {product.google_data?.rating && (
                                    <div className="flex items-center gap-1">
                                        <Star className="w-4 h-4 text-yellow-400 fill-current" />
                                        <span className="text-white text-sm">
                                            {product.google_data.rating.rating.toFixed(1)}/5.0
                                        </span>
                                    </div>
                                )}

                                <div className="flex items-baseline gap-2">
                                    <DollarSign className="w-6 h-6 text-green-400" />
                                    <span className="text-3xl font-bold text-green-400">
                                        ${product.estimated_value.toFixed(2)}
                                    </span>
                                    {product.pricing_status === 'loading' && (
                                        <span className="text-xs text-gray-400">Updating...</span>
                                    )}
                                </div>

                                {product.market_data?.summary && (
                                    <div className="text-sm text-gray-300">
                                        <p>Median: ${product.market_data.summary.median}</p>
                                        <p>Based on {product.market_data.summary.count} comparable listings</p>
                                    </div>
                                )}

                                <div className="flex gap-2 pt-2">
                                    <button className="flex-1 px-3 py-2 bg-blue-500/20 text-blue-300 rounded-lg hover:bg-blue-500/30 transition-all flex items-center justify-center gap-2">
                                        <Facebook className="w-4 h-4" />
                                        Facebook
                                    </button>
                                    <button className="flex-1 px-3 py-2 bg-yellow-500/20 text-yellow-300 rounded-lg hover:bg-yellow-500/30 transition-all flex items-center justify-center gap-2">
                                        <ShoppingCart className="w-4 h-4" />
                                        eBay
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
