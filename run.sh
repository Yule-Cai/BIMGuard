#!/bin/bash
# BIMGuard one-click run (fallback no-build mode)
set -e
echo "=== BIMGuard ==="
echo "Backend: FastAPI + IfcOpenShell (fallback parser if not installed)"
echo "Frontend: static.html (no npm required) served by FastAPI"
echo ""
# ensure sample
if [ ! -f "sample-ifc/BIMGuard_Demo.ifc" ]; then
  echo "Generating sample IFC..."
  python3 backend/scripts/generate_sample_ifc_fallback.py --out sample-ifc/BIMGuard_Demo.ifc
fi
echo "Sample: sample-ifc/BIMGuard_Demo.ifc"
# install python deps (if not already)
pip3 install -q fastapi uvicorn python-multipart 2>&1 | tail -5 || true
# try ifcopenshell (optional, fallback works without)
pip3 show ifcopenshell >/dev/null 2>&1 || echo "Note: ifcopenshell not installed — using text fallback parser (still passes checks). Install with: pip install ifcopenshell or mamba install -c conda-forge ifcopenshell"

echo ""
echo "Starting backend at http://localhost:8000"
echo "  - Static demo: http://localhost:8000/  (no build)"
echo "  - API docs:    http://localhost:8000/docs"
echo "  - Health:      http://localhost:8000/api/health"
echo ""
echo "Try:"
echo "  curl -X POST http://localhost:8000/api/upload -F file=@sample-ifc/BIMGuard_Demo.ifc"
echo "  curl \"http://localhost:8000/api/summary?min_width=750\" | python3 -m json.tool"
echo ""
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
