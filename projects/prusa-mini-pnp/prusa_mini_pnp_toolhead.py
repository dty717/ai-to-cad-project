import adsk.core
import adsk.fusion
import math
import traceback

# ==============================================================================
# CONFIGURATION (all dimensions in mm)
# ==============================================================================

CFG = {
    'rod_spacing': 45.0,        # Center-to-center vertical distance between X smooth rods
    'rod_dia': 8.0,             # Smooth rod diameter
    'rod_clear_dia': 9.6,       # End-wall rod clearance slot diameter
    'lm8uu_od': 15.2,           # LM8UU 15mm OD + 0.2mm print fit clearance
    'lm8uu_len': 24.4,          # LM8UU 24mm length + 0.4mm axial clearance
    'carriage_width': 55.0,     # Total carriage width along X
    'belt_width': 6.8,          # Horizontal GT2 belt channel width along Y (6mm belt + 0.8mm clearance)
    'screw_hole_dia': 3.4,      # M3 clearance bore
    'screw_thread_dia': 3.2,    # M3 self-threading / tight pass bore
    'screw_head_dia': 6.2,      # M3 screw head counterbore
    'belt_clamp_x': 8.0,        # Left/Right X offset of the 2 belt-clamp screws (+/- 8.0mm, clears +/-16mm rear grid)
    'belt_clamp_y': -16.7,      # Y centerline of vertical belt-clamp screws & side-entry nut bays
    'mount_screw_x': 16.5,      # X offset of front syringe-mount screw grid (+/- 16.5mm -> 33mm wide)
    'mount_screw_z_lo': 12.5,   # Lower Z of front syringe-mount screw grid (clear of stylus Z=6.5)
    'mount_screw_z_hi': 32.5,   # Upper Z of front syringe-mount screw grid (clear of stylus Z=38.5)
    'stylus_hole_offset': 16.0, # Stylus holder HOLE_OFFSET (+/- 16.0mm -> 32x32mm grid)
    'stylus_center_z': 22.5,    # Centered between rods (holes at Z=6.5 & 38.5, both clear of rods)
    'rear_mount_x': 16.0,       # X offset of rear/bottom M3 grid (+/- 16.0mm -> 32.0mm wide)
    'rear_mount_z_lo': 6.5,     # Lower Z of rear/bottom M3 grid
    'rear_mount_z_hi': 38.5,    # Upper Z of rear/bottom M3 grid (32.0mm tall)
    'sensor_dia': 8.0,          # Single Z-distance sensor OD (8.0mm SuperPINDA/MINDA; 12.0mm LJ12A3)
    'sensor_x': 32.5,           # Distance sensor X center (clears syringe mount & minimizes X-overhang)
    'sensor_y': 22.66,          # Distance sensor Y center (aligned with vacuum nozzle Y=22.66 -> dY=0)
    'sensor_z_mid': -6.5,       # Distance sensor clamp Z midpoint (-15.5..+2.5, flush with carriage bottom)
    'sensor_h': 18.0,           # Distance sensor clamp vertical height
    'syringe_od': 10.3,         # Dedicated PnP_Sized_Syringe_Mount OD (1mL6.8, 3mL10.3, 5mL13.8, 10mL16.2)
    'nozzle_od': 8.0,           # Printable PnP_Vacuum_Nozzle_Adapter barrel OD
}


def mm(val_mm: float) -> float:
    """Convert millimeters to Fusion 360 internal units (centimeters)."""
    return val_mm * 0.1


def wpt(sketch: adsk.fusion.Sketch, x_mm: float, y_mm: float, z_mm: float) -> adsk.core.Point3D:
    """Convert local component coordinates (mm) into the sketch's 2D space."""
    return sketch.modelToSketchSpace(
        adsk.core.Point3D.create(mm(x_mm), mm(y_mm), mm(z_mm))
    )


def offset_plane(
    comp: adsk.fusion.Component,
    base_plane: adsk.fusion.ConstructionPlane,
    coord_mm: float,
    world_axis: adsk.core.Vector3D,
) -> adsk.fusion.ConstructionPlane:
    """Create a construction plane at an exact coordinate regardless of base plane normal sign."""
    planes = comp.constructionPlanes
    inp = planes.createInput()
    dot = base_plane.geometry.normal.dotProduct(world_axis)
    sign = 1.0 if dot >= 0 else -1.0
    inp.setByOffset(base_plane, adsk.core.ValueInput.createByReal(sign * mm(coord_mm)))
    return planes.add(inp)


def draw_closed_poly(sketch: adsk.fusion.Sketch, pts_mm: list) -> None:
    """Draw a watertight closed polygon in sketch space from (x, y, z) mm tuples."""
    lines = sketch.sketchCurves.sketchLines
    first_line = None
    prev_end = wpt(sketch, *pts_mm[0])
    for i in range(1, len(pts_mm)):
        nxt = wpt(sketch, *pts_mm[i])
        ln = lines.addByTwoPoints(prev_end, nxt)
        if first_line is None:
            first_line = ln
        prev_end = ln.endSketchPoint
    lines.addByTwoPoints(prev_end, first_line.startSketchPoint)


def extrude_symmetric(
    comp: adsk.fusion.Component,
    sketch: adsk.fusion.Sketch,
    total_dist_mm: float,
    operation: adsk.fusion.FeatureOperations,
    all_profiles: bool = False,
) -> adsk.fusion.ExtrudeFeature:
    """Extrude symmetrically from the sketch plane by total_dist_mm."""
    if all_profiles:
        target = adsk.core.ObjectCollection.create()
        for prof in sketch.profiles:
            target.add(prof)
    else:
        target = sketch.profiles.item(0)

    ext_feats = comp.features.extrudeFeatures
    ext_in = ext_feats.createInput(target, operation)
    ext_in.setSymmetricExtent(adsk.core.ValueInput.createByReal(mm(total_dist_mm)), True)
    return ext_feats.add(ext_in)


