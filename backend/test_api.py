"""Quick smoke tests without running the FastAPI server."""
import os
import tempfile

from app import ifc_engine
from app.rules.door_width import check_door_width
from app.rules.clash import detect_clashes
from app.agent.tools import route_message


def _demo_path():
    base = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(base, "sample-ifc/BIMGuard_Demo.ifc")
    alt = os.path.join(os.path.dirname(__file__), "../sample-ifc/BIMGuard_Demo.ifc")
    if os.path.exists(path):
        return path
    if os.path.exists(alt):
        return alt
    return "sample-ifc/BIMGuard_Demo.ifc"


def _test_project_unit_conversion():
    """Verify that a millimetre-based IFC does not rely on magnitude heuristics."""
    if not ifc_engine.HAS_IFC:
        print("- unit-scale test skipped (IfcOpenShell not installed)")
        return

    mm_ifc = """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('BIMGuard unit test'),'2;1');
FILE_NAME('unit_mm.ifc','2026-09-04T00:00:00',(''),(''),'','','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#6=IFCCARTESIANPOINT((0.,0.,0.));
#15=IFCAXIS2PLACEMENT3D(#6,$,$);
#20=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-05,#15,$);
#31=IFCSIUNIT(*,.LENGTHUNIT.,.MILLI.,.METRE.);
#30=IFCUNITASSIGNMENT((#31));
#10=IFCPROJECT('0UnitScaleProject00000',$,'Unit Test',$,$,$,$,(#20),#30);
#140=IFCDOOR('0UnitScaleDoor000000000',$,'D-MM','D-MM',$,$,680.,2100.,$,$,$,$);
ENDSEC;
END-ISO-10303-21;
"""
    handle = tempfile.NamedTemporaryFile("w", suffix=".ifc", delete=False)
    try:
        handle.write(mm_ifc)
        handle.close()
        ifc_engine.set_current_file(handle.name)
        model = ifc_engine.get_current_model()
        results = check_door_width(model, 750)
        assert len(results) == 1, results
        assert results[0]["measured_mm"] == 680.0, results[0]
        assert results[0]["status"] == "fail", results[0]
        print("✓ IFC project-unit conversion pass (680 project-mm -> 680mm)")
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass


def test():
    path = _demo_path()
    ifc_engine.set_current_file(path)
    model = ifc_engine.get_current_model()
    assert model is not None, "model not loaded"

    doors = check_door_width(model, 750)
    assert len(doors) == 3, f"expected 3 doors, got {len(doors)}"
    fails = [d for d in doors if d["status"] == "fail"]
    assert len(fails) == 1 and fails[0]["name"] == "D-102", (
        f"expected D-102 fail, got {fails}"
    )
    assert fails[0]["measured_mm"] == 680.0
    assert fails[0].get("width_source") == "IfcDoor.OverallWidth"

    clashes = detect_clashes(model)
    assert len(clashes) >= 1, "expected controlled demo clash"
    assert clashes[0]["severity"] == "high"
    assert clashes[0]["method"] == "synthetic_aabb_fallback", clashes[0]
    print("✓ controlled demo door + labelled synthetic clash checks pass")

    r = route_message("Why is D-102 a problem?", 750)
    assert "680" in r["reply"] and "750" in r["reply"], (
        "agent reply missing evidence"
    )
    print("✓ agent grounded explanation pass")

    _test_project_unit_conversion()

    print("All smoke tests passed")
    print(f"Doors: {doors}")
    print(f"Clashes: {clashes}")


if __name__ == "__main__":
    test()
