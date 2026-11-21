# Author: Parametric CAD Generator for Wall-Mountable External NUOXI EC-C100 + MG90S Autofocus (v4)
# Description: Creates a new Fusion 360 document and builds:
#   1. Reference_NUOXI_EC_C100   (56 x 36 mm webcam mockup, hide before STL export)
#   2. Reference_MG90S_Servo     (MG90S servo mockup, hide before STL export)
#   3. External_Autofocus_Mount  (support-free 4 mm collar, 10.5 mm servo tower, 4x M3 clamps, 4x M4 wall ears, VL53L0X pod)
#   4. Wall_Standoff_Adapter     (15 mm rear wall-clearance riser with matching 4x M4 holes)
#   5. Focus_Ring_Gear_Z26       (28 mm OD x 5.5 mm gear with 5.5 mm hub + 2x M3 radial set-screws at Z = +2.6 mm)
#   6. Servo_Drive_Gear_Z30      (32 mm OD x 5.5 mm gear with reinforced MG90S double-arm horn pocket)

import adsk.core
import adsk.fusion
import traceback
import math

MM = 0.1  # Fusion 360 internal API unit is cm (1 mm = 0.1 cm)


def pt(x_mm: float, y_mm: float, z_mm: float = 0.0) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(x_mm * MM, y_mm * MM, z_mm * MM)


def draw_circle(sketch: adsk.fusion.Sketch, cx_mm: float, cy_mm: float, r_mm: float):
    return sketch.sketchCurves.sketchCircles.addByCenterRadius(pt(cx_mm, cy_mm), r_mm * MM)


def add_user_param(design: adsk.fusion.Design, name: str, val_mm: float, unit: str = 'mm', comment: str = ''):
    try:
        vi = adsk.core.ValueInput.createByReal(val_mm) if unit == '' else adsk.core.ValueInput.createByString(f'{val_mm} {unit}')
        design.userParameters.add(name, vi, unit, comment)
    except Exception:
        pass


def create_component(root_comp: adsk.fusion.Component, name: str, tx_mm: float = 0.0, ty_mm: float = 0.0, tz_mm: float = 0.0):
    transform = adsk.core.Matrix3D.create()
    if tx_mm != 0.0 or ty_mm != 0.0 or tz_mm != 0.0:
        transform.translation = adsk.core.Vector3D.create(tx_mm * MM, ty_mm * MM, tz_mm * MM)
    occ = root_comp.occurrences.addNewComponent(transform)
    occ.activate()
    comp = occ.component
    comp.name = name
    return occ, comp


def offset_xy_plane(comp: adsk.fusion.Component, z_mm: float):
    base = comp.xYConstructionPlane
    if abs(z_mm) < 1e-6:
        return base
    sign = 1.0 if base.geometry.normal.z >= 0 else -1.0
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(base, adsk.core.ValueInput.createByReal(sign * z_mm * MM))
    return planes.add(plane_input)


def offset_xz_plane(comp: adsk.fusion.Component, y_mm: float):
    base = comp.xZConstructionPlane
    if abs(y_mm) < 1e-6:
        return base
    sign = 1.0 if base.geometry.normal.y >= 0 else -1.0
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(base, adsk.core.ValueInput.createByReal(sign * y_mm * MM))
    return planes.add(plane_input)


def offset_yz_plane(comp: adsk.fusion.Component, x_mm: float):
    base = comp.yZConstructionPlane
    if abs(x_mm) < 1e-6:
        return base
    sign = 1.0 if base.geometry.normal.x >= 0 else -1.0
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(base, adsk.core.ValueInput.createByReal(sign * x_mm * MM))
    return planes.add(plane_input)


def draw_rect(sketch: adsk.fusion.Sketch, x_min: float, y_min: float, x_max: float, y_max: float):
    return sketch.sketchCurves.sketchLines.addTwoPointRectangle(pt(x_min, y_min, 0.0), pt(x_max, y_max, 0.0))


def draw_rounded_rect(sketch: adsk.fusion.Sketch, cx: float, cy: float, w: float, h: float, r: float):
    r = min(r, w * 0.5 - 0.1, h * 0.5 - 0.1)
    if r <= 0.05:
        draw_rect(sketch, cx - w * 0.5, cy - h * 0.5, cx + w * 0.5, cy + h * 0.5)
        return

    hx = w * 0.5
    hy = h * 0.5
    lines = sketch.sketchCurves.sketchLines
    arcs = sketch.sketchCurves.sketchArcs

    br_arc = arcs.addByCenterStartSweep(pt(cx + hx - r, cy - hy + r), pt(cx + hx - r, cy - hy), math.pi * 0.5)
    right_line = lines.addByTwoPoints(br_arc.endSketchPoint, pt(cx + hx, cy + hy - r))
    tr_arc = arcs.addByCenterStartSweep(pt(cx + hx - r, cy + hy - r), right_line.endSketchPoint, math.pi * 0.5)
    top_line = lines.addByTwoPoints(tr_arc.endSketchPoint, pt(cx - hx + r, cy + hy))
    tl_arc = arcs.addByCenterStartSweep(pt(cx - hx + r, cy + hy - r), top_line.endSketchPoint, math.pi * 0.5)
    left_line = lines.addByTwoPoints(tl_arc.endSketchPoint, pt(cx - hx, cy - hy + r))
    bl_arc = arcs.addByCenterStartSweep(pt(cx - hx + r, cy - hy + r), left_line.endSketchPoint, math.pi * 0.5)
    lines.addByTwoPoints(bl_arc.endSketchPoint, br_arc.startSketchPoint)


