import adsk.core
import adsk.fusion
import traceback
import math


def add_rounded_rectangle(sketch_lines, sketch_arcs, x1, y1, x2, y2, r):
    """Draws a closed rectangle with 4 tangent circular arc filleted corners."""
    k = r * (1.0 - math.sqrt(2) / 2.0)
    sketch_arcs.addByThreePoints(
        adsk.core.Point3D.create(x2, y1 + r, 0),
        adsk.core.Point3D.create(x2 - k, y1 + k, 0),
        adsk.core.Point3D.create(x2 - r, y1, 0)
    )
    sketch_lines.addByTwoPoints(
        adsk.core.Point3D.create(x2 - r, y1, 0),
        adsk.core.Point3D.create(x1 + r, y1, 0)
    )
    sketch_arcs.addByThreePoints(
        adsk.core.Point3D.create(x1 + r, y1, 0),
        adsk.core.Point3D.create(x1 + k, y1 + k, 0),
        adsk.core.Point3D.create(x1, y1 + r, 0)
    )
    sketch_lines.addByTwoPoints(
        adsk.core.Point3D.create(x1, y1 + r, 0),
        adsk.core.Point3D.create(x1, y2 - r, 0)
    )
    sketch_arcs.addByThreePoints(
        adsk.core.Point3D.create(x1, y2 - r, 0),
        adsk.core.Point3D.create(x1 + k, y2 - k, 0),
        adsk.core.Point3D.create(x1 + r, y2, 0)
    )
    sketch_lines.addByTwoPoints(
        adsk.core.Point3D.create(x1 + r, y2, 0),
        adsk.core.Point3D.create(x2 - r, y2, 0)
    )
    sketch_arcs.addByThreePoints(
        adsk.core.Point3D.create(x2 - r, y2, 0),
        adsk.core.Point3D.create(x2 - k, y2 - k, 0),
        adsk.core.Point3D.create(x2, y2 - r, 0)
    )
    sketch_lines.addByTwoPoints(
        adsk.core.Point3D.create(x2, y2 - r, 0),
        adsk.core.Point3D.create(x2, y1 + r, 0)
    )


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            raise RuntimeError("Failed to create or access the design document.")

        rootComp = design.rootComponent
        sketches = rootComp.sketches
        extrudes = rootComp.features.extrudeFeatures
        xyPlane = rootComp.xYConstructionPlane

        mm = 0.1

        BASE_THICK = 4.0 * mm
        WALL_THICK = 3.5 * mm
        WALL_HEIGHT = 8.0 * mm

        SE2_LEN = 139.0 * mm
        SE2_WID = 68.0 * mm
        pocket_outer_x = SE2_LEN + 2.0 * WALL_THICK
        pocket_outer_y = SE2_WID + 2.0 * WALL_THICK

        pocket_x1 = -87.5 * mm
        pocket_x2 = pocket_x1 + pocket_outer_x
        pocket_y1 = -87.5 * mm
        pocket_y2 = pocket_y1 + pocket_outer_y

        arm_w = 24.0 * mm
        arm_x1 = pocket_x2
        arm_x2 = arm_x1 + arm_w
        MOUNT_ARM_FILLET_R = 10.0 * mm

        ARM_SLOT_ENABLE = True
        ARM_SLOT_W = 10.0 * mm
        ARM_SLOT_Y1 = 4.0 * mm
        ARM_SLOT_Y2 = 46.0 * mm

        mount_bar_d = 18.0 * mm
        mount_y2 = 82.0 * mm
        mount_y1 = mount_y2 - mount_bar_d
        pin_y = (mount_y1 + mount_y2) / 2.0

        BED_PIN_HOLE_DIA = 3.8 * mm
        BED_PIN_RADIUS = BED_PIN_HOLE_DIA / 2.0
        pin_spacing = 100.0 * mm
        hole1_x = -pin_spacing / 2.0
        hole2_x = pin_spacing / 2.0

        MOUNT_LEFT_EXT = 6.0 * mm
        mount_left_cx = hole1_x - MOUNT_LEFT_EXT
        MOUNT_ARC_LEFT_R = mount_bar_d / 2.0
        mount_left_apex_x = mount_left_cx - MOUNT_ARC_LEFT_R

        MOUNT_ARC_RIGHT_R = 12.0 * mm

        inner_x1 = pocket_x1 + WALL_THICK
        inner_x2 = pocket_x2 - WALL_THICK
        inner_y1 = pocket_y1 + WALL_THICK
        inner_y2 = pocket_y2 - WALL_THICK

        CAM_SIZE_X = 42.0 * mm
        CAM_SIZE_Y = 42.0 * mm
        cam_x2 = inner_x2
        cam_x1 = inner_x2 - CAM_SIZE_X
        cam_y1 = inner_y1
        cam_y2 = inner_y1 + CAM_SIZE_Y

        GRID_CUT_ENABLE = True
        PLATE_MARGIN = 5.0 * mm
        GRID_RIB_W = 5.0 * mm
        GRID_CORNER_R = 3.5 * mm

        WALL_LIP_HEIGHT = 0.0 * mm
        PORT_CUT_ENABLE = True
        PORT_CUT_W = 15.0 * mm
        FRONT_BUTTON_CUT_ENABLE = True
        FRONT_BUTTON_CUT_W = 38.0 * mm
        FRONT_BUTTON_CUT_X = 20.0 * mm
        REAR_BUTTON_CUT_ENABLE = True
        REAR_BUTTON_CUT_W = 20.0 * mm
        REAR_BUTTON_CUT_X = 18.5 * mm

        HOME_CUT_ENABLE = True
        HOME_CUT_W = 24.0 * mm
        HOME_CUT_D = 25.0 * mm

        baseSketch = sketches.add(xyPlane)
        bLines = baseSketch.sketchCurves.sketchLines
        bArcs = baseSketch.sketchCurves.sketchArcs
        bCircles = baseSketch.sketchCurves.sketchCircles

        bLines.addByTwoPoints(
            adsk.core.Point3D.create(pocket_x1, pocket_y1, 0),
            adsk.core.Point3D.create(arm_x2, pocket_y1, 0)
        )

        p_tr_start = adsk.core.Point3D.create(arm_x2, mount_y2 - MOUNT_ARC_RIGHT_R, 0)
        bLines.addByTwoPoints(adsk.core.Point3D.create(arm_x2, pocket_y1, 0), p_tr_start)

        p_tr_end = adsk.core.Point3D.create(arm_x2 - MOUNT_ARC_RIGHT_R, mount_y2, 0)
        p_tr_mid = adsk.core.Point3D.create(
            arm_x2 - MOUNT_ARC_RIGHT_R * (1.0 - math.sqrt(2) / 2.0),
            mount_y2 - MOUNT_ARC_RIGHT_R * (1.0 - math.sqrt(2) / 2.0),
            0
        )
        bArcs.addByThreePoints(p_tr_start, p_tr_mid, p_tr_end)

        p_tl_start = adsk.core.Point3D.create(mount_left_cx, mount_y2, 0)
        bLines.addByTwoPoints(p_tr_end, p_tl_start)

        p_left_apex = adsk.core.Point3D.create(mount_left_apex_x, pin_y, 0)
        p_tl_mid = adsk.core.Point3D.create(
            mount_left_cx - MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            pin_y + MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            0
        )
        bArcs.addByThreePoints(p_tl_start, p_tl_mid, p_left_apex)

        p_bl_end = adsk.core.Point3D.create(mount_left_cx, mount_y1, 0)
        p_bl_mid = adsk.core.Point3D.create(
            mount_left_cx - MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            pin_y - MOUNT_ARC_LEFT_R * math.sqrt(2) / 2.0,
            0
        )
        bArcs.addByThreePoints(p_left_apex, p_bl_mid, p_bl_end)

        p_fillet_start = adsk.core.Point3D.create(arm_x1 - MOUNT_ARM_FILLET_R, mount_y1, 0)
        bLines.addByTwoPoints(p_bl_end, p_fillet_start)

        p_arm_inner_top = adsk.core.Point3D.create(arm_x1, mount_y1 - MOUNT_ARM_FILLET_R, 0)
        p_fillet_mid = adsk.core.Point3D.create(
            arm_x1 - MOUNT_ARM_FILLET_R * (1.0 - math.sqrt(2) / 2.0),
            mount_y1 - MOUNT_ARM_FILLET_R * (1.0 - math.sqrt(2) / 2.0),
            0
        )
        bArcs.addByThreePoints(p_fillet_start, p_fillet_mid, p_arm_inner_top)

        p_corner_90 = adsk.core.Point3D.create(arm_x1, pocket_y2, 0)
        bLines.addByTwoPoints(p_arm_inner_top, p_corner_90)

        p_pocket_rl = adsk.core.Point3D.create(pocket_x1, pocket_y2, 0)
        bLines.addByTwoPoints(p_corner_90, p_pocket_rl)
        bLines.addByTwoPoints(p_pocket_rl, adsk.core.Point3D.create(pocket_x1, pocket_y1, 0))

        bCircles.addByCenterRadius(adsk.core.Point3D.create(hole1_x, pin_y, 0), BED_PIN_RADIUS)
        bCircles.addByCenterRadius(adsk.core.Point3D.create(hole2_x, pin_y, 0), BED_PIN_RADIUS)

        baseProf = max(baseSketch.profiles, key=lambda p: p.areaProperties().area)
        baseInput = extrudes.createInput(baseProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        baseInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BASE_THICK))
        mainBody = extrudes.add(baseInput).bodies.item(0)
        mainBody.name = "Prusa_Mini_iPhone_SideArm_Mount"

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

        if WALL_LIP_HEIGHT > 0:
            lipPlaneInput = topPlanes.createInput()
            lipPlaneInput.setByOffset(baseTopPlane, adsk.core.ValueInput.createByReal(WALL_LIP_HEIGHT))
            cutPlane = topPlanes.add(lipPlaneInput)
        else:
            cutPlane = baseTopPlane

        wallCutSketch = sketches.add(cutPlane)
        wcLines = wallCutSketch.sketchCurves.sketchLines
        wallCutProfs = adsk.core.ObjectCollection.create()

        if PORT_CUT_ENABLE and PORT_CUT_W > 0:
            port_cy = (inner_y1 + inner_y2) / 2.0
            wcLines.addTwoPointRectangle(
                adsk.core.Point3D.create(pocket_x1 - 1.0 * mm, port_cy - PORT_CUT_W / 2.0, 0),
                adsk.core.Point3D.create(inner_x1 + 1.0 * mm, port_cy + PORT_CUT_W / 2.0, 0)
            )

        if FRONT_BUTTON_CUT_ENABLE and FRONT_BUTTON_CUT_W > 0:
            wcLines.addTwoPointRectangle(
                adsk.core.Point3D.create(FRONT_BUTTON_CUT_X - FRONT_BUTTON_CUT_W / 2.0, pocket_y1 - 1.0 * mm, 0),
                adsk.core.Point3D.create(FRONT_BUTTON_CUT_X + FRONT_BUTTON_CUT_W / 2.0, inner_y1 + 1.0 * mm, 0)
            )

        if REAR_BUTTON_CUT_ENABLE and REAR_BUTTON_CUT_W > 0:
            wcLines.addTwoPointRectangle(
                adsk.core.Point3D.create(REAR_BUTTON_CUT_X - REAR_BUTTON_CUT_W / 2.0, inner_y2 - 1.0 * mm, 0),
                adsk.core.Point3D.create(REAR_BUTTON_CUT_X + REAR_BUTTON_CUT_W / 2.0, pocket_y2 + 1.0 * mm, 0)
            )

        for prof in wallCutSketch.profiles:
            wallCutProfs.add(prof)

        if wallCutProfs.count > 0:
            wallCutInput = extrudes.createInput(wallCutProfs, adsk.fusion.FeatureOperations.CutFeatureOperation)
            wallCutInput.participantBodies = [mainBody]
            wallCutInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(WALL_HEIGHT * 1.5))
            extrudes.add(wallCutInput)

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

            for r in range(3):
                for c in range(3):
                    if (r + c) % 2 == 1:
                        cx1 = grid_x_min + c * (cell_w + GRID_RIB_W)
                        cx2 = cx1 + cell_w
                        cy1 = grid_y_min + r * (cell_d + GRID_RIB_W)
                        cy2 = cy1 + cell_d
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

        if ui:
            ui.messageBox("Prusa Mini Mount Generated Successfully!")

    except Exception:
        if ui:
            ui.messageBox("Script Failed:\n{}".format(traceback.format_exc()))
