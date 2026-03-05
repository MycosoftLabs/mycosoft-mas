/**
 * Memory Bridge - TypeScript client for Mycosoft Memory API
 * Created: March 5, 2026
 * Enables Website (Next.js) to store/retrieve memory via MAS.
 *
 * Usage:
 *   const bridge = new MemoryBridge(process.env.MAS_API_URL || 'http://192.168.0.188:8001');
 *   await bridge.write('user', 'user_123', 'preferences.theme', { dark: true });
 *   const val = await bridge.read('user', 'user_123', 'preferences.theme');
 */

export type MemoryScope =
  | 'conversation'
  | 'user'
  | 'agent'
  | 'system'
  | 'ephemeral'
  | 'device'
  | 'experiment'
  | 'workflow';

export interface MemoryResponse {
  success: boolean;
  scope: string;
  namespace: string;
  key?: string;
  value?: unknown;
  metadata?: Record<string, unknown>;
  timestamp: string;
}

export interface MemoryListResponse {
  success: boolean;
  scope: string;
  namespace: string;
  keys: string[];
  count: number;
}

export class MemoryBridge {
  constructor(
    private baseUrl: string,
    private fetchFn: typeof fetch = fetch
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async request<T>(
    path: string,
    options?: RequestInit & { body?: object }
  ): Promise<T> {
    const url = `${this.baseUrl}/api/memory${path}`;
    const init: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    };
    if (options?.body) {
      init.body = JSON.stringify(options.body);
      delete (init as Record<string, unknown>).body;
    }
    const res = await this.fetchFn(url, init);
    if (!res.ok) {
      throw new Error(`Memory API error ${res.status}: ${await res.text()}`);
    }
    return res.json() as Promise<T>;
  }

  async write(
    scope: MemoryScope,
    namespace: string,
    key: string,
    value: unknown,
    ttlSeconds?: number
  ): Promise<MemoryResponse> {
    return this.request<MemoryResponse>('/write', {
      method: 'POST',
      body: { scope, namespace, key, value, ttl_seconds: ttlSeconds },
    });
  }

  async read(
    scope: MemoryScope,
    namespace: string,
    key?: string,
    semanticQuery?: string
  ): Promise<MemoryResponse> {
    return this.request<MemoryResponse>('/read', {
      method: 'POST',
      body: { scope, namespace, key, semantic_query: semanticQuery },
    });
  }

  async delete(scope: MemoryScope, namespace: string, key: string): Promise<MemoryResponse> {
    return this.request<MemoryResponse>('/delete', {
      method: 'POST',
      body: { scope, namespace, key },
    });
  }

  async list(scope: MemoryScope, namespace: string): Promise<MemoryListResponse> {
    return this.request<MemoryListResponse>(`/list/${scope}/${encodeURIComponent(namespace)}`);
  }

  async health(): Promise<{ status: string }> {
    const res = await this.fetchFn(`${this.baseUrl}/api/memory/health`);
    return res.json() as Promise<{ status: string }>;
  }
}
