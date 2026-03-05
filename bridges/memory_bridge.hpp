/**
 * Memory Bridge - C++ header for Mycosoft Memory API
 * Created: March 5, 2026
 * Enables MycoBrain (ESP32/firmware) or C++ services to store/retrieve memory via MAS.
 *
 * Requires: HTTP client (e.g. libcurl, Arduino HttpClient, ESP-IDF esp_http_client)
 * This is a reference interface - implement with your platform's HTTP stack.
 *
 * Example (pseudo):
 *   MemoryBridge bridge("http://192.168.0.188:8001");
 *   bridge.write("device", "mushroom1", "last_reading", "{\"temp\":22.5}");
 *   std::string val = bridge.read("device", "mushroom1", "last_reading");
 */

#ifndef MYCOSOFT_MEMORY_BRIDGE_HPP
#define MYCOSOFT_MEMORY_BRIDGE_HPP

#include <string>
#include <functional>
#include <optional>
#include <cstdio>
#include <cctype>

namespace mycosoft {

enum class MemoryScope {
    conversation,
    user,
    agent,
    system,
    ephemeral,
    device,
    experiment,
    workflow
};

inline const char* to_string(MemoryScope s) {
    switch (s) {
        case MemoryScope::conversation: return "conversation";
        case MemoryScope::user: return "user";
        case MemoryScope::agent: return "agent";
        case MemoryScope::system: return "system";
        case MemoryScope::ephemeral: return "ephemeral";
        case MemoryScope::device: return "device";
        case MemoryScope::experiment: return "experiment";
        case MemoryScope::workflow: return "workflow";
        default: return "user";
    }
}

/**
 * HTTP client callback - implement for your platform.
 * Signature: (method, url, body) -> response_body or empty on error
 */
using HttpRequestFn = std::function<std::optional<std::string>(
    const std::string& method,
    const std::string& url,
    const std::string& body
)>;

class MemoryBridge {
public:
    explicit MemoryBridge(
        const std::string& base_url,
        HttpRequestFn http_fn = nullptr
    )
        : base_url_(rstrip_slash(base_url))
        , http_(std::move(http_fn))
    {}

    /// POST /api/memory/write
    std::optional<std::string> write(
        MemoryScope scope,
        const std::string& ns,
        const std::string& key,
        const std::string& value,
        std::optional<int> ttl_seconds = {}
    ) {
        std::string val_part = (value.empty() || value[0] == '{' || value[0] == '[')
            ? value : ("\"" + escape_json(value) + "\"");
        std::string body = "{\"scope\":\"" + std::string(to_string(scope)) +
            "\",\"namespace\":\"" + escape_json(ns) +
            "\",\"key\":\"" + escape_json(key) +
            "\",\"value\":" + val_part;
        if (ttl_seconds) {
            body += ",\"ttl_seconds\":" + std::to_string(*ttl_seconds);
        }
        body += "}";
        return http_("POST", base_url_ + "/api/memory/write", body);
    }

    /// POST /api/memory/read
    std::optional<std::string> read(
        MemoryScope scope,
        const std::string& ns,
        const std::string& key = ""
    ) {
        std::string body = "{\"scope\":\"" + std::string(to_string(scope)) +
            "\",\"namespace\":\"" + escape_json(ns) + "\"";
        if (!key.empty()) {
            body += ",\"key\":\"" + escape_json(key) + "\"";
        }
        body += "}";
        return http_("POST", base_url_ + "/api/memory/read", body);
    }

    /// POST /api/memory/delete
    std::optional<std::string> remove(
        MemoryScope scope,
        const std::string& ns,
        const std::string& key
    ) {
        std::string body = "{\"scope\":\"" + std::string(to_string(scope)) +
            "\",\"namespace\":\"" + escape_json(ns) +
            "\",\"key\":\"" + escape_json(key) + "\"}";
        return http_("POST", base_url_ + "/api/memory/delete", body);
    }

    /// GET /api/memory/list/{scope}/{namespace}
    std::optional<std::string> list(
        MemoryScope scope,
        const std::string& ns
    ) {
        std::string path = base_url_ + "/api/memory/list/" +
            std::string(to_string(scope)) + "/" + url_encode(ns);
        return http_("GET", path, "");
    }

private:
    std::string base_url_;
    HttpRequestFn http_;

    static std::string rstrip_slash(const std::string& s) {
        if (s.empty() || s.back() != '/') return s;
        return s.substr(0, s.size() - 1);
    }
    static std::string escape_json(const std::string& s) {
        std::string out;
        for (char c : s) {
            if (c == '"') out += "\\\"";
            else if (c == '\\') out += "\\\\";
            else if (c == '\n') out += "\\n";
            else out += c;
        }
        return out;
    }
    static std::string url_encode(const std::string& s) {
        std::string out;
        for (unsigned char c : s) {
            if (std::isalnum(c) || c == '-' || c == '_' || c == '.') out += c;
            else { char buf[4]; snprintf(buf, sizeof(buf), "%%%02X", c); out += buf; }
        }
        return out;
    }
};

}  // namespace mycosoft

#endif  // MYCOSOFT_MEMORY_BRIDGE_HPP
