"""Smoke-test BIMGuard against an external IFC file.

Usage:
    PYTHONPATH=backend python backend/test_external_ifc.py /path/to/model.ifc

The goal is not to assume a particular violation. It verifies that a real IFC is
parsed by IfcOpenShell (not the regex demo parser), reports project unit scaling,
runs both implemented checks, and guarantees that arbitrary external files never
receive the synthetic AABB clash fallback.
"""
import json
import os
import sys

from app import ifc_engine
from app.rules.door_width import check_door_width
from app.rules.clash import detect_clashes


def main(path):
    if not os.path.isfile(path):
        raise SystemExit(f"IFC not found: {path}")
    if not ifc_engine.HAS_IFC:
        raise SystemExit(
            "IfcOpenShell is required for external IFC validation. "
            "Run: pip install -r backend/requirements.txt"
        )

    ifc_engine.set_current_file(path)
    model = ifc_engine.get_current_model()
    if isinstance(model, dict) and model.get("_fallback"):
        raise SystemExit("External IFC unexpectedly fell back to the demo regex parser")

    import ifcopenshell.util.unit

    unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
    doors = check_door_width(model, 750)
    clashes = detect_clashes(model)

    synthetic = [c for c in clashes if c.get("method") == "synthetic_aabb_fallback"]
    assert not synthetic, "External IFC must never use synthetic AABB fallback"

    report = {
        "file": os.path.basename(path),
        "schema": getattr(model, "schema", "unknown"),
        "project_length_to_m_scale": unit_scale,
        "shape_representations": len(model.by_type("IfcShapeRepresentation")),
        "doors_checked": len(doors),
        "door_status": {
            "pass": sum(d["status"] == "pass" for d in doors),
            "fail": sum(d["status"] == "fail" for d in doors),
            "unknown": sum(d["status"] == "unknown" for d in doors),
        },
        "clashes_found": len(clashes),
        "clash_methods": sorted({c.get("method", "unknown") for c in clashes}),
    }
    print(json.dumps(report, indent=2))
    print("✓ external IFC smoke test completed without synthetic geometry claims")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: PYTHONPATH=backend python backend/test_external_ifc.py model.ifc"
        )
    main(sys.argv[1])
