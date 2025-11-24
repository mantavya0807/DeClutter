import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatCardProps {
    title: string;
    value: string | number;
    trend?: string;
    trendUp?: boolean;
    icon: any;
    color?: string;
}

export default function StatCard({ title, value, trend, trendUp, icon: Icon, color = "indigo" }: StatCardProps) {
    const colorClasses: Record<string, string> = {
        indigo: "bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400",
        green: "bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400",
        blue: "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400",
        purple: "bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400",
        teal: "bg-teal-50 dark:bg-teal-900/20 text-teal-600 dark:text-teal-400",
    };

    return (
        <motion.div
            whileHover={{ y: -2 }}
            className="bg-white dark:bg-[#112233] p-6 rounded-2xl border border-gray-100 dark:border-[#1e3a52] shadow-sm transition-all duration-300"
        >
            <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-xl ${colorClasses[color] || colorClasses.indigo}`}>
                    <Icon className="w-6 h-6" />
                </div>
                {trend && (
                    <div className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${trendUp
                            ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400'
                            : 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400'
                        }`}>
                        {trendUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {trend}
                    </div>
                )}
            </div>

            <div>
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">{title}</h3>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">{value}</div>
            </div>
        </motion.div>
    );
}
