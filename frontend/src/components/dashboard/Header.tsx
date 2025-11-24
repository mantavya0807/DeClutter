import { ThemeToggle } from '@/components/ThemeToggle';

interface HeaderProps {
    userProfile: {
        name: string;
        email: string;
        avatar?: string;
    };
    title: string;
}

export default function Header({ userProfile, title }: HeaderProps) {
    return (
        <header className="h-20 bg-white/80 dark:bg-[#0a1b2a]/80 backdrop-blur-md border-b border-gray-200 dark:border-[#1e3a52] sticky top-0 z-30 px-8 flex items-center justify-between transition-colors duration-300">
            {/* Page Title */}
            <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{title}</h1>
            </div>

            {/* Right Actions */}
            <div className="flex items-center gap-6">
                <div className="flex items-center gap-4">
                    <ThemeToggle />

                    <div className="h-8 w-[1px] bg-gray-200 dark:bg-[#1e3a52]" />

                    <div className="flex items-center gap-3">
                        <div className="text-right hidden md:block">
                            <p className="text-sm font-semibold text-gray-900 dark:text-white">{userProfile.name}</p>
                            <p className="text-xs text-gray-500 dark:text-gray-400">{userProfile.email}</p>
                        </div>
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#5BAAA7] to-[#1A6A6A] flex items-center justify-center text-white font-bold shadow-md">
                            {userProfile.avatar ? (
                                <img src={userProfile.avatar} alt={userProfile.name} className="w-full h-full rounded-full object-cover" />
                            ) : (
                                userProfile.name.charAt(0).toUpperCase()
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
