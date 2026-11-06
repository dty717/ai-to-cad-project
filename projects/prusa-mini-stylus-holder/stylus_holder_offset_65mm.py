import adsk.core
import adsk.fusion
import traceback
import math

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

        PLATE_W = 44.0 * mm
        PLATE_H = 44.0 * mm
        BASE_THICK = 4.0 * mm

        HOLE_OFFSET = 16.0 * mm
        HOLE_DIA = 3.4 * mm
        CB_DIA = 12.0 * mm
        CB_DEPTH = 2.5 * mm

        STYLUS_DIA = 7.3 * mm
        BORE_RAD = (STYLUS_DIA / 2.0)
        WALL_THICK = 3.5 * mm
        CANTILEVER_OFFSET = 65.0 * mm

        baseSketch = sketches.add(xyPlane)
        bLines = baseSketch.sketchCurves.sketchLines
        bCircles = baseSketch.sketchCurves.sketchCircles

        bLines.addTwoPointRectangle(
            adsk.core.Point3D.create(-PLATE_W / 2.0, -PLATE_H / 2.0, 0),
            adsk.core.Point3D.create(PLATE_W / 2.0, PLATE_H / 2.0, 0)
        )

        bCircles.addByCenterRadius(adsk.core.Point3D.create(-HOLE_OFFSET, -HOLE_OFFSET, 0), HOLE_DIA / 2.0)
        bCircles.addByCenterRadius(adsk.core.Point3D.create(HOLE_OFFSET, HOLE_OFFSET, 0), HOLE_DIA / 2.0)

        baseProf = baseSketch.profiles.item(0)
        baseInput = extrudes.createInput(baseProf, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        baseInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(BASE_THICK))
        mainBody = extrudes.add(baseInput).bodies.item(0)
        mainBody.name = "Prusa_Mini_Stylus_Holder_Offset_65mm"

        topPlanes = rootComp.constructionPlanes
        planeInput = topPlanes.createInput()
        planeInput.setByOffset(xyPlane, adsk.core.ValueInput.createByReal(BASE_THICK))
        baseTopPlane = topPlanes.add(planeInput)

        cbSketch = sketches.add(baseTopPlane)
        cbCircles = cbSketch.sketchCurves.sketchCircles
        cbCircles.addByCenterRadius(adsk.core.Point3D.create(-HOLE_OFFSET, -HOLE_OFFSET, 0), CB_DIA / 2.0)
        cbCircles.addByCenterRadius(adsk.core.Point3D.create(HOLE_OFFSET, HOLE_OFFSET, 0), CB_DIA / 2.0)

        cbProfs = adsk.core.ObjectCollection.create()
        for prof in cbSketch.profiles:
            cbProfs.add(prof)

        if cbProfs.count > 0:
            cbInput = extrudes.createInput(cbProfs, adsk.fusion.FeatureOperations.CutFeatureOperation)
            cbInput.participantBodies = [mainBody]
            cbInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(CB_DEPTH))
            extrudes.add(cbInput)

        armSketch = sketches.add(baseTopPlane)
        aLines = armSketch.sketchCurves.sketchLines
        aCircles = armSketch.sketchCurves.sketchCircles

        arm_w = 16.0 * mm
        aLines.addTwoPointRectangle(
            adsk.core.Point3D.create(-arm_w / 2.0, 0, 0),
            adsk.core.Point3D.create(arm_w / 2.0, CANTILEVER_OFFSET, 0)
        )

        stylus_center = adsk.core.Point3D.create(0, CANTILEVER_OFFSET, 0)
        housing_radius = BORE_RAD + WALL_THICK
        aCircles.addByCenterRadius(stylus_center, housing_radius)

        armProf = min(armSketch.profiles, key=lambda p: p.areaProperties().area)
        armInput = extrudes.createInput(armProf, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        STYLUS_H = 35.0 * mm
        armInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(STYLUS_H))
        extrudes.add(armInput)

        stylusTopPlaneInput = topPlanes.createInput()
        stylusTopPlaneInput.setByOffset(baseTopPlane, adsk.core.ValueInput.createByReal(STYLUS_H))
        stylusTopPlane = topPlanes.add(stylusTopPlaneInput)

        boreSketch = sketches.add(stylusTopPlane)
        bCircles2 = boreSketch.sketchCurves.sketchCircles
        bCircles2.addByCenterRadius(adsk.core.Point3D.create(0, CANTILEVER_OFFSET, 0), BORE_RAD)

        boreProf = boreSketch.profiles.item(0)
        boreInput = extrudes.createInput(boreProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
        boreInput.participantBodies = [mainBody]
        boreInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(STYLUS_H * 1.2))
        extrudes.add(boreInput)

        if ui:
            ui.messageBox("Prusa Mini Stylus Holder (+65mm Offset Variant) Generated Successfully!")

    except Exception:
        if ui:
            ui.messageBox("Script Failed:\n{}".format(traceback.format_exc()))
