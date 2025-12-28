import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

// Get MAS API URL from environment or default
const MAS_API_URL = process.env.MAS_API_URL || 'http://localhost:8001';

export async function GET() {
  try {
    // Try to fetch real data from MAS backend
    try {
      const [healthRes, agentsRes] = await Promise.all([
        fetch(`${MAS_API_URL}/health`, { signal: AbortSignal.timeout(3000) }),
        fetch(`${MAS_API_URL}/agents/registry/`, { signal: AbortSignal.timeout(3000) }),
      ]);

      if (healthRes.ok && agentsRes.ok) {
        const healthData = await healthRes.json();
        const agentsData = await agentsRes.json();

        // Transform real agent data into topology format
        const agents = agentsData.agents || [];
        const entities = [
          {
            id: 'orchestrator-1',
            name: 'MYCA Orchestrator',
            type: 'orchestrator',
            status: healthData.status === 'ok' ? 'active' : 'error',
            x: 400,
            y: 100,
            connections: agents.map((a: { id: string }) => a.id),
            metadata: {
              uptime: healthData.uptime || 'Unknown',
              tasksCompleted: agentsData.total_agents || 0,
              tasksInProgress: agents.filter((a: { status: string }) => a.status === 'active').length,
              downloadSpeed: 0,
              uploadSpeed: 0,
              experience: 'Excellent' as const,
            },
          },
          ...agents.map((agent: { id: string; name: string; status: string; category?: string; metadata?: Record<string, unknown> }, index: number) => ({
            id: agent.id,
            name: agent.name,
            type: 'agent',
            category: agent.category || 'core',
            status: agent.status === 'active' ? 'active' : agent.status === 'idle' ? 'idle' : 'error',
            x: 200 + (index % 4) * 150,
            y: 250 + Math.floor(index / 4) * 100,
            connections: ['orchestrator-1'],
            metadata: agent.metadata || {},
          })),
        ];

        const connections = agents.map((agent: { id: string }) => ({
          from: 'orchestrator-1',
          to: agent.id,
          type: 'agent-to-orchestrator',
          status: 'active',
        }));

        return NextResponse.json({
          entities,
          connections,
          source: 'live',
        });
      }
    } catch (e) {
      console.log('MAS API not available, using mock data:', e instanceof Error ? e.message : 'Unknown');
    }

    // Fallback to mock data

    // Mock topology data
    const entities = [
      {
        id: 'orchestrator-1',
        name: 'MYCA Orchestrator',
        type: 'orchestrator',
        status: 'active',
        x: 400,
        y: 100,
        connections: ['agent-1', 'agent-2', 'agent-3', 'operator-1', 'user-1'],
        metadata: {
          ip: '192.168.0.1',
          uptime: '2w 4d 4h',
          tasksCompleted: 1247,
          tasksInProgress: 3,
          downloadSpeed: 159,
          uploadSpeed: 136,
          experience: 'Excellent' as const,
        },
      },
      {
        id: 'agent-1',
        name: 'Financial Agent',
        type: 'agent',
        category: 'financial',
        status: 'active',
        x: 300,
        y: 250,
        connections: ['orchestrator-1', 'database-1'],
        metadata: {
          ip: '192.168.0.172',
          uptime: '8d 20m',
          tasksCompleted: 89,
          tasksInProgress: 1,
          downloadSpeed: 49,
          uploadSpeed: 5,
          experience: 'Excellent' as const,
        },
      },
      {
        id: 'agent-2',
        name: 'Mycology Research',
        type: 'agent',
        category: 'mycology',
        status: 'active',
        x: 500,
        y: 250,
        connections: ['orchestrator-1', 'database-2'],
        metadata: {
          ip: '192.168.0.248',
          uptime: '8d 20m',
          tasksCompleted: 234,
          tasksInProgress: 2,
          downloadSpeed: 36,
          uploadSpeed: 49,
          experience: 'Excellent' as const,
        },
      },
      {
        id: 'agent-3',
        name: 'Project Manager',
        type: 'agent',
        category: 'core',
        status: 'active',
        x: 400,
        y: 350,
        connections: ['orchestrator-1', 'database-1'],
        metadata: {
          ip: '192.168.0.248',
          uptime: '17d 47m',
          tasksCompleted: 412,
          tasksInProgress: 5,
          downloadSpeed: 0,
          uploadSpeed: 0,
          experience: 'Excellent' as const,
        },
      },
      {
        id: 'operator-1',
        name: 'System Operator',
        type: 'operator',
        status: 'active',
        x: 200,
        y: 450,
        connections: ['orchestrator-1', 'database-1'],
      },
      {
        id: 'database-1',
        name: 'PostgreSQL',
        type: 'database',
        status: 'online',
        x: 150,
        y: 200,
        connections: ['agent-1', 'agent-3', 'operator-1'],
      },
      {
        id: 'database-2',
        name: 'Redis Cache',
        type: 'database',
        status: 'online',
        x: 150,
        y: 320,
        connections: ['agent-2'],
      },
      {
        id: 'program-1',
        name: 'n8n Workflows',
        type: 'program',
        status: 'active',
        x: 650,
        y: 200,
        connections: ['orchestrator-1'],
      },
      {
        id: 'program-2',
        name: 'External API',
        type: 'program',
        status: 'active',
        x: 650,
        y: 320,
        connections: ['agent-2'],
      },
      {
        id: 'user-1',
        name: 'Admin User',
        type: 'user',
        status: 'active',
        x: 300,
        y: 550,
        connections: ['orchestrator-1'],
      },
    ];

    const connections = [
      { from: 'orchestrator-1', to: 'agent-1', type: 'agent-to-orchestrator', status: 'active' },
      { from: 'orchestrator-1', to: 'agent-2', type: 'agent-to-orchestrator', status: 'active' },
      { from: 'orchestrator-1', to: 'agent-3', type: 'agent-to-orchestrator', status: 'active' },
      { from: 'orchestrator-1', to: 'operator-1', type: 'agent-to-operator', status: 'active' },
      { from: 'orchestrator-1', to: 'user-1', type: 'user-to-orchestrator', status: 'active' },
      { from: 'agent-1', to: 'database-1', type: 'agent-to-database', status: 'active' },
      { from: 'agent-2', to: 'database-2', type: 'agent-to-database', status: 'active' },
      { from: 'agent-3', to: 'database-1', type: 'agent-to-database', status: 'active' },
      { from: 'agent-2', to: 'program-2', type: 'agent-to-program', status: 'active' },
      { from: 'operator-1', to: 'database-1', type: 'operator-to-database', status: 'active' },
      { from: 'orchestrator-1', to: 'program-1', type: 'agent-to-program', status: 'active' },
    ];

    return NextResponse.json({
      entities,
      connections,
      source: 'mock',
    });
  } catch (error) {
    console.error('Error fetching topology:', error);
    return NextResponse.json(
      { error: 'Failed to fetch topology data' },
      { status: 500 }
    );
  }
}
