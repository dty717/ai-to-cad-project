# CAD tools

This directory contains utility tooling for Fusion 360 workflows and related developer support scripts.

Project-specific CAD generators live in the [`../projects/`](../projects/) directory instead of under `tools/`.

## Tool catalog

| Tool | Description | Status |
| --- | --- | --- |
| [`fusion-mcp-studio`](./fusion-mcp-studio/) | Browser UI for connecting to Fusion 360's MCP server, editing/running Python scripts, discovering local scripts, and viewing screenshots. | Implemented |
| `text-to-screw-generator` | Proposed configurable metric fastener generator. | Planned; no generator files yet |

## Using Fusion MCP Studio

**Requirements:** Autodesk Fusion 360 with its MCP server running on `127.0.0.1:27182`, plus Node.js for the proxy.

1. Start Fusion 360 and enable/start the MCP server that listens on port `27182`.
2. In a terminal, run the proxy from the repository root:

   ```bash
   node tools/fusion-mcp-studio/mcp-http-proxy.js
   ```

3. Open `tools/fusion-mcp-studio/fusion-mcp-studio.html` in a browser.
4. Click **Connect** and use the built-in examples or open/scan a script.

## Running a Fusion modeling tool

Open a tool's script folder in Fusion 360's Scripts and Add-Ins (`Shift+S`), select the script, and click **Run**. Fusion's `adsk` API is available in Fusion 360's scripting environment, not as a standalone Python runtime.
