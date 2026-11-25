Write a clean, parametric Fusion 360 Python API script that creates a new parametric document, registers top-level driving dimensions as Fusion 360 User Parameters, and builds a complete Pick-and-Place (PnP) Vacuum Toolhead conversion for a Prusa MINI clone (replacing the hotend and cooling fan entirely) as six separate, assembly-aligned components.

### Key Driving Dimensions (Top-Level Variables & User Parameters)
- `rod_spacing = 34.0 mm` (center-to-center vertical distance between the two 8 mm X-axis smooth rods)
- `lm8uu_od = 15.2 mm`, `lm8uu_len = 24.4 mm` (clearance fit for two LM8UU linear bearings)
- `carriage_width = 55.0 mm` (overall width symmetric about the X = 0 center plane)
- `belt_width = 6.8 mm`, `belt_spacing = 11.4 mm` (width and vertical center-to-center spacing of the horizontal 6 mm GT2 timing belt runs)
- `mount_grid_size = 32.0 mm` (square 32 × 32 mm coaxial front-and-rear M3 accessory grid)
- `sensor_dia = 12.0 mm` (CHE12-4NA-A710 M12 inductive distance sensor outer diameter)
- `syringe_od = 10.3 mm`, `nozzle_od = 8.0 mm` (target barrel diameters for the dedicated snap-fit syringe mount and hollow vacuum pickup spindle)
- Derive standard M3 hardware clearances (clearance bore, counterbore, and captive hex/square nut pocket allowances) parametrically from M3 sizing.

### Geometric Relationships & CAD Workflow (6 Components)

1. **`PnP_Carriage_Base`**
   - **Base Body & Outer Columns:** Sketch the side profile on the central YZ plane and extrude symmetrically by `carriage_width`. Include a completely flat front mounting face, a flat rear belt tower spanning vertically between the upper and lower belt centerlines, upper rear outer columns flanking the central bearing-cap pocket (with an open pass-through arch above the upper belt plane), and lower outer rod cheeks extending rearward around the lower smooth rod with a 45° support-free underside chamfer.
   - **2-Piece Bolted LM8UU Cradles & Closed Full-Circle Smooth Rod Bores:** Centered on the lower and upper rod axes, cut front-half cylindrical LM8UU seats (`lm8uu_len` wide) and rear bearing-cap seating pockets with zero overhanging lip so bearings drop in cleanly. On the outer end walls outside the bearing pockets, cut closed full-circle smooth-rod clearance bores (no rear U-slots), leaving solid wall thickness above, below, and behind both rods.
   - **Symmetric Toothed Upper & Lower GT2 Belt Grooves:** Align both belt channels coplanar in the vertical XZ plane with the LM8UU bearing centerlines. On both the top and bottom horizontal faces of the rear belt tower, cut symmetric left and right GT2-toothed grooves (12 teeth per side biting vertically into the belt), separated by open center excess-belt exit slots extending straight out the rear face, plus full-width pinch channels for the clamp wings.
   - **Flexible Belt-Clamp Nut Bays & Variable-Length Screw Bores:** Inward of the 32 × 32 mm grid and behind the belt runs, cut full-height vertical M3 through-bores between the upper and lower belt planes. Intersect them with straight, uniform-height side-entry flexible captive M3 nut bays featuring pinched spring-flex entry lips and front stress-relief slots sized for multi-height nuts and locknuts.
   - **Front/Rear M3 Grids & Minimal Closest-Face Nut Pockets:** On the flat front face, cut a 4-hole blind syringe-mount M3 clearance pattern (wider in X and shorter in Z than the 32 × 32 mm grid, positioned clear of rods, belts, and adjacent holes) plus a coaxial front-to-rear 32 × 32 mm 4-hole M3 through-pattern (lower row centered cleanly in the solid bridge between the two belt runs; upper row centered cleanly above the upper smooth rod). Cut minimal, locknut-depth captive M3 nut pockets with gentle retention pinches routed from the closest open face (outer side, inner bearing pocket, top face, or open belt-tower arch) for all 8 front holes, all 4 rear 32 × 32 mm holes, and the 4 horizontal bearing-cap mounting bores (top-drop for the upper cap, bottom-drop for the lower cap).
   - **Nozzle-Aligned Distance Sensor Block:** Flush with the bottom-right front corner of the carriage and anchored strictly forward of the smooth rods and X-end idler, join a monolithic gusseted collar centered in Y with the vacuum nozzle centerline (zero Y-offset) and clear to the right of the syringe mount. Bore it vertically for `sensor_dia` clearance, cut an outward flex slit, and add twin pinch ears with a front-facing M3 counterbore and a rear captive hex nut pocket.

2. **`PnP_Upper_Belt_Bearing_Clamp`**
   - Model a symmetric rear cap fitting cleanly between the upper outer columns, uniting an upper semicircular LM8UU bearing seat (with 2 horizontal M3 counterbored clamping holes near the top) with wide forward under-bearing belt-pinch wings, a center excess-belt exit relief underneath, and a rear flange behind the bearing cap containing 2 vertical M3 screw holes with unobstructed top counterbores aligned to the belt-clamp bores.

3. **`PnP_Lower_Bearing_Clamp`**
   - Model the exact vertical mirror of the upper clamp fitting cleanly between the lower outer cheeks, uniting a lower semicircular LM8UU bearing seat (with 2 horizontal M3 counterbored clamping holes near the bottom) with wide forward over-bearing belt-pinch wings, a center excess-belt exit relief above, and a rear flange behind the bearing cap containing 2 vertical M3 screw holes with unobstructed bottom counterbores aligned coaxially with the belt-clamp through-bores.

4. **`PnP_Universal_Flex_Syringe_Mount`**
   - Create a flat-backed rectangular plate flush against the carriage's front face with a centered vertical 90° V-cradle and front-counterbored M3 mounting holes matching the front syringe-mount pattern. Join symmetric upper and lower gooseneck compliant spring jaws with flared tips and outer elastic-band hooks, plus a single open C-clip vacuum hose guide bridged above one upper jaw.

5. **`PnP_Sized_Syringe_Mount`**
   - Offset cleanly to the side of the assembly so no bodies overlap. Reuse the same flat-backed M3-counterbored mounting plate, join a vertical front cylindrical boss, bore it for `syringe_od` clearance, and cut a flared front snap-in throat.

6. **`PnP_Vacuum_Nozzle_Adapter`**
   - Centered coaxially inside the universal mount's V-cradle, build stacked vertical cylinders: a clamping barrel (`nozzle_od`), a lower tapered nose, an upper axial stop collar resting atop the mount, a barbed vacuum hose stem, a continuous internal vacuum airway through-bore, and a lower Luer-slip socket.

### Script Requirements
- Use only watertight closed sketches, clean solid Boolean joins/cuts, and zero self-intersections.
- Organize each part inside its own named component, activate the root component at the end, and fit the viewport.