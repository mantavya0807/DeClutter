import { createClient } from '@/utils/supabase/server';
import DashboardClient, { Listing, BuyerMessage, Sale, PlatformStats, DetectedItem, MarketIntelligence } from './DashboardClient';
import { redirect } from 'next/navigation';

export default async function DashboardPage() {
  const supabase = await createClient();

  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    redirect('/login');
  }

  // Fetch Listings
  const { data: listingsData } = await supabase
    .from('listings')
    .select('*, cropped:cropped_id(*)')
    .eq('user_id', user.id);

  // Fetch Conversations (Messages)
  const { data: conversationsData, error: convError } = await supabase
    .from('conversations')
    .select('*')
    .order('last_message_at', { ascending: false });

  if (convError) {
    console.error('Error fetching conversations:', convError);
  }

  // Fetch messages separately to manually join them
  let enrichedConversations = conversationsData || [];

  if (enrichedConversations.length > 0) {
    const conversationIds = enrichedConversations.map((c: any) => c.id);
    const { data: messagesData } = await supabase
      .from('messages')
      .select('conversation_id, content, created_at')
      .in('conversation_id', conversationIds)
      .order('created_at', { ascending: false });

    // Manually join messages to conversations
    enrichedConversations = enrichedConversations.map((conv: any) => {
      const convMessages = (messagesData || []).filter((m: any) => m.conversation_id === conv.id);
      return {
        ...conv,
        messages: convMessages
      };
    });
  }

  // Derive Sales from Listings (since we don't have a separate sales table yet)
  // We consider a listing "sold" if status is 'sold'
  const salesDataRaw = (listingsData || []).filter((l: any) => l.status === 'sold');

  // Map data to interfaces
  const listings: Listing[] = (listingsData || []).map((item: any) => {
    // Map platforms from string array to object array
    const platformList = Array.isArray(item.platforms) ? item.platforms : [];
    const mappedPlatforms = platformList.map((p: string) => ({
      name: p.charAt(0).toUpperCase() + p.slice(1), // Capitalize
      status: item.status === 'posted' ? 'Active' : 'Pending',
      views: Math.floor(Math.random() * 50), // Mock views for now
      messages: 0, // Default
      price: item.price || 0
    }));

    return {
      id: item.id,
      title: item.title || 'Untitled Listing',
      image: item.cropped?.cropped_image_url || null,
      price: item.price || 0,
      originalPrice: item.original_price || item.price || 0,
      description: item.description || '',
      tags: item.tags || [],
      status: item.status === 'posted' ? 'Active' : (item.status === 'sold' ? 'Sold' : 'Draft'),
      platforms: mappedPlatforms,
      analytics: item.analytics || {
        totalViews: Math.floor(Math.random() * 100),
        engagementRate: 0,
        timesSaved: 0,
        avgTimeOnListing: 0,
        topAgeGroup: 'N/A',
        topLocation: 'N/A'
      },
      offers: item.offers || []
    };
  });

  const buyerMessages: BuyerMessage[] = (enrichedConversations || []).map((item: any) => {
    // Determine the message to display
    let displayMessage = item.last_message || '';

    // Fallback to messages table if last_message is empty/missing
    if (!displayMessage && item.messages && Array.isArray(item.messages) && item.messages.length > 0) {
      displayMessage = item.messages[0].content;
    }

    return {
      id: item.id,
      itemTitle: item.item_title || 'Unknown Item',
      buyerName: item.buyer_name || 'Unknown Buyer',
      platform: 'Facebook', // Default to Facebook for now as it's the main source
      offerAmount: item.offer_amount || 0,
      originalPrice: item.original_price || 0,
      message: displayMessage,
      timestamp: item.updated_at || new Date().toISOString(),
      status: item.status || 'pending',
      aiAnalysis: item.ai_analysis || {
        sentiment: 'neutral',
        urgency: 'low',
        negotiationLikelihood: 0,
        recommendedResponse: '',
        suggestedPrice: 0,
        reasoning: ''
      },
      buyerHistory: item.buyer_history || {
        previousPurchases: 0,
        avgResponseTime: 'N/A',
        cancellationRate: 0,
        rating: 0
      }
    };
  });

  const salesData: Sale[] = salesDataRaw.map((item: any) => ({
    id: item.id,
    title: item.title,
    image: item.cropped?.cropped_image_url || "/vercel.svg",
    soldPrice: item.price || 0, // Assuming sold at listed price for now
    originalAskingPrice: item.price || 0,
    costBasis: 0, // Not tracked yet
    netProfit: item.price || 0, // Simplified
    platform: (item.platforms && item.platforms.length > 0) ? item.platforms[0] : 'Unknown',
    buyer: 'Unknown Buyer',
    saleDate: item.updated_at || new Date().toISOString(),
    daysListed: Math.floor(Math.random() * 10) + 1, // Mock
    totalViews: Math.floor(Math.random() * 200),
    offers: 1,
    negotiations: 0,
    finalDiscount: 0,
    platformFees: 0,
    shippingCost: 0,
    paymentMethod: 'Online',
    category: 'General',
    condition: 'Used'
  }));

  // Calculate Platform Stats from real data
  const platformStats: Record<string, PlatformStats> = {
    facebook: { totalListings: 0, activeBuyers: 0, avgTimeToSell: 0, avgSalePrice: 0, successRate: 0, monthlyTrend: '+0%', topCategories: [], recentSales: [] },
    ebay: { totalListings: 0, activeBuyers: 0, avgTimeToSell: 0, avgSalePrice: 0, successRate: 0, monthlyTrend: '+0%', topCategories: [], recentSales: [] }
  };

  // Helper to process stats for a platform
  const processPlatformStats = (platformKey: string) => {
    const platformSales = salesData.filter(s => s.platform.toLowerCase().includes(platformKey));
    const platformListings = listings.filter(l => l.platforms.some(p => p.name.toLowerCase().includes(platformKey) && p.status === 'Active'));

    const totalSales = platformSales.length;
    const totalRevenue = platformSales.reduce((sum, s) => sum + s.soldPrice, 0);
    const totalDays = platformSales.reduce((sum, s) => sum + s.daysListed, 0);

    // Calculate top categories
    const categories = platformSales.map(s => s.category);
    const categoryCounts = categories.reduce((acc, curr) => {
      acc[curr] = (acc[curr] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    const topCategories = Object.entries(categoryCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([cat]) => cat);

    // Calculate recent sales
    const recentSales = platformSales
      .sort((a, b) => new Date(b.saleDate).getTime() - new Date(a.saleDate).getTime())
      .slice(0, 3)
      .map(s => ({ item: s.title, price: s.soldPrice, date: new Date(s.saleDate).toLocaleDateString() }));

    platformStats[platformKey] = {
      totalListings: platformListings.length,
      activeBuyers: platformSales.length + Math.floor(Math.random() * 5), // Add some active interest
      avgTimeToSell: totalSales > 0 ? Math.round(totalDays / totalSales) : 0,
      avgSalePrice: totalSales > 0 ? Math.round(totalRevenue / totalSales) : 0,
      successRate: (totalSales + platformListings.length) > 0 ? (totalSales / (totalSales + platformListings.length)) : 0,
      monthlyTrend: totalSales > 0 ? `+${Math.floor(Math.random() * 20) + 5}%` : '0%', // Mock trend for now as we don't have historical snapshots
      topCategories: topCategories.length > 0 ? topCategories : ['General'],
      recentSales: recentSales
    };
  };

  processPlatformStats('facebook');
  processPlatformStats('ebay');

  const detectedItems: DetectedItem[] = [];

  // Mock Market Intelligence based on real sales data categories if available
  const allCategories = salesData.map(s => s.category);
  const uniqueCategories = Array.from(new Set(allCategories));

  const marketIntelligence: MarketIntelligence = {
    trending: {
      upCategories: uniqueCategories.slice(0, 2).map(c => ({ name: c, growth: '+12%', avgPrice: 45 })),
      downCategories: uniqueCategories.slice(2, 4).map(c => ({ name: c, growth: '-5%', avgPrice: 30 }))
    },
    seasonality: {
      current: 'Spring Cleaning',
      peakMonths: ['March', 'April', 'May'],
      recommendations: ['List winter gear now for clearance', 'Prepare outdoor furniture listings']
    },
    competition: {
      avgListingTime: 14, // Market benchmark
      yourAvgTime: salesData.length > 0 ? Math.round(salesData.reduce((sum, s) => sum + s.daysListed, 0) / salesData.length) : 0,
      avgSuccessRate: 0.65, // Market benchmark
      yourSuccessRate: (salesData.length + listings.filter(l => l.status === 'Active').length) > 0
        ? salesData.length / (salesData.length + listings.filter(l => l.status === 'Active').length)
        : 0
    }
  };

  const userProfile = {
    name: user.user_metadata?.full_name || user.email?.split('@')[0] || 'User',
    email: user.email || '',
    avatar: user.user_metadata?.avatar_url || ''
  };

  return (
    <DashboardClient
      userId={user.id}
      userProfile={userProfile}
      platformStats={platformStats}
      detectedItems={detectedItems}
      listings={listings}
      buyerMessages={buyerMessages}
      salesData={salesData}
      marketIntelligence={marketIntelligence}
    />
  );
}
