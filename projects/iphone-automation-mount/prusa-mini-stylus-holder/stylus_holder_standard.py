"""
Standalone Rebuild Script for: ai stylus holder
Auto-generated from full_steps.json (12 timeline steps)
Reconstructs all sketches, constraints, dimensions, and extrusions natively.
"""
import adsk.core
import adsk.fusion
import traceback
import math

# Compatibility aliases for JSON literal compatibility
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
# STEP 0: SKETCH "Sketch1"
# ==============================================================================
def build_step_0_Sketch1(root_comp, ctx):
    # Planar attachment
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 0.0}, 'offset_mm': 0.0, 'body_name': 'Body1'}
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
    # Curve 0: line
    c_desc = {'id': 0, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 26.9, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 21.099999999999998, 'y': 16.000000135103857, 'z': 0.0}, 'end': {'x': 21.10000071260656, 'y': -10.899998230934058, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[0] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.099999999999998, 16.000000135103857, 0.0), pt(21.10000071260656, -10.899998230934058, 0.0))
        curves[0] = l
    # Curve 1: line
    c_desc = {'id': 1, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 16.8, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 10.900000000000002, 'y': 16.00000015199185, 'z': 0.0}, 'end': {'x': 10.900000604987234, 'y': -0.7999985011419924, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[1] = matched_c
    else:
        l = lines.addByTwoPoints(pt(10.900000000000002, 16.00000015199185, 0.0), pt(10.900000604987234, -0.7999985011419924, 0.0))
        curves[1] = l
    # Curve 2: line
    c_desc = {'id': 2, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 16.8, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': -16.000000243186957, 'y': -10.900000000000007, 'z': 0.0}, 'end': {'x': 0.7999979310567462, 'y': -10.900000000000007, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[2] = matched_c
    else:
        l = lines.addByTwoPoints(pt(-16.000000243186957, -10.900000000000007, 0.0), pt(0.7999979310567462, -10.900000000000007, 0.0))
        curves[2] = l
    # Curve 3: line
    c_desc = {'id': 3, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 26.9, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': -16.000000243186935, 'y': -21.099999999999994, 'z': 0.0}, 'end': {'x': 10.900000000000002, 'y': -21.10000128269188, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[3] = matched_c
    else:
        l = lines.addByTwoPoints(pt(-16.000000243186935, -21.099999999999994, 0.0), pt(10.900000000000002, -21.10000128269188, 0.0))
        curves[3] = l
    # Curve 4: circle
    c_desc = {'id': 4, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': 16.0, 'y': 16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[4] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(16.0, 16.0, 0.0), 1.7 * 0.1)
        curves[4] = cir
    # Curve 5: circle
    c_desc = {'id': 5, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': -16.0, 'y': -16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[5] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(-16.0, -16.0, 0.0), 1.7 * 0.1)
        curves[5] = cir
    # Curve 6: arc
    c_desc = {'id': 6, 'type': 'arc', 'is_reference': False, 'is_construction': False, 'radius_mm': 5.1, 'start': {'x': 21.099999999999998, 'y': 16.000000135103857, 'z': 0.0}, 'end': {'x': 10.900000000000002, 'y': 16.00000015199185, 'z': 0.0}, 'center': {'x': 16.0, 'y': 16.0, 'z': 0.0}, 'mid': {'x': 16.0000000070715, 'y': 21.1, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[6] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(21.099999999999998, 16.000000135103857, 0.0), pt(16.0000000070715, 21.1, 0.0), pt(10.900000000000002, 16.00000015199185, 0.0))
        curves[6] = arc
    # Curve 7: arc
    c_desc = {'id': 7, 'type': 'arc', 'is_reference': False, 'is_construction': False, 'radius_mm': 5.1, 'start': {'x': -16.000000243186957, 'y': -10.900000000000007, 'z': 0.0}, 'end': {'x': -16.000000243186935, 'y': -21.099999999999994, 'z': 0.0}, 'center': {'x': -16.0, 'y': -16.0, 'z': 0.0}, 'mid': {'x': -21.099999999999998, 'y': -16.000000005889767, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[7] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(-16.000000243186957, -10.900000000000007, 0.0), pt(-21.099999999999998, -16.000000005889767, 0.0), pt(-16.000000243186935, -21.099999999999994, 0.0))
        curves[7] = arc
    # Curve 8: arc
    c_desc = {'id': 8, 'type': 'arc', 'is_reference': False, 'is_construction': False, 'radius_mm': 10.2, 'start': {'x': 10.900000000000002, 'y': -21.10000128269188, 'z': 0.0}, 'end': {'x': 21.10000071260656, 'y': -10.899998230934058, 'z': 0.0}, 'center': {'x': 10.899997931056312, 'y': -10.899998501141841, 'z': 0.0}, 'mid': {'x': 18.11248989302703, 'y': -18.112488809082688, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[8] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(10.900000000000002, -21.10000128269188, 0.0), pt(18.11248989302703, -18.112488809082688, 0.0), pt(21.10000071260656, -10.899998230934058, 0.0))
        curves[8] = arc
    # Curve 9: arc
    c_desc = {'id': 9, 'type': 'arc', 'is_reference': False, 'is_construction': False, 'radius_mm': 10.1, 'start': {'x': 0.7999979310567462, 'y': -10.900000000000007, 'z': 0.0}, 'end': {'x': 10.900000604987234, 'y': -0.7999985011419924, 'z': 0.0}, 'center': {'x': 0.7999988051556783, 'y': -0.7999982001384797, 'z': 0.0}, 'mid': {'x': 7.9417781523726605, 'y': -7.94177837827837, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[9] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(0.7999979310567462, -10.900000000000007, 0.0), pt(7.9417781523726605, -7.94177837827837, 0.0), pt(10.900000604987234, -0.7999985011419924, 0.0))
        curves[9] = arc

    # 2. Points
    points[0] = sketch.originPoint
    points[1] = getattr(curves.get(4), "centerSketchPoint", None)
    points[2] = getattr(curves.get(5), "centerSketchPoint", None)
    points[3] = pts.add(pt(-21.1, -16.0, 0.0))
    points[4] = pts.add(pt(-16.0, -21.1, 0.0))
    points[5] = pts.add(pt(-16.0, -10.9, 0.0))
    points[6] = pts.add(pt(16.0, 21.1, 0.0))
    points[7] = pts.add(pt(21.1, 16.0, 0.0))
    points[8] = pts.add(pt(10.9, 16.0, 0.0))
    points[9] = getattr(curves.get(6), "startSketchPoint", None)
    points[10] = getattr(curves.get(6), "endSketchPoint", None)
    points[11] = getattr(curves.get(6), "centerSketchPoint", None)
    points[12] = getattr(curves.get(7), "startSketchPoint", None)
    points[13] = getattr(curves.get(7), "endSketchPoint", None)
    points[14] = getattr(curves.get(7), "centerSketchPoint", None)
    points[15] = getattr(curves.get(8), "endSketchPoint", None)
    points[16] = getattr(curves.get(9), "endSketchPoint", None)
    points[17] = getattr(curves.get(9), "startSketchPoint", None)
    points[18] = getattr(curves.get(8), "startSketchPoint", None)
    points[19] = getattr(curves.get(8), "centerSketchPoint", None)
    points[20] = getattr(curves.get(9), "centerSketchPoint", None)

    # 3. Geometric Constraints
    try:
        if 0 in curves and 6 in curves:
            gc.addTangent(curves[0], curves[6])
    except:
        pass
    try:
        if 1 in curves and 6 in curves:
            gc.addTangent(curves[1], curves[6])
    except:
        pass
    try:
        if 1 in curves:
            gc.addVertical(curves[1])
    except:
        pass
    try:
        if 2 in curves and 7 in curves:
            gc.addTangent(curves[2], curves[7])
    except:
        pass
    try:
        if 3 in curves and 7 in curves:
            gc.addTangent(curves[3], curves[7])
    except:
        pass
    try:
        if 8 in curves and 0 in curves:
            gc.addTangent(curves[8], curves[0])
    except:
        pass
    try:
        if 9 in curves and 1 in curves:
            gc.addTangent(curves[9], curves[1])
    except:
        pass

    # 4. Dimensions
    try:
        if 4 in curves:
            dim = dims.addDiameterDimension(curves[4], pt(15.849815463651854, 15.163373078940264, 0.0))
            dim.parameter.expression = "3.4 mm"
    except:
        pass
    try:
        if 5 in curves:
            dim = dims.addDiameterDimension(curves[5], pt(-15.282115955059158, -15.54487089961267, 0.0))
            dim.parameter.expression = "3.4 mm"
    except:
        pass
    try:
        e1, e2 = points.get(1), sketch.originPoint
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, pt(10.834950572136917, -4.191445677417693, 0.0))
            dim.parameter.expression = "16 mm"
    except:
        pass
    try:
        e1, e2 = points.get(1), sketch.originPoint
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, pt(-16.11696474067747, 14.551785124000212, 0.0))
            dim.parameter.expression = "16 mm"
    except:
        pass
    try:
        e1, e2 = points.get(2), sketch.originPoint
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation, pt(-8.485115075705734, -22.363427318083286, 0.0))
            dim.parameter.expression = "16 mm"
    except:
        pass
    try:
        e1, e2 = sketch.originPoint, points.get(2)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.VerticalDimensionOrientation, pt(-42.38494253839412, -10.520981227639055, 0.0))
            dim.parameter.expression = "16 mm"
    except:
        pass
    try:
        e1, e2 = points.get(3), points.get(2)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(-18.876535070694967, -5.845996853814098, 0.0))
            dim.parameter.expression = "5.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(2), points.get(4)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(-9.282311540781851, -19.225317842824253, 0.0))
            dim.parameter.expression = "5.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(5), points.get(2)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(-6.914421059145697, -15.495833746043054, 0.0))
            dim.parameter.expression = "5.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(6), points.get(1)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(35.921956271084206, 15.565012496345794, 0.0))
            dim.parameter.expression = "5.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(7), points.get(1)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(18.481289987185193, 9.678735217323917, 0.0))
            dim.parameter.expression = "5.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(1), points.get(8)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(10.357452998683932, 28.98123214658014, 0.0))
            dim.parameter.expression = "5.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(16), points.get(19)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(37.55384838174818, -9.114640036922237, 0.0))
            dim.parameter.expression = "10.1 mm"
    except:
        pass
    try:
        e1, e2 = points.get(19), points.get(17)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(-0.21567897688240523, 8.826263083363704, 0.0))
            dim.parameter.expression = "10.1 mm"
    except:
        pass
    ctx.register("Sketch1", sketch, curves, points)

# ==============================================================================
# STEP 1: EXTRUDE "Extrude1"
# ==============================================================================
def build_step_1_Extrude1(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch1")
    curves = ctx.curves.get("Sketch1", {})
    target_profiles = [{'area_mm2': 715.9188, 'centroid': {'x': 7.0338, 'y': -7.0338, 'z': 0.0}, 'outer_curve_ids': [0, 1, 2, 3, 6, 7, 8, 9], 'inner_loops_count': 2}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = 3
    if root_comp.bRepBodies.count == 0 and op in (0, 1, 2):
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.4))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude1"

# ==============================================================================
# STEP 2: SKETCH "Sketch3"
# ==============================================================================
def build_step_2_Sketch3(root_comp, ctx):
    # Planar attachment
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 4.0}, 'offset_mm': 4.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    if face:
        sketch = root_comp.sketches.add(face)
    else:
        plane = resolve_canonical_plane(root_comp, "XY")
        sketch = root_comp.sketches.add(plane)
    sketch.name = "Sketch3"
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
    # Curve 0: line
    c_desc = {'id': 0, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 26.9, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': -16.000000243186935, 'y': -21.09999999999999, 'z': 0.0}, 'end': {'x': 10.9, 'y': -21.10000128269188, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[0] = matched_c
    else:
        l = lines.addByTwoPoints(pt(-16.000000243186935, -21.09999999999999, 0.0), pt(10.9, -21.10000128269188, 0.0))
        curves[0] = l
    # Curve 1: line
    c_desc = {'id': 1, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 26.9, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 21.10000071260656, 'y': -10.899998230934056, 'z': 0.0}, 'end': {'x': 21.099999999999994, 'y': 16.00000013510386, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[1] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.10000071260656, -10.899998230934056, 0.0), pt(21.099999999999994, 16.00000013510386, 0.0))
        curves[1] = l
    # Curve 2: line
    c_desc = {'id': 2, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 16.8, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 10.900000000000002, 'y': 16.00000015199185, 'z': 0.0}, 'end': {'x': 10.900000605017237, 'y': -0.7999985011419941, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[2] = matched_c
    else:
        l = lines.addByTwoPoints(pt(10.900000000000002, 16.00000015199185, 0.0), pt(10.900000605017237, -0.7999985011419941, 0.0))
        curves[2] = l
    # Curve 3: line
    c_desc = {'id': 3, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 16.8, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 0.7999979310567455, 'y': -10.900000000000002, 'z': 0.0}, 'end': {'x': -16.000000243186957, 'y': -10.900000000000007, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[3] = matched_c
    else:
        l = lines.addByTwoPoints(pt(0.7999979310567455, -10.900000000000002, 0.0), pt(-16.000000243186957, -10.900000000000007, 0.0))
        curves[3] = l
    # Curve 4: line
    c_desc = {'id': 4, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 15.0, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 21.10000018679014, 'y': 8.948907775903765, 'z': 0.0}, 'end': {'x': 21.100000584154426, 'y': -6.051092224096232, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[4] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.10000018679014, 8.948907775903765, 0.0), pt(21.100000584154426, -6.051092224096232, 0.0))
        curves[4] = l
    # Curve 5: line
    c_desc = {'id': 5, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 21.10000018679014, 'y': 8.948907775903765, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': 8.948907510994244, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[5] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.10000018679014, 8.948907775903765, 0.0), pt(11.100000186790144, 8.948907510994244, 0.0))
        curves[5] = l
    # Curve 6: line
    c_desc = {'id': 6, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 21.100000584154426, 'y': -6.051092224096232, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': -6.051092224096232, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[6] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.100000584154426, -6.051092224096232, 0.0), pt(11.100000186790144, -6.051092224096232, 0.0))
        curves[6] = l
    # Curve 7: line
    c_desc = {'id': 7, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 15.0, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 11.100000186790144, 'y': -6.051092224096232, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': 8.948907510994244, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[7] = matched_c
    else:
        l = lines.addByTwoPoints(pt(11.100000186790144, -6.051092224096232, 0.0), pt(11.100000186790144, 8.948907510994244, 0.0))
        curves[7] = l
    # Curve 8: line
    c_desc = {'id': 8, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 11.100000186790144, 'y': 8.948907510994244, 'z': 0.0}, 'end': {'x': 21.100000584154426, 'y': 8.948907510994244, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[8] = matched_c
    else:
        l = lines.addByTwoPoints(pt(11.100000186790144, 8.948907510994244, 0.0), pt(21.100000584154426, 8.948907510994244, 0.0))
        curves[8] = l
    # Curve 9: line
    c_desc = {'id': 9, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 15.0, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 21.100000584154426, 'y': 8.948907510994244, 'z': 0.0}, 'end': {'x': 21.100000584154426, 'y': -6.051092224096232, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[9] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.100000584154426, 8.948907510994244, 0.0), pt(21.100000584154426, -6.051092224096232, 0.0))
        curves[9] = l
    # Curve 10: line
    c_desc = {'id': 10, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 18.0278, 'is_horizontal': False, 'is_vertical': False, 'start': {'x': 21.10000018679014, 'y': 8.948907775903765, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': -6.051092224096232, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[10] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.10000018679014, 8.948907775903765, 0.0), pt(11.100000186790144, -6.051092224096232, 0.0))
        curves[10] = l
    # Curve 11: circle
    c_desc = {'id': 11, 'type': 'circle', 'is_reference': True, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': -16.0, 'y': -16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[11] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(-16.0, -16.0, 0.0), 1.7 * 0.1)
        curves[11] = cir
    # Curve 12: circle
    c_desc = {'id': 12, 'type': 'circle', 'is_reference': True, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': 16.0, 'y': 16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[12] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(16.0, 16.0, 0.0), 1.7 * 0.1)
        curves[12] = cir
    # Curve 13: arc
    c_desc = {'id': 13, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 5.1, 'start': {'x': -16.000000243186957, 'y': -10.900000000000007, 'z': 0.0}, 'end': {'x': -16.000000243186935, 'y': -21.09999999999999, 'z': 0.0}, 'center': {'x': -16.0, 'y': -16.0, 'z': 0.0}, 'mid': {'x': -21.099999999999998, 'y': -16.000000002866752, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[13] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(-16.000000243186957, -10.900000000000007, 0.0), pt(-21.099999999999998, -16.000000002866752, 0.0), pt(-16.000000243186935, -21.09999999999999, 0.0))
        curves[13] = arc
    # Curve 14: arc
    c_desc = {'id': 14, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 10.2, 'start': {'x': 10.9, 'y': -21.10000128269188, 'z': 0.0}, 'end': {'x': 21.10000071260656, 'y': -10.899998230934056, 'z': 0.0}, 'center': {'x': 10.899997931056312, 'y': -10.899998501141841, 'z': 0.0}, 'mid': {'x': 18.11248989302703, 'y': -18.112488809082688, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[14] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(10.9, -21.10000128269188, 0.0), pt(18.11248989302703, -18.112488809082688, 0.0), pt(21.10000071260656, -10.899998230934056, 0.0))
        curves[14] = arc
    # Curve 15: arc
    c_desc = {'id': 15, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 5.1, 'start': {'x': 21.099999999999994, 'y': 16.00000013510386, 'z': 0.0}, 'end': {'x': 10.900000000000002, 'y': 16.00000015199185, 'z': 0.0}, 'center': {'x': 16.0, 'y': 16.0, 'z': 0.0}, 'mid': {'x': 16.00000000189974, 'y': 21.099999999999994, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[15] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(21.099999999999994, 16.00000013510386, 0.0), pt(16.00000000189974, 21.099999999999994, 0.0), pt(10.900000000000002, 16.00000015199185, 0.0))
        curves[15] = arc
    # Curve 16: arc
    c_desc = {'id': 16, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 10.1, 'start': {'x': 0.7999979310567455, 'y': -10.900000000000002, 'z': 0.0}, 'end': {'x': 10.900000605017237, 'y': -0.7999985011419941, 'z': 0.0}, 'center': {'x': 0.7999988051556817, 'y': -0.7999982001384781, 'z': 0.0}, 'mid': {'x': 7.9417781523726605, 'y': -7.941778378278367, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[16] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(0.7999979310567455, -10.900000000000002, 0.0), pt(7.9417781523726605, -7.941778378278367, 0.0), pt(10.900000605017237, -0.7999985011419941, 0.0))
        curves[16] = arc

    # 2. Points
    points[0] = sketch.originPoint
    points[1] = getattr(curves.get(13), "centerSketchPoint", None)
    points[2] = getattr(curves.get(15), "centerSketchPoint", None)
    points[3] = getattr(curves.get(13), "startSketchPoint", None)
    points[4] = getattr(curves.get(13), "endSketchPoint", None)
    points[5] = getattr(curves.get(14), "startSketchPoint", None)
    points[6] = getattr(curves.get(14), "endSketchPoint", None)
    points[7] = getattr(curves.get(14), "centerSketchPoint", None)
    points[8] = getattr(curves.get(15), "startSketchPoint", None)
    points[9] = getattr(curves.get(15), "endSketchPoint", None)
    points[10] = getattr(curves.get(16), "endSketchPoint", None)
    points[11] = getattr(curves.get(16), "startSketchPoint", None)
    points[12] = getattr(curves.get(16), "centerSketchPoint", None)
    points[13] = pts.add(pt(21.1, 8.9489, 0.0))
    points[14] = getattr(curves.get(10), "startSketchPoint", None)
    points[15] = getattr(curves.get(9), "endSketchPoint", None)
    points[16] = getattr(curves.get(8), "startSketchPoint", None)
    points[17] = getattr(curves.get(10), "endSketchPoint", None)
    points[18] = getattr(curves.get(9), "startSketchPoint", None)
    sp_19 = pts.add(pt(16.1, 1.4489, 0.0))
    apply_midpoint(gc, sp_19, curves.get(10))
    points[19] = sp_19

    # 3. Geometric Constraints
    try:
        if 5 in curves and 1 in curves:
            gc.addPerpendicular(curves[5], curves[1])
    except:
        pass
    try:
        if 6 in curves:
            gc.addHorizontal(curves[6])
    except:
        pass
    try:
        if 7 in curves:
            gc.addVertical(curves[7])
    except:
        pass
    try:
        if 8 in curves:
            gc.addHorizontal(curves[8])
    except:
        pass
    try:
        if 9 in curves:
            gc.addVertical(curves[9])
    except:
        pass
    try:
        apply_midpoint(gc, points.get(19), curves.get(10))
    except:
        pass

    # 4. Dimensions
    try:
        e1, e2 = points.get(13), points.get(15)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(24.755706285730593, -0.08738749205341234, 0.0))
            dim.parameter.expression = "15 mm"
    except:
        pass
    try:
        e1, e2 = points.get(14), points.get(16)
        if e1 and e2:
            dim = dims.addDistanceDimension(e1, e2, adsk.fusion.DimensionOrientations.AlignedDimensionOrientation, pt(19.317671408796077, 10.784543583257104, 0.0))
            dim.parameter.expression = "10 mm"
    except:
        pass
    ctx.register("Sketch3", sketch, curves, points)

# ==============================================================================
# STEP 3: EXTRUDE "Extrude3"
# ==============================================================================
def build_step_3_Extrude3(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch3")
    curves = ctx.curves.get("Sketch3", {})
    target_profiles = [{'area_mm2': 75.0, 'centroid': {'x': 17.7667, 'y': -1.0511, 'z': 0.0}, 'outer_curve_ids': [1, 6, 10], 'inner_loops_count': 0}, {'area_mm2': 75.0, 'centroid': {'x': 14.4333, 'y': 3.9489, 'z': 0.0}, 'outer_curve_ids': [5, 7, 10], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = 0
    if root_comp.bRepBodies.count == 0 and op in (0, 1, 2):
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(1.0))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude3"

# ==============================================================================
# STEP 4: SKETCH "Sketch4"
# ==============================================================================
def build_step_4_Sketch4(root_comp, ctx):
    # Planar attachment
    plane_info = {'plane': 'XZ', 'type': 'FACE', 'normal': {'x': 0.0, 'y': -1.0, 'z': 0.0}, 'origin': {'x': 0.0, 'y': -6.0511, 'z': 0.0}, 'offset_mm': -6.0511, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    if face:
        sketch = root_comp.sketches.add(face)
    else:
        plane = resolve_canonical_plane(root_comp, "XZ")
        sketch = root_comp.sketches.add(plane)
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

    # 1. Create Curves
    # Curve 0: line
    c_desc = {'id': 0, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 11.100000186790144, 'y': 4.0, 'z': 0.0}, 'end': {'x': 21.100000584154426, 'y': 4.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[0] = matched_c
    else:
        l = lines.addByTwoPoints(pt(11.100000186790144, 4.0, 0.0), pt(21.100000584154426, 4.0, 0.0))
        curves[0] = l
    # Curve 1: line
    c_desc = {'id': 1, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 21.100000584154426, 'y': 4.0, 'z': 0.0}, 'end': {'x': 21.100000584154426, 'y': 14.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[1] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.100000584154426, 4.0, 0.0), pt(21.100000584154426, 14.0, 0.0))
        curves[1] = l
    # Curve 2: line
    c_desc = {'id': 2, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 21.100000584154426, 'y': 14.0, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': 14.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[2] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.100000584154426, 14.0, 0.0), pt(11.100000186790144, 14.0, 0.0))
        curves[2] = l
    # Curve 3: line
    c_desc = {'id': 3, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 10.0, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': 11.100000186790144, 'y': 14.0, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': 4.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[3] = matched_c
    else:
        l = lines.addByTwoPoints(pt(11.100000186790144, 14.0, 0.0), pt(11.100000186790144, 4.0, 0.0))
        curves[3] = l
    # Curve 4: line
    c_desc = {'id': 4, 'type': 'line', 'is_reference': False, 'is_construction': False, 'length_mm': 14.1421, 'is_horizontal': False, 'is_vertical': False, 'start': {'x': 21.100000584154426, 'y': 14.0, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': 4.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[4] = matched_c
    else:
        l = lines.addByTwoPoints(pt(21.100000584154426, 14.0, 0.0), pt(11.100000186790144, 4.0, 0.0))
        curves[4] = l
    # Curve 5: circle
    c_desc = {'id': 5, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 3.65, 'diameter_mm': 7.3, 'center': {'x': 16.100000385472285, 'y': 9.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[5] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(16.100000385472285, 9.0, 0.0), 3.65 * 0.1)
        curves[5] = cir
    # Curve 6: arc
    c_desc = {'id': 6, 'type': 'arc', 'is_reference': False, 'is_construction': False, 'radius_mm': 5.0, 'start': {'x': 21.100000584154426, 'y': 9.0, 'z': 0.0}, 'end': {'x': 11.100000186790144, 'y': 9.0, 'z': 0.0}, 'center': {'x': 16.100000385472285, 'y': 8.999999801317852, 'z': 0.0}, 'mid': {'x': 16.100000376743427, 'y': 14.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[6] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(21.100000584154426, 9.0, 0.0), pt(16.100000376743427, 14.0, 0.0), pt(11.100000186790144, 9.0, 0.0))
        curves[6] = arc

    # 2. Points
    points[0] = sketch.originPoint
    points[1] = getattr(curves.get(3), "endSketchPoint", None)
    points[2] = getattr(curves.get(1), "startSketchPoint", None)
    points[3] = getattr(curves.get(2), "startSketchPoint", None)
    points[4] = getattr(curves.get(3), "startSketchPoint", None)
    points[5] = getattr(curves.get(4), "startSketchPoint", None)
    points[6] = getattr(curves.get(4), "endSketchPoint", None)
    sp_7 = pts.add(pt(16.1, 9.0, 0.0))
    apply_midpoint(gc, sp_7, curves.get(4))
    points[7] = sp_7
    points[8] = getattr(curves.get(5), "centerSketchPoint", None)
    sp_9 = pts.add(pt(11.1, 9.0, 0.0))
    apply_midpoint(gc, sp_9, curves.get(3))
    points[9] = sp_9
    sp_10 = pts.add(pt(21.1, 9.0, 0.0))
    apply_midpoint(gc, sp_10, curves.get(1))
    points[10] = sp_10
    sp_11 = pts.add(pt(16.1, 14.0, 0.0))
    apply_midpoint(gc, sp_11, curves.get(2))
    points[11] = sp_11
    points[12] = getattr(curves.get(6), "endSketchPoint", None)
    points[13] = getattr(curves.get(6), "startSketchPoint", None)
    points[14] = getattr(curves.get(6), "centerSketchPoint", None)

    # 3. Geometric Constraints
    try:
        apply_midpoint(gc, points.get(7), curves.get(4))
    except:
        pass
    try:
        apply_midpoint(gc, points.get(10), curves.get(1))
    except:
        pass
    try:
        apply_midpoint(gc, points.get(9), curves.get(3))
    except:
        pass
    try:
        apply_midpoint(gc, points.get(11), curves.get(2))
    except:
        pass
    try:
        if 6 in curves and 2 in curves:
            gc.addTangent(curves[6], curves[2])
    except:
        pass

    # 4. Dimensions
    try:
        if 5 in curves:
            dim = dims.addDiameterDimension(curves[5], pt(23.88127783176686, 10.746457885497131, 0.0))
            dim.parameter.expression = "7.3 mm"
    except:
        pass
    ctx.register("Sketch4", sketch, curves, points)

# ==============================================================================
# STEP 5: EXTRUDE "Extrude4"
# ==============================================================================
def build_step_5_Extrude4(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch4")
    curves = ctx.curves.get("Sketch4", {})
    target_profiles = [{'area_mm2': 2.6825, 'centroid': {'x': 19.3169, 'y': 13.5494, 'z': 0.0}, 'outer_curve_ids': [2, 4, 6], 'inner_loops_count': 0}, {'area_mm2': 2.6825, 'centroid': {'x': 20.6494, 'y': 12.2169, 'z': 0.0}, 'outer_curve_ids': [1, 4, 6], 'inner_loops_count': 0}, {'area_mm2': 5.365, 'centroid': {'x': 12.2168, 'y': 12.8832, 'z': 0.0}, 'outer_curve_ids': [2, 3, 6], 'inner_loops_count': 0}, {'area_mm2': 20.9269, 'centroid': {'x': 17.1954, 'y': 7.9046, 'z': 0.0}, 'outer_curve_ids': [4, 5], 'inner_loops_count': 0}, {'area_mm2': 20.9269, 'centroid': {'x': 15.0046, 'y': 10.0954, 'z': 0.0}, 'outer_curve_ids': [4, 5], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = 1
    if root_comp.bRepBodies.count == 0 and op in (0, 1, 2):
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-1.5))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude4"

# ==============================================================================
# STEP 6: SKETCH "Sketch8"
# ==============================================================================
def build_step_6_Sketch8(root_comp, ctx):
    # Planar attachment
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 4.0}, 'offset_mm': 4.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    if face:
        sketch = root_comp.sketches.add(face)
    else:
        plane = resolve_canonical_plane(root_comp, "XY")
        sketch = root_comp.sketches.add(plane)
    sketch.name = "Sketch8"
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
    # Curve 0: circle
    c_desc = {'id': 0, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 3.0, 'diameter_mm': 6.0, 'center': {'x': 16.10000018679014, 'y': 1.4489077759037672, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[0] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(16.10000018679014, 1.4489077759037672, 0.0), 3.0 * 0.1)
        curves[0] = cir

    # 2. Points
    points[0] = sketch.originPoint
    points[1] = pts.add(pt(16.1, 1.4489, 0.0))
    points[2] = getattr(curves.get(0), "centerSketchPoint", None)

    # 3. Geometric Constraints

    # 4. Dimensions
    try:
        if 0 in curves:
            dim = dims.addDiameterDimension(curves[0], pt(15.506078035017598, 2.8263171114441765, 0.0))
            dim.parameter.expression = "6 mm"
    except:
        pass
    ctx.register("Sketch8", sketch, curves, points)

# ==============================================================================
# STEP 7: EXTRUDE "Extrude6"
# ==============================================================================
def build_step_7_Extrude6(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch8")
    curves = ctx.curves.get("Sketch8", {})
    target_profiles = [{'area_mm2': 28.2743, 'centroid': {'x': 16.1, 'y': 1.4489, 'z': 0.0}, 'outer_curve_ids': [0], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = 3
    if root_comp.bRepBodies.count == 0 and op in (0, 1, 2):
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.25))
    ext_in.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(0.9))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude6"

# ==============================================================================
# STEP 8: SKETCH "Sketch7"
# ==============================================================================
def build_step_8_Sketch7(root_comp, ctx):
    # Planar attachment
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': -1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 0.0}, 'offset_mm': 0.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    if face:
        sketch = root_comp.sketches.add(face)
    else:
        plane = resolve_canonical_plane(root_comp, "XY")
        sketch = root_comp.sketches.add(plane)
    sketch.name = "Sketch7"
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
    # Curve 0: line
    c_desc = {'id': 0, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 16.8, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': 16.000000231407444, 'y': -10.900000000000002, 'z': 0.0}, 'end': {'x': -0.7999979310567462, 'y': -10.900000000000007, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[0] = matched_c
    else:
        l = lines.addByTwoPoints(pt(16.000000231407444, -10.900000000000002, 0.0), pt(-0.7999979310567462, -10.900000000000007, 0.0))
        curves[0] = l
    # Curve 1: line
    c_desc = {'id': 1, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 16.8, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': -10.90000060501724, 'y': -0.7999985011419929, 'z': 0.0}, 'end': {'x': -10.900000000000002, 'y': 16.00000015199185, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[1] = matched_c
    else:
        l = lines.addByTwoPoints(pt(-10.90000060501724, -0.7999985011419929, 0.0), pt(-10.900000000000002, 16.00000015199185, 0.0))
        curves[1] = l
    # Curve 2: line
    c_desc = {'id': 2, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 26.9, 'is_horizontal': False, 'is_vertical': True, 'start': {'x': -21.099999999999998, 'y': 16.000000132358853, 'z': 0.0}, 'end': {'x': -21.100000712606555, 'y': -10.899998230934058, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[2] = matched_c
    else:
        l = lines.addByTwoPoints(pt(-21.099999999999998, 16.000000132358853, 0.0), pt(-21.100000712606555, -10.899998230934058, 0.0))
        curves[2] = l
    # Curve 3: line
    c_desc = {'id': 3, 'type': 'line', 'is_reference': True, 'is_construction': False, 'length_mm': 26.9, 'is_horizontal': True, 'is_vertical': False, 'start': {'x': -10.9, 'y': -21.10000128269189, 'z': 0.0}, 'end': {'x': 16.000000243186935, 'y': -21.09999999999999, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[3] = matched_c
    else:
        l = lines.addByTwoPoints(pt(-10.9, -21.10000128269189, 0.0), pt(16.000000243186935, -21.09999999999999, 0.0))
        curves[3] = l
    # Curve 4: circle
    c_desc = {'id': 4, 'type': 'circle', 'is_reference': True, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': 16.0, 'y': -16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[4] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(16.0, -16.0, 0.0), 1.7 * 0.1)
        curves[4] = cir
    # Curve 5: circle
    c_desc = {'id': 5, 'type': 'circle', 'is_reference': True, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': -16.0, 'y': 16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[5] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(-16.0, 16.0, 0.0), 1.7 * 0.1)
        curves[5] = cir
    # Curve 6: circle
    c_desc = {'id': 6, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 1.7, 'diameter_mm': 3.4, 'center': {'x': -16.10000018679014, 'y': 1.4489077759037672, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[6] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(-16.10000018679014, 1.4489077759037672, 0.0), 1.7 * 0.1)
        curves[6] = cir
    # Curve 7: arc
    c_desc = {'id': 7, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 5.1, 'start': {'x': 16.000000243186935, 'y': -21.09999999999999, 'z': 0.0}, 'end': {'x': 16.000000231407444, 'y': -10.900000000000002, 'z': 0.0}, 'center': {'x': 16.0, 'y': -16.0, 'z': 0.0}, 'mid': {'x': 21.099999999999994, 'y': -15.999999991048227, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[7] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(16.000000243186935, -21.09999999999999, 0.0), pt(21.099999999999994, -15.999999991048227, 0.0), pt(16.000000231407444, -10.900000000000002, 0.0))
        curves[7] = arc
    # Curve 8: arc
    c_desc = {'id': 8, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 10.1, 'start': {'x': -10.90000060501724, 'y': -0.7999985011419929, 'z': 0.0}, 'end': {'x': -0.7999979310567462, 'y': -10.900000000000007, 'z': 0.0}, 'center': {'x': -0.7999988051556772, 'y': -0.7999982001384787, 'z': 0.0}, 'mid': {'x': -7.9417781523726605, 'y': -7.941778378278368, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[8] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(-10.90000060501724, -0.7999985011419929, 0.0), pt(-7.9417781523726605, -7.941778378278368, 0.0), pt(-0.7999979310567462, -10.900000000000007, 0.0))
        curves[8] = arc
    # Curve 9: arc
    c_desc = {'id': 9, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 5.1, 'start': {'x': -10.900000000000002, 'y': 16.00000015199185, 'z': 0.0}, 'end': {'x': -21.099999999999998, 'y': 16.000000132358853, 'z': 0.0}, 'center': {'x': -16.0, 'y': 16.0, 'z': 0.0}, 'mid': {'x': -16.00000001498825, 'y': 21.1, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[9] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(-10.900000000000002, 16.00000015199185, 0.0), pt(-16.00000001498825, 21.1, 0.0), pt(-21.099999999999998, 16.000000132358853, 0.0))
        curves[9] = arc
    # Curve 10: arc
    c_desc = {'id': 10, 'type': 'arc', 'is_reference': True, 'is_construction': False, 'radius_mm': 10.2, 'start': {'x': -21.100000712606555, 'y': -10.899998230934058, 'z': 0.0}, 'end': {'x': -10.9, 'y': -21.10000128269189, 'z': 0.0}, 'center': {'x': -10.8999979310563, 'y': -10.899998501141834, 'z': 0.0}, 'mid': {'x': -18.112489893027025, 'y': -18.112488809082688, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[10] = matched_c
    else:
        arc = arcs.addByThreePoints(pt(-21.100000712606555, -10.899998230934058, 0.0), pt(-18.112489893027025, -18.112488809082688, 0.0), pt(-10.9, -21.10000128269189, 0.0))
        curves[10] = arc

    # 2. Points
    points[0] = sketch.originPoint
    points[1] = getattr(curves.get(7), "centerSketchPoint", None)
    points[2] = getattr(curves.get(9), "centerSketchPoint", None)
    points[3] = getattr(curves.get(7), "startSketchPoint", None)
    points[4] = getattr(curves.get(7), "endSketchPoint", None)
    points[5] = getattr(curves.get(8), "endSketchPoint", None)
    points[6] = getattr(curves.get(8), "startSketchPoint", None)
    points[7] = getattr(curves.get(8), "centerSketchPoint", None)
    points[8] = getattr(curves.get(9), "startSketchPoint", None)
    points[9] = getattr(curves.get(9), "endSketchPoint", None)
    points[10] = getattr(curves.get(10), "startSketchPoint", None)
    points[11] = getattr(curves.get(10), "endSketchPoint", None)
    points[12] = getattr(curves.get(10), "centerSketchPoint", None)
    points[13] = pts.add(pt(-16.1, 1.4489, 0.0))
    points[14] = getattr(curves.get(6), "centerSketchPoint", None)

    # 3. Geometric Constraints

    # 4. Dimensions
    try:
        if 6 in curves:
            dim = dims.addDiameterDimension(curves[6], pt(-19.523625155497083, 2.8878610915615566, 0.0))
            dim.parameter.expression = "3.4 mm"
    except:
        pass
    ctx.register("Sketch7", sketch, curves, points)

# ==============================================================================
# STEP 9: EXTRUDE "Extrude7"
# ==============================================================================
def build_step_9_Extrude7(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch7")
    curves = ctx.curves.get("Sketch7", {})
    target_profiles = [{'area_mm2': 9.0792, 'centroid': {'x': -16.1, 'y': 1.4489, 'z': 0.0}, 'outer_curve_ids': [6], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = 1
    if root_comp.bRepBodies.count == 0 and op in (0, 1, 2):
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    ext_in = root_comp.features.extrudeFeatures.createInput(prof_input, op)
    ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByReal(-0.8))
    ext_in.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(-1.0))
    ext_feat = root_comp.features.extrudeFeatures.add(ext_in)
    ext_feat.name = "Extrude7"

# ==============================================================================
# STEP 10: SKETCH "Sketch9"
# ==============================================================================
def build_step_10_Sketch9(root_comp, ctx):
    # Planar attachment
    plane_info = {'plane': 'XY', 'type': 'FACE', 'normal': {'x': 0.0, 'y': 0.0, 'z': 1.0}, 'origin': {'x': 0.0, 'y': 0.0, 'z': 4.0}, 'offset_mm': 4.0, 'body_name': 'Body1'}
    face = find_matching_face(root_comp, plane_info)
    if face:
        sketch = root_comp.sketches.add(face)
    else:
        plane = resolve_canonical_plane(root_comp, "XY")
        sketch = root_comp.sketches.add(plane)
    sketch.name = "Sketch9"
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
    # Curve 0: circle
    c_desc = {'id': 0, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 6.0, 'diameter_mm': 12.0, 'center': {'x': 16.0, 'y': 16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[0] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(16.0, 16.0, 0.0), 6.0 * 0.1)
        curves[0] = cir
    # Curve 1: circle
    c_desc = {'id': 1, 'type': 'circle', 'is_reference': False, 'is_construction': False, 'radius_mm': 6.0, 'diameter_mm': 12.0, 'center': {'x': -16.0, 'y': -16.0, 'z': 0.0}}
    matched_c = next((ec for ec in existing if curve_matches(c_desc, ec)), None)
    if matched_c:
        curves[1] = matched_c
    else:
        cir = circles.addByCenterRadius(pt(-16.0, -16.0, 0.0), 6.0 * 0.1)
        curves[1] = cir

    # 2. Points
    points[0] = sketch.originPoint
    points[1] = pts.add(pt(16.0, 16.0, 0.0))
    points[2] = pts.add(pt(-16.0, -16.0, 0.0))
    points[3] = getattr(curves.get(0), "centerSketchPoint", None)
    points[4] = getattr(curves.get(1), "centerSketchPoint", None)

    # 3. Geometric Constraints
    try:
        if 0 in curves and 1 in curves:
            gc.addEqual(curves[0], curves[1])
    except:
        pass

    # 4. Dimensions
    try:
        if 0 in curves:
            dim = dims.addDiameterDimension(curves[0], pt(13.05825800529798, 16.588348567268238, 0.0))
            dim.parameter.expression = "12 mm"
    except:
        pass
    ctx.register("Sketch9", sketch, curves, points)

# ==============================================================================
# STEP 11: EXTRUDE "Extrude8"
# ==============================================================================
def build_step_11_Extrude8(root_comp, ctx):
    sketch = ctx.sketches.get("Sketch9")
    curves = ctx.curves.get("Sketch9", {})
    target_profiles = [{'area_mm2': 113.0973, 'centroid': {'x': 16.0, 'y': 16.0, 'z': 0.0}, 'outer_curve_ids': [0], 'inner_loops_count': 0}, {'area_mm2': 113.0973, 'centroid': {'x': -16.0, 'y': -16.0, 'z': 0.0}, 'outer_curve_ids': [1], 'inner_loops_count': 0}]
    matched_profs = find_matching_profiles(sketch, target_profiles, curves)
    prof_input = matched_profs.item(0) if matched_profs.count == 1 else matched_profs
    op = 1
    if root_comp.bRepBodies.count == 0 and op in (0, 1, 2):
        op = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
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
        ui.messageBox("REBUILD COMPLETE!\n\nModel 'ai stylus holder' reconstructed successfully with 12 steps.", "Success")
    except:
        if ui:
            ui.messageBox(f"Rebuild failed:\n{traceback.format_exc()}")
        else:
            print(traceback.format_exc())
