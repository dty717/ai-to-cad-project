Write a clean, single-file, parametric Fusion 360 Python API script (`adsk.core`, `adsk.fusion`) that creates a brand-new parametric design document in millimeter units, registers top-level driving dimensions as Fusion 360 User Parameters, and builds a complete **Prusa MINI–architecture Z-Carriage, Front X-Motor Mount, Rear Bowden Extruder, and Flush X-Endstop Assembly** compatible with a 3030 Z-axis top mount and an X-axis PnP carriage.

### Key Driving Dimensions (Top-Level Variables & User Parameters)

Define all key dimensions as top-level parametric variables and User Parameters so secondary geometry updates automatically:
- **Z-Axis Interface:** `40.0 mm` center-to-center spacing between dual `8.0 mm` Z-axis smooth rods (with the TR8 leadscrew centered midway at the origin), maintaining a `6.0 mm` clear edge gap from the `30.0 × 30.0 mm` (3030) aluminum extrusion to the inner Z-rod.
- **Dual Z-Axis Linear Bearings (`LM8UU`):** `15.2 mm` bearing cradle diameter and `24.4 mm` pocket length for two stacked `24.0 mm` `LM8UU` bearings per Z smooth rod (`4` bearings total).
- **X-Axis Interface:** `34.0 mm` vertical center-to-center spacing between dual `8.0 mm` X-axis smooth rods, and `11.4 mm` vertical center-to-center spacing for the `6.0 mm` GT2 timing belt runs (`6.8 mm` clearance width) coplanar with the X-axis rods.
- **Overall Carriage Height:** `62.0 mm` symmetric vertically about the X-axis mid-plane (providing solid end shoulders, a central retaining rib between the stacked `LM8UU` bearings, and sufficient bottom wall below the lower X-rod to fully enclose the endstop switch).
- **Front X-Motor Plate Thickness:** `6.0 mm` flat-backed detachable front plate supporting a standard `42.3 mm` NEMA 17 (`17HS4401S`) stepper motor in a `0°` square orientation.
- **X-Endstop Microswitch Envelope:** Standard `19.8 × 6.4 × 10.2 mm` (`KW11` / `SS-5GL`) snap-action microswitch.
- **Hardware Clearances:** Derive standard M3 and M2 clearance bores, socket-head counterbores, and captive square nut (`M3nS`) pocket allowances parametrically from standard fastener sizing.

### Geometric Layout & Relationships

- **Reference Coordinate Alignment:** Center the TR8 leadscrew axis at `(X = 0, Y = 0)` and the vertical mid-plane between the X-axis smooth rods at `Z = 0`. Position the two vertical Z-rods symmetrically along `Y = 0`, with the 3030 extrusion running vertically beside the inner Z-rod separated by the extrusion-to-rod gap (leaving a small running clearance between the Z-carriage edge and the extrusion face).
- **Forward X-Axis Plane:** Offset the vertical XZ plane of the X-axis smooth rods and GT2 belt forward (`-Y`) from the Z-axis centerline so the horizontal blind X-rod sockets clear the Z-axis `LM8UU` cradles and TR8 nut flange completely.
- **Unified Coplanar Outer Envelope:** Align the right side faces (`+X`) of the main Z-carriage, the detachable front motor plate, the bolted rear bearing clamp, the rear extruder body, and the endstop microswitch actuation face flush in one common vertical plane. Keep all carriage and switch features cleanly enclosed within the unified top and bottom horizontal planes with zero protruding ears.
- **Front X-Motor & Rear Extruder Separation:** Mount the X-axis stepper motor on the front (`-Y`) via the detachable plate with its shaft pointing rearward (`+Y`) so the GT2 16T pulley aligns directly in the X-axis belt plane, and mount the Prusa MINI Bowden extruder cleanly on the rear (`+Y`) face of the rear bearing clamp clear of the 3030 extrusion.

### CAD Modeling Workflow (Component Structure)

1. **`Z_Carriage_X_Motor_Mount` (Main Front Carriage Body)**
   - **Base Body & X-Rod Bosses:** Extrude the core carriage block symmetrically in height from the Z-axis split plane (`Y = 0`) forward to the central belt-clearance face, then join upper and lower forward clamping bosses around the upper and lower X-axis rod zones, leaving a recessed central horizontal corridor across the belt and pulley zone.
   - **Dual `LM8UU` Cradles & TR8 Seat:** Cut vertical full-height Z-rod clearance bores and the central TR8 barrel bore. Along both Z-rod axes, cut front semicircular upper and lower `LM8UU` bearing seats separated by a solid central retaining rib and bounded by solid top and bottom retaining shoulders. On the bottom face, cut a semicircular TR8 flange recess plus mounting bores and split-entry `M3nS` nut pockets.
   - **Blind X-Rod Sockets & Pinch Clamps:** From the right face, cut two horizontal blind sockets for the 8 mm X-axis rods stopping before the left wall, cut front rod-seating inspection windows near the blind ends, cut vertical pinch slits from each rod bore out to the top/bottom faces, and cut horizontal front-counterbored M3 clamp bores intersecting top/bottom drop `M3nS` nut pockets.
   - **Flush Front-Open X-Endstop Pocket & Forward Wire Bay:** Below the lower X-rod inside the unified right and bottom envelope, cut a horizontal switch pocket from the right face and open its front face all the way through to the front plate mating plane (eliminating any thin front wall so the flat front plate encloses and retains the switch). Behind the switch pins, cut a wide, tall pin cavity and straight forward (`-Y`) wire channel opening cleanly to the front mating plane and staying clear of the `LM8UU` bearings, lower X-rod, and adjacent nut pockets. Cut two vertical bottom-counterbored M2 mounting holes through the floor of the pocket.
   - **Carriage & Front-Plate Fastener Pockets:** Cut horizontal M3 clamp bores and top/bottom/side-entry `M3nS` nut pockets for the rear bearing clamp and the four corner mounting bolts of the front motor plate, ensuring solid walls separate every pocket from the switch wire channel and pinch slits.

