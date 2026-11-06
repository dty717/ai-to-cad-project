# ⚡ AI-to-CAD: Parametric B-Rep 3D with Fusion 360

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CAD: Autodesk Fusion 360](https://img.shields.io/badge/CAD-Autodesk%20Fusion%20360-orange.svg)](https://www.autodesk.com/products/fusion-360/)
[![Language: Python](https://img.shields.io/badge/Language-Python%203.x-blue.svg)](https://www.python.org/)
[![MCP: roadmap](https://img.shields.io/badge/MCP-roadmap-purple.svg)](https://modelcontextprotocol.io/)

> **Bridging AI-assisted design and physical making.** This project explores a code-first path from natural-language requirements to editable, parametric solid models in Autodesk Fusion 360—using Fusion's Python API today, with MCP integration as a future direction.

---

## 🎯 The vision: AI → code → parametric CAD

Mesh-generation tools can produce compelling shapes, but a mesh alone is not the same as an editable CAD model. This project focuses on scripted geometry and Fusion 360 feature operations so designs can be inspected and revised in the CAD environment.

```text
Design requirements
        ↓
AI-assisted engineering and script authoring
        ↓
Fusion 360 Python API script
        ↓
Editable Fusion 360 features and solid geometry
        ↓
Review, refine, and export for fabrication
```

The repository currently includes a Fusion 360 iPhone bed-mount generator and a generated STL example. An MCP server and automatic prompt-to-model execution are **roadmap items**, not implemented features.

## 🗂️ Tools

| Tool | Input | What it does | Status |
| --- | --- | --- | --- |
| [`iphone-automation-mount`](./tools/iphone-automation-mount/) | Python configuration in the Fusion 360 script | Creates a configurable phone pocket, printer-bed mount features, clearance cutouts, and a camera-aware floor layout. | **Implemented** |
| `text-to-screw-generator` | — | Proposed natural-language-driven metric fastener generator. | **Planned** |
| `enclosure-generator` | — | Proposed configurable electronics enclosure. | **Idea** |

## 🚀 Run the iPhone mount generator

The script uses Fusion 360's `adsk` API and must run inside Fusion 360; a regular Python installation does not include that API.

1. Clone or download this repository.
2. In Fusion 360, open **Scripts and Add-Ins** (`Shift+S`).
3. Add the `tools/iphone-automation-mount/` folder as a script location, then select and run `iphone_automation_mount.py`.
4. Review the generated model and feature tree, and adjust the configuration values near the top of the script as needed.

See the [module notes](./tools/iphone-automation-mount/README.md) for design details and review guidance.

## 🔎 Spotlight: iPhone automation bed mount

The generator targets a Prusa Mini-sized bed layout and an iPhone SE2-sized pocket. Its configurable Fusion 360 script builds a base, retaining walls, alignment-pin holes, an arm slot, button/port and homing-clearance cuts, plus floor cutouts that account for a camera opening. A sample mesh is checked in at [`iphone_automation_mount.stl.stl`](./tools/iphone-automation-mount/iphone_automation_mount.stl.stl).

These are design parameters and intended clearances—not a verified fit or structural certification. Confirm dimensions against your printer and device, inspect the generated model, and validate material, strength, fit, and print settings before use.

## 📐 Fusion 360 scripting conventions

- **Make units explicit.** Fusion 360's internal database length unit is centimeters. For millimeter-defined inputs, `mm = 0.1` converts millimeters to centimeters.
- **Prefer stable geometry.** Use named parameters and sketch geometry; avoid fragile reliance on topology-dependent edge indices where practical.
- **Keep models editable.** Use meaningful parameters and a readable feature sequence.
- **Inspect results.** Check dimensions, bodies, clearances, and intended use before exporting or manufacturing.

For reusable AI authoring guidance, see [`prompts/fusion360_system_prompt.md`](./prompts/fusion360_system_prompt.md).

## 🗺️ Roadmap

- [x] Add a Fusion 360 parametric iPhone mount generator and sample STL.
- [ ] Add reusable prompts and shared CAD helpers.
- [ ] Develop a local, safeguarded MCP bridge for AI-assisted Fusion 360 workflows.
- [ ] Add automated geometry checks and documented STEP/mesh export workflows.
- [ ] Explore text-driven fastener and enclosure generators.

## 📄 License

This project is distributed under the [MIT License](LICENSE).
