# ⚡ AI-to-CAD: Parametric B-Rep 3D via Fusion 360 & MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CAD](https://img.shields.io/badge/CAD-Autodesk%20Fusion%20360-orange.svg)](https://www.autodesk.com/products/fusion-360/)
[![Python](https://img.shields.io/badge/Language-Python%203.x-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-purple.svg)](https://modelcontextprotocol.io/)

> **Bridging Large Language Models to Precision Physical Manufacturing.**  
> Transform natural language prompts into parametric, solid B-Rep CAD models inside Autodesk Fusion 360 using Python API scripting and Model Context Protocol (MCP).

---

## 🎯 The Core Mission: Code-to-CAD Automation

Most "AI-to-3D" systems generate uncalibrated polygon meshes (STLs or NeRFs) that cannot be edited or toleranced for mechanical assembly. 

**This project builds a direct bridge from AI prompts to exact, engineering-grade CAD:**
```text
┌─────────────────────────────────────────────────────────────┐
│                 Natural Language Prompt                     │
│   "Mount iPhone SE2 to Prusa Mini bed, clear homing zone,   │
│    and add a +65mm cantilever stylus holder to heatsink."   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               LLM Agent (Claude, Cursor, GPT)               │
│   - Calculates kinematic offsets, hole spacing & clearances │
│   - Generates deterministic Fusion 360 Python API code      │
└──────────────────────────────┬──────────────────────────────┘
                               │
            Model Context Protocol (MCP) / Script Runner
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Autodesk Fusion 360 Engine                  │
│   - Constructs B-Rep solids, sketches, and extrusions       │
│   - Validates dimensions, volume, and interference          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Physical Manufacturing Output               │
│       .STEP (Universal CAD)  │  .STL / .3MF (3D Printing)    │
└─────────────────────────────────────────────────────────────┘

🤖 Featured Automation System: iPhone Touch-Test Rig

By combining parametric CAD generators, this project converts a standard Prusa
Mini/Mini+ 3D printer into an automated robotic iPhone touchscreen testing
workstation:

       [ Prusa Mini X-Carriage / Hotend ]
                      │
        tools/prusa-mini-stylus-holder
         (Extends +65mm cantilever arm)
                      │
                      ▼
               [ Capacitive Stylus ]
                      │   (Taps / Swipes / Gestures)
                      ▼
              [ iPhone SE2 / 8 / 7 ]
                      │
                      ▲
         tools/iphone-bed-mount
      (Secured to Y-bed alignment pins)
                      │
         [ Prusa Mini Heated Bed ]

🗂️ Tools & Generative Modules Catalog

| Module                                                              | Installation Target          | Description                                                                                                                         | Status                   |
| :------------------------------------------------------------------ | :--------------------------- | :---------------------------------------------------------------------------------------------------------------------------------- | :----------------------- |
| **[`iphone-bed-mount`](./tools/iphone-bed-mount/)**                 | Prusa Mini Bed (Y-Axis)      | Bed fixture with non-overlapping 3×3 weight-saving grid, arm lightening slot, and $90^\circ$ printer homing window.                 | 🟢 **Production**         |
| **[`prusa-mini-stylus-holder`](./tools/prusa-mini-stylus-holder/)** | Prusa Mini Heatsink (X-Axis) | Mounts a $\varnothing 7.3\text{ mm}$ stylus to the hotend carriage with a $+65\text{ mm}$ cantilever extension to reach the screen. | 🟢 **Production**         |
| **[`text-to-screw-generator`](./tools/text-to-screw-generator/)**   | Fasteners / Hardware         | Generates metric/imperial machine screws directly from text descriptions (e.g. `"M3x16 button head"`).                              | 🟡 **Active Development** |

🚀 Quickstart: Running in Fusion 360

1.  Clone the repository:
    `git clone https://github.com/dty717/ai-to-cad-project.git`
2.  Open Autodesk Fusion 360.
3.  Press `Shift + S` to open **Scripts and Add-Ins**.
4.  Click the green **+** (Add) icon under **My Scripts**.
5.  Select either generator folder:
      - `tools/iphone-bed-mount/`
      - `tools/prusa-mini-stylus-holder/`
6.  Select the script and click **Run**. The model will generate in your active canvas.

📐 AI-to-CAD Engineering Rules

When prompting an LLM to generate code for Fusion 360:

1.  **Internal Units:** Fusion 360 stores lengths in centimeters. Scripts must define `mm = 0.1` and multiply all millimetric inputs by `mm`.
2.  **Stable Geometry:** Avoid brittle topological edge references for fillets. Model transitions with mathematically calculated tangent circular arcs in sketch space.
3.  **Additive-First Sequence:** Create the main body footprint first, join bosses/walls, and then apply subtractive cuts.

📄 License

Distributed under the MIT License.
