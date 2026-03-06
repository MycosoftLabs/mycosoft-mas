# GitHub MCP Token Setup for Issue Comments

**Date:** March 2, 2026  
**Purpose:** Configure GitHub MCP so agents can post issue comments automatically (e.g. issue-response-agent thanking reporters).

---

## What Changed

The GitHub MCP in Cursor was switched from **api.githubcopilot.com** (Copilot MCP) to **@modelcontextprotocol/server-github**, which provides the `add_issue_comment` tool and full GitHub API access for issues, PRs, repos, and search.

**Config location:** `C:\Users\admin2\.cursor\mcp.json`

```json
"github": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
  }
}
```

---

## Token Requirements

To **post issue comments** (and other write operations), the token must have:

| Scope       | Purpose                          |
|------------|-----------------------------------|
| `repo`     | Full control of private repos     |
| `public_repo` | Public repos only (if no private) |

### If You Get 403 "Resource not accessible by personal access token"

1. Go to [GitHub Personal Access Tokens](https://github.com/settings/tokens)
2. Create a new token (classic or fine-grained)
3. For classic: check **repo** (or **public_repo** for public-only)
4. For fine-grained: grant **Contents** and **Issues** (Read and Write)
5. Copy the token
6. Update `mcp.json` → `github.env.GITHUB_PERSONAL_ACCESS_TOKEN` with the new value
7. **Restart Cursor** so the MCP reloads

---

## Optional: Use Environment Variable

For better security, store the token in your Windows environment instead of `mcp.json`:

1. Set `GITHUB_PERSONAL_ACCESS_TOKEN` in System or User environment variables
2. Remove the `env` block from the `github` entry in `mcp.json`:
   ```json
   "github": {
     "command": "npx",
     "args": ["-y", "@modelcontextprotocol/server-github"]
   }
   ```
3. The server inherits the parent process env; Cursor passes it to MCP subprocesses
4. Restart Cursor

---

## Verification

After restarting Cursor:

- The `add_issue_comment` tool should be available
- Agents (e.g. issue-response-agent) can post thank-you comments on fixed issues
- If 403 persists, create a new PAT with `repo` scope per above

---

## Related

- `docs/CURSOR_MCP_AND_EXTENSIONS_FEB12_2026.md` — MCP usage by task
- `.cursor/agents/issue-response-agent.md` — Auto-respond to fixed issues
