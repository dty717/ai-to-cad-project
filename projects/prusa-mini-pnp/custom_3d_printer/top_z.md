Write a clean, single-file, parametric Fusion 360 Python API script (adsk.core,
adsk.fusion) that creates a brand-new design document in millimeter units and
builds a complete 3D Z-axis top mount assembly for a 3030 T-slot printer frame
with dual 8 mm smooth rods and a top-mounted 17HS4401S (NEMA 17) stepper motor.

Key Driving Dimensions (Top-Level Variables)

Define all key dimensions as top-level parametric variables so secondary
geometry updates automatically:

  - Extrusion Mounting Pitch: 22.8 mm square 4-bolt M5 pattern centered on the
    3030 (30×30 mm) aluminum extrusion.
  - Bracket Height: 17 mm.
  - Extrusion-to-Rod Gap: 6 mm clear edge gap from the front face of the 3030
    extrusion to the nearest 8 mm smooth rod.
  - Rod-to-Rod Center Spacing: 40 mm between the two 8 mm smooth rods (with the
    motor and leadscrew centered midway between them).
  - Motor Platform Width: 44 mm (sized to fully support a 17HS4401S NEMA 17
    motor in a 0° square orientation).
  - Leadscrew Clearance Bore: 13 mm diameter through-hole.
  - Motor Mounting Counterbores: 6.4 mm diameter counterbores from the bottom
    face for the four M3 motor bolts.

Geometric Layout & Relationships

  - Center the entire bracket symmetrically about the X = 0 plane.
  - Arrange the features inline from rear (-Y) to front (+Y) along the
    centerline (X = 0): first the 3030 extrusion (whose rear face defines the
    back reference), followed by the inner 8 mm smooth rod, the 17HS4401S motor
    / TR8 leadscrew centered midway between the rods, and the outer 8 mm smooth
    rod.
  - Keep the 17HS4401S motor mounted on the top face (+Z) in a 0° square
    orientation, while the 3030 extrusion, smooth rods, linear bearings, and
    leadscrew extend downward (-Z).

CAD Modeling Workflow

1.  Main Bracket (MINI_z_top)

      - Base Sketch → Extrude: Sketch a symmetric outer profile spanning from
        the rear of the 3030 extrusion to a rounded nose around the outer smooth
        rod:
          - Around the four M5 extrusion holes, create rounded circular lobes
            concentric with each hole (providing a thick, uniform wall around
            the M5 counterbores), connected by a flat back edge flush with the
            extrusion's rear face and slightly recessed side waists just wider
            than the 3030 extrusion.
          - Flare smoothly outward from the front extrusion lobes into the 44 mm
            wide rectangular motor platform extending far enough forward to
            support all four corners of the 17HS4401S motor.
          - Cap the front end with a circular nose arc concentric with the outer
            8 mm rod (with generous wall thickness), joined smoothly by lines
            tangent from the sides of the motor platform.
      - Extrude upward by the bracket height (17 mm) and apply vertical corner
        fillets along the waist transitions, flare corners, and motor shoulders,
        plus a small polish fillet around the top outer perimeter.
      - Cut Blind Smooth Rod Sockets: On the bottom face, cut two blind circular
        sockets sized for a snug slip fit on the 8 mm smooth rods, leaving a
        solid roof underneath the top-mounted motor so the rods cannot poke
        through the top face.
      - Cut Motor Pilot Pocket, Leadscrew Bore & Motor Fasteners:
          - On the top face centered midway between the rods, cut a shallow
            circular pilot pocket sized for the 17HS4401S pilot boss, then cut
            the 13 mm leadscrew clearance bore all the way through the bracket.
          - Using the standard 0° square NEMA 17 bolt pattern symmetric around
            the motor center, cut four M3 clearance through-holes and
            counterbore them from the bottom face using the 6.4 mm head
            diameter, leaving a thick top flange for M3 bolts threading upward
            into the motor.
      - Cut Extrusion Mounts: From the top face at the four corners of the 22.8
        mm square pattern, cut M5 clearance through-holes and deep socket-head
        counterbores leaving a solid bottom flange for M5 bolts.
      - Cut Top Wire Groove & Drop Slot:
          - On the top face, cut a shallow flat-bottomed wire channel starting
            just in front of the inner smooth rod (leaving a solid wall in front
            of the rod socket), running straight down the centerline between the
            M5 counterbores to the extrusion center, then turning outward to the
            +X side.
          - Cut a full-depth vertical U-shaped drop slot at the +X extrusion
            edge—centered cleanly between the front-right and rear-right M5
            counterbores—so motor wires drop straight down from the top groove
            into the extrusion's +X T-slot.
      - Cut Pinch Clamps & Square Nut Pockets:
          - Cut narrow vertical pinch slits all the way through the bracket
            along the centerline (X = 0) between each smooth rod socket and the
            leadscrew clearance bore.
          - Centered midway between the leadscrew bore and each smooth rod along
            Y, cut horizontal M3 clamp through-holes across the full motor
            platform width, counterbored from the -X side. Place these clamp
            holes at a Z-elevation strictly above the bottom motor-bolt
            counterbores and below the top pilot pocket so there is solid
            material separating all features.
          - On the +X side of the pinch slits, cut vertical blind pockets from
            the bottom face for M3 square nuts (M3nS), positioned outward from
            the centerline and stopping below the pilot pocket so the nuts have
            zero overlap with the pilot pocket, pilot boss, motor bolts, or
            pinch slits.

2.  Supporting Assembly Subcomponents Create each group as a separate Fusion 360
    subcomponent aligned to the bracket:

      - Extrusion_3030: Extrude a standard 30×30 mm T-slot aluminum extrusion
        downward from the bracket's bottom face with four-sided T-slots, a
        central bore, and four M5 tap holes matching the 22.8 mm square pitch.
      - Smooth_Rods_8mm: Extrude two 8 mm cylindrical rods downward starting
        from the top of the bracket's blind sockets.
      - LM8LUU_Bearings: Model two standard LM8LUU linear bearings concentric
        with the rods underneath the bracket/motor zone.
      - NEMA17_17HS4401S_0deg: Model the 17HS4401S NEMA 17 motor body (chamfered
        square footprint in 0° orientation) sitting on the top face, with its
        pilot boss and integrated TR8 leadscrew protruding downward through the
        bracket and four M3 tapped holes on its mounting face.
      - Fasteners_Hardware: Model all fasteners in their installed positions:
        four M3 bolts entering upward from the bottom counterbores into the
        motor, four M5 socket-head bolts entering downward into the extrusion
        corners, two M3 square nuts seated in their pockets, and two horizontal
        M3 clamp screws entering from the -X counterbores across the pinch slits
        through the square nuts.

3.  Script Behavior

      - Ensure every cut and join feature targets existing solid geometry with
        no redundant air cuts or component collisions.
      - Fit the viewport and show a brief completion summary dialog when
        finished.
