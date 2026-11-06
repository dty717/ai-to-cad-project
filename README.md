# 🛠️ Parametric CAD Toolkit

> **A code-to-CAD toolkit for parametric design and digital fabrication.** This project collects programmatic CAD generators and design-automation scripts for Autodesk Fusion 360, with a path toward AI-assisted workflows and an MCP bridge.

## About

Instead of manually modeling repetitive or configurable parts, the tools in this repository aim to generate editable CAD geometry from scripts and design parameters. The focus is on native Fusion 360 sketches and features, with export to formats such as STEP, STL, and 3MF where supported.

Generated models are design starting points, not guarantees of manufacturing readiness. Verify dimensions, material, clearances, loads, and process-specific tolerances before using a design in production.

## Tools catalog

| Tool | Category | Input | Description | Status |
| --- | --- | --- | --- | --- |
| [`iphone-automation-mount`](./tools/iphone-automation-mount/) | Jigs and fixtures | Script parameters | Planned parametric bed-mounted iPhone fixture concept with printer clearance requirements. | Planned |
| [`text-to-screw-generator`](./tools/text-to-screw-generator/) | Fasteners | Designation and parameters | Planned configurable screw generator for metric sizes and head styles. | Planned |
| `future-tools` | Mechanical design | To be determined | Future ideas may include enclosures, gears, and other parametric utilities. | Planned |

The `tools/` directory is the home for individual projects. A tool should be listed as implemented only after its files and behavior are present and validated.

## Repository structure

```text
ai-to-cad-project/
├── README.md
├── LICENSE
├── tools/
│   ├── README.md
│   ├── iphone-automation-mount/
│   │   ├── README.md
│   │   ├── generate_mount.py
│   │   └── exports/                 # Optional generated examples
│   └── text-to-screw-generator/
│       ├── README.md
│       ├── generate_screw.py
│       └── presets.json
├── utils/                            # Optional shared CAD helpers
├── prompts/                          # Planned reusable AI and engineering prompts
└── tests/                            # Planned validation checks
```

This describes the intended layout. The tool folders and example scripts will be added as they are implemented; exported CAD files are optional and should be generated from validated scripts.

## Quickstart: Fusion 360 scripts

Once a Fusion 360 script has been added to a tool folder:

1. Clone or download this repository.
2. Open Autodesk Fusion 360 and open **Scripts and Add-Ins** (Shift+S).
3. Add the tool's script folder under **My Scripts**.
4. Select the script and click **Run**.
5. Review the resulting feature tree and geometry, adjust parameters, and export as needed.

Fusion 360's `adsk` API is available in its scripting environment; a regular system Python interpreter does not provide those modules. Follow the specific Fusion 360 API setup and requirements for your installed version.

## AI-to-CAD and MCP direction

The long-term workflow is to translate natural-language requirements into reviewed Fusion 360 API operations, run them in Fusion 360, inspect the resulting model, and export the design. A local MCP bridge and automated feedback loop are future work and are not currently provided by this repository. Any execution bridge should validate requests and avoid running untrusted generated code without review.

## Tool development standards

- **Make units explicit.** Fusion 360's internal database length unit is centimeters. For millimeter-defined inputs, a helper such as `mm = 0.1` converts millimeters to centimeters; document the units used by parameters and API values.
- **Prefer deterministic geometry.** Use named parameters and stable sketch geometry. Avoid fragile dependence on edge indices for fillets or other topology-sensitive operations where practical.
- **Keep tools self-contained.** Each tool should include a short README, its script, configuration or presets where needed, and usage instructions.
- **Validate before export.** Check dimensions, expected bodies, and geometry; test fit, strength, and process-specific constraints before manufacturing.
- **Keep designs editable.** Use meaningful parameter names and a clear feature tree.

## Roadmap

- [ ] Add and validate a first parametric Fusion 360 tool.
- [ ] Add reusable prompts and shared helpers for common CAD conventions.
- [ ] Add tests or in-Fusion checks for dimensions, bodies, and volume.
- [ ] Develop a safeguarded local MCP-to-Fusion 360 bridge.
- [ ] Add documented export workflows for STEP and mesh formats.

## License

This project is licensed under the [MIT License](LICENSE).
