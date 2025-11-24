import {
    LayoutDashboard,
    Package,
    TrendingUp,
    Sparkles,
    LogOut,
    ChevronLeft,
    ChevronRight,
    MessageCircle
} from 'lucide-react';
import { motion } from 'framer-motion';
import { useState } from 'react';

interface SidebarProps {
    activeTab: string;
    setActiveTab: (tab: string) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
    const [isCollapsed, setIsCollapsed] = useState(false);

    const menuItems = [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard },
        { id: 'listings', label: 'Listings', icon: Package },
        { id: 'messages', label: 'Messages', icon: MessageCircle },
        { id: 'sales', label: 'Sales', icon: TrendingUp },
        { id: 'ai', label: 'AI Assistant', icon: Sparkles },
    ];

    return (
        <motion.aside
            initial={{ width: 280 }}
            animate={{ width: isCollapsed ? 80 : 280 }}
            className="h-screen bg-white dark:bg-[#0a1b2a] border-r border-gray-200 dark:border-[#1e3a52] flex flex-col fixed left-0 top-0 z-40 transition-colors duration-300"
        >
            {/* Logo Section */}
            <div className="h-20 flex items-center px-6 border-b border-gray-100 dark:border-[#1e3a52]">
                <div className="flex items-center gap-3 overflow-hidden">
                    <div className="w-8 h-8 bg-gradient-to-br from-[#5BAAA7] to-[#1A6A6A] rounded-lg flex items-center justify-center flex-shrink-0">
                        <Sparkles className="w-5 h-5 text-white" />
                    </div>
                    {!isCollapsed && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="font-bold text-xl whitespace-nowrap"
                        >
                            <span className="text-[#5BAAA7]">de</span>
                            <span className="text-gray-900 dark:text-white">Cluttered</span>
                        </motion.div>
                    )}
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-6 px-3 space-y-2">
                {menuItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => setActiveTab(item.id)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 group relative ${activeTab === item.id
                                ? 'bg-[#5BAAA7]/10 text-[#5BAAA7]'
                                : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-[#112233] hover:text-gray-900 dark:hover:text-white'
                            }`}
                    >
                        <item.icon className={`w-5 h-5 flex-shrink-0 ${activeTab === item.id ? 'text-[#5BAAA7]' : ''}`} />

                        {!isCollapsed && (
                            <span className="font-medium text-sm whitespace-nowrap">{item.label}</span>
                        )}

                        {/* Active Indicator */}
                        {activeTab === item.id && (
                            <motion.div
                                layoutId="activeTab"
                                className="absolute left-0 w-1 h-8 bg-[#5BAAA7] rounded-r-full"
                            />
                        )}

                        {/* Tooltip for collapsed state */}
                        {isCollapsed && (
                            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-50">
                                {item.label}
                            </div>
                        )}
                    </button>
                ))}
            </nav>

            {/* Bottom Actions */}
            <div className="p-3 border-t border-gray-100 dark:border-[#1e3a52] space-y-2">
                <button
                    onClick={async () => {
                        const { createClient } = await import('@/utils/supabase/client');
                        const supabase = createClient();
                        await supabase.auth.signOut();
                        window.location.href = '/login';
                    }}
                    className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-200"
                >
                    <LogOut className="w-5 h-5 flex-shrink-0" />
                    {!isCollapsed && <span className="font-medium text-sm">Sign Out</span>}
                </button>

                {/* Collapse Toggle */}
                <button
                    onClick={() => setIsCollapsed(!isCollapsed)}
                    className="w-full flex items-center justify-center p-2 mt-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                    {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
                </button>
            </div>
        </motion.aside>
    );
}
