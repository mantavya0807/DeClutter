import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  Send,
  Sparkles,
  MessageSquare,
  Loader2,
  Zap,
  TrendingUp,
  DollarSign,
  Package,
  ArrowRight,
  Activity,
  Tag
} from 'lucide-react';

interface Message {
  id: string;
  type: 'user' | 'bot' | 'system';
  text: string;
  timestamp: Date;
}

interface AIChatbotProps {
  listings: any[];
  salesData: any[];
  platformStats: any;
}

export default function AIChatbot({ listings, salesData, platformStats }: AIChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      text: text,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      const context = {
        recentListings: listings,
        salesHistory: salesData,
        analytics: {
          totalRevenue: salesData.reduce((sum, s) => sum + s.soldPrice, 0),
          platformStats: platformStats
        }
      };

      // Prepare history
      const history = messages
        .filter(m => m.type !== 'system')
        .map(m => ({
          role: m.type === 'user' ? 'user' : 'model',
          parts: [{ text: m.text }]
        }));

      const response = await fetch('http://localhost:5000/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          context: context,
          history: history
        }),
      });

      if (!response.ok) throw new Error('Failed to get response');
      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let botMessageId = (Date.now() + 1).toString();
      let botText = '';

      // Create initial bot message
      setMessages(prev => [...prev, {
        id: botMessageId,
        type: 'bot',
        text: '',
        timestamp: new Date()
      }]);

      setIsTyping(false); // Stop "thinking" indicator, start streaming

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        botText += chunk;

        setMessages(prev => prev.map(msg =>
          msg.id === botMessageId ? { ...msg, text: botText } : msg
        ));
      }

    } catch (error) {
      console.error('AI Error:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        type: 'bot',
        text: "I'm having trouble connecting to the server. Please ensure the backend is running.",
        timestamp: new Date()
      }]);
      setIsTyping(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputValue);
  };

  const quickActions = [
    { label: 'Analyze Pricing', icon: DollarSign, query: 'Analyze the pricing of my active listings. Are they competitive?' },
    { label: 'Sales Trends', icon: TrendingUp, query: 'What are the recent sales trends in my dashboard?' },
    { label: 'Active Listings', icon: Package, query: 'Give me a summary of my active listings.' },
  ];

  const activeListingsCount = listings.filter(l => l.status === 'Active').length;
  const totalRevenue = salesData.reduce((sum, s) => sum + s.soldPrice, 0);

  return (
    <div className="flex h-full w-full bg-white dark:bg-[#0a1b2a] rounded-2xl shadow-sm border border-gray-200 dark:border-[#112233] overflow-hidden font-sans transition-colors duration-300">
      {/* Chat Area (Left/Center) */}
      <div className="flex-1 flex flex-col border-r border-gray-100 dark:border-[#112233]">
        {/* Header */}
        <div className="bg-white dark:bg-[#0a1b2a] border-b border-gray-100 dark:border-[#112233] p-4 flex items-center justify-between transition-colors duration-300">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-50 dark:bg-indigo-900/30 rounded-xl flex items-center justify-center transition-colors duration-300">
              <Sparkles className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900 dark:text-white transition-colors duration-300">Market Assistant</h3>
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                Connected to Dashboard
              </div>
            </div>
          </div>
          <button
            onClick={() => setMessages([])}
            className="text-xs text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-colors"
          >
            Clear Chat
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-gray-50/30 dark:bg-[#050e16]/50 transition-colors duration-300">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-60">
              <div className="w-16 h-16 bg-indigo-50 dark:bg-indigo-900/20 rounded-2xl flex items-center justify-center mb-4 transition-colors duration-300">
                <MessageSquare className="w-8 h-8 text-indigo-400 dark:text-indigo-500" />
              </div>
              <h4 className="font-semibold text-gray-900 dark:text-white mb-2 transition-colors duration-300">How can I help you today?</h4>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs mx-auto mb-8 transition-colors duration-300">
                I can analyze your sales data, suggest pricing strategies, or summarize your inventory.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => handleSendMessage(action.query)}
                    className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-[#112233] border border-gray-200 dark:border-[#1e3a52] rounded-xl hover:border-indigo-300 dark:hover:border-indigo-500 hover:shadow-sm transition-all text-sm text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400"
                  >
                    <action.icon className="w-5 h-5" />
                    <span>{action.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] rounded-2xl px-5 py-4 ${msg.type === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm shadow-md'
                  : 'bg-white dark:bg-[#112233] text-gray-800 dark:text-gray-200 border border-gray-100 dark:border-[#1e3a52] rounded-bl-sm shadow-sm'
                }`}>
                {msg.type === 'user' ? (
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.text}</div>
                ) : (
                  <div className="prose prose-sm max-w-none prose-indigo dark:prose-invert prose-p:leading-relaxed prose-pre:bg-gray-50 dark:prose-pre:bg-gray-900 prose-pre:text-gray-700 dark:prose-pre:text-gray-300">
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-[#112233] border border-gray-100 dark:border-[#1e3a52] rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm flex items-center gap-2 transition-colors duration-300">
                <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
                <span className="text-xs text-gray-400 dark:text-gray-500 font-medium">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 bg-white dark:bg-[#0a1b2a] border-t border-gray-100 dark:border-[#112233] transition-colors duration-300">
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your question..."
              className="flex-1 px-4 py-3 rounded-xl border border-gray-200 dark:border-[#1e3a52] focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 bg-gray-50 dark:bg-[#112233] focus:bg-white dark:focus:bg-[#0a1b2a] text-gray-900 dark:text-white transition-all text-sm"
              disabled={isTyping}
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isTyping}
              className="bg-indigo-600 hover:bg-indigo-700 text-white p-3 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm hover:shadow-md"
            >
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </div>

      {/* Context Panel (Right) */}
      <div className="w-80 bg-gray-50 dark:bg-[#050e16]/50 border-l border-gray-100 dark:border-[#112233] p-6 hidden lg:flex flex-col gap-6 overflow-y-auto transition-colors duration-300">
        <div>
          <h4 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-4">Live Context</h4>

          {/* Active Listings Card */}
          <div className="bg-white dark:bg-[#112233] p-4 rounded-xl border border-gray-200 dark:border-[#1e3a52] shadow-sm mb-4 transition-colors duration-300">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <Tag className="w-4 h-4" />
                <span className="text-sm font-medium">Active Listings</span>
              </div>
              <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400">{activeListingsCount}</span>
            </div>
            <div className="space-y-2">
              {listings.filter(l => l.status === 'Active').slice(0, 3).map((item) => (
                <div key={item.id} className="text-xs text-gray-500 dark:text-gray-400 truncate border-l-2 border-indigo-100 dark:border-indigo-900 pl-2">
                  {item.title}
                </div>
              ))}
              {activeListingsCount > 3 && (
                <div className="text-xs text-indigo-500 dark:text-indigo-400 font-medium pl-2">
                  + {activeListingsCount - 3} more
                </div>
              )}
            </div>
          </div>

          {/* Revenue Card */}
          <div className="bg-white dark:bg-[#112233] p-4 rounded-xl border border-gray-200 dark:border-[#1e3a52] shadow-sm mb-4 transition-colors duration-300">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <Activity className="w-4 h-4" />
                <span className="text-sm font-medium">Total Revenue</span>
              </div>
              <span className="text-lg font-bold text-green-600 dark:text-green-400">${totalRevenue.toLocaleString()}</span>
            </div>
            <div className="text-xs text-gray-400 dark:text-gray-500">
              Based on {salesData.length} completed sales
            </div>
          </div>

          {/* Recent Sales */}
          <div className="bg-white dark:bg-[#112233] p-4 rounded-xl border border-gray-200 dark:border-[#1e3a52] shadow-sm transition-colors duration-300">
            <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 mb-3">
              <Package className="w-4 h-4" />
              <span className="text-sm font-medium">Recent Sales</span>
            </div>
            <div className="space-y-3">
              {salesData.slice(0, 3).map((sale) => (
                <div key={sale.id} className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-400 truncate max-w-[120px]">{sale.title}</span>
                  <span className="font-medium text-green-600 dark:text-green-400">${sale.soldPrice}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-auto">
          <div className="bg-indigo-50 dark:bg-indigo-900/20 p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/50 transition-colors duration-300">
            <div className="flex items-start gap-3">
              <Zap className="w-4 h-4 text-indigo-600 dark:text-indigo-400 mt-0.5" />
              <div>
                <h5 className="text-sm font-bold text-indigo-900 dark:text-indigo-300 mb-1">Pro Tip</h5>
                <p className="text-xs text-indigo-700 dark:text-indigo-400 leading-relaxed">
                  Ask me to "Analyze my pricing" to get a competitive breakdown of your active listings.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}