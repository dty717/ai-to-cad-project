# ⚡ AI-to-CAD: Generative Parametric 3D with Fusion 360 & MCP

> **Bridging generative AI and precision manufacturing.** Turn natural-language design requirements into editable, parametric B-Rep CAD models in Autodesk Fusion 360 using Python API scripts and, eventually, a Model Context Protocol (MCP) bridge.

## The idea

Many AI-to-3D workflows produce polygon meshes that are difficult to dimension, edit, or prepare for engineering workflows. This project explores a **code-to-CAD** approach instead:

1. **Describe the design.** Provide geometry, dimensions, fit requirements, and intended use in a prompt.
2. **Generate CAD instructions.** An AI agent reasons about the requirements and produces a deterministic Fusion 360 Python API script.
3. **Build and inspect.** Run the script in Fusion 360 to create native sketches, features, and solid B-Rep geometry.
4. **Edit and export.** Adjust model parameters in CAD and export formats such as STEP, STL, or 3MF as appropriate.

The goal is editable CAD geometry and a repeatable modeling process—not a guarantee that every generated design is safe or ready to manufacture. Validate dimensions, clearances, strength, material, and process-specific tolerances before production.

## Example directions

| Module | Example prompt | Intended result | Status |
| --- | --- | --- | --- |
| `iphone-automation-mount` | “Mount an iPhone SE2 to a Prusa Mini bed, clear the homing zone, reduce mass, and protect ports.” | Parametric fixture concept with a homing clearance and lightweighting features. | Planned |
| `text-to-fastener` | “Create an M3 × 16 socket-head screw with a specified thread standard.” | Parametric fastener geometry with configurable dimensions. | Planned |
| `enclosure-generator` | “Create a snap-fit enclosure for a 50 × 70 mm PCB with M2.5 standoffs.” | Two-part enclosure concept with a lid and board supports. | Planned |

These are project directions and prompts, not claims that the modules or manufacturing validation are already implemented.

## Architecture

```text
Natural-language requirements
              │
              ▼
      LLM / AI agent
  engineering reasoning and
  Fusion 360 script generation
              │
              ▼
       Script runner / MCP
              │
              ▼
       Autodesk Fusion 360
  sketches · features · checks
              │
              ▼
 Editable B-Rep CAD and exports
       STEP · STL · 3MF
```

An MCP server and closed-loop Fusion 360 integration are future work. Until implemented, scripts can be run manually through Fusion 360's Scripts and Add-Ins interface.

## Repository structure

The layout below is the intended project structure; directories will be added as their modules are implemented.

```text
ai-to-cad-project/
├── README.md
├── mcp-server/                    # Planned local bridge to Fusion 360
│   ├── server.py
│   └── fusion_client.py
├── modules/
│   ├── iphone-automation-mount/
│   │   ├── README.md
│   │   └── generate_mount.py
│   ├── text-to-fastener/
│   │   └── generate_fastener.py
│   └── enclosure-generator/
├── prompts/
│   ├── fusion360_system_prompt.md
│   └── engineering_rules.md
└── tests/
```

## Getting started

### Run a script in Fusion 360

Once a module script has been added:

1. Clone this repository.
2. Open Autodesk Fusion 360 and open **Scripts and Add-Ins** (Shift+S).
3. Add the module script and run it.
4. Inspect the resulting feature tree and geometry, then save or export the design.

Fusion 360's API and scripting environment are specific to Fusion 360. A regular system Python interpreter does not provide the Fusion `adsk` API modules.

### MCP workflow (planned)

The intended workflow is to run a local MCP service, connect it to a Fusion 360-side script runner, and let an authorized AI client request model operations. This bridge is not currently included. Any future implementation should validate incoming operations and avoid executing untrusted code without review.

## CAD and engineering conventions

Scripts and generated designs should follow these principles:

- **Make units explicit.** Fusion 360's internal database length unit is centimeters. For millimeter-defined inputs, a conversion helper such as `mm = 0.1` converts millimeters to centimeters; document the units of every parameter and API value.
- **Prefer deterministic feature construction.** Use named parameters and stable sketch geometry. Avoid relying on fragile edge indices for fillets or other topology-dependent operations where possible.
- **Validate generated geometry.** Check that expected bodies and features exist and that the resulting solid has sensible dimensions and volume.
- **Treat manufacturing constraints as process-specific.** Clearances, wall thicknesses, overhangs, fillets, and tolerances depend on material, printer or machine, orientation, load, and intended use. Document assumptions and validate before manufacturing.
- **Keep designs editable.** Use meaningful parameter names and a feature tree that makes expected changes straightforward.

## Roadmap

- [ ] Add and validate a first Fusion 360 parametric module.
- [ ] Add reusable prompts for Fusion 360 API scripting and engineering assumptions.
- [ ] Add automated or in-Fusion checks for dimensions, bodies, and volume.
- [ ] Build a local MCP-to-Fusion 360 bridge with explicit execution safeguards.
- [ ] Add export workflows for STEP and mesh formats.
- [ ] Explore feedback from Fusion 360 errors and model checks to improve generated scripts.

## License

This project is licensed under the [MIT License](LICENSE).
