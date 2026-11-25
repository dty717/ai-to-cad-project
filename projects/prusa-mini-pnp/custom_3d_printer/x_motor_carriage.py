# Fusion 360 Python API Script: Prusa MINI Z-Carriage, Flush Front X-Motor Mount,
# Rear Bowden Extruder, Dual 24mm LM8UU per Z-Rod, Flush X-Endstop & Clean -Y Wire Port

import adsk.core
import adsk.fusion
import math
import traceback


def cm(mm_val: float) -> float:
    """Convert millimeters to Fusion 360 internal centimeters."""
    return mm_val / 10.0


def add_user_param(user_params: adsk.fusion.UserParameters, name: str, val_mm: float, comment: str = ""):
    val_input = adsk.core.ValueInput.createByString(f"{val_mm} mm")
    existing = user_params.itemByName(name)
    if existing:
        existing.expression = f"{val_mm} mm"
    else:
        user_params.add(name, val_input, "mm", comment)


def get_sketch_normal(sketch: adsk.fusion.Sketch) -> adsk.core.Vector3D:
    n = sketch.xDirection.crossProduct(sketch.yDirection)
    n.normalize()
    return n


def create_world_plane(comp: adsk.fusion.Component, axis: str, offset_mm: float) -> adsk.fusion.ConstructionPlane:
    """Create a construction plane perpendicular to world 'X', 'Y', or 'Z' at offset_mm."""
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    axis = axis.upper()
    if axis == "Z":
        base = comp.xYConstructionPlane
        sign = 1.0 if base.geometry.normal.z >= 0 else -1.0
    elif axis == "Y":
        base = comp.xZConstructionPlane
        sign = 1.0 if base.geometry.normal.y >= 0 else -1.0
    elif axis == "X":
        base = comp.yZConstructionPlane
        sign = 1.0 if base.geometry.normal.x >= 0 else -1.0
    else:
        raise ValueError(f"Invalid axis: {axis}")

    plane_input.setByOffset(base, adsk.core.ValueInput.createByReal(cm(offset_mm * sign)))
    return planes.add(plane_input)


def world_pt(sketch: adsk.fusion.Sketch, wx: float, wy: float, wz: float) -> adsk.core.Point3D:
    """Transform world millimeter coordinates into the target sketch's local space."""
    return sketch.modelToSketchSpace(adsk.core.Point3D.create(cm(wx), cm(wy), cm(wz)))


def add_world_rect(sketch: adsk.fusion.Sketch, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float):
    """Draw a closed 4-edge rectangle in the sketch from two opposite world mm corners."""
    lines = sketch.sketchCurves.sketchLines
    if abs(z1 - z2) < 1e-6:
        pts = [(x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1)]
    elif abs(y1 - y2) < 1e-6:
        pts = [(x1, y1, z1), (x2, y1, z1), (x2, y1, z2), (x1, y1, z2)]
    elif abs(x1 - x2) < 1e-6:
        pts = [(x1, y1, z1), (x1, y2, z1), (x1, y2, z2), (x1, y1, z2)]
    else:
        raise ValueError("Points must lie on a common axis-aligned plane.")

    spts = [world_pt(sketch, *p) for p in pts]
    for i in range(4):
        lines.addByTwoPoints(spts[i], spts[(i + 1) % 4])


def add_world_polygon(sketch: adsk.fusion.Sketch, world_pts):
    lines = sketch.sketchCurves.sketchLines
    spts = [world_pt(sketch, *p) for p in world_pts]
    for i in range(len(spts)):
        lines.addByTwoPoints(spts[i], spts[(i + 1) % len(spts)])


def add_world_circle(sketch: adsk.fusion.Sketch, wx: float, wy: float, wz: float, dia_mm: float):
    circles = sketch.sketchCurves.sketchCircles
    circles.addByCenterRadius(world_pt(sketch, wx, wy, wz), cm(dia_mm / 2.0))


def largest_profile(sketch: adsk.fusion.Sketch) -> adsk.fusion.Profile:
    best_prof = None
    best_area = -1.0
    for i in range(sketch.profiles.count):
        prof = sketch.profiles.item(i)
        area = prof.areaProperties().area
        if area > best_area:
            best_area = area
            best_prof = prof
    return best_prof


def all_profiles_collection(sketch: adsk.fusion.Sketch) -> adsk.core.ObjectCollection:
    coll = adsk.core.ObjectCollection.create()
    for i in range(sketch.profiles.count):
        coll.add(sketch.profiles.item(i))
    return coll


def extrude_along_world(
    comp: adsk.fusion.Component,
    sketch: adsk.fusion.Sketch,
    profiles,
    world_axis: str,
    dist_mm: float,
    operation: adsk.fusion.FeatureOperations,
    target_bodies=None,
) -> adsk.fusion.ExtrudeFeature:
    """Extrude profile(s) by signed dist_mm along world 'X', 'Y', or 'Z'."""
    n = get_sketch_normal(sketch)
    axis_map = {"X": n.x, "Y": n.y, "Z": n.z}
    sign = 1.0 if axis_map[world_axis.upper()] >= 0 else -1.0
    signed_dist = cm(dist_mm * sign)

    extrudes = comp.features.extrudeFeatures
    ext_input = extrudes.createInput(profiles, operation)
    ext_input.setDistanceExtent(False, adsk.core.ValueInput.createByReal(signed_dist))
    if target_bodies:
        ext_input.participantBodies = target_bodies
    return extrudes.add(ext_input)


