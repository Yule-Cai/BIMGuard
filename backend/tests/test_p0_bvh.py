"""P0-3/4/5 Real BVH geometry tests."""
import os, sys, tempfile, math
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.app.rules.clash import detect_clashes

HAS_GEOM = False
try:
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.util.unit
    import ifcopenshell.geom
    HAS_GEOM = True
except:
    pass

pytestmark = pytest.mark.skipif(not HAS_GEOM, reason="IfcOpenShell geom not available")

def _create_bvh_ifc(path, beam_pos, pipe_pos, beam_size=(5,0.3,0.4), pipe_size=(4,0.1,0.1), add_geometry=True):
    """Create IFC with beam and pipe, optionally with real geometry."""
    import ifcopenshell
    import ifcopenshell.api

    model = ifcopenshell.file(schema="IFC4")
    project = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcProject", name="BVH Test")
    # Create Model/Body contexts
    context = ifcopenshell.api.run("context.add_context", model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW")
    body = ifcopenshell.api.run("context.add_context", model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=context)

    site = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcSite", name="Site")
    building = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuilding", name="B")
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="L1")
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=project, products=[site])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=site, products=[building])
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

    beam = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBeam", name="B-TEST")
    beam.Tag = "B-TEST"
    mat_b = np.eye(4)
    mat_b[0,3], mat_b[1,3], mat_b[2,3] = beam_pos
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=beam, matrix=mat_b, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[beam], relating_structure=storey)

    pipe = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcPipeSegment", name="P-TEST")
    pipe.Tag = "P-TEST"
    mat_p = np.eye(4)
    mat_p[0,3], mat_p[1,3], mat_p[2,3] = pipe_pos
    ifcopenshell.api.run("geometry.edit_object_placement", model, product=pipe, matrix=mat_p, is_si=True)
    ifcopenshell.api.run("spatial.assign_container", model, products=[pipe], relating_structure=storey)

    if add_geometry:
        # Real BVH geometry via wall-like swept solid (proven to work)
        # Beam: length 5, height 0.4, thickness 0.3 ; Pipe: 4, 0.2, 0.2
        try:
            rep_beam = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=beam_size[0], height=beam_size[2], thickness=beam_size[1])
            ifcopenshell.api.run("geometry.assign_representation", model, product=beam, representation=rep_beam)
            rep_pipe = ifcopenshell.api.run("geometry.add_wall_representation", model, context=body, length=pipe_size[0], height=pipe_size[2], thickness=pipe_size[1])
            ifcopenshell.api.run("geometry.assign_representation", model, product=pipe, representation=rep_pipe)
        except Exception as e:
            # Fallback manual extruded solid
            try:
                ctx = body
                bp = model.create_entity("IfcRectangleProfileDef", "AREA", "Beam Profile", None, beam_size[1], beam_size[2])
                bs = model.create_entity("IfcExtrudedAreaSolid", bp, None, model.create_entity("IfcAxis2Placement3D", model.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0)), None, None), beam_size[0])
                br = model.create_entity("IfcShapeRepresentation", ctx, "Body", "SweptSolid", [bs])
                bds = model.create_entity("IfcProductDefinitionShape", None, None, [br])
                beam.Representation = bds
                pp = model.create_entity("IfcRectangleProfileDef", "AREA", "Pipe Profile", None, pipe_size[1], pipe_size[2])
                ps = model.create_entity("IfcExtrudedAreaSolid", pp, None, model.create_entity("IfcAxis2Placement3D", model.create_entity("IfcCartesianPoint", (0.0, 0.0, 0.0)), None, None), pipe_size[0])
                pr = model.create_entity("IfcShapeRepresentation", ctx, "Body", "SweptSolid", [ps])
                pds = model.create_entity("IfcProductDefinitionShape", None, None, [pr])
                pipe.Representation = pds
            except Exception as e2:
                print(f"Failed to add geometry: {e} / {e2}")

    model.write(path)
    return path

