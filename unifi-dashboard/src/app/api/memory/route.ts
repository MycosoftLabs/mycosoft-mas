/**
 * Memory API Route - February 5, 2026
 * 
 * Proxies all /api/memory/* requests to the MAS backend.
 * Provides unified memory access from the frontend.
 */

import { NextRequest, NextResponse } from 'next/server';

const MAS_ORCHESTRATOR_URL = process.env.MAS_ORCHESTRATOR_URL || 'http://192.168.0.188:8001';

interface MemoryRequest {
  action: 'read' | 'write' | 'search' | 'delete' | 'stats';
  scope?: string;
  namespace?: string;
  key?: string;
  value?: Record<string, unknown>;
  query?: string;
  layer?: string;
  limit?: number;
  tags?: string[];
  importance?: number;
  agent_id?: string;
}

interface MemoryResponse {
  success: boolean;
  data?: unknown;
  error?: string;
}

async function proxyToMAS(endpoint: string, method: string, body?: unknown): Promise<Response> {
  const url = +""+${'$'}{MAS_ORCHESTRATOR_URL}/api/v1/memory{endpoint}+""+;
  
  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  
  return response;
}

export async function POST(request: NextRequest): Promise<NextResponse<MemoryResponse>> {
  try {
    const body: MemoryRequest = await request.json();
    
    switch (body.action) {
      case 'read': {
        const params = new URLSearchParams();
        if (body.scope) params.append('scope', body.scope);
        if (body.namespace) params.append('namespace', body.namespace);
        if (body.key) params.append('key', body.key);
        
        const response = await proxyToMAS(+""+/read?{params.toString()}+""+, 'GET');
        const data = await response.json();
        
        return NextResponse.json({ success: true, data });
      }
      
      case 'write': {
        const response = await proxyToMAS('/remember', 'POST', {
          agent_id: body.agent_id || 'frontend',
          content: body.value,
          layer: body.layer || 'session',
          importance: body.importance || 0.5,
          tags: body.tags || [],
        });
        const data = await response.json();
        
        return NextResponse.json({ success: true, data });
      }
      
      case 'search': {
        const response = await proxyToMAS('/recall', 'POST', {
          agent_id: body.agent_id || 'frontend',
          query: body.query,
          layer: body.layer,
          tags: body.tags,
          limit: body.limit || 10,
        });
        const data = await response.json();
        
        return NextResponse.json({ success: true, data });
      }
      
      case 'delete': {
        const response = await proxyToMAS(+""+/delete/{body.key}+""+, 'DELETE');
        const data = await response.json();
        
        return NextResponse.json({ success: true, data });
      }
      
      case 'stats': {
        const response = await proxyToMAS('/stats', 'GET');
        const data = await response.json();
        
        return NextResponse.json({ success: true, data });
      }
      
      default:
        return NextResponse.json({ 
          success: false, 
          error: +""+Unknown action: {body.action}+""+ 
        }, { status: 400 });
    }
  } catch (error) {
    console.error('Memory API error:', error);
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error' 
    }, { status: 500 });
  }
}

export async function GET(request: NextRequest): Promise<NextResponse<MemoryResponse>> {
  try {
    const { searchParams } = new URL(request.url);
    const endpoint = searchParams.get('endpoint') || '/stats';
    
    const response = await proxyToMAS(endpoint, 'GET');
    const data = await response.json();
    
    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('Memory API error:', error);
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error' 
    }, { status: 500 });
  }
}
