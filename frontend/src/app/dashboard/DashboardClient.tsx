'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/dashboard/Sidebar';
import Header from '@/components/dashboard/Header';
import Overview from '@/components/dashboard/views/Overview';
import Listings from '@/components/dashboard/views/Listings';
import Messages from '@/components/dashboard/views/Messages';
import Sales from '@/components/dashboard/views/Sales';
import AIAssistant from '@/components/dashboard/views/AIAssistant';
import DeclutterFlow from '@/components/DeclutterFlow';
import { createClient } from '@/utils/supabase/client';

interface DashboardClientProps {
    userId: string;
    userProfile: { name: string; email: string; avatar?: string };
    platformStats: Record<string, any>;
    listings: any[];
    buyerMessages: any[];
    salesData: any[];
}

export default function DashboardClient({
    userId,
    userProfile,
    platformStats,
    listings,
    buyerMessages,
    salesData,
}: DashboardClientProps) {
    const [activeTab, setActiveTab] = useState<'overview' | 'listings' | 'messages' | 'sales' | 'ai' | 'declutter'>('overview');
    const supabase = createClient();

    const changeTab = (tab: string) => setActiveTab(tab as any);

    const handleDeleteListing = async (id: string) => {
        if (confirm('Are you sure you want to delete this listing?')) {
            const { error } = await supabase.from('listings').delete().eq('id', id);
            if (error) {
                console.error('Error deleting listing:', error);
                alert('Failed to delete listing');
            } else {
                window.location.reload();
            }
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-[#050e16] text-gray-900 dark:text-gray-100 font-sans transition-colors duration-300">
            <Sidebar activeTab={activeTab} setActiveTab={changeTab} />
            <div className="pl-20 lg:pl-[280px] transition-all duration-300">
                <Header userProfile={userProfile} title={activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} />
                <main className="p-6 lg:p-8 max-w-[1600px] mx-auto">
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            transition={{ duration: 0.2 }}
                        >
                            {activeTab === 'overview' && (
                                <Overview userProfile={userProfile} listings={listings} salesData={salesData} setActiveTab={changeTab} />
                            )}
                            {activeTab === 'listings' && (
                                <Listings listings={listings} onDelete={handleDeleteListing} />
                            )}
                            {activeTab === 'messages' && <Messages messages={buyerMessages} />}
                            {activeTab === 'sales' && <Sales salesData={salesData} platformStats={platformStats} />}
                            {activeTab === 'ai' && (
                                <AIAssistant listings={listings} salesData={salesData} platformStats={platformStats} />
                            )}
                            {activeTab === 'declutter' && (
                                <DeclutterFlow
                                    userId={userId}
                                    onComplete={() => setActiveTab('listings')}
                                    onBack={() => setActiveTab('overview')}
                                />
                            )}
                        </motion.div>
                    </AnimatePresence>
                </main>
            </div>
        </div>
    );
}
