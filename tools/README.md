# CAD tools

This directory contains self-contained Fusion 360 automation projects. The iPhone automation mount is implemented in [`iphone-automation-mount/`](./iphone-automation-mount/); its Fusion 360 script and sample STL are included.

## Tool catalog

| Tool | Description | Status |
| --- | --- | --- |
| [`iphone-automation-mount`](./iphone-automation-mount/) | Configurable Fusion 360 generator for a phone fixture layout, with printer-bed mount features and clearance cutouts. | Implemented |
| `text-to-screw-generator` | Proposed configurable metric fastener generator. | Planned; no generator files yet |

## Running a tool

Open the tool's script folder in Fusion 360's **Scripts and Add-Ins** (`Shift+S`), select the script, and click **Run**. Fusion's `adsk` API is available in Fusion 360's scripting environment, not ordinary system Python. See each module README for tool-specific notes.

## Development conventions

- Make units explicit and document any conversion from millimeters to Fusion's internal centimeters.
- Prefer stable, parameterized sketch geometry over topology-sensitive edge-index assumptions.
- Keep each tool self-contained and its feature sequence readable.
- Review dimensions, bodies, clearances, and manufacturing constraints before using or exporting a design.