def build_chamfered_motor_body(
    comp: adsk.fusion.Component,
    cx: float,
    cy_face: float,
    cz: float,
    size_mm: float,
    length_signed_mm: float,
    chamfer_mm: float,
    name: str,
) -> adsk.fusion.BRepBody:
    """Build a chamfered-square NEMA 17 motor body extending along signed Y from cy_face."""
    h = size_mm / 2.0
    c = chamfer_mm
    pts = [
        (cx - h + c, cy_face, cz - h),
        (cx + h - c, cy_face, cz - h),
        (cx + h, cy_face, cz - h + c),
        (cx + h, cy_face, cz + h - c),
        (cx + h - c, cy_face, cz + h),
        (cx - h + c, cy_face, cz + h),
        (cx - h, cy_face, cz + h - c),
        (cx - h, cy_face, cz - h + c),
    ]
    pl = create_world_plane(comp, "Y", cy_face)
    sk = comp.sketches.add(pl)
    add_world_polygon(sk, pts)
    feat = extrude_along_world(
        comp, sk, largest_profile(sk), "Y", length_signed_mm, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    body = feat.bodies.item(0)
    body.name = name
    return body


def build_shcs_bolt(
    comp: adsk.fusion.Component,
    hx: float,
    hy: float,
    hz: float,
    axis: str,
    direction: int,
    head_dia: float,
    head_len: float,
    shank_dia: float,
    shank_len: float,
    name: str,
):
    """Build a socket-head cap screw whose head starts at (hx, hy, hz) and points along direction*axis."""
    if axis == "Y":
        pl_h = create_world_plane(comp, "Y", hy)
        sk_h = comp.sketches.add(pl_h)
        add_world_circle(sk_h, hx, hy, hz, head_dia)
        feat = extrude_along_world(
            comp, sk_h, largest_profile(sk_h), "Y", direction * head_len,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        body = feat.bodies.item(0)
        body.name = name
        s_y = hy + direction * head_len
        pl_s = create_world_plane(comp, "Y", s_y)
        sk_s = comp.sketches.add(pl_s)
        add_world_circle(sk_s, hx, s_y, hz, shank_dia)
        extrude_along_world(
            comp, sk_s, largest_profile(sk_s), "Y", direction * shank_len,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [body]
        )
    elif axis == "Z":
        pl_h = create_world_plane(comp, "Z", hz)
        sk_h = comp.sketches.add(pl_h)
        add_world_circle(sk_h, hx, hy, hz, head_dia)
        feat = extrude_along_world(
            comp, sk_h, largest_profile(sk_h), "Z", direction * head_len,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        body = feat.bodies.item(0)
        body.name = name
        s_z = hz + direction * head_len
        pl_s = create_world_plane(comp, "Z", s_z)
        sk_s = comp.sketches.add(pl_s)
        add_world_circle(sk_s, hx, hy, s_z, shank_dia)
        extrude_along_world(
            comp, sk_s, largest_profile(sk_s), "Z", direction * shank_len,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [body]
        )


def build_square_nut(
    comp: adsk.fusion.Component,
    nx: float,
    ny: float,
    nz: float,
    width_x: float,
    thick_y: float,
    height_z: float,
    bore_dia: float,
    bore_axis: str,
    name: str,
):
    """Build an M3nS square nut centered at (nx, ny, nz)."""
    pl = create_world_plane(comp, "Z", nz - height_z / 2.0)
    sk = comp.sketches.add(pl)
    add_world_rect(
        sk,
        nx - width_x / 2.0, ny - thick_y / 2.0, nz - height_z / 2.0,
        nx + width_x / 2.0, ny + thick_y / 2.0, nz - height_z / 2.0,
    )
    feat = extrude_along_world(
        comp, sk, largest_profile(sk), "Z", height_z, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    body = feat.bodies.item(0)
    body.name = name
    if bore_axis == "Y":
        pl_b = create_world_plane(comp, "Y", ny - thick_y / 2.0)
        sk_b = comp.sketches.add(pl_b)
        add_world_circle(sk_b, nx, ny - thick_y / 2.0, nz, bore_dia)
        extrude_along_world(
            comp, sk_b, largest_profile(sk_b), "Y", thick_y,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [body]
        )
    elif bore_axis == "Z":
        pl_b = create_world_plane(comp, "Z", nz - height_z / 2.0)
        sk_b = comp.sketches.add(pl_b)
        add_world_circle(sk_b, nx, ny, nz - height_z / 2.0, bore_dia)
        extrude_along_world(
            comp, sk_b, largest_profile(sk_b), "Z", height_z,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [body]
        )


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # ------------------------------------------------------------------
        # 1. Create Brand-New Parametric Design Document (Millimeter Units)
        # ------------------------------------------------------------------
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        up = design.userParameters

        # ------------------------------------------------------------------
        # 2. Top-Level Driving Dimensions (Matching MINI_z_top & PnP_Carriage_Base)
        # ------------------------------------------------------------------
        # Z-Axis Interface (MINI_z_top + Dual 24mm LM8UU per Z smooth rod)
        z_extrusion_size = 30.0       # 3030 T-slot aluminum extrusion
        z_extrusion_rod_gap = 6.0     # Clear gap from 3030 face to inner 8 mm Z rod
        z_rod_spacing = 40.0          # Center-to-center Z-rod spacing (TR8 midway at X=0)
        z_rod_dia = 8.0               # 8 mm smooth rod diameter
        z_rod_bore_dia = 8.3          # Vertical clearance bore in end & center retaining ribs
        z_lm8uu_od = 15.2             # LM8UU bearing seat diameter (15 mm + 0.2 mm fit)
        z_lm8uu_len = 24.4            # 24.0 mm LM8UU + 0.4 mm axial fit (2 per Z-rod)
        z_bearing_center_rib = 2.2    # Solid retaining rib between upper & lower LM8UU
        tr8_bore_dia = 10.4           # TR8 trapezoidal nut barrel clearance bore
        tr8_flange_dia = 22.5         # TR8 trapezoidal nut flange recess (22.0 mm OD + 0.5)
        tr8_flange_thick = 3.5        # Recess depth at bottom face (Z = -31 mm)
        tr8_flange_pcd = 16.0         # 4x M3 PCD on TR8 nut flange

        # X-Axis Interface (PnP_Carriage_Base)
        x_rod_spacing = 34.0          # Vertical center-to-center distance between X rods
        x_rod_dia = 8.0               # 8 mm X-axis smooth rods
        x_rod_bore_dia = 8.15         # Snug horizontal socket diameter
        belt_spacing = 11.4           # Vertical GT2 belt center-to-center spacing
        belt_width = 6.8              # 6 mm GT2 belt width clearance
        x_axis_y = -20.0              # Forward Y-plane of X-rods and GT2 belt (coplanar)

        # Unified Coplanar Z-Carriage Body Layout (Right Face Flush at X = +38.0 mm)
        carriage_height = 62.0        # Z in [-31.0, +31.0] mm (encloses flush switch & dual LM8UU)
        z_carriage_xmin = -29.0       # 1.0 mm clear running gap to 3030 face at X = -30.0
        z_carriage_xmax = 38.0        # Unified flush right plane for all carriage & switch bodies
        rear_clamp_ymax = 13.0        # Rear face of bolted LM8UU clamp cap (extruder mount plane)
        front_boss_ymin = -26.0       # Front face of upper/lower X-rod clamping bosses
        center_recess_y = -14.0       # Front face of central pulley/belt clearance window

        # Front-Mounted X-Axis Stepper Motor (17HS4401S, 0-deg on Flush Front Plate)
        nema17_size = 42.3
        nema17_x_len = 40.0
        nema17_pilot_dia = 24.0
        nema17_bolt_pitch = 31.0
        x_motor_x = 5.0
        x_motor_z = 0.0
        front_plate_thick = 6.0       # Front plate spans Y in [-32.0, -26.0] mm
        x_motor_face_y = front_boss_ymin - front_plate_thick  # -32.0 mm

        # Rear-Mounted Prusa MINI Bowden Extruder (Right Face Flush at X = +38.0 mm)
        ext_motor_size = 42.3
        ext_motor_len = 23.0
        ext_motor_x = 15.0
        ext_motor_z = -2.0
        ext_gear_x = 2.0
        ext_gear_z = 20.0
        ext_housing_xmin = -16.0
        ext_housing_xmax = z_carriage_xmax  # 38.0 mm coplanar right face
        ext_housing_ymin = rear_clamp_ymax  # 13.0 mm
        ext_housing_ymax = 31.0
        ext_housing_zmin = -24.0
        ext_housing_zmax = 32.0

        # Flush Recessed X-Endstop Click Switch (KW11 / SS-5GL Microswitch)
        switch_len = 19.8             # Length along Y
        switch_thick = 6.4            # Thickness along Z
        switch_height = 10.2          # Depth along X (flush inside X <= +38.0 mm)
        switch_hole_spacing = 9.5     # Vertical M2 mounting hole pitch along Y
        switch_hole_from_pins = 2.8   # Hole offset from pin face (+X inward)
        switch_hole_dia = 2.3         # M2 bolt clearance/tap diameter

        # Standard M3 Hardware Allowances
        m3_clear_dia = 3.4
        m3_cbore_dia = 6.0
        m3_motor_cbore_dia = 6.4
        m3_nut_w = 5.8
        m3_nut_t = 2.8

        # Register Fusion 360 User Parameters
        params_to_register = [
            ("z_extrusion_size", z_extrusion_size, "3030 extrusion width"),
            ("z_extrusion_rod_gap", z_extrusion_rod_gap, "Gap from 3030 face to inner Z rod"),
            ("z_rod_spacing", z_rod_spacing, "Z-axis smooth rod center spacing"),
            ("z_lm8uu_od", z_lm8uu_od, "LM8UU bearing seat diameter"),
            ("z_lm8uu_len", z_lm8uu_len, "LM8UU 24mm bearing length"),
            ("x_rod_spacing", x_rod_spacing, "X-axis vertical smooth rod spacing"),
            ("belt_spacing", belt_spacing, "GT2 belt vertical center spacing"),
            ("belt_width", belt_width, "GT2 belt width clearance"),
            ("x_axis_y_offset", abs(x_axis_y), "Forward offset of X-rod/belt plane from Z-axis"),
            ("carriage_height", carriage_height, "Overall Z-carriage height"),
            ("nema17_size", nema17_size, "NEMA 17 motor width"),
            ("x_motor_x", x_motor_x, "Front X-motor shaft X coordinate"),
            ("front_plate_thick", front_plate_thick, "Detachable front X-motor plate thickness"),
            ("switch_len", switch_len, "X-endstop click switch length"),
            ("switch_thick", switch_thick, "X-endstop click switch thickness"),
            ("switch_height", switch_height, "X-endstop click switch body height"),
            ("m3_clear_dia", m3_clear_dia, "M3 clearance bore diameter"),
        ]
        for pname, pval, pcomment in params_to_register:
            add_user_param(up, pname, pval, pcomment)

        # Derived coordinates
        hz = carriage_height / 2.0                  # 31.0 mm
        z_rod_inner_x = -z_rod_spacing / 2.0        # -20.0 mm
        z_rod_outer_x = z_rod_spacing / 2.0         # +20.0 mm
        extrusion_right_x = z_rod_inner_x - (z_rod_dia / 2.0) - z_extrusion_rod_gap  # -30.0 mm
        extrusion_center_x = extrusion_right_x - (z_extrusion_size / 2.0)            # -45.0 mm
        x_rod_upper_z = x_rod_spacing / 2.0         # +17.0 mm
        x_rod_lower_z = -x_rod_spacing / 2.0        # -17.0 mm
        x_rod_blind_x = -24.0
        boss_inner_z = 10.5

        # Dual 24.4 mm LM8UU Z-intervals per rod (leaves 5.5 mm top/bottom shoulders)
        z_bear_upper_bot = z_bearing_center_rib / 2.0                   # +1.1 mm (top +25.5)
        z_bear_lower_bot = -(z_bearing_center_rib / 2.0 + z_lm8uu_len)  # -25.5 mm (top -1.1)

        # Flush Recessed Click Switch Coordinates (front-open pocket capped by X_Motor_Front_Plate)
        sw_body_xmax = z_carriage_xmax              # 38.0 mm (flush with right carriage plane)
        sw_body_xmin = sw_body_xmax - switch_height # 27.8 mm (clear of outer LM8UU)
        sw_body_ymin = -25.8                        # 0.2 mm clean clearance behind X_Motor_Front_Plate (-26.0)
        sw_body_ymax = sw_body_ymin + switch_len    # -6.0 mm
        sw_body_zmin = -28.8                        # 2.2 mm solid floor above Z = -31.0 mm
        sw_body_zmax = sw_body_zmin + switch_thick  # -22.4 mm (1.325 mm wall below lower X-rod)
        sw_hole_x = sw_body_xmin + switch_hole_from_pins  # 30.6 mm
        sw_hole_y_mid = (sw_body_ymin + sw_body_ymax) / 2.0  # -15.9 mm
        sw_hole_ys = [sw_hole_y_mid - switch_hole_spacing / 2.0, sw_hole_y_mid + switch_hole_spacing / 2.0]

        # Spacious Forward (-Y) Wire Bay & Front Exit Port (6.3 x 6.8 mm, zero thin walls)
        wire_bay_xmin = 21.5                        # 2.1 mm clear of front_plate bolt nut (+19.4)
        wire_bay_xmax = 27.8                        # Opens straight onto switch pins & matches port width
        wire_port_xmax = 27.8                       # Coplanar with wire_bay_xmax; caps switch at X >= 27.8
        wire_bay_ymax = -8.2                        # 0.6 mm clear in front of LM8UU (-7.6 mm)
        wire_bay_zmin = -29.0                       # 2.0 mm solid floor above Z = -31.0 mm
        wire_bay_zmax = -22.2                       # 6.8 mm tall (1.125 mm below X-rod & 1.05 mm below X-motor)

        # Fastener coordinates (generous walls around expanded wire channel)
        z_clamp_pts = [
            (-9.5, 9.0), (-9.5, -9.0),
            (9.5, 9.0), (9.5, -9.0),
            (32.0, 26.0), (32.0, 0.0),
        ]
        z_clamp_nut_y = -10.5

        x_clamp_x_locs = [-10.5, 10.5]
        x_clamp_z_locs = [26.0, -26.0]
        x_clamp_nut_y = -14.0

        front_plate_bolts = [(-24.5, 26.0), (-24.5, -26.0), (16.5, 26.0), (16.5, -26.0)]
        front_plate_nut_y = -22.5

        ext_mount_pts = [(-9.5, 18.0), (9.5, 18.0), (32.0, -15.0)]
        ext_mount_nut_y = 5.0

        tr8_r = tr8_flange_pcd / 2.0
        tr8_diag = tr8_r * math.cos(math.radians(45.0))

        # ------------------------------------------------------------------
        # Component 1: Z_Carriage_X_Motor_Mount (Main Printed Front Part)
        # ------------------------------------------------------------------
        occ_main = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_main = occ_main.component
        comp_main.name = "Z_Carriage_X_Motor_Mount"

        # 1A. Z-Carriage Core Block (X in [-29, +38], Y in [-14, 0], Z in [-31, +31])
        pl_bot = create_world_plane(comp_main, "Z", -hz)
        sk_core = comp_main.sketches.add(pl_bot)
        add_world_rect(sk_core, z_carriage_xmin, center_recess_y, -hz, z_carriage_xmax, 0.0, -hz)
        feat_core = extrude_along_world(
            comp_main, sk_core, largest_profile(sk_core), "Z", carriage_height,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        main_body = feat_core.bodies.item(0)
        main_body.name = "Z_Carriage_X_Motor_Mount_Body"

        # 1B. Upper & Lower Forward X-Rod Clamping Bosses (Y in [-26, -13.5], Z in [±10.5, ±31.0])
        for z_lo, z_hi in [(boss_inner_z, hz), (-hz, -boss_inner_z)]:
            pl_boss = create_world_plane(comp_main, "Z", z_lo)
            sk_boss = comp_main.sketches.add(pl_boss)
            add_world_rect(
                sk_boss,
                z_carriage_xmin, front_boss_ymin, z_lo,
                z_carriage_xmax, center_recess_y + 0.5, z_lo
            )
            extrude_along_world(
                comp_main, sk_boss, largest_profile(sk_boss), "Z", (z_hi - z_lo),
                adsk.fusion.FeatureOperations.JoinFeatureOperation, [main_body]
            )

        # 1C. Cut Flush Click-Switch Pocket (open to Y = -26.0, no thin front sliver!)
        # Pocket spans X in [27.6, 38.0], Y in [-26.0, -5.8], Z in [-29.0, -22.2]
        pl_sw_cut = create_world_plane(comp_main, "X", sw_body_xmax)
        sk_sw_cut = comp_main.sketches.add(pl_sw_cut)
        add_world_rect(
            sk_sw_cut,
            sw_body_xmax, front_boss_ymin, sw_body_zmin - 0.2,
            sw_body_xmax, sw_body_ymax + 0.2, sw_body_zmax + 0.2
        )
        extrude_along_world(
            comp_main, sk_sw_cut, largest_profile(sk_sw_cut), "X", -(sw_body_xmax - 27.6),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # Spacious pin & forward wire channel (6.3 x 6.8 mm, Y = -8.2 forward out Y = -26.0)
        pl_wire_back = create_world_plane(comp_main, "Y", wire_bay_ymax)
        sk_wire_bay = comp_main.sketches.add(pl_wire_back)
        add_world_rect(
            sk_wire_bay,
            wire_bay_xmin, wire_bay_ymax, wire_bay_zmin,
            wire_bay_xmax, wire_bay_ymax, wire_bay_zmax
        )
        extrude_along_world(
            comp_main, sk_wire_bay, largest_profile(sk_wire_bay), "Y", (front_boss_ymin - wire_bay_ymax),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # 2x Vertical M2 Mounting Holes & Bottom Counterbores for Click Switch
        sk_swh = comp_main.sketches.add(pl_bot)
        for hy in sw_hole_ys:
            add_world_circle(sk_swh, sw_hole_x, hy, -hz, switch_hole_dia)
        extrude_along_world(
            comp_main, sk_swh, all_profiles_collection(sk_swh), "Z", 9.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        sk_swh_cb = comp_main.sketches.add(pl_bot)
        for hy in sw_hole_ys:
            add_world_circle(sk_swh_cb, sw_hole_x, hy, -hz, 4.4)
        extrude_along_world(
            comp_main, sk_swh_cb, all_profiles_collection(sk_swh_cb), "Z", 1.2,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # 1D. Cut Vertical Z-Rod Bores & TR8 Barrel Bore (All the way through Z)
        sk_zbores = comp_main.sketches.add(pl_bot)
        add_world_circle(sk_zbores, z_rod_inner_x, 0.0, -hz, z_rod_bore_dia)
        add_world_circle(sk_zbores, z_rod_outer_x, 0.0, -hz, z_rod_bore_dia)
        add_world_circle(sk_zbores, 0.0, 0.0, -hz, tr8_bore_dia)
        extrude_along_world(
            comp_main, sk_zbores, all_profiles_collection(sk_zbores), "Z", carriage_height,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # 1E. Cut Front Semicircular DUAL LM8UU (24.4 mm) Cradles per Z-Rod
        for zb in (z_bear_lower_bot, z_bear_upper_bot):
            pl_bear = create_world_plane(comp_main, "Z", zb)
            sk_bear = comp_main.sketches.add(pl_bear)
            add_world_circle(sk_bear, z_rod_inner_x, 0.0, zb, z_lm8uu_od)
            add_world_circle(sk_bear, z_rod_outer_x, 0.0, zb, z_lm8uu_od)
            extrude_along_world(
                comp_main, sk_bear, all_profiles_collection(sk_bear), "Z", z_lm8uu_len,
                adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
            )

        # 1F. Cut Bottom TR8 Trapezoidal Nut Flange Recess & Front Mounting Holes/Pockets
        sk_tr8_fl = comp_main.sketches.add(pl_bot)
        add_world_circle(sk_tr8_fl, 0.0, 0.0, -hz, tr8_flange_dia)
        extrude_along_world(
            comp_main, sk_tr8_fl, largest_profile(sk_tr8_fl), "Z", tr8_flange_thick,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        pl_tr8_holes = create_world_plane(comp_main, "Z", -hz + tr8_flange_thick)
        sk_tr8_holes = comp_main.sketches.add(pl_tr8_holes)
        for sx in (-1.0, 1.0):
            add_world_circle(sk_tr8_holes, sx * tr8_diag, -tr8_diag, -hz + tr8_flange_thick, m3_clear_dia)
        extrude_along_world(
            comp_main, sk_tr8_holes, all_profiles_collection(sk_tr8_holes), "Z", 10.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        pl_tr8_nut = create_world_plane(comp_main, "Y", 0.0)
        sk_tr8_nut = comp_main.sketches.add(pl_tr8_nut)
        for sx in (-1.0, 1.0):
            cx = sx * tr8_diag
            add_world_rect(
                sk_tr8_nut,
                cx - m3_nut_w / 2.0, 0.0, -21.0 - m3_nut_t / 2.0,
                cx + m3_nut_w / 2.0, 0.0, -21.0 + m3_nut_t / 2.0
            )
        extrude_along_world(
            comp_main, sk_tr8_nut, all_profiles_collection(sk_tr8_nut), "Y", -(tr8_diag + m3_nut_w / 2.0),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # 1G. Cut Horizontal X-Axis Blind Smooth Rod Sockets (X = +38.0 down to -24.0 mm)
        pl_xright = create_world_plane(comp_main, "X", z_carriage_xmax)
        sk_xrods = comp_main.sketches.add(pl_xright)
        add_world_circle(sk_xrods, z_carriage_xmax, x_axis_y, x_rod_upper_z, x_rod_bore_dia)
        add_world_circle(sk_xrods, z_carriage_xmax, x_axis_y, x_rod_lower_z, x_rod_bore_dia)
        extrude_along_world(
            comp_main, sk_xrods, all_profiles_collection(sk_xrods), "X", -(z_carriage_xmax - x_rod_blind_x),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # Rod-seating inspection windows on front face
        pl_insp = create_world_plane(comp_main, "Y", front_boss_ymin)
        sk_insp = comp_main.sketches.add(pl_insp)
        for rz in (x_rod_upper_z, x_rod_lower_z):
            add_world_rect(sk_insp, -23.0, front_boss_ymin, rz - 2.0, -19.0, front_boss_ymin, rz + 2.0)
        extrude_along_world(
            comp_main, sk_insp, all_profiles_collection(sk_insp), "Y", 5.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # Vertical X-rod pinch slits (1.2 mm wide from rod center out to ±31.0 mm)
        slit_w = 1.2
        for rz, dz in [(x_rod_upper_z, hz - x_rod_upper_z), (x_rod_lower_z, -hz - x_rod_lower_z)]:
            pl_slit = create_world_plane(comp_main, "Z", rz)
            sk_slit = comp_main.sketches.add(pl_slit)
            add_world_rect(
                sk_slit,
                x_rod_blind_x, x_axis_y - slit_w / 2.0, rz,
                z_carriage_xmax, x_axis_y + slit_w / 2.0, rz
            )
            extrude_along_world(
                comp_main, sk_slit, largest_profile(sk_slit), "Z", dz,
                adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
            )

        # 4x X-rod horizontal M3 clamp bores, front counterbores, and top/bottom M3nS pockets
        sk_xclamp = comp_main.sketches.add(pl_insp)
        for cx in x_clamp_x_locs:
            for cz in x_clamp_z_locs:
                add_world_circle(sk_xclamp, cx, front_boss_ymin, cz, m3_clear_dia)
        extrude_along_world(
            comp_main, sk_xclamp, all_profiles_collection(sk_xclamp), "Y", 15.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        sk_xclamp_cb = comp_main.sketches.add(pl_insp)
        for cx in x_clamp_x_locs:
            for cz in x_clamp_z_locs:
                add_world_circle(sk_xclamp_cb, cx, front_boss_ymin, cz, m3_cbore_dia)
        extrude_along_world(
            comp_main, sk_xclamp_cb, all_profiles_collection(sk_xclamp_cb), "Y", 3.2,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        for z_start, z_dir, z_depth in [(hz, -1.0, 8.5), (-hz, 1.0, 8.5)]:
            pl_xnut = create_world_plane(comp_main, "Z", z_start)
            sk_xnut = comp_main.sketches.add(pl_xnut)
            for cx in x_clamp_x_locs:
                add_world_rect(
                    sk_xnut,
                    cx - m3_nut_w / 2.0, x_clamp_nut_y - m3_nut_t / 2.0, z_start,
                    cx + m3_nut_w / 2.0, x_clamp_nut_y + m3_nut_t / 2.0, z_start
                )
            extrude_along_world(
                comp_main, sk_xnut, all_profiles_collection(sk_xnut), "Z", z_dir * z_depth,
                adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
            )

        # 1H. Cut 4x Front-Plate Mounting Bores & M3nS Pockets (X = -24.5, +16.5; Z = ±26.0)
        sk_fpb = comp_main.sketches.add(pl_insp)
        for cx, cz in front_plate_bolts:
            add_world_circle(sk_fpb, cx, front_boss_ymin, cz, m3_clear_dia)
        extrude_along_world(
            comp_main, sk_fpb, all_profiles_collection(sk_fpb), "Y", 5.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        for z_start, z_dir, z_depth in [(hz, -1.0, 8.5), (-hz, 1.0, 8.5)]:
            pl_fpn = create_world_plane(comp_main, "Z", z_start)
            sk_fpn = comp_main.sketches.add(pl_fpn)
            for cx in (-24.5, 16.5):
                add_world_rect(
                    sk_fpn,
                    cx - m3_nut_w / 2.0, front_plate_nut_y - m3_nut_t / 2.0, z_start,
                    cx + m3_nut_w / 2.0, front_plate_nut_y + m3_nut_t / 2.0, z_start
                )
            extrude_along_world(
                comp_main, sk_fpn, all_profiles_collection(sk_fpn), "Z", z_dir * z_depth,
                adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
            )

        # 1I. Cut 6x Z-Carriage Clamp M3 Bores & M3nS Pockets
        pl_split = create_world_plane(comp_main, "Y", 0.0)
        sk_zclamp = comp_main.sketches.add(pl_split)
        for cx, cz in z_clamp_pts:
            add_world_circle(sk_zclamp, cx, 0.0, cz, m3_clear_dia)
        extrude_along_world(
            comp_main, sk_zclamp, all_profiles_collection(sk_zclamp), "Y", -12.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        pl_top = create_world_plane(comp_main, "Z", hz)
        sk_znut_top = comp_main.sketches.add(pl_top)
        for cx in (-9.5, 9.5):
            add_world_rect(
                sk_znut_top,
                cx - m3_nut_w / 2.0, z_clamp_nut_y - m3_nut_t / 2.0, hz,
                cx + m3_nut_w / 2.0, z_clamp_nut_y + m3_nut_t / 2.0, hz
            )
        extrude_along_world(
            comp_main, sk_znut_top, all_profiles_collection(sk_znut_top), "Z", -(hz - 5.5),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        sk_znut_bot = comp_main.sketches.add(pl_bot)
        for cx in (-9.5, 9.5):
            add_world_rect(
                sk_znut_bot,
                cx - m3_nut_w / 2.0, z_clamp_nut_y - m3_nut_t / 2.0, -hz,
                cx + m3_nut_w / 2.0, z_clamp_nut_y + m3_nut_t / 2.0, -hz
            )
        extrude_along_world(
            comp_main, sk_znut_bot, all_profiles_collection(sk_znut_bot), "Z", (hz - 5.5),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        sk_ornut_top = comp_main.sketches.add(pl_top)
        add_world_rect(
            sk_ornut_top,
            32.0 - m3_nut_w / 2.0, z_clamp_nut_y - m3_nut_t / 2.0, hz,
            32.0 + m3_nut_w / 2.0, z_clamp_nut_y + m3_nut_t / 2.0, hz
        )
        extrude_along_world(
            comp_main, sk_ornut_top, largest_profile(sk_ornut_top), "Z", -8.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        sk_ornut_mid = comp_main.sketches.add(pl_sw_cut)
        add_world_rect(
            sk_ornut_mid,
            z_carriage_xmax, z_clamp_nut_y - m3_nut_t / 2.0, -m3_nut_w / 2.0,
            z_carriage_xmax, z_clamp_nut_y + m3_nut_t / 2.0, m3_nut_w / 2.0
        )
        extrude_along_world(
            comp_main, sk_ornut_mid, largest_profile(sk_ornut_mid), "X", -(z_carriage_xmax - 29.0),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [main_body]
        )

        # ------------------------------------------------------------------
        # Component 2: X_Motor_Front_Plate (Flush Mount + Caps Switch Front)
        # ------------------------------------------------------------------
        occ_fplate = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_fplate = occ_fplate.component
        comp_fplate.name = "X_Motor_Front_Plate"

        pl_fp_face = create_world_plane(comp_fplate, "Y", x_motor_face_y)
        sk_fp_outer = comp_fplate.sketches.add(pl_fp_face)
        fp_pts = [
            (z_carriage_xmin, x_motor_face_y, -hz),
            (z_carriage_xmax, x_motor_face_y, -hz),
            (z_carriage_xmax, x_motor_face_y, hz),
            (z_carriage_xmin, x_motor_face_y, hz),
        ]
        add_world_polygon(sk_fp_outer, fp_pts)
        feat_fp = extrude_along_world(
            comp_fplate, sk_fp_outer, largest_profile(sk_fp_outer), "Y", front_plate_thick,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        fp_body = feat_fp.bodies.item(0)
        fp_body.name = "X_Motor_Front_Plate_Body"

        sk_fp_mot = comp_fplate.sketches.add(pl_fp_face)
        add_world_circle(sk_fp_mot, x_motor_x, x_motor_face_y, x_motor_z, nema17_pilot_dia)
        hb = nema17_bolt_pitch / 2.0
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                add_world_circle(sk_fp_mot, x_motor_x + sx * hb, x_motor_face_y, x_motor_z + sz * hb, m3_clear_dia)
        extrude_along_world(
            comp_fplate, sk_fp_mot, all_profiles_collection(sk_fp_mot), "Y", front_plate_thick,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [fp_body]
        )

        pl_fp_rear = create_world_plane(comp_fplate, "Y", front_boss_ymin)
        sk_fp_mcb = comp_fplate.sketches.add(pl_fp_rear)
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                add_world_circle(sk_fp_mcb, x_motor_x + sx * hb, front_boss_ymin, x_motor_z + sz * hb, m3_motor_cbore_dia)
        extrude_along_world(
            comp_fplate, sk_fp_mcb, all_profiles_collection(sk_fp_mcb), "Y", -3.2,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [fp_body]
        )

        sk_fp_mnt = comp_fplate.sketches.add(pl_fp_face)
        for cx, cz in front_plate_bolts:
            add_world_circle(sk_fp_mnt, cx, x_motor_face_y, cz, m3_clear_dia)
        extrude_along_world(
            comp_fplate, sk_fp_mnt, all_profiles_collection(sk_fp_mnt), "Y", front_plate_thick,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [fp_body]
        )

        sk_fp_mcb2 = comp_fplate.sketches.add(pl_fp_face)
        for cx, cz in front_plate_bolts:
            add_world_circle(sk_fp_mcb2, cx, x_motor_face_y, cz, m3_cbore_dia)
        extrude_along_world(
            comp_fplate, sk_fp_mcb2, all_profiles_collection(sk_fp_mcb2), "Y", 2.2,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [fp_body]
        )

        # Cut straight-through forward (-Y) wire exit port (6.3 x 6.8 mm, X in [21.5, 27.8])
        sk_fp_wire = comp_fplate.sketches.add(pl_fp_face)
        add_world_rect(
            sk_fp_wire,
            wire_bay_xmin, x_motor_face_y, wire_bay_zmin,
            wire_port_xmax, x_motor_face_y, wire_bay_zmax
        )
        extrude_along_world(
            comp_fplate, sk_fp_wire, largest_profile(sk_fp_wire), "Y", front_plate_thick,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [fp_body]
        )

        # ------------------------------------------------------------------
        # Component 3: Z_Carriage_Rear_Clamp (Solid Bolted LM8UU Clamp)
        # ------------------------------------------------------------------
        occ_clamp = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_clamp = occ_clamp.component
        comp_clamp.name = "Z_Carriage_Rear_Clamp"

        pl_cbot = create_world_plane(comp_clamp, "Z", -hz)
        sk_clamp_base = comp_clamp.sketches.add(pl_cbot)
        add_world_rect(sk_clamp_base, z_carriage_xmin, 0.0, -hz, z_carriage_xmax, rear_clamp_ymax, -hz)
        feat_clamp = extrude_along_world(
            comp_clamp, sk_clamp_base, largest_profile(sk_clamp_base), "Z", carriage_height,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        clamp_body = feat_clamp.bodies.item(0)
        clamp_body.name = "Z_Carriage_Rear_Clamp_Body"

        sk_c_zbores = comp_clamp.sketches.add(pl_cbot)
        add_world_circle(sk_c_zbores, z_rod_inner_x, 0.0, -hz, z_rod_bore_dia)
        add_world_circle(sk_c_zbores, z_rod_outer_x, 0.0, -hz, z_rod_bore_dia)
        add_world_circle(sk_c_zbores, 0.0, 0.0, -hz, tr8_bore_dia)
        extrude_along_world(
            comp_clamp, sk_c_zbores, all_profiles_collection(sk_c_zbores), "Z", carriage_height,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        for zb in (z_bear_lower_bot, z_bear_upper_bot):
            pl_cbear = create_world_plane(comp_clamp, "Z", zb)
            sk_cbear = comp_clamp.sketches.add(pl_cbear)
            add_world_circle(sk_cbear, z_rod_inner_x, 0.0, zb, z_lm8uu_od)
            add_world_circle(sk_cbear, z_rod_outer_x, 0.0, zb, z_lm8uu_od)
            extrude_along_world(
                comp_clamp, sk_cbear, all_profiles_collection(sk_cbear), "Z", z_lm8uu_len,
                adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
            )

        # TR8 flange recess & 2 rear TR8 M3 mounting bores + nut pockets
        sk_c_tr8_fl = comp_clamp.sketches.add(pl_cbot)
        add_world_circle(sk_c_tr8_fl, 0.0, 0.0, -hz, tr8_flange_dia)
        extrude_along_world(
            comp_clamp, sk_c_tr8_fl, largest_profile(sk_c_tr8_fl), "Z", tr8_flange_thick,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        pl_c_tr8_h = create_world_plane(comp_clamp, "Z", -hz + tr8_flange_thick)
        sk_c_tr8_h = comp_clamp.sketches.add(pl_c_tr8_h)
        for sx in (-1.0, 1.0):
            add_world_circle(sk_c_tr8_h, sx * tr8_diag, tr8_diag, -hz + tr8_flange_thick, m3_clear_dia)
        extrude_along_world(
            comp_clamp, sk_c_tr8_h, all_profiles_collection(sk_c_tr8_h), "Z", 10.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        pl_c_rear = create_world_plane(comp_clamp, "Y", rear_clamp_ymax)
        sk_c_tr8_nut = comp_clamp.sketches.add(pl_c_rear)
        for sx in (-1.0, 1.0):
            cx = sx * tr8_diag
            add_world_rect(
                sk_c_tr8_nut,
                cx - m3_nut_w / 2.0, rear_clamp_ymax, -21.0 - m3_nut_t / 2.0,
                cx + m3_nut_w / 2.0, rear_clamp_ymax, -21.0 + m3_nut_t / 2.0
            )
        extrude_along_world(
            comp_clamp, sk_c_tr8_nut, all_profiles_collection(sk_c_tr8_nut), "Y", -(rear_clamp_ymax - tr8_diag + m3_nut_w / 2.0),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        # 6x horizontal Z-clamp M3 bores & rear counterbores
        sk_c_bolts = comp_clamp.sketches.add(pl_c_rear)
        for cx, cz in z_clamp_pts:
            add_world_circle(sk_c_bolts, cx, rear_clamp_ymax, cz, m3_clear_dia)
        extrude_along_world(
            comp_clamp, sk_c_bolts, all_profiles_collection(sk_c_bolts), "Y", -rear_clamp_ymax,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        sk_c_cb = comp_clamp.sketches.add(pl_c_rear)
        for cx, cz in z_clamp_pts:
            add_world_circle(sk_c_cb, cx, rear_clamp_ymax, cz, m3_cbore_dia)
        extrude_along_world(
            comp_clamp, sk_c_cb, all_profiles_collection(sk_c_cb), "Y", -4.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        # 3x Rear Bowden Extruder Mounting Bores & M3nS Pockets
        sk_c_ext = comp_clamp.sketches.add(pl_c_rear)
        for cx, cz in ext_mount_pts:
            add_world_circle(sk_c_ext, cx, rear_clamp_ymax, cz, m3_clear_dia)
        extrude_along_world(
            comp_clamp, sk_c_ext, all_profiles_collection(sk_c_ext), "Y", -10.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        pl_c_top = create_world_plane(comp_clamp, "Z", hz)
        sk_c_ext_topnut = comp_clamp.sketches.add(pl_c_top)
        for cx in (-9.5, 9.5):
            add_world_rect(
                sk_c_ext_topnut,
                cx - m3_nut_w / 2.0, ext_mount_nut_y - m3_nut_t / 2.0, hz,
                cx + m3_nut_w / 2.0, ext_mount_nut_y + m3_nut_t / 2.0, hz
            )
        extrude_along_world(
            comp_clamp, sk_c_ext_topnut, all_profiles_collection(sk_c_ext_topnut), "Z", -16.5,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        pl_c_side = create_world_plane(comp_clamp, "X", z_carriage_xmax)
        sk_c_ext_sidenut = comp_clamp.sketches.add(pl_c_side)
        add_world_rect(
            sk_c_ext_sidenut,
            z_carriage_xmax, ext_mount_nut_y - m3_nut_t / 2.0, -15.0 - m3_nut_w / 2.0,
            z_carriage_xmax, ext_mount_nut_y + m3_nut_t / 2.0, -15.0 + m3_nut_w / 2.0
        )
        extrude_along_world(
            comp_clamp, sk_c_ext_sidenut, largest_profile(sk_c_ext_sidenut), "X", -(z_carriage_xmax - 29.0),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [clamp_body]
        )

        # ------------------------------------------------------------------
        # Component 4: MINI_Extruder_Assembly (Rear Prusa MINI Bowden Extruder)
        # ------------------------------------------------------------------
        occ_ext = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_ext = occ_ext.component
        comp_ext.name = "MINI_Extruder_Assembly"

        pl_ext_f = create_world_plane(comp_ext, "Y", ext_housing_ymin)
        sk_ext = comp_ext.sketches.add(pl_ext_f)
        ext_pts = [
            (ext_housing_xmin, ext_housing_ymin, 0.0),
            (ext_housing_xmin + 8.0, ext_housing_ymin, ext_housing_zmin),
            (ext_housing_xmax, ext_housing_ymin, ext_housing_zmin),
            (ext_housing_xmax, ext_housing_ymin, ext_housing_zmax),
            (-5.0, ext_housing_ymin, ext_housing_zmax),
            (ext_housing_xmin, ext_housing_ymin, 16.0),
        ]
        add_world_polygon(sk_ext, ext_pts)
        feat_ext = extrude_along_world(
            comp_ext, sk_ext, largest_profile(sk_ext), "Y", (ext_housing_ymax - ext_housing_ymin),
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        ext_body = feat_ext.bodies.item(0)
        ext_body.name = "MINI_Extruder_Body"

        pl_bow = create_world_plane(comp_ext, "Z", ext_housing_zmax)
        sk_bow = comp_ext.sketches.add(pl_bow)
        add_world_circle(sk_bow, 24.0, 22.0, ext_housing_zmax, 14.0)
        extrude_along_world(
            comp_ext, sk_bow, largest_profile(sk_bow), "Z", 6.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [ext_body]
        )

        pl_bow_top = create_world_plane(comp_ext, "Z", ext_housing_zmax + 6.0)
        sk_bow_cut = comp_ext.sketches.add(pl_bow_top)
        add_world_circle(sk_bow_cut, 24.0, 22.0, ext_housing_zmax + 6.0, 8.8)
        extrude_along_world(
            comp_ext, sk_bow_cut, largest_profile(sk_bow_cut), "Z", -9.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        pl_ext_r = create_world_plane(comp_ext, "Y", ext_housing_ymax)
        sk_ext_mot = comp_ext.sketches.add(pl_ext_r)
        add_world_circle(sk_ext_mot, ext_motor_x, ext_housing_ymax, ext_motor_z, 22.4)
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                add_world_circle(sk_ext_mot, ext_motor_x + sx * hb, ext_housing_ymax, ext_motor_z + sz * hb, m3_clear_dia)
        extrude_along_world(
            comp_ext, sk_ext_mot, all_profiles_collection(sk_ext_mot), "Y", -6.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        pl_gc = create_world_plane(comp_ext, "Y", 19.0)
        sk_gc = comp_ext.sketches.add(pl_gc)
        add_world_circle(sk_gc, ext_gear_x, 19.0, ext_gear_z, 41.0)
        add_world_circle(sk_gc, ext_motor_x, 19.0, ext_motor_z, 15.0)
        extrude_along_world(
            comp_ext, sk_gc, all_profiles_collection(sk_gc), "Y", 8.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        sk_625 = comp_ext.sketches.add(pl_ext_f)
        add_world_circle(sk_625, ext_gear_x, ext_housing_ymin, ext_gear_z, 16.2)
        extrude_along_world(
            comp_ext, sk_625, largest_profile(sk_625), "Y", 5.2,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        sk_ext_mnt = comp_ext.sketches.add(pl_ext_f)
        for cx, cz in ext_mount_pts:
            add_world_circle(sk_ext_mnt, cx, ext_housing_ymin, cz, m3_clear_dia)
        extrude_along_world(
            comp_ext, sk_ext_mnt, all_profiles_collection(sk_ext_mnt), "Y", (ext_housing_ymax - ext_housing_ymin),
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        sk_ext_cb = comp_ext.sketches.add(pl_ext_r)
        for cx, cz in ext_mount_pts:
            add_world_circle(sk_ext_cb, cx, ext_housing_ymax, cz, m3_cbore_dia)
        extrude_along_world(
            comp_ext, sk_ext_cb, all_profiles_collection(sk_ext_cb), "Y", -9.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        pl_inlet = create_world_plane(comp_ext, "X", ext_housing_xmin)
        sk_inlet = comp_ext.sketches.add(pl_inlet)
        add_world_circle(sk_inlet, ext_housing_xmin, 22.0, 10.0, 4.3)
        extrude_along_world(
            comp_ext, sk_inlet, largest_profile(sk_inlet), "X", 18.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [ext_body]
        )

        pl_idl = create_world_plane(comp_ext, "Y", 17.0)
        sk_idl = comp_ext.sketches.add(pl_idl)
        idl_pts = [
            (-10.0, 17.0, 22.0),
            (18.0, 17.0, 22.0),
            (18.0, 17.0, 36.0),
            (-10.0, 17.0, 32.0),
        ]
        add_world_polygon(sk_idl, idl_pts)
        f_idl = extrude_along_world(
            comp_ext, sk_idl, largest_profile(sk_idl), "Y", 10.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        f_idl.bodies.item(0).name = "MINI_Extruder_Idler_Arm"

        pl_g = create_world_plane(comp_ext, "Y", 20.5)
        sk_g1 = comp_ext.sketches.add(pl_g)
        add_world_circle(sk_g1, ext_gear_x, 20.5, ext_gear_z, 38.0)
        fg1 = extrude_along_world(
            comp_ext, sk_g1, largest_profile(sk_g1), "Y", 5.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        fg1.bodies.item(0).name = "Extruder_Spur_Gear_50T"

        sk_g2 = comp_ext.sketches.add(pl_g)
        add_world_circle(sk_g2, ext_motor_x, 20.5, ext_motor_z, 11.5)
        fg2 = extrude_along_world(
            comp_ext, sk_g2, largest_profile(sk_g2), "Y", 5.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        fg2.bodies.item(0).name = "Extruder_Motor_Pinion"

        ext_mot_body = build_chamfered_motor_body(
            comp_ext, ext_motor_x, ext_housing_ymax, ext_motor_z,
            ext_motor_size, ext_motor_len, 4.5, "NEMA17_17HS4023_Extruder_Motor"
        )
        sk_epilot = comp_ext.sketches.add(pl_ext_r)
        add_world_circle(sk_epilot, ext_motor_x, ext_housing_ymax, ext_motor_z, 22.0)
        extrude_along_world(
            comp_ext, sk_epilot, largest_profile(sk_epilot), "Y", -2.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [ext_mot_body]
        )
        sk_eshaft = comp_ext.sketches.add(pl_ext_r)
        add_world_circle(sk_eshaft, ext_motor_x, ext_housing_ymax, ext_motor_z, 5.0)
        extrude_along_world(
            comp_ext, sk_eshaft, largest_profile(sk_eshaft), "Y", -12.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [ext_mot_body]
        )

        # ------------------------------------------------------------------
        # Component 5: X_Endstop_Click_Switch (Flush Inside X = +38.0 mm Plane)
        # ------------------------------------------------------------------
        occ_sw = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_sw = occ_sw.component
        comp_sw.name = "X_Endstop_Click_Switch"

        pl_sw = create_world_plane(comp_sw, "Z", sw_body_zmin)
        sk_sw = comp_sw.sketches.add(pl_sw)
        add_world_rect(sk_sw, sw_body_xmin, sw_body_ymin, sw_body_zmin, sw_body_xmax, sw_body_ymax, sw_body_zmin)
        f_sw = extrude_along_world(
            comp_sw, sk_sw, largest_profile(sk_sw), "Z", switch_thick,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        sw_body = f_sw.bodies.item(0)
        sw_body.name = "KW11_Microswitch_Body"

        sk_sw_h = comp_sw.sketches.add(pl_sw)
        for hy in sw_hole_ys:
            add_world_circle(sk_sw_h, sw_hole_x, hy, sw_body_zmin, switch_hole_dia)
        extrude_along_world(
            comp_sw, sk_sw_h, all_profiles_collection(sk_sw_h), "Z", switch_thick,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [sw_body]
        )

        pl_sw_face = create_world_plane(comp_sw, "X", sw_body_xmax)
        sk_plunge = comp_sw.sketches.add(pl_sw_face)
        add_world_rect(
            sk_plunge,
            sw_body_xmax, x_axis_y - 1.2, sw_body_zmin + 1.7,
            sw_body_xmax, x_axis_y + 1.2, sw_body_zmax - 1.7
        )
        f_plunge = extrude_along_world(
            comp_sw, sk_plunge, largest_profile(sk_plunge), "X", 1.1,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        f_plunge.bodies.item(0).name = "Switch_Plunger"

        sw_zmid = (sw_body_zmin + sw_body_zmax) / 2.0
        pl_lev = create_world_plane(comp_sw, "Z", sw_zmid - 2.0)
        sk_lev = comp_sw.sketches.add(pl_lev)
        lever_pts = [
            (sw_body_xmax + 0.1, sw_body_ymax - 3.0, sw_zmid - 2.0),
            (sw_body_xmax + 2.2, sw_body_ymin + 2.0, sw_zmid - 2.0),
            (sw_body_xmax + 2.6, sw_body_ymin + 2.0, sw_zmid - 2.0),
            (sw_body_xmax + 0.5, sw_body_ymax - 3.0, sw_zmid - 2.0),
        ]
        add_world_polygon(sk_lev, lever_pts)
        f_lev = extrude_along_world(
            comp_sw, sk_lev, largest_profile(sk_lev), "Z", 4.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        f_lev.bodies.item(0).name = "Switch_Spring_Lever"

        pl_pins = create_world_plane(comp_sw, "X", sw_body_xmin)
        sk_pins = comp_sw.sketches.add(pl_pins)
        for py in (sw_body_ymin + 3.0, sw_hole_y_mid, sw_body_ymax - 3.0):
            add_world_rect(
                sk_pins,
                sw_body_xmin, py - 0.3, sw_zmid - 1.6,
                sw_body_xmin, py + 0.3, sw_zmid + 1.6
            )
        f_pins = extrude_along_world(
            comp_sw, sk_pins, all_profiles_collection(sk_pins), "X", -3.2,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        for pi in range(f_pins.bodies.count):
            f_pins.bodies.item(pi).name = f"Switch_Terminal_Pin_{pi + 1}"

        # ------------------------------------------------------------------
        # Component 6: Z_Motion_Reference (3030, Z-Rods, 4x 24mm LM8UU, TR8)
        # ------------------------------------------------------------------
        occ_zref = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_zref = occ_zref.component
        comp_zref.name = "Z_Motion_Reference"

        z_ref_zmin = -85.0
        z_ref_len = 170.0
        pl_zref = create_world_plane(comp_zref, "Z", z_ref_zmin)

        sk_3030 = comp_zref.sketches.add(pl_zref)
        hs = z_extrusion_size / 2.0
        add_world_rect(
            sk_3030,
            extrusion_center_x - hs, -hs, z_ref_zmin,
            extrusion_center_x + hs, hs, z_ref_zmin
        )
        feat_3030 = extrude_along_world(
            comp_zref, sk_3030, largest_profile(sk_3030), "Z", z_ref_len,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        body_3030 = feat_3030.bodies.item(0)
        body_3030.name = "Extrusion_3030"

        sk_3030_slots = comp_zref.sketches.add(pl_zref)
        add_world_circle(sk_3030_slots, extrusion_center_x, 0.0, z_ref_zmin, 6.8)
        slot_w, slot_d = 8.2, 6.5
        add_world_rect(sk_3030_slots, extrusion_center_x - slot_w / 2, hs - slot_d, z_ref_zmin, extrusion_center_x + slot_w / 2, hs, z_ref_zmin)
        add_world_rect(sk_3030_slots, extrusion_center_x - slot_w / 2, -hs, z_ref_zmin, extrusion_center_x + slot_w / 2, -hs + slot_d, z_ref_zmin)
        add_world_rect(sk_3030_slots, extrusion_center_x + hs - slot_d, -slot_w / 2, z_ref_zmin, extrusion_center_x + hs, slot_w / 2, z_ref_zmin)
        add_world_rect(sk_3030_slots, extrusion_center_x - hs, -slot_w / 2, z_ref_zmin, extrusion_center_x - hs + slot_d, slot_w / 2, z_ref_zmin)
        extrude_along_world(
            comp_zref, sk_3030_slots, all_profiles_collection(sk_3030_slots), "Z", z_ref_len,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [body_3030]
        )

        for rname, rx in [("Z_Smooth_Rod_Inner", z_rod_inner_x), ("Z_Smooth_Rod_Outer", z_rod_outer_x), ("TR8_Leadscrew", 0.0)]:
            sk_r = comp_zref.sketches.add(pl_zref)
            add_world_circle(sk_r, rx, 0.0, z_ref_zmin, z_rod_dia)
            fr = extrude_along_world(
                comp_zref, sk_r, largest_profile(sk_r), "Z", z_ref_len,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            )
            fr.bodies.item(0).name = rname

        for tag_z, z_b0 in [("Lower", z_bear_lower_bot + 0.2), ("Upper", z_bear_upper_bot + 0.2)]:
            pl_zb = create_world_plane(comp_zref, "Z", z_b0)
            for tag_x, bx in [("Inner", z_rod_inner_x), ("Outer", z_rod_outer_x)]:
                sk_b = comp_zref.sketches.add(pl_zb)
                add_world_circle(sk_b, bx, 0.0, z_b0, 15.0)
                fb = extrude_along_world(
                    comp_zref, sk_b, largest_profile(sk_b), "Z", 24.0,
                    adsk.fusion.FeatureOperations.NewBodyFeatureOperation
                )
                b_body = fb.bodies.item(0)
                b_body.name = f"LM8UU_24mm_{tag_x}_{tag_z}"
                sk_bi = comp_zref.sketches.add(pl_zb)
                add_world_circle(sk_bi, bx, 0.0, z_b0, 8.0)
                extrude_along_world(
                    comp_zref, sk_bi, largest_profile(sk_bi), "Z", 24.0,
                    adsk.fusion.FeatureOperations.CutFeatureOperation, [b_body]
                )

        pl_tnut = create_world_plane(comp_zref, "Z", -hz)
        sk_tnut = comp_zref.sketches.add(pl_tnut)
        add_world_circle(sk_tnut, 0.0, 0.0, -hz, 22.0)
        f_tnut = extrude_along_world(
            comp_zref, sk_tnut, largest_profile(sk_tnut), "Z", tr8_flange_thick,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        tnut_body = f_tnut.bodies.item(0)
        tnut_body.name = "TR8_Trapezoidal_Nut"

        pl_tbar = create_world_plane(comp_zref, "Z", -hz + tr8_flange_thick)
        sk_tbar = comp_zref.sketches.add(pl_tbar)
        add_world_circle(sk_tbar, 0.0, 0.0, -hz + tr8_flange_thick, 10.2)
        extrude_along_world(
            comp_zref, sk_tbar, largest_profile(sk_tbar), "Z", 11.5,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [tnut_body]
        )

        sk_tcut = comp_zref.sketches.add(pl_tnut)
        add_world_circle(sk_tcut, 0.0, 0.0, -hz, 8.0)
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                add_world_circle(sk_tcut, sx * tr8_diag, sy * tr8_diag, -hz, 3.4)
        extrude_along_world(
            comp_zref, sk_tcut, all_profiles_collection(sk_tcut), "Z", 15.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation, [tnut_body]
        )

        # ------------------------------------------------------------------
        # Component 7: X_Motion_Reference (X-Rods, Front X-Motor, Pulley, Belt)
        # ------------------------------------------------------------------
        occ_xref = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_xref = occ_xref.component
        comp_xref.name = "X_Motion_Reference"

        x_rod_len = 244.0
        pl_xstart = create_world_plane(comp_xref, "X", x_rod_blind_x)
        for xr_name, rz in [("X_Smooth_Rod_Upper", x_rod_upper_z), ("X_Smooth_Rod_Lower", x_rod_lower_z)]:
            sk_xr = comp_xref.sketches.add(pl_xstart)
            add_world_circle(sk_xr, x_rod_blind_x, x_axis_y, rz, x_rod_dia)
            fxr = extrude_along_world(
                comp_xref, sk_xr, largest_profile(sk_xr), "X", x_rod_len,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            )
            fxr.bodies.item(0).name = xr_name

        motor_body = build_chamfered_motor_body(
            comp_xref, x_motor_x, x_motor_face_y, x_motor_z,
            nema17_size, -nema17_x_len, 4.5, "NEMA17_Front_X_Motor"
        )
        pl_mface = create_world_plane(comp_xref, "Y", x_motor_face_y)
        sk_pilot = comp_xref.sketches.add(pl_mface)
        add_world_circle(sk_pilot, x_motor_x, x_motor_face_y, x_motor_z, 22.0)
        extrude_along_world(
            comp_xref, sk_pilot, largest_profile(sk_pilot), "Y", 2.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [motor_body]
        )
        sk_shaft = comp_xref.sketches.add(pl_mface)
        add_world_circle(sk_shaft, x_motor_x, x_motor_face_y, x_motor_z, 5.0)
        extrude_along_world(
            comp_xref, sk_shaft, largest_profile(sk_shaft), "Y", 18.0,
            adsk.fusion.FeatureOperations.JoinFeatureOperation, [motor_body]
        )

        pl_pul = create_world_plane(comp_xref, "Y", x_axis_y - 3.5)
        sk_pul = comp_xref.sketches.add(pl_pul)
        add_world_circle(sk_pul, x_motor_x, x_axis_y - 3.5, x_motor_z, 10.2)
        f_pul = extrude_along_world(
            comp_xref, sk_pul, largest_profile(sk_pul), "Y", 7.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        pul_body = f_pul.bodies.item(0)
        pul_body.name = "GT2_16T_Pulley"
        for fy, fl_len in [(x_axis_y - 9.0, 5.5), (x_axis_y + 3.5, 1.0)]:
            pl_pf = create_world_plane(comp_xref, "Y", fy)
            sk_pf = comp_xref.sketches.add(pl_pf)
            add_world_circle(sk_pf, x_motor_x, fy, x_motor_z, 13.0 if fl_len > 2.0 else 16.0)
            extrude_along_world(
                comp_xref, sk_pf, largest_profile(sk_pf), "Y", fl_len,
                adsk.fusion.FeatureOperations.JoinFeatureOperation, [pul_body]
            )

        belt_half_z = belt_spacing / 2.0
        belt_thick = 1.38
        pl_belt = create_world_plane(comp_xref, "Y", x_axis_y - 3.0)
        sk_belt = comp_xref.sketches.add(pl_belt)
        for bz in (belt_half_z, -belt_half_z):
            add_world_rect(
                sk_belt,
                x_motor_x, x_axis_y - 3.0, bz - belt_thick / 2.0,
                210.0, x_axis_y - 3.0, bz + belt_thick / 2.0
            )
        f_belt = extrude_along_world(
            comp_xref, sk_belt, all_profiles_collection(sk_belt), "Y", 6.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        for bi in range(f_belt.bodies.count):
            f_belt.bodies.item(bi).name = f"GT2_Belt_Run_{bi + 1}"

        # ------------------------------------------------------------------
        # Component 8: Fasteners_Hardware (Installed M3/M2 SHCS & M3nS)
        # ------------------------------------------------------------------
        occ_hw = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp_hw = occ_hw.component
        comp_hw.name = "Fasteners_Hardware"

        idx = 1
        for sx in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                build_shcs_bolt(
                    comp_hw, x_motor_x + sx * hb, front_boss_ymin - 0.2, x_motor_z + sz * hb,
                    "Y", -1, 5.5, 3.0, 3.0, 10.0, f"M3x10_XMotor_{idx}"
                )
                idx += 1

        for i, (cx, cz) in enumerate(front_plate_bolts, start=1):
            build_shcs_bolt(
                comp_hw, cx, x_motor_face_y + 0.2, cz,
                "Y", 1, 5.5, 2.0, 3.0, 10.0, f"M3x10_FrontPlate_{i}"
            )
            build_square_nut(comp_hw, cx, front_plate_nut_y, cz, 5.5, 2.4, 5.5, 3.0, "Y", f"M3nS_FrontPlate_{i}")

        for i, (cx, cz) in enumerate(z_clamp_pts, start=1):
            build_shcs_bolt(
                comp_hw, cx, rear_clamp_ymax - 1.5, cz,
                "Y", -1, 5.5, 3.0, 3.0, 20.0, f"M3x20_ZClamp_{i}"
            )
            build_square_nut(comp_hw, cx, z_clamp_nut_y, cz, 5.5, 2.4, 5.5, 3.0, "Y", f"M3nS_ZClamp_{i}")

        idx = 1
        for cx in x_clamp_x_locs:
            for cz in x_clamp_z_locs:
                build_shcs_bolt(
                    comp_hw, cx, front_boss_ymin + 0.2, cz,
                    "Y", 1, 5.5, 3.0, 3.0, 12.0, f"M3x12_XRodClamp_{idx}"
                )
                build_square_nut(comp_hw, cx, x_clamp_nut_y, cz, 5.5, 2.4, 5.5, 3.0, "Y", f"M3nS_XRodClamp_{idx}")
                idx += 1

        idx = 1
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                bx, by = sx * tr8_diag, sy * tr8_diag
                build_shcs_bolt(
                    comp_hw, bx, by, -hz + 0.5,
                    "Z", 1, 5.5, 3.0, 3.0, 12.0, f"M3x12_TR8Nut_{idx}"
                )
                build_square_nut(comp_hw, bx, by, -21.0, 5.5, 5.5, 2.4, 3.0, "Z", f"M3nS_TR8Nut_{idx}")
                idx += 1

        for i, (cx, cz) in enumerate(ext_mount_pts, start=1):
            build_shcs_bolt(
                comp_hw, cx, ext_housing_ymax - 6.0, cz,
                "Y", -1, 5.5, 3.0, 3.0, 22.0, f"M3x22_ExtruderMount_{i}"
            )
            build_square_nut(comp_hw, cx, ext_mount_nut_y, cz, 5.5, 2.4, 5.5, 3.0, "Y", f"M3nS_ExtruderMount_{i}")

        for i, hy in enumerate(sw_hole_ys, start=1):
            build_shcs_bolt(
                comp_hw, sw_hole_x, hy, -hz + 0.2,
                "Z", 1, 3.8, 1.2, 2.0, 9.0, f"M2x9_ClickSwitch_{i}"
            )

        # ------------------------------------------------------------------
        # 3. Activate Root Component, Fit Viewport & Summary Dialog
        # ------------------------------------------------------------------
        design.activateRootComponent()
        app.activeViewport.fit()

        ui.messageBox(
            "Prusa MINI Z-Carriage (Thin Sliver Removed) Built!\n\n"
            "Clean Geometry Highlights:\n"
            f"• Front-Open Switch Pocket: Open to Y = {front_boss_ymin:.1f} mm, capped directly by flat 6.0 mm X_Motor_Front_Plate\n"
            f"• Straight Wire Bay & Port: 6.3 × 6.8 mm (X ∈ [{wire_bay_xmin:.1f}, {wire_bay_xmax:.1f}] mm) clear of LM8UU & nuts\n"
            f"• Coplanar Right Plane: X = +{z_carriage_xmax:.1f} mm across all carriage, plate, extruder & switch faces\n"
            f"• Dual 24 mm LM8UU per Z-Rod: 4× LM8UU (24.4 mm pockets, {z_bearing_center_rib:.1f} mm center rib)",
            "Prusa MINI Z-Carriage Complete"
        )

    except Exception:
        if ui:
            ui.messageBox(f"Script failed:\n{traceback.format_exc()}")