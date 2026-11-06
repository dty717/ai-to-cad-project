# iPhone Automation Bed Mount Generator

A configurable Autodesk Fusion 360 Python script for generating a phone fixture layout intended for a Prusa Mini-sized printer bed.

## Features in the current script

- iPhone SE2-sized pocket dimensions, with configurable retaining walls.
- Base outline with rear alignment-pin holes and a side arm.
- Optional arm lightening slot.
- Configurable wall openings, homing-clearance cut, and a camera opening.
- Optional floor-grid cutouts that avoid the defined camera keep-out region.
- Sketch-space rounded corners for the grid cutouts and mount/arm transition.

## Files

- [`iphone_automation_mount.py`](./iphone-bed-mount/iphone-bed-mount.py) — Fusion 360 generator.
- [`iphone_automation_mount.stl`](./iphone-bed-mount/iphone-bed-mount.stl) — committed mesh example.

## Run it

1. Open Autodesk Fusion 360.
2. Press `Shift+S` to open **Scripts and Add-Ins**.
3. Add this module folder under **My Scripts** if it is not already available.
4. Select `iphone_automation_mount.py` and click **Run**.
5. Adjust configuration values near the top of the script before running when needed.

The script depends on Fusion 360's `adsk` API and is not a standalone system-Python script.

## Review before use

The dimensions and clearances in the script are design inputs, not verified compatibility or engineering certification. Check the generated model against the actual printer and phone, inspect the features, and update dimensions as needed before use.
