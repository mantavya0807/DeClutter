import AIChatbot from '@/components/AIChatbot';

interface AIAssistantViewProps {
    listings: any[];
    salesData: any[];
    platformStats: any;
}

export default function AIAssistantView({ listings, salesData, platformStats }: AIAssistantViewProps) {
    return (
        <div className="h-[calc(100vh-8rem)] w-full">
            <AIChatbot
                listings={listings}
                salesData={salesData}
                platformStats={platformStats}
            />
        </div>
    );
}
