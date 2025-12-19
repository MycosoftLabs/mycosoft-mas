import { NextResponse } from 'next/server';

const MAS_API_URL = process.env.MAS_API_URL || 'http://localhost:8001';

export async function GET() {
  try {
    // Try to fetch from MAS backend
    const response = await fetch(`${MAS_API_URL}/voice/feedback/recent?limit=20`, {
      cache: 'no-store',
    });

    if (response.ok) {
      const data = await response.json();
      
      // Transform feedback to activity format
      const messages = (data.items || []).map((item: { 
        id?: string; 
        agent_name?: string; 
        transcript?: string; 
        response_text?: string;
        created_at?: string;
      }, i: number) => ({
        id: item.id || String(i),
        from: item.agent_name || 'User',
        to: 'MYCA',
        type: 'request',
        content: item.transcript || item.response_text || 'Voice interaction',
        timestamp: formatTimestamp(item.created_at),
      }));

      return NextResponse.json({
        messages,
        insights: generateInsights(),
      });
    }

    // Fallback mock data
    return NextResponse.json({
      messages: [
        { id: '1', from: 'Morgan', to: 'MYCA', type: 'request', content: 'What is the status of all agents?', timestamp: '1m ago' },
        { id: '2', from: 'MYCA', to: 'Morgan', type: 'response', content: 'All 6 active agents are running normally. 42 total agents registered.', timestamp: '1m ago' },
        { id: '3', from: 'MYCA', to: 'FinancialAgent', type: 'request', content: 'Generate monthly expense report', timestamp: '5m ago' },
        { id: '4', from: 'FinancialAgent', to: 'MYCA', type: 'response', content: 'Report generated: Total expenses $12,450.00', timestamp: '4m ago' },
        { id: '5', from: 'OpportunityScout', to: 'MYCA', type: 'event', content: 'Found 3 new business opportunities in mycology sector', timestamp: '10m ago' },
        { id: '6', from: 'MYCA', to: 'ProjectManagerAgent', type: 'request', content: 'Update project timeline for Q1 2025', timestamp: '15m ago' },
      ],
      insights: generateInsights(),
    });
  } catch (error) {
    console.error('Failed to fetch activity:', error);
    return NextResponse.json({
      messages: [],
      insights: [],
      error: 'Failed to connect to MAS backend',
    }, { status: 500 });
  }
}

function formatTimestamp(isoString?: string): string {
  if (!isoString) return 'Just now';
  
  const date = new Date(isoString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  
  const minutes = Math.floor(diff / (1000 * 60));
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function generateInsights() {
  return [
    { id: '1', type: 'success', title: 'Task Completed', description: 'OpportunityScout found 3 new business opportunities', timestamp: '2m ago', agent: 'OpportunityScout' },
    { id: '2', type: 'info', title: 'Research Update', description: 'MycologyBioAgent added 12 new species to database', timestamp: '15m ago', agent: 'MycologyBioAgent' },
    { id: '3', type: 'warning', title: 'High Memory Usage', description: 'MycologyBioAgent using 67% memory during analysis', timestamp: '20m ago', agent: 'MycologyBioAgent' },
    { id: '4', type: 'success', title: 'Voice Command', description: "Successfully processed Morgan's voice request", timestamp: '1h ago', agent: 'MYCA' },
    { id: '5', type: 'info', title: 'Workflow Complete', description: 'n8n Jarvis workflow executed successfully', timestamp: '2h ago', agent: 'MYCA' },
    { id: '6', type: 'success', title: 'Agent Online', description: 'FinancialAgent initialized and ready', timestamp: '3h ago', agent: 'FinancialAgent' },
  ];
}
