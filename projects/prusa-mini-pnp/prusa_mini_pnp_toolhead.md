Write a clean, parametric **Fusion 360 Python API script** that **creates a new Fusion 360 document first**, defines top-level driving variables and Fusion 360 User Parameters, and builds a complete **Pick-and-Place (PnP) Vacuum Toolhead** conversion for a **Prusa MINI clone** (replacing the broken hotend and fan shroud entirely—no 3D printing hotend or cooling fan).

### Key Driving Dimensions (Top-Level Parametric Variables)
* `rod_spacing = 45.0 mm` (vertical center-to-center distance between the two `8 mm` X-axis smooth rods)
* `lm8uu_od = 15.2 mm`, `lm8uu_len = 24.4 mm` (clearance fit for `2 × LM8UU` linear bearings)
* `carriage_width = 55.0 mm` (overall carriage width, symmetric about the `X = 0` center plane)
* `belt_width = 6.8 mm` (width of a horizontal `6 mm` GT2 timing belt lying flat in `XY`)
* `sensor_dia = 8.0 mm` (cylindrical Z-distance sensor diameter, e.g., SuperPINDA/M.I.N.D.A.)
* `syringe_od = 10.3 mm` (target diameter for the dedicated snap-fit syringe mount)
* `nozzle_od = 8.0 mm` (barrel diameter of the printable vacuum pickup spindle)
* Standard `M3` hardware clearances (clearance holes, counterbores, and captive hex nut pockets)

---

### Geometric Architecture & CAD Workflow (6 Components)

Build each part as a separate component inside the new document, aligned in assembly position (with the optional dedicated syringe mount offset cleanly to the side so nothing overlaps):

1. **`PnP_Carriage_Base`**
   * **Base Body:** Sketch the side profile on the `YZ` plane and extrude symmetrically by `carriage_width`. Include a completely **flat front mounting face (`+Y`)** spanning full height above and below the rods, and a **flat rear belt tower (`-Y`)** centered vertically between the two rods.
   * **Upper Rear Outer Columns:** On the left and right outer edges of the rear face, extrude symmetric mounting columns upward from the belt tower, leaving an open horizontal pass-out arch above the belt shelf for the GT2 belt to exit sideways and staying clear behind the upper smooth rod. The rear faces of these columns sit flush with the flat rear belt-tower face.
   * **Bearings & Rod Slots:** Centered at `X = 0` on the lower and upper rod axes, cut symmetric `LM8UU` snap-in cradles (`lm8uu_len` wide), then cut full-width `8 mm` smooth-rod clearance bores and rear `U`-slots so the carriage snaps onto the rods.
   * **Horizontal GT2 Belt Routing & Slack Exit:** Cut a smooth horizontal lower belt tunnel (`belt_width` wide along `Y`) straight through the carriage for the returning span. On the top horizontal surface of the rear belt tower, cut symmetric left and right GT2-toothed grooves (`belt_width` wide along `Y`, teeth biting vertically in `Z`) separated by a wide open center slot extending to the rear face so excess belt length from an oversized belt exits freely without cutting.
   * **Flexible Belt-Clamp Nut Bays & Variable-Length Screw Bores:** Under the left and right upper belt grooves (behind the lower belt tunnel), cut full-height vertical `M3` through-bores exiting out the bottom of the belt tower so short through extra-long `M3` screws never bottom out. Cut **side-entry flexible captive M3 nut bays** intersecting each vertical bore—taller than a single nut for multi-height/locknut compatibility, with pinched spring-flex entry lips and front stress-relief slots while keeping a thick solid roof above the nut, solid rear wall, and solid outer pillars.
   * **Front & Rear Flat Screw Grids:** On the flat front face (`+Y`), cut a symmetric 4-hole `M3` grid cleared of the `LM8UU` bearings and smooth rods for bolting on syringe mounts. On the flat opposite/rear face (`-Y`), cut a wide 4-hole `M3` grid spanning near the outer edges of the lower belt tower and upper rear columns (widely spaced horizontally and vertically, stopping clear of the lower belt tunnel and nut bays) for rear accessories.
   * **Single Distance Sensor Block (Lower-Right Only):** Flush with the bottom-right front corner of the carriage (only one sensor mount on the entire toolhead), join a solid monolithic gusseted block positioned clear in front of the lower smooth rod and clear to the right of the front syringe mount. Cut a vertical `sensor_dia` bore, a front flex slit, and extend two thick front pinch ears. Through the pinch ears, cut a horizontal `M3` screw bore with a screw-head counterbore on one ear and a recessed 6-sided captive `M3` hex nut pocket on the opposite ear.

2. **`PnP_Belt_Clamp_Left` & `PnP_Belt_Clamp_Right`**
   * Sketch symmetric bridge-clamp profiles on `YZ` planes aligned over the left and right GT2 grooves, spanning from a rear screw foot (flush with the flat rear carriage face) over a stepped belt-pinch rib down to a front fulcrum foot.
   * Extrude symmetrically to straddle each toothed groove while leaving the center belt-exit gap open, then cut vertical `M3` screw holes with deep top counterbores leaving a thin clamping flange so even short `M3` screws engage the nuts.

3. **`PnP_Universal_Flex_Syringe_Mount`**
   * **Flat Base & V-Cradle:** Create a flat-backed rectangular mounting plate flush against the front face of `PnP_Carriage_Base` with a centered vertical 90° V-cradle cut into its front face, and cut the matching 4-hole `M3` mounting pattern with front screw-head counterbores.
   * **Changeable-Syringe Spring Jaws:** At upper and lower levels on both sides of the V-cradle, join symmetric gooseneck compliant spring arms with flared lead-in tips (sized to elastically hug syringe barrels across a wide range of diameters) plus outer side hooks for an optional elastic retention band.
   * **Hose Clip:** Above the upper spring jaw on one side, bridge a small open C-clip guide for routing silicone vacuum tubing (keep no second sensor/camera collar).

4. **`PnP_Sized_Syringe_Mount`**
   * Offset cleanly to the side of the main assembly. Use the exact same flat-backed `4-hole M3` mounting plate and counterbores, join a vertical cylindrical boss on the front centered on `syringe_od`, bore it to `syringe_od` with print clearance, and cut a flared front snap-in throat.

5. **`PnP_Vacuum_Nozzle_Adapter`**
   * Centered inside the V-cradle of `PnP_Universal_Flex_Syringe_Mount`, build stacked coaxial cylinders along `Z`: an `nozzle_od` clamping barrel, a top axial stop collar above the mount, a barbed vacuum-hose stem at the top, a tapered nose at the bottom, a continuous internal vacuum airway through-bore, and a lower Luer-slip socket for blunt SMD needles or suction cups.

Ensure every sketch uses watertight closed profiles, clean solid Boolean joins/cuts, zero self-intersections, and finishes by activating the root component and fitting the viewport.