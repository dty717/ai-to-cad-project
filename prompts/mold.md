Generate a Fusion 360 Python script for a casting mold based on [Part / Dimensions].

Requirements:
1. Mold Style: Open-top container mold (no top lid, poured from above).
2. Number of Pieces: 4-part split (corner quadrants for 45° diagonal demolding).
3. Geometry: 
   - Outer and inner walls at the SAME HEIGHT.
   - Stepped floor to handle wall/lip differences (zero undercuts/overhangs).
   - Hollow/empty center through-hole.
4. Fasteners:
   - Clamped with [M3 / M4] bolts.
   - Include recessed counterbores for screw heads and pockets for nuts.
   - DO NOT draw 3D screws; only model the holes/pockets.
5. API Rule: Use `sketch.modelToSketchSpace()` for any non-XY sketch planes to avoid coordinate mapping errors.