def test_p0_3_real_bvh_positive():
    """Beam and pipe with ~100mm penetration must be detected via BVH."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    # Beam at (0,0,2), size 5x0.3x0.4  => x 0-5, y -0.15..0.15, z 2-2.4
    # Pipe at (2,0,2.1), size 4x0.1x0.1 => x 2-6, y -0.05..0.05, z 2.1-2.2
    # Overlap: x 2-5 (3m), y -0.05..0.05 (0.1m), z 2.1-2.2 (0.1m) => penetration 100mm
    _create_bvh_ifc(path, beam_pos=(0,0,2), pipe_pos=(2,0,2.1))
    model = ifcopenshell.open(path)
    # Verify geometry exists
    reps = len(model.by_type("IfcShapeRepresentation"))
    print(f"Positive test: {reps} shape reps")
    assert reps >= 2, f"Expected real geometry, got {reps} reps"
    clashes = detect_clashes(model, tolerance=0.001)
    print(f"Clashes: {clashes}")
    assert len(clashes) == 1, f"Expected 1 clash, got {len(clashes)}: {clashes}"
    c = clashes[0]
    assert c["method"] == "ifcopenshell_bvh", f"Expected BVH, got {c['method']}"
    assert c["a_guid"] != c["b_guid"]
    # penetration should be ~100mm ( allow 20mm tolerance for geometry)
    assert 80 <= c["penetration_mm"] <= 120, f"Expected ~100mm, got {c['penetration_mm']}"
    os.unlink(path)

def test_p0_4_real_bvh_negative():
    """Beam and pipe separated by 500mm must NOT clash."""
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    # Beam at (0,0,2), pipe at (10,0,2.1) => separated by 5m in x, no overlap
    _create_bvh_ifc(path, beam_pos=(0,0,2), pipe_pos=(10,0,2.1))
    model = ifcopenshell.open(path)
    reps = len(model.by_type("IfcShapeRepresentation"))
    assert reps >= 2
    clashes = detect_clashes(model, tolerance=0.001)
    print(f"Negative test clashes: {clashes}")
    assert len(clashes) == 0, f"Expected 0 clashes, got {len(clashes)}"
    os.unlink(path)

def test_p0_5_tolerance():
    """Tolerance 2mm: contact and 1mm should not clash, 5mm should."""
    # Tolerance is in metres: 0.002 m = 2mm
    tolerance = 0.002
    # Contact: pipe at exactly beam top (z=2.4)
    # Beam z 2-2.4, pipe z 2.4-2.5 => touching at z=2.4, no penetration
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    _create_bvh_ifc(path, beam_pos=(0,0,2), pipe_pos=(2,0,2.4))
    model = ifcopenshell.open(path)
    clashes = detect_clashes(model, tolerance=tolerance)
    print(f"Contact clashes (tol 2mm): {clashes}")
    # Contact should be considered not a clash or filtered by tolerance
    # The spec says protrusion < tolerance filtered, so contact (0 penetration) should not be reported
    # We expect 0
    assert len(clashes) == 0, f"Contact should not clash at 2mm tol, got {clashes}"
    os.unlink(path)

    # 1mm penetration: pipe at z=2.399 (1mm into beam)
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    _create_bvh_ifc(path, beam_pos=(0,0,2), pipe_pos=(2,0,2.399))
    model = ifcopenshell.open(path)
    clashes = detect_clashes(model, tolerance=tolerance)
    print(f"1mm clashes: {clashes}")
    # 1mm < 2mm tolerance, should be filtered
    assert len(clashes) == 0, f"1mm should be filtered at 2mm tol, got {clashes}"
    os.unlink(path)

    # 5mm penetration: pipe at z=2.395 (5mm into beam)
    with tempfile.NamedTemporaryFile(suffix=".ifc", delete=False) as tmp:
        path = tmp.name
    _create_bvh_ifc(path, beam_pos=(0,0,2), pipe_pos=(2,0,2.395))
    model = ifcopenshell.open(path)
    clashes = detect_clashes(model, tolerance=tolerance)
    print(f"5mm clashes: {clashes}")
    assert len(clashes) == 1, f"5mm should clash at 2mm tol, got {clashes}"
    assert clashes[0]["penetration_mm"] >= 4, f"Expected >=4mm, got {clashes[0]['penetration_mm']}"
    os.unlink(path)
