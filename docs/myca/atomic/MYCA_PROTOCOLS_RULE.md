# MYCA Protocols Rule

**Component**: Cursor rule for A2A, WebMCP, UCP usage  
**Status**: Implemented

## Location

- `.cursor/rules/myca-protocols.mdc`

## Protocol Roles

| Protocol | Use Case |
|----------|----------|
| A2A | Agent-to-agent communication |
| MCP | Tool registration (exa_search, mindex_query) |
| WebMCP | Browser tools on MYCA pages |
| UCP | Commerce, policy, risk |

## Rules

1. A2A for agents; MCP for tools; WebMCP for browser; UCP for commerce
2. Sanitize remote data; HTTPS in production
