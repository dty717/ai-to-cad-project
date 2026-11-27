import adsk.core
import adsk.fusion
import traceback
import math


def mm(value_mm: float) -> float:
    """Convert millimeters to Fusion 360 internal units (centimeters)."""
    return value_mm * 0.1


def pt(x_mm: float, y_mm: float, z_mm: float = 0.0) -> adsk.core.Point3D:
    """Create a Point3D from millimeter coordinates."""
    return adsk.core.Point3D.create(mm(x_mm), mm(y_mm), mm(z_mm))


def collect_all_profiles(sketch: adsk.fusion.Sketch) -> adsk.core.ObjectCollection:
    """Return an ObjectCollection containing every profile in a sketch."""
    coll = adsk.core.ObjectCollection.create()
    for i in range(sketch.profiles.count):
        coll.add(sketch.profiles.item(i))
    return coll


def draw_circle(sketch: adsk.fusion.Sketch, x_mm: float, y_mm: float, dia_mm: float):
    """Draw a 2D circle on the sketch plane using world X/Y mm coordinates."""
    center = sketch.modelToSketchSpace(pt(x_mm, y_mm, 0.0))
    center.z = 0.0
    sketch.sketchCurves.sketchCircles.addByCenterRadius(center, mm(dia_mm / 2.0))


def sketch_pt_2d(sketch: adsk.fusion.Sketch, x_mm: float, y_mm: float) -> adsk.core.Point3D:
    """Project a world X/Y mm point onto an XY-parallel sketch plane."""
    p = sketch.modelToSketchSpace(pt(x_mm, y_mm, 0.0))
    p.z = 0.0
    return p


def add_extrude(
    comp: adsk.fusion.Component,
    sketch: adsk.fusion.Sketch,
    distance_mm: float,
    operation: adsk.fusion.FeatureOperations,
    direction: adsk.fusion.ExtentDirections = adsk.fusion.ExtentDirections.PositiveExtentDirection,
):
    """Extrude all profiles in a sketch by distance_mm."""
    extrudes = comp.features.extrudeFeatures
    profiles = collect_all_profiles(sketch)
    ext_input = extrudes.createInput(profiles, operation)

    dist_val = adsk.core.ValueInput.createByReal(mm(distance_mm))
    ext_input.setOneSideExtent(
        adsk.fusion.DistanceExtentDefinition.create(dist_val),
        direction,
    )
    return extrudes.add(ext_input)


def cut_polyline_slot(
    comp: adsk.fusion.Component,
    points_xy: list,
    width_mm: float,
    depth_mm: float,
    sketch_prefix: str,
    base_plane: adsk.fusion.ConstructionPlane = None,
    direction: adsk.fusion.ExtentDirections = adsk.fusion.ExtentDirections.PositiveExtentDirection,
    cut_end_joint: bool = True,
):
    """Cut a continuous flat-bottomed slot along a 2D polyline on base_plane (or XY plane)."""
    half_w = width_mm / 2.0
    target_plane = base_plane if base_plane is not None else comp.xYConstructionPlane

    for idx in range(len(points_xy) - 1):
        x1, y1 = points_xy[idx]
        x2, y2 = points_xy[idx + 1]
        dx = x2 - x1
        dy = y2 - y1
        seg_len = math.hypot(dx, dy)
        if seg_len < 1e-6:
            continue
        nx = -dy / seg_len * half_w
        ny = dx / seg_len * half_w

        sk = comp.sketches.add(target_plane)
        sk.name = f"{sketch_prefix}_Seg_{idx + 1}"
        lines = sk.sketchCurves.sketchLines
        p1 = sketch_pt_2d(sk, x1 + nx, y1 + ny)
        p2 = sketch_pt_2d(sk, x2 + nx, y2 + ny)
        p3 = sketch_pt_2d(sk, x2 - nx, y2 - ny)
        p4 = sketch_pt_2d(sk, x1 - nx, y1 - ny)
        l1 = lines.addByTwoPoints(p1, p2)
        l2 = lines.addByTwoPoints(l1.endSketchPoint, p3)
        l3 = lines.addByTwoPoints(l2.endSketchPoint, p4)
        lines.addByTwoPoints(l3.endSketchPoint, l1.startSketchPoint)

        add_extrude(
            comp,
            sk,
            depth_mm,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            direction,
        )

    joint_pts = points_xy if cut_end_joint else points_xy[:-1]
    for idx, (px, py) in enumerate(joint_pts):
        sk_j = comp.sketches.add(target_plane)
        sk_j.name = f"{sketch_prefix}_Joint_{idx + 1}"
        draw_circle(sk_j, px, py, width_mm)
        add_extrude(
            comp,
            sk_j,
            depth_mm,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            direction,
        )


def create_offset_xy_plane(comp: adsk.fusion.Component, z_mm: float) -> adsk.fusion.ConstructionPlane:
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(
        comp.xYConstructionPlane,
        adsk.core.ValueInput.createByReal(mm(z_mm)),
    )
    return planes.add(plane_input)


