import adsk.core
import adsk.fusion
import traceback
import math


def add_rounded_rectangle(lines, arcs, x1, y1, x2, y2, r):
    """Draws a closed rectangle with filleted corners on a sketch."""
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1

    max_r = min((x2 - x1) / 2.0, (y2 - y1) / 2.0)
    r = min(r, max_r)
    if r <= 0:
        lines.addTwoPointRectangle(
            adsk.core.Point3D.create(x1, y1, 0),
            adsk.core.Point3D.create(x2, y2, 0)
        )
        return

    diag = r * (1.0 - math.sqrt(2) / 2.0)

    # Bottom-Right Corner
    p_br_s = adsk.core.Point3D.create(x2 - r, y1, 0)
    p_br_m = adsk.core.Point3D.create(x2 - diag, y1 + diag, 0)
    p_br_e = adsk.core.Point3D.create(x2, y1 + r, 0)

    # Top-Right Corner
    p_tr_s = adsk.core.Point3D.create(x2, y2 - r, 0)
    p_tr_m = adsk.core.Point3D.create(x2 - diag, y2 - diag, 0)
    p_tr_e = adsk.core.Point3D.create(x2 - r, y2, 0)

    # Top-Left Corner
    p_tl_s = adsk.core.Point3D.create(x1 + r, y2, 0)
    p_tl_m = adsk.core.Point3D.create(x1 + diag, y2 - diag, 0)
    p_tl_e = adsk.core.Point3D.create(x1, y2 - r, 0)

    # Bottom-Left Corner
    p_bl_s = adsk.core.Point3D.create(x1, y1 + r, 0)
    p_bl_m = adsk.core.Point3D.create(x1 + diag, y1 + diag, 0)
    p_bl_e = adsk.core.Point3D.create(x1 + r, y1, 0)

    # Perimeter segments
    lines.addByTwoPoints(p_bl_e, p_br_s)
    arcs.addByThreePoints(p_br_s, p_br_m, p_br_e)
    lines.addByTwoPoints(p_br_e, p_tr_s)
    arcs.addByThreePoints(p_tr_s, p_tr_m, p_tr_e)
    lines.addByTwoPoints(p_tr_e, p_tl_s)
    arcs.addByThreePoints(p_tl_s, p_tl_m, p_tl_e)
    lines.addByTwoPoints(p_tl_e, p_bl_s)
    arcs.addByThreePoints(p_bl_s, p_bl_m, p_bl_e)


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # -------------------------------------------------------------
        # 1. CREATE NEW DESIGN DOCUMENT
        # -------------------------------------------------------------
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError("Failed to create or access the design document.")

        rootComp = design.rootComponent
        sketches = rootComp.sketches
        extrudes = rootComp.features.extrudeFeatures
        xyPlane = rootComp.xYConstructionPlane

        # Internal Fusion 360 units are CENTIMETERS
        mm = 0.1  # 1 mm = 0.1 cm

        # -------------------------------------------------------------
        # 2. ENVELOPE & BASE DIMENSIONS (PRUSA MINI 180x180, 2.5mm MARGIN)
        # Safe Envelope: X in [-87.5, +87.5] mm, Y in [-87.5, +87.5] mm
        # -------------------------------------------------------------
        BASE_THICK = 4.0 * mm        # 4.0 mm rigid base plate thickness
        WALL_THICK = 3.5 * mm        # 3.5 mm retaining wall thickness
        WALL_HEIGHT = 8.0 * mm       # 8.0 mm wall height (iPhone SE2 is 7.3 mm)

        # iPhone SE2 Pocket Cavity
        SE2_LEN = 139.0 * mm         # Length along X
        SE2_WID = 68.0 * mm          # Width along Y

        pocket_outer_x = SE2_LEN + 2.0 * WALL_THICK  # 146.0 mm outer width
        pocket_outer_y = SE2_WID + 2.0 * WALL_THICK  # 75.0 mm outer depth

        # Margin & Boundary coordinates
        pocket_x1 = -87.5 * mm                       # Left edge at -87.5 mm
        pocket_x2 = pocket_x1 + pocket_outer_x       # +58.5 mm
        pocket_y1 = -87.5 * mm                       # Front edge at -87.5 mm
        pocket_y2 = pocket_y1 + pocket_outer_y       # -12.5 mm

        # Arm Placed to the RIGHT of the iPhone Pocket
        arm_w = 24.0 * mm                            # Sturdy 24 mm wide arm
        arm_x1 = pocket_x2                           # +58.5 mm
        arm_x2 = arm_x1 + arm_w                      # +82.5 mm (Right design limit line)

        # Root Junction Fillet (Mount to Arm)
        MOUNT_ARM_FILLET_R = 10.0 * mm

        # Rear Mount Bar Dimensions
        mount_bar_d = 18.0 * mm                      # 18 mm mount bar depth
        mount_y2 = 82.0 * mm                         # Rear edge (+82.0 mm, Top design limit line)
        mount_y1 = mount_y2 - mount_bar_d            # +64.0 mm
        pin_y = (mount_y1 + mount_y2) / 2.0          # +73.0 mm

        # Dual alignment pin holes for Prusa Mini rear bed pins (-50mm and +50mm)
        BED_PIN_HOLE_DIA = 3.8 * mm
        BED_PIN_RADIUS = BED_PIN_HOLE_DIA / 2.0
        pin_spacing = 100.0 * mm
        hole1_x = -pin_spacing / 2.0                 # -50.0 mm
        hole2_x = pin_spacing / 2.0                  # +50.0 mm

        # Left Rounded Nose
        MOUNT_LEFT_EXT = 6.0 * mm
        mount_left_cx = hole1_x - MOUNT_LEFT_EXT     # -56.0 mm
        MOUNT_ARC_LEFT_R = mount_bar_d / 2.0         # 9.0 mm radius
        mount_left_apex_x = mount_left_cx - MOUNT_ARC_LEFT_R  # -65.0 mm

        # -------------------------------------------------------------
        # TOP-RIGHT RECTANGULAR CORNER CUT (REPLACES ARC CORNER)
        # 22 x 10 mm 90° Stepped Corner Cutout to Design Limit Lines
        # -------------------------------------------------------------
        CORNER_CUT_W = 22.0 * mm                     # 22.0 mm width along X (from arm_x2 inward)
        CORNER_CUT_D = 10.0 * mm                     # 10.0 mm depth along Y (from mount_y2 forward)

        corner_inner_x = arm_x2 - CORNER_CUT_W       # +60.5 mm
        corner_inner_y = mount_y2 - CORNER_CUT_D     # +72.0 mm

        # Arm Lightening Slot Parameters
        ARM_SLOT_ENABLE = True
        ARM_SLOT_W = 10.0 * mm                       # 10 mm wide central slot
        ARM_SLOT_Y1 = 4.0 * mm                       # Starts above pocket rear wall
        ARM_SLOT_Y2 = min(46.0 * mm, corner_inner_y - 6.0 * mm)  # 46.0 mm (26 mm solid bridge before step)

        # Inner pocket cavity boundaries
        inner_x1 = pocket_x1 + WALL_THICK            # -84.0 mm (Phone Bottom / Lightning Port)
        inner_x2 = pocket_x2 - WALL_THICK            # +55.0 mm (Phone Top)
        inner_y1 = pocket_y1 + WALL_THICK            # -84.0 mm (Phone Right Side / Front Wall)
        inner_y2 = pocket_y2 - WALL_THICK            # -16.0 mm (Phone Left Side / Rear Wall)

        # Camera Cutout (iPhone SE2 Single Lens + Flash)
        CAM_SIZE_X = 26.0 * mm
        CAM_SIZE_Y = 26.0 * mm
        cam_x2 = inner_x2                            # +55.0 mm
        cam_x1 = inner_x2 - CAM_SIZE_X               # +29.0 mm
        cam_y1 = inner_y1                            # -84.0 mm
        cam_y2 = inner_y1 + CAM_SIZE_Y               # -58.0 mm

        # 3x3 Plate Grid Parameters
        GRID_CUT_ENABLE = True
        PLATE_MARGIN = 5.0 * mm
        GRID_RIB_W = 5.0 * mm
        GRID_CORNER_R = 3.5 * mm

        # Wall Cutouts (iPhone SE2 Side Button & Controls)
        WALL_LIP_HEIGHT = 0.0 * mm
        PORT_CUT_ENABLE = True
        PORT_CUT_W = 16.0 * mm

        SIDE_BUTTON_CUT_ENABLE = True
        SIDE_BUTTON_DIST_FROM_TOP = 34.64 * mm
        SIDE_BUTTON_CUT_W = 22.0 * mm
        SIDE_BUTTON_CUT_X = inner_x2 - SIDE_BUTTON_DIST_FROM_TOP

        VOLUME_CUT_ENABLE = True
        VOLUME_CUT_DIST_FROM_TOP = 35.0 * mm
        VOLUME_CUT_W = 42.0 * mm
        VOLUME_CUT_X = inner_x2 - VOLUME_CUT_DIST_FROM_TOP

        # Printer Homing Clearance (Right-Bottom Corner)
        HOME_CUT_ENABLE = True
        HOME_CUT_W = 24.0 * mm
        HOME_CUT_D = 25.0 * mm

        # -------------------------------------------------------------
        # STEP 1: Monolithic Base Plate with Rectangular Stepped Corner
        # -------------------------------------------------------------
        baseSketch = sketches.add(xyPlane)
        bLines = baseSketch.sketchCurves.sketchLines
        bArcs = baseSketch.sketchCurves.sketchArcs
        bCircles = baseSketch.sketchCurves.sketchCircles

        # 1. Front Edge
        bLines.addByTwoPoints(
            adsk.core.Point3D.create(pocket_x1, pocket_y1, 0),
            adsk.core.Point3D.create(arm_x2, pocket_y1, 0)
        )

        # 2. Arm Right Vertical Edge (runs to bottom of rectangular corner cut)
        p_corner_b = adsk.core.Point3D.create(arm_x2, corner_inner_y, 0)
        bLines.addByTwoPoints(adsk.core.Point3D.create(arm_x2, pocket_y1, 0), p_corner_b)

        # 3. Rectangular Corner: 90° Inward Horizontal Step
        p_corner_inner = adsk.core.Point3D.create(corner_inner_x, corner_inner_y, 0)
        bLines.addByTwoPoints(p_corner_b, p_corner_inner)

        # 4. Rectangular Corner: 90° Upward Vertical Step to Top Limit Line
        p_corner_t = adsk.core.Point3D.create(corner_inner_x, mount_y2, 0)
        bLines.addByTwoPoints(p_corner_inner, p_corner_t)

        # 5. Top Horizontal Edge (runs across to left rounded nose)
        p_tl_start = adsk.core.Point3D.create(mount_left_cx, mount_y2, 0)
        bLines.addByTwoPoints(p_corner_t, p_tl_start)

        # 6. Top-Left Arc
        p_left_apex = adsk.core.Point3D.create(mount_left_apex_x, pin_y, 0)
        p_tl_mid = adsk.core.Point3D.create(
            mount_left_cx - MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            pin_y + MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            0
        )
        bArcs.addByThreePoints(p_tl_start, p_tl_mid, p_left_apex)

        # 7. Bottom-Left Arc
        p_bl_end = adsk.core.Point3D.create(mount_left_cx, mount_y1, 0)
        p_bl_mid = adsk.core.Point3D.create(
            mount_left_cx - MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            pin_y - MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            0
        )
        bArcs.addByThreePoints(p_left_apex, p_bl_mid, p_bl_end)

        # 8. Mount Bar Bottom Edge to Root Fillet
        p_fillet_start = adsk.core.Point3D.create(arm_x1 - MOUNT_ARM_FILLET_R, mount_y1, 0)
        bLines.addByTwoPoints(p_bl_end, p_fillet_start)

        # 9. Tangent Circular Arc Fillet at Mount/Arm Root
        p_arm_inner_top = adsk.core.Point3D.create(arm_x1, mount_y1 - MOUNT_ARM_FILLET_R, 0)
        p_fillet_mid = adsk.core.Point3D.create(
            arm_x1 - MOUNT_ARM_FILLET_R * (1.0 - math.sqrt(2) / 2.0),
            mount_y1 - MOUNT_ARM_FILLET_R * (1.0 - math.sqrt(2) / 2.0),
            0
        )
        bArcs.addByThreePoints(p_fillet_start, p_fillet_mid, p_arm_inner_top)

        # 10. Arm Inner Edge straight down to pocket
        p_corner_90 = adsk.core.Point3D.create(arm_x1, pocket_y2, 0)
        bLines.addByTwoPoints(p_arm_inner_top, p_corner_90)

        # 11. Pocket Rear Edge
        p_pocket_rl = adsk.core.Point3D.create(pocket_x1, pocket_y2, 0)
        bLines.addByTwoPoints(p_corner_90, p_pocket_rl)

        # 12. Pocket Left Edge back to Front-Left (closing loop)
        bLines.addByTwoPoints(p_pocket_rl, adsk.core.Point3D.create(pocket_x1, pocket_y1, 0))

        # Dual alignment pin holes
        bCircles.addByCenterRadius(adsk.core.Point3D.create(hole1_x, pin_y, 0), BED_PIN_RADIUS)
        bCircles.addByCenterRadius(adsk.core.Point3D.create(hole2_x, pin_y, 0), BED_PIN_RADIUS)

        # Extrude base plate
        baseProf = max(baseSketch.profiles, key=lambda p: p.areaProperties().area)
        baseInput = extrudes.createInput(baseProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        baseInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BASE_THICK))
        mainBody = extrudes.add(baseInput).bodies.item(0)
        mainBody.name = "Prusa_Mini_iPhone_SideArm_Mount"

        # -------------------------------------------------------------
        # STEP 1b: Arm Lightening Slot
        # -------------------------------------------------------------
        if ARM_SLOT_ENABLE:
            armSlotSketch = sketches.add(xyPlane)
            asLines = armSlotSketch.sketchCurves.sketchLines
            asArcs = armSlotSketch.sketchCurves.sketchArcs

            slot_r = ARM_SLOT_W / 2.0
            slot_cx = (arm_x1 + arm_x2) / 2.0
            slot_x_left = slot_cx - slot_r
            slot_x_right = slot_cx + slot_r

            p_b_start = adsk.core.Point3D.create(slot_x_left, ARM_SLOT_Y1 + slot_r, 0)
            p_b_end = adsk.core.Point3D.create(slot_x_right, ARM_SLOT_Y1 + slot_r, 0)
            p_b_mid = adsk.core.Point3D.create(slot_cx, ARM_SLOT_Y1, 0)
            asArcs.addByThreePoints(p_b_start, p_b_mid, p_b_end)

            p_t_end = adsk.core.Point3D.create(slot_x_right, ARM_SLOT_Y2 - slot_r, 0)
            asLines.addByTwoPoints(p_b_end, p_t_end)

            p_t_start = adsk.core.Point3D.create(slot_x_left, ARM_SLOT_Y2 - slot_r, 0)
            p_t_mid = adsk.core.Point3D.create(slot_cx, ARM_SLOT_Y2, 0)
            asArcs.addByThreePoints(p_t_end, p_t_mid, p_t_start)

            asLines.addByTwoPoints(p_t_start, p_b_start)

            armSlotProf = armSlotSketch.profiles.item(0)
            armSlotCutInput = extrudes.createInput(armSlotProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
            armSlotCutInput.participantBodies = [mainBody]
            armSlotCutInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BASE_THICK * 2.0))
            extrudes.add(armSlotCutInput)

        # -------------------------------------------------------------
        # STEP 2: Retaining Walls for the iPhone Pocket
        # -------------------------------------------------------------
        topPlanes = rootComp.constructionPlanes
        planeInput = topPlanes.createInput()
        planeInput.setByOffset(xyPlane, adsk.core.ValueInput.createByReal(BASE_THICK))
        baseTopPlane = topPlanes.add(planeInput)

        wallSketch = sketches.add(baseTopPlane)
        wLines = wallSketch.sketchCurves.sketchLines

        wLines.addTwoPointRectangle(
            adsk.core.Point3D.create(pocket_x1, pocket_y1, 0),
            adsk.core.Point3D.create(pocket_x2, pocket_y2, 0)
        )
        wLines.addTwoPointRectangle(
            adsk.core.Point3D.create(inner_x1, inner_y1, 0),
            adsk.core.Point3D.create(inner_x2, inner_y2, 0)
        )

        wallProf = min(wallSketch.profiles, key=lambda p: p.areaProperties().area)
        wallInput = extrudes.createInput(wallProf, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        wallInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(WALL_HEIGHT))
        extrudes.add(wallInput)

        # -------------------------------------------------------------
        # STEP 3: Wall Cutouts (iPhone SE2 Controls)
        # -------------------------------------------------------------
        if WALL_LIP_HEIGHT > 0:
            lipPlaneInput = topPlanes.createInput()
            lipPlaneInput.setByOffset(baseTopPlane, adsk.core.ValueInput.createByReal(WALL_LIP_HEIGHT))
            cutPlane = topPlanes.add(lipPlaneInput)
        else:
            cutPlane = baseTopPlane

        wallCutSketch = sketches.add(cutPlane)
        wcLines = wallCutSketch.sketchCurves.sketchLines
        wallCutProfs = adsk.core.ObjectCollection.create()

        # 1. Lightning Port Cutout on Left Wall (Bottom of iPhone)
        if PORT_CUT_ENABLE and PORT_CUT_W > 0:
            port_cy = (inner_y1 + inner_y2) / 2.0
            wcLines.addTwoPointRectangle(
                adsk.core.Point3D.create(pocket_x1 - 1.0 * mm, port_cy - PORT_CUT_W / 2.0, 0),
                adsk.core.Point3D.create(inner_x1 + 1.0 * mm, port_cy + PORT_CUT_W / 2.0, 0)
            )

        # 2. Side Button (Sleep/Wake) Cutout on Front Wall (Right side of iPhone SE2)
        if SIDE_BUTTON_CUT_ENABLE and SIDE_BUTTON_CUT_W > 0:
            wcLines.addTwoPointRectangle(
                adsk.core.Point3D.create(SIDE_BUTTON_CUT_X - SIDE_BUTTON_CUT_W / 2.0, pocket_y1 - 1.0 * mm, 0),
                adsk.core.Point3D.create(SIDE_BUTTON_CUT_X + SIDE_BUTTON_CUT_W / 2.0, inner_y1 + 1.0 * mm, 0)
            )

        # 3. Volume Buttons & Mute Switch Cutout on Rear Wall (Left side of iPhone SE2)
        if VOLUME_CUT_ENABLE and VOLUME_CUT_W > 0:
            wcLines.addTwoPointRectangle(
                adsk.core.Point3D.create(VOLUME_CUT_X - VOLUME_CUT_W / 2.0, inner_y2 - 1.0 * mm, 0),
                adsk.core.Point3D.create(VOLUME_CUT_X + VOLUME_CUT_W / 2.0, pocket_y2 + 1.0 * mm, 0)
            )

        for prof in wallCutSketch.profiles:
            wallCutProfs.add(prof)

        if wallCutProfs.count > 0:
            wallCutInput = extrudes.createInput(wallCutProfs, adsk.fusion.FeatureOperations.CutFeatureOperation)
            wallCutInput.participantBodies = [mainBody]
            wallCutInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(WALL_HEIGHT * 1.5))
            extrudes.add(wallCutInput)

        # -------------------------------------------------------------
        # STEP 4: Printer Homing Clearance Cut (Right-Bottom Corner)
        # -------------------------------------------------------------
        if HOME_CUT_ENABLE and HOME_CUT_W > 0 and HOME_CUT_D > 0:
            homeSketch = sketches.add(xyPlane)
            hLines = homeSketch.sketchCurves.sketchLines

            hLines.addTwoPointRectangle(
                adsk.core.Point3D.create(arm_x2 - HOME_CUT_W, pocket_y1, 0),
                adsk.core.Point3D.create(arm_x2, pocket_y1 + HOME_CUT_D, 0)
            )

            homeProf = homeSketch.profiles.item(0)
            homeCutInput = extrudes.createInput(homeProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
            homeCutInput.participantBodies = [mainBody]
            homeCutInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal((BASE_THICK + WALL_HEIGHT) * 2.0))
            extrudes.add(homeCutInput)

        # -------------------------------------------------------------
        # STEP 5: iPhone Plate 3x3 Grid (space-solid-space pattern)
        # -------------------------------------------------------------
        if GRID_CUT_ENABLE:
            gridSketch = sketches.add(xyPlane)
            gLines = gridSketch.sketchCurves.sketchLines
            gArcs = gridSketch.sketchCurves.sketchArcs
            gridProfs = adsk.core.ObjectCollection.create()

            grid_x_min = inner_x1 + PLATE_MARGIN
            grid_x_max = inner_x2 - PLATE_MARGIN
            grid_y_min = inner_y1 + PLATE_MARGIN
            grid_y_max = inner_y2 - PLATE_MARGIN

            avail_w = grid_x_max - grid_x_min
            avail_d = grid_y_max - grid_y_min

            cell_w = (avail_w - 2.0 * GRID_RIB_W) / 3.0
            cell_d = (avail_d - 2.0 * GRID_RIB_W) / 3.0

            cam_box_x1 = cam_x1 - GRID_RIB_W
            cam_box_y2 = cam_y2 + GRID_RIB_W

            # Checkerboard pattern: (r + c) % 2 == 0
            for r in range(3):
                for c in range(3):
                    if (r + c) % 2 == 0:
                        cx1 = grid_x_min + c * (cell_w + GRID_RIB_W)
                        cx2 = cx1 + cell_w
                        cy1 = grid_y_min + r * (cell_d + GRID_RIB_W)
                        cy2 = cy1 + cell_d

                        # Check collision with camera cutout
                        overlaps_camera = not (cx2 <= cam_box_x1 or cy1 >= cam_box_y2)

                        if not overlaps_camera:
                            add_rounded_rectangle(gLines, gArcs, cx1, cy1, cx2, cy2, GRID_CORNER_R)

            for prof in gridSketch.profiles:
                gridProfs.add(prof)

            if gridProfs.count > 0:
                gridCutInput = extrudes.createInput(gridProfs, adsk.fusion.FeatureOperations.CutFeatureOperation)
                gridCutInput.participantBodies = [mainBody]
                gridCutInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BASE_THICK * 2.0))
                extrudes.add(gridCutInput)

        # -------------------------------------------------------------
        # STEP 6: Camera Cutout (Compact 26x26mm Through Base Floor)
        # -------------------------------------------------------------
        camSketch = sketches.add(xyPlane)
        camLines = camSketch.sketchCurves.sketchLines

        camLines.addTwoPointRectangle(
            adsk.core.Point3D.create(cam_x1, cam_y1, 0),
            adsk.core.Point3D.create(cam_x2, cam_y2, 0)
        )

        camProf = camSketch.profiles.item(0)
        camCutInput = extrudes.createInput(camProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
        camCutInput.participantBodies = [mainBody]
        camCutInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BASE_THICK * 2.0))
        extrudes.add(camCutInput)

        # -------------------------------------------------------------
        # SUCCESS NOTIFICATION
        # -------------------------------------------------------------
        if ui:
            ui.messageBox(
                "Prusa Mini Mount Generated Successfully!\n\n"
                "• Rectangular Corner Cutout Applied:\n"
                "  1. Stepped Corner Geometry (90° Sharp Corner):\n"
                "     - Removed top-right arc corner entirely.\n"
                "     - Inward horizontal cut along X: {:.1f} mm (from X = {:.1f} to {:.1f} mm).\n"
                "     - Forward depth along Y: {:.1f} mm (from Y = {:.1f} to rear edge {:.1f} mm).\n"
                "     - Cutout lines directly meet design limit lines (Right edge and Rear edge).\n"
                "  2. Preserved Rigidity:\n"
                "     - Solid wall from Bed Pin 2 (+50 mm): {:.1f} mm.\n"
                "     - Solid bridge before arm slot: 26.0 mm.\n"
                "  3. Retained Clearances:\n"
                "     - 26x26 mm camera cutout.\n"
                "     - iPhone SE2 button clearances."
                .format(
                    CORNER_CUT_W / mm,
                    arm_x2 / mm,
                    corner_inner_x / mm,
                    CORNER_CUT_D / mm,
                    corner_inner_y / mm,
                    mount_y2 / mm,
                    (corner_inner_x - (hole2_x + BED_PIN_RADIUS)) / mm
                )
            )

    except Exception:
        if ui:
            ui.messageBox("Script Failed:\n{}".format(traceback.format_exc()))