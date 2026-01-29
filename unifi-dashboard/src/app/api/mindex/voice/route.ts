import { NextRequest, NextResponse } from 'next/server';

// MINDEX Voice Query API - Natural language to MINDEX queries
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { query } = body;
    
    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }
    
    // Parse natural language query
    const parsedQuery = parseNaturalLanguageQuery(query);
    
    // Forward to MINDEX API
    const mindexUrl = process.env.MINDEX_URL || 'http://192.168.0.188:8000';
    
    let endpoint = '/api/mindex/v1/search';
    const params: Record<string, string> = { q: parsedQuery.searchTerm };
    
    if (parsedQuery.type === 'species') {
      endpoint = '/api/mindex/v1/taxa/search';
    } else if (parsedQuery.type === 'compound') {
      endpoint = '/api/mindex/compounds/search';
    } else if (parsedQuery.type === 'device') {
      endpoint = '/api/mindex/devices';
    }
    
    const response = await fetch(mindexUrl + endpoint + '?' + new URLSearchParams(params), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (response.ok) {
      const data = await response.json();
      const voiceResponse = formatForVoice(data, parsedQuery);
      
      return NextResponse.json({
        success: true,
        query: parsedQuery,
        results: data,
        voiceResponse,
      });
    }
    
    return NextResponse.json({
      success: false,
      error: 'MINDEX query failed',
      voiceResponse: 'I had trouble searching the database.',
    });
    
  } catch (error) {
    console.error('MINDEX voice query error:', error);
    return NextResponse.json({
      success: false,
      error: 'Internal error',
      voiceResponse: 'I encountered an error.',
    }, { status: 500 });
  }
}

interface ParsedQuery {
  type: 'species' | 'compound' | 'device' | 'general';
  searchTerm: string;
  filters: Record<string, string>;
}

function parseNaturalLanguageQuery(query: string): ParsedQuery {
  const q = query.toLowerCase();
  
  if (q.includes('species') || q.includes('mushroom') || q.includes('fungus')) {
    const searchTerm = q.replace(/what (is|are) (the )?/g, '').replace(/species|mushroom|fungus/g, '').trim();
    return { type: 'species', searchTerm, filters: {} };
  }
  
  if (q.includes('compound') || q.includes('chemical') || q.includes('medicinal')) {
    const searchTerm = q.replace(/what (is|are) (the )?/g, '').replace(/compounds?|chemicals?|medicinal/g, '').trim();
    return { type: 'compound', searchTerm, filters: {} };
  }
  
  if (q.includes('device') || q.includes('sensor')) {
    const searchTerm = q.replace(/devices?|sensors?/g, '').trim();
    return { type: 'device', searchTerm, filters: {} };
  }
  
  return { type: 'general', searchTerm: q, filters: {} };
}

function formatForVoice(data: any, query: ParsedQuery): string {
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return 'I could not find any results for ' + query.searchTerm + '.';
  }
  
  if (Array.isArray(data) && data.length > 0) {
    return 'I found ' + data.length + ' results for ' + query.searchTerm + '.';
  }
  
  return 'Here is what I found for ' + query.searchTerm + '.';
}
