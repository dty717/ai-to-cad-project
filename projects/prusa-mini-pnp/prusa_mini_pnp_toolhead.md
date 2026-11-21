Here is the updated **README / specification** reflecting every change made during our conversation (the `32×32 mm` front & rear grids, the 2-piece bolted `LM8UU` bearing holders, the unified belt + upper bearing clamp, the lower bearing clamp with under-belt hook-tab, and the relocated nozzle-aligned distance sensor holder):

---

# Prusa MINI Clone Pick-and-Place (PnP) Vacuum Toolhead

Write a clean, parametric **Fusion 360 Python API script** that **creates a new Fusion 360 document first**, defines top-level driving variables and Fusion 360 User Parameters, and builds a complete **Pick-and-Place (PnP) Vacuum Toolhead** conversion for a **Prusa MINI clone** (replacing the broken hotend and fan shroud entirely—no 3D printing hotend or cooling fan).

### Key Driving Dimensions (Top-Level Parametric Variables)
* `rod_spacing = 45.0 mm` (vertical center-to-center distance between the two `8 mm` X-axis smooth rods)
* `lm8uu_od = 15.2 mm`, `lm8uu_len = 24.4 mm` (clearance fit for `2 × LM8UU` linear bearings)
* `carriage_width = 55.0 mm` (overall carriage width, symmetric about the `X = 0` center plane)
* `belt_width = 6.8 mm` (width of a horizontal `6 mm` GT2 timing belt lying flat in `XY`)
* `belt_clamp_x = 8.0 mm`, `belt_clamp_y = -16.7 mm` (left/right `M3` belt-clamp screw centerline, shifted inward to clear the `32×32 mm` rear mounting grid)
* `mount_screw_x = 16.5 mm`, `mount_screw_z_lo = 12.5 mm`, `mount_screw_z_hi = 32.5 mm` (`33 × 20 mm` front syringe-mount `M3` grid, clear of both smooth rods and the `32×32 mm` stylus holes)
* `stylus_hole_offset = 16.0 mm`, `stylus_center_z = 22.5 mm` (`32 × 32 mm` stylus holder `M3` through-hole grid at `X = ±16.0 mm`, `Z = 6.5 & 38.5 mm`)
* `rear_mount_x = 16.0 mm`, `rear_mount_z_lo = 6.5 mm`, `rear_mount_z_hi = 38.5 mm` (`32 × 32 mm` rear/bottom `M3` mounting grid aligned coaxially with the stylus through-holes)
* `sensor_dia = 8.0 mm`, `sensor_x = 32.5 mm`, `sensor_y = 22.66 mm`, `sensor_z_mid = -6.5 mm`, `sensor_h = 18.0 mm` (cylindrical Z-distance sensor holder, aligned with the vacuum nozzle `Y = 22.66 mm` for `dY = 0` probe offset)
* `syringe_od = 10.3 mm` (target diameter for the dedicated snap-fit syringe mount)
* `nozzle_od = 8.0 mm` (barrel diameter of the printable vacuum pickup spindle)
* Standard `M3` hardware clearances (`3.4 mm` clearance, `3.2 mm` self-threading/tight pass, `6.2 mm` counterbores, and captive hex nut pockets)

---

### Geometric Architecture & CAD Workflow (6 Components)

Build each part as a separate component inside the new document, aligned in assembly position (with the optional dedicated sized syringe mount offset cleanly to the side at `X = +95 mm` so nothing overlaps):

