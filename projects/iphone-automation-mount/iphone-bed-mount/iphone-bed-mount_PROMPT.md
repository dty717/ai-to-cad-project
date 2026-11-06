Create a parametric Autodesk Fusion 360 Python script named `iphone-bed-mount.py`. 

Rather than hardcoding static sketch coordinates, define high-level primary design parameters at the top and calculate all boundaries, offsets, and cutouts relationally through parametric geometry.

---

### 1. Design Purpose & High-Level Architecture
The goal is to model a single-piece, rigid 3D-printable test automation fixture that mounts an iPhone SE (2nd Gen) directly to the heated bed of a Prusa Mini 3D printer so the phone moves with the printer's Y-carriage.

The part consists of three continuous, monolithic regions:
1. **Phone Cradle (Front-Left)**: A recessed pocket holding the phone securely facing up/down.
2. **Connecting Side Arm (Right Side)**: A structural arm extending from the right side of the cradle toward the rear of the bed.
3. **Rear Mount Bar (Back Edge)**: A horizontal bar that locates onto the Prusa Mini's rear bed alignment pins.

---

### 2. Primary Design Parameters (Declare at the top)
Define only the core physical dimensions; all other geometry must be derived relationally:
- **Printer Bed**: 180 × 180 mm build envelope, centered at (0, 0), with a 2.5 mm perimeter safety margin.
- **Rear Bed Alignment Pins**: Dual pins spaced 100 mm apart (symmetric at X = ±50 mm), 3.8 mm pin diameter, positioned near the rear edge of the bed.
- **Phone Dimensions (iPhone SE 2)**: 139.0 mm (L) × 68.0 mm (W) × ~7.3 mm (H).
- **Structural Thicknesses**:
  - Base floor plate: 4.0 mm rigid thickness.
  - Cradle retaining walls: 3.5 mm thick, standing 8.0 mm above the base floor (fully shrouding the phone).
  - Side arm width: 24.0 mm.
  - Rear mount bar depth: 18.0 mm (centered over the bed pins).

*Note on Units: Fusion 360 internally uses centimeters (`cm`). Set a global multiplier `mm = 0.1` and apply it to all dimension values.*

---

### 3. Relational Layout & Topology

1. **Phone Cradle Placement**:
   - Nest the cradle in the **front-left corner** of the printer's safe envelope (aligning its outer left and front walls with the minimum safe X and Y bounds).
   - Derive the outer cradle boundary by offsetting the phone dimensions outward by the retaining wall thickness.

2. **Side Arm Transition & Reinforcement**:
   - Place the side arm directly adjacent to the **right outer wall** of the cradle, running along the +Y direction up to the rear mount bar.
   - **Inner Junction**: Keep a crisp 90° orthogonal step between the phone pocket's rear wall and the arm's inner edge.
   - **Rear Junction**: Blend the inner edge of the arm into the bottom edge of the mount bar using a generous **tangent circular fillet arc (R = 10 mm)** to reduce stress concentrations caused by rapid Y-axis bed acceleration.
   - **Outer Rear Corner**: Round the top-right corner where the mount bar meets the outer arm edge with a **90° circular fillet (R = 12 mm)** to maintain clearance within the bed boundary.

3. **Rear Mount Bar & Alignment**:
   - Center the mount bar's Y-position over the printer's bed pin line.
   - Place two 3.8 mm diameter through-holes matching the 100 mm pin spacing.
   - End the left side of the bar just past the left pin with a smooth **180° semi-circular rounded nose** whose diameter matches the mount bar depth.

---

### 4. Functional Clearance & Cutout Relationships

All cutouts should be computed relative to the phone pocket boundaries and printer clearances:

1. **Arm Inertia Reduction (Lightening Slot)**:
   - Cut a central stadium slot (with semi-circular ends) through the arm along the Y axis, spanning from just behind the cradle to just before the mount bar.
   - Size the slot width so it leaves two equal-width structural rails (~7 mm each) on either side of the arm.

2. **Phone Controls & Port Access (Wall Cutouts)**:
   - Cut through the retaining walls completely down to the base floor level:
     - **Lightning Port**: Centered along the pocket's left short wall.
     - **Volume / Mute Switches**: Cutout on the front long wall aligned with the phone's button cluster.
     - **Power Button**: Cutout on the rear long wall aligned with the power switch.

3. **Camera Window**:
   - Create a 42 × 42 mm square through-hole in the base floor at the front-right of the inner pocket floor, directly under the iPhone camera and flash module.

4. **Printer Homing Notch**:
   - Cut a rectangular clearance notch (width matching the arm width, depth ~25 mm) into the bottom-right corner of the base plate to prevent physical interference with the printer's extruder assembly during X-axis homing.

5. **Floor Weight-Reduction Grid**:
   - Hollow out the phone cradle floor using a **3×3 checkerboard grid** of cutouts to reduce weight and print time:
     - Maintain an uninterrupted 5 mm shelf around the inner pocket perimeter to support the phone edges.
     - Separate adjacent cutouts with 5 mm wide internal ribs.
     - Every cutout cell must have filleted corners (R = 3.5 mm) for stress relief (implement a helper function that constructs 4-arc tangent rounded rectangles).
     - **Collision Avoidance**: Programmatically check bounds and skip any grid cell that overlaps with the camera cutout zone or its clearance margin.

---

### 5. CAD Modeling Pipeline & Output
- Build the model sequentially on the XY plane:
  1. Base plate outer profile + alignment pin holes → Extrude New Body (4.0 mm).
  2. Arm lightening slot → Extrude Cut.
  3. Cradle walls sketch on top of base → Extrude Join (8.0 mm).
  4. Wall port cutouts → Extrude Cut.
  5. Printer homing notch → Extrude Cut.
  6. Floor checkerboard grid & camera cutout → Extrude Cut through the floor.
- Wrap execution in a `try...except` block with a dialog message box summarizing the generated body and applied features.
- Save and output the script as `iphone_automation_mount.py`.