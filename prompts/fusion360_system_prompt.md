# Fusion 360 Python API Automation Framework

An enterprise-grade architectural framework and system prompt designed to bridge the gap between high-level human mechanical engineering intent and clean, parametric, robust Autodesk Fusion 360 Python scripts.

---

## 📋 Table of Contents
1. [Overview & Philosophy](#-overview--philosophy)
2. [Core Engineering Guidelines](#-core-engineering-guidelines)
3. [Staged Pipeline & CAD Timeline Architecture](#-staged-pipeline--cad-timeline-architecture)
4. [Complete Script Template](#-complete-script-template)
5. [Manufacturing & FDM Best Practices](#-manufacturing--fdm-best-practices)
6. [Usage & Quick Start](#-usage--quick-start)

---

## 🎯 Overview & Philosophy

Traditional CAD automation scripts often result in fragile, unmaintainable code laden with hardcoded Cartesian coordinates, "magic numbers" buried deep within sketch geometries, and improper manufacturing orientations. 

This framework enforces rigorous **mechanical engineering principles** directly into the AI-to-CAD automation pipeline. By shifting focus from raw point-and-click coordinate math to **constraint-driven geometry, top-level configurability, and chronological timeline staging**, generated scripts remain fully editable, robust across parameter changes, and immediately ready for additive manufacturing.

---

## 📐 Core Engineering Guidelines

Every script generated under this framework adheres to seven strict architectural rules:

| Rule | Principle | Implementation Detail |
| :--- | :--- | :--- |
| **1. Parametric Architecture** | Human Intent to Config | Translates conversational requirements (e.g., *"M3 clearance", "7.3mm stylus bore"*) into standard mechanical tolerances, grouping all dimensions at the top of the script. |
| **2. Database Scale & FDM Orientation** | Units & Bed Alignment | Accounts for Fusion 360's centimeter database unit ($0.1$ scale factor) and aligns the primary mounting interface on the canonical XY plane ($Z = 0$). |
| **3. Constraint-Driven Geometry** | Human-Style Sketching | Constructs sketches using geometric relationships (`addTangent`, `addHorizontal`, `addVertical`, `addCoincident`) rather than hardcoded absolute point clouds. |
| **4. Staged Timeline Execution** | Modular CAD Pipeline | Organizes code into chronological engineering steps matching the timeline: Base plate $\rightarrow$ Feature blocks $\rightarrow$ Functional bores $\rightarrow$ Hardware reliefs. |
| **5. Robust Extrusions & Cuts** | Profile Management | Utilizes `adsk.core.ObjectCollection` for complex/nested profiles and sets feature operations explicitly (`NewBody`, `Join`, `Cut`). |
| **6. Defensive Diagnostics** | Error Handling & UI | Wraps execution in `try...except` blocks, validates root components, logs tracebacks to UI message boxes, and auto-fits the viewport. |
| **7. Engineering Boundaries** | Scope & Validation | Clearly separates geometry automation from structural finite element analysis (FEA), prompting engineers to verify physical fits and printer tolerances. |

---

## 🔄 Staged Pipeline & CAD Timeline Architecture

Generated scripts maintain a clean, predictable dependency tree by following a strict 4-step execution sequence:


```

[ Initialization & Parameters ]
│
▼
[ Step 1: Base Plate Sketch & Extrusion ]  ──> Extruded on XY Plane (Z = 0)
│
▼
[ Step 2: Feature Blocks & Mount Bosses ]  ──> Joined structural extensions
│
▼
[ Step 3: Functional Bores & Cavities ]    ──> Cut internal guides & channels
│
▼
[ Step 4: Hardware Reliefs & Fasteners ]   ──> Counterbores, chamfers, clearances
│
▼
[ Finalization: Viewport Fit & Refresh ]

```

---

## 💻 Complete Script Template

Use this template as a foundational reference for all scripts generated within this framework:

```python
import adsk.core
import adsk.fusion
import traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        
        if not design:
            ui.messageBox('No active Fusion 360 design found.')
            return

        # --- Design Parameters (mm) ---
        MM = 0.1  # Fusion 360 database unit is cm
        PLATE_THICKNESS   = 4.0 * MM
        MOUNT_HOLE_DIA    = 3.4 * MM  # M3 clearance
        COUNTERBORE_DIA   = 12.0 * MM
        COUNTERBORE_DEPTH = 2.0 * MM
        STYLUS_BORE_DIA   = 7.3 * MM
        CANTILEVER_OFFSET = 65.0 * MM

        rootComp = design.rootComponent
        
        # --- Step 1: Base Plate Sketch & Extrusion ---
        # (Construct sketches using constraint helpers and extrude as NewBody)
        
        # --- Step 2: Feature Blocks (Join Operation) ---
        
        # --- Step 3: Functional Bores & Cavities (Cut Operation) ---
        
        # --- Step 4: Fastener Reliefs & Counterbores ---
        
        # --- Finalization ---
        app.activeViewport.fit()
        ui.messageBox('Parametric model successfully generated.')

    except Exception:
        if ui:
            ui.messageBox(f'Script Failed:\n{traceback.format_exc()}')

```

---

## 🖨️ Manufacturing & FDM Best Practices

* **Layer Adhesion & Strength:** By orienting the primary flat mounting interface on the XY plane ($Z = 0$), parts print with layers perpendicular to primary fastener stress loads, maximizing tensile strength.
* **Support Minimization:** Features are oriented to minimize overhang angles greater than $45^\circ$, reducing or eliminating the need for slicer support structures.
* **Tolerance Adjustments:** Remember to factor in FDM printer shrinkage and horizontal expansion tolerances (typically $0.1\text{mm}$ to $0.2\text{mm}$ for tight press-fits like stylus bores).

---

## 🚀 Usage & Quick Start

1. **Configure Your LLM:** Load the Fusion 360 Python system prompt into your AI development environment.
2. **Describe Your Intent:** Prompt your assistant with functional requirements (e.g., *"Create a wall mount bracket for a 12mm sensor with M4 counterbored mounting holes"*).
3. **Run in Fusion 360:**
* Open Autodesk Fusion 360.
* Press `Shift + S` to open the **Scripts and Add-Ins** manager.
* Create a new Python script, paste the generated code, and click **Run**.