def ensure_single_body(comp: adsk.fusion.Component, main_body: adsk.fusion.BRepBody = None) -> adsk.fusion.BRepBody:
    if comp.bRepBodies.count == 0:
        raise RuntimeError(f'Component "{comp.name}" has no solid bodies.')
    if main_body is None:
        main_body = comp.bRepBodies.item(0)
    if comp.bRepBodies.count == 1:
        return main_body

    tools = adsk.core.ObjectCollection.create()
    for i in range(comp.bRepBodies.count):
        b = comp.bRepBodies.item(i)
        if b != main_body:
            tools.add(b)
    if tools.count > 0:
        comb_input = comp.features.combineFeatures.createInput(main_body, tools)
        comb_input.operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        comb_input.isKeepToolBodies = False
        comp.features.combineFeatures.add(comb_input)
    return main_body


def extrude_all_profiles(
    comp: adsk.fusion.Component,
    sketch: adsk.fusion.Sketch,
    dist_mm: float,
    op: adsk.fusion.FeatureOperations,
    target_body: adsk.fusion.BRepBody = None
):
    if sketch.profiles.count == 0:
        raise RuntimeError(f'No closed profiles found in sketch "{sketch.name}".')
    if sketch.profiles.count == 1:
        profs = sketch.profiles.item(0)
    else:
        profs = adsk.core.ObjectCollection.create()
        for i in range(sketch.profiles.count):
            profs.add(sketch.profiles.item(i))

    extrudes = comp.features.extrudeFeatures
    if op != adsk.fusion.FeatureOperations.CutFeatureOperation:
        return extrudes.addSimple(profs, adsk.core.ValueInput.createByReal(dist_mm * MM), op)

    if target_body is None:
        target_body = ensure_single_body(comp)

    tool_ext = extrudes.addSimple(
        profs,
        adsk.core.ValueInput.createByReal(dist_mm * MM),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    )
    tools = adsk.core.ObjectCollection.create()
    for i in range(tool_ext.bodies.count):
        b = tool_ext.bodies.item(i)
        if b != target_body:
            tools.add(b)
    if tools.count == 0:
        raise RuntimeError(f'Tool body creation failed for cut "{sketch.name}".')

    comb_input = comp.features.combineFeatures.createInput(target_body, tools)
    comb_input.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
    comb_input.isKeepToolBodies = False
    return comp.features.combineFeatures.add(comb_input)


def set_component_color(app: adsk.core.Application, design: adsk.fusion.Design, comp: adsk.fusion.Component, name: str, r: int, g: int, b: int):
    try:
        lib = app.materialLibraries.itemByName('Fusion Appearance Library')
        if not lib:
            lib = app.materialLibraries.itemByName('Fusion 360 Appearance Library')
        if not lib:
            return
        base_app = None
        for candidate in ('Plastic - Matte (Gray)', 'Paint - Enamel Glossy (Yellow)', 'Plastic - Matte (Yellow)'):
            base_app = lib.appearances.itemByName(candidate)
            if base_app:
                break
        if not base_app and lib.appearances.count > 0:
            base_app = lib.appearances.item(0)
        if not base_app:
            return

        new_app = design.appearances.itemByName(name)
        if not new_app:
            new_app = design.appearances.addByCopy(base_app, name)
        color_prop = adsk.core.ColorProperty.cast(new_app.appearanceProperties.itemByName('Color'))
        if color_prop:
            color_prop.value = adsk.core.Color.create(r, g, b, 255)
        for body in comp.bRepBodies:
            body.appearance = new_app
    except Exception:
        pass


