# Fusion 360 Python Script: Prusa MINI Clone PnP Head
# Updates:
#   - Wide 47.7mm x 27.0mm rear M3 mounting grid on flat -Y face (X=+/-23.85, Z=11.5 & 38.5)
#   - Distance sensor holder uses horizontal M3 screw + recessed hex nut pocket (no empty cuboid notches)
#   - Flat +Y front face with 4x M3 holes (33mm x 28.5mm) for screw-mounted changeable syringe holders
#   - Horizontal 6mm GT2 belt clamps with side-entry flex nut bays (fits M3x8..35mm+ screws)
# Creates a NEW Fusion 360 document before generating geometry.

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
    'belt_clamp_x': 13.5,       # Left/Right X offset of the 2 belt-clamp screws (+/- 13.5mm)
    'belt_clamp_y': -16.7,      # Y centerline of vertical belt-clamp screws & side-entry nut bays
    'mount_screw_x': 16.5,      # X offset of front syringe-mount screw grid (+/- 16.5mm -> 33mm wide)
    'mount_screw_z_lo': 9.0,    # Lower Z of front syringe-mount screw grid
    'mount_screw_z_hi': 37.5,   # Upper Z of front syringe-mount screw grid (28.5mm tall)
    'rear_mount_x': 23.85,      # X offset of rear opposite-face M3 grid (+/- 23.85mm -> 47.7mm wide)
    'rear_mount_z_lo': 11.5,    # Lower Z of rear opposite-face M3 grid
    'rear_mount_z_hi': 38.5,    # Upper Z of rear opposite-face M3 grid (27.0mm tall)
    'sensor_dia': 8.0,          # Single Z-distance sensor OD (8.0mm SuperPINDA/MINDA; 12.0mm LJ12A3)
    'syringe_od': 10.3,         # Dedicated PnP_Sized_Syringe_Mount OD (1mL~6.8, 3mL~10.3, 5mL~13.8, 10mL~16.2)
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
    """Component 1: PnP_Carriage_Base (47.7 x 27.0mm rear M3 grid + screw-clamped distance sensor)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Carriage_Base'

    rs = CFG['rod_spacing']
    cw = CFG['carriage_width']
    hw = cw / 2.0
    lm_od = CFG['lm8uu_od']
    lm_len = CFG['lm8uu_len']
    z_bot = -10.0
    z_top = rs + 10.0
    y_front = 13.5
    y_snap = -2.8
    y_tower_back = -23.5
    z_tower_bot = 8.8
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

    # 1b. Upper rear outer mounting columns (X = +/-20.2 to +/-27.5, Z = 30.6..44.5)
    #     Leaves belt pass-out arch open at Z = 29.6..31.8 (Y = -13.5..-5.5) and clears upper rod
    for side_tag, x_col in (('Left', -23.85), ('Right', 23.85)):
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
        extrude_symmetric(comp, sk_col, 7.3, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 2. Cut 2x LM8UU snap-in bearing cradles
    sk_bearings = comp.sketches.add(comp.yZConstructionPlane)
    sk_bearings.name = 'LM8UU_Snap_Cradles'
    sk_bearings.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bearings, 0, 0, 0), mm(lm_od / 2.0))
    sk_bearings.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bearings, 0, 0, rs), mm(lm_od / 2.0))
    extrude_symmetric(comp, sk_bearings, lm_len, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 3. Cut 8mm smooth rod clearance holes + rear U-slots
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

    # 4. Lower horizontal GT2 belt pass-through tunnel (Y = -13.0..-6.2mm, Z = 10.6..14.0mm)
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

    # 5. Upper horizontal GT2 toothed belt grooves (X = +/-7.0 to +/-28.0mm)
    y_belt_mid = (y_belt_lo + y_belt_hi) / 2.0
    pl_belt_y = offset_plane(comp, comp.xZConstructionPlane, y_belt_mid, adsk.core.Vector3D.create(0, 1, 0))
    sk_belt_hi = comp.sketches.add(pl_belt_y)
    sk_belt_hi.name = 'GT2_Upper_Horizontal_Toothed_Grooves'

    left_pts = [(-(hw + 0.5), y_belt_mid, 31.2), (-7.0, y_belt_mid, 31.2), (-7.0, y_belt_mid, 30.35)]
    for k in range(10):
        xr = -8.0 - 2.0 * k
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

    # 6. Open center excess-belt exit slot (X = -7.0..+7.0, Y = -24.0..-6.1, Z = 29.6..31.2)
    pl_exit = offset_plane(comp, comp.xZConstructionPlane, -15.05, adsk.core.Vector3D.create(0, 1, 0))
    sk_exit = comp.sketches.add(pl_exit)
    sk_exit.name = 'Excess_Belt_Center_Exit_Slot'
    draw_closed_poly(sk_exit, [
        (-7.0, -15.05, 29.6),
        (7.0, -15.05, 29.6),
        (7.0, -15.05, 31.2),
        (-7.0, -15.05, 31.2),
    ])
    extrude_symmetric(comp, sk_exit, 17.9, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 7. Full open-bottom vertical M3 belt-clamp screw bores (X = +/-13.5mm, fits M3x8..35mm+)
    bx = CFG['belt_clamp_x']
    by = CFG['belt_clamp_y']
    pl_sc = offset_plane(comp, comp.xYConstructionPlane, 19.75, adsk.core.Vector3D.create(0, 0, 1))
    sk_sc = comp.sketches.add(pl_sc)
    sk_sc.name = 'Belt_Clamp_Full_Through_M3_Bores'
    sk_sc.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sc, -bx, by, 19.75), mm(1.8))
    sk_sc.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sc, bx, by, 19.75), mm(1.8))
    extrude_symmetric(comp, sk_sc, 23.5, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 8. Side-entry flexible captive nut bays (X = +/-27.7 inward to +/-10.2mm)
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
        (-10.2, by - 2.95, z_bay_mid),
        (-10.2, by + 2.95, z_bay_mid),
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
        (10.2, by + 2.95, z_bay_mid),
        (10.2, by - 2.95, z_bay_mid),
        (21.8, by - 2.95, z_bay_mid),
        (23.0, by - 2.55, z_bay_mid),
        (24.5, by - 2.55, z_bay_mid),
        (25.5, by - 3.2, z_bay_mid),
    ])
    extrude_symmetric(comp, sk_bay, z_bay_h, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 9. Front flex-relief slots for side-entry nut bays
    sk_flex = comp.sketches.add(pl_bay)
    sk_flex.name = 'Nut_Bay_Front_Flex_Slots'
    for x1, x2 in ((-(hw + 0.2), -10.5), (10.5, (hw + 0.2))):
        draw_closed_poly(sk_flex, [
            (x1, by + 4.15, z_bay_mid),
            (x2, by + 4.15, z_bay_mid),
            (x2, by + 5.15, z_bay_mid),
            (x1, by + 5.15, z_bay_mid),
        ])
    extrude_symmetric(comp, sk_flex, z_bay_h, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 10. Front flat-face 4x M3 mounting holes (X = +/-16.5, Z = 9.0 & 37.5)
    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']
    pl_front_m = offset_plane(comp, comp.xZConstructionPlane, 5.4, adsk.core.Vector3D.create(0, 1, 0))
    sk_fm = comp.sketches.add(pl_front_m)
    sk_fm.name = 'Front_Flat_Syringe_Mount_M3_Holes'
    for sx in (-mx, mx):
        for sz in (mz_lo, mz_hi):
            sk_fm.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_fm, sx, 5.4, sz), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_fm, 17.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 11. Opposite/rear flat-face 4x M3 mounting holes (wide 47.7mm x 27.0mm grid at Y = -23.5)
    rx = CFG['rear_mount_x']
    rz_lo = CFG['rear_mount_z_lo']
    rz_hi = CFG['rear_mount_z_hi']
    pl_rear_m = offset_plane(comp, comp.xZConstructionPlane, -19.1, adsk.core.Vector3D.create(0, 1, 0))
    sk_rm = comp.sketches.add(pl_rear_m)
    sk_rm.name = 'Rear_Flat_Accessory_M3_Holes'
    for sx in (-rx, rx):
        for sz in (rz_lo, rz_hi):
            sk_rm.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_rm, sx, -19.1, sz), mm(CFG['screw_thread_dia'] / 2.0))
    extrude_symmetric(comp, sk_rm, 9.2, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 12. ONLY ONE Distance Sensor Holder: Monolithic Block + Horizontal M3 Screw & Hex Nut Pinch Clamp
    sx = 36.5 + (CFG['sensor_dia'] - 8.0) / 2.0
    sy = 18.0
    z_sens_mid = -1.0
    sens_h = 18.0
    sr_in = (CFG['sensor_dia'] + 0.1) / 2.0
    sr_out = sr_in + 4.8
    pl_sens = offset_plane(comp, comp.xYConstructionPlane, z_sens_mid, adsk.core.Vector3D.create(0, 0, 1))

    sk_arm = comp.sketches.add(pl_sens)
    sk_arm.name = 'Distance_Sensor_Monolithic_Gusset'
    draw_closed_poly(sk_arm, [
        (hw - 0.5, 5.6, z_sens_mid),
        (sx, 5.6, z_sens_mid),
        (sx + sr_out - 0.5, 13.5, z_sens_mid),
        (sx, sy, z_sens_mid),
        (sx - sr_out + 0.2, sy, z_sens_mid),
        (hw - 0.5, 13.5, z_sens_mid),
    ])
    extrude_symmetric(comp, sk_arm, sens_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_col = comp.sketches.add(pl_sens)
    sk_col.name = 'Distance_Sensor_Collar_Boss'
    sk_col.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_col, sx, sy, z_sens_mid), mm(sr_out))
    extrude_symmetric(comp, sk_col, sens_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # Thick pinch ears (4.3mm thick each) with M3 screw & hex nut clamping (no empty cuboid notches!)
    sk_ears = comp.sketches.add(pl_sens)
    sk_ears.name = 'Distance_Sensor_Screw_Pinch_Ears'
    for ex1, ex2 in ((sx - 5.2, sx - 0.9), (sx + 0.9, sx + 5.2)):
        draw_closed_poly(sk_ears, [
            (ex1, sy + sr_in - 0.5, z_sens_mid),
            (ex2, sy + sr_in - 0.5, z_sens_mid),
            (ex2, sy + sr_out + 6.0, z_sens_mid),
            (ex1, sy + sr_out + 6.0, z_sens_mid),
        ])
    extrude_symmetric(comp, sk_ears, sens_h, adsk.fusion.FeatureOperations.JoinFeatureOperation, all_profiles=True)

    sk_sbore = comp.sketches.add(pl_sens)
    sk_sbore.name = 'Distance_Sensor_Bore'
    sk_sbore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sbore, sx, sy, z_sens_mid), mm(sr_in))
    extrude_symmetric(comp, sk_sbore, sens_h + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    sk_sslit = comp.sketches.add(pl_sens)
    sk_sslit.name = 'Distance_Sensor_Flex_Slit'
    draw_closed_poly(sk_sslit, [
        (sx - 0.9, sy, z_sens_mid),
        (sx + 0.9, sy, z_sens_mid),
        (sx + 0.9, sy + sr_out + 6.8, z_sens_mid),
        (sx - 0.9, sy + sr_out + 6.8, z_sens_mid),
    ])
    extrude_symmetric(comp, sk_sslit, sens_h + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # Horizontal M3 screw hole + left screw-head counterbore + right captive hex nut pocket
    y_pinch = sy + sr_out + 2.2
    pl_px = offset_plane(comp, comp.yZConstructionPlane, sx, adsk.core.Vector3D.create(1, 0, 0))
    sk_pscrew = comp.sketches.add(pl_px)
    sk_pscrew.name = 'Distance_Sensor_Pinch_M3_Hole'
    sk_pscrew.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_pscrew, sx, y_pinch, z_sens_mid), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_pscrew, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    pl_pcb = offset_plane(comp, comp.yZConstructionPlane, sx - 4.3, adsk.core.Vector3D.create(1, 0, 0))
    sk_pcb = comp.sketches.add(pl_pcb)
    sk_pcb.name = 'Distance_Sensor_Pinch_M3_Counterbore'
    sk_pcb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_pcb, sx - 4.3, y_pinch, z_sens_mid), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_pcb, 2.4, adsk.fusion.FeatureOperations.CutFeatureOperation)

    pl_pnut = offset_plane(comp, comp.yZConstructionPlane, sx + 3.9, adsk.core.Vector3D.create(1, 0, 0))
    sk_pnut = comp.sketches.add(pl_pnut)
    sk_pnut.name = 'Distance_Sensor_Pinch_Hex_Nut_Pocket'
    r_hex = 2.9 / math.cos(math.radians(30.0))  # 5.8mm across flats M3 hex nut pocket
    hex_pts = [
        (
            sx + 3.9,
            y_pinch + r_hex * math.cos(k * math.pi / 3.0),
            z_sens_mid + r_hex * math.sin(k * math.pi / 3.0),
        )
        for k in range(6)
    ]
    draw_closed_poly(sk_pnut, hex_pts)
    extrude_symmetric(comp, sk_pnut, 3.2, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_belt_clamp_jaw(root: adsk.fusion.Component, side_name: str, x_center_mm: float) -> None:
    """Components 2 & 3: Horizontal GT2 top-down bridge clamps aligned to rear flat face Y=-23.5."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = f'PnP_Belt_Clamp_{side_name}'

    pl_side = offset_plane(comp, comp.yZConstructionPlane, x_center_mm, adsk.core.Vector3D.create(1, 0, 0))
    sk_jaw = comp.sketches.add(pl_side)
    sk_jaw.name = f'Horizontal_Belt_Clamp_Profile_{side_name}'
    draw_closed_poly(sk_jaw, [
        (x_center_mm, -23.5, 30.8),
        (x_center_mm, -13.5, 30.8),
        (x_center_mm, -13.5, 31.2),
        (x_center_mm, -12.6, 31.2),
        (x_center_mm, -12.6, 30.6),
        (x_center_mm, -6.4, 30.6),
        (x_center_mm, -6.4, 31.2),
        (x_center_mm, -5.8, 31.2),
        (x_center_mm, -5.8, 30.8),
        (x_center_mm, -3.8, 30.8),
        (x_center_mm, -3.8, 36.4),
        (x_center_mm, -23.5, 36.4),
    ])
    extrude_symmetric(comp, sk_jaw, 12.0, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    by = CFG['belt_clamp_y']
    pl_hole = offset_plane(comp, comp.xYConstructionPlane, 33.6, adsk.core.Vector3D.create(0, 0, 1))
    sk_hole = comp.sketches.add(pl_hole)
    sk_hole.name = 'M3_Vertical_Hole'
    sk_hole.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hole, x_center_mm, by, 33.6), mm(1.8))
    extrude_symmetric(comp, sk_hole, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    pl_cb = offset_plane(comp, comp.xYConstructionPlane, 35.05, adsk.core.Vector3D.create(0, 0, 1))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'M3_Top_Counterbore'
    sk_cb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cb, x_center_mm, by, 35.05), mm(CFG['screw_head_dia'] / 2.0))
    extrude_symmetric(comp, sk_cb, 3.7, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_universal_flex_syringe_mount(root: adsk.fusion.Component) -> None:
    """Component 4: Flat-back screw-mounted syringe holder with compliant jaws for 8-17mm syringes."""
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
    for sx in (-mx, mx):
        for sz in (mz_lo, mz_hi):
            sk_holes.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_holes, sx, 17.5, sz), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_holes, 10.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xZConstructionPlane, 19.8, adsk.core.Vector3D.create(0, 1, 0))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Syringe_Mount_M3_Counterbores'
    for sx in (-mx, mx):
        for sz in (mz_lo, mz_hi):
            sk_cb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cb, sx, 19.8, sz), mm(CFG['screw_head_dia'] / 2.0))
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
        for sx in (-1.0, 1.0):
            draw_closed_poly(sk_lug, [
                (sx * 26.0, 13.5, z_jaw),
                (sx * 28.8, 13.5, z_jaw),
                (sx * 28.8, 17.5, z_jaw),
                (sx * 26.0, 17.5, z_jaw),
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
    """Component 5: Flat-back screw-mounted exact-fit snap cradle driven by CFG['syringe_od'] (at X=+95mm)."""
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
    for sx in (-mx, mx):
        for sz in (mz_lo, mz_hi):
            sk_holes.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_holes, sx, 17.25, sz), mm(CFG['screw_hole_dia'] / 2.0))
    extrude_symmetric(comp, sk_holes, 10.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xZConstructionPlane, 19.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Syringe_Mount_M3_Counterbores'
    for sx in (-mx, mx):
        for sz in (mz_lo, mz_hi):
            sk_cb.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cb, sx, 19.5, sz), mm(CFG['screw_head_dia'] / 2.0))
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
        build_belt_clamp_jaw(root, 'Left', -CFG['belt_clamp_x'])
        build_belt_clamp_jaw(root, 'Right', CFG['belt_clamp_x'])
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
                'Created Updated Prusa MINI PnP Head in a new file:\n\n'
                '1. PnP_Carriage_Base (47.7 x 27.0mm rear M3 grid + screw/hex-nut distance sensor clamp)\n'
                '2. PnP_Belt_Clamp_Left & Right (horizontal GT2 clamps at X=+/-13.5mm)\n'
                '3. PnP_Universal_Flex_Syringe_Mount (flat back with 4x M3 holes + spring jaws for 8-17mm syringes)\n'
                '4. PnP_Sized_Syringe_Mount (at X=+95mm, flat back with 4x M3 holes + exact snap cradle)\n'
                '5. PnP_Vacuum_Nozzle_Adapter (printable 8mm hollow Luer-slip PnP barrel)'
            )

    except Exception:
        if ui:
            ui.messageBox('Script Failed:\n{}'.format(traceback.format_exc()))