import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, Grid, List, MoreVertical, Trash2, Edit, ExternalLink } from 'lucide-react';

interface ListingsViewProps {
    listings: any[];
    onDelete: (id: string) => void;
}

export default function ListingsView({ listings, onDelete }: ListingsViewProps) {
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [filter, setFilter] = useState('All');
    const [searchQuery, setSearchQuery] = useState('');

    const filteredListings = listings.filter(item => {
        const matchesFilter = filter === 'All' || item.status === filter;
        const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesFilter && matchesSearch;
    });

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-[#112233] p-4 rounded-2xl border border-gray-100 dark:border-[#1e3a52] shadow-sm">
                <div className="flex items-center gap-4 overflow-x-auto pb-2 md:pb-0">
                    {['All', 'Active', 'Sold', 'Draft'].map((status) => (
                        <button
                            key={status}
                            onClick={() => setFilter(status)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap ${filter === status
                                    ? 'bg-[#5BAAA7] text-white shadow-lg shadow-[#5BAAA7]/20'
                                    : 'text-gray-500 hover:bg-gray-50 dark:hover:bg-[#0a1b2a] dark:text-gray-400'
                                }`}
                        >
                            {status}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search listings..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="pl-10 pr-4 py-2 bg-gray-50 dark:bg-[#0a1b2a] border border-gray-200 dark:border-[#1e3a52] rounded-xl text-sm focus:outline-none focus:border-[#5BAAA7] w-full md:w-64 text-gray-900 dark:text-white"
                        />
                    </div>
                    <div className="flex bg-gray-50 dark:bg-[#0a1b2a] p-1 rounded-xl border border-gray-200 dark:border-[#1e3a52]">
                        <button
                            onClick={() => setViewMode('grid')}
                            className={`p-2 rounded-lg transition-all ${viewMode === 'grid' ? 'bg-white dark:bg-[#112233] shadow-sm text-[#5BAAA7]' : 'text-gray-400'}`}
                        >
                            <Grid className="w-4 h-4" />
                        </button>
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-2 rounded-lg transition-all ${viewMode === 'list' ? 'bg-white dark:bg-[#112233] shadow-sm text-[#5BAAA7]' : 'text-gray-400'}`}
                        >
                            <List className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>

            {/* Grid View */}
            {viewMode === 'grid' && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    <AnimatePresence>
                        {filteredListings.map((item) => (
                            <motion.div
                                key={item.id}
                                layout
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.9 }}
                                className="group bg-white dark:bg-[#112233] rounded-2xl border border-gray-100 dark:border-[#1e3a52] overflow-hidden hover:shadow-xl transition-all duration-300"
                            >
                                <div className="aspect-square relative overflow-hidden bg-gray-100 dark:bg-[#0a1b2a]">
                                    {item.image ? (
                                        <img src={item.image} alt={item.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-gray-400">No Image</div>
                                    )}
                                    <div className="absolute top-3 right-3">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold shadow-sm backdrop-blur-md ${item.status === 'Active' ? 'bg-green-500/90 text-white' :
                                                item.status === 'Sold' ? 'bg-blue-500/90 text-white' :
                                                    'bg-gray-500/90 text-white'
                                            }`}>
                                            {item.status}
                                        </span>
                                    </div>
                                </div>

                                <div className="p-4">
                                    <div className="flex justify-between items-start mb-2">
                                        <h3 className="font-bold text-gray-900 dark:text-white truncate pr-2">{item.title}</h3>
                                        <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                                            <MoreVertical className="w-4 h-4" />
                                        </button>
                                    </div>

                                    <div className="flex items-center justify-between mb-4">
                                        <span className="text-lg font-bold text-[#5BAAA7]">${item.price}</span>
                                        <span className="text-xs text-gray-500 dark:text-gray-400">{item.platforms.length} Platforms</span>
                                    </div>

                                    <div className="flex gap-2 pt-4 border-t border-gray-100 dark:border-[#1e3a52]">
                                        <button className="flex-1 py-2 bg-gray-50 dark:bg-[#0a1b2a] text-gray-600 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-100 dark:hover:bg-[#1e3a52] transition-colors flex items-center justify-center gap-2">
                                            <Edit className="w-3 h-3" /> Edit
                                        </button>
                                        <button
                                            onClick={() => onDelete(item.id)}
                                            className="p-2 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}

            {/* List View */}
            {viewMode === 'list' && (
                <div className="bg-white dark:bg-[#112233] rounded-2xl border border-gray-100 dark:border-[#1e3a52] overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-gray-50 dark:bg-[#0a1b2a] border-b border-gray-100 dark:border-[#1e3a52]">
                            <tr>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Item</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Price</th>
                                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Platforms</th>
                                <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-[#1e3a52]">
                            {filteredListings.map((item) => (
                                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-[#0a1b2a]/50 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-lg bg-gray-100 dark:bg-[#0a1b2a] overflow-hidden flex-shrink-0">
                                                {item.image && <img src={item.image} alt="" className="w-full h-full object-cover" />}
                                            </div>
                                            <span className="font-medium text-gray-900 dark:text-white">{item.title}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`px-3 py-1 rounded-full text-xs font-bold ${item.status === 'Active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                item.status === 'Sold' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                                    'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                                            }`}>
                                            {item.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-gray-900 dark:text-white font-medium">${item.price}</td>
                                    <td className="px-6 py-4 text-gray-500 dark:text-gray-400 text-sm">{item.platforms.map((p: any) => p.name).join(', ')}</td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2">
                                            <button className="p-2 text-gray-400 hover:text-[#5BAAA7] transition-colors">
                                                <Edit className="w-4 h-4" />
                                            </button>
                                            <button
                                                onClick={() => onDelete(item.id)}
                                                className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
