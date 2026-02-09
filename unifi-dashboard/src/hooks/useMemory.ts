/**
 * useMemory Hook - February 5, 2026
 * 
 * React hook for interacting with the MAS memory system.
 * Provides unified memory operations for frontend components.
 * 
 * EXTENDED: Added user profile, episodes, brain status, and management operations.
 */

import { useState, useCallback } from 'react';

interface MemoryEntry {
  id: string;
  content: Record<string, unknown>;
  layer: string;
  importance: number;
  created_at: string;
  tags: string[];
}

interface ConversationTurn {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

interface UserFact {
  id: string;
  subject: string;
  predicate?: string;
  object?: string;
  content?: Record<string, unknown>;
  learned_at: string;
}

interface MemoryStats {
  coordinator: {
    initialized: boolean;
    active_conversations: number;
    agent_namespaces: string[];
  };
  myca_memory: {
    total_memories: number;
    layers: Record<string, { count: number; avg_importance: number }>;
  };
}

interface UserProfile {
  user_id: string;
  preferences: Record<string, string | number | boolean>;
  facts: Array<{
    type: string;
    content: string;
    learned_from?: string;
    timestamp?: string;
  }>;
  last_interaction?: string;
}

interface Episode {
  id: string;
  event_type: string;
  description: string;
  importance: number;
  context?: Record<string, unknown>;
  timestamp: string;
  agent_id?: string;
}

interface BrainStatus {
  status: string;
  brain: {
    initialized: boolean;
    frontier_router?: boolean;
    memory_coordinator?: boolean;
  };
  providers: Record<string, { healthy: boolean }>;
}

interface UseMemoryReturn {
  // State
  loading: boolean;
  error: string | null;
  
  // Read operations
  fetchConversations: (scope: string, namespace: string) => Promise<ConversationTurn[]>;
  fetchFacts: (userId: string) => Promise<UserFact[]>;
  searchMemory: (query: string, scope?: string) => Promise<MemoryEntry[]>;
  getStats: () => Promise<MemoryStats | null>;
  
  // Write operations
  writeMemory: (entry: Partial<MemoryEntry>) => Promise<string | null>;
  
  // Delete operations
  deleteMemory: (scope: string, namespace: string, key: string) => Promise<boolean>;
  
  // User Profile operations
  getUserProfile: (userId: string) => Promise<UserProfile | null>;
  updateUserProfile: (userId: string, preferences: Record<string, string | number | boolean>) => Promise<boolean>;
  
  // Episode operations
  getEpisodes: (agentId?: string, limit?: number, eventType?: string) => Promise<Episode[]>;
  
  // Brain operations
  getBrainStatus: () => Promise<BrainStatus | null>;
  getBrainContext: (userId: string, query?: string) => Promise<Record<string, unknown> | null>;
  