def register_user_parameters(design: adsk.fusion.Design) -> None:
    """Store key design values as Fusion 360 User Parameters."""
    for key, val in CFG.items():
        design.userParameters.add(
            key,
            adsk.core.ValueInput.createByString(f'{val} mm'),
            'mm',
            f'PnP parameter: {key}',
        )


def build_carriage_base(root: adsk.fusion.Component) -> None:
    """Component 1: PnP_Carriage_Base with 2-piece bolted LM8UU cradles, 32x32mm grids & nozzle-aligned sensor mount."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Carriage_Base'

    rs = CFG['rod_spacing']
    cw = CFG['carriage_width']
    hw = cw / 2.0
    lm_od = CFG['lm8uu_od']
    lm_len = CFG['lm8uu_len']
    z_bot = -15.5           # Extended from -10.0 to support Z=-11.5 lower bearing-cap screws
    z_top = rs + 15.5       # 60.5mm: extended from 55.0 to support Z=56.5 upper bearing-cap screws
    y_front = 13.5
    y_snap = -2.8
    y_tower_back = -23.5
    z_tower_bot = 9.0
    z_tower_top = 30.8

    # 1. Main body with completely FLAT front (+Y = 13.5) and FLAT rear (-Y = -23.5) faces
    sk_body = comp.sketches.add(comp.yZConstructionPlane)
    sk_body.name = 'Base_Side_Profile'
    draw_closed_poly(sk_body, [
        (0.0, y_snap, z_bot),
        (0.0, y_front, z_bot),
        (0.0, y_front, z_top),
        (0.0, y_snap, z_top),
        (0.0, y_snap, z_tower_top),
        (0.0, y_tower_back, z_tower_top),
        (0.0, y_tower_back, z_tower_bot),
        (0.0, y_snap, z_tower_bot),
    ])
    extrude_symmetric(comp, sk_body, cw, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # 1b. Upper rear outer mounting columns (X = +/-12.5..27.5, clears combined upper clamp at +/-12.1)
    for side_tag, x_col in (('Left', -20.0), ('Right', 20.0)):
        pl_col = offset_plane(comp, comp.yZConstructionPlane, x_col, adsk.core.Vector3D.create(1, 0, 0))
        sk_col = comp.sketches.add(pl_col)
        sk_col.name = f'Upper_Rear_Mount_Column_{side_tag}'
        draw_closed_poly(sk_col, [
            (x_col, y_tower_back, 30.6),
            (x_col, -13.5, 30.6),
            (x_col, -13.5, 31.8),
            (x_col, -5.5, 31.8),
            (x_col, -5.5, 30.6),
            (x_col, y_front, 30.6),
            (x_col, y_front, 40.0),
            (x_col, -5.2, 40.0),
            (x_col, -5.2, 44.5),
            (x_col, y_tower_back, 44.5),
        ])
        extrude_symmetric(comp, sk_col, 15.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 1c. Lower rear outer mounting columns (X = +/-12.5..27.5, Z = 2.0..9.2, supports Z=6.5 rear holes)
    for side_tag, x_col in (('Left', -20.0), ('Right', 20.0)):
        pl_lcol = offset_plane(comp, comp.yZConstructionPlane, x_col, adsk.core.Vector3D.create(1, 0, 0))
        sk_lcol = comp.sketches.add(pl_lcol)
        sk_lcol.name = f'Lower_Rear_Mount_Column_{side_tag}'
        draw_closed_poly(sk_lcol, [
            (x_col, y_tower_back, 2.0),
            (x_col, y_snap, 2.0),
            (x_col, y_snap, z_tower_bot + 0.2),
            (x_col, y_tower_back, z_tower_bot + 0.2),
        ])
        extrude_symmetric(comp, sk_lcol, 15.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 2. Cut 2x LM8UU front-half cylindrical bearing seats
    sk_bearings = comp.sketches.add(comp.yZConstructionPlane)
    sk_bearings.name = 'LM8UU_Front_Half_Cradles'
    sk_bearings.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bearings, 0, 0, 0), mm(lm_od / 2.0))
    sk_bearings.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bearings, 0, 0, rs), mm(lm_od / 2.0))
    extrude_symmetric(comp, sk_bearings, lm_len, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 2b. Cut upper bearing-cap seating pocket (|x| <= 12.3, Y <= +0.2, Z = 30.8..61.0)
    sk_up_pkt = comp.sketches.add(comp.yZConstructionPlane)
    sk_up_pkt.name = 'Upper_Bearing_Cap_Pocket'
    draw_closed_poly(sk_up_pkt, [
        (0.0, -24.0, 30.8),
        (0.0,   0.2, 30.8),
        (0.0,   0.2, z_top + 0.5),
        (0.0, -24.0, z_top + 0.5),
    ])
    extrude_symmetric(comp, sk_up_pkt, lm_len + 0.2, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2c. Cut lower bearing-cap seating pocket (|x| <= 12.3, Y <= +0.2, Z = -16.0..+9.0)
    sk_lo_pkt = comp.sketches.add(comp.yZConstructionPlane)
    sk_lo_pkt.name = 'Lower_Bearing_Cap_Pocket'
    draw_closed_poly(sk_lo_pkt, [
        (0.0, -24.0, z_bot - 0.5),
        (0.0,   0.2, z_bot - 0.5),
        (0.0,   0.2, z_tower_bot),
        (0.0, -24.0, z_tower_bot),
    ])
    extrude_symmetric(comp, sk_lo_pkt, lm_len + 0.2, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2d. Cut center hook-tab recess for the lower bearing cap (|x| <= 5.7, clears X=+/-8.0 belt screws)
    sk_tab_pkt = comp.sketches.add(comp.yZConstructionPlane)
    sk_tab_pkt.name = 'Lower_Bearing_Cap_Center_Tab_Pocket'
    draw_closed_poly(sk_tab_pkt, [
        (0.0, -24.0,  8.8),
        (0.0,   0.2,  8.8),
        (0.0,   0.2, 10.6),
        (0.0, -19.5, 10.6),
        (0.0, -19.5, 16.6),
        (0.0, -24.0, 16.6),
    ])
    extrude_symmetric(comp, sk_tab_pkt, 11.4, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2e. M3 self-threading holes in base for Upper Bearing Cap (X=+/-6.5, Z=56.5, Y=0.0..11.5)
    pl_cap_th = offset_plane(comp, comp.xZConstructionPlane, 5.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_up_th = comp.sketches.add(pl_cap_th)
    sk_up_th.name = 'Upper_Bearing_Cap_M3_Thread_Holes'
    for sx_h in (-6.5, 6.5):
        sk_up_th.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_up_th, sx_h, 5.5, 56.5), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_up_th, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 2f. M3 self-threading holes in base for Lower Bearing Cap bottom (X=+/-6.5, Z=-11.5, Y=0.0..11.5)
    sk_lo_th = comp.sketches.add(pl_cap_th)
    sk_lo_th.name = 'Lower_Bearing_Cap_Bottom_M3_Thread_Holes'
    for sx_h in (-6.5, 6.5):
        sk_lo_th.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_lo_th, sx_h, 5.5, -11.5), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_lo_th, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 2g. M3 self-threading hole in base for Lower Bearing Cap top hook-tab (X=0.0, Z=13.5, Y=-19.5..-13.5)
    pl_tab_th = offset_plane(comp, comp.xZConstructionPlane, -16.6, adsk.core.Vector3D.create(0, 1, 0))
    sk_tab_th = comp.sketches.add(pl_tab_th)
    sk_tab_th.name = 'Lower_Bearing_Cap_Top_Tab_M3_Thread_Hole'
    sk_tab_th.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_tab_th, 0.0, -16.6, 13.5), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_tab_th, 6.2, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 3. Cut 8mm smooth rod clearance holes + rear U-slots (for end walls |x| > 12.3)
    rod_r = CFG['rod_clear_dia'] / 2.0
    sk_rods = comp.sketches.add(comp.yZConstructionPlane)
    sk_rods.name = 'Smooth_Rod_Clearance_Bores'
    sk_rods.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_rods, 0, 0, 0), mm(rod_r))
    sk_rods.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_rods, 0, 0, rs), mm(rod_r))
    extrude_symmetric(comp, sk_rods, cw + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    sk_uslot = comp.sketches.add(comp.yZConstructionPlane)
    sk_uslot.name = 'Smooth_Rod_Rear_U_Slots'
    for z_c in (0.0, rs):
        draw_closed_poly(sk_uslot, [
            (0.0, -3.8, z_c - rod_r),
            (0.0, 0.0, z_c - rod_r),
            (0.0, 0.0, z_c + rod_r),
            (0.0, -3.8, z_c + rod_r),
        ])
    extrude_symmetric(comp, sk_uslot, cw + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 4. Lower horizontal GT2 belt pass-through tunnel
    y_belt_lo = -13.0
    y_belt_hi = y_belt_lo + CFG['belt_width']
    sk_belt_lo = comp.sketches.add(comp.yZConstructionPlane)
    sk_belt_lo.name = 'GT2_Lower_Horizontal_Tunnel'
    draw_closed_poly(sk_belt_lo, [
        (0.0, y_belt_lo, 10.6),
        (0.0, y_belt_hi, 10.6),
        (0.0, y_belt_hi, 14.0),
        (0.0, y_belt_lo, 14.0),
    ])
    extrude_symmetric(comp, sk_belt_lo, cw + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 5. Upper horizontal GT2 toothed belt grooves
    y_belt_mid = (y_belt_lo + y_belt_hi) / 2.0
    pl_belt_y = offset_plane(comp, comp.xZConstructionPlane, y_belt_mid, adsk.core.Vector3D.create(0, 1, 0))
    sk_belt_hi = comp.sketches.add(pl_belt_y)
    sk_belt_hi.name = 'GT2_Upper_Horizontal_Toothed_Grooves'

    left_pts = [(-(hw + 0.5), y_belt_mid, 31.2), (-3.6, y_belt_mid, 31.2), (-3.6, y_belt_mid, 30.35)]
    for k in range(12):
        xr = -4.0 - 2.0 * k
        xl = xr - 1.1
        left_pts.extend([
            (xr, y_belt_mid, 30.35),
            (xr, y_belt_mid, 29.60),
            (xl, y_belt_mid, 29.60),
            (xl, y_belt_mid, 30.35),
        ])
    left_pts.append((-(hw + 0.5), y_belt_mid, 30.35))
    draw_closed_poly(sk_belt_hi, left_pts)

    right_pts = [(-px, py, pz) for (px, py, pz) in left_pts]
    draw_closed_poly(sk_belt_hi, right_pts)
    extrude_symmetric(comp, sk_belt_hi, CFG['belt_width'], adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 6. Open center excess-belt exit slot
    pl_exit = offset_plane(comp, comp.xZConstructionPlane, -15.05, adsk.core.Vector3D.create(0, 1, 0))
    sk_exit = comp.sketches.add(pl_exit)
    sk_exit.name = 'Excess_Belt_Center_Exit_Slot'
    draw_closed_poly(sk_exit, [
        (-3.6, -15.05, 29.6),
        (3.6, -15.05, 29.6),
        (3.6, -15.05, 31.2),
        (-3.6, -15.05, 31.2),
    ])
    extrude_symmetric(comp, sk_exit, 17.9, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 7. Full open-bottom vertical M3 belt-clamp screw bores (Z = 8.0 to 31.5)
    bx = CFG['belt_clamp_x']
    by = CFG['belt_clamp_y']
    pl_sc = offset_plane(comp, comp.xYConstructionPlane, 19.75, adsk.core.Vector3D.create(0, 0, 1))
    sk_sc = comp.sketches.add(pl_sc)
    sk_sc.name = 'Belt_Clamp_Full_Through_M3_Bores'
    sk_sc.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sc, -bx, by, 19.75), mm(1.8))
    sk_sc.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sc, bx, by, 19.75), mm(1.8))
    extrude_symmetric(comp, sk_sc, 23.5, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 8. Side-entry flexible captive nut bays
    z_bay_mid = 22.1
    z_bay_h = 10.2
    pl_bay = offset_plane(comp, comp.xYConstructionPlane, z_bay_mid, adsk.core.Vector3D.create(0, 0, 1))
    sk_bay = comp.sketches.add(pl_bay)
    sk_bay.name = 'Side_Entry_Flexible_Nut_Bays'
    draw_closed_poly(sk_bay, [
        (-(hw + 0.2), by - 3.2, z_bay_mid),
        (-25.5, by - 3.2, z_bay_mid),
        (-24.5, by - 2.55, z_bay_mid),
        (-23.0, by - 2.55, z_bay_mid),
        (-21.8, by - 2.95, z_bay_mid),
        (-4.7, by - 2.95, z_bay_mid),
        (-4.7, by + 2.95, z_bay_mid),
        (-21.8, by + 2.95, z_bay_mid),
        (-23.0, by + 2.55, z_bay_mid),
        (-24.5, by + 2.55, z_bay_mid),
        (-25.5, by + 3.2, z_bay_mid),
        (-(hw + 0.2), by + 3.2, z_bay_mid),
    ])
    draw_closed_poly(sk_bay, [
        ((hw + 0.2), by - 3.2, z_bay_mid),
        ((hw + 0.2), by + 3.2, z_bay_mid),
        (25.5, by + 3.2, z_bay_mid),
        (24.5, by + 2.55, z_bay_mid),
        (23.0, by + 2.55, z_bay_mid),
        (21.8, by + 2.95, z_bay_mid),
        (4.7, by + 2.95, z_bay_mid),
        (4.7, by - 2.95, z_bay_mid),
        (21.8, by - 2.95, z_bay_mid),
        (23.0, by - 2.55, z_bay_mid),
        (24.5, by - 2.55, z_bay_mid),
        (25.5, by - 3.2, z_bay_mid),
    ])
    extrude_symmetric(comp, sk_bay, z_bay_h, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 9. Front flex-relief slots for side-entry nut bays
    sk_flex = comp.sketches.add(pl_bay)
    sk_flex.name = 'Nut_Bay_Front_Flex_Slots'
    for x1, x2 in ((-(hw + 0.2), -5.0), (5.0, (hw + 0.2))):
        draw_closed_poly(sk_flex, [
            (x1, by + 4.15, z_bay_mid),
            (x2, by + 4.15, z_bay_mid),
            (x2, by + 5.15, z_bay_mid),
            (x1, by + 5.15, z_bay_mid),
        ])
    extrude_symmetric(comp, sk_flex, z_bay_h, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 10. Front flat-face 4x M3 mounting holes (Syringe Mount grid: X=+/-16.5, Z=12.5 & 32.5, blind from -Y)
    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']
    pl_front_m = offset_plane(comp, comp.xZConstructionPlane, 5.4, adsk.core.Vector3D.create(0, 1, 0))
    sk_fm = comp.sketches.add(pl_front_m)
    sk_fm.name = 'Front_Flat_Syringe_Mount_M3_Holes'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_fm.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_fm, sx_h, 5.4, sz_h), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_fm, 17.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 10b. Front 4x M3 holes for Stylus Holder (32x32mm: X=+/-16.0, Z=6.5 & 38.5)
    st_off = CFG['stylus_hole_offset']
    st_zc = CFG['stylus_center_z']
    sk_st = comp.sketches.add(pl_front_m)
    sk_st.name = 'Front_Stylus_Holder_32x32_M3_Holes'
    for sx_h in (-st_off, st_off):
        for sz_h in (st_zc - st_off, st_zc + st_off):
            sk_st.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_st, sx_h, 5.4, sz_h), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_st, 17.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 11. Rear/bottom flat-face 4x M3 mounting holes (32.0mm x 32.0mm grid at X=+/-16.0, Z=6.5 & 38.5)
    rx = CFG['rear_mount_x']
    rz_lo = CFG['rear_mount_z_lo']
    rz_hi = CFG['rear_mount_z_hi']
    pl_rear_m = offset_plane(comp, comp.xZConstructionPlane, -13.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_rm = comp.sketches.add(pl_rear_m)
    sk_rm.name = 'Rear_Flat_Accessory_32x32_M3_Holes'
    for sx_h in (-rx, rx):
        for sz_h in (rz_lo, rz_hi):
            sk_rm.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_rm, sx_h, -13.5, sz_h), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_rm, 22.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 12. Distance Sensor Holder: Nozzle-aligned Y=22.66, compact X=32.5, flush Z=-15.5..+2.5, front-accessible screw
    sx = CFG['sensor_x'] + (CFG['sensor_dia'] - 8.0) / 2.0
    sy = CFG['sensor_y']
    z_sens_mid = CFG['sensor_z_mid']
    sens_h = CFG['sensor_h']
    sr_in = (CFG['sensor_dia'] + 0.1) / 2.0
    sr_out = sr_in + 4.0
    pl_sens = offset_plane(comp, comp.xYConstructionPlane, z_sens_mid, adsk.core.Vector3D.create(0, 0, 1))

    # Anchored strictly at Y >= 10.0 so it completely clears the Prusa MINI X-end idler & smooth rod
    sk_arm = comp.sketches.add(pl_sens)
    sk_arm.name = 'Distance_Sensor_Monolithic_Gusset'
    draw_closed_poly(sk_arm, [
        (hw - 3.0, 10.0, z_sens_mid),
        (hw,       10.0, z_sens_mid),
        (sx + sr_out * 0.7, sy - sr_out * 0.5, z_sens_mid),
        (sx,       sy,   z_sens_mid),
        (sx - sr_out + 0.5, sy, z_sens_mid),
        (hw - 3.0, 13.5, z_sens_mid),
    ])
    extrude_symmetric(comp, sk_arm, sens_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_col = comp.sketches.add(pl_sens)
    sk_col.name = 'Distance_Sensor_Collar_Boss'
    sk_col.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_col, sx, sy, z_sens_mid), mm(sr_out))
    extrude_symmetric(comp, sk_col, sens_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Outward (+X) pinch ears with front-facing (+Y) M3 screw access
    ear_x_end = sx + sr_out + 6.5
    sk_ears = comp.sketches.add(pl_sens)
    sk_ears.name = 'Distance_Sensor_Screw_Pinch_Ears'
    for ey1, ey2 in ((sy - 5.2, sy - 0.9), (sy + 0.9, sy + 5.2)):
        draw_closed_poly(sk_ears, [
            (sx + sr_in - 0.5, ey1, z_sens_mid),
            (ear_x_end,        ey1, z_sens_mid),
            (ear_x_end,        ey2, z_sens_mid),
            (sx + sr_in - 0.5, ey2, z_sens_mid),
        ])
    extrude_symmetric(comp, sk_ears, sens_h, adsk.fusion.FeatureOperations.JoinFeatureOperation, all_profiles=True)

    sk_sbore = comp.sketches.add(pl_sens)
    sk_sbore.name = 'Distance_Sensor_Bore'
    sk_sbore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sbore, sx, sy, z_sens_mid), mm(sr_in))
    extrude_symmetric(comp, sk_sbore, sens_h + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    sk_sslit = comp.sketches.add(pl_sens)
    sk_sslit.name = 'Distance_Sensor_Flex_Slit'
    draw_closed_poly(sk_sslit, [
        (sx,               sy - 0.9, z_sens_mid),
        (ear_x_end + 0.8,  sy - 0.9, z_sens_mid),
        (ear_x_end + 0.8,  sy + 0.9, z_sens_mid),
        (sx,               sy + 0.9, z_sens_mid),
    ])
    extrude_symmetric(comp, sk_sslit, sens_h + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    x_pinch = sx + sr_out + 2.2
    pl_py = offset_plane(comp, comp.xZConstructionPlane, sy, adsk.core.Vector3D.create(0, 1, 0))
    sk_pscrew = comp.sketches.add(pl_py)
    sk_pscrew.name = 'Distance_Sensor_Pinch_M3_Hole'
    sk_pscrew.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_pscrew, x_pinch, sy, z_sens_mid), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_pscrew, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    pl_pcb = offset_plane(comp, comp.xZConstructionPlane, sy + 4.2, adsk.core.Vector3D.create(0, 1, 0))
    sk_pcb = comp.sketches.add(pl_pcb)
    sk_pcb.name = 'Distance_Sensor_Pinch_M3_Counterbore'
    sk_pcb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_pcb, x_pinch, sy + 4.2, z_sens_mid), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_pcb, 2.4, adsk.fusion.FeatureOperations.CutFeatureOperation)

    pl_pnut = offset_plane(comp, comp.xZConstructionPlane, sy - 4.0, adsk.core.Vector3D.create(0, 1, 0))
    sk_pnut = comp.sketches.add(pl_pnut)
    sk_pnut.name = 'Distance_Sensor_Pinch_Hex_Nut_Pocket'
    r_hex = 2.9 / math.cos(math.radians(30.0))
    hex_pts = [
        (
            x_pinch + r_hex * math.cos(k * math.pi / 3.0),
            sy - 4.0,
            z_sens_mid + r_hex * math.sin(k * math.pi / 3.0),
        )
        for k in range(6)
    ]
    draw_closed_poly(sk_pnut, hex_pts)
    extrude_symmetric(comp, sk_pnut, 3.2, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_upper_belt_bearing_clamp(root: adsk.fusion.Component) -> None:
    """Component 2: Unified GT2 Belt Clamp + Upper LM8UU Linear Bearing Rear Cap (24.2mm wide)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Upper_Belt_Bearing_Clamp'

    cap_w = CFG['lm8uu_len'] - 0.2   # 24.2mm (X = -12.1..+12.1, 0.4mm clearance to columns)
    rs = CFG['rod_spacing']
    bx = CFG['belt_clamp_x']
    by = CFG['belt_clamp_y']

    # 1. Combined belt-clamp bridge + upper LM8UU bearing cap body
    sk_body = comp.sketches.add(comp.yZConstructionPlane)
    sk_body.name = 'Upper_Belt_And_Bearing_Clamp_Profile'
    draw_closed_poly(sk_body, [
        (0.0, -23.5, 30.8),
        (0.0, -13.5, 30.8),
        (0.0, -13.5, 31.2),
        (0.0, -12.6, 31.2),
        (0.0, -12.6, 30.6),
        (0.0,  -6.4, 30.6),
        (0.0,  -6.4, 31.2),
        (0.0,  -5.8, 31.2),
        (0.0,  -5.8, 30.8),
        (0.0,  -3.8, 30.8),
        (0.0,  -3.8, 32.0),
        (0.0,   0.0, 32.0),
        (0.0,   0.0, 60.3),
        (0.0, -10.5, 60.3),
        (0.0, -10.5, 36.4),
        (0.0, -23.5, 36.4),
    ])
    extrude_symmetric(comp, sk_body, cap_w, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # 2. Cut center excess-belt exit relief under the bridge (X = -3.7..+3.7)
    pl_rel = offset_plane(comp, comp.yZConstructionPlane, 0.0, adsk.core.Vector3D.create(1, 0, 0))
    sk_rel = comp.sketches.add(pl_rel)
    sk_rel.name = 'Center_Excess_Belt_Exit_Relief'
    draw_closed_poly(sk_rel, [
        (0.0, -24.0, 30.2),
        (0.0,  -5.8, 30.2),
        (0.0,  -5.8, 31.6),
        (0.0, -24.0, 31.6),
    ])
    extrude_symmetric(comp, sk_rel, 7.4, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 3. Cut 2x vertical M3 belt-clamp holes + top counterbores (X = +/-8.0, Y = -16.7)
    pl_hole = offset_plane(comp, comp.xYConstructionPlane, 33.6, adsk.core.Vector3D.create(0, 0, 1))
    sk_hole = comp.sketches.add(pl_hole)
    sk_hole.name = 'Belt_Clamp_M3_Vertical_Holes'
    for sx_h in (-bx, bx):
        sk_hole.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hole, sx_h, by, 33.6), mm(1.8))
    extrude_symmetric(comp, sk_hole, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xYConstructionPlane, 35.05, adsk.core.Vector3D.create(0, 0, 1))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Belt_Clamp_M3_Top_Counterbores'
    for sx_h in (-bx, bx):
        sk_cb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cb, sx_h, by, 35.05), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_cb, 3.7, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 4. Cut Upper LM8UU semicircular rear bearing seat (centered at Y=0.0, Z=45.0)
    sk_bore = comp.sketches.add(comp.yZConstructionPlane)
    sk_bore.name = 'Upper_LM8UU_Rear_Half_Bore'
    sk_bore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bore, 0.0, 0.0, rs), mm(CFG['lm8uu_od'] / 2.0))
    extrude_symmetric(comp, sk_bore, cap_w + 1.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 5. Cut 2x horizontal M3 clamping holes + counterbores above the bearing (X=+/-6.5, Z=56.5, M3x16)
    pl_mh = offset_plane(comp, comp.xZConstructionPlane, -5.25, adsk.core.Vector3D.create(0, 1, 0))
    sk_mh = comp.sketches.add(pl_mh)
    sk_mh.name = 'Upper_Bearing_Clamp_M3_Holes'
    for sx_h in (-6.5, 6.5):
        sk_mh.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_mh, sx_h, -5.25, 56.5), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_mh, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_mcb = offset_plane(comp, comp.xZConstructionPlane, -8.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_mcb = comp.sketches.add(pl_mcb)
    sk_mcb.name = 'Upper_Bearing_Clamp_M3_Counterbores'
    for sx_h in (-6.5, 6.5):
        sk_mcb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_mcb, sx_h, -8.5, 56.5), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_mcb, 4.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)


