# ⚡ AI-to-CAD: Parametric B-Rep 3D Generation via Fusion 360

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CAD](https://img.shields.io/badge/CAD-Autodesk%20Fusion%20360-orange.svg)](https://www.autodesk.com/products/fusion-360/)
[![Python](https://img.shields.io/badge/Language-Python%203.x-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-purple.svg)](https://modelcontextprotocol.io/)

> **Deterministic AI-to-CAD Automation Framework.**  
> Transform natural language and mechanical requirements into editable, native solid B-Rep CAD models inside Autodesk Fusion 360 using Python API scripting and Model Context Protocol (MCP).

---

## 🎯 Overview

Most AI-to-3D approaches generate uncalibrated polygon meshes (STLs, OBJs) that lack editable sketch geometry, assembly constraints, and parametric timeline history.

This project implements a deterministic code-generation pipeline: an LLM interprets physical requirements and outputs native Autodesk Fusion 360 Python API scripts that construct true parametric B-Rep solids.

```
┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐
│   User Requirements    │ ──►  │    LLM + CAD Rules     │ ──►  │  Fusion 360 API Script │ ──►  │   Native B-Rep Solid   │
│ (Dimensions, Cutouts)  │      │ (Prompt & Constraints) │      │   (Python Automation)  │      │ (Timeline, STEP, 3MF)  │
└────────────────────────┘      └────────────────────────┘      └────────────────────────┘      └────────────────────────┘
```

---

## 🔄 Generative Workflow

1. **Requirement Formulation**  
   Specify the physical bounding envelope, mounting patterns, clearances, and manufacturing tolerances (e.g. wall thickness, bolt spacing, fit offsets).

2. **Prompt Synthesis**  
   Pass the functional requirements alongside strict Fusion 360 API constraints into an LLM (Claude, GPT, Cursor, etc.).

3. **Deterministic Code Generation**  
   The model produces self-contained Python code using the `adsk.fusion` API, building sketches, constraints, and extrusions.

4. **CAD Execution & Export**  
   Run the script inside Fusion 360 (manually or via an MCP bridge) to generate editable geometry with a preserved parametric timeline, ready for `.STEP`, `.STL`, or `.3MF` export.

---

## 🗂️ Included Modules & Generators

| Module | Category | Description | Status |
| :--- | :--- | :--- | :--- |
| **[`tools/iphone-bed-mount`](./tools/iphone-bed-mount/)** | Fixtures | Parametric device cradle featuring weight-saving pocket grids, cable relief channels, and machine homing cutouts. | 🟢 **Stable** |
| **[`tools/prusa-mini-stylus-holder`](./tools/prusa-mini-stylus-holder/)** | Tooling | Cantilever tool-holding clamp adapter for carriage mounting with custom bore diameters. | 🟢 **Stable** |
| **[`tools/text-to-screw-generator`](./tools/text-to-screw-generator/)** | Hardware | Parametric fastener generator producing ISO/metric bolts and screws directly from text descriptions. | 🟡 **Active** |

---

## 📐 AI-to-CAD Engineering Rules

When prompting an LLM to generate code for Autodesk Fusion 360, adhere to these fundamental constraints to avoid broken geometry and API errors:

1. **Internal Units are Centimeters**:  
   Fusion 360 stores lengths internally in centimeters (`cm`). All millimeter measurements must be scaled explicitly:
   ```python
   mm = 0.1  # 1 mm = 0.1 cm
   width = 50.0 * mm
   ```

2. **Avoid Fragile Topological References**:  
   Do not reference edges or faces by index (`faces.item(...)` or `edges.item(...)`), as topology IDs change dynamically across feature rebuilds. Model transitions and fillets directly in **sketch space** using tangent circular arcs.

3. **Additive-First Sequence**:  
   Always build the main solid body first, join mounting bosses or walls, and apply subtractive features (pockets, clearance holes) in subsequent cut operations.

4. **Manufacturing Fit Tolerances**:  
   Include sliding fit clearances (`+0.3 mm` to `+0.4 mm`) on mating pockets and captive hardware slots to account for 3D printer thermal expansion.

---

## 🚀 Quickstart: Running Scripts in Fusion 360

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dty717/ai-to-cad-project.git
   ```

2. **Open Fusion 360**:
   - Press <kbd>Shift</kbd> + <kbd>S</kbd> to open the **Scripts and Add-Ins** dialog.
   - Under the **Scripts** tab, click **+ (Create / Add)** next to *My Scripts*.
   - Browse to any module folder inside `tools/` (e.g., `tools/iphone-bed-mount/`).

3. **Execute**:
   - Select the script and click **Run**.
   - The solid body will build directly in your active design canvas with full timeline history.

---

## 📄 License

Distributed under the [MIT License](./LICENSE).