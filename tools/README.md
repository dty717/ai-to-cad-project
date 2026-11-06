# CAD tools

This directory contains self-contained Fusion 360 automation projects. The iPhone automation mount is implemented in [`iphone-automation-mount/`](./iphone-automation-mount/). The browser-based Fusion MCP client and its local HTTP proxy are in [`fusion-mcp-studio/`](./fusion-mcp-studio/).

## Tool catalog

| Tool | Description | Status |
| --- | --- | --- |
| [`iphone-automation-mount`](./iphone-automation-mount/) | Configurable Fusion 360 generator for a phone fixture layout, with printer-bed mount features and clearance cutouts. | Implemented |
| [`fusion-mcp-studio`](./fusion-mcp-studio/) | Browser UI for connecting to Fusion 360's MCP server, editing/running Python scripts, discovering local scripts, and viewing screenshots. | Implemented |
| `text-to-screw-generator` | Proposed configurable metric fastener generator. | Planned; no generator files yet |

## Using Fusion MCP Studio

**Requirements:** Autodesk Fusion 360 with its MCP server running on `127.0.0.1:27182`, plus Node.js for the proxy.

1. Start Fusion 360 and enable/start the MCP server that listens on port `27182`.
2. In a terminal, run the proxy from the repository root:

   ```bash
   node tools/fusion-mcp-studio/mcp-http-proxy.js
   ```

   The proxy listens on `http://127.0.0.1:27183` and forwards requests to Fusion's MCP endpoint.
3. Open `tools/fusion-mcp-studio/fusion-mcp-studio.html` in a browser. The endpoint field defaults to `http://127.0.0.1:27183/mcp`; change its path if your Fusion MCP server uses a different endpoint.
4. Click **Connect**. Once connected, use the built-in examples or open/scan a Python script, then click **Run**. Use **Screenshot** to request a view of the current Fusion document.

The UI can execute Python code inside Fusion and can load/run scripts from Fusion's local script folders. Only run code you trust, and review scripts before execution. The proxy is unauthenticated; keep it bound to loopback and do not expose it to a LAN or the public internet. The proxy uses permissive CORS to support browser access, so only use the interface on a trusted local machine.

## Running a Fusion modeling tool

Open a tool's script folder in Fusion 360's **Scripts and Add-Ins** (`Shift+S`), select the script, and click **Run**. Fusion's `adsk` API is available in Fusion 360's scripting environment, not standalone system Python.

## Development conventions

- Make units explicit and document any conversion from millimeters to Fusion's internal centimeters.
- Prefer stable, parameterized sketch geometry over topology-sensitive edge-index assumptions.
- Keep each tool self-contained and its feature sequence readable.
- Review dimensions, bodies, clearances, and manufacturing constraints before using or exporting a design.
