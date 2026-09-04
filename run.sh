#!/bin/bash
# BIMGuard one-click lightweight demo mode
set -e
echo "=== BIMGuard ==="
echo "Backend: FastAPI; IfcOpenShell used when installed"
echo "Frontend: static.html (no npm required) served by FastAPI"
echo ""
# ensure sample
if [ ! -f "sample-ifc/BIMGuard_Demo.ifc" ]; then
  echo "Generating sample IFC..."
  python3 backend/scripts/generate_sample_ifc_fallback.py --out sample-ifc/BIMGuard_Demo.ifc
fi
echo "Sample: sample-ifc/BIMGuard_Demo.ifc"

# Lightweight launcher installs only the web API dependencies. For real IFC
# geometry/BVH checks use the full requirements.txt (which includes IfcOpenShell).
pip3 install -q fastapi uvicorn python-multipart 2>&1 | tail -5 || true
if ! pip3 show ifcopenshell >/dev/null 2>&1; then
  echo "Note: IfcOpenShell is not installed. The controlled BIMGuard_Demo.ifc can still use its labelled synthetic fallback, but arbitrary real IFC clash detection is disabled."
  echo "For full geometry mode run: pip install -r backend/requirements.txt"
fi

echo ""
echo "Starting backend at http://localhost:8000"
echo "  - Static demo: http://localhost:8000/"
echo "  - API docs:    http://localhost:8000/docs"
echo "  - Health:      http://localhost:8000/api/health"
echo ""
echo "Try:"
echo "  curl -X POST http://localhost:8000/api/upload -F file=@sample-ifc/BIMGuard_Demo.ifc"
echo "  curl \"http://localhost:8000/api/summary?min_width=750\" | python3 -m json.tool"
echo ""
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