1. **`PnP_Carriage_Base`**
   * **Base Body:** Sketch the side profile on the `YZ` plane and extrude symmetrically by `carriage_width`. Include a completely **flat front mounting face (`+Y = +13.5 mm`)** spanning `Z = -15.5 mm` to `+60.5 mm` (providing solid upper and lower flanges for the 2-piece bearing caps), and a **flat rear belt tower (`-Y = -23.5 mm`)** spanning `Z = 9.0..30.8 mm` between the two rods.
   * **Upper & Lower Rear Outer Columns:** On the left and right outer edges of the rear face (`|X| = 12.5..27.5 mm`, outside the `24.4 mm` bearing-cap pocket), extrude symmetric upper columns (`Z = 30.6..44.5 mm`, leaving an open pass-out arch above the belt shelf and staying clear behind the upper smooth rod) and lower columns (`Z = 2.0..9.2 mm`, staying clear below the lower bearing cradle). The rear faces of all columns sit flush with `-Y = -23.5 mm`.
   * **2-Piece Bolted LM8UU Cradles & Rod Slots (No Fragile Snap-Fits):** Centered at `X = 0` on the lower (`Z = 0`) and upper (`Z = 45 mm`) rod axes, cut symmetric `LM8UU` front-half cylindrical seats (`lm8uu_len` wide) and cut rear bearing-cap seating pockets (`|X| <= 12.3 mm`) back to `Y = +0.2 mm`—leaving zero overhang so bearings drop in without stressing 3D-printed Z-layers, plus a `0.2 mm` pinch gap for firm clamping. Cut full-width `8 mm` smooth-rod clearance bores (`9.6 mm`) and rear `U`-slots on the outer end walls (`|X| > 12.3 mm`). Cut `M3` self-threading holes in the base for the upper cap (`X = ±6.5 mm, Z = 56.5 mm`), lower cap bottom (`X = ±6.5 mm, Z = -11.5 mm`), and lower cap under-belt hook-tab (`X = 0.0 mm, Z = 13.5 mm`, stopping shy of the lower belt tunnel).
   * **Horizontal GT2 Belt Routing & Slack Exit:** Cut a smooth horizontal lower belt tunnel (`belt_width` wide along `Y`, `Z = 10.6..14.0 mm`) straight through the carriage for the returning span. On the top horizontal surface of the rear belt tower, cut symmetric left and right GT2-toothed grooves (`12` teeth per side, `belt_width` wide along `Y`, teeth biting vertically in `Z`) separated by an open center exit slot (`X = ±3.6 mm`) extending to the rear face so excess belt length exits freely without cutting.
   * **Flexible Belt-Clamp Nut Bays & Variable-Length Screw Bores:** Under the left and right upper belt grooves at `X = ±8.0 mm, Y = -16.7 mm` (behind the lower belt tunnel), cut full-height vertical `M3` through-bores exiting out the bottom of the belt tower (`Z = 8.0..31.5 mm`) so short through extra-long `M3` screws never bottom out. Cut **side-entry flexible captive M3 nut bays** (`|X| >= 4.7 mm`) intersecting each vertical bore—taller than a single nut for multi-height/locknut compatibility, with pinched spring-flex entry lips and front stress-relief slots while keeping a thick solid roof above the nut, solid rear wall, and solid outer pillars.
   * **Front & Rear Flat Screw Grids (`8` Front Holes / `4` Bottom-View `32×32 mm` Holes):**
     * On the flat front face (`+Y = +13.5 mm`), cut **8 M3 holes**: a `33 × 20 mm` 4-hole grid (`X = ±16.5 mm, Z = 12.5 & 32.5 mm`, kept blind from `-Y`) for bolting on syringe mounts, plus a `32 × 32 mm` 4-hole grid (`X = ±16.0 mm, Z = 6.5 & 38.5 mm`, centered at `Z = 22.5 mm`) clear of both smooth rods for a stylus holder.
     * On the flat opposite/rear face (`-Y = -23.5 mm`), cut a matching **`32 × 32 mm` 4-hole M3 grid (`X = ±16.0 mm, Z = 6.5 & 38.5 mm`)** connecting coaxially to the front `32 × 32 mm` holes to form full `+Y` to `-Y` through-holes, so the rear/bottom view presents cleanly as `4` holes spaced `32 mm` apart in both X and Z.
   * **Single Distance Sensor Block (Lower-Right, Nozzle-Aligned):** Flush with the bottom-right front corner of the carriage (`Z = -15.5..+2.5 mm`, `z_sens_mid = -6.5 mm`)—the only sensor mount on the entire toolhead—join a solid monolithic gusseted block anchored strictly at `Y >= 10.0 mm` (completely clear of the Prusa MINI X-end idler and smooth rod) and positioned at `X = 32.5 mm, Y = 22.66 mm` (aligned in `Y` with the vacuum nozzle centerline and clear to the right of the syringe mount). Cut a vertical `sensor_dia` bore, an outward (`+X`) flex slit, and two thick pinch ears with a horizontal `M3` screw bore whose counterbore faces straight forward (`+Y`) and captive 6-sided `M3` hex nut pocket sits on the rear (`-Y`) ear for unobstructed front tightening.

