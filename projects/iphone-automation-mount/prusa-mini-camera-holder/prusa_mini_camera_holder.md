Write a complete, robust, and parametric Autodesk Fusion 360 Python API script
that generates a single-piece, support-free 3D printable webcam mount for the
Prusa MINI/MINI+. The part mounts directly over the inverted top Z-axis stepper
motor and cantilevers outward to hold a compact webcam pointing straight down at
the print bed.

Key Driving Dimensions (Declare as top-level editable variables in mm)

  - Motor Socket: Fits a standard NEMA 17 stepper motor (42.6 mm width/height
    across flats, 4.0 mm corner chamfers, 20.0 mm sleeve depth, 2.5 mm wall and
    ceiling thickness).
  - Motor Wire Slot: 15.0 mm wide pass-through channel.
  - Arm Center-to-Center Offsets: 156.0 mm along the X-axis and 76.0 mm along
    the Y-axis from the motor center to the camera cradle center.
  - Arm Cross-Section: 18.0 mm beam width, 9.0 mm thickness, reinforced with a
    15.0 mm diagonal gusset at the inside elbow.
  - Camera Pocket: Fits a compact webcam head (57.5 mm inner width, 37.5 mm
    inner depth, 22.0 mm wall height, 2.8 mm wall thickness, 2.5 mm floor
    thickness).
  - Lens & LED Optical Window: 44.0 mm wide × 24.0 mm deep opening centered in
    the cradle floor.
  - Camera Cable Notch: 12.0 mm wide cutout on the cradle rear wall.

Geometric Relationships & Layout

1.  Coplanar Print Base (Z = 0): The bottom rim of the motor cap, the underside
    of the entire arm, and the bottom face of the camera cradle floor must share
    the exact same Z = 0 plane so the part prints completely flat on the build
    plate with zero supports.
2.  Motor Orientation: The NEMA 17 socket is centered at the origin (0, 0) and
    rotated 45^\circ around the Z-axis (diamond profile) to match the Prusa MINI
    Z-top bracket. The 4 flat faces are oriented diagonally, with corner
    chamfers aligned to the cardinal axes.
3.  Motor Wire Channel: The wire relief slot must be centered exactly in the
    middle of the bottom-left diagonal flat face (cutting completely through the
    wall and ceiling) so the motor harness can slide in without unplugging. The
    adjacent corner chamfers must remain untouched.
4.  Arm Path & Cradle Interface:
      - The arm originates rooted inside the +X corner of the motor cap outer
        shell and extends along +X to the X-offset distance.
      - It turns 90^\circ along +Y toward the Y-offset distance.
      - Crucial Boundary Condition: The arm must stop flush against the exterior
        front wall of the camera cradle. It must never intrude into or cross the
        inner camera pocket or floor.
      - The interior 90^\circ corner of the elbow must be bridged with a
        45^\circ diagonal reinforcing gusset to suppress cantilever vibration.
5.  Camera Cradle ("Face to Bed"):
      - Centered at the target (X, Y) offset coordinates.
      - The cradle floor sits at Z = 0, with perimeter walls extending upward
        along +Z. The webcam drops into the open top so its lens points directly
        straight down along -Z.
      - The optical window cuts through the floor, leaving a uniform perimeter
        ledge to support the camera body while giving the lens and built-in LEDs
        an unobstructed view of the bed.
      - The rear wall features the 12.0\text{ mm} cable exit notch.

Human CAD Modeling Workflow

Structure the script to execute features in this exact logical order to prevent
geometry overlap bugs:

1.  Additive Phase (All Joins First):
      - Step 1 (Outer Cap): Sketch the 45^\circ-rotated 8-sided outer motor
        profile on the XY plane (Z = 0) and extrude upward by the total cap
        height (cap_depth + roof_thickness) as a new solid body.
      - Step 2 (Arm): Sketch the coplanar L-shaped arm profile (including the
        inside diagonal gusset) on the XY plane. Extrude upward by the arm
        thickness using a Join operation into the cap.
      - Step 3 (Cradle Floor): Sketch the outer rectangular perimeter of the
        camera cradle on the XY plane centered at the target offset. Extrude
        upward by the cradle floor thickness using Join.
      - Step 4 (Cradle Walls): Sketch the outer and inner pocket boundaries on
        the top face of the cradle floor. Extrude the perimeter wall upward by
        the cradle wall height using Join.
2.  Subtractive Phase (Cuts & Hollows):
      - Step 5 (Motor Cavity Cut): Sketch the 45^\circ-rotated 8-sided inner
        motor profile on the XY plane. Extrude upward as a Cut by the motor
        sleeve depth. (Cutting after joining the arm guarantees zero plastic
        intrudes into the motor socket).
      - Step 6 (Motor Wire Slot Cut): Sketch the wire slot rectangle centered on
        the bottom-left diagonal face. Extrude as a through-all Cut.
      - Step 7 (Socket Entry Relief): Add a 1.2\text{ mm} deep, slightly
        enlarged profile cut at the mouth of the motor socket (Z = 0) to
        eliminate elephant's foot binding.
      - Step 8 (Optical Window Cut): Sketch the rectangular window centered in
        the cradle floor and extrude as a Cut completely through the floor
        thickness.
      - Step 9 (Rear Cable Notch Cut): Sketch the 12.0\text{ mm} notch on the
        top of the cradle rear wall and extrude as a Cut.
      - Step 10 (Zip-Tie Slots): Sketch two small rectangular through-slots
        along the arm beam and cut through the arm thickness for cable
        management.

Script Technical Requirements

  - Write in clean Python using the Autodesk Fusion 360 API (adsk.core,
    adsk.fusion).
  - Automatically handle internal unit conversions (Fusion 360 API requires
    lengths in centimeters, while all exposed top-level variables must be in
    millimeters).
  - Ensure all geometry merges into exactly one continuous solid B-Rep body
    named PrusaMini_Webcam_Mount. Include standard error handling (try/except
    with UI message boxes).
