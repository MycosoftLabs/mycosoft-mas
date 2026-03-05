// Memory Bridge - C# client for Mycosoft Memory API
// Created: March 5, 2026
// Enables NatureOS (.NET) to store/retrieve memory via MAS.
//
// Usage:
//   var bridge = new MemoryBridge("http://192.168.0.188:8001");
//   await bridge.WriteAsync("user", "user_123", "preferences.theme", new { dark = true });
//   var val = await bridge.ReadAsync("user", "user_123", "preferences.theme");

using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace Mycosoft.MemoryBridge;

public enum MemoryScope
{
    conversation,
    user,
    agent,
    system,
    ephemeral,
    device,
    experiment,
    workflow
}

public record MemoryResponse(
    bool Success,
    string Scope,
    string Namespace,
    string? Key,
    object? Value,
    Dictionary<string, object>? Metadata,
    string Timestamp
);

public record MemoryListResponse(
    bool Success,
    string Scope,
    string Namespace,
    string[] Keys,
    int Count
);

public class MemoryBridge
{
    private readonly HttpClient _http;
    private readonly string _baseUrl;

    public MemoryBridge(string baseUrl, HttpClient? httpClient = null)
    {
        _baseUrl = baseUrl.TrimEnd('/');
        _http = httpClient ?? new HttpClient();
    }

    private async Task<T> RequestAsync<T>(string path, HttpMethod method, object? body = null, CancellationToken ct = default)
    {
        var url = $"{_baseUrl}/api/memory{path}";
        using var req = new HttpRequestMessage(method, url);
        if (body != null)
        {
            req.Content = new StringContent(
                JsonSerializer.Serialize(body),
                Encoding.UTF8,
                "application/json"
            );
        }
        var res = await _http.SendAsync(req, ct);
        res.EnsureSuccessStatusCode();
        var json = await res.Content.ReadAsStringAsync(ct);
        return JsonSerializer.Deserialize<T>(json) ?? throw new InvalidOperationException("Null response");
    }

    public async Task<MemoryResponse> WriteAsync(
        MemoryScope scope,
        string ns,
        string key,
        object value,
        int? ttlSeconds = null,
        CancellationToken ct = default
    )
    {
        var body = new Dictionary<string, object?>
        {
            ["scope"] = scope.ToString(),
            ["namespace"] = ns,
            ["key"] = key,
            ["value"] = value,
            ["ttl_seconds"] = ttlSeconds
        };
        return await RequestAsync<MemoryResponse>("/write", HttpMethod.Post, body, ct);
    }

    public async Task<MemoryResponse> ReadAsync(
        MemoryScope scope,
        string ns,
        string? key = null,
        string? semanticQuery = null,
        CancellationToken ct = default
    )
    {
        var body = new Dictionary<string, object?>
        {
            ["scope"] = scope.ToString(),
            ["namespace"] = ns,
            ["key"] = key,
            ["semantic_query"] = semanticQuery
        };
        return await RequestAsync<MemoryResponse>("/read", HttpMethod.Post, body, ct);
    }

    public async Task<MemoryResponse> DeleteAsync(
        MemoryScope scope,
        string ns,
        string key,
        CancellationToken ct = default
    )
    {
        var body = new Dictionary<string, object>
        {
            ["scope"] = scope.ToString(),
            ["namespace"] = ns,
            ["key"] = key
        };
        return await RequestAsync<MemoryResponse>("/delete", HttpMethod.Post, body, ct);
    }

    public async Task<MemoryListResponse> ListAsync(
        MemoryScope scope,
        string ns,
        CancellationToken ct = default
    )
    {
        var path = $"/list/{scope}/{Uri.EscapeDataString(ns)}";
        return await RequestAsync<MemoryListResponse>(path, HttpMethod.Get, null, ct);
    }

    public async Task<JsonDocument> HealthAsync(CancellationToken ct = default)
    {
        var res = await _http.GetAsync($"{_baseUrl}/api/memory/health", ct);
        res.EnsureSuccessStatusCode();
        return await res.Content.ReadFromJsonAsync<JsonDocument>(ct) ?? throw new InvalidOperationException("Null health");
    }
}