def create_offset_yz_plane(comp: adsk.fusion.Component, x_world_mm: float) -> adsk.fusion.ConstructionPlane:
    """Create a plane parallel to YZ at a specific world X coordinate."""
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    normal_x = comp.yZConstructionPlane.geometry.normal.x
    offset = x_world_mm / normal_x
    plane_input.setByOffset(
        comp.yZConstructionPlane,
        adsk.core.ValueInput.createByReal(mm(offset)),
    )
    return planes.add(plane_input)


def add_subcomponent(root: adsk.fusion.Component, name: str) -> adsk.fusion.Component:
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    return comp


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # 1. Create a brand-new Fusion 360 design document before editing
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("Failed to initialize a new Fusion 360 design.")
            return

        try:
            design.fusionUnitsManager.distanceDisplayUnits = (
                adsk.fusion.DistanceDisplayUnits.MillimeterDistanceDisplayUnits
            )
        except Exception:
            pass

        root = design.rootComponent

        # ---------------------------------------------------------------------
        # Parametric Dimensions (mm) - Measured Plate + 17HS4401S (0° Top Mount)
        # ---------------------------------------------------------------------
        extrusion_size = 30.0          # X: -15.0 .. +15.0, Y: 0.0 .. 30.0 mm
        extrusion_len = 289.0

        nema17_w = 44.0                # X: -22.0 .. +22.0 (>= 42.3 mm 17HS4401S face)
        total_height = 17.0            # Z:   0.0 .. +17.0 mm above 3030

        # Measured 8mm smooth rod positions (40.0 / 60.0 / 80.0 mm from Y=0)
        # Rod length equals extrusion_len; bottom sits 4.5 mm deep in opposite plate hole -> Z=-4.5..-293.5
        rod_dia = 8.0
        rod_edge_from_3030 = 6.0                           # Measured 39.83 -> 40.0 mm
        rod_to_rod_spacing = 40.0                          # Measured 39.97 -> 40.0 mm
        opposite_rod_hole_depth = 4.5                      # 4-5 mm deep hole at bottom plate
        rod_len = extrusion_len                            # 289.0 mm (same height as Extrusion_3030)
        rod_top_z = -opposite_rod_hole_depth               # -4.5 mm
        rod_bore_dia = 8.2
        rod_bore_depth = 13.5                              # Socket depth into lower block (Z=-18.0..-4.5)
        lower_drop_h = opposite_rod_hole_depth + rod_bore_depth  # 18.0 mm below Z=0 on rod/motor end
        lower_start_y = 32.0                               # 2.0 mm clearance in front of Extrusion_3030

        rod_b_y = extrusion_size + rod_edge_from_3030 + rod_dia / 2.0  # 40.0 mm
        motor_y = rod_b_y + rod_to_rod_spacing / 2.0                   # 60.0 mm
        rod_a_y = rod_b_y + rod_to_rod_spacing                         # 80.0 mm
        rod_pts = [(0.0, rod_a_y), (0.0, rod_b_y)]

        # 0°-oriented 17HS4401S (NEMA 17) mounted on top (+Z)
        motor_body_size = 42.3
        motor_body_chamf = 4.0
        motor_body_len = 40.0
        nema17_bolt_half = 15.5                            # 31.0 x 31.0 mm M3 pattern
        motor_pilot_dia = 22.6
        motor_pilot_depth = 3.0
        motor_boss_dia = 22.0
        motor_boss_h = 2.0
        leadscrew_dia = 8.0
        leadscrew_clear_dia = 15.0                         # Enlarged center leadscrew bore
        leadscrew_len = 295.0

        m3_clear_dia = 3.4
        m3_cbore_dia = 6.4                                 # Enlarged M3 socket head counterbore
        m3_flange_top_z = 5.0                              # 12.0 mm flange -> 4.0 mm engagement with M3x16

        motor_bolt_pts = [
            (-nema17_bolt_half, motor_y - nema17_bolt_half),
            (nema17_bolt_half, motor_y - nema17_bolt_half),
            (-nema17_bolt_half, motor_y + nema17_bolt_half),
            (nema17_bolt_half, motor_y + nema17_bolt_half),
        ]

        # Nose arc around Rod A (R=9.5 -> 5.4 mm outer wall)
        nose_r = 9.5
        nose_cy = rod_a_y                                  # 80.0 mm
        total_length = nose_cy + nose_r                    # 89.5 mm
        shoulder_y = motor_y + 21.5                        # 81.5 mm (supports full 42.3 mm motor)

        # 4x M5 extrusion corner screws (measured 22.8 x 22.8 mm pitch) + round lobes
        m5_half_pitch = 11.4
        ear_back_y = 15.0 - m5_half_pitch                  # 3.6 mm
        ear_front_y = 15.0 + m5_half_pitch                 # 26.4 mm
        m5_holes = [
            (m5_half_pitch, ear_back_y),                   # ( 11.4,  3.6)
            (-m5_half_pitch, ear_back_y),                  # (-11.4,  3.6)
            (m5_half_pitch, ear_front_y),                  # ( 11.4, 26.4)
            (-m5_half_pitch, ear_front_y),                 # (-11.4, 26.4)
        ]
        m5_clear_dia = 5.4
        m5_cbore_dia = 9.6                                 # Updated M5 counterbore diameter
        m5_cbore_depth = 11.0                              # Leaves 6.0 mm flange (10 mm M5x16r tap depth)
        ear_r = 6.8                                        # Ø13.6 mm round lobes (2.0 mm wall around Ø9.6 cbore)
        waist_x = 16.0                                     # Waist between front & back lobes (outside 3030)

        # Top wire groove (Z=12.5..17) along X=0 corridor into +X 3030 T-slot
        groove_width = 6.0
        groove_depth = 4.5
        groove_path = [
            (0.0, 34.5),                                   # Exits in front of 17HS4401S -Y face
            (0.0, 15.0),                                   # Straight down center between ±11.4 M5 heads
            (waist_x + 0.5, 15.0),                         # Exits through +X waist into 3030 T-slot
        ]

        # Pinch slits + horizontal M3x30 rod-clamp bolts & M3nS square nuts inside rod grip zone (Z=-18..-4.5)
        pinch_slit_w = 1.2
        pinch_slit_top_z = 2.0                             # Z=-18..+2 (keeps top 15 mm rigid under motor)
        side_hole_ys = [50.0, 70.0]                        # Centered between rods & leadscrew
        side_hole_z = -11.0                                # Centered on Z=-18..-4.5 rod socket zone
        side_cbore_dia = 5.8
        side_cbore_x_seat = -19.0                          # Outside -18.7 motor cbore; M3x30 reaches X=+11.0
        m3ns_width = 5.6
        m3ns_thickness = 2.2
        m3ns_x_center = 6.5                                # Clears slit (0.6), leadscrew (6.5 R), & +X motor cbore (12.3)
        m3ns_top_z = side_hole_z + m3ns_width / 2.0        # -8.2 mm

        # =====================================================================
        # COMPONENT 1: MINI_z_top (Z-Axis Top Mount)
        # =====================================================================
        comp_top = add_subcomponent(root, "MINI_z_top")

        sk_body = comp_top.sketches.add(comp_top.xYConstructionPlane)
        sk_body.name = "Main_Body_Profile"
        lines = sk_body.sketchCurves.sketchLines
        arcs = sk_body.sketchCurves.sketchArcs

        # 4 rounded corner lobe coordinates around (±11.4, 3.6) and (±11.4, 26.4)
        back_flat_x = m5_half_pitch - math.sqrt(ear_r**2 - ear_back_y**2)
        ear_back_waist_y = ear_back_y + math.sqrt(ear_r**2 - (waist_x - m5_half_pitch)**2)
        ear_front_waist_y = ear_front_y - math.sqrt(ear_r**2 - (waist_x - m5_half_pitch)**2)
        flare_x = 16.8
        ear_front_flare_y = ear_front_y + math.sqrt(ear_r**2 - (flare_x - m5_half_pitch)**2)

        a1 = math.atan2(-ear_back_y, back_flat_x - m5_half_pitch)
        a2 = math.atan2(ear_back_waist_y - ear_back_y, waist_x - m5_half_pitch)
        am_back = (a1 + a2) / 2.0
        mid_br_x = m5_half_pitch + ear_r * math.cos(am_back)
        mid_br_y = ear_back_y + ear_r * math.sin(am_back)

        # Exact tangent point from (nema17_w/2, shoulder_y) to nose circle (0, nose_cy, r=nose_r)
        sx = nema17_w / 2.0
        sy = shoulder_y
        dist_s = math.hypot(sx, sy - nose_cy)
        alpha = math.atan2(sy - nose_cy, sx) + math.acos(nose_r / dist_s)
        tan_x = nose_r * math.cos(alpha)
        tan_y = nose_cy + nose_r * math.sin(alpha)
        motor_start_y = motor_y - 21.5                     # 38.5 mm

        # Counterclockwise perimeter with 4 rounded extrusion lobes
        first_line = lines.addByTwoPoints(
            pt(-back_flat_x, 0.0),
            pt(back_flat_x, 0.0),
        )
        br_arc = arcs.addByThreePoints(
            first_line.endSketchPoint,
            pt(mid_br_x, mid_br_y),
            pt(waist_x, ear_back_waist_y),
        )
        r_waist = lines.addByTwoPoints(
            br_arc.endSketchPoint,
            pt(waist_x, ear_front_waist_y),
        )
        fr_arc = arcs.addByThreePoints(
            r_waist.endSketchPoint,
            pt(m5_half_pitch + ear_r, ear_front_y),
            pt(flare_x, ear_front_flare_y),
        )
        prev = fr_arc
        for px, py in [
            (sx, motor_start_y),
            (sx, shoulder_y),
            (tan_x, tan_y),
        ]:
            prev = lines.addByTwoPoints(prev.endSketchPoint, pt(px, py))

        nose_arc = arcs.addByThreePoints(
            prev.endSketchPoint,
            pt(0.0, total_length),
            pt(-tan_x, tan_y),
        )

        prev = nose_arc
        for px, py in [
            (-sx, shoulder_y),
            (-sx, motor_start_y),
            (-flare_x, ear_front_flare_y),
        ]:
            prev = lines.addByTwoPoints(prev.endSketchPoint, pt(px, py))

        fl_arc = arcs.addByThreePoints(
            prev.endSketchPoint,
            pt(-(m5_half_pitch + ear_r), ear_front_y),
            pt(-waist_x, ear_front_waist_y),
        )
        l_waist = lines.addByTwoPoints(
            fl_arc.endSketchPoint,
            pt(-waist_x, ear_back_waist_y),
        )
        arcs.addByThreePoints(
            l_waist.endSketchPoint,
            pt(-mid_br_x, mid_br_y),
            first_line.startSketchPoint,
        )

        body_ext = add_extrude(
            comp_top,
            sk_body,
            total_height,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )
        main_body = body_ext.bodies.item(0)
        main_body.name = "MINI_z_top_Body"

        # Lower downward rod-socket block (Z=-18.0..0.0, Y>=32.0 so it clears Extrusion_3030)
        t_flare = (lower_start_y - ear_front_flare_y) / (motor_start_y - ear_front_flare_y)
        flare_lower_x = flare_x + t_flare * (sx - flare_x)

        sk_lower = comp_top.sketches.add(comp_top.xYConstructionPlane)
        sk_lower.name = "Lower_Rod_Mount_Block"
        l_lines = sk_lower.sketchCurves.sketchLines
        l_arcs = sk_lower.sketchCurves.sketchArcs
        l_first = l_lines.addByTwoPoints(
            pt(-flare_lower_x, lower_start_y),
            pt(flare_lower_x, lower_start_y),
        )
        l_prev = l_first
        for px, py in [
            (sx, motor_start_y),
            (sx, shoulder_y),
            (tan_x, tan_y),
        ]:
            l_prev = l_lines.addByTwoPoints(l_prev.endSketchPoint, pt(px, py))
        l_nose = l_arcs.addByThreePoints(
            l_prev.endSketchPoint,
            pt(0.0, total_length),
            pt(-tan_x, tan_y),
        )
        l_prev = l_nose
        for px, py in [
            (-sx, shoulder_y),
            (-sx, motor_start_y),
        ]:
            l_prev = l_lines.addByTwoPoints(l_prev.endSketchPoint, pt(px, py))
        l_lines.addByTwoPoints(l_prev.endSketchPoint, l_first.startSketchPoint)

        add_extrude(
            comp_top,
            sk_lower,
            lower_drop_h,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        # Smooth vertical corner fillets along motor shoulders, flare corners, and ear-waist transitions
        for y_min, y_max, f_rad in [(36.0, 83.0, 3.0), (7.0, 23.0, 2.0)]:
            try:
                fillets = comp_top.features.filletFeatures
                edge_coll = adsk.core.ObjectCollection.create()
                for edge in main_body.edges:
                    p1 = edge.startVertex.geometry
                    p2 = edge.endVertex.geometry
                    if abs(p1.x - p2.x) < 1e-4 and abs(p1.y - p2.y) < 1e-4 and abs(p1.z - p2.z) > mm(10.0):
                        if mm(y_min) < p1.y < mm(y_max):
                            edge_coll.add(edge)
                if edge_coll.count > 0:
                    f_input = fillets.createInput()
                    f_input.addConstantRadiusEdgeSet(
                        edge_coll,
                        adsk.core.ValueInput.createByReal(mm(f_rad)),
                        True,
                    )
                    fillets.add(f_input)
            except Exception:
                pass

        try:
            fillets = comp_top.features.filletFeatures
            top_edges = adsk.core.ObjectCollection.create()
            for edge in main_body.edges:
                if edge.startVertex == edge.endVertex:
                    continue
                p1 = edge.startVertex.geometry
                p2 = edge.endVertex.geometry
                if abs(p1.z - mm(total_height)) < 1e-4 and abs(p2.z - mm(total_height)) < 1e-4:
                    top_edges.add(edge)
            if top_edges.count > 0:
                top_f_input = fillets.createInput()
                top_f_input.addConstantRadiusEdgeSet(
                    top_edges,
                    adsk.core.ValueInput.createByReal(mm(0.8)),
                    True,
                )
                fillets.add(top_f_input)
        except Exception:
            pass

        top_plane = create_offset_xy_plane(comp_top, total_height)
        bot_lower_plane = create_offset_xy_plane(comp_top, -lower_drop_h)

        # 8mm smooth rod blind sockets (13.5 mm deep upward from Z=-18.0 to Z=-4.5)
        sk_rods = comp_top.sketches.add(bot_lower_plane)
        sk_rods.name = "Smooth_Rod_Sockets"
        for rx, ry in rod_pts:
            draw_circle(sk_rods, rx, ry, rod_bore_dia)
        add_extrude(
            comp_top,
            sk_rods,
            rod_bore_depth,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )

        # 17HS4401S pilot pocket (3mm deep on top) + Ø13.0 mm leadscrew through-bore
        sk_pilot = comp_top.sketches.add(top_plane)
        sk_pilot.name = "NEMA17_Pilot_Pocket"
        draw_circle(sk_pilot, 0.0, motor_y, motor_pilot_dia)
        add_extrude(
            comp_top,
            sk_pilot,
            motor_pilot_depth,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        sk_lead = comp_top.sketches.add(top_plane)
        sk_lead.name = "TR8_Leadscrew_Clearance_Bore"
        draw_circle(sk_lead, 0.0, motor_y, leadscrew_clear_dia)
        add_extrude(
            comp_top,
            sk_lead,
            total_height + lower_drop_h + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        # 4x M3 through-holes & Ø6.4 mm bottom counterbores (Z=-18.0..+5.0 for M3x16)
        sk_m3_motor = comp_top.sketches.add(bot_lower_plane)
        sk_m3_motor.name = "NEMA17_0deg_M3_Through_Holes"
        for bx, by in motor_bolt_pts:
            draw_circle(sk_m3_motor, bx, by, m3_clear_dia)
        add_extrude(
            comp_top,
            sk_m3_motor,
            total_height + lower_drop_h + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )

        sk_m3_cbore = comp_top.sketches.add(bot_lower_plane)
        sk_m3_cbore.name = "NEMA17_0deg_M3_Counterbores"
        for bx, by in motor_bolt_pts:
            draw_circle(sk_m3_cbore, bx, by, m3_cbore_dia)
        add_extrude(
            comp_top,
            sk_m3_cbore,
            lower_drop_h + m3_flange_top_z,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )

        # 3030 extrusion 4x M5 mounting holes & Ø9.6 mm counterbores (22.8 x 22.8 mm pitch)
        sk_m5_thru = comp_top.sketches.add(top_plane)
        sk_m5_thru.name = "Extrusion_M5_Through_Holes"
        for hx, hy in m5_holes:
            draw_circle(sk_m5_thru, hx, hy, m5_clear_dia)
        add_extrude(
            comp_top,
            sk_m5_thru,
            total_height + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        sk_m5_cbore = comp_top.sketches.add(top_plane)
        sk_m5_cbore.name = "Extrusion_M5_Counterbores"
        for hx, hy in m5_holes:
            draw_circle(sk_m5_cbore, hx, hy, m5_cbore_dia)
        add_extrude(
            comp_top,
            sk_m5_cbore,
            m5_cbore_depth,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        # Top-side motor wire groove (Z=12.5..17); skip end-joint at open +X exit
        cut_polyline_slot(
            comp_top,
            groove_path,
            groove_width,
            groove_depth,
            "Motor_Cable_Groove_Top",
            base_plane=top_plane,
            direction=adsk.fusion.ExtentDirections.NegativeExtentDirection,
            cut_end_joint=False,
        )

        # Vertical pass-through U-slot (Z=0..17) into +X 3030 T-slot
        half_gw = groove_width / 2.0
        sk_drop = comp_top.sketches.add(top_plane)
        sk_drop.name = "Motor_Cable_Drop_Slot"
        d_lines = sk_drop.sketchCurves.sketchLines
        p_tr = sketch_pt_2d(sk_drop, waist_x + 0.5, 15.0 + half_gw)
        p_tl = sketch_pt_2d(sk_drop, 10.0, 15.0 + half_gw)
        p_mid = sketch_pt_2d(sk_drop, 10.0 - half_gw, 15.0)
        p_bl = sketch_pt_2d(sk_drop, 10.0, 15.0 - half_gw)
        p_br = sketch_pt_2d(sk_drop, waist_x + 0.5, 15.0 - half_gw)
        l_top = d_lines.addByTwoPoints(p_tr, p_tl)
        arc_end = sk_drop.sketchCurves.sketchArcs.addByThreePoints(
            l_top.endSketchPoint,
            p_mid,
            p_bl,
        )
        l_bot = d_lines.addByTwoPoints(arc_end.endSketchPoint, p_br)
        d_lines.addByTwoPoints(l_bot.endSketchPoint, l_top.startSketchPoint)
        add_extrude(
            comp_top,
            sk_drop,
            total_height + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        # Horizontal rod-clamp pinch slits along X=0 (Z=-18.0..+2.0 around rod sockets)
        sk_slits = comp_top.sketches.add(bot_lower_plane)
        sk_slits.name = "Rod_Clamp_Pinch_Slits"
        lead_r = leadscrew_clear_dia / 2.0
        sk_slits.sketchCurves.sketchLines.addTwoPointRectangle(
            sketch_pt_2d(sk_slits, -pinch_slit_w / 2.0, rod_b_y),
            sketch_pt_2d(sk_slits, pinch_slit_w / 2.0, motor_y - lead_r),
        )
        sk_slits.sketchCurves.sketchLines.addTwoPointRectangle(
            sketch_pt_2d(sk_slits, -pinch_slit_w / 2.0, motor_y + lead_r),
            sketch_pt_2d(sk_slits, pinch_slit_w / 2.0, rod_a_y),
        )
        add_extrude(
            comp_top,
            sk_slits,
            lower_drop_h + pinch_slit_top_z,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )

        # M3nS square nut pockets on +X side (X=+6.5, Z=-18.0..-8.2 -> clear of motor & pilot)
        sk_nuts = comp_top.sketches.add(bot_lower_plane)
        sk_nuts.name = "M3nS_Nut_Pockets"
        for sy in side_hole_ys:
            sk_nuts.sketchCurves.sketchLines.addTwoPointRectangle(
                sketch_pt_2d(sk_nuts, m3ns_x_center - m3ns_thickness / 2.0, sy - m3ns_width / 2.0),
                sketch_pt_2d(sk_nuts, m3ns_x_center + m3ns_thickness / 2.0, sy + m3ns_width / 2.0),
            )
        add_extrude(
            comp_top,
            sk_nuts,
            m3ns_top_z + lower_drop_h,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )

        # Horizontal M3x30 clamp through-holes + left-side spotface counterbores (at Z=-11.0 mm)
        side_x_start = -nema17_w / 2.0 - 0.5
        side_plane = create_offset_yz_plane(comp_top, side_x_start)
        to_pos_x = (
            adsk.fusion.ExtentDirections.PositiveExtentDirection
            if side_plane.geometry.normal.x > 0
            else adsk.fusion.ExtentDirections.NegativeExtentDirection
        )

        sk_side_thru = comp_top.sketches.add(side_plane)
        sk_side_thru.name = "Side_Clamp_M3_Through_Holes"
        for sy in side_hole_ys:
            c3d = pt(side_x_start, sy, side_hole_z)
            c2d = sk_side_thru.modelToSketchSpace(c3d)
            c2d.z = 0.0
            sk_side_thru.sketchCurves.sketchCircles.addByCenterRadius(
                c2d, mm(m3_clear_dia / 2.0)
            )
        add_extrude(
            comp_top,
            sk_side_thru,
            nema17_w + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            to_pos_x,
        )

        sk_side_cbore = comp_top.sketches.add(side_plane)
        sk_side_cbore.name = "Side_Clamp_M3_Counterbores"
        for sy in side_hole_ys:
            c3d = pt(side_x_start, sy, side_hole_z)
            c2d = sk_side_cbore.modelToSketchSpace(c3d)
            c2d.z = 0.0
            sk_side_cbore.sketchCurves.sketchCircles.addByCenterRadius(
                c2d, mm(side_cbore_dia / 2.0)
            )
        add_extrude(
            comp_top,
            sk_side_cbore,
            side_cbore_x_seat - side_x_start,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            to_pos_x,
        )

        # =====================================================================
        # COMPONENT 2: 3030 Aluminum Extrusion (289 mm)
        # =====================================================================
        comp_extr = add_subcomponent(root, "Extrusion_3030")
        sk_extr = comp_extr.sketches.add(comp_extr.xYConstructionPlane)
        sk_extr.name = "Extrusion_3030_Block"
        sk_extr.sketchCurves.sketchLines.addTwoPointRectangle(
            pt(-extrusion_size / 2.0, 0.0),
            pt(extrusion_size / 2.0, extrusion_size),
        )
        extr_body = add_extrude(
            comp_extr,
            sk_extr,
            extrusion_len,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        ).bodies.item(0)
        extr_body.name = "Extrusion_3030_Profile"

        sk_slots = comp_extr.sketches.add(comp_extr.xYConstructionPlane)
        sk_slots.name = "T_Slots"
        sl_lines = sk_slots.sketchCurves.sketchLines
        sl_lines.addTwoPointRectangle(pt(-15.5, 11.0), pt(-7.0, 19.0))   # -X slot
        sl_lines.addTwoPointRectangle(pt(7.0, 11.0), pt(15.5, 19.0))     # +X slot
        sl_lines.addTwoPointRectangle(pt(-4.0, -0.5), pt(4.0, 8.0))      # -Y slot
        sl_lines.addTwoPointRectangle(pt(-4.0, 22.0), pt(4.0, 30.5))     # +Y slot
        add_extrude(
            comp_extr,
            sk_slots,
            extrusion_len + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        sk_extr_c = comp_extr.sketches.add(comp_extr.xYConstructionPlane)
        sk_extr_c.name = "Extrusion_Center_Hole"
        draw_circle(sk_extr_c, 0.0, 15.0, 6.8)
        add_extrude(
            comp_extr,
            sk_extr_c,
            extrusion_len + 1.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        sk_extr_m5 = comp_extr.sketches.add(comp_extr.xYConstructionPlane)
        sk_extr_m5.name = "Extrusion_M5_Taps"
        for hx, hy in m5_holes:
            draw_circle(sk_extr_m5, hx, hy, 4.2)
        add_extrude(
            comp_extr,
            sk_extr_m5,
            16.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        # =====================================================================
        # COMPONENT 3: Two 8mm Smooth Rods (289 mm long, Z=-4.5..-293.5 mm)
        # =====================================================================
        comp_rods = add_subcomponent(root, "Smooth_Rods_8mm")
        rod_top_plane = create_offset_xy_plane(comp_rods, rod_top_z)
        sk_smooth_rods = comp_rods.sketches.add(rod_top_plane)
        sk_smooth_rods.name = "Smooth_Rods_Profile"
        for rx, ry in rod_pts:
            draw_circle(sk_smooth_rods, rx, ry, rod_dia)
        rods_ext = add_extrude(
            comp_rods,
            sk_smooth_rods,
            rod_len,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )
        rods_ext.bodies.item(0).name = "Smooth_Rod_A_Outer"
        rods_ext.bodies.item(1).name = "Smooth_Rod_B_Inner"

        # =====================================================================
        # COMPONENT 4: Two LM8LUU Linear Bearings (Ø15 x 45 mm)
        # =====================================================================
        comp_brg = add_subcomponent(root, "LM8LUU_Bearings")
        brg_plane = create_offset_xy_plane(comp_brg, -55.0)
        sk_brg = comp_brg.sketches.add(brg_plane)
        sk_brg.name = "LM8LUU_Outer"
        for rx, ry in rod_pts:
            draw_circle(sk_brg, rx, ry, 15.0)
        brg_ext = add_extrude(
            comp_brg,
            sk_brg,
            45.0,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )
        brg_ext.bodies.item(0).name = "LM8LUU_A_Outer"
        brg_ext.bodies.item(1).name = "LM8LUU_B_Inner"

        sk_brg_id = comp_brg.sketches.add(brg_plane)
        sk_brg_id.name = "LM8LUU_Bore"
        for rx, ry in rod_pts:
            draw_circle(sk_brg_id, rx, ry, 8.2)
        add_extrude(
            comp_brg,
            sk_brg_id,
            46.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        # =====================================================================
        # COMPONENT 5: 0° 17HS4401S (NEMA 17) Z-Axis Motor (on Top +Z) & TR8 Leadscrew
        # =====================================================================
        comp_motor = add_subcomponent(root, "NEMA17_17HS4401S_0deg")
        motor_mount_plane = create_offset_xy_plane(comp_motor, total_height)

        sk_motor = comp_motor.sketches.add(motor_mount_plane)
        sk_motor.name = "Motor_Body_0deg"
        m_lines = sk_motor.sketchCurves.sketchLines
        hs = motor_body_size / 2.0
        ch = motor_body_chamf
        oct_pts = [
            (hs - ch, motor_y - hs),
            (hs, motor_y - hs + ch),
            (hs, motor_y + hs - ch),
            (hs - ch, motor_y + hs),
            (-hs + ch, motor_y + hs),
            (-hs, motor_y + hs - ch),
            (-hs, motor_y - hs + ch),
            (-hs + ch, motor_y - hs),
        ]
        m_first = m_lines.addByTwoPoints(
            sketch_pt_2d(sk_motor, *oct_pts[0]),
            sketch_pt_2d(sk_motor, *oct_pts[1]),
        )
        m_prev = m_first
        for p_xy in oct_pts[2:]:
            m_prev = m_lines.addByTwoPoints(m_prev.endSketchPoint, sketch_pt_2d(sk_motor, *p_xy))
        m_lines.addByTwoPoints(m_prev.endSketchPoint, m_first.startSketchPoint)

        motor_ext = add_extrude(
            comp_motor,
            sk_motor,
            motor_body_len,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )
        motor_body = motor_ext.bodies.item(0)
        motor_body.name = "NEMA17_17HS4401S_Body"

        sk_boss = comp_motor.sketches.add(motor_mount_plane)
        sk_boss.name = "Motor_Pilot_Boss"
        draw_circle(sk_boss, 0.0, motor_y, motor_boss_dia)
        add_extrude(
            comp_motor,
            sk_boss,
            motor_boss_h,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        sk_screw = comp_motor.sketches.add(motor_mount_plane)
        sk_screw.name = "TR8_Leadscrew"
        draw_circle(sk_screw, 0.0, motor_y, leadscrew_dia)
        add_extrude(
            comp_motor,
            sk_screw,
            leadscrew_len + motor_boss_h,
            adsk.fusion.FeatureOperations.JoinFeatureOperation,
            adsk.fusion.ExtentDirections.NegativeExtentDirection,
        )

        sk_m_taps = comp_motor.sketches.add(motor_mount_plane)
        sk_m_taps.name = "Motor_M3_Holes"
        for mx, my in motor_bolt_pts:
            draw_circle(sk_m_taps, mx, my, 2.6)
        add_extrude(
            comp_motor,
            sk_m_taps,
            6.0,
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            adsk.fusion.ExtentDirections.PositiveExtentDirection,
        )

        # =====================================================================
        # COMPONENT 6: Fasteners (4x M3x16, 4x M5x16r, 2x M3x30, 2x M3nS)
        # =====================================================================
        comp_hw = add_subcomponent(root, "Fasteners_Hardware")

        # 4x M3x16 bolts enter from bottom counterbore seat (Z=+5) upward into 17HS4401S (Z=17..21)
        m3_seat_plane = create_offset_xy_plane(comp_hw, m3_flange_top_z)
        for idx, (bx, by) in enumerate(motor_bolt_pts):
            sk_h = comp_hw.sketches.add(m3_seat_plane)
            sk_h.name = f"M3x16_Head_{idx + 1}"
            draw_circle(sk_h, bx, by, 5.4)
            head_body = add_extrude(
                comp_hw,
                sk_h,
                3.0,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                adsk.fusion.ExtentDirections.NegativeExtentDirection,
            ).bodies.item(0)
            head_body.name = f"M3x16_Bolt_{idx + 1}"

            sk_s = comp_hw.sketches.add(m3_seat_plane)
            sk_s.name = f"M3x16_Shaft_{idx + 1}"
            draw_circle(sk_s, bx, by, 3.0)
            add_extrude(
                comp_hw,
                sk_s,
                16.0,
                adsk.fusion.FeatureOperations.JoinFeatureOperation,
                adsk.fusion.ExtentDirections.PositiveExtentDirection,
            )

        # 4x M5x16r extrusion bolts seated at Z=6.0
        m5_seat_plane = create_offset_xy_plane(comp_hw, total_height - m5_cbore_depth)
        for idx, (hx, hy) in enumerate(m5_holes):
            sk_h = comp_hw.sketches.add(m5_seat_plane)
            sk_h.name = f"M5x16r_Head_{idx + 1}"
            draw_circle(sk_h, hx, hy, 8.8)
            m5_body = add_extrude(
                comp_hw,
                sk_h,
                3.0,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                adsk.fusion.ExtentDirections.PositiveExtentDirection,
            ).bodies.item(0)
            m5_body.name = f"M5x16r_Bolt_{idx + 1}"

            sk_s = comp_hw.sketches.add(m5_seat_plane)
            sk_s.name = f"M5x16r_Shaft_{idx + 1}"
            draw_circle(sk_s, hx, hy, 5.0)
            add_extrude(
                comp_hw,
                sk_s,
                16.0,
                adsk.fusion.FeatureOperations.JoinFeatureOperation,
                adsk.fusion.ExtentDirections.NegativeExtentDirection,
            )

        # 2x M3nS square nuts at X=+6.5 (Y=50.0, 70.0, Z=-11.0 -> inside lower rod clamp zone)
        nut_bot_plane = create_offset_xy_plane(comp_hw, side_hole_z - 2.7)
        for idx, sy in enumerate(side_hole_ys):
            sk_nut = comp_hw.sketches.add(nut_bot_plane)
            sk_nut.name = f"M3nS_Nut_{idx + 1}"
            sk_nut.sketchCurves.sketchLines.addTwoPointRectangle(
                sketch_pt_2d(sk_nut, m3ns_x_center - 0.9, sy - 2.7),
                sketch_pt_2d(sk_nut, m3ns_x_center + 0.9, sy + 2.7),
            )
            nut_body = add_extrude(
                comp_hw,
                sk_nut,
                5.4,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                adsk.fusion.ExtentDirections.PositiveExtentDirection,
            ).bodies.item(0)
            nut_body.name = f"M3nS_Nut_{idx + 1}"

        # 2x M3x30 clamp screws entering from X=-19.0 through M3nS nuts at X=+6.5
        hw_side_plane = create_offset_yz_plane(comp_hw, side_cbore_x_seat)
        hw_to_pos_x = (
            adsk.fusion.ExtentDirections.PositiveExtentDirection
            if hw_side_plane.geometry.normal.x > 0
            else adsk.fusion.ExtentDirections.NegativeExtentDirection
        )
        hw_to_neg_x = (
            adsk.fusion.ExtentDirections.NegativeExtentDirection
            if hw_side_plane.geometry.normal.x > 0
            else adsk.fusion.ExtentDirections.PositiveExtentDirection
        )
        for idx, sy in enumerate(side_hole_ys):
            sk_cs = comp_hw.sketches.add(hw_side_plane)
            sk_cs.name = f"M3x30_Shaft_{idx + 1}"
            c2d = sk_cs.modelToSketchSpace(pt(side_cbore_x_seat, sy, side_hole_z))
            c2d.z = 0.0
            sk_cs.sketchCurves.sketchCircles.addByCenterRadius(c2d, mm(1.5))
            c_body = add_extrude(
                comp_hw,
                sk_cs,
                30.0,
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                hw_to_pos_x,
            ).bodies.item(0)
            c_body.name = f"M3x30_Bolt_{idx + 1}"

            sk_ch = comp_hw.sketches.add(hw_side_plane)
            sk_ch.name = f"M3x30_Head_{idx + 1}"
            c2d_h = sk_ch.modelToSketchSpace(pt(side_cbore_x_seat, sy, side_hole_z))
            c2d_h.z = 0.0
            sk_ch.sketchCurves.sketchCircles.addByCenterRadius(c2d_h, mm(2.7))
            add_extrude(
                comp_hw,
                sk_ch,
                3.0,
                adsk.fusion.FeatureOperations.JoinFeatureOperation,
                hw_to_neg_x,
            )

        app.activeViewport.fit()
        ui.messageBox(
            "Created Z-Axis assembly (m5_cbore_dia=9.6 mm; 289 mm rods sitting 4.5 mm lower than Extrusion_3030 with stepped lower rod-clamp sockets)."
        )

    except Exception:
        if ui:
            ui.messageBox(f"Script failed:\n{traceback.format_exc()}")