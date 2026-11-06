# ⚡ AI-to-CAD: Parametric B-Rep Generation with Fusion 360

> A prompt-driven workflow for turning mechanical requirements into editable Autodesk Fusion 360 models using Python API scripts. The repository includes prompt specifications, runnable scripts, and project examples.

---

## 📂 Repository layout

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
├── README.md
└── .gitignore
```

## 🧩 Modules

| Module | Prompt specification | Fusion 360 script | Available output / status |
| :--- | :--- | :--- | :--- |
| **iPhone bed mount** | [`./projects/iphone-bed-mount/iphone-bed-mount_PROMPT.md`](./projects/iphone-bed-mount/iphone-bed-mount_PROMPT.md) | [`./projects/iphone-bed-mount/iphone-bed-mount.py`](./projects/iphone-bed-mount/iphone-bed-mount.py) | Example STL included in the project folder |
| **Prusa Mini stylus holder — standard** | [`./projects/prusa-mini-stylus-holder/stylus_holder_standard_PROMPT.md`](./projects/prusa-mini-stylus-holder/stylus_holder_standard_PROMPT.md) | [`./projects/prusa-mini-stylus-holder/stylus_holder_standard.py`](./projects/prusa-mini-stylus-holder/stylus_holder_standard.py) | Implemented |
| **Prusa Mini stylus holder — 65 mm offset** | [`./projects/prusa-mini-stylus-holder/stylus_holder_offset_65mm_PROMPT.md`](./projects/prusa-mini-stylus-holder/stylus_holder_offset_65mm_PROMPT.md) | [`./projects/prusa-mini-stylus-holder/stylus_holder_offset_65mm.py`](./projects/prusa-mini-stylus-holder/stylus_holder_offset_65mm.py) | Implemented |

See the [projects directory](./projects/README.md) for project organization and notes.

## 🚀 Quickstart

1. Open Autodesk Fusion 360 and press Shift + S to open Scripts and Add-Ins.
2. Add the folder containing the script you want to run, for example `projects/iphone-bed-mount/`.
3. Select the Python script and click Run.

The scripts use Fusion 360's `adsk` API and must run in Fusion 360's scripting environment; they are not standalone system-Python programs.
