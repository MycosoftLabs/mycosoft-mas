/**
 * MYCA Memory Bridge - C# Interface
 * Created: February 5, 2026
 * 
 * Provides C# integration with MYCA memory system.
 * Used by: Unity, Windows Services, .NET applications
 */

using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace Mycosoft.MYCA.Memory
{
    public enum MemoryLayer
    {
        Ephemeral,
        Session,
        Working,
        Semantic,
        Episodic,
        System
    }

    public class MemoryEntry
    {
        public string Id { get; set; }
        public MemoryLayer Layer { get; set; }
        public Dictionary<string, object> Content { get; set; }
        public Dictionary<string, object> Metadata { get; set; }
        public float Importance { get; set; }
        public List<string> Tags { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime AccessedAt { get; set; }
    }

    public class MemoryQuery
    {
        public string Text { get; set; }
        public MemoryLayer? Layer { get; set; }
        public List<string> Tags { get; set; }
        public float MinImportance { get; set; }
        public DateTime? Since { get; set; }
        public int Limit { get; set; } = 10;
    }

    public class MYCAMemoryBridge : IDisposable
    {
        private readonly HttpClient _client;
        private readonly string _baseUrl;
        private readonly string _apiKey;

        public MYCAMemoryBridge(string baseUrl = "http://localhost:8000", string apiKey = null)
        {
            _baseUrl = baseUrl;
            _apiKey = apiKey;
            _client = new HttpClient();
            _client.Timeout = TimeSpan.FromSeconds(10);
            
            if (!string.IsNullOrEmpty(apiKey))
            {
                _client.DefaultRequestHeaders.Add("Authorization", $"Bearer {apiKey}");
            }
        }

        public async Task<string> RememberAsync(
            Dictionary<string, object> content,
            MemoryLayer layer = MemoryLayer.Session,
            float importance = 0.5f,
            List<string> tags = null)
        {
            var payload = new
            {
                content = content,
                layer = layer.ToString().ToLower(),
                importance = importance,
                tags = tags ?? new List<string>()
            };

            var json = JsonSerializer.Serialize(payload);
            var response = await _client.PostAsync(
                $"{_baseUrl}/api/memory/remember",
                new StringContent(json, Encoding.UTF8, "application/json")
            );

            response.EnsureSuccessStatusCode();
            var result = await JsonSerializer.DeserializeAsync<Dictionary<string, object>>(
                await response.Content.ReadAsStreamAsync()
            );
            return result["id"].ToString();
        }

        public async Task<List<MemoryEntry>> RecallAsync(MemoryQuery query)
        {
            var json = JsonSerializer.Serialize(query);
            var response = await _client.PostAsync(
                $"{_baseUrl}/api/memory/recall",
                new StringContent(json, Encoding.UTF8, "application/json")
            );

            response.EnsureSuccessStatusCode();
            var result = await JsonSerializer.DeserializeAsync<RecallResult>(
                await response.Content.ReadAsStreamAsync()
            );
            return result.Memories;
        }

        public async Task<bool> ForgetAsync(string entryId, bool hardDelete = false)
        {
            var request = new HttpRequestMessage(HttpMethod.Delete, $"{_baseUrl}/api/memory/forget/{entryId}");
            request.Content = new StringContent(
                JsonSerializer.Serialize(new { hardDelete = hardDelete }),
                Encoding.UTF8,
                "application/json"
            );

            var response = await _client.SendAsync(request);
            return response.IsSuccessStatusCode;
        }

        public void Dispose()
        {
            _client?.Dispose();
        }

        private class RecallResult
        {
            public List<MemoryEntry> Memories { get; set; }
        }
    }
}