def build_involute_gear_base(
    comp: adsk.fusion.Component,
    module_mm: float,
    num_teeth: int,
    pressure_deg: float,
    backlash_mm: float,
    thickness_mm: float,
    z_start_mm: float,
    rot_offset_deg: float = 0.0,
    body_name: str = 'Gear'
) -> adsk.fusion.BRepBody:
    alpha = math.radians(pressure_deg)
    rp = module_mm * num_teeth * 0.5
    rb = rp * math.cos(alpha)
    ra = rp + module_mm
    rf = rp - 1.25 * module_mm

    root_plane = offset_xy_plane(comp, z_start_mm)
    root_sk = comp.sketches.add(root_plane)
    root_sk.name = f'{body_name}_Root'
    draw_circle(root_sk, 0.0, 0.0, rf)
    root_ext = extrude_all_profiles(comp, root_sk, thickness_mm, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    main_body = root_ext.bodies.item(0)
    main_body.name = body_name

    tooth_sk = comp.sketches.add(root_plane)
    tooth_sk.name = f'{body_name}_Tooth'
    tooth_sk.isComputeDeferred = True

    sp = (math.pi * module_mm * 0.5) - backlash_mm
    psi_p = sp / (2.0 * rp)
    inv_alpha = math.tan(alpha) - alpha
    gamma = psi_p + inv_alpha

    rot_offset = math.radians(rot_offset_deg)
    r_start = max(rb, rf)
    r_overlap = rf - 0.6
    n_pts = 8

    bot_pts = adsk.core.ObjectCollection.create()
    top_pts = adsk.core.ObjectCollection.create()
    ang_bot_start = rot_offset - gamma
    ang_top_start = rot_offset + gamma

    for i in range(n_pts):
        r = r_start + (ra - r_start) * (i / (n_pts - 1))
        cos_val = min(1.0, max(-1.0, rb / r))
        phi = math.acos(cos_val)
        theta = math.tan(phi) - phi
        ang_b = rot_offset - gamma + theta
        ang_t = rot_offset + gamma - theta
        if i == 0:
            ang_bot_start = ang_b
            ang_top_start = ang_t
        bot_pts.add(pt(r * math.cos(ang_b), r * math.sin(ang_b)))
        top_pts.add(pt(r * math.cos(ang_t), r * math.sin(ang_t)))

    splines = tooth_sk.sketchCurves.sketchFittedSplines
    lines = tooth_sk.sketchCurves.sketchLines
    arcs = tooth_sk.sketchCurves.sketchArcs

    sp_bot = splines.add(bot_pts)
    sp_top = splines.add(top_pts)

    p_in_bot = pt(r_overlap * math.cos(ang_bot_start), r_overlap * math.sin(ang_bot_start))
    p_in_top = pt(r_overlap * math.cos(ang_top_start), r_overlap * math.sin(ang_top_start))
    l_bot = lines.addByTwoPoints(p_in_bot, sp_bot.startSketchPoint)
    l_top = lines.addByTwoPoints(p_in_top, sp_top.startSketchPoint)
    lines.addByTwoPoints(l_bot.startSketchPoint, l_top.startSketchPoint)

    mid_tip = pt(ra * math.cos(rot_offset), ra * math.sin(rot_offset))
    try:
        arcs.addByThreePoints(sp_bot.endSketchPoint, mid_tip, sp_top.endSketchPoint)
    except Exception:
        lines.addByTwoPoints(sp_bot.endSketchPoint, sp_top.endSketchPoint)

    tooth_sk.isComputeDeferred = False
    tooth_ext = extrude_all_profiles(comp, tooth_sk, thickness_mm, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    circ_patterns = comp.features.circularPatternFeatures
    entities = adsk.core.ObjectCollection.create()
    entities.add(tooth_ext)
    pat_input = circ_patterns.createInput(entities, comp.zConstructionAxis)
    pat_input.quantity = adsk.core.ValueInput.createByString(str(num_teeth))
    pat_input.totalAngle = adsk.core.ValueInput.createByString('360 deg')
    pat_input.isSymmetric = False
    try:
        pat_input.patternComputeOption = adsk.fusion.PatternComputeOptions.IdenticalPatternCompute
    except Exception:
        pass
    circ_patterns.add(pat_input)

    return ensure_single_body(comp, main_body)


def build_webcam_reference(root_comp: adsk.fusion.Component, app, design, p: dict):
    _, comp = create_component(root_comp, 'Reference_NUOXI_EC_C100')

    sk_body = comp.sketches.add(offset_xy_plane(comp, -p['cam_d']))
    sk_body.name = 'Webcam_Body'
    draw_rounded_rect(sk_body, 0.0, 0.0, p['cam_w'], p['cam_h'], p['cam_corner_r'])
    ext_body = extrude_all_profiles(comp, sk_body, p['cam_d'], adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    cam_body = ext_body.bodies.item(0)
    cam_body.name = 'NUOXI_Body'

    sk_bezel = comp.sketches.add(comp.xYConstructionPlane)
    sk_bezel.name = 'Webcam_Front_Bezel'
    draw_circle(sk_bezel, p['lens_x'], p['lens_y'], 12.0)
    draw_circle(sk_bezel, 15.0, 0.0, 5.0)
    extrude_all_profiles(comp, sk_bezel, 1.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_focus = comp.sketches.add(offset_xy_plane(comp, 1.0))
    sk_focus.name = 'Webcam_Focus_Ring'
    draw_circle(sk_focus, p['lens_x'], p['lens_y'], p['focus_ring_dia'] * 0.5)
    extrude_all_profiles(comp, sk_focus, p['focus_ring_depth'] - 1.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_leds = comp.sketches.add(comp.xYConstructionPlane)
    sk_leds.name = 'Webcam_3_LEDs'
    for ly in (-5.5, 0.0, 5.5):
        draw_circle(sk_leds, -24.5, ly, 1.3)
    extrude_all_profiles(comp, sk_leds, 0.4, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_neck = comp.sketches.add(offset_xz_plane(comp, -p['cam_h'] * 0.5))
    sk_neck.name = 'Webcam_Swivel_Neck'
    c_neck = sk_neck.modelToSketchSpace(pt(0.0, -p['cam_h'] * 0.5, -p['cam_d'] * 0.5))
    sk_neck.sketchCurves.sketchCircles.addByCenterRadius(c_neck, 7.0 * MM)
    normal = sk_neck.xDirection.crossProduct(sk_neck.yDirection)
    neck_dist = -8.0 if normal.y > 0 else 8.0
    extrude_all_profiles(comp, sk_neck, neck_dist, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    cam_body = ensure_single_body(comp, cam_body)

    sk_glass = comp.sketches.add(offset_xy_plane(comp, p['focus_ring_depth'] + 0.5))
    sk_glass.name = 'Webcam_Lens_Opening'
    draw_circle(sk_glass, p['lens_x'], p['lens_y'], 5.0)
    extrude_all_profiles(comp, sk_glass, -3.0, adsk.fusion.FeatureOperations.CutFeatureOperation, cam_body)

    set_component_color(app, design, comp, 'Webcam_Gray', 75, 80, 88)


def build_servo_reference(root_comp: adsk.fusion.Component, app, design, p: dict):
    _, comp = create_component(root_comp, 'Reference_MG90S_Servo')
    bx = p['servo_body_cx']
    by = p['servo_shaft_y']
    fz = p['servo_flange_z_front']

    sk_body = comp.sketches.add(offset_xy_plane(comp, fz - 18.5))
    sk_body.name = 'MG90S_Body'
    draw_rect(
        sk_body,
        bx - p['servo_body_l'] * 0.5,
        by - p['servo_body_w'] * 0.5,
        bx + p['servo_body_l'] * 0.5,
        by + p['servo_body_w'] * 0.5
    )
    ext = extrude_all_profiles(comp, sk_body, 28.4, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    servo_body = ext.bodies.item(0)
    servo_body.name = 'MG90S_Body'

    sk_flange = comp.sketches.add(offset_xy_plane(comp, fz))
    sk_flange.name = 'MG90S_Flange'
    draw_rect(
        sk_flange,
        bx - p['servo_flange_l'] * 0.5,
        by - p['servo_body_w'] * 0.5,
        bx + p['servo_flange_l'] * 0.5,
        by + p['servo_body_w'] * 0.5
    )
    extrude_all_profiles(comp, sk_flange, 2.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_shaft = comp.sketches.add(offset_xy_plane(comp, fz + 9.9))
    sk_shaft.name = 'MG90S_Spline_Shaft'
    draw_circle(sk_shaft, p['servo_shaft_x'], p['servo_shaft_y'], 2.45)
    extrude_all_profiles(comp, sk_shaft, 3.7, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    servo_body = ensure_single_body(comp, servo_body)

    sk_holes = comp.sketches.add(offset_xy_plane(comp, fz + 3.0))
    sk_holes.name = 'MG90S_Flange_Holes'
    for hx in (bx - p['servo_hole_span'] * 0.5, bx + p['servo_hole_span'] * 0.5):
        draw_circle(sk_holes, hx, by, 1.1)
    extrude_all_profiles(comp, sk_holes, -3.5, adsk.fusion.FeatureOperations.CutFeatureOperation, servo_body)

    set_component_color(app, design, comp, 'Servo_Dark_Blue', 30, 50, 85)


def build_external_autofocus_mount(root_comp: adsk.fusion.Component, app, design, p: dict):
    _, comp = create_component(root_comp, 'External_Autofocus_Mount')

    inner_w = p['cam_w'] + 2.0 * p['cam_tol']       # 56.6 mm
    inner_h = p['cam_h'] + 2.0 * p['cam_tol']       # 36.6 mm
    outer_w = inner_w + 2.0 * p['wall']             # 64.6 mm (X = -32.3 .. +32.3)
    y_min_outer = -(inner_h * 0.5 + p['wall'])      # -22.3 mm
    servo_slot_h = p['servo_body_w'] + p['servo_tol']
    servo_slot_y_min = p['servo_shaft_y'] - servo_slot_h * 0.5   # +21.7 mm
    servo_slot_y_max = p['servo_shaft_y'] + servo_slot_h * 0.5   # +34.3 mm
    cradle_y_max = servo_slot_y_min
    cradle_h = cradle_y_max - y_min_outer
    cradle_cy = (cradle_y_max + y_min_outer) * 0.5
    z_back = -p['clip_depth']                       # -15.0 mm (100% flat bed base)

    # 1. Open-back external collar (Z = -15.0 mm to 0.0 mm)
    sk_collar = comp.sketches.add(offset_xy_plane(comp, z_back))
    sk_collar.name = 'Clip_Collar_Outer'
    draw_rounded_rect(sk_collar, 0.0, cradle_cy, outer_w, cradle_h, 5.0)
    ext_collar = extrude_all_profiles(comp, sk_collar, abs(z_back), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    mount_body = ext_collar.bodies.item(0)
    mount_body.name = 'External_Autofocus_Mount_Body'

    # 2. Front retaining tabs (1.2 mm overlap on flat side edges; clear of 3 LEDs & Focus Gear)
    sk_lips = comp.sketches.add(comp.xYConstructionPlane)
    sk_lips.name = 'Clip_Front_Retaining_Lips'
    draw_rect(sk_lips, inner_w * 0.5 - 1.2, -12.0, outer_w * 0.5, 12.0)       # Right lip
    draw_rect(sk_lips, -outer_w * 0.5, 9.5, -inner_w * 0.5 + 1.2, 17.5)       # Top-left tab
    draw_rect(sk_lips, -outer_w * 0.5, -17.5, -inner_w * 0.5 + 1.2, -9.5)     # Bottom-left tab
    extrude_all_profiles(comp, sk_lips, 1.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 3. Support-free clamping screw pads starting flush at build plate Z = -15.0 to -2.0 mm (6.2 mm wall thickness)
    sk_pads = comp.sketches.add(offset_xy_plane(comp, z_back))
    sk_pads.name = 'External_Clamp_Screw_Pads'
    draw_rounded_rect(sk_pads, -32.2, 0.0, 4.6, 23.0, 1.8)     # Left wall M3 pad (Y = -11.5..+11.5)
    draw_rounded_rect(sk_pads, -20.0, -22.2, 9.0, 4.6, 1.8)    # Bottom-left M3 pad
    draw_rounded_rect(sk_pads, 20.0, -22.2, 9.0, 4.6, 1.8)     # Bottom-right M3 pad
    extrude_all_profiles(comp, sk_pads, 13.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 4. Beefed-up Top MG90S Servo Tower (10.5 mm thick: Z = -15.0 to -4.5 mm)
    bx = p['servo_body_cx']
    tower_x_min = bx - 20.4
    tower_x_max = outer_w * 0.5
    tower_y_min = cradle_y_max - 2.4
    tower_y_max = servo_slot_y_max + 4.7
    tower_w = tower_x_max - tower_x_min
    tower_h = tower_y_max - tower_y_min
    tower_cx = (tower_x_min + tower_x_max) * 0.5
    tower_cy = (tower_y_min + tower_y_max) * 0.5
    tower_depth = p['servo_flange_z_front'] - z_back  # 10.5 mm

    sk_tower = comp.sketches.add(offset_xy_plane(comp, z_back))
    sk_tower.name = 'Thick_Servo_Tower_And_MCU_Block'
    draw_rounded_rect(sk_tower, tower_cx, tower_cy, tower_w, tower_h, 2.5)
    extrude_all_profiles(comp, sk_tower, tower_depth, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 5. External VL53L0X ToF laser sensor pod on right wall (16 mm wide -> fits 10.7 mm & 12.5 mm boards)
    pod_x_min = inner_w * 0.5 + 1.7                # +30.0 mm
    pod_x_max = pod_x_min + 16.0                   # +46.0 mm
    pod_y_min = -10.0
    pod_y_max = 17.5
    sk_pod = comp.sketches.add(offset_xy_plane(comp, z_back))
    sk_pod.name = 'External_VL53L0X_Pod'
    draw_rounded_rect(
        sk_pod,
        (pod_x_min + pod_x_max) * 0.5,
        (pod_y_min + pod_y_max) * 0.5,
        pod_x_max - pod_x_min,
        pod_y_max - pod_y_min,
        2.0
    )
    extrude_all_profiles(comp, sk_pod, abs(z_back) + 3.5, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 6. Four Wall-Mount Screw Ears (6.0 mm thick tabs flush at Z = -15.0 to -9.0 mm)
    sk_ears = comp.sketches.add(offset_xy_plane(comp, z_back))
    sk_ears.name = 'Wall_Mount_Screw_Ears'
    draw_rounded_rect(sk_ears, -38.15, 16.7, 15.7, 10.0, 2.5)   # Top-Left ear (X = -46.0..-30.3)
    draw_rounded_rect(sk_ears, -38.15, -17.3, 15.7, 10.0, 2.5)  # Bottom-Left ear (X = -46.0..-30.3)
    draw_rounded_rect(sk_ears, 38.15, 29.5, 15.7, 12.0, 2.5)    # Top-Right ear (X = +30.3..+46.0)
    draw_rounded_rect(sk_ears, 38.15, -17.3, 15.7, 10.0, 2.5)   # Bottom-Right ear (X = +30.3..+46.0)
    extrude_all_profiles(comp, sk_ears, 6.0, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    mount_body = ensure_single_body(comp, mount_body)

    # 7. Cut open-back through-pocket for the 56 x 36 mm webcam
    sk_cam_hole = comp.sketches.add(offset_xy_plane(comp, 0.5))
    sk_cam_hole.name = 'Clip_Camera_Through_Cut'
    draw_rounded_rect(sk_cam_hole, 0.0, 0.0, inner_w, inner_h, p['cam_corner_r'])
    extrude_all_profiles(comp, sk_cam_hole, -(abs(z_back) + 1.5), adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    # 8. Bottom swivel neck / spring-clip gap
    sk_bot_gap = comp.sketches.add(offset_xy_plane(comp, 0.5))
    sk_bot_gap.name = 'Clip_Bottom_Open_Slot'
    draw_rect(sk_bot_gap, -11.0, y_min_outer - 1.5, 11.0, -inner_h * 0.5 + 0.5)
    extrude_all_profiles(comp, sk_bot_gap, -(abs(z_back) + 1.5), adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    # 9. Straight-through MG90S servo slot + 2x M2 holes + 2x MCU zip-tie slots (zero internal step overhang)
    servo_slot_w = p['servo_body_l'] + p['servo_tol']
    sk_servo_cut = comp.sketches.add(offset_xy_plane(comp, p['servo_flange_z_front'] + 0.5))
    sk_servo_cut.name = 'Mount_Servo_Slot_Holes_And_MCU_Ties'
    draw_rect(sk_servo_cut, bx - servo_slot_w * 0.5, servo_slot_y_min, bx + servo_slot_w * 0.5, servo_slot_y_max)
    for hx in (bx - p['servo_hole_span'] * 0.5, bx + p['servo_hole_span'] * 0.5):
        draw_circle(sk_servo_cut, hx, p['servo_shaft_y'], 0.9)
    draw_rect(sk_servo_cut, 17.5, 32.5, 21.0, 36.0)   # MCU zip-tie slot 1
    draw_rect(sk_servo_cut, 26.5, 32.5, 30.0, 36.0)   # MCU zip-tie slot 2
    extrude_all_profiles(comp, sk_servo_cut, -(tower_depth + 1.5), adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    # 10. Front VL53L0X pocket (13.0 x 25.6 mm) + centered header-pin wire slot (7.5 x 16.5 mm) + 2x M2 holes (19.3 mm span)
    pod_cx = (pod_x_min + pod_x_max) * 0.5  # +38.0 mm
    pod_cy = (pod_y_min + pod_y_max) * 0.5  # +3.75 mm
    sk_tof_pocket = comp.sketches.add(offset_xy_plane(comp, 4.0))
    sk_tof_pocket.name = 'VL53L0X_Front_Pocket'
    draw_rect(sk_tof_pocket, pod_cx - 6.5, pod_cy - 12.8, pod_cx + 6.5, pod_cy + 12.8)
    extrude_all_profiles(comp, sk_tof_pocket, -5.5, adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    sk_tof_wire = comp.sketches.add(offset_xy_plane(comp, 0.5))
    sk_tof_wire.name = 'VL53L0X_Header_Wire_Pass_Slot'
    draw_rect(sk_tof_wire, pod_cx - 3.75, pod_cy - 8.25, pod_cx + 3.75, pod_cy + 8.25)
    extrude_all_profiles(comp, sk_tof_wire, -(abs(z_back) + 1.5), adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    sk_tof_screws = comp.sketches.add(offset_xy_plane(comp, 0.5))
    sk_tof_screws.name = 'VL53L0X_M2_Screw_Holes'
    draw_circle(sk_tof_screws, pod_cx, pod_cy + 9.65, 0.9)  # 19.3 mm standard GY-VL53L0XV2 spacing
    draw_circle(sk_tof_screws, pod_cx, pod_cy - 9.65, 0.9)
    extrude_all_profiles(comp, sk_tof_screws, -8.5, adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    # 11. Wall-Mount 4x M4 / #8 Screw Through-Holes + Screw-Head Counterbores
    wall_pts = p['wall_hole_pts']
    sk_wall_holes = comp.sketches.add(offset_xy_plane(comp, z_back + 6.5))
    sk_wall_holes.name = 'Wall_Mount_Through_Holes'
    for wx, wy in wall_pts:
        draw_circle(sk_wall_holes, wx, wy, 2.25)  # Ø 4.5 mm
    extrude_all_profiles(comp, sk_wall_holes, -7.5, adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    sk_wall_cbore = comp.sketches.add(offset_xy_plane(comp, z_back + 6.5))
    sk_wall_cbore.name = 'Wall_Mount_Counterbores'
    for wx, wy in wall_pts:
        draw_circle(sk_wall_cbore, wx, wy, 4.25)  # Ø 8.5 mm x 2.0 mm counterbore
    extrude_all_profiles(comp, sk_wall_cbore, -2.5, adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    # 12. External frame 4x M3 camera-locking screw pilot holes (2 left + 2 bottom)
    sk_left_screws = comp.sketches.add(offset_yz_plane(comp, -35.5))
    sk_left_screws.name = 'Left_M3_Clamp_Screw_Holes'
    for sy in (-8.0, 8.0):
        c_ls = sk_left_screws.modelToSketchSpace(pt(-35.5, sy, -7.5))
        sk_left_screws.sketchCurves.sketchCircles.addByCenterRadius(c_ls, 1.25 * MM)
    n_left = sk_left_screws.xDirection.crossProduct(sk_left_screws.yDirection)
    extrude_all_profiles(comp, sk_left_screws, 9.0 if n_left.x > 0 else -9.0, adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    sk_bot_screws = comp.sketches.add(offset_xz_plane(comp, -25.5))
    sk_bot_screws.name = 'Bottom_M3_Clamp_Screw_Holes'
    for sx in (-20.0, 20.0):
        c_bs = sk_bot_screws.modelToSketchSpace(pt(sx, -25.5, -7.5))
        sk_bot_screws.sketchCurves.sketchCircles.addByCenterRadius(c_bs, 1.25 * MM)
    n_bot = sk_bot_screws.xDirection.crossProduct(sk_bot_screws.yDirection)
    extrude_all_profiles(comp, sk_bot_screws, 9.0 if n_bot.y > 0 else -9.0, adsk.fusion.FeatureOperations.CutFeatureOperation, mount_body)

    set_component_color(app, design, comp, 'Mount_Teal', 0, 130, 175)


def build_wall_standoff_adapter(root_comp: adsk.fusion.Component, app, design, p: dict):
    _, comp = create_component(root_comp, 'Wall_Standoff_Adapter')

    z_mount_back = -p['clip_depth']               # -15.0 mm
    standoff_h = p['wall_standoff_depth']         # 15.0 mm (7 mm clear behind MG90S, 12 mm behind camera)
    z_wall = z_mount_back - standoff_h            # -30.0 mm

    # 1. Left & Right vertical standoff rails (X = -46.0..-32.3 and +32.3..+46.0)
    sk_rails = comp.sketches.add(offset_xy_plane(comp, z_wall))
    sk_rails.name = 'Standoff_Side_Rails'
    draw_rounded_rect(sk_rails, -39.15, 8.85, 13.7, 62.3, 2.5)
    draw_rounded_rect(sk_rails, 39.15, 8.85, 13.7, 62.3, 2.5)
    ext_rails = extrude_all_profiles(comp, sk_rails, standoff_h, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    adapter_body = ext_rails.bodies.item(0)
    adapter_body.name = 'Wall_Standoff_Adapter_Body'

    # 2. Top cross-bridge above MG90S servo tail (Y = +35.0 to +40.0)
    sk_bridge = comp.sketches.add(offset_xy_plane(comp, z_wall))
    sk_bridge.name = 'Standoff_Top_Crossbar'
    draw_rect(sk_bridge, -34.0, 35.0, 34.0, 40.0)
    extrude_all_profiles(comp, sk_bridge, standoff_h, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    adapter_body = ensure_single_body(comp, adapter_body)

    # 3. Matching 4x M4 / #8 wall-screw through-holes aligned with External_Autofocus_Mount ears
    sk_holes = comp.sketches.add(offset_xy_plane(comp, z_mount_back + 0.5))
    sk_holes.name = 'Standoff_Matching_Wall_Holes'
    for wx, wy in p['wall_hole_pts']:
        draw_circle(sk_holes, wx, wy, 2.25)
    extrude_all_profiles(comp, sk_holes, -(standoff_h + 1.0), adsk.fusion.FeatureOperations.CutFeatureOperation, adapter_body)

    set_component_color(app, design, comp, 'Adapter_Slate', 95, 115, 135)


def build_focus_ring_gear(root_comp: adsk.fusion.Component, app, design, p: dict):
    _, comp = create_component(root_comp, 'Focus_Ring_Gear_Z26', p['lens_x'], p['lens_y'], 0.0)

    gear_z0 = p['gear_z_start']   # +6.0 mm
    gear_t = p['gear_thickness']  # 5.5 mm (Z = +6.0 to +11.5 mm)
    skirt_z0 = 0.5                # clamping hub Z = +0.5 to +6.0 mm (5.5 mm tall)

    body = build_involute_gear_base(
        comp=comp,
        module_mm=p['module_m'],
        num_teeth=p['teeth_focus'],
        pressure_deg=p['pressure_deg'],
        backlash_mm=p['backlash_mm'],
        thickness_mm=gear_t,
        z_start_mm=gear_z0,
        rot_offset_deg=0.0,
        body_name='Focus_Ring_Gear_Z26'
    )

    sk_hub = comp.sketches.add(offset_xy_plane(comp, gear_z0))
    sk_hub.name = 'Focus_Gear_Clamping_Hub'
    draw_circle(sk_hub, 0.0, 0.0, 11.7)
    extrude_all_profiles(comp, sk_hub, -(gear_z0 - skirt_z0), adsk.fusion.FeatureOperations.JoinFeatureOperation)

    sk_boss = comp.sketches.add(offset_xy_plane(comp, gear_z0))
    sk_boss.name = 'Focus_Gear_M3_Screw_Bosses'
    draw_rounded_rect(sk_boss, 0.0, 0.0, 25.6, 5.8, 1.8)
    extrude_all_profiles(comp, sk_boss, -(gear_z0 - skirt_z0), adsk.fusion.FeatureOperations.JoinFeatureOperation)

    body = ensure_single_body(comp, body)

    bore_r = (p['focus_ring_dia'] + p['focus_ring_tol']) * 0.5
    sk_bore = comp.sketches.add(offset_xy_plane(comp, gear_z0 + gear_t + 0.5))
    sk_bore.name = 'Focus_Ring_Bore'
    draw_circle(sk_bore, 0.0, 0.0, bore_r)
    extrude_all_profiles(comp, sk_bore, -(gear_z0 + gear_t - skirt_z0 + 1.0), adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    sk_set_screws = comp.sketches.add(offset_yz_plane(comp, -14.5))
    sk_set_screws.name = 'Focus_Gear_2x_M3_SetScrews'
    c_screw = sk_set_screws.modelToSketchSpace(pt(-14.5, 0.0, 2.6))
    sk_set_screws.sketchCurves.sketchCircles.addByCenterRadius(c_screw, 1.25 * MM)
    n_sc = sk_set_screws.xDirection.crossProduct(sk_set_screws.yDirection)
    extrude_all_profiles(comp, sk_set_screws, 29.0 if n_sc.x > 0 else -29.0, adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    return body, comp


def build_servo_drive_gear(root_comp: adsk.fusion.Component, app, design, p: dict):
    _, comp = create_component(root_comp, 'Servo_Drive_Gear_Z30', p['servo_shaft_x'], p['servo_shaft_y'], 0.0)

    gear_z0 = p['gear_z_start']   # +6.0 mm
    gear_t = p['gear_thickness']  # 5.5 mm (Z = +6.0 to +11.5 mm)
    half_pitch_deg = 180.0 / p['teeth_servo']

    body = build_involute_gear_base(
        comp=comp,
        module_mm=p['module_m'],
        num_teeth=p['teeth_servo'],
        pressure_deg=p['pressure_deg'],
        backlash_mm=p['backlash_mm'],
        thickness_mm=gear_t,
        z_start_mm=gear_z0,
        rot_offset_deg=half_pitch_deg,
        body_name='Servo_Drive_Gear_Z30'
    )

    sk_horn = comp.sketches.add(offset_xy_plane(comp, gear_z0 - 0.5))
    sk_horn.name = 'Servo_Horn_Arm_Slot'
    draw_rounded_rect(sk_horn, 0.0, 0.0, 24.0, 4.4, 1.8)
    extrude_all_profiles(comp, sk_horn, 2.5, adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    sk_hub = comp.sketches.add(offset_xy_plane(comp, gear_z0 - 0.5))
    sk_hub.name = 'Servo_Horn_Hub_Pocket'
    draw_circle(sk_hub, 0.0, 0.0, 3.7)
    extrude_all_profiles(comp, sk_hub, 3.7, adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    sk_screw = comp.sketches.add(offset_xy_plane(comp, gear_z0 + gear_t + 0.5))
    sk_screw.name = 'Servo_Gear_Screw_Access'
    draw_circle(sk_screw, 0.0, 0.0, 2.25)
    extrude_all_profiles(comp, sk_screw, -(gear_t + 1.0), adsk.fusion.FeatureOperations.CutFeatureOperation, body)

    return body, comp


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Create a brand-new Fusion 360 document before editing
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(doc.products.itemByProductType('DesignProductType'))
        if not design:
            design = adsk.fusion.Design.cast(app.activeProduct)

        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root_comp = design.rootComponent

        module_m = 1.0
        teeth_focus = 26
        teeth_servo = 30
        center_dist = module_m * (teeth_focus + teeth_servo) * 0.5  # 28.0 mm

        p = {
            'cam_w': 56.0,
            'cam_h': 36.0,
            'cam_d': 18.0,
            'cam_corner_r': 4.5,
            'cam_tol': 0.3,
            'wall': 4.0,
            'clip_depth': 15.0,
            'wall_standoff_depth': 15.0,
            'wall_hole_pts': [
                (-39.5, 16.7),
                (-39.5, -17.3),
                (39.5, 29.5),
                (39.5, -17.3),
            ],
            'lens_x': -7.0,
            'lens_y': 0.0,
            'focus_ring_dia': 17.0,
            'focus_ring_tol': 0.2,
            'focus_ring_depth': 4.5,
            'module_m': module_m,
            'teeth_focus': teeth_focus,
            'teeth_servo': teeth_servo,
            'pressure_deg': 20.0,
            'backlash_mm': 0.08,
            'gear_z_start': 6.0,
            'gear_thickness': 8.0,
            'servo_shaft_x': -7.0,
            'servo_shaft_y': center_dist,
            'servo_body_l': 22.8,
            'servo_body_w': 12.2,
            'servo_flange_l': 32.5,
            'servo_hole_span': 27.6,
            'servo_body_cx': -7.0 + 5.4,
            'servo_tol': 0.4,
            'servo_flange_z_front': -4.5,
        }

        add_user_param(design, 'cam_width', p['cam_w'], 'mm', 'NUOXI webcam width')
        add_user_param(design, 'cam_height', p['cam_h'], 'mm', 'NUOXI webcam height')
        add_user_param(design, 'lens_offset_x', p['lens_x'], 'mm', 'Lens center X from body center')
        add_user_param(design, 'focus_ring_dia', p['focus_ring_dia'], 'mm', 'Focus ring outer diameter')
        add_user_param(design, 'gear_center_dist', center_dist, 'mm', 'Lens-to-servo center distance')
        add_user_param(design, 'wall_standoff_depth', p['wall_standoff_depth'], 'mm', 'Rear wall spacer height')

        build_webcam_reference(root_comp, app, design, p)
        build_servo_reference(root_comp, app, design, p)
        build_external_autofocus_mount(root_comp, app, design, p)
        build_wall_standoff_adapter(root_comp, app, design, p)

        _, focus_comp = build_focus_ring_gear(root_comp, app, design, p)
        set_component_color(app, design, focus_comp, 'Gear_Green', 55, 175, 95)

        _, servo_gear_comp = build_servo_drive_gear(root_comp, app, design, p)
        set_component_color(app, design, servo_gear_comp, 'Gear_Orange', 235, 115, 35)

        try:
            design.activateRootComponent()
        except Exception:
            pass

        if app.activeViewport:
            app.activeViewport.fit()

        print(
            'SUCCESS: Created v4 support-free wall-mountable NUOXI + MG90S Autofocus Assembly.'
        )

    except Exception:
        err = traceback.format_exc()
        print('FAILED:\n' + err)
        if ui:
            ui.messageBox('Failed:\n{}'.format(err))