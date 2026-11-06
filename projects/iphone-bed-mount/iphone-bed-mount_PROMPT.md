Create a parametric Autodesk Fusion 360 Python script named `iphone-bed-mount.py`.

Rather than hardcoding static sketch coordinates, define high-level primary design parameters at the top and calculate all boundaries, offsets, and cutouts relationally through parametric geometry.

### 1. Design Purpose & High-Level Architecture
The goal is to model a single-piece, rigid 3D-printable test automation fixture that mounts an iPhone SE (2nd Gen) directly to the heated bed of a Prusa Mini 3D printer so the phone moves with the printer.

The part consists of three continuous, monolithic regions:
1. Phone Cradle
2. Connecting Side Arm
3. Rear Mount Bar

### 2. Primary Design Parameters
- Printer Bed: 180 × 180 mm build envelope, centered at (0, 0), with a 2.5 mm perimeter safety margin.
- Rear Bed Alignment Pins: dual pins spaced 100 mm apart, symmetric at X = ±50 mm, 3.8 mm pin diameter.
- Phone Dimensions: 139.0 mm × 68.0 mm × ~7.3 mm.
- Structural thicknesses: 4.0 mm base plate, 3.5 mm retaining walls, 8.0 mm wall height, 24.0 mm side arm.

*Note on units: Fusion 360 internally uses centimeters. Set a `mm = 0.1` multiplier and apply it to all dimension values.*
