import adsk.core
import adsk.fusion
import math
import traceback

# ==============================================================================
# CONFIGURATION (all dimensions in mm)
# ==============================================================================
CFG = {
    'rod_spacing': 34.0,          # Center-to-center vertical distance between X smooth rods (verify: outer_to_outer - 8.0)
    'rod_dia': 8.0,               # Smooth rod diameter
    'rod_clear_dia': 9.6,         # End-wall rod clearance bore diameter
    'lm8uu_od': 15.2,             # LM8UU 15mm OD + 0.2mm print fit clearance
    'lm8uu_len': 24.4,            # LM8UU 24mm length + 0.4mm axial clearance
    'carriage_width': 55.0,       # Total carriage width along X
    'belt_width': 6.8,            # Horizontal GT2 belt channel width along Y (centered at Y=0.0, aligned with LM8UU)
    'belt_spacing': 11.4,         # Center-to-center Z distance between upper & lower GT2 belt runs (623 idler 10mm + 1.38mm belt)
    'screw_hole_dia': 3.4,        # M3 clearance bore
    'screw_thread_dia': 3.2,      # M3 self-threading / tight pass bore
    'screw_head_dia': 6.2,        # M3 screw head counterbore
    'belt_clamp_x': 8.0,          # Left/Right X offset of the 2 belt-clamp screws (+/- 8.0mm, clears +/-16mm rear grid)
    'belt_clamp_y': -13.8,        # Y centerline of vertical belt-clamp screws & nut bays (clears -10.5 cap & -17.4 rear nut bays)
    'mount_screw_x': 16.5,        # X offset of front syringe-mount screw grid (+/- 16.5mm -> 33mm wide)
    'mount_screw_z_lo': 6.5,      # Lower Z of front syringe-mount screw grid (blind in front of Y=+4.5mm)
    'mount_screw_z_hi': 26.5,     # Upper Z of front syringe-mount screw grid (20mm tall, clear of stylus Z=17.0)
    'stylus_hole_offset': 16.0,   # Stylus holder HOLE_OFFSET (+/- 16.0mm -> 32x32mm grid)
    'stylus_center_z': 33.0,      # Centered at z_mid + 16.0 (holes at Z=17.0 & 49.0 for rod_spacing=34.0)
    'rear_mount_x': 16.0,         # X offset of rear/bottom M3 grid (+/- 16.0mm -> 32.0mm wide)
    'rear_mount_z_lo': 17.0,      # Lower Z of rear/bottom M3 grid (z_mid, between lower & upper belt runs)
    'rear_mount_z_hi': 49.0,      # Upper Z of rear/bottom M3 grid (z_mid + 32.0, clear above upper rod)
    'sensor_dia': 12.0,           # CHE12-4NA-A710 M12 inductive proximity sensor OD
    'sensor_x': 34.5,             # Distance sensor X center (clears syringe mount & 20.2mm OD collar)
    'sensor_y': 22.66,            # Distance sensor Y center (aligned with vacuum nozzle Y=22.66 -> dY=0)
    'sensor_z_mid': -7.5,         # Distance sensor clamp Z midpoint (-16.5..+1.5, flush with carriage bottom)
    'sensor_h': 18.0,             # Distance sensor clamp vertical height
    'syringe_od': 10.3,           # Dedicated PnP_Sized_Syringe_Mount OD (1mL=6.8, 3mL=10.3, 5mL=13.8, 10mL=16.2)
    'nozzle_od': 8.0,             # Printable PnP_Vacuum_Nozzle_Adapter barrel OD
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


def derive_layout() -> dict:
    """Derive vertical layout coordinates parametrically from rod_spacing & belt_spacing."""
    rs = CFG['rod_spacing']
    bs = CFG['belt_spacing']
    z_mid = rs / 2.0
    z_belt_lo = z_mid - bs / 2.0
    z_belt_hi = z_mid + bs / 2.0
    return {
        'rs': rs,
        'z_mid': z_mid,
        'z_bot': -16.5,
        'z_top': z_mid + 37.5,          # 54.5mm at rs=34 -> 2.5mm solid roof above Z=49.0 nut bays
        'z_belt_lo': z_belt_lo,
        'z_belt_hi': z_belt_hi,
        'z_cap_up_screw': rs + 12.0,    # 46.0mm at rs=34
        'z_cap_lo_screw': -12.0,
        'z_grid_lo': z_mid,             # 17.0mm at rs=34 (between belts)
        'z_grid_hi': z_mid + 32.0,      # 49.0mm at rs=34 (above upper rod)
    }


def build_carriage_base(root: adsk.fusion.Component) -> None:
    """Component 1: PnP_Carriage_Base with symmetric toothed upper/lower belt grooves, full-circle rod bores & nut bays."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Carriage_Base'

    lay = derive_layout()
    rs = lay['rs']
    z_bot = lay['z_bot']
    z_top = lay['z_top']
    z_belt_lo = lay['z_belt_lo']
    z_belt_hi = lay['z_belt_hi']

    cw = CFG['carriage_width']
    hw = cw / 2.0
    lm_od = CFG['lm8uu_od']
    lm_len = CFG['lm8uu_len']
    y_front = 13.5
    y_snap = -3.8
    y_tower_back = -23.5
    z_tower_bot = z_belt_lo
    z_tower_top = z_belt_hi

    # 1. Main body with completely FLAT front (+Y = 13.5) and FLAT rear (-Y = -23.5) symmetric belt tower
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

    # 1b. Upper rear outer mounting columns (|X| = 12.5..27.5, clears Z <= z_belt_hi+2.2 belt-pinch wings)
    for side_tag, x_col in (('Left', -20.0), ('Right', 20.0)):
        pl_col = offset_plane(comp, comp.yZConstructionPlane, x_col, adsk.core.Vector3D.create(1, 0, 0))
        sk_col = comp.sketches.add(pl_col)
        sk_col.name = f'Upper_Rear_Mount_Column_{side_tag}'
        draw_closed_poly(sk_col, [
            (x_col, y_tower_back, z_belt_hi + 2.5),
            (x_col, y_front,      z_belt_hi + 2.5),
            (x_col, y_front,      z_top),
            (x_col, y_tower_back, z_top),
        ])
        extrude_symmetric(comp, sk_col, 15.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 1c. Lower outer rod cheeks (|X| = 12.5..27.5, encloses lower rod at Y=-7.5, clears Z >= z_belt_lo-2.2 pinch wings)
    for side_tag, x_col in (('Left', -20.0), ('Right', 20.0)):
        pl_lchk = offset_plane(comp, comp.yZConstructionPlane, x_col, adsk.core.Vector3D.create(1, 0, 0))
        sk_lchk = comp.sketches.add(pl_lchk)
        sk_lchk.name = f'Lower_Outer_Rod_Cheek_{side_tag}'
        draw_closed_poly(sk_lchk, [
            (x_col, y_snap, -11.7),
            (x_col, -7.5,    -8.0),
            (x_col, -7.5,    z_belt_lo - 2.5),
            (x_col, y_snap,  z_belt_lo - 2.5),
        ])
        extrude_symmetric(comp, sk_lchk, 15.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 2. Cut 2x LM8UU front-half cylindrical bearing seats (Y = 0.0, Z = 0 & rs)
    sk_bearings = comp.sketches.add(comp.yZConstructionPlane)
    sk_bearings.name = 'LM8UU_Front_Half_Cradles'
    sk_bearings.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bearings, 0, 0, 0), mm(lm_od / 2.0))
    sk_bearings.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bearings, 0, 0, rs), mm(lm_od / 2.0))
    extrude_symmetric(comp, sk_bearings, lm_len, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 2b. Cut upper bearing-cap seating pocket (|X| <= 12.3, Y <= +0.2, Z = z_belt_hi + 0.1..z_top + 0.5)
    sk_up_pkt = comp.sketches.add(comp.yZConstructionPlane)
    sk_up_pkt.name = 'Upper_Bearing_Cap_Pocket'
    draw_closed_poly(sk_up_pkt, [
        (0.0, -24.0, z_belt_hi + 0.1),
        (0.0,   0.2, z_belt_hi + 0.1),
        (0.0,   0.2, z_top + 0.5),
        (0.0, -24.0, z_top + 0.5),
    ])
    extrude_symmetric(comp, sk_up_pkt, lm_len + 0.2, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2c. Cut upper belt-pinch channel across full width (Y = -24.0..+3.8, Z = z_belt_hi - 0.1..z_belt_hi + 2.2)
    sk_ub_chan = comp.sketches.add(comp.yZConstructionPlane)
    sk_ub_chan.name = 'Upper_Belt_Pinch_Channel'
    draw_closed_poly(sk_ub_chan, [
        (0.0, -24.0, z_belt_hi - 0.1),
        (0.0,   3.8, z_belt_hi - 0.1),
        (0.0,   3.8, z_belt_hi + 2.2),
        (0.0, -24.0, z_belt_hi + 2.2),
    ])
    extrude_symmetric(comp, sk_ub_chan, cw + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2d. Cut lower bearing-cap seating pocket (|X| <= 12.3, Y <= +0.2, Z = z_bot - 0.5..z_belt_lo - 0.1)
    sk_lo_pkt = comp.sketches.add(comp.yZConstructionPlane)
    sk_lo_pkt.name = 'Lower_Bearing_Cap_Pocket'
    draw_closed_poly(sk_lo_pkt, [
        (0.0, -24.0, z_bot - 0.5),
        (0.0,   0.2, z_bot - 0.5),
        (0.0,   0.2, z_belt_lo - 0.1),
        (0.0, -24.0, z_belt_lo - 0.1),
    ])
    extrude_symmetric(comp, sk_lo_pkt, lm_len + 0.2, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2e. Cut lower belt-pinch channel across full width (Y = -24.0..+3.8, Z = z_belt_lo - 2.2..z_belt_lo + 0.1)
    sk_lb_chan = comp.sketches.add(comp.yZConstructionPlane)
    sk_lb_chan.name = 'Lower_Belt_Pinch_Channel'
    draw_closed_poly(sk_lb_chan, [
        (0.0, -24.0, z_belt_lo - 2.2),
        (0.0,   3.8, z_belt_lo - 2.2),
        (0.0,   3.8, z_belt_lo + 0.1),
        (0.0, -24.0, z_belt_lo + 0.1),
    ])
    extrude_symmetric(comp, sk_lb_chan, cw + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 2f. M3 clearance holes in base for Upper Bearing Cap (X=+/-6.5, Z=rs+12.0, Y=-0.5..+12.0 -> feeds nut pocket)
    pl_cap_th = offset_plane(comp, comp.xZConstructionPlane, 5.75, adsk.core.Vector3D.create(0, 1, 0))
    sk_up_th = comp.sketches.add(pl_cap_th)
    sk_up_th.name = 'Upper_Bearing_Cap_M3_Clearance_Holes'
    for sx_h in (-6.5, 6.5):
        sk_up_th.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_up_th, sx_h, 5.75, lay['z_cap_up_screw']),
            mm(CFG['screw_hole_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_up_th, 12.5, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 2g. M3 clearance holes in base for Lower Bearing Cap bottom (X=+/-6.5, Z=-12.0, Y=-0.5..+12.0 -> feeds nut pocket)
    sk_lo_th = comp.sketches.add(pl_cap_th)
    sk_lo_th.name = 'Lower_Bearing_Cap_Bottom_M3_Clearance_Holes'
    for sx_h in (-6.5, 6.5):
        sk_lo_th.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_lo_th, sx_h, 5.75, lay['z_cap_lo_screw']),
            mm(CFG['screw_hole_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_lo_th, 12.5, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 3. Cut closed full-circle 8mm smooth rod clearance bores (no U-slots)
    rod_r = CFG['rod_clear_dia'] / 2.0
    sk_rods = comp.sketches.add(comp.yZConstructionPlane)
    sk_rods.name = 'Smooth_Rod_Clearance_Bores'
    sk_rods.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_rods, 0, 0, 0), mm(rod_r))
    sk_rods.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_rods, 0, 0, rs), mm(rod_r))
    extrude_symmetric(comp, sk_rods, cw + 4.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 4. Lower horizontal GT2 toothed belt grooves (aligned at Y = 0.0, 12 teeth per side pointing down into belt)
    sk_belt_lo = comp.sketches.add(comp.xZConstructionPlane)
    sk_belt_lo.name = 'GT2_Lower_Horizontal_Toothed_Grooves'

    lo_left_pts = [(-(hw + 0.5), 0.0, z_belt_lo - 0.5), (-3.6, 0.0, z_belt_lo - 0.5), (-3.6, 0.0, z_belt_lo)]
    for k in range(12):
        xr = -4.0 - 2.0 * k
        xl = xr - 1.1
        lo_left_pts.extend([
            (xr, 0.0, z_belt_lo),
            (xr, 0.0, z_belt_lo + 0.75),
            (xl, 0.0, z_belt_lo + 0.75),
            (xl, 0.0, z_belt_lo),
        ])
    lo_left_pts.append((-(hw + 0.5), 0.0, z_belt_lo))
    draw_closed_poly(sk_belt_lo, lo_left_pts)

    lo_right_pts = [(-px, py, pz) for (px, py, pz) in lo_left_pts]
    draw_closed_poly(sk_belt_lo, lo_right_pts)
    extrude_symmetric(comp, sk_belt_lo, CFG['belt_width'], adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 5. Upper horizontal GT2 toothed belt grooves (aligned at Y = 0.0, 12 teeth per side pointing up into belt)
    sk_belt_hi = comp.sketches.add(comp.xZConstructionPlane)
    sk_belt_hi.name = 'GT2_Upper_Horizontal_Toothed_Grooves'

    left_pts = [(-(hw + 0.5), 0.0, z_belt_hi + 0.5), (-3.6, 0.0, z_belt_hi + 0.5), (-3.6, 0.0, z_belt_hi)]
    for k in range(12):
        xr = -4.0 - 2.0 * k
        xl = xr - 1.1
        left_pts.extend([
            (xr, 0.0, z_belt_hi),
            (xr, 0.0, z_belt_hi - 0.75),
            (xl, 0.0, z_belt_hi - 0.75),
            (xl, 0.0, z_belt_hi),
        ])
    left_pts.append((-(hw + 0.5), 0.0, z_belt_hi))
    draw_closed_poly(sk_belt_hi, left_pts)

    right_pts = [(-px, py, pz) for (px, py, pz) in left_pts]
    draw_closed_poly(sk_belt_hi, right_pts)
    extrude_symmetric(comp, sk_belt_hi, CFG['belt_width'], adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 6. Open center excess-belt exit slots for BOTH upper and lower belts (Y = +3.4 out to rear -24.0, |X| <= 3.6)
    pl_exit = offset_plane(comp, comp.xZConstructionPlane, -10.3, adsk.core.Vector3D.create(0, 1, 0))
    sk_exit = comp.sketches.add(pl_exit)
    sk_exit.name = 'Excess_Belt_Center_Exit_Slots'
    draw_closed_poly(sk_exit, [
        (-3.6, -10.3, z_belt_hi - 0.75),
        ( 3.6, -10.3, z_belt_hi - 0.75),
        ( 3.6, -10.3, z_belt_hi + 0.5),
        (-3.6, -10.3, z_belt_hi + 0.5),
    ])
    draw_closed_poly(sk_exit, [
        (-3.6, -10.3, z_belt_lo - 0.5),
        ( 3.6, -10.3, z_belt_lo - 0.5),
        ( 3.6, -10.3, z_belt_lo + 0.75),
        (-3.6, -10.3, z_belt_lo + 0.75),
    ])
    extrude_symmetric(comp, sk_exit, 27.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 7. Full through vertical M3 belt-clamp screw bores (Z = z_belt_lo - 0.5 to z_belt_hi + 0.5, serves both clamps)
    bx = CFG['belt_clamp_x']
    by = CFG['belt_clamp_y']
    z_sc_lo = z_belt_lo - 0.5
    z_sc_hi = z_belt_hi + 0.5
    z_sc_mid = (z_sc_lo + z_sc_hi) / 2.0
    pl_sc = offset_plane(comp, comp.xYConstructionPlane, z_sc_mid, adsk.core.Vector3D.create(0, 0, 1))
    sk_sc = comp.sketches.add(pl_sc)
    sk_sc.name = 'Belt_Clamp_Full_Through_M3_Bores'
    sk_sc.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sc, -bx, by, z_sc_mid), mm(1.8))
    sk_sc.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_sc, bx, by, z_sc_mid), mm(1.8))
    extrude_symmetric(comp, sk_sc, z_sc_hi - z_sc_lo, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 8. Original straight full-height side-entry flexible captive nut bays (Z = z_belt_lo+2.0..z_belt_hi-2.5)
    z_bay_lo = z_belt_lo + 2.0
    z_bay_hi = z_belt_hi - 2.5
    z_bay_mid = (z_bay_lo + z_bay_hi) / 2.0
    z_bay_h = z_bay_hi - z_bay_lo
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

    # Helpers for MINIMAL captive M3 nut bays (4.1-4.2mm deep along screw axis for locknuts & varying screw lengths)
    def add_mini_outer_side_nut_bay(name: str, x_hole: float, y_center: float, z_center: float, bay_w: float = 4.2) -> None:
        """6.0mm tall outer side-entry nut slot (fits standard M3 nuts, washers, or 4mm locknuts)."""
        hw_bay = bay_w / 2.0
        hw_pinch = hw_bay - 0.4
        x_in = x_hole - 3.2
        pl = offset_plane(comp, comp.xYConstructionPlane, z_center, adsk.core.Vector3D.create(0, 0, 1))
        sk = comp.sketches.add(pl)
        sk.name = name
        left_pts = [
            (-(hw + 0.2), y_center - hw_bay,   z_center),
            (-25.0,       y_center - hw_bay,   z_center),
            (-24.8,       y_center - hw_pinch, z_center),
            (-24.0,       y_center - hw_pinch, z_center),
            (-23.8,       y_center - hw_bay,   z_center),
            (-x_in,       y_center - hw_bay,   z_center),
            (-x_in,       y_center + hw_bay,   z_center),
            (-23.8,       y_center + hw_bay,   z_center),
            (-24.0,       y_center + hw_pinch, z_center),
            (-24.8,       y_center + hw_pinch, z_center),
            (-25.0,       y_center + hw_bay,   z_center),
            (-(hw + 0.2), y_center + hw_bay,   z_center),
        ]
        draw_closed_poly(sk, left_pts)
        draw_closed_poly(sk, [(-px, py, pz) for (px, py, pz) in left_pts])
        extrude_symmetric(comp, sk, 6.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    def add_mini_inner_pocket_nut_bay(name: str, x_hole: float, y_center: float, z_center: float, bay_w: float = 4.1) -> None:
        """Short 7.1mm nut slot cut outward from the open bearing-cap pocket (|X|=12.1..19.2)."""
        hw_bay = bay_w / 2.0
        hw_pinch = hw_bay - 0.4
        x_out = x_hole + 3.2
        pl = offset_plane(comp, comp.xYConstructionPlane, z_center, adsk.core.Vector3D.create(0, 0, 1))
        sk = comp.sketches.add(pl)
        sk.name = name
        left_pts = [
            (-12.1,  y_center - hw_bay,   z_center),
            (-12.4,  y_center - hw_bay,   z_center),
            (-12.5,  y_center - hw_pinch, z_center),
            (-12.9,  y_center - hw_pinch, z_center),
            (-13.0,  y_center - hw_bay,   z_center),
            (-x_out, y_center - hw_bay,   z_center),
            (-x_out, y_center + hw_bay,   z_center),
            (-13.0,  y_center + hw_bay,   z_center),
            (-12.9,  y_center + hw_pinch, z_center),
            (-12.5,  y_center + hw_pinch, z_center),
            (-12.4,  y_center + hw_bay,   z_center),
            (-12.1,  y_center + hw_bay,   z_center),
        ]
        draw_closed_poly(sk, left_pts)
        draw_closed_poly(sk, [(-px, py, pz) for (px, py, pz) in left_pts])
        extrude_symmetric(comp, sk, 6.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    def add_mini_top_drop_nut_bay(name: str, x_hole: float, y_center: float, z_hole: float, z_open: float, bay_w: float = 4.2) -> None:
        """Short vertical drop-in nut pocket from an open +Z face/arch."""
        hw_x = 6.0 / 2.0
        hw_pinch = 5.2 / 2.0
        z_bot_bay = z_hole - 3.0
        z_pinch_lo = z_open - 2.0
        z_pinch_hi = z_open - 1.0
        z_top_bay = z_open + 0.2
        pl = offset_plane(comp, comp.xZConstructionPlane, y_center, adsk.core.Vector3D.create(0, 1, 0))
        sk = comp.sketches.add(pl)
        sk.name = name
        for side in (-1.0, 1.0):
            cx = side * x_hole
            draw_closed_poly(sk, [
                (cx - hw_x,     y_center, z_bot_bay),
                (cx + hw_x,     y_center, z_bot_bay),
                (cx + hw_x,     y_center, z_pinch_lo),
                (cx + hw_pinch, y_center, z_pinch_lo + 0.2),
                (cx + hw_pinch, y_center, z_pinch_hi - 0.2),
                (cx + hw_x,     y_center, z_pinch_hi),
                (cx + hw_x,     y_center, z_top_bay),
                (cx - hw_x,     y_center, z_top_bay),
                (cx - hw_x,     y_center, z_pinch_hi),
                (cx - hw_pinch, y_center, z_pinch_hi - 0.2),
                (cx - hw_pinch, y_center, z_pinch_lo + 0.2),
                (cx - hw_x,     y_center, z_pinch_lo),
            ])
        extrude_symmetric(comp, sk, bay_w, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    def add_mini_bottom_drop_nut_bay(name: str, x_hole: float, y_center: float, z_hole: float, z_open: float, bay_w: float = 4.2) -> None:
        """Short vertical drop-in nut pocket from the bottom -Z face."""
        hw_x = 6.0 / 2.0
        hw_pinch = 5.2 / 2.0
        z_top_bay = z_hole + 3.0
        z_pinch_hi = z_open + 2.0
        z_pinch_lo = z_open + 1.0
        z_bot_bay = z_open - 0.2
        pl = offset_plane(comp, comp.xZConstructionPlane, y_center, adsk.core.Vector3D.create(0, 1, 0))
        sk = comp.sketches.add(pl)
        sk.name = name
        for side in (-1.0, 1.0):
            cx = side * x_hole
            draw_closed_poly(sk, [
                (cx - hw_x,     y_center, z_top_bay),
                (cx + hw_x,     y_center, z_top_bay),
                (cx + hw_x,     y_center, z_pinch_hi),
                (cx + hw_pinch, y_center, z_pinch_hi - 0.2),
                (cx + hw_pinch, y_center, z_pinch_lo + 0.2),
                (cx + hw_x,     y_center, z_pinch_lo),
                (cx + hw_x,     y_center, z_bot_bay),
                (cx - hw_x,     y_center, z_bot_bay),
                (cx - hw_x,     y_center, z_pinch_lo),
                (cx - hw_pinch, y_center, z_pinch_lo + 0.2),
                (cx - hw_pinch, y_center, z_pinch_hi - 0.2),
                (cx - hw_x,     y_center, z_pinch_hi),
            ])
        extrude_symmetric(comp, sk, bay_w, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 9b. Captive M3 nut pockets for Upper & Lower Bearing Cap horizontal clamping screws (X=+/-6.5, Y=+5.4..+9.6)
    add_mini_top_drop_nut_bay('Upper_Bearing_Cap_Top_Nut_Bays', x_hole=6.5, y_center=7.5, z_hole=lay['z_cap_up_screw'], z_open=z_top, bay_w=4.2)
    add_mini_bottom_drop_nut_bay('Lower_Bearing_Cap_Bottom_Nut_Bays', x_hole=6.5, y_center=7.5, z_hole=lay['z_cap_lo_screw'], z_open=z_bot, bay_w=4.2)

    # 10. Front flat-face 4x Syringe Mount M3 clearance holes (Y = +4.5..+13.5) + 4.2mm Deep Mini Nut Bays
    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']
    pl_front_m = offset_plane(comp, comp.xZConstructionPlane, 9.05, adsk.core.Vector3D.create(0, 1, 0))
    sk_fm = comp.sketches.add(pl_front_m)
    sk_fm.name = 'Front_Flat_Syringe_Mount_M3_Holes'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_fm.sketchCurves.sketchCircles.addByCenterRadius(
                wpt(sk_fm, sx_h, 9.05, sz_h),
                mm(CFG['screw_hole_dia'] / 2.0),
            )
    extrude_symmetric(comp, sk_fm, 9.1, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    for sz_h in (mz_lo, mz_hi):
        add_mini_outer_side_nut_bay(f'Front_Syringe_Mini_Nut_Bay_Z{sz_h}', x_hole=mx, y_center=7.5, z_center=sz_h, bay_w=4.2)

    # 11. Coaxial Front + Rear 32x32mm M3 clearance through-holes + Minimal Closest-Side Nut Bays
    rx = CFG['rear_mount_x']
    pl_thru = offset_plane(comp, comp.xZConstructionPlane, -5.0, adsk.core.Vector3D.create(0, 1, 0))
    sk_rm = comp.sketches.add(pl_thru)
    sk_rm.name = 'Front_Rear_Coaxial_32x32_M3_Through_Holes'
    for sx_h in (-rx, rx):
        for sz_h in (lay['z_grid_lo'], lay['z_grid_hi']):
            sk_rm.sketchCurves.sketchCircles.addByCenterRadius(
                wpt(sk_rm, sx_h, -5.0, sz_h),
                mm(CFG['screw_hole_dia'] / 2.0),
            )
    extrude_symmetric(comp, sk_rm, 38.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # Lower 32x32 (Z=z_grid_lo): Front uses slim outer side cut; Rear drops straight down from open arch above belt tower
    add_mini_outer_side_nut_bay(f'Front_32x32_Mini_Nut_Bay_Z{lay["z_grid_lo"]}', x_hole=rx, y_center=7.5, z_center=lay['z_grid_lo'], bay_w=4.2)
    add_mini_top_drop_nut_bay(f'Rear_32x32_Mini_Arch_Nut_Bay_Z{lay["z_grid_lo"]}', x_hole=rx, y_center=-19.45, z_hole=lay['z_grid_lo'], z_open=z_belt_hi, bay_w=4.1)

    # Upper 32x32 (Z=z_grid_hi): Front drops straight down from top face; Rear cuts outward from open inner cap pocket
    add_mini_top_drop_nut_bay(f'Front_32x32_Mini_Top_Nut_Bay_Z{lay["z_grid_hi"]}', x_hole=rx, y_center=7.5, z_hole=lay['z_grid_hi'], z_open=z_top, bay_w=4.2)
    add_mini_inner_pocket_nut_bay(f'Rear_32x32_Mini_Inner_Nut_Bay_Z{lay["z_grid_hi"]}', x_hole=rx, y_center=-19.45, z_center=lay['z_grid_hi'], bay_w=4.1)

    # 12. Distance Sensor Holder (CHE12-4NA-A710, 12.0mm): Nozzle-aligned Y=22.66, X=34.5, Z=-16.5..+1.5
    sx = CFG['sensor_x']
    sy = CFG['sensor_y']
    z_sens_mid = CFG['sensor_z_mid']
    sens_h = CFG['sensor_h']
    sr_in = (CFG['sensor_dia'] + 0.2) / 2.0
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
        (sx,              sy - 0.9, z_sens_mid),
        (ear_x_end + 0.8, sy - 0.9, z_sens_mid),
        (ear_x_end + 0.8, sy + 0.9, z_sens_mid),
        (sx,              sy + 0.9, z_sens_mid),
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
    """Component 2: Unified GT2 Belt Clamp + Upper LM8UU Linear Bearing Rear Cap (Y=0 aligned)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Upper_Belt_Bearing_Clamp'

    lay = derive_layout()
    rs = lay['rs']
    z_top = lay['z_top'] - 0.2
    z_bh = lay['z_belt_hi']
    cap_w = CFG['lm8uu_len'] - 0.2   # 24.2mm (X = -12.1..+12.1)
    bx = CFG['belt_clamp_x']
    by = CFG['belt_clamp_y']

    # 1. Bearing cap core + rear vertical-screw flange (24.2mm wide)
    sk_body = comp.sketches.add(comp.yZConstructionPlane)
    sk_body.name = 'Upper_Bearing_And_Belt_Clamp_Profile'
    draw_closed_poly(sk_body, [
        (0.0, -18.5, z_bh + 0.5),
        (0.0,  -3.8, z_bh + 0.5),
        (0.0,  -3.8, z_bh + 2.0),
        (0.0,   0.0, z_bh + 2.0),
        (0.0,   0.0, z_top),
        (0.0, -10.5, z_top),
        (0.0, -10.5, z_bh + 6.5),
        (0.0, -18.5, z_bh + 6.5),
    ])
    extrude_symmetric(comp, sk_body, cap_w, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # 1b. Forward belt-pinch bridge + outer pinch wings (44.0mm wide: X=-22.0..+22.0, Y=-10.5..+3.4)
    sk_wing = comp.sketches.add(comp.yZConstructionPlane)
    sk_wing.name = 'Upper_Belt_Pinch_Wings'
    draw_closed_poly(sk_wing, [
        (0.0, -10.5, z_bh + 0.5),
        (0.0,  -3.4, z_bh + 0.5),
        (0.0,  -3.4, z_bh + 0.3),
        (0.0,   3.4, z_bh + 0.3),
        (0.0,   3.4, z_bh + 2.0),
        (0.0, -10.5, z_bh + 2.0),
    ])
    extrude_symmetric(comp, sk_wing, 44.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 2. Cut center excess-belt exit relief under the bridge (X = -3.7..+3.7)
    sk_rel = comp.sketches.add(comp.yZConstructionPlane)
    sk_rel.name = 'Center_Excess_Belt_Exit_Relief'
    draw_closed_poly(sk_rel, [
        (0.0, -19.0, z_bh - 0.2),
        (0.0,  -3.4, z_bh - 0.2),
        (0.0,  -3.4, z_bh + 1.1),
        (0.0, -19.0, z_bh + 1.1),
    ])
    extrude_symmetric(comp, sk_rel, 7.4, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 3. Cut 2x vertical M3 belt-clamp holes + top counterbores (X = +/-8.0, Y = -13.8)
    z_hole_mid = z_bh + 3.5
    pl_hole = offset_plane(comp, comp.xYConstructionPlane, z_hole_mid, adsk.core.Vector3D.create(0, 0, 1))
    sk_hole = comp.sketches.add(pl_hole)
    sk_hole.name = 'Belt_Clamp_M3_Vertical_Holes'
    for sx_h in (-bx, bx):
        sk_hole.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hole, sx_h, by, z_hole_mid), mm(1.8))
    extrude_symmetric(comp, sk_hole, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    z_cb_mid = z_bh + 5.2
    pl_cb = offset_plane(comp, comp.xYConstructionPlane, z_cb_mid, adsk.core.Vector3D.create(0, 0, 1))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Belt_Clamp_M3_Top_Counterbores'
    for sx_h in (-bx, bx):
        sk_cb.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_cb, sx_h, by, z_cb_mid),
            mm(CFG['screw_head_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_cb, 3.6, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 4. Cut Upper LM8UU semicircular rear bearing seat (centered at Y=0.0, Z=rs)
    sk_bore = comp.sketches.add(comp.yZConstructionPlane)
    sk_bore.name = 'Upper_LM8UU_Rear_Half_Bore'
    sk_bore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bore, 0.0, 0.0, rs), mm(CFG['lm8uu_od'] / 2.0))
    extrude_symmetric(comp, sk_bore, cap_w + 1.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 5. Cut 2x horizontal M3 clamping holes + counterbores above the bearing (X=+/-6.5, Z=rs+12.0, M3x16)
    pl_mh = offset_plane(comp, comp.xZConstructionPlane, -5.25, adsk.core.Vector3D.create(0, 1, 0))
    sk_mh = comp.sketches.add(pl_mh)
    sk_mh.name = 'Upper_Bearing_Clamp_M3_Holes'
    for sx_h in (-6.5, 6.5):
        sk_mh.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_mh, sx_h, -5.25, lay['z_cap_up_screw']),
            mm(CFG['screw_hole_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_mh, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_mcb = offset_plane(comp, comp.xZConstructionPlane, -8.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_mcb = comp.sketches.add(pl_mcb)
    sk_mcb.name = 'Upper_Bearing_Clamp_M3_Counterbores'
    for sx_h in (-6.5, 6.5):
        sk_mcb.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_mcb, sx_h, -8.5, lay['z_cap_up_screw']),
            mm(CFG['screw_head_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_mcb, 4.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)


def build_lower_bearing_clamp(root: adsk.fusion.Component) -> None:
    """Component 3: Unified Lower GT2 Belt Clamp + Lower LM8UU Linear Bearing Rear Cap (symmetric mirror of Upper)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Lower_Bearing_Clamp'

    lay = derive_layout()
    z_bot = lay['z_bot'] + 0.2
    z_bl = lay['z_belt_lo']
    cap_w = CFG['lm8uu_len'] - 0.2   # 24.2mm (X = -12.1..+12.1)
    bx = CFG['belt_clamp_x']
    by = CFG['belt_clamp_y']

    # 1. Bearing cap core + rear vertical-screw flange (24.2mm wide)
    sk_body = comp.sketches.add(comp.yZConstructionPlane)
    sk_body.name = 'Lower_Bearing_And_Belt_Clamp_Profile'
    draw_closed_poly(sk_body, [
        (0.0, -18.5, z_bl - 0.5),
        (0.0,  -3.8, z_bl - 0.5),
        (0.0,  -3.8, z_bl - 2.0),
        (0.0,   0.0, z_bl - 2.0),
        (0.0,   0.0, z_bot),
        (0.0, -10.5, z_bot),
        (0.0, -10.5, z_bl - 6.5),
        (0.0, -18.5, z_bl - 6.5),
    ])
    extrude_symmetric(comp, sk_body, cap_w, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    # 1b. Forward belt-pinch bridge + outer pinch wings (44.0mm wide: X=-22.0..+22.0, Y=-10.5..+3.4)
    sk_wing = comp.sketches.add(comp.yZConstructionPlane)
    sk_wing.name = 'Lower_Belt_Pinch_Wings'
    draw_closed_poly(sk_wing, [
        (0.0, -10.5, z_bl - 0.5),
        (0.0,  -3.4, z_bl - 0.5),
        (0.0,  -3.4, z_bl - 0.3),
        (0.0,   3.4, z_bl - 0.3),
        (0.0,   3.4, z_bl - 2.0),
        (0.0, -10.5, z_bl - 2.0),
    ])
    extrude_symmetric(comp, sk_wing, 44.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 2. Cut center excess-belt exit relief above the bridge (X = -3.7..+3.7)
    sk_rel = comp.sketches.add(comp.yZConstructionPlane)
    sk_rel.name = 'Lower_Center_Excess_Belt_Exit_Relief'
    draw_closed_poly(sk_rel, [
        (0.0, -19.0, z_bl + 0.2),
        (0.0,  -3.4, z_bl + 0.2),
        (0.0,  -3.4, z_bl - 1.1),
        (0.0, -19.0, z_bl - 1.1),
    ])
    extrude_symmetric(comp, sk_rel, 7.4, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 3. Cut 2x vertical M3 belt-clamp holes + bottom counterbores (X = +/-8.0, Y = -13.8)
    z_hole_mid = z_bl - 3.5
    pl_hole = offset_plane(comp, comp.xYConstructionPlane, z_hole_mid, adsk.core.Vector3D.create(0, 0, 1))
    sk_hole = comp.sketches.add(pl_hole)
    sk_hole.name = 'Lower_Belt_Clamp_M3_Vertical_Holes'
    for sx_h in (-bx, bx):
        sk_hole.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hole, sx_h, by, z_hole_mid), mm(1.8))
    extrude_symmetric(comp, sk_hole, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    z_cb_mid = z_bl - 5.2
    pl_cb = offset_plane(comp, comp.xYConstructionPlane, z_cb_mid, adsk.core.Vector3D.create(0, 0, 1))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Lower_Belt_Clamp_M3_Bottom_Counterbores'
    for sx_h in (-bx, bx):
        sk_cb.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_cb, sx_h, by, z_cb_mid),
            mm(CFG['screw_head_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_cb, 3.6, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    # 4. Cut Lower LM8UU semicircular rear bearing seat (centered at Y=0.0, Z=0.0)
    sk_bore = comp.sketches.add(comp.yZConstructionPlane)
    sk_bore.name = 'Lower_LM8UU_Rear_Half_Bore'
    sk_bore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bore, 0.0, 0.0, 0.0), mm(CFG['lm8uu_od'] / 2.0))
    extrude_symmetric(comp, sk_bore, cap_w + 1.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # 5. Cut 2x bottom horizontal M3 clamping holes + counterbores (X=+/-6.5, Z=-12.0, M3x16)
    pl_mh = offset_plane(comp, comp.xZConstructionPlane, -5.25, adsk.core.Vector3D.create(0, 1, 0))
    sk_mh = comp.sketches.add(pl_mh)
    sk_mh.name = 'Lower_Bearing_Clamp_Bottom_M3_Holes'
    for sx_h in (-6.5, 6.5):
        sk_mh.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_mh, sx_h, -5.25, lay['z_cap_lo_screw']),
            mm(CFG['screw_hole_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_mh, 12.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_mcb = offset_plane(comp, comp.xZConstructionPlane, -8.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_mcb = comp.sketches.add(pl_mcb)
    sk_mcb.name = 'Lower_Bearing_Clamp_Bottom_M3_Counterbores'
    for sx_h in (-6.5, 6.5):
        sk_mcb.sketchCurves.sketchCircles.addByCenterRadius(
            wpt(sk_mcb, sx_h, -8.5, lay['z_cap_lo_screw']),
            mm(CFG['screw_head_dia'] / 2.0),
        )
    extrude_symmetric(comp, sk_mcb, 4.4, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)


def build_universal_flex_syringe_mount(root: adsk.fusion.Component) -> None:
    """Component 4: Flat-back screw-mounted syringe holder (holes at X=+/-16.5, Z=6.5 & 26.5)."""
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.activate()
    comp = occ.component
    comp.name = 'PnP_Universal_Flex_Syringe_Mount'

    pl_mid = offset_plane(comp, comp.xYConstructionPlane, 20.0, adsk.core.Vector3D.create(0, 0, 1))
    sk_body = comp.sketches.add(pl_mid)
    sk_body.name = 'Flat_Base_And_VCradle_Body'
    draw_closed_poly(sk_body, [
        (-22.0, 13.5, 20.0),
        ( 22.0, 13.5, 20.0),
        ( 22.0, 21.5, 20.0),
        (  8.0, 21.5, 20.0),
        (  0.0, 17.0, 20.0),
        ( -8.0, 21.5, 20.0),
        (-22.0, 21.5, 20.0),
    ])
    extrude_symmetric(comp, sk_body, 50.0, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']

    pl_hole = offset_plane(comp, comp.xZConstructionPlane, 17.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_holes = comp.sketches.add(pl_hole)
    sk_holes.name = 'Syringe_Mount_M3_Holes'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_holes.sketchCurves.sketchCircles.addByCenterRadius(
                wpt(sk_holes, sx_h, 17.5, sz_h),
                mm(CFG['screw_hole_dia'] / 2.0),
            )
    extrude_symmetric(comp, sk_holes, 10.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xZConstructionPlane, 19.8, adsk.core.Vector3D.create(0, 1, 0))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Syringe_Mount_M3_Counterbores'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_cb.sketchCurves.sketchCircles.addByCenterRadius(
                wpt(sk_cb, sx_h, 19.8, sz_h),
                mm(CFG['screw_head_dia'] / 2.0),
            )
    extrude_symmetric(comp, sk_cb, 3.8, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    for tag, z_jaw in (('Lower', 14.0), ('Upper', 34.0)):
        pl_jaw = offset_plane(comp, comp.xYConstructionPlane, z_jaw, adsk.core.Vector3D.create(0, 0, 1))
        sk_jaw = comp.sketches.add(pl_jaw)
        sk_jaw.name = f'Compliant_Syringe_Jaws_{tag}'

        left_arm = [
            (-21.7, 13.5, z_jaw),
            (-21.7, 15.5, z_jaw),
            (-23.5, 15.5, z_jaw),
            (-23.5, 29.0, z_jaw),
            (-15.5, 30.3, z_jaw),
            ( -8.8, 26.5, z_jaw),
            ( -5.2, 24.3, z_jaw),
            ( -4.0, 27.0, z_jaw),
            ( -4.6, 31.7, z_jaw),
            ( -7.2, 38.5, z_jaw),
            ( -9.5, 40.0, z_jaw),
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
    pl_hose = offset_plane(comp, comp.xYConstructionPlane, 42.25, adsk.core.Vector3D.create(0, 0, 1))

    sk_hose_bridge = comp.sketches.add(pl_hose)
    sk_hose_bridge.name = 'Vacuum_Hose_Clip_Bridge'
    draw_closed_poly(sk_hose_bridge, [
        (21.5, 13.5, 42.25),
        (hose_x, 13.5, 42.25),
        (hose_x, 21.5, 42.25),
        (21.5, 21.5, 42.25),
    ])
    extrude_symmetric(comp, sk_hose_bridge, 5.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_hose_b = comp.sketches.add(pl_hose)
    sk_hose_b.name = 'Vacuum_Hose_Clip_Boss'
    sk_hose_b.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hose_b, hose_x, hose_y, 42.25), mm(5.6))
    extrude_symmetric(comp, sk_hose_b, 5.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_hose_c = comp.sketches.add(pl_hose)
    sk_hose_c.name = 'Vacuum_Hose_Clip_Bore'
    sk_hose_c.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_hose_c, hose_x, hose_y, 42.25), mm(3.1))
    extrude_symmetric(comp, sk_hose_c, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    sk_hose_s = comp.sketches.add(pl_hose)
    sk_hose_s.name = 'Vacuum_Hose_Clip_Open_Slot'
    draw_closed_poly(sk_hose_s, [
        (hose_x - 2.1, hose_y, 42.25),
        (hose_x + 2.1, hose_y, 42.25),
        (hose_x + 2.1, hose_y + 7.0, 42.25),
        (hose_x - 2.1, hose_y + 7.0, 42.25),
    ])
    extrude_symmetric(comp, sk_hose_s, 8.0, adsk.fusion.FeatureOperations.CutFeatureOperation)


def build_sized_syringe_mount(root: adsk.fusion.Component) -> None:
    """Component 5: Flat-back screw-mounted snap cradle (holes at X=+/-16.5, Z=6.5 & 26.5, placed at X=+95mm)."""
    mat = adsk.core.Matrix3D.create()
    mat.translation = adsk.core.Vector3D.create(mm(95.0), 0.0, 0.0)
    occ = root.occurrences.addNewComponent(mat)
    occ.activate()
    comp = occ.component
    comp.name = f'PnP_Sized_Syringe_Mount_{CFG["syringe_od"]}mm'

    r_in = (CFG['syringe_od'] + 0.2) / 2.0
    r_out = r_in + 4.0
    y_cyl = 20.0 + r_in

    pl_mid = offset_plane(comp, comp.xYConstructionPlane, 20.0, adsk.core.Vector3D.create(0, 0, 1))
    sk_base = comp.sketches.add(pl_mid)
    sk_base.name = 'Flat_Mounting_Plate'
    draw_closed_poly(sk_base, [
        (-22.0, 13.5, 20.0),
        ( 22.0, 13.5, 20.0),
        ( 22.0, 21.0, 20.0),
        (-22.0, 21.0, 20.0),
    ])
    extrude_symmetric(comp, sk_base, 50.0, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

    mx = CFG['mount_screw_x']
    mz_lo = CFG['mount_screw_z_lo']
    mz_hi = CFG['mount_screw_z_hi']

    pl_hole = offset_plane(comp, comp.xZConstructionPlane, 17.25, adsk.core.Vector3D.create(0, 1, 0))
    sk_holes = comp.sketches.add(pl_hole)
    sk_holes.name = 'Syringe_Mount_M3_Holes'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_holes.sketchCurves.sketchCircles.addByCenterRadius(
                wpt(sk_holes, sx_h, 17.25, sz_h),
                mm(CFG['screw_hole_dia'] / 2.0),
            )
    extrude_symmetric(comp, sk_holes, 10.0, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    pl_cb = offset_plane(comp, comp.xZConstructionPlane, 19.5, adsk.core.Vector3D.create(0, 1, 0))
    sk_cb = comp.sketches.add(pl_cb)
    sk_cb.name = 'Syringe_Mount_M3_Counterbores'
    for sx_h in (-mx, mx):
        for sz_h in (mz_lo, mz_hi):
            sk_cb.sketchCurves.sketchCircles.addByCenterRadius(
                wpt(sk_cb, sx_h, 19.5, sz_h),
                mm(CFG['screw_head_dia'] / 2.0),
            )
    extrude_symmetric(comp, sk_cb, 3.6, adsk.fusion.FeatureOperations.CutFeatureOperation, all_profiles=True)

    sk_cyl = comp.sketches.add(pl_mid)
    sk_cyl.name = 'Syringe_Cradle_Boss'
    sk_cyl.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_cyl, 0.0, y_cyl, 20.0), mm(r_out))
    extrude_symmetric(comp, sk_cyl, 44.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_bore = comp.sketches.add(pl_mid)
    sk_bore.name = 'Syringe_Cradle_Bore'
    sk_bore.sketchCurves.sketchCircles.addByCenterRadius(wpt(sk_bore, 0.0, y_cyl, 20.0), mm(r_in))
    extrude_symmetric(comp, sk_bore, 48.0, adsk.fusion.FeatureOperations.CutFeatureOperation)

    half_open = 0.425 * CFG['syringe_od']
    half_flare = 0.58 * CFG['syringe_od']
    sk_open = comp.sketches.add(pl_mid)
    sk_open.name = 'Syringe_Snap_Throat'
    draw_closed_poly(sk_open, [
        (-half_open, y_cyl, 20.0),
        ( half_open, y_cyl, 20.0),
        ( half_flare, y_cyl + r_out + 2.0, 20.0),
        (-half_flare, y_cyl + r_out + 2.0, 20.0),
    ])
    extrude_symmetric(comp, sk_open, 48.0, adsk.fusion.FeatureOperations.CutFeatureOperation)


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

    add_cyl('Clamping_Barrel', 17.0, 56.0, r_barrel, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    add_cyl('Luer_Tip_Nose', -16.0, 10.0, 3.4, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Axial_Stop_Collar', 46.75, 3.5, 5.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Vacuum_Hose_Stem', 54.5, 12.0, 2.25, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Vacuum_Hose_Barb_Ring', 56.0, 3.0, 2.65, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    add_cyl('Internal_Vacuum_Airway', 19.75, 83.5, 1.1, adsk.fusion.FeatureOperations.CutFeatureOperation)
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
                'Created Prusa MINI PnP Head (Symmetric Toothed Upper & Lower Belt Clamps) in a new file:\n\n'
                f'1. PnP_Carriage_Base (rod_spacing={CFG["rod_spacing"]}mm, belt_spacing={CFG["belt_spacing"]}mm, Y_belt=0.0; '
                f'full-circle rod bores; 12 GT2 teeth upper & lower; cap nut holes at X=+/-6.5; M12 CHE12 sensor)\n'
                '2. PnP_Upper_Belt_Bearing_Clamp (unified Y=0 belt pinch wings + upper LM8UU cap)\n'
                '3. PnP_Lower_Bearing_Clamp (unified Y=0 belt pinch wings + lower LM8UU cap)\n'
                '4. PnP_Universal_Flex_Syringe_Mount (X=+/-16.5, Z=6.5 & 26.5)\n'
                '5. PnP_Sized_Syringe_Mount (X=+/-16.5, Z=6.5 & 26.5)\n'
                '6. PnP_Vacuum_Nozzle_Adapter'
            )

    except Exception:
        if ui:
            ui.messageBox('Script Failed:\n{}'.format(traceback.format_exc()))