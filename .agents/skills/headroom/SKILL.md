---
name: headroom
description: "Use headroom to compress token usage, optimize context length, manage local caching/proxy servers, and learn from failed agent sessions. Activates when running context optimization, compressing logs/tool output, starting/configuring headroom proxies, or using the headroom CLI."
---

# Headroom Context Optimizer Skill

Headroom is an open-source context compression layer designed to optimize AI agent performance and reduce token usage by 60–95% without compromising answer quality.

## Installation

### Python (Recommended)
Install the package with full features (proxy, MCP tools, and ML compression):
```bash
pip install "headroom-ai[all]"
```
* Core library only: `pip install headroom-ai`
* Proxy server + MCP tools: `pip install "headroom-ai[proxy]"`
* ML-based compression: `pip install "headroom-ai[ml]"`

### Node.js / TypeScript
```bash
npm install headroom-ai
```

---

## Core Features and Usage

### 1. Model Context Protocol (MCP) Server
You can install Headroom as an MCP server to connect it directly to AI coding assistants like Claude Code, Cursor, or Gemini CLI.
```bash
headroom mcp install
```
This exposes the following tools to the agent:
- `headroom_compress`: Compresses logs, JSON structures, AST, or text context.
- `headroom_retrieve`: Recalls the full, uncompressed content from the local Cache (CCR store) if needed by the model.
- `headroom_stats`: Displays current compression ratios and token savings.

Alternatively, register it manually in your `mcp_config.json`:
```json
{
  "mcpServers": {
    "headroom": {
      "command": "npx",
      "args": ["-y", "headroom-ai", "mcp", "start"]
    }
  }
}
```

### 2. Zero-Code Proxy
Run Headroom as a local OpenAI-compatible proxy to intercept and compress API calls transparently.
```bash
headroom proxy --port 8787
```
Then configure your agent's API base URL to `http://localhost:8787/v1`.

### 3. Agent Wrapper
Wrap your CLI coding assistants to automatically intercept their standard outputs and compress them:
```bash
headroom wrap claude
```

### 4. Self-Learning Loop (`headroom learn`)
Analyze failed agent sessions and automatically inject fixes or system prompt corrections into configuration files like `CLAUDE.md` or `AGENTS.md`.
```bash
headroom learn
```

---

## Modality-Aware Compressors
Headroom automatically detects content types to apply optimal compression:
- **Code:** Uses AST-aware tree-sitter compression to strip boilerplate.
- **JSON:** Uses "SmartCrusher" to prune structural redundancies.
- **Logs:** Aggregates recurring patterns and stack traces.
- **RAG Chunks:** Performs semantic deduplication.
