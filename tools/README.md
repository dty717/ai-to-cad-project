# 🛠️ Parametric CAD Tools

This directory is the home for individual parametric CAD generators, hardware utilities, and design-automation scripts for Autodesk Fusion 360. Each tool lives in its own folder so it can have focused documentation, scripts, presets, and optional exported examples.

> **Project status:** The tools listed here are planned concepts unless their implementation files are present. Generated designs must be reviewed and validated for dimensions, clearances, strength, materials, and manufacturing process before use.

## Tool catalog

| Tool | Category | Input | Description | Status |
| --- | --- | --- | --- | --- |
| [`iphone-automation-mount`](./iphone-automation-mount/) | Jigs and fixtures | Script parameters | Intended to generate a configurable bed-mounted phone fixture with printer clearance requirements. | Planned |
| [`text-to-screw-generator`](./text-to-screw-generator/) | Fasteners | Screw designation and parameters | Intended to generate configurable metric machine-screw geometry, including head styles and drive recesses. | Planned |
| Future tools | Mechanical design | To be determined | Possible additions include enclosures, gears, and other parametric utilities. | Planned |

## Intended layout

```text
tools/
├── README.md
├── iphone-automation-mount/
│   ├── README.md
│   ├── generate_mount.py
│   └── exports/                 # Optional validated sample exports
└── text-to-screw-generator/
    ├── README.md
    ├── generate_screw.py
    └── presets.json
```

This is the target organization; folders and files should be added as each tool is implemented. Shared CAD helpers, if needed, belong in the repository-level `utils/` directory.

## Running a Fusion 360 script

After a tool's script has been implemented:

1. Open Autodesk Fusion 360 and open **Scripts and Add-Ins** (Shift+S).
2. Add the tool's folder under **My Scripts**.
3. Select its Fusion 360 script and click **Run**.
4. Review the generated feature tree and geometry, adjust parameters, and export as appropriate.

Fusion 360's `adsk` API is available in Fusion 360's scripting environment; a regular system Python interpreter does not provide those modules. Follow the setup requirements for the installed Fusion 360 version.

## Development conventions

- **Make units explicit.** Fusion 360's internal database length unit is centimeters. For millimeter-defined inputs, a conversion helper such as `mm = 0.1` converts millimeters to centimeters. Document parameter units and conversions.
- **Prefer deterministic geometry.** Use named parameters and stable sketch geometry. Avoid fragile reliance on edge indices for fillets or other topology-dependent operations where practical.
- **Keep each tool self-contained.** Include a tool-specific README, script, configuration or presets where applicable, and usage instructions.
- **Validate before export or manufacture.** Check expected dimensions, bodies, and geometry. Evaluate fit, strength, material, and process-specific tolerances for the intended application.
- **Keep models editable.** Use meaningful parameter names and a clear, maintainable Fusion 360 feature tree.

## AI-assisted workflow direction

These tools may be generated or adapted with AI from natural-language requirements, then reviewed and run in Fusion 360. A local MCP bridge and direct text-to-model workflow are future work; no MCP server is provided here yet. Do not execute unreviewed generated code.
