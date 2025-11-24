import { motion } from 'framer-motion';
import StatCard from '../StatCard';
import { DollarSign, Package, ShoppingBag, Activity, Plus, Sparkles } from 'lucide-react';

interface OverviewProps {
    userProfile: any;
    listings: any[];
    salesData: any[];
    setActiveTab: (tab: string) => void;
}

export default function Overview({ userProfile, listings, salesData, setActiveTab }: OverviewProps) {
    const activeListings = listings.filter(l => l.status === 'Active').length;
    const totalRevenue = salesData.reduce((sum, s) => sum + s.soldPrice, 0);
    const totalSales = salesData.length;

    const recentActivity = [
        ...salesData.map(s => ({ type: 'sale', item: s, date: new Date(s.saleDate) })),
        ...listings.map(l => ({ type: 'listing', item: l, date: new Date() }))
    ].sort((a, b) => b.date.getTime() - a.date.getTime()).slice(0, 5);

    return (
        <div className="space-y-8">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                        Welcome back, {userProfile.name.split(' ')[0]}! 👋
                    </h2>
                    <p className="text-gray-500 dark:text-gray-400 mt-1">
                        Here's what's happening with your inventory today.
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => setActiveTab('ai')}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-xl font-medium hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors"
                    >
                        <Sparkles className="w-4 h-4" />
                        Ask AI
                    </button>
                    <button
                        onClick={() => setActiveTab('declutter')}
                        className="flex items-center gap-2 px-4 py-2 bg-[#5BAAA7] text-white rounded-xl font-medium hover:bg-[#4a8f8c] transition-colors shadow-lg shadow-[#5BAAA7]/20"
                    >
                        <Plus className="w-4 h-4" />
                        New Listing
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard title="Total Revenue" value={`$${totalRevenue.toLocaleString()}`} icon={DollarSign} color="green" />
                <StatCard title="Active Listings" value={activeListings} icon={Package} color="blue" />
                <StatCard title="Total Sales" value={totalSales} icon={ShoppingBag} color="purple" />
                <StatCard title="Engagement" value="High" icon={Activity} color="teal" />
            </div>

            <div className="bg-white dark:bg-[#112233] rounded-2xl border border-gray-100 dark:border-[#1e3a52] p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="font-bold text-lg text-gray-900 dark:text-white">Recent Activity</h3>
                </div>
                <div className="space-y-4">
                    {recentActivity.map((activity: any, idx) => (
                        <div key={idx} className="flex items-center justify-between p-4 rounded-xl bg-gray-50 dark:bg-[#0a1b2a] border border-gray-100 dark:border-[#1e3a52]">
                            <div className="flex items-center gap-4">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${activity.type === 'sale' ? 'bg-green-100 dark:bg-green-900/20 text-green-600' : 'bg-blue-100 dark:bg-blue-900/20 text-blue-600'}`}>
                                    {activity.type === 'sale' ? <DollarSign className="w-5 h-5" /> : <Package className="w-5 h-5" />}
                                </div>
                                <div>
                                    <p className="font-medium text-gray-900 dark:text-white">
                                        {activity.type === 'sale' ? 'Item Sold' : 'New Listing Created'}
                                    </p>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">
                                        {activity.item.title}
                                    </p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="font-bold text-gray-900 dark:text-white">
                                    {activity.type === 'sale' ? `+$${activity.item.soldPrice}` : `$${activity.item.price}`}
                                </p>
                                <p className="text-xs text-gray-400">
                                    {activity.date.toLocaleDateString()}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
