import { NextResponse } from 'next/server';

const MAS_API_URL = process.env.MAS_API_URL || 'http://localhost:8001';

export async function GET() {
  try {
    // Try to fetch from MAS backend
    const response = await fetch(`${MAS_API_URL}/agents/registry`, {
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      return NextResponse.json(data);
    }

    // Fallback to mock data if MAS not available
    return NextResponse.json({
      agents: [
        { id: 'myca', name: 'MYCA', displayName: 'MYCA Orchestrator', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 1247, tasksInProgress: 3, cpuUsage: 12, memoryUsage: 45 },
        { id: 'financial', name: 'FinancialAgent', displayName: 'Financial Agent', category: 'financial', status: 'active', lastActivity: '2m ago', tasksCompleted: 89, tasksInProgress: 1, cpuUsage: 5, memoryUsage: 23 },
        { id: 'marketing', name: 'MarketingAgent', displayName: 'Marketing Agent', category: 'communication', status: 'idle', lastActivity: '15m ago', tasksCompleted: 56, tasksInProgress: 0, cpuUsage: 0, memoryUsage: 18 },
        { id: 'mycology', name: 'MycologyBioAgent', displayName: 'Mycology Research', category: 'mycology', status: 'active', lastActivity: '1m ago', tasksCompleted: 234, tasksInProgress: 2, cpuUsage: 28, memoryUsage: 67 },
        { id: 'project', name: 'ProjectManagerAgent', displayName: 'Project Manager', category: 'core', status: 'active', lastActivity: '30s ago', tasksCompleted: 412, tasksInProgress: 5, cpuUsage: 8, memoryUsage: 31 },
        { id: 'opportunity', name: 'OpportunityScout', displayName: 'Opportunity Scout', category: 'research', status: 'active', lastActivity: '5m ago', tasksCompleted: 78, tasksInProgress: 1, cpuUsage: 15, memoryUsage: 42 },
        { id: 'dao', name: 'MycoDAOAgent', displayName: 'MycoDAO Agent', category: 'dao', status: 'idle', lastActivity: '1h ago', tasksCompleted: 23, tasksInProgress: 0, cpuUsage: 0, memoryUsage: 12 },
        { id: 'dashboard', name: 'DashboardAgent', displayName: 'Dashboard Agent', category: 'core', status: 'active', lastActivity: 'Just now', tasksCompleted: 890, tasksInProgress: 1, cpuUsage: 3, memoryUsage: 15 },
      ],
      totalAgents: 42,
      activeAgents: 6,
    });
  } catch (error) {
    console.error('Failed to fetch agent registry:', error);
    return NextResponse.json({
      agents: [],
      totalAgents: 0,
      activeAgents: 0,
      error: 'Failed to connect to MAS backend',
    }, { status: 500 });
  }
}
