# Fusion MCP Studio: MCP handshake and tool discovery

This note documents the initial JSON-RPC exchange used to connect to the Fusion MCP Server Adapter and discover its available tools.

## 1. Initialize the session

### Request (`req1`)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "FusionStudio",
      "version": "1.0.0"
    }
  }
}
```

### Response (`res1`)

```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "capabilities": {
      "resources": {
        "listChanged": false,
        "subscribe": false
      },
      "tools": {
        "listChanged": false
      }
    },
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "MCP Server Adapter",
      "version": "1.0.0"
    }
  }
}
```

The response confirms the negotiated protocol version and reports the server's resource and tool capabilities.

## 2. Discover available tools

### Request (`req2`)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Response (`res2`)

The server returns a `result.tools` array. Each tool entry includes a `name`, `description`, and `inputSchema`. The response provided for this server contains these tools:

| Tool | Purpose |
| --- | --- |
| `fusion_mcp_electronics_read` | Read Fusion Electronics design data, including schematic, board, and library entities. |
| `fusion_mcp_execute` | Execute supported operations in the active Fusion model, such as scripts, document actions, image operations, and presentation generation. |
| `fusion_mcp_read` | Read model information, API documentation, documents, licensing, screenshots, and active command state. |
| `fusion_mcp_update` | Undo or redo the most recent operation in the active document. |

Each tool's `inputSchema` describes the accepted parameters. Consult that schema before calling a tool; the descriptions also document supported operations, requirements, and safety constraints. The full `tools/list` response is intentionally not duplicated here because it includes extensive per-tool documentation and JSON schemas.

## Exchange sequence

Send `initialize` first and inspect the server's response. Then call `tools/list` to retrieve the current tool definitions and schemas. Tool availability and schemas can vary by server version.