  // Management operations
  exportMemory: (scope: string, format?: 'json' | 'csv') => Promise<Blob | null>;
  cleanupMemory: (scope: string, olderThanDays: number) => Promise<{ deleted: number } | null>;
}

export function useMemory(): UseMemoryReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const apiCall = useCallback(async <T>(
    action: string,
    params: Record<string, unknown>
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...params }),
      });
      
      const result = await response.json();
      
      if (!result.success) {
        throw new Error(result.error || 'Memory operation failed');
      }
      
      return result.data as T;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  
  const fetchConversations = useCallback(async (
    scope: string,
    namespace: string
  ): Promise<ConversationTurn[]> => {
    const result = await apiCall<{ memories: MemoryEntry[] }>('search', {
      agent_id: namespace,
      layer: 'session',
      tags: ['conversation'],
      limit: 50,
    });
    
    if (!result?.memories) return [];
    
    return result.memories.map((m) => ({
      role: (m.content.role as 'user' | 'assistant') || 'user',
      content: String(m.content.content || m.content.text || ''),
      timestamp: m.created_at,
    }));
  }, [apiCall]);
  
  const fetchFacts = useCallback(async (userId: string): Promise<UserFact[]> => {
    const result = await apiCall<{ memories: MemoryEntry[] }>('search', {
      agent_id: userId,
      layer: 'semantic',
      tags: ['fact'],
      limit: 100,
    });
    
    if (!result?.memories) return [];
    
    return result.memories.map((m) => ({
      id: m.id,
      subject: String(m.content.subject || ''),
      predicate: String(m.content.predicate || ''),
      object: String(m.content.object || ''),
      content: m.content,
      learned_at: m.created_at,
    }));
  }, [apiCall]);
  
  const searchMemory = useCallback(async (
    query: string,
    scope?: string
  ): Promise<MemoryEntry[]> => {
    const result = await apiCall<{ memories: MemoryEntry[] }>('search', {
      query,
      layer: scope,
      limit: 20,
    });
    
    return result?.memories || [];
  }, [apiCall]);
  
  const getStats = useCallback(async (): Promise<MemoryStats | null> => {
    return apiCall<MemoryStats>('stats', {});
  }, [apiCall]);
  
  const writeMemory = useCallback(async (
    entry: Partial<MemoryEntry>
  ): Promise<string | null> => {
    const result = await apiCall<{ id: string }>('write', {
      value: entry.content,
      layer: entry.layer || 'session',
      importance: entry.importance || 0.5,
      tags: entry.tags || [],
    });
    
    return result?.id || null;
  }, [apiCall]);
  
  const deleteMemory = useCallback(async (
    scope: string,
    namespace: string,
    key: string
  ): Promise<boolean> => {
    const result = await apiCall<{ status: string }>('delete', {
      scope,
      namespace,
      key,
    });
    
    return result?.status === 'deleted';
  }, [apiCall]);
  
  // User Profile operations
  const getUserProfile = useCallback(async (userId: string): Promise<UserProfile | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(+""+/api/memory/user/$+""+{userId}+""+);
      const result = await response.json();
      if (!result.success) throw new Error(result.error);
      return result.data as UserProfile;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  
  const updateUserProfile = useCallback(async (
    userId: string,
    preferences: Record<string, string | number | boolean>
  ): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(+""+/api/memory/user/$+""+{userId}+""+, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'update_preferences', preferences }),
      });
      const result = await response.json();
      return result.success === true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Episode operations
  const getEpisodes = useCallback(async (
    agentId = 'myca_brain',
    limit = 20,
    eventType?: string
  ): Promise<Episode[]> => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        agent_id: agentId,
        limit: limit.toString(),
        ...(eventType && { event_type: eventType }),
      });
      const response = await fetch(+""+/api/memory/episodes?$+""+{params}+""+);
      const result = await response.json();
      if (!result.success) throw new Error(result.error);
      return result.data?.episodes || [];
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Brain operations
  const getBrainStatus = useCallback(async (): Promise<BrainStatus | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/brain?endpoint=status');
      const result = await response.json();
      if (!result.success) throw new Error(result.error);
      return result.data as BrainStatus;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  
  const getBrainContext = useCallback(async (
    userId: string,
    query = 'general context'
  ): Promise<Record<string, unknown> | null> => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ query });
      const response = await fetch(+""+/api/brain/context/$+""+{userId}?$+""+{params}+""+);
      const result = await response.json();
      if (!result.success) throw new Error(result.error);
      return result.data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Management operations
  const exportMemory = useCallback(async (
    scope: string,
    format: 'json' | 'csv' = 'json'
  ): Promise<Blob | null> => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'export', scope, format }),
      });
      if (!response.ok) throw new Error('Export failed');
      return await response.blob();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);
  
  const cleanupMemory = useCallback(async (
    scope: string,
    olderThanDays: number
  ): Promise<{ deleted: number } | null> => {
    return apiCall<{ deleted: number }>('cleanup', { scope, older_than_days: olderThanDays });
  }, [apiCall]);
  
  return {
    loading,
    error,
    fetchConversations,
    fetchFacts,
    searchMemory,
    getStats,
    writeMemory,
    deleteMemory,
    getUserProfile,
    updateUserProfile,
    getEpisodes,
    getBrainStatus,
    getBrainContext,
    exportMemory,
    cleanupMemory,
  };
}

export default useMemory;
