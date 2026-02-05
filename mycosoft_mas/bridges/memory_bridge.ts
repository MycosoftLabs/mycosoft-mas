/**
 * MYCA Memory Bridge - TypeScript Interface
 * Created: February 5, 2026
 * 
 * Provides TypeScript/JavaScript integration with MYCA memory system.
 * Used by: Website, Dashboard, n8n nodes
 */

export interface MemoryEntry {
  id: string;
  layer: 'ephemeral' | 'session' | 'working' | 'semantic' | 'episodic' | 'system';
  content: Record<string, any>;
  metadata?: Record<string, any>;
  importance?: number;
  tags?: string[];
  createdAt?: string;
  accessedAt?: string;
}

export interface MemoryQuery {
  text?: string;
  layer?: string;
  tags?: string[];
  minImportance?: number;
  since?: string;
  limit?: number;
}

export interface MemoryBridgeConfig {
  apiUrl: string;
  apiKey?: string;
  timeout?: number;
}

export class MYCAMemoryBridge {
  private config: MemoryBridgeConfig;

  constructor(config: MemoryBridgeConfig) {
    this.config = {
      apiUrl: config.apiUrl || 'http://localhost:8000',
      timeout: config.timeout || 5000,
      ...config
    };
  }

  async remember(
    content: Record<string, any>,
    layer: MemoryEntry['layer'] = 'session',
    options?: { importance?: number; tags?: string[] }
  ): Promise<string> {
    const response = await fetch(`${this.config.apiUrl}/api/memory/remember`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      },
      body: JSON.stringify({
        content,
        layer,
        importance: options?.importance ?? 0.5,
        tags: options?.tags ?? []
      })
    });
    
    const result = await response.json();
    return result.id;
  }

  async recall(query: MemoryQuery): Promise<MemoryEntry[]> {
    const response = await fetch(`${this.config.apiUrl}/api/memory/recall`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      },
      body: JSON.stringify(query)
    });
    
    const result = await response.json();
    return result.memories;
  }

  async forget(entryId: string, hardDelete: boolean = false): Promise<boolean> {
    const response = await fetch(`${this.config.apiUrl}/api/memory/forget/${entryId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      },
      body: JSON.stringify({ hardDelete })
    });
    
    return response.ok;
  }

  async getStats(): Promise<Record<string, any>> {
    const response = await fetch(`${this.config.apiUrl}/api/memory/stats`, {
      headers: {
        ...(this.config.apiKey && { 'Authorization': `Bearer ${this.config.apiKey}` })
      }
    });
    
    return response.json();
  }
}

// Default export for easy use
export default MYCAMemoryBridge;
