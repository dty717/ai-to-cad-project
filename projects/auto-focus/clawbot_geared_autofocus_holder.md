Create a complete, parametric Fusion 360 Python API script (creating a new parametric millimeter document with top-level driving variables and Fusion 360 User Parameters) to generate a **ClawBot-Mounted NUOXI EC-C100 + MG90S Autofocus Assembly**.

In this design, there is no wall mount: replace the original wall spacer and the HackMakeMod ClawBot's forearm + `Gear-Servo - Claw` assembly with a single integrated geared arm holder (`ClawBot_Arm_Holder`) so the ClawBot keeps a 3-servo configuration (shoulder, elbow, and camera autofocus).

### Key Driving Dimensions (Top-Level Parameters)
- **Webcam Envelope (`NUOXI EC-C100`)**: `56 × 36 × 18 mm` rounded body with a `17 mm` diameter front focus ring.
- **Autofocus Mount**: `4 mm` collar wall thickness; sized for a standard MG90S servo (`22.8 × 12.2 mm` body) and a right-side `VL53L0X` ToF sensor module.
- **Autofocus Gears**: `Module 1.0 mm` involute spur gears (`26` teeth on the focus ring gear, `30` teeth on the MG90S drive gear).
- **Holder Rear Clearance**: `15 mm` open standoff depth behind the mount's rear face so the webcam rear, MG90S servo tail, and wires clear without interference.
- **Integrated ClawBot Forearm**: `14.2 mm` total arm thickness, `38 mm` reach from the holder's rear spine to the elbow pivot center.
- **ClawBot Elbow Gear & Pivot**: `Module 0.8 mm`, `17`-tooth half-circle gear sector (`32`-tooth full-circle pitch equivalent, `5.59 mm` thick) concentric with a `3.2 mm` M3 stepped pivot bore.

### Components & Human CAD Workflow

1. **Reference Mockups (separate components to hide before STL export)**
   - **`Reference_NUOXI_EC_C100`**: Sketch a rounded rectangle for the webcam body → Extrude rearward from the origin plane → Sketch and extrude front bezel, `17 mm` focus ring, three side status LEDs, and bottom swivel neck → Cut the front lens opening.
   - **`Reference_MG90S_Servo`**: Positioned above the webcam at the gear center distance (`Module 1.0`, `26T + 30T`) → Extrude rectangular body, mounting flanges with holes, and spline shaft.
   - **`Reference_ClawBot_Pinion_Z16`**: Sketch and extrude a `Module 0.8 mm`, `16`-tooth spur pinion gear positioned behind and coplanar with the holder's elbow gear sector to verify the 2:1 elbow mesh.

2. **`External_Autofocus_Mount`**
   - **Base Collar & Retaining Tabs**: Sketch rounded outer collar sized around the webcam body plus print tolerance → Extrude rearward → Sketch front retaining tabs along the side edges (clear of the LEDs and focus gear) → Extrude forward.
   - **Clamp Pads, Servo Tower & Sensor Pod**: Add external M3 clamping pads on the left and bottom outer walls → Add a top MG90S servo tower flush with the rear face and supporting the servo flange → Add a side pod on the right wall for the `VL53L0X` sensor → Add four symmetric corner/side mounting ears flush with the rear face.
   - **Cutouts & Fastener Holes**: Cut the open-back webcam through-pocket and bottom swivel-neck relief slot → Cut the straight-through MG90S servo slot, two M2 servo flange holes, and two MCU zip-tie slots → Cut the front `VL53L0X` pocket, centered header-wire slot, and two M2 mounting holes → Cut four counterbored M4 mounting holes through the four rear ears → Cut M3 clamp pilot holes into the left and bottom clamp pads.

3. **`Focus_Ring_Gear_Z26` & `Servo_Drive_Gear_Z30`**
   - **`Focus_Ring_Gear_Z26` (Coaxial with Webcam Focus Ring)**: Sketch root circle → Extrude gear blank → Sketch single `Module 1.0 mm` involute tooth → Extrude and Circular Pattern (`26` teeth) → Join a cylindrical clamping hub and radial boss extending toward the webcam face → Cut the center bore to fit the `17 mm` focus ring plus clearance → Cut radial M3 set-screw pilot holes through the clamping hub.
   - **`Servo_Drive_Gear_Z30` (Coaxial with MG90S Shaft)**: Build `30`-tooth `Module 1.0 mm` involute gear coplanar and meshing with the focus gear → Cut a recessed pocket on the rear face for a standard MG90S double-arm servo horn and hub → Cut a central front screw-access hole.

4. **`ClawBot_Arm_Holder` (Replaces Wall Spacer & ClawBot Forearm/Claw)**
   - **Rear Standoff Frame**: Sketch left and right vertical standoff rails aligned with the four mounting ears on `External_Autofocus_Mount`, plus a connecting rear structural spine plate behind the `15 mm` clearance zone → Extrude rails forward to mate flush with the mount's rear ears and extrude the spine at the back → Cut two symmetric vertical cable-routing windows through the spine → Cut a wire-exit channel through the right rail aligned behind the `VL53L0X` wire slot.
   - **Ear Fastening**: Project/align the exact four M4 ear hole centers from `External_Autofocus_Mount` → Cut M4 clearance through-holes through the rails → Cut rear anti-spin M4 hex-nut capture pockets centered on those four holes.
   - **Integrated Geared Forearm (`14.2 mm` thick)**: Sketch a reinforced transition collar centered on the rear spine → Extrude rearward → Sketch the forearm beam and rounded pivot boss extending `38 mm` rearward along the arm centerline in the vertical-longitudinal plane → Extrude symmetrically to `14.2 mm` total thickness → Sketch a `Module 0.8 mm` half-circle root disc and `17`-tooth involute gear sector centered on the elbow pivot (`5.59 mm` thick, flush with one side of the forearm and facing rearward) → Extrude and join to the arm.
   - **Stepped M3 Elbow Pivot Bore**: Create a construction axis through the elbow gear center perpendicular to the arm face → Sketch a closed half-profile on the opposite side of the arm from the gear: an outer frustum cone opening (`~14.15 mm`) with a smooth curved entry lip tapering down to a mid-depth cylindrical counterbore (`~8.2 mm`), stepping down to a `3.2 mm` M3 clearance bore through the back shelf → Revolve Cut `360°` around the pivot axis.

### Script Requirements
- Organize the script into modular functions per component, assign distinct visual colors to printable parts versus mockups, combine multi-feature parts into clean single solid bodies, activate the root component and fit the viewport on completion, and handle errors gracefully via the Fusion 360 UI.