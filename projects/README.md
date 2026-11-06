# CAD projects

This directory contains the project-specific Fusion 360 design generators and related prompt files, separated from the utility tooling in `tools/`.

## Current structure

The repository is organized around a top-level project folder, with individual design variants grouped underneath it:

- [`iphone-automation-mount/`](./iphone-automation-mount/) — umbrella project for the iPhone automation mount workflow.
  - [`README.md`](./iphone-automation-mount/README.md) — overview and notes for the project.
  - [`iphone-bed-mount/`](./iphone-automation-mount/iphone-bed-mount/) — parametric iPhone bed mount for a Prusa Mini printer.
    - [`iphone-bed-mount.py`](./iphone-automation-mount/iphone-bed-mount/iphone-bed-mount.py) — Fusion 360 generator.
    - [`iphone-bed-mount.stl`](./iphone-automation-mount/iphone-bed-mount/iphone-bed-mount.stl) — example mesh output.
    - [`iphone-bed-mount_PROMPT.md`](./iphone-automation-mount/iphone-bed-mount/iphone-bed-mount_PROMPT.md) — design prompt.
  - [`prusa-mini-stylus-holder/`](./iphone-automation-mount/prusa-mini-stylus-holder/) — stylus holder variations for the Prusa Mini toolhead.
    - [`stylus_holder_standard.py`](./iphone-automation-mount/prusa-mini-stylus-holder/stylus_holder_standard.py) — standard stylus holder generator.
    - [`stylus_holder_standard_PROMPT.md`](./iphone-automation-mount/prusa-mini-stylus-holder/stylus_holder_standard_PROMPT.md) — prompt for the standard holder.
    - [`stylus_holder_offset_65mm.py`](./iphone-automation-mount/prusa-mini-stylus-holder/stylus_holder_offset_65mm.py) — offset variation generator.
    - [`stylus_holder_offset_65mm_PROMPT.md`](./iphone-automation-mount/prusa-mini-stylus-holder/stylus_holder_offset_65mm_PROMPT.md) — prompt for the offset holder.

## Notes

- Keep project-specific CAD files in dedicated project folders rather than under `tools/`.
- Use `tools/` for utilities such as Fusion MCP Studio and other developer support scripts.
- Add a new top-level project folder under `projects/` when a separate design family is introduced, and keep related variants grouped under that project directory.
