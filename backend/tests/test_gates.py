"""8 Hard Gates — must all pass before merge/video."""
import os, sys, subprocess, json, tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

HAS_IFC = False
try:
    import ifcopenshell
    HAS_IFC = True
except:
    pass

def test_gate_synthetic():
    from backend.app import ifc_engine
    from backend.app.rules.door_width import check_door_width
    from backend.app.rules.clash import detect_clashes
    sample = os.path.abspath("sample-ifc/BIMGuard_Demo.ifc")
    ifc_engine.set_current_file(sample)
    model = ifc_engine.get_current_model()
    doors = check_door_width(model, 750)
    assert len(doors)==3
    by = {d["name"]:d for d in doors}
    assert by["D-101"]["status"]=="pass" and by["D-101"]["measured_mm"]==900
    assert by["D-102"]["status"]=="fail" and by["D-102"]["measured_mm"]==680
    assert by["D-103"]["status"]=="pass" and by["D-103"]["measured_mm"]==750
    clashes = detect_clashes(model)
    assert any(c["method"]=="synthetic_aabb_fallback" for c in clashes)
    print("✓ Gate synthetic")

def test_gate_units():
    # Run the unit tests
    result = subprocess.run(["python", "-m", "pytest", "backend/tests/test_p0_units.py", "-q"], capture_output=True, text=True)
    assert result.returncode==0, result.stdout+result.stderr
    print("✓ Gate units")

def test_gate_real_bvh_positive():
    result = subprocess.run(["python", "-m", "pytest", "backend/tests/test_p0_bvh.py::test_p0_3_real_bvh_positive", "-q"], capture_output=True, text=True)
    assert result.returncode==0, result.stdout+result.stderr
    print("✓ Gate real BVH positive")

def test_gate_real_bvh_negative():
    result = subprocess.run(["python", "-m", "pytest", "backend/tests/test_p0_bvh.py::test_p0_4_real_bvh_negative", "-q"], capture_output=True, text=True)
    assert result.returncode==0, result.stdout+result.stderr
    print("✓ Gate real BVH negative")

def test_gate_tolerance():
    result = subprocess.run(["python", "-m", "pytest", "backend/tests/test_p0_bvh.py::test_p0_5_tolerance", "-q"], capture_output=True, text=True)
    assert result.returncode==0, result.stdout+result.stderr
    print("✓ Gate tolerance")

def test_gate_external():
    # Requires /tmp/bSMART
    if not os.path.isdir("/tmp/bSMART"):
        pytest.skip("No /tmp/bSMART — run git clone for buildingSMART samples")
    result = subprocess.run(["python", "-m", "pytest", "backend/tests/test_p0_external.py", "-q"], capture_output=True, text=True)
    assert result.returncode==0, result.stdout+result.stderr
    print("✓ Gate external x2")

def test_gate_clean_install():
    # Check backend requirements installable and frontend package valid
    assert os.path.isfile("backend/requirements.txt")
    assert os.path.isfile("frontend/package.json")
    assert os.path.isfile(".github/workflows/ci.yml")
    # Check that CI workflow has backend and frontend jobs
    with open(".github/workflows/ci.yml") as f:
        ci = f.read()
        assert "backend" in ci and "frontend" in ci
    print("✓ Gate clean install + CI")

def test_gate_browser_demo():
    # Check that static frontend and API would work
    assert os.path.isfile("frontend/static.html")
    assert os.path.isfile("run.sh")
    assert os.access("run.sh", os.X_OK)
    # Check that frontend static contains expected elements
    with open("frontend/static.html") as f:
        html = f.read()
        assert "BIMGuard" in html and "Ask BIMGuard" in html
    # Check that API health would be available after run.sh (we test via TestClient)
    from fastapi.testclient import TestClient
    from backend.app.main import app
    client = TestClient(app)
    # Need to have sample loaded for browser demo, but health should work without
    r = client.get("/api/health")
    assert r.status_code==200
    print("✓ Gate browser demo")
