"""P0-6 External buildingSMART IFC smoke — 2 files, no synthetic fallback."""
import os, sys, subprocess

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

HAS_IFC = False
try:
    import ifcopenshell
    HAS_IFC = True
except:
    pass

pytestmark = pytest.mark.skipif(not HAS_IFC, reason="IfcOpenShell required")

# Try to find buildingSMART samples at /tmp/bSMART or via env var
CANDIDATES = [
    "/tmp/bSMART/IFC 4.0.2.1 (IFC 4)/PCERT-Sample-Scene/Building-Architecture.ifc",
    "/tmp/bSMART/IFC 4.3.2.0 (IFC4X3_ADD2)/PCERT-Sample-Scene/Building-Architecture.ifc",
    "sample-ifc/external-ifc4.ifc",
    "sample-ifc/external-ifc43.ifc",
]

def _find_external_pair():
    found = [p for p in CANDIDATES if os.path.isfile(p)]
    return found

def test_p0_6_external_pair():
    found = _find_external_pair()
    if len(found) < 2:
        pytest.skip(f"Need 2 external IFCs, found {len(found)}: {found}. Run: git clone --depth 1 https://github.com/buildingSMART/Sample-Test-Files.git /tmp/bSMART")
    for path in found[:2]:
        # Run the smoke script via subprocess to get JSON
        result = subprocess.run(
            ["python", "backend/test_external_ifc.py", path],
            capture_output=True, text=True, env={**os.environ, "PYTHONPATH": "backend"}
        )
        assert result.returncode == 0, f"smoke failed for {path}: {result.stdout} {result.stderr}"
        assert "✓ external IFC smoke test completed without synthetic" in result.stdout
        assert "synthetic_aabb_fallback" not in result.stdout
        # Also verify via API that it doesn't use synthetic
        from backend.app import ifc_engine
        from backend.app.rules.clash import detect_clashes
        ifc_engine.set_current_file(os.path.abspath(path))
        model = ifc_engine.get_current_model()
        assert not (isinstance(model, dict) and model.get("_fallback")), f"{path} fell back to regex"
        clashes = detect_clashes(model)
        for c in clashes:
            assert c.get("method") != "synthetic_aabb_fallback", f"Real IFC must not use synthetic: {c}"
