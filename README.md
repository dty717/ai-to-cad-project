# ⚡ AI-to-CAD: Parametric B-Rep Generation with Fusion 360

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Autodesk Fusion](https://img.shields.io/badge/Platform-Autodesk%20Fusion-orange.svg)](https://www.autodesk.com/products/fusion-360)
[![Language: Python 3](https://img.shields.io/badge/Language-Python%203-blue.svg)](https://www.python.org/)
[![MCP tooling](https://img.shields.io/badge/Integration-MCP-purple.svg)](./tools/)

> A prompt-driven workflow for translating mechanical requirements into editable Autodesk Fusion models using the native Python API. This repository brings together design prompts, Fusion scripts, example project files, and Fusion MCP Studio tooling.

## Why AI-to-CAD?

Many generative 3D workflows produce triangulated meshes such as `.stl` or `.obj`. Meshes can be useful for visualization and printing, but they are generally less convenient to dimension, constrain, and edit than native CAD geometry.

This project focuses on generating **parametric B-Rep models** in Fusion:

- **Native CAD features:** Build models from Fusion sketches and modeling features rather than treating the result only as a triangle mesh.
- **Editable designs:** Keep the design in Fusion so you can inspect and revise its geometry and feature history.
- **Prompt-guided workflow:** Pair mechanical requirements with Fusion-specific prompt guidance and runnable Python scripts.
- **MCP tooling:** `tools/fusion-mcp-studio` provides a browser UI for connecting to Fusion's MCP server, editing and running scripts, discovering local scripts, and viewing screenshots. See [Tools](./tools/README.md) for setup.

## Workflow

```mermaid
flowchart LR
    A[Mechanical requirements] --> B[Project prompt]
    B --> C[LLM + Fusion system prompt]
    C --> D[Fusion Python script]
    D -->|Run in Fusion| E[Editable parametric model]
    E --> F[Inspect or export as needed]
```

1. **Specify** the requirements, interfaces, dimensions, and constraints in a project prompt.
2. **Generate or adapt** a script using the [Fusion 360 system prompt](./prompts/fusion360_system_prompt.md) as guidance.
3. **Run** the script in Fusion 360's Scripts and Add-Ins environment, or use the MCP tooling described in [`tools/README.md`](./tools/README.md).
4. **Review and iterate** on the resulting design in Fusion.

## Projects

| Project | Prompt | Fusion script | Included artifact / notes |
| --- | --- | --- | --- |
| **iPhone bed mount** | [Prompt](./projects/iphone-bed-mount/iphone-bed-mount_PROMPT.md) | [Script](./projects/iphone-bed-mount/iphone-bed-mount.py) | STL included |
| **Prusa Mini stylus holder — standard** | [Prompt](./projects/prusa-mini-stylus-holder/stylus_holder_standard_PROMPT.md) | [Script](./projects/prusa-mini-stylus-holder/stylus_holder_standard.py) | Prompt and script included |
| **Prusa Mini stylus holder — 65 mm offset** | [Prompt](./projects/prusa-mini-stylus-holder/stylus_holder_offset_65mm_PROMPT.md) | [Script](./projects/prusa-mini-stylus-holder/stylus_holder_offset_65mm.py) | Prompt and script included |
| **iPhone automation mount** | [Project overview](./projects/iphone-automation-mount/README.md) | — | Project documentation |

See [`projects/README.md`](./projects/README.md) for project organization and notes.

## Quickstart: run a Fusion script

### Requirements

- Autodesk Fusion 360
- A project script from this repository

### Run

1. Open Fusion 360.
2. Press **Shift + S** to open **Scripts and Add-Ins**.
3. Add or select the folder containing the script you want to run, for example `projects/iphone-bed-mount/`.
4. Select the script and click **Run**.

These scripts use Fusion's `adsk` API and must run inside Fusion's scripting environment; they are not standalone system-Python programs.

## Fusion API notes

- Fusion's internal database unit for lengths is centimeters. For length values, `ValueInput.createByReal(10)` represents 10 cm—not 10 mm. Use `ValueInput.createByString("25 mm")` when specifying a value with units, or convert millimeters to centimeters when an API call expects an internal-unit number.
- Avoid relying on arbitrary profile indices when selecting sketch regions. Where practical, identify the intended profile from its geometry or location.
- Make script errors visible during development by handling exceptions and reporting useful traceback information in Fusion's UI or log.

For broader prompt and API guidance, see [`prompts/fusion360_system_prompt.md`](./prompts/fusion360_system_prompt.md).

## Fusion MCP Studio

The [`tools/fusion-mcp-studio`](./tools/fusion-mcp-studio/) directory contains a browser UI for working with Fusion's MCP server. The repository's [tools guide](./tools/README.md) documents the requirements and startup steps. In brief, it requires Fusion's MCP server listening on `127.0.0.1:27182` and Node.js for the proxy.

## Repository layout

```text
ai-to-cad-project/
├── projects/
│   ├── README.md
│   ├── iphone-automation-mount/
│   │   └── README.md
│   ├── iphone-bed-mount/
│   │   ├── iphone-bed-mount_PROMPT.md
│   │   ├── iphone-bed-mount.py
│   │   └── iphone-bed-mount.stl
│   └── prusa-mini-stylus-holder/
│       ├── stylus_holder_standard_PROMPT.md
│       ├── stylus_holder_standard.py
│       ├── stylus_holder_offset_65mm_PROMPT.md
│       └── stylus_holder_offset_65mm.py
├── prompts/
│   └── fusion360_system_prompt.md
├── tools/
│   ├── README.md
│   └── fusion-mcp-studio/
├── LICENSE
└── README.md
```

## Contributing

Contributions of new mechanical designs, prompt templates, and tooling improvements are welcome. For a new CAD project, use a dedicated folder under `projects/` and include the design prompt and runnable Fusion script. Add exported artifacts or preview images when available, and document any special setup or limitations.

## License

This project is distributed under the terms of the [MIT License](./LICENSE).
