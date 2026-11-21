Write a clean, well-structured, parametric Autodesk Fusion 360 Python API script that builds a 100% external, wall-mountable motorized autofocus assembly for a cheap webcam (NUOXI EC-C100 style) driven by an MG90S micro servo.

### Global Script & API Requirements
1. **New Document First**: Programmatically create a brand-new Fusion 360 design document set to **millimeters** before creating any geometry, and enable parametric design mode.
2. **Top-Level Driving Variables**: Define clear top-level variables and register key Fusion 360 User Parameters for the essential dimensions:
   - Webcam body profile: **56 mm × 36 mm** (approx. **18 mm** deep), with a **17 mm** diameter protruding manual focus ring.
   - Servo: standard **MG90S** micro servo (**22.8 mm × 12.2 mm** body, **27.6 mm** flange mounting-hole span).
   - Gear train: **1.0 mm** metric module, **20°** pressure angle, **26 teeth** on the focus gear and **30 teeth** on the servo drive gear (**28 mm** center distance).
   - Frame & standoff sizing: **4 mm** collar wall thickness, **15 mm** open-back collar depth, **10.5 mm** thick servo tower, and **15 mm** rear wall-standoff depth.
   - External ToF sensor housing: sized for a **25 mm × 12.5 mm** `VL53L0X` breakout board.
   - Fastener pilot sizes: **M2** (servo and ToF sensor), **M3** (focus gear set-screws and camera-clamping screws), and **M4** (wall-mounting holes).
3. **CAD Reliability Rules**:
   - Activate each new component occurrence while building its sketches and features, then reactivate the root component and fit the viewport at the end.
   - Remember that Fusion 360's internal API uses centimeters (`1 mm = 0.1 cm`) for all coordinates, lengths, and circle radii.
   - Ensure each component forms a single joined solid body before cutting, start cut profiles slightly outside the entry face to avoid coplanar artifacts, and perform cuts via explicit tool-body Combine-Cut operations so every boolean succeeds cleanly.
   - Orient every printable component so it has a completely flat base and prints with zero 3D-printer supports.

### Required Components & Human CAD Workflow

#### 1. `Reference_NUOXI_EC_C100` (Visual Mockup)
- **Base Extrude**: Sketch a rounded rectangle matching the **56 mm × 36 mm** webcam profile centered on the origin, extruding backward from the front XY plane.
- **Front Features**: On the front face, join an outer lens bezel and the **17 mm** protruding focus ring slightly offset to the left of center, a circular snapshot button on the right, and three small vertical LED bumps near the left edge.
- **Neck & Lens**: Join a cylindrical swivel neck stub centered on the bottom face, and cut a recessed optical opening centered inside the focus ring.

#### 2. `Reference_MG90S_Servo` (Visual Mockup)
- **Position**: Centered horizontally with the webcam focus ring and positioned directly above it at the exact gear pitch center distance (**28 mm**), facing forward (`+Z`).
- **Features**: Extrude the rectangular MG90S body, join the wider mounting flange and forward output spline shaft, and cut the two flange mounting holes.

#### 3. `External_Autofocus_Mount` (Support-Free Open-Back External Clip-On Frame)
- **Base Collar**: Sketch an outer rounded perimeter wrapping around the webcam profile offset outward by the **4 mm** wall thickness (plus small fit clearance), extruding **15 mm** backward from the front XY plane so the rear stays completely open for the camera's curved shell, monitor clip, and USB cable.
- **Front Retaining Tabs**: Join thin front retaining lips along the right edge and top-left/bottom-left corners to keep the webcam seated while clearing the three front LEDs and the focus gear.
- **Flush Clamping Pads**: Extrude thickened reinforcement pads flush from the rear print plane along the left side wall and bottom corners.
- **Thick Servo Tower & MCU Shelf**: Join a **10.5 mm** deep solid rectangular bridge extending upward from the top of the collar, flush with the rear face, spanning across to the right edge to provide rigid servo support and an adjacent microcontroller tie-down shelf.
- **External `VL53L0X` Sensor Pod**: Join a forward-facing rectangular pod onto the outside right wall of the collar at lens height, flush with the rear plane and clear of both gears.
- **Four Wall-Mount Ears**: Join four rounded mounting ears flush with the rear plane at the top-left, bottom-left, top-right, and bottom-right outer corners, clear of the clamping pads and sensor pod.
- **Cutouts & Fastener Holes**:
  - Cut the open-back camera through-pocket and an open bottom U-slot for the webcam's swivel neck.
  - Cut a straight-through MG90S servo slot flanked by two **M2** pilot holes, plus two rectangular zip-tie slots on the MCU shelf.
  - Cut the front `VL53L0X` recess in the right-side pod, a centered vertical rear pass-through slot for soldered header pins and wires, and two **M2** pilot holes aligned to standard board spacing.
  - Cut four **M4** wall-mount through-holes with front screw-head counterbores centered in the four corner ears.
  - Cut four horizontal/vertical **M3** pilot holes through the left and bottom clamping pads to lock the collar onto the webcam housing.

#### 4. `Wall_Standoff_Adapter` (15 mm Rear Wall-Clearance Riser)
- **Rails & Crossbar**: Behind and flush with the rear face of `External_Autofocus_Mount`, extrude left and right vertical spacer rails spanning the **15 mm** standoff depth (leaving the entire middle and bottom open for the webcam tail, USB cable, and MG90S body), joined by a top horizontal bridge positioned safely above the servo body.
- **Aligned Holes**: Cut four **M4** through-holes coaxially aligned with the four wall-mount ears on `External_Autofocus_Mount`.

#### 5. `Focus_Ring_Gear_Z26` (Driven Gear with Dual Radial Set-Screws)
- **Base Gear**: Centered on the webcam lens axis and positioned axially in front of the outer bezel, build a **26-tooth** involute spur gear (root cylinder + extruded involute tooth profile circular-patterned around the gear Z axis).
- **Clamping Hub & Dual Screw Bosses**: Join a cylindrical rear clamping collar extending back toward the bezel (outer diameter slightly smaller than the gear root circle) along with two opposing horizontal screw bosses aligned directly behind two opposite gear teeth so the part prints flat gear-face-down without supports.
- **Bore & Set-Screws**: Cut a central through-bore sized for a slip fit over the **17 mm** focus ring, then cut a coaxial radial **M3** pilot hole straight across both bosses at the axial midpoint of the focus ring's protrusion so two opposing **M3** screws clamp the gear firmly onto the ring.

#### 6. `Servo_Drive_Gear_Z30` (Drive Gear with MG90S Horn Pocket)
- **Base Gear**: Centered on the MG90S spline shaft axis in the same axial plane as `Focus_Ring_Gear_Z26`, build a **30-tooth** involute spur gear rotated by half a tooth pitch so its teeth mesh cleanly with the 26-tooth gear.
- **Horn Recess & Screw Access**: From the rear face, cut a rounded-rectangle slot sized to press-fit an MG90S double-arm servo horn and a deeper circular central hub pocket; from the front face, cut a smaller coaxial through-hole for screwdriver access to the center horn retaining screw.