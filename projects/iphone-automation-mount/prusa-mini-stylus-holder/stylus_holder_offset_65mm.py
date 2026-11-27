"""
Standalone Rebuild Script for: ai stylus holder (Prusa Mini Heatsink Mod)
Relocates the stylus holder feature +65 mm along the positive X-axis while
maintaining fixed mounting hole positions at (16, 16) and (-16, -16), extending
the base plate continuously into a robust cantilever arm.
"""
import adsk.core
import adsk.fusion
import traceback
import math

# Compatibility aliases
true = True
false = False
null = None

# ==============================================================================
# RUNTIME HELPER UTILITIES
# ==============================================================================
def pt(x_mm, y_mm, z_mm=0.0):
    """Fusion 360 internal database unit is centimeters (1 cm = 10 mm)."""
    return adsk.core.Point3D.create(x_mm * 0.1, y_mm * 0.1, z_mm * 0.1)


def get_token(entity):
    try:
        return entity.entityToken
    except:
        return None


def resolve_canonical_plane(root_comp, plane_name):
    name = (plane_name or "").upper()
    if "YZ" in name:
        return root_comp.yZConstructionPlane
    elif "XZ" in name:
        return root_comp.xZConstructionPlane
    return root_comp.xYConstructionPlane


def find_matching_face(root_comp, plane_info):
    if root_comp.bRepBodies.count == 0 or not plane_info:
        return None
    if plane_info.get("type") != "FACE" or "normal" not in plane_info or "origin" not in plane_info:
        return None

    tn = plane_info["normal"]
    to = plane_info["origin"]
    best_face = None
    best_dist = 1e9

    for body in root_comp.bRepBodies:
        for face in body.faces:
            try:
                pln = face.geometry
                if not hasattr(pln, "normal"):
                    continue
                fn = pln.normal
                dot = fn.x * tn["x"] + fn.y * tn["y"] + fn.z * tn["z"]
                if abs(abs(dot) - 1.0) < 1e-3:
                    dist_cm = abs(
                        (to["x"] * 0.1 - pln.origin.x) * fn.x +
                        (to["y"] * 0.1 - pln.origin.y) * fn.y +
                        (to["z"] * 0.1 - pln.origin.z) * fn.z
                    )
                    dist_mm = dist_cm * 10.0
                    if dist_mm < 0.2 and dist_mm < best_dist:
                        best_dist = dist_mm
                        best_face = face
            except:
                pass
    return best_face


def curve_matches(c_desc, ec):
    c_type = c_desc.get("type")
    try:
        if c_type == "line" and hasattr(ec, "startSketchPoint"):
            p1 = ec.startSketchPoint.geometry
            p2 = ec.endSketchPoint.geometry
            s, e = c_desc["start"], c_desc["end"]
            d_fwd = (p1.x*10 - s["x"])**2 + (p1.y*10 - s["y"])**2 + (p2.x*10 - e["x"])**2 + (p2.y*10 - e["y"])**2
            d_rev = (p1.x*10 - e["x"])**2 + (p1.y*10 - e["y"])**2 + (p2.x*10 - s["x"])**2 + (p2.y*10 - s["y"])**2
            return min(d_fwd, d_rev) < 0.05
        elif c_type == "circle" and hasattr(ec, "centerSketchPoint"):
            c = ec.centerSketchPoint.geometry
            r_mm = ec.radius * 10.0
            dist_c = (c.x*10 - c_desc["center"]["x"])**2 + (c.y*10 - c_desc["center"]["y"])**2
            return dist_c < 0.05 and abs(r_mm - c_desc["radius_mm"]) < 0.05
        elif c_type == "arc" and hasattr(ec, "startSketchPoint"):
            p1 = ec.startSketchPoint.geometry
            p2 = ec.endSketchPoint.geometry
            s, e = c_desc["start"], c_desc["end"]
            d_fwd = (p1.x*10 - s["x"])**2 + (p1.y*10 - s["y"])**2 + (p2.x*10 - e["x"])**2 + (p2.y*10 - e["y"])**2
            d_rev = (p1.x*10 - e["x"])**2 + (p1.y*10 - e["y"])**2 + (p2.x*10 - s["x"])**2 + (p2.y*10 - s["y"])**2
            return min(d_fwd, d_rev) < 0.05
    except:
        pass
    return False