2. **`X_Motor_Front_Plate` (Detachable Front X-Motor Mount)**
   - Extrude a flat-backed rectangular plate flush against the front bosses, spanning the full carriage width and height so its outer edges remain coplanar with the main carriage and its solid lower-right corner caps the front of the microswitch pocket.
   - Centered near the carriage center horizontally and midway vertically between the X-rods, cut a circular pilot/pulley-hub bore and four `0°` NEMA 17 M3 mounting holes counterbored from the rear mating face so bench-installed motor screws sit flush inside the plate.
   - Cut four front-counterbored corner M3 mounting holes aligned to the carriage bosses (clear of the motor body and X-rods), plus a straight-through rectangular wire exit port aligned directly with the switch wire channel and located cleanly underneath the X-motor body.

3. **`Z_Carriage_Rear_Clamp` (Bolted Rear `LM8UU` Cap & Extruder Mount)**
   - Extrude the rear clamping block from the Z-axis split plane (`Y = 0`) rearward, matching the outer width and height of the main carriage.
   - Cut matching rear Z-rod clearance bores, upper and lower semicircular `LM8UU` cradles, the central TR8 barrel arch, and the rear half of the bottom TR8 flange recess with mounting bores and rear-entry nut pockets.
   - Cut rear-counterbored horizontal M3 clamping bores aligned with the front carriage clamp pockets, plus three triangularly spaced M3 mounting bores with top- and side-entry `M3nS` pockets for mounting the rear extruder.

4. **`MINI_Extruder_Assembly` (Rear Bowden Extruder)**
   - **Extruder Housing:** Flush against the rear face of the rear clamp and extending rightward to the unified right plane (while keeping generous clearance from the 3030 extrusion), extrude the extruder body with an upper-right Bowden brass-fitting boss (`M10` pilot bore), a left-facing PTFE filament inlet funnel, a rear stepper mounting recess, an internal gear chamber pocket, a `625ZZ` bearing pocket, and counterbored mounting holes aligned to the rear clamp.
   - **Drivetrain, Idler & Motor:** Model the pivoting idler arm, the 3:1 reduction spur gear and motor pinion inside the gear chamber, and a rear-mounted pancake NEMA 17 stepper motor with pilot boss and shaft extending forward into the pinion.

5. **`X_Endstop_Click_Switch`**
   - Model the `KW11` / `SS-5GL` microswitch seated inside the recessed lower-right pocket with its body flush with the right carriage plane, its M2 mounting holes aligned to the bottom bores, its plunger and spring lever centered on the X-rod plane facing outward (`+X`), and its three terminal pins extending inward into the forward wire bay.

6. **Supporting Reference & Hardware Subcomponents**
   - **`Z_Motion_Reference`:** Model the 3030 T-slot extrusion, dual 8 mm Z-rods, four 24 mm `LM8UU` bearings seated in their cradles, TR8 leadscrew, and bottom-mounted TR8 trapezoidal flange nut.
   - **`X_Motion_Reference`:** Model the two 8 mm X-axis smooth rods seated in the blind sockets, the front-mounted `17HS4401S` NEMA 17 X-motor with rearward shaft, the GT2 16T pulley centered on the belt plane, and the upper/lower horizontal GT2 belt runs.
   - **`Fasteners_Hardware`:** Model all installed fasteners in position: NEMA 17 X-motor bolts, front plate corner bolts and `M3nS` nuts, Z-carriage clamp bolts and `M3nS` nuts, X-rod pinch bolts and `M3nS` nuts, TR8 flange nut bolts and `M3nS` nuts, rear extruder mounting bolts and `M3nS` nuts, and microswitch M2 mounting screws.

### Script Requirements

- Use only closed watertight sketches, clean solid Boolean joins/cuts targeting specific participant bodies, and zero self-intersections or unintended collisions.
- Organize each subassembly in its own named component, activate the root component at the end, fit the viewport, and show a concise completion summary dialog.