2. **`PnP_Upper_Belt_Bearing_Clamp`** *(Unified Belt Clamp + Upper LM8UU Cap)*
   * Replaces separate left/right clamps with a **single `24.2 mm` wide bridge** (`X = -12.1..+12.1 mm`) sitting cleanly between the upper rear columns.
   * The lower section (`Z = 30.8..36.4 mm`, `Y = -23.5..-3.8 mm`) straddles both left and right GT2 toothed grooves with stepped belt-pinch ribs, a center excess-belt exit relief (`X = ±3.7 mm`) underneath the bridge, and two vertical `M3` screw holes with deep top counterbores (`X = ±8.0 mm, Y = -16.7 mm`) left completely open above `Z = 36.4 mm` for unobstructed vertical screwdriver access.
   * The upper section (`Z = 32.0..60.3 mm`, `Y = -10.5..0.0 mm`) forms the **rear half of the upper `LM8UU` bearing holder** (`Z = 45.0 mm`), bored with a semicircular `lm8uu_od` seat and clamped straight forward (`+Y`) into `PnP_Carriage_Base` via `2 × M3x16` horizontal screws with counterbores at `X = ±6.5 mm, Z = 56.5 mm`.

3. **`PnP_Lower_Bearing_Clamp`** *(Lower LM8UU Cap)*
   * A **`24.2 mm` wide rear cap** (`X = -12.1..+12.1 mm`, `Z = -15.3..+8.8 mm`, `Y = -10.5..0.0 mm`) forming the **rear half of the lower `LM8UU` bearing holder** (`Z = 0.0 mm`), bored with a semicircular `lm8uu_od` seat and clamped at the bottom via `2 × M3x16` horizontal screws with counterbores at `X = ±6.5 mm, Z = -11.5 mm`.
   * Includes an `11.0 mm` wide center rear hook-tab (`X = ±5.5 mm`) that bridges cleanly **under** the lower GT2 belt tunnel (`Z = 7.5..10.4 mm`) and rises flush to `Y = -23.5 mm` (`Z = 10.4..16.4 mm`) to bolt into the rear tower with `1 × M3x8` horizontal screw (`X = 0.0 mm, Z = 13.5 mm`, stopping short of the belt tunnel).

4. **`PnP_Universal_Flex_Syringe_Mount`**
   * **Flat Base & V-Cradle:** Create a flat-backed rectangular mounting plate flush against the front face (`+Y = 13.5 mm`) of `PnP_Carriage_Base` with a centered vertical 90° V-cradle cut into its front face, and cut the matching `4-hole M3` mounting pattern (`X = ±16.5 mm, Z = 12.5 & 32.5 mm`) with front screw-head counterbores.
   * **Changeable-Syringe Spring Jaws:** At upper and lower levels on both sides of the V-cradle, join symmetric gooseneck compliant spring arms with flared lead-in tips (sized to elastically hug syringe barrels across a wide range of diameters) plus outer side hooks for an optional elastic retention band.
   * **Hose Clip:** Above the upper spring jaw on one side, bridge a small open C-clip guide for routing silicone vacuum tubing (no second sensor/camera collar).

5. **`PnP_Sized_Syringe_Mount`**
   * Offset cleanly to the side of the main assembly (`X = +95 mm`). Use the exact same flat-backed `4-hole M3` mounting plate (`X = ±16.5 mm, Z = 12.5 & 32.5 mm`) and counterbores, join a vertical cylindrical boss on the front sized for `syringe_od`, bore it to `syringe_od` with print clearance, and cut a flared front snap-in throat.

6. **`PnP_Vacuum_Nozzle_Adapter`**
   * Centered inside the V-cradle (`Y = 22.66 mm`) of `PnP_Universal_Flex_Syringe_Mount`, build stacked coaxial cylinders along `Z`: an `nozzle_od` clamping barrel, a top axial stop collar above the mount, a barbed vacuum-hose stem at the top, a tapered nose at the bottom, a continuous internal vacuum airway through-bore, and a lower Luer-slip socket for blunt SMD needles or suction cups.

Ensure every sketch uses watertight closed profiles, clean solid Boolean joins/cuts, zero self-intersections, and finishes by activating the root component and fitting the viewport.