def apply_midpoint(geo_constraints, point, curve):
    if not point or not curve:
        return False
    for m_name, args in [("addMidPoint", (point, curve)), ("addMidpoint", (point, curve)),
                         ("addMidPoint", (curve, point)), ("addMidpoint", (curve, point))]:
        if hasattr(geo_constraints, m_name):
            try:
                res = getattr(geo_constraints, m_name)(*args)
                if res is not None:
                    return True
            except:
                pass
    return False


def find_matching_profiles(sketch, target_profiles, created_curves):
    matched = adsk.core.ObjectCollection.create()
    total = sketch.profiles.count
    if total == 0:
        return matched

    if target_profiles:
        rev_map = {get_token(c): cid for cid, c in created_curves.items() if get_token(c)}
        used = set()
        for t_prof in target_profiles:
            t_outer = set(t_prof.get("outer_curve_ids", []))
            t_area = t_prof.get("area_mm2", 0.0)
            t_cent = t_prof.get("centroid")
            t_inner = t_prof.get("inner_loops_count")
            best_prof, best_score, best_idx = None, -1e9, -1

            for p_idx in range(total):
                if p_idx in used:
                    continue
                p = sketch.profiles.item(p_idx)
                try:
                    c_area = p.areaProperties().area * 100.0
                    cnt = p.areaProperties().centroid
                    cx, cy = cnt.x * 10.0, cnt.y * 10.0
                except:
                    c_area, cx, cy = 0.0, 0.0, 0.0

                c_outer = set()
                c_inner = 0
                for loop in p.profileLoops:
                    if loop.isOuter:
                        for pc in loop.profileCurves:
                            tok = get_token(pc.sketchEntity)
                            if tok in rev_map:
                                c_outer.add(rev_map[tok])
                    else:
                        c_inner += 1

                score = 0.0
                if t_outer and c_outer:
                    score += (len(t_outer & c_outer) / max(1, len(t_outer | c_outer))) * 100.0
                if t_inner is not None and t_inner == c_inner:
                    score += 25.0
                if t_cent:
                    dist = math.sqrt((cx - t_cent["x"])**2 + (cy - t_cent["y"])**2)
                    score += 50.0 if dist < 0.2 else (20.0 if dist < 2.0 else -dist)
                if t_area > 0 and c_area > 0:
                    score += (min(t_area, c_area) / max(t_area, c_area)) * 30.0

                if score > best_score:
                    best_score, best_prof, best_idx = score, p, p_idx

            if best_prof is not None:
                matched.add(best_prof)
                used.add(best_idx)

        if matched.count > 0:
            return matched

    matched.add(sketch.profiles.item(0))
    return matched


class ModelContext:
    def __init__(self):
        self.sketches = {}
        self.curves = {}
        self.points = {}

    def register(self, name, sketch, curves, points):
        self.sketches[name] = sketch
        self.curves[name] = curves
        self.points[name] = points


# ==============================================================================
# STEP 0: SKETCH "Sketch1" (Modified: Extended Cantilever Base Plate)
# ==============================================================================
def build_step_0_Sketch1(root_comp, ctx):
    plane = resolve_canonical_plane(root_comp, "XY")
    sketch = root_comp.sketches.add(plane)
    sketch.name = "Sketch1"
    sketch.isVisible = True
    lines = sketch.sketchCurves.sketchLines
    circles = sketch.sketchCurves.sketchCircles
    arcs = sketch.sketchCurves.sketchArcs
    pts = sketch.sketchPoints
    gc = sketch.geometricConstraints
    dims = sketch.sketchDimensions
    existing = [c for c in sketch.sketchCurves]
    curves = {}
    points = {}

    # 1. Create Curves
    # Curve 0: Vertical segment down from top mounting boss (x = 21.1) to cantilever top (y = 8.9489)
    curves[0] = lines.addByTwoPoints(pt(21.1, 16.0, 0.0), pt(21.1, 8.9489, 0.0))

    # Curve 1: Upper horizontal edge of cantilever arm extending to relocated holder edge (x = 86.1)
    curves[1] = lines.addByTwoPoints(pt(21.1, 8.9489, 0.0), pt(86.1, 8.9489, 0.0))

    # Curve 2: Right vertical edge of base plate flush with holder outer edge (x = 86.1)
    curves[2] = lines.addByTwoPoints(pt(86.1, 8.9489, 0.0), pt(86.1, -10.9, 0.0))

    # Curve 3: Lower-right corner fillet arc (R = 10.2 mm, center at (75.9, -10.9))
    curves[3] = arcs.addByThreePoints(pt(86.1, -10.9, 0.0), pt(83.1125, -18.1125, 0.0), pt(75.9, -21.1, 0.0))

    # Curve 4: Full bottom edge extending from cantilever tip back to rear mounting hole
    curves[4] = lines.addByTwoPoints(pt(75.9, -21.1, 0.0), pt(-16.0, -21.1, 0.0))

    # Curve 5: Rounded boss around lower mounting hole (-16, -16) (R = 5.1 mm)
    curves[5] = arcs.addByThreePoints(pt(-16.0, -21.1, 0.0), pt(-21.1, -16.0, 0.0), pt(-16.0, -10.9, 0.0))

    # Curve 6: Inside horizontal segment from lower boss to internal corner fillet
    curves[6] = lines.addByTwoPoints(pt(-16.0, -10.9, 0.0), pt(0.8, -10.9, 0.0))

    # Curve 7: Internal inside fillet arc (R = 10.1 mm, center at (0.8, -0.8))
    curves[7] = arcs.addByThreePoints(pt(0.8, -10.9, 0.0), pt(7.9418, -7.9418, 0.0), pt(10.9, -0.8, 0.0))

    # Curve 8: Inside vertical segment leading up to upper mounting boss
    curves[8] = lines.addByTwoPoints(pt(10.9, -0.8, 0.0), pt(10.9, 16.0, 0.0))

    # Curve 9: Rounded boss around upper mounting hole (16, 16) (R = 5.1 mm)
    curves[9] = arcs.addByThreePoints(pt(10.9, 16.0, 0.0), pt(16.0, 21.1, 0.0), pt(21.1, 16.0, 0.0))

    # Curve 10: Upper mounting hole (fixed at 16, 16) - dia 3.4 mm
    curves[10] = circles.addByCenterRadius(pt(16.0, 16.0, 0.0), 1.7 * 0.1)

    # Curve 11: Lower mounting hole (fixed at -16, -16) - dia 3.4 mm
    curves[11] = circles.addByCenterRadius(pt(-16.0, -16.0, 0.0), 1.7 * 0.1)

    # 2. Tangent Constraints
    for c1, c2 in [(8, 9), (9, 0), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]:
        try:
            gc.addTangent(curves[c1], curves[c2])
        except:
            pass

    # 3. Dimensions
    try:
        dims.addDiameterDimension(curves[10], pt(15.8, 15.1, 0.0)).parameter.expression = "3.4 mm"
    except:
        pass
    try:
        dims.addDiameterDimension(curves[11], pt(-15.3, -15.5, 0.0)).parameter.expression = "3.4 mm"
    except:
        pass

    ctx.register("Sketch1", sketch, curves, points)


# ==============================================================================
# STEP 1: EXTRUDE "Extrude1" (Base Plate Extrusion)
# ==============================================================================
def build_step_1_Extrude1(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch1")
    curves = ctx.curves.get("Sketch1", {})
    target_profiles = [{'area_mm2': 2670.0, 'centroid': {'x': 37.0, 'y': -7.0, 'z': 0.0}, 'outer_curve_ids': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 'inner_loops_count': 2}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.4))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude1"


# ==============================================================================
# STEP 2: SKETCH "Sketch3" (Stylus Holder Block Footprint: Relocated +65 mm)
# ==============================================================================
def build_step_2_Sketch3(root_comp, ctx):
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 4.0}, 'offset_mm': 4.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    sketch = root_comp.sketches.add(face) if face else root_comp.sketches.add(resolve_canonical_plane(root_comp, "XY"))
    sketch.name = "Sketch3"
    sketch.isVisible = True
    lines = sketch.sketchCurves.sketchLines
    pts = sketch.sketchPoints
    gc = sketch.geometricConstraints
    dims = sketch.sketchDimensions
    curves = {}
    points = {}

    # Shifted: X from [11.1, 21.1] -> [76.1, 86.1] (+65 mm)
    curves[4] = lines.addByTwoPoints(pt(86.1, 8.9489, 0.0), pt(86.1, -6.0511, 0.0))
    curves[5] = lines.addByTwoPoints(pt(86.1, 8.9489, 0.0), pt(76.1, 8.9489, 0.0))
    curves[6] = lines.addByTwoPoints(pt(86.1, -6.0511, 0.0), pt(76.1, -6.0511, 0.0))
    curves[7] = lines.addByTwoPoints(pt(76.1, -6.0511, 0.0), pt(76.1, 8.9489, 0.0))
    curves[8] = lines.addByTwoPoints(pt(76.1, 8.9489, 0.0), pt(86.1, 8.9489, 0.0))
    curves[9] = lines.addByTwoPoints(pt(86.1, 8.9489, 0.0), pt(86.1, -6.0511, 0.0))
    curves[10] = lines.addByTwoPoints(pt(86.1, 8.9489, 0.0), pt(76.1, -6.0511, 0.0))

    try:
        gc.addHorizontal(curves[5])
        gc.addHorizontal(curves[6])
        gc.addVertical(curves[7])
        gc.addVertical(curves[4])
    except:
        pass

    ctx.register("Sketch3", sketch, curves, points)


