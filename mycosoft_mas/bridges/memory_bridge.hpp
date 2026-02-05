/**
 * MYCA Memory Bridge - C++ Interface
 * Created: February 5, 2026
 * 
 * Provides C++ integration with MYCA memory system.
 * Used by: MycoBrain firmware, ESP32 devices, Native applications
 */

#ifndef MYCA_MEMORY_BRIDGE_H
#define MYCA_MEMORY_BRIDGE_H

#include <string>
#include <vector>
#include <map>
#include <memory>

namespace mycosoft {
namespace myca {

enum class MemoryLayer {
    EPHEMERAL,
    SESSION,
    WORKING,
    SEMANTIC,
    EPISODIC,
    SYSTEM
};

struct MemoryEntry {
    std::string id;
    MemoryLayer layer;
    std::map<std::string, std::string> content;
    std::map<std::string, std::string> metadata;
    float importance;
    std::vector<std::string> tags;
    std::string created_at;
    std::string accessed_at;
};

struct MemoryQuery {
    std::string text;
    MemoryLayer layer;
    std::vector<std::string> tags;
    float min_importance;
    std::string since;
    int limit;
    
    MemoryQuery() : layer(MemoryLayer::SESSION), min_importance(0.0f), limit(10) {}
};

class MYCAMemoryBridge {
public:
    MYCAMemoryBridge(const std::string& base_url = "http://localhost:8000",
                     const std::string& api_key = "");
    ~MYCAMemoryBridge();
    
    // Store a memory
    std::string remember(
        const std::map<std::string, std::string>& content,
        MemoryLayer layer = MemoryLayer::SESSION,
        float importance = 0.5f,
        const std::vector<std::string>& tags = {}
    );
    
    // Recall memories
    std::vector<MemoryEntry> recall(const MemoryQuery& query);
    
    // Forget a memory
    bool forget(const std::string& entry_id, bool hard_delete = false);
    
    // Check connection
    bool is_connected();
    
private:
    class Impl;
    std::unique_ptr<Impl> pImpl;
};

// Lightweight version for embedded systems (ESP32)
class MYCAMemoryBridgeLite {
public:
    MYCAMemoryBridgeLite(const char* base_url);
    
    // Simple string-based remember
    bool remember(const char* key, const char* value, float importance = 0.5f);
    
    // Simple string-based recall
    const char* recall(const char* key);
    
private:
    char _base_url[128];
    char _buffer[1024];
};

} // namespace myca
} // namespace mycosoft

#endif // MYCA_MEMORY_BRIDGE_H
