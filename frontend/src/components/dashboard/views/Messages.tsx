import { useState, useMemo } from 'react';
import { MessageCircle, User, DollarSign, Clock, CheckCircle, XCircle, Sparkles, Loader2 } from 'lucide-react';

interface MessagesViewProps {
    messages: any[];
}

export default function MessagesView({ messages }: MessagesViewProps) {
    const [localMessages, setLocalMessages] = useState<any[]>(messages);
    const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
    const [replyText, setReplyText] = useState('');
    const [isGenerating, setIsGenerating] = useState(false);

    // Sync local messages with prop updates
    useMemo(() => {
        setLocalMessages(messages);
    }, [messages]);

    // Group messages by buyer name and item
    const groupedConversations = useMemo(() => {
        const groups = new Map<string, any[]>();

        localMessages.forEach((msg) => {
            const key = `${msg.buyerName}-${msg.itemTitle}`;
            if (!groups.has(key)) {
                groups.set(key, []);
            }
            groups.get(key)!.push(msg);
        });

        // Convert to array and get the most recent message for each conversation
        return Array.from(groups.entries()).map(([key, msgs]) => {
            const sortedMsgs = msgs.sort((a, b) =>
                new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
            );
            return {
                id: key,
                buyerName: sortedMsgs[0].buyerName,
                itemTitle: sortedMsgs[0].itemTitle,
                platform: sortedMsgs[0].platform,
                offerAmount: sortedMsgs.find(m => m.offerAmount > 0)?.offerAmount || 0,
                latestMessage: sortedMsgs[0].message,
                timestamp: sortedMsgs[0].timestamp,
                messageCount: msgs.length,
                messages: msgs.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
            };
        }).sort((a, b) =>
            new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );
    }, [localMessages]);

    const handleSendMessage = (conversationId: string, text: string) => {
        if (!text.trim()) return;

        const conv = groupedConversations.find(c => c.id === conversationId);
        if (!conv) return;

        const newMessage = {
            buyerName: conv.buyerName,
            itemTitle: conv.itemTitle,
            platform: conv.platform,
            offerAmount: 0,
            message: text,
            timestamp: new Date().toISOString(),
            sender: 'seller'
        };

        setLocalMessages(prev => [...prev, newMessage]);
        setReplyText('');
    };

    const handleAcceptOffer = (conversationId: string) => {
        const conv = groupedConversations.find(c => c.id === conversationId);
        if (!conv) return;

        handleSendMessage(conversationId, `Offer accepted! I'll get this shipped out to you right away.`);
    };

    const handleCounterOffer = (conversationId: string) => {
        const conv = groupedConversations.find(c => c.id === conversationId);
        if (!conv) return;

        const amount = prompt("Enter counter offer amount:", `$${Math.round(conv.offerAmount * 1.1)}`);
        if (amount) {
            handleSendMessage(conversationId, `Would you be willing to do ${amount}?`);
        }
    };

    const handleDraftMessage = async (conversationId: string) => {
        const conv = groupedConversations.find(c => c.id === conversationId);
        if (!conv) return;

        setIsGenerating(true);
        try {
            const response = await fetch('http://localhost:5000/api/chat/generate-draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    buyerName: conv.buyerName,
                    itemTitle: conv.itemTitle,
                    offerAmount: conv.offerAmount,
                    messages: conv.messages
                }),
            });

            const data = await response.json();
            if (data.draft) {
                setReplyText(data.draft);
            }
        } catch (error) {
            console.error('Failed to generate draft:', error);
            // Fallback
            setReplyText(`Hi ${conv.buyerName}, thanks for your message!`);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div className="flex h-[calc(100vh-8rem)] bg-white dark:bg-[#112233] rounded-2xl border border-gray-100 dark:border-[#1e3a52] overflow-hidden shadow-sm">
            {/* Conversation List */}
            <div className="w-full md:w-1/3 border-r border-gray-100 dark:border-[#1e3a52] flex flex-col">
                <div className="p-4 border-b border-gray-100 dark:border-[#1e3a52]">
                    <h3 className="font-bold text-gray-900 dark:text-white">Messages</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{groupedConversations.length} conversations</p>
                </div>
                <div className="flex-1 overflow-y-auto">
                    {groupedConversations.length === 0 ? (
                        <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                            No messages yet.
                        </div>
                    ) : (
                        groupedConversations.map((conv) => (
                            <button
                                key={conv.id}
                                onClick={() => setSelectedConversation(conv.id)}
                                className={`w-full p-4 text-left border-b border-gray-50 dark:border-[#1e3a52] hover:bg-gray-50 dark:hover:bg-[#0a1b2a]/50 transition-colors ${selectedConversation === conv.id ? 'bg-indigo-50 dark:bg-indigo-900/20 border-l-4 border-l-indigo-500' : ''
                                    }`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <span className="font-semibold text-gray-900 dark:text-white text-sm">{conv.buyerName}</span>
                                    <div className="flex items-center gap-2">
                                        <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-xs font-medium">
                                            {conv.platform}
                                        </span>
                                        <span className="text-xs text-gray-400">{new Date(conv.timestamp).toLocaleDateString()}</span>
                                    </div>
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400 mb-2 flex items-center justify-between">
                                    <span className="truncate max-w-[70%]">{conv.itemTitle}</span>
                                    {conv.messageCount > 1 && (
                                        <span className="bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded-full text-xs">
                                            {conv.messageCount} msgs
                                        </span>
                                    )}
                                </div>
                                <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
                                    {conv.latestMessage}
                                </p>
                                {conv.offerAmount > 0 && (
                                    <div className="mt-2 flex items-center gap-1 text-green-600 dark:text-green-400 text-xs font-medium">
                                        <DollarSign className="w-3 h-3" />
                                        Offer: ${conv.offerAmount}
                                    </div>
                                )}
                            </button>
                        ))
                    )}
                </div>
            </div>

            {/* Conversation Detail */}
            <div className="hidden md:flex flex-1 flex-col bg-gray-50/50 dark:bg-[#0a1b2a]/50">
                {selectedConversation ? (
                    (() => {
                        const conv = groupedConversations.find(c => c.id === selectedConversation);
                        if (!conv) return null;

                        // Check if item is sold based on message history
                        const isSold = conv.messages.some(m => m.sender === 'seller' && m.message.includes('Offer accepted'));

                        return (
                            <>
                                <div className="p-6 bg-white dark:bg-[#112233] border-b border-gray-100 dark:border-[#1e3a52] flex justify-between items-center">
                                    <div className="flex items-center gap-4">
                                        <div className="w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
                                            <User className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h3 className="font-bold text-gray-900 dark:text-white">{conv.buyerName}</h3>
                                            <p className="text-sm text-gray-500 dark:text-gray-400">Regarding: {conv.itemTitle}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {isSold && (
                                            <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full text-xs font-bold flex items-center gap-1">
                                                <CheckCircle className="w-3 h-3" /> Sold
                                            </span>
                                        )}
                                        <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-full text-xs font-bold">
                                            {conv.platform}
                                        </span>
                                        {conv.offerAmount > 0 && !isSold && (
                                            <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 flex items-center gap-1">
                                                <DollarSign className="w-3 h-3" /> Offer: ${conv.offerAmount}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="flex-1 p-6 overflow-y-auto space-y-4">
                                    {conv.messages.map((msg: any, idx: number) => {
                                        const isSeller = msg.sender === 'seller';
                                        return (
                                            <div key={idx} className={`flex gap-4 ${isSeller ? 'flex-row-reverse' : ''}`}>
                                                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center ${isSeller
                                                        ? 'bg-[#5BAAA7]/20 text-[#5BAAA7]'
                                                        : 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400'
                                                    }`}>
                                                    <User className="w-4 h-4" />
                                                </div>
                                                <div className={`flex-1 max-w-[80%] ${isSeller ? 'flex justify-end' : ''}`}>
                                                    <div className={`p-4 rounded-2xl shadow-sm border ${isSeller
                                                            ? 'bg-[#5BAAA7] text-white rounded-tr-none border-[#5BAAA7]'
                                                            : 'bg-white dark:bg-[#112233] text-gray-800 dark:text-gray-200 rounded-tl-none border-gray-100 dark:border-[#1e3a52]'
                                                        }`}>
                                                        <p>{msg.message}</p>
                                                        <p className={`text-xs mt-2 ${isSeller ? 'text-white/70' : 'text-gray-400'}`}>
                                                            {new Date(msg.timestamp).toLocaleString()}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}

                                    {/* AI Analysis Box - Only show if not sold */}
                                    {!isSold && (
                                        <div className="bg-gradient-to-br from-[#5BAAA7]/10 to-[#1A6A6A]/10 border border-[#5BAAA7]/20 rounded-xl p-4">
                                            <div className="flex items-center gap-2 mb-2 text-[#1A6A6A] dark:text-[#5BAAA7] font-bold text-sm">
                                                <MessageCircle className="w-4 h-4" />
                                                AI Analysis
                                            </div>
                                            <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                                                This offer is {conv.offerAmount > 0 ? `${Math.round(((conv.offerAmount / (conv.offerAmount * 1.15)) - 1) * -100)}% below your asking price` : 'pending'}. The buyer has a high rating. I suggest {conv.offerAmount > 0 ? `countering at $${Math.round(conv.offerAmount * 1.1)}` : 'responding promptly'}.
                                            </p>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => handleAcceptOffer(conv.id)}
                                                    className="px-3 py-1.5 bg-white dark:bg-[#112233] border border-gray-200 dark:border-[#1e3a52] rounded-lg text-xs font-medium hover:bg-green-50 dark:hover:bg-green-900/20 hover:text-green-600 hover:border-green-200 transition-all"
                                                >
                                                    Accept Offer
                                                </button>
                                                <button
                                                    onClick={() => handleCounterOffer(conv.id)}
                                                    className="px-3 py-1.5 bg-white dark:bg-[#112233] border border-gray-200 dark:border-[#1e3a52] rounded-lg text-xs font-medium hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 hover:border-blue-200 transition-all"
                                                >
                                                    Counter Offer
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="p-4 bg-white dark:bg-[#112233] border-t border-gray-100 dark:border-[#1e3a52]">
                                    {/* AI Draft Button */}
                                    {!isSold && (
                                        <div className="flex justify-end mb-2">
                                            <button
                                                onClick={() => handleDraftMessage(conv.id)}
                                                disabled={isGenerating}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-lg text-xs font-medium hover:bg-indigo-100 dark:hover:bg-indigo-900/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {isGenerating ? (
                                                    <Loader2 className="w-3 h-3 animate-spin" />
                                                ) : (
                                                    <Sparkles className="w-3 h-3" />
                                                )}
                                                {isGenerating ? 'Drafting...' : 'Draft AI Response'}
                                            </button>
                                        </div>
                                    )}

                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={replyText}
                                            onChange={(e) => setReplyText(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage(conv.id, replyText)}
                                            placeholder="Type a reply..."
                                            className="flex-1 px-4 py-2 bg-gray-50 dark:bg-[#0a1b2a] border border-gray-200 dark:border-[#1e3a52] rounded-xl focus:outline-none focus:border-[#5BAAA7] text-gray-900 dark:text-white"
                                        />
                                        <button
                                            onClick={() => handleSendMessage(conv.id, replyText)}
                                            className="px-4 py-2 bg-[#5BAAA7] text-white rounded-xl font-medium hover:bg-[#4a8f8c] transition-colors"
                                        >
                                            Send
                                        </button>
                                    </div>
                                </div>
                            </>
                        );
                    })()
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
                        <MessageCircle className="w-12 h-12 mb-4 opacity-20" />
                        <p>Select a conversation to view details</p>
                    </div>
                )}
            </div>
        </div>
    );
}
