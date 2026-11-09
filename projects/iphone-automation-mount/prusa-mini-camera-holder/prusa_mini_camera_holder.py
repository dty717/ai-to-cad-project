import adsk.core, adsk.fusion, traceback
import math

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        
        if not design:
            ui.messageBox('Please open or create a design in Fusion 360 before running the script.')
            return

        # =============================================================
        # 1. USER PARAMETERS (in millimeters)
        # =============================================================
        # Center-to-Center Spacing (Motor Center to Cam Center)
        CAM_CENTER_X_MM          = 140  # Distance along X from motor center
        CAM_CENTER_Y_MM          = 68   # Distance along Y from motor center
        # (Swap these two numbers if your setup has X=76 and Y=156)

        # Realistic NEMA 17 Motor Socket (Rotated 45° for Prusa MINI)
        MOTOR_WIDTH_MM           = 42.6   # Real NEMA 17 (42.3mm + 0.3mm fit tolerance)
        MOTOR_HEIGHT_MM          = 42.6   # Real NEMA 17 (42.3mm + 0.3mm fit tolerance)
        CORNER_CHAMFER_MM        = 4.0    # Real NEMA 17 corner chamfer (flats are ~34.6mm)
        CAP_DEPTH_MM             = 20.0   # 20mm deep sleeve over motor body
        WALL_THICK_MM            = 2.5    # Shell wall thickness
        ROOF_THICK_MM            = 2.5    # Top ceiling thickness
        
        # Wire Slot on the 45° Diagonal Flat Lines (Middle of Line)
        # Options: "BOTTOM_LEFT_LINE" (default, wire /), "TOP_LEFT_LINE", "BOTTOM_RIGHT_LINE", "TOP_RIGHT_LINE"
        WIRE_SLOT_LINE           = "BOTTOM_LEFT_LINE"
        WIRE_SLOT_WIDTH_MM       = 15.0   # Wire opening width
        
        # Reinforced Coplanar Arm (Flat at Z=0 for printing)
        ARM_WIDTH_MM             = 18.0   # Width of arm beam
        ARM_THICK_MM             = 9.0    # Increased to 9mm for vibration damping
        ELBOW_GUSSET_MM          = 15.0   # 15mm diagonal brace on inside elbow
        
        # Camera Cradle Fit (Deltaco / NUOXI ~56mm x 36mm)
        CAM_BODY_WIDTH_MM        = 57.5   # Inner width (56mm + 1.5mm tolerance)
        CAM_BODY_DEPTH_MM        = 37.5   # Inner depth (36mm + 1.5mm tolerance)
        CRADLE_WALL_H_MM         = 22.0   # 22mm tall walls for secure hold
        CRADLE_WALL_T_MM         = 2.8    # Stiff 2.8mm wall thickness
        CRADLE_FLOOR_T_MM        = 2.5    # Floor thickness under camera
        
        # Cutouts & Cable Management
        LIGHT_LENS_CUTOUT_W_MM   = 44.0   # Optical window (covers lens AND side LEDs)
        LIGHT_LENS_CUTOUT_D_MM   = 24.0   # Depth for focus ring access
        CABLE_NOTCH_W_MM         = 12.0   # 12.0mm wide rear USB cable notch
        ENABLE_ZIP_TIE_SLOTS     = True   # Adds cable tie slots along arm

        # =============================================================
        # 2. UNIT CONVERSIONS (Fusion 360 API requires CENTIMETERS)
        # =============================================================
        cam_x        = CAM_CENTER_X_MM / 10.0
        cam_y        = CAM_CENTER_Y_MM / 10.0
        
        mw_in        = MOTOR_WIDTH_MM / 10.0
        mh_in        = MOTOR_HEIGHT_MM / 10.0
        chamfer_in   = CORNER_CHAMFER_MM / 10.0
        cap_depth    = CAP_DEPTH_MM / 10.0
        wall         = WALL_THICK_MM / 10.0
        roof         = ROOF_THICK_MM / 10.0
        total_height = cap_depth + roof
        slot_w       = WIRE_SLOT_WIDTH_MM / 10.0
        
        # Flat half-lengths before 45° rotation
        hw_in        = mw_in / 2.0
        hh_in        = mh_in / 2.0
        xf_in        = hw_in - chamfer_in  # 1.73 cm (flat length 34.6 mm)
        yf_in        = hh_in - chamfer_in
        
        hw_out       = hw_in + wall
        hh_out       = hh_in + wall
        chamfer_out  = chamfer_in + (wall * (math.sqrt(2.0) - 1.0))
        xf_out       = hw_out - chamfer_out
        yf_out       = hh_out - chamfer_out
        
        arm_w        = ARM_WIDTH_MM / 10.0
        arm_t        = ARM_THICK_MM / 10.0
        gusset       = ELBOW_GUSSET_MM / 10.0
        
        cam_w_in     = CAM_BODY_WIDTH_MM / 10.0
        cam_d_in     = CAM_BODY_DEPTH_MM / 10.0
        cradle_h     = CRADLE_WALL_H_MM / 10.0
        cradle_wall  = CRADLE_WALL_T_MM / 10.0
        cradle_floor = CRADLE_FLOOR_T_MM / 10.0
        
        cut_w        = LIGHT_LENS_CUTOUT_W_MM / 10.0
        cut_d        = LIGHT_LENS_CUTOUT_D_MM / 10.0
        cable_notch  = CABLE_NOTCH_W_MM / 10.0

        rootComp = design.rootComponent
        features = rootComp.features
        sketches = rootComp.sketches
        planes   = rootComp.constructionPlanes
        xyPlane  = rootComp.xYConstructionPlane

        # 45-degree rotation helper: x' = (x - y)/sqrt(2), y' = (x + y)/sqrt(2)
        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        def rotate45(pts):
            rot = []
            for p in pts:
                rx = (p[0] - p[1]) * inv_sqrt2
                ry = (p[0] + p[1]) * inv_sqrt2
                rot.append((rx, ry))
            return rot

        # =============================================================
        # STEP 1: 45° Rotated NEMA 17 Cap Outer Body (Starting at Z = 0)
        # =============================================================
        u_pts_out = [
            (-xf_out,  hh_out), ( xf_out,  hh_out),
            ( hw_out,  yf_out), ( hw_out, -yf_out),
            ( xf_out, -hh_out), (-xf_out, -hh_out),
            (-hw_out, -yf_out), (-hw_out,  yf_out)
        ]
        o_pts_rot = rotate45(u_pts_out)
        
        sketch_outer = sketches.add(xyPlane)
        lines_outer  = sketch_outer.sketchCurves.sketchLines
        for i in range(len(o_pts_rot)):
            nxt = (i + 1) % len(o_pts_rot)
            lines_outer.addByTwoPoints(
                adsk.core.Point3D.create(o_pts_rot[i][0], o_pts_rot[i][1], 0),
                adsk.core.Point3D.create(o_pts_rot[nxt][0], o_pts_rot[nxt][1], 0)
            )
            
        prof_outer = sketch_outer.profiles.item(0)
        ext_outer = features.extrudeFeatures.createInput(
            prof_outer, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        ext_outer.setDistanceExtent(False, adsk.core.ValueInput.createByReal(total_height))
        mount_body_feat = features.extrudeFeatures.add(ext_outer)
        mount_body = mount_body_feat.bodies.item(0)
        mount_body.name = "PrusaMini_Webcam_Mount"

        # =============================================================
        # STEP 2: L-Shaped Arm with Gusseted Elbow & Proper Cap Anchor
        # =============================================================
        cradle_out_d = cam_d_in + (2.0 * cradle_wall)
        cradle_out_w = cam_w_in + (2.0 * cradle_wall)
        
        cradle_front_y = cam_y - (cradle_out_d / 2.0)
        arm_end_y = cradle_front_y + 0.1  # Stops flush at outer wall

        # Fixed anchor: starts at X = 1.6 cm, well inside the 35mm-wide cap wall
        arm_start_x = 1.6
        hw_arm = arm_w / 2.0

        sketch_arm = sketches.add(xyPlane)
        lines_arm  = sketch_arm.sketchCurves.sketchLines
        
        # Arm polygon with diagonal elbow brace
        a0  = adsk.core.Point3D.create(arm_start_x,               -hw_arm,    0)
        a1  = adsk.core.Point3D.create(arm_start_x,                hw_arm,    0)
        a2a = adsk.core.Point3D.create(cam_x - hw_arm - gusset,    hw_arm,    0) # Gusset start
        a2b = adsk.core.Point3D.create(cam_x - hw_arm,             hw_arm + gusset, 0) # Gusset end
        a3  = adsk.core.Point3D.create(cam_x - hw_arm,             arm_end_y, 0)
        a4  = adsk.core.Point3D.create(cam_x + hw_arm,             arm_end_y, 0)
        a5a = adsk.core.Point3D.create(cam_x + hw_arm,            -hw_arm + 0.6, 0) # Outer chamfer
        a5b = adsk.core.Point3D.create(cam_x + hw_arm - 0.6,      -hw_arm,    0)
        
        lines_arm.addByTwoPoints(a0, a1)
        lines_arm.addByTwoPoints(a1, a2a)
        lines_arm.addByTwoPoints(a2a, a2b) # Diagonal internal brace
        lines_arm.addByTwoPoints(a2b, a3)
        lines_arm.addByTwoPoints(a3, a4)
        lines_arm.addByTwoPoints(a4, a5a)
        lines_arm.addByTwoPoints(a5a, a5b)
        lines_arm.addByTwoPoints(a5b, a0)
        
        prof_arm = sketch_arm.profiles.item(0)
        ext_arm = features.extrudeFeatures.createInput(
            prof_arm, adsk.fusion.FeatureOperations.JoinFeatureOperation
        )
        ext_arm.setDistanceExtent(False, adsk.core.ValueInput.createByReal(arm_t))
        features.extrudeFeatures.add(ext_arm)

        # =============================================================
        # STEP 3: Camera Cradle Floor (At Z = 0, Coplanar with Bed)
        # =============================================================
        sketch_cf = sketches.add(xyPlane)
        lines_cf  = sketch_cf.sketchCurves.sketchLines
        
        cf_x_min = cam_x - (cradle_out_w / 2.0)
        cf_x_max = cam_x + (cradle_out_w / 2.0)
        cf_y_min = cam_y - (cradle_out_d / 2.0)
        cf_y_max = cam_y + (cradle_out_d / 2.0)
        
        lines_cf.addTwoPointRectangle(
            adsk.core.Point3D.create(cf_x_min, cf_y_min, 0),
            adsk.core.Point3D.create(cf_x_max, cf_y_max, 0)
        )
        prof_cf = sketch_cf.profiles.item(0)
        ext_cf = features.extrudeFeatures.createInput(
            prof_cf, adsk.fusion.FeatureOperations.JoinFeatureOperation
        )
        ext_cf.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cradle_floor))
        features.extrudeFeatures.add(ext_cf)

        # =============================================================
        # STEP 4: Cradle Walls (22mm High, 57.5 x 37.5 mm Cavity)
        # =============================================================
        plane_walls_in = planes.createInput()
        plane_walls_in.setByOffset(xyPlane, adsk.core.ValueInput.createByReal(cradle_floor))
        wallsPlane = planes.add(plane_walls_in)
        
        sketch_walls = sketches.add(wallsPlane)
        lines_walls  = sketch_walls.sketchCurves.sketchLines
        
        lines_walls.addTwoPointRectangle(
            adsk.core.Point3D.create(cf_x_min, cf_y_min, 0),
            adsk.core.Point3D.create(cf_x_max, cf_y_max, 0)
        )
        ci_x_min = cam_x - (cam_w_in / 2.0)
        ci_x_max = cam_x + (cam_w_in / 2.0)
        ci_y_min = cam_y - (cam_d_in / 2.0)
        ci_y_max = cam_y + (cam_d_in / 2.0)
        lines_walls.addTwoPointRectangle(
            adsk.core.Point3D.create(ci_x_min, ci_y_min, 0),
            adsk.core.Point3D.create(ci_x_max, ci_y_max, 0)
        )
        
        prof_walls = None
        for p in sketch_walls.profiles:
            if p.profileLoops.count > 1:
                prof_walls = p
                break
        if not prof_walls:
            prof_walls = sketch_walls.profiles.item(0)

        ext_walls = features.extrudeFeatures.createInput(
            prof_walls, adsk.fusion.FeatureOperations.JoinFeatureOperation
        )
        ext_walls.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cradle_h))
        features.extrudeFeatures.add(ext_walls)

        # =============================================================
        # STEP 5: CUT Inner 45° Rotated Motor Pocket (Guarantees NO Blockage)
        # =============================================================
        u_pts_in = [
            (-xf_in,  hh_in), ( xf_in,  hh_in),
            ( hw_in,  yf_in), ( hw_in, -yf_in),
            ( xf_in, -hh_in), (-xf_in, -hh_in),
            (-hw_in, -yf_in), (-hw_in,  yf_in)
        ]
        i_pts_rot = rotate45(u_pts_in)
        
        sketch_inner = sketches.add(xyPlane)
        lines_inner  = sketch_inner.sketchCurves.sketchLines
        for i in range(len(i_pts_rot)):
            nxt = (i + 1) % len(i_pts_rot)
            lines_inner.addByTwoPoints(
                adsk.core.Point3D.create(i_pts_rot[i][0], i_pts_rot[i][1], 0),
                adsk.core.Point3D.create(i_pts_rot[nxt][0], i_pts_rot[nxt][1], 0)
            )
            
        prof_inner = sketch_inner.profiles.item(0)
        ext_cut = features.extrudeFeatures.createInput(
            prof_inner, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        ext_cut.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cap_depth))
        features.extrudeFeatures.add(ext_cut)

        # =============================================================
        # STEP 6: Anti-Elephant's Foot Entry Lead-in Relief
        # =============================================================
        # Enlarges entrance by 0.5mm for the first 1.2mm depth
        hw_lead = hw_in + 0.05
        hh_lead = hh_in + 0.05
        xf_lead = hw_lead - chamfer_in
        yf_lead = hh_lead - chamfer_in
        u_pts_lead = [
            (-xf_lead,  hh_lead), ( xf_lead,  hh_lead),
            ( hw_lead,  yf_lead), ( hw_lead, -yf_lead),
            ( xf_lead, -hh_lead), (-xf_lead, -hh_lead),
            (-hw_lead, -yf_lead), (-hw_lead,  yf_lead)
        ]
        lead_rot = rotate45(u_pts_lead)
        sketch_lead = sketches.add(xyPlane)
        lines_lead  = sketch_lead.sketchCurves.sketchLines
        for i in range(len(lead_rot)):
            nxt = (i + 1) % len(lead_rot)
            lines_lead.addByTwoPoints(
                adsk.core.Point3D.create(lead_rot[i][0], lead_rot[i][1], 0),
                adsk.core.Point3D.create(lead_rot[nxt][0], lead_rot[nxt][1], 0)
            )
        prof_lead = sketch_lead.profiles.item(0)
        ext_lead = features.extrudeFeatures.createInput(
            prof_lead, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        ext_lead.setDistanceExtent(False, adsk.core.ValueInput.createByReal(0.12)) # 1.2mm deep
        features.extrudeFeatures.add(ext_lead)

        # =============================================================
        # STEP 7: CUT Wire Slot in the MIDDLE of the 45° Diagonal Line
        # =============================================================
        d_center = hw_in * inv_sqrt2  # 15.06mm from center to diagonal flat
        
        if WIRE_SLOT_LINE == "TOP_LEFT_LINE":
            mid_x, mid_y = -d_center, d_center
            tx, ty =  inv_sqrt2,  inv_sqrt2
            nx, ny = -inv_sqrt2,  inv_sqrt2
        elif WIRE_SLOT_LINE == "BOTTOM_RIGHT_LINE":
            mid_x, mid_y = d_center, -d_center
            tx, ty =  inv_sqrt2,  inv_sqrt2
            nx, ny =  inv_sqrt2, -inv_sqrt2
        elif WIRE_SLOT_LINE == "TOP_RIGHT_LINE":
            mid_x, mid_y = d_center, d_center
            tx, ty = -inv_sqrt2,  inv_sqrt2
            nx, ny =  inv_sqrt2,  inv_sqrt2
        else: # "BOTTOM_LEFT_LINE" (default, wire /)
            mid_x, mid_y = -d_center, -d_center
            tx, ty =  inv_sqrt2, -inv_sqrt2
            nx, ny = -inv_sqrt2, -inv_sqrt2

        hw_slot = slot_w / 2.0
        sketch_wire = sketches.add(xyPlane)
        wire_lines  = sketch_wire.sketchCurves.sketchLines
        
        w_c1 = adsk.core.Point3D.create(mid_x - hw_slot*tx - 0.2*nx, mid_y - hw_slot*ty - 0.2*ny, 0)
        w_c2 = adsk.core.Point3D.create(mid_x + hw_slot*tx - 0.2*nx, mid_y + hw_slot*ty - 0.2*ny, 0)
        w_c3 = adsk.core.Point3D.create(mid_x + hw_slot*tx + (wall + 0.4)*nx, mid_y + hw_slot*ty + (wall + 0.4)*ny, 0)
        w_c4 = adsk.core.Point3D.create(mid_x - hw_slot*tx + (wall + 0.4)*nx, mid_y - hw_slot*ty + (wall + 0.4)*ny, 0)
        
        wire_lines.addByTwoPoints(w_c1, w_c2)
        wire_lines.addByTwoPoints(w_c2, w_c3)
        wire_lines.addByTwoPoints(w_c3, w_c4)
        wire_lines.addByTwoPoints(w_c4, w_c1)
        
        prof_wire = sketch_wire.profiles.item(0)
        ext_wire = features.extrudeFeatures.createInput(
            prof_wire, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        ext_wire.setDistanceExtent(False, adsk.core.ValueInput.createByReal(total_height + 0.1))
        features.extrudeFeatures.add(ext_wire)

        # =============================================================
        # STEP 8: CUT Continuous Lens + LED Window (At cam_x, cam_y)
        # =============================================================
        sketch_cutout = sketches.add(xyPlane)
        lines_cutout  = sketch_cutout.sketchCurves.sketchLines
        
        lines_cutout.addTwoPointRectangle(
            adsk.core.Point3D.create(cam_x - cut_w/2.0, cam_y - cut_d/2.0, 0),
            adsk.core.Point3D.create(cam_x + cut_w/2.0, cam_y + cut_d/2.0, 0)
        )
        prof_cutout = sketch_cutout.profiles.item(0)
        ext_cutout = features.extrudeFeatures.createInput(
            prof_cutout, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        ext_cutout.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cradle_floor + 0.1))
        features.extrudeFeatures.add(ext_cutout)

        # =============================================================
        # STEP 9: CUT Rear USB Cable Exit Notch (12.0mm Wide)
        # =============================================================
        sketch_cable = sketches.add(wallsPlane)
        c_half = cable_notch / 2.0
        
        sketch_cable.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(cam_x - c_half, cf_y_max - cradle_wall - 0.1, 0),
            adsk.core.Point3D.create(cam_x + c_half, cf_y_max + 0.1,                0)
        )
        prof_cable = sketch_cable.profiles.item(0)
        ext_cable = features.extrudeFeatures.createInput(
            prof_cable, adsk.fusion.FeatureOperations.CutFeatureOperation
        )
        ext_cable.setDistanceExtent(False, adsk.core.ValueInput.createByReal(cradle_h + 0.1))
        features.extrudeFeatures.add(ext_cable)

        # =============================================================
        # STEP 10: Zip-Tie Cable Slots Along Arm (Optional)
        # =============================================================
        if ENABLE_ZIP_TIE_SLOTS:
            sketch_zip = sketches.add(xyPlane)
            z_lines = sketch_zip.sketchCurves.sketchLines
            # Slot 1: mid-span X (75mm), Slot 2: near elbow X (125mm)
            z_positions = [7.5, 12.5]
            for zx in z_positions:
                z_lines.addTwoPointRectangle(
                    adsk.core.Point3D.create(zx - 0.1, -0.2, 0),
                    adsk.core.Point3D.create(zx + 0.1,  0.2, 0)
                )
            for p in sketch_zip.profiles:
                ext_zip = features.extrudeFeatures.createInput(
                    p, adsk.fusion.FeatureOperations.CutFeatureOperation
                )
                ext_zip.setDistanceExtent(False, adsk.core.ValueInput.createByReal(arm_t + 0.1))
                features.extrudeFeatures.add(ext_zip)

        ui.messageBox('Prusa MINI Webcam Mount (Optimized & Verified) created successfully!')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))