# ==============================================================================
# STEP 3: EXTRUDE "Extrude3" (Stylus Block Extrusion)
# ==============================================================================
def build_step_3_Extrude3(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch3")
    curves = ctx.curves.get("Sketch3", {})
    # Centroids shifted +65 mm along X
    target_profiles = [
        {'area_mm2': 75.0, 'centroid': {'x': 82.7667, 'y': -1.0511, 'z': 0.0}, 'outer_curve_ids': [4, 6, 10], 'inner_loops_count': 0},
        {'area_mm2': 75.0, 'centroid': {'x': 79.4333, 'y': 3.9489, 'z': 0.0}, 'outer_curve_ids': [5, 7, 10], 'inner_loops_count': 0}
    ]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(1.0))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude3"


# ==============================================================================
# STEP 4: SKETCH "Sketch4" (Stylus Bore & Top Rounding: Relocated +65 mm)
# ==============================================================================
def build_step_4_Sketch4(root_comp, ctx):
    plane_info = {'plane': 'XZ', 'type': 'FACE', 'normal': {'x': 0.0, 'y': -1.0, 'z': 0.0}, 'origin': {'x': 0.0, 'y': -6.0511, 'z': 0.0}, 'offset_mm': -6.0511, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    sketch = root_comp.sketches.add(face) if face else root_comp.sketches.add(resolve_canonical_plane(root_comp, "XZ"))
    sketch.name = "Sketch4"
    sketch.isVisible = True
    lines = sketch.sketchCurves.sketchLines
    circles = sketch.sketchCurves.sketchCircles
    arcs = sketch.sketchCurves.sketchArcs
    pts = sketch.sketchPoints
    gc = sketch.geometricConstraints
    dims = sketch.sketchDimensions
    existing = [c for c in sketch.sketchCurves]
    curves = {}
    points = {}

    # Shifted: X from [11.1, 21.1] -> [76.1, 86.1], center X = 81.1
    # Reference frame curves
    c_desc0 = {'id': 0, 'type': 'line', 'is_reference': True, 'start': {'x': 76.1, 'y': 4.0, 'z': 0.0}, 'end': {'x': 86.1, 'y': 4.0, 'z': 0.0}}
    matched_c0 = next((ec for ec in existing if curve_matches(c_desc0, ec)), None)
    curves[0] = matched_c0 if matched_c0 else lines.addByTwoPoints(pt(76.1, 4.0, 0.0), pt(86.1, 4.0, 0.0))

    c_desc1 = {'id': 1, 'type': 'line', 'is_reference': True, 'start': {'x': 86.1, 'y': 4.0, 'z': 0.0}, 'end': {'x': 86.1, 'y': 14.0, 'z': 0.0}}
    matched_c1 = next((ec for ec in existing if curve_matches(c_desc1, ec)), None)
    curves[1] = matched_c1 if matched_c1 else lines.addByTwoPoints(pt(86.1, 4.0, 0.0), pt(86.1, 14.0, 0.0))

    c_desc2 = {'id': 2, 'type': 'line', 'is_reference': True, 'start': {'x': 86.1, 'y': 14.0, 'z': 0.0}, 'end': {'x': 76.1, 'y': 14.0, 'z': 0.0}}
    matched_c2 = next((ec for ec in existing if curve_matches(c_desc2, ec)), None)
    curves[2] = matched_c2 if matched_c2 else lines.addByTwoPoints(pt(86.1, 14.0, 0.0), pt(76.1, 14.0, 0.0))

    c_desc3 = {'id': 3, 'type': 'line', 'is_reference': True, 'start': {'x': 76.1, 'y': 14.0, 'z': 0.0}, 'end': {'x': 76.1, 'y': 4.0, 'z': 0.0}}
    matched_c3 = next((ec for ec in existing if curve_matches(c_desc3, ec)), None)
    curves[3] = matched_c3 if matched_c3 else lines.addByTwoPoints(pt(76.1, 14.0, 0.0), pt(76.1, 4.0, 0.0))

    # Cutting geometry
    curves[4] = lines.addByTwoPoints(pt(86.1, 14.0, 0.0), pt(76.1, 4.0, 0.0))
    curves[5] = circles.addByCenterRadius(pt(81.1, 9.0, 0.0), 3.65 * 0.1)
    curves[6] = arcs.addByThreePoints(pt(86.1, 9.0, 0.0), pt(81.1, 14.0, 0.0), pt(76.1, 9.0, 0.0))

    try:
        dims.addDiameterDimension(curves[5], pt(88.8, 10.7, 0.0)).parameter.expression = "7.3 mm"
    except:
        pass

    ctx.register("Sketch4", sketch, curves, points)


# ==============================================================================
# STEP 5: EXTRUDE "Extrude4" (Through Cut for Bore & Rounded Crown)
# ==============================================================================
def build_step_5_Extrude4(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch4")
    curves = ctx.curves.get("Sketch4", {})
    # Shifted centroids +65 mm along X
    target_profiles = [
        {'area_mm2': 2.6825, 'centroid': {'x': 84.3169, 'y': 13.5494, 'z': 0.0}, 'outer_curve_ids': [2, 4, 6], 'inner_loops_count': 0},
        {'area_mm2': 2.6825, 'centroid': {'x': 85.6494, 'y': 12.2169, 'z': 0.0}, 'outer_curve_ids': [1, 4, 6], 'inner_loops_count': 0},
        {'area_mm2': 5.365, 'centroid': {'x': 77.2168, 'y': 12.8832, 'z': 0.0}, 'outer_curve_ids': [2, 3, 6], 'inner_loops_count': 0},
        {'area_mm2': 20.9269, 'centroid': {'x': 82.1954, 'y': 7.9046, 'z': 0.0}, 'outer_curve_ids': [4, 5], 'inner_loops_count': 0},
        {'area_mm2': 20.9269, 'centroid': {'x': 80.0046, 'y': 10.0954, 'z': 0.0}, 'outer_curve_ids': [4, 5], 'inner_loops_count': 0}
    ]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = adsk.fusion.FeatureOperations.CutFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-1.5))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude4"


# ==============================================================================
# STEP 6: SKETCH "Sketch8" (Top Boss: Relocated +65 mm)
# ==============================================================================
def build_step_6_Sketch8(root_comp, ctx):
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 4.0}, 'offset_mm': 4.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    sketch = root_comp.sketches.add(face) if face else root_comp.sketches.add(resolve_canonical_plane(root_comp, "XY"))
    sketch.name = "Sketch8"
    sketch.isVisible = True
    circles = sketch.sketchCurves.sketchCircles
    dims = sketch.sketchDimensions
    curves = {}
    points = {}

    # Center shifted +65 mm: (16.1 + 65, 1.4489) = (81.1, 1.4489)
    curves[0] = circles.addByCenterRadius(pt(81.1, 1.4489, 0.0), 3.0 * 0.1)
    try:
        dims.addDiameterDimension(curves[0], pt(80.5, 2.8, 0.0)).parameter.expression = "6 mm"
    except:
        pass

    ctx.register("Sketch8", sketch, curves, points)


# ==============================================================================
# STEP 7: EXTRUDE "Extrude6" (Top Boss Extrude)
# ==============================================================================
def build_step_7_Extrude6(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch8")
    curves = ctx.curves.get("Sketch8", {})
    target_profiles = [{'area_mm2': 28.2743, 'centroid': {'x': 81.1, 'y': 1.4489, 'z': 0.0}, 'outer_curve_ids': [0], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = adsk.fusion.FeatureOperations.JoinFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.25))
    ext_in.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(0.9))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude6"


# ==============================================================================
# STEP 8: SKETCH "Sketch7" (Bottom Hole: Relocated +65 mm)
# ==============================================================================
def build_step_8_Sketch7(root_comp, ctx):
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': -1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 0.0}, 'offset_mm': 0.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    sketch = root_comp.sketches.add(face) if face else root_comp.sketches.add(resolve_canonical_plane(root_comp, "XY"))
    sketch.name = "Sketch7"
    sketch.isVisible = True
    circles = sketch.sketchCurves.sketchCircles
    dims = sketch.sketchDimensions
    curves = {}
    points = {}

    # Under normal (0, 0, -1), sketch X = -world X -> sketch X = -(16.1 + 65) = -81.1 mm
    curves[6] = circles.addByCenterRadius(pt(-81.1, 1.4489, 0.0), 1.7 * 0.1)
    try:
        dims.addDiameterDimension(curves[6], pt(-84.5, 2.8, 0.0)).parameter.expression = "3.4 mm"
    except:
        pass

    ctx.register("Sketch7", sketch, curves, points)


# ==============================================================================
# STEP 9: EXTRUDE "Extrude7" (Bottom Hole Cut)
# ==============================================================================
def build_step_9_Extrude7(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch7")
    curves = ctx.curves.get("Sketch7", {})
    target_profiles = [{'area_mm2': 9.0792, 'centroid': {'x': -81.1, 'y': 1.4489, 'z': 0.0}, 'outer_curve_ids': [6], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = adsk.fusion.FeatureOperations.CutFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-0.8))
    ext_in.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(-1.0))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude7"


# ==============================================================================
# STEP 10: SKETCH "Sketch9" (Fixed Mounting Counterbores)
# ==============================================================================
def build_step_10_Sketch9(root_comp, ctx):
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 4.0}, 'offset_mm': 4.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    sketch = root_comp.sketches.add(face) if face else root_comp.sketches.add(resolve_canonical_plane(root_comp, "XY"))
    sketch.name = "Sketch9"
    sketch.isVisible = True
    circles = sketch.sketchCurves.sketchCircles
    gc = sketch.geometricConstraints
    dims = sketch.sketchDimensions
    curves = {}
    points = {}

    # Mounting counterbores remain fixed at (16, 16) and (-16, -16)
    curves[0] = circles.addByCenterRadius(pt(16.0, 16.0, 0.0), 6.0 * 0.1)
    curves[1] = circles.addByCenterRadius(pt(-16.0, -16.0, 0.0), 6.0 * 0.1)

    try:
        gc.addEqual(curves[0], curves[1])
        dims.addDiameterDimension(curves[0], pt(13.0, 16.5, 0.0)).parameter.expression = "12 mm"
    except:
        pass

    ctx.register("Sketch9", sketch, curves, points)


# ==============================================================================
# STEP 11: EXTRUDE "Extrude8" (Mounting Counterbore Cuts)
# ==============================================================================
def build_step_11_Extrude8(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch9")
    curves = ctx.curves.get("Sketch9", {})
    target_profiles = [
        {'area_mm2': 113.0973, 'centroid': {'x': 16.0, 'y': 16.0, 'z': 0.0}, 'outer_curve_ids': [0], 'inner_loops_count': 0},
        {'area_mm2': 113.0973, 'centroid': {'x': -16.0, 'y': -16.0, 'z': 0.0}, 'outer_curve_ids': [1], 'inner_loops_count': 0}
    ]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = adsk.fusion.FeatureOperations.CutFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-0.2))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude8"


# ==============================================================================
# MAIN EXECUTION SEQUENCE
# ==============================================================================
ALL_STEPS = [
    build_step_0_Sketch1,
    build_step_1_Extrude1,
    build_step_2_Sketch3,
    build_step_3_Extrude3,
    build_step_4_Sketch4,
    build_step_5_Extrude4,
    build_step_6_Sketch8,
    build_step_7_Extrude6,
    build_step_8_Sketch7,
    build_step_9_Extrude7,
    build_step_10_Sketch9,
    build_step_11_Extrude8,
]


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        product = app.activeProduct
        if not product:
            ui.messageBox("Please create an active Fusion 360 design document first.")
            return

        design = adsk.fusion.Design.cast(product)
        root_comp = design.rootComponent
        ctx = ModelContext()

        for step_fn in ALL_STEPS:
            step_fn(root_comp, ctx)

        for sk in ctx.sketches.values():
            sk.isVisible = True

        app.activeViewport.fit()
        app.activeViewport.refresh()
        ui.messageBox("REBUILD COMPLETE!\n\nPrusa Mini heatsink bracket reconstructed successfully with +65 mm offset stylus holder.", "Success")
    except:
        if ui:
            ui.messageBox(f"Rebuild failed:\n{traceback.format_exc()}")
        else:
            print(traceback.format_exc())