def build_lower_bearing_clamp(root: adsk.fusion.Component) -> None:
    """Component 3: Lower LM8UU Linear Bearing Rear Cap (24.2mm wide + center hook-tab under lower belt)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Lower_Bearing_Clamp'

    cap_w = CFG['lm8uu_len'] - 0.2   # 24.2mm (X = -12.1..+12.1)

    # 1. Main lower bearing cap body (Z = -15.3..+8.8, Y = -10.5..0.0)
    sk_body = comp.sketches.add(comp.yZConstructionPlane)
    sk_body.name = 'Lower_Bearing_Clamp_Profile'
    draw_closed_poly(sk_body, [
        (0.0, -10.5, -15.3),
        (0.0,   0.0, -15.3),
        (0.0,   0.0,   8.8),
        (0.0, -10.5,   8.8),
    ])
    extrude_symmetric(comp, sk_body, cap_w, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # 2. Center rear hook-tab (11.0mm wide, passes under Z=10.6..14.0 belt tunnel, mounts at Z=13.5)
    sk_tab = comp.sketches.add(comp.yZConstructionPlane)
    sk_tab.name = 'Lower_Bearing_Clamp_Rear_Hook_Tab'
    draw_closed_poly(sk_tab, [
        (0.0, -23.5,  7.5),
        (0.0,   0.0,  7.5),
        (0.0,   0.0, 10.4),
        (0.0, -19.7, 10.4),
        (0.0, -19.7, 16.4),
        (0.0, -23.5, 16.4),
    ])
    extrude_symmetric(comp, sk_tab, 11.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 3. Cut Lower LM8UU semicircular rear bearing seat (centered at Y=0.0, Z=0.0)
    sk_bore = comp.sketches.add(comp.yZConstructionPlane)
    sk_bore.name = 'Lower_LM8UU_Rear_Half_Bore'
    sk_bore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bore, 0.0, 0.0, 0.0), mm(CFG['lm8uu_od'] / 2.0))
    extrude_symmetric(comp, sk_bore, cap_w + 1.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 4. Cut 2x bottom horizontal M3 clamping holes + counterbores (X=+/-6.5, Z=-11.5, M3x16)
    pl_mh = offset_plane(comp, comp.xZConstructionPlane, -5.25, adsk.core.Vector3D.create(0, 1, 0))
    sk_mh = comp.sketches.add(pl_mh)
    sk_mh.name = 'Lower_Bearing_Clamp_Bottom_M3_Holes'
    for sx_h in (-6.5, 6.5):
        sk_mh.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_mh, sx_h, -5.25, -11.5), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_mh, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_mcb = offset_plane(comp, comp.xZConstructionPlane, -8.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_mcb = comp.sketches.add(pl_mcb)
    sk_mcb.name = 'Lower_Bearing_Clamp_Bottom_M3_Counterbores'
    for sx_h in (-6.5, 6.5):
        sk_mcb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_mcb, sx_h, -8.5, -11.5), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_mcb, 4.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 5. Cut 1x top-tab horizontal M3 hole + shallow counterbore (X=0.0, Z=13.5, M3x8)
    pl_th = offset_plane(comp, comp.xZConstructionPlane, -21.6, adsk.core.Vector3D.create(0, 1, 0))
    sk_th = comp.sketches.add(pl_th)
    sk_th.name = 'Lower_Bearing_Clamp_Top_Tab_M3_Hole'
    sk_th.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_th, 0.0, -21.6, 13.5), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_th, 5.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    pl_tcb = offset_plane(comp, comp.xZConstructionPlane, -22.75, adsk.core.Vector3D.create(0, 1, 0))
    sk_tcb = comp.sketches.add(pl_tcb)
    sk_tcb.name = 'Lower_Bearing_Clamp_Top_Tab_M3_Counterbore'
    sk_tcb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_tcb, 0.0, -22.75, 13.5), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_tcb, 2.0, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_universal_flex_syringe_mount(root: adsk.fusion.Component) -> None:
    """Component 4: Flat-back screw-mounted syringe holder (holes at X=+/-16.5, Z=12.5 & 32.5)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Universal_Flex_Syringe_Mount'

    pl_mid = offset_plane(comp, comp.xYConstructionPlane, 23.5, adsk.core.Vector3D.create(0, 0, 1))
    sk_body = comp.sketches.add(pl_mid)
    sk_body.name = 'Flat_Base_And_VCradle_Body'
    draw_closed_poly(sk_body, [
        (-22.0, 13.5, 23.5),
        (22.0, 13.5, 23.5),
        (22.0, 21.5, 23.5),
        (8.0, 21.5, 23.5),
        (0.0, 17.0, 23.5),
        (-8.0, 21.5, 23.5),
        (-22.0, 21.5, 23.5),
    ])
    extrude_symmetric(comp, sk_body, 55.0, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']

    pl_hole = offset_plane(comp, comp.xZConstructionPlane, 17.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_holes = comp.sketches.add(pl_hole)
    sk_holes.name = 'Syringe_Mount_M3_Holes'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_holes.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_holes, sx_h, 17.5, sz_h), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_holes, 10.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xZConstructionPlane, 19.8, adsk.core.Vector3D.create(0, 1, 0))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Syringe_Mount_M3_Counterbores'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_cb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cb, sx_h, 19.8, sz_h), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_cb, 3.8, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    for tag, z_jaw in (('Lower', 18.0), ('Upper', 38.0)):
        pl_jaw = offset_plane(comp, comp.xYConstructionPlane, z_jaw, adsk.core.Vector3D.create(0, 0, 1))
        sk_jaw = comp.sketches.add(pl_jaw)
        sk_jaw.name = f'Compliant_Syringe_Jaws_{tag}'

        left_arm = [
            (-21.7, 13.5, z_jaw),
            (-21.7, 15.5, z_jaw),
            (-23.5, 15.5, z_jaw),
            (-23.5, 29.0, z_jaw),
            (-15.5, 30.3, z_jaw),
            (-8.8, 26.5, z_jaw),
            (-5.2, 24.3, z_jaw),
            (-4.0, 27.0, z_jaw),
            (-4.6, 31.7, z_jaw),
            (-7.2, 38.5, z_jaw),
            (-9.5, 40.0, z_jaw),
            (-16.0, 35.0, z_jaw),
            (-26.3, 31.3, z_jaw),
            (-26.3, 13.5, z_jaw),
        ]
        draw_closed_poly(sk_jaw, left_arm)
        right_arm = [(-px, py, pz) for (px, py, pz) in left_arm]
        draw_closed_poly(sk_jaw, right_arm)
        extrude_symmetric(comp, sk_jaw, 12.0, adsk.fusion.FeatureOperations.JoinFeatureOperation, all_profiles=True)

        sk_lug = comp.sketches.add(pl_jaw)
        sk_lug.name = f'Elastic_Band_Hooks_{tag}'
        for sx_h in (-1.0, 1.0):
            draw_closed_poly(sk_lug, [
                (sx_h * 26.0, 13.5, z_jaw),
                (sx_h * 28.8, 13.5, z_jaw),
                (sx_h * 28.8, 17.5, z_jaw),
                (sx_h * 26.0, 17.5, z_jaw),
            ])
        extrude_symmetric(comp, sk_lug, 8.0, adsk.fusion.FeatureOperations.JoinFeatureOperation, all_profiles=True)

    hose_x = 26.5
    hose_y = 17.5
    pl_hose = offset_plane(comp, comp.xYConstructionPlane, 48.25, adsk.core.Vector3D.create(0, 0, 1))

    sk_hose_bridge = comp.sketches.add(pl_hose)
    sk_hose_bridge.name = 'Vacuum_Hose_Clip_Bridge'
    draw_closed_poly(sk_hose_bridge, [
        (21.5, 13.5, 48.25),
        (hose_x, 13.5, 48.25),
        (hose_x, 21.5, 48.25),
        (21.5, 21.5, 48.25),
    ])
    extrude_symmetric(comp, sk_hose_bridge, 5.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_hose_b = comp.sketches.add(pl_hose)
    sk_hose_b.name = 'Vacuum_Hose_Clip_Boss'
    sk_hose_b.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hose_b, hose_x, hose_y, 48.25), mm(5.6))
    extrude_symmetric(comp, sk_hose_b, 5.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_hose_c = comp.sketches.add(pl_hose)
    sk_hose_c.name = 'Vacuum_Hose_Clip_Bore'
    sk_hose_c.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hose_c, hose_x, hose_y, 48.25), mm(3.1))
    extrude_symmetric(comp, sk_hose_c, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    sk_hose_s = comp.sketches.add(pl_hose)
    sk_hose_s.name = 'Vacuum_Hose_Clip_Open_Slot'
    draw_closed_poly(sk_hose_s, [
        (hose_x - 2.1, hose_y, 48.25),
        (hose_x + 2.1, hose_y, 48.25),
        (hose_x + 2.1, hose_y + 7.0, 48.25),
        (hose_x - 2.1, hose_y + 7.0, 48.25),
    ])
    extrude_symmetric(comp, sk_hose_s, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_sized_syringe_mount(root: adsk.fusion.Component) -> None:
    """Component 5: Flat-back screw-mounted snap cradle (holes at X=+/-16.5, Z=12.5 & 32.5, placed at X=+95mm)."""
    mat = adsk.core.Matrix3D.create()
    mat.translation = adsk.core.Vector3D.create(mm(95.0), 0.0, 0.0)
    occ = root.occurrences.addNewComponent(mat)
    occ.activate()
    comp = occ.component
    comp.name = f'PnP_Sized_Syringe_Mount_{CFG["syringe_od"]}mm'

    r_in = (CFG['syringe_od'] + 0.2) / 2.0
    r_out = r_in + 4.0
    y_cyl = 20.0 + r_in

    pl_mid = offset_plane(comp, comp.xYConstructionPlane, 23.5, adsk.core.Vector3D.create(0, 0, 1))
    sk_base = comp.sketches.add(pl_mid)
    sk_base.name = 'Flat_Mounting_Plate'
    draw_closed_poly(sk_base, [
        (-22.0, 13.5, 23.5),
        (22.0, 13.5, 23.5),
        (22.0, 21.0, 23.5),
        (-22.0, 21.0, 23.5),
    ])
    extrude_symmetric(comp, sk_base, 55.0, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']

    pl_hole = offset_plane(comp, comp.xZConstructionPlane, 17.25, adsk.core.Vector3D.create(0, 1, 0))
    sk_holes = comp.sketches.add(pl_hole)
    sk_holes.name = 'Syringe_Mount_M3_Holes'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_holes.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_holes, sx_h, 17.25, sz_h), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_holes, 10.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xZConstructionPlane, 19.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Syringe_Mount_M3_Counterbores'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_cb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cb, sx_h, 19.5, sz_h), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_cb, 3.6, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    sk_cyl = comp.sketches.add(pl_mid)
    sk_cyl.name = 'Syringe_Cradle_Boss'
    sk_cyl.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cyl, 0.0, y_cyl, 23.5), mm(r_out))
    extrude_symmetric(comp, sk_cyl, 48.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_bore = comp.sketches.add(pl_mid)
    sk_bore.name = 'Syringe_Cradle_Bore'
    sk_bore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bore, 0.0, y_cyl, 23.5), mm(r_in))
    extrude_symmetric(comp, sk_bore, 52.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    half_open = 0.425 * CFG['syringe_od']
    half_flare = 0.58 * CFG['syringe_od']
    sk_open = comp.sketches.add(pl_mid)
    sk_open.name = 'Syringe_Snap_Throat'
    draw_closed_poly(sk_open, [
        (-half_open, y_cyl, 23.5),
        (half_open, y_cyl, 23.5),
        (half_flare, y_cyl + r_out + 2.0, 23.5),
        (-half_flare, y_cyl + r_out + 2.0, 23.5),
    ])
    extrude_symmetric(comp, sk_open, 52.0, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_vacuum_nozzle_adapter(root: adsk.fusion.Component) -> None:
    """Component 6: Printable 8mm hollow PnP pickup spindle seated inside the universal mount."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Vacuum_Nozzle_Adapter'

    yc = 22.66
    r_barrel = CFG['nozzle_od'] / 2.0

    def add_cyl(name: str, z_mid_mm: float, height_mm: float, radius_mm: float, op: adsk.fusion.FeatureOperations):
        pl = offset_plane(comp, comp.xYConstructionPlane, z_mid_mm, adsk.core.Vector3D.create(0, 0, 1))
        sk = comp.sketches.add(pl)
        sk.name = name
        sk.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk, 0.0, yc, z_mid_mm), mm(radius_mm))
        extrude_symmetric(comp, sk, height_mm, op)

    add_cyl('Clamping_Barrel', 22.0, 66.0, r_barrel, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    add_cyl('Luer_Tip_Nose', -16.0, 10.0, 3.4, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Axial_Stop_Collar', 56.75, 3.5, 5.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Vacuum_Hose_Stem', 64.5, 12.0, 2.25, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Vacuum_Hose_Barb_Ring', 66.0, 3.0, 2.65, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Internal_Vacuum_Airway', 24.75, 93.5, 1.1, adsk.fusion.FeatureOperations.CutFeatureOperation)
    add_cyl('Luer_Slip_Socket', -17.5, 9.0, 2.15, adsk.fusion.FeatureOperations.CutFeatureOperation)


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent

        register_user_parameters(design)
        build_carriage_base(root)
        build_upper_belt_bearing_clamp(root)
        build_lower_bearing_clamp(root)
        build_universal_flex_syringe_mount(root)
        build_sized_syringe_mount(root)
        build_vacuum_nozzle_adapter(root)

        design.activateRootComponent()
        try:
            app.activeViewport.fit()
        except Exception:
            pass

        if ui:
            ui.messageBox(
                'Created Prusa MINI PnP Head in a new file:\n\n'
                '1. PnP_Carriage_Base (2-piece LM8UU cradles; 32x32mm grids; sensor at X=32.5, Y=22.66, Z=-15.5..+2.5)\n'
                '2. PnP_Upper_Belt_Bearing_Clamp (unified belt clamp + upper LM8UU cap)\n'
                '3. PnP_Lower_Bearing_Clamp (lower LM8UU cap + hook-tab)\n'
                '4. PnP_Universal_Flex_Syringe_Mount (X=+/-16.5, Z=12.5 & 32.5)\n'
                '5. PnP_Sized_Syringe_Mount (X=+/-16.5, Z=12.5 & 32.5)\n'
                '6. PnP_Vacuum_Nozzle_Adapter'
            )

    except Exception:
        if ui:
            ui.messageBox('Script Failed:\n{}'.format(traceback.format_exc()))