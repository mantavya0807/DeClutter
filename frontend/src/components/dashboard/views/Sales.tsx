import { DollarSign, TrendingUp, Package, Target, Clock } from 'lucide-react';
import StatCard from '../StatCard';

interface SalesViewProps {
    salesData: any[];
    platformStats: any;
}

export default function SalesView({ salesData, platformStats }: SalesViewProps) {
    const totalRevenue = salesData.reduce((sum, s) => sum + s.soldPrice, 0);
    const totalProfit = salesData.reduce((sum, s) => sum + s.netProfit, 0);
    const itemsSold = salesData.length;
    const avgDaysToSell = itemsSold > 0 ? Math.round(salesData.reduce((sum, s) => sum + s.daysListed, 0) / itemsSold) : 0;
    const successRate = platformStats.facebook?.successRate || 0;

    return (
        <div className="space-y-8">
            {/* Top Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard
                    title="Net Profit"
                    value={`$${totalProfit.toLocaleString()}`}
                    icon={DollarSign}
                    color="green"
                />
                <StatCard
                    title="Items Sold"
                    value={itemsSold}
                    icon={Package}
                    color="blue"
                />
                <StatCard
                    title="Avg Days to Sell"
                    value={avgDaysToSell}
                    icon={Clock}
                    color="purple"
                />
                <StatCard
                    title="Success Rate"
                    value={`${Math.round(successRate * 100)}%`}
                    icon={Target}
                    color="teal"
                />
            </div>

            {/* Platform Performance Analysis */}
            <div className="bg-white dark:bg-[#112233] rounded-2xl border border-gray-100 dark:border-[#1e3a52] p-6 shadow-sm">
                <h3 className="font-bold text-lg text-gray-900 dark:text-white mb-6">Platform Performance Analysis</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {Object.entries(platformStats).map(([platformKey, stats]: [string, any]) => (
                        <div key={platformKey} className="bg-gray-50 dark:bg-[#0a1b2a] p-6 rounded-xl border border-gray-100 dark:border-[#1e3a52]">
                            <div className="flex items-center justify-between mb-4">
                                <h4 className="font-bold text-gray-900 dark:text-white capitalize">{platformKey}</h4>
                                <span className={`px-2 py-1 rounded text-xs font-bold ${stats.successRate > 0.5
                                        ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                                        : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                                    }`}>
                                    {Math.round(stats.successRate * 100)}%
                                </span>
                            </div>

                            <div className="space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500 dark:text-gray-400">Active Listings:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">{stats.totalListings}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500 dark:text-gray-400">Avg Sale Price:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">${stats.avgSalePrice}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500 dark:text-gray-400">Avg Time to Sell:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">{stats.avgTimeToSell} days</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-gray-500 dark:text-gray-400">Success Rate:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">{Math.round(stats.successRate * 100)}%</span>
                                </div>
                                {stats.topCategories && stats.topCategories.length > 0 && (
                                    <div className="pt-3 border-t border-gray-200 dark:border-[#1e3a52]">
                                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">Top Categories:</p>
                                        <div className="flex flex-wrap gap-1">
                                            {stats.topCategories.map((cat: string, idx: number) => (
                                                <span key={idx} className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded text-xs">
                                                    {cat}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Transaction History */}
            <div className="bg-white dark:bg-[#112233] rounded-2xl border border-gray-100 dark:border-[#1e3a52] overflow-hidden shadow-sm">
                <div className="p-6 border-b border-gray-100 dark:border-[#1e3a52]">
                    <h3 className="font-bold text-lg text-gray-900 dark:text-white">Recent Transactions</h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-gray-50 dark:bg-[#0a1b2a]">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Item</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Platform</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Amount</th>
                                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-[#1e3a52]">
                            {salesData.map((sale) => (
                                <tr key={sale.id} className="hover:bg-gray-50 dark:hover:bg-[#0a1b2a]/50 transition-colors">
                                    <td className="px-6 py-4">
                                        <span className="font-medium text-gray-900 dark:text-white">{sale.title}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-xs font-medium">
                                            {sale.platform}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-sm">{new Date(sale.saleDate).toLocaleDateString()}</td>
                                    <td className="px-6 py-4 text-right font-medium text-gray-900 dark:text-white">${sale.soldPrice}</td>
                                    <td className="px-6 py-4 text-right">
                                        <span className="px-2 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                                            Completed
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
