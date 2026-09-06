import os
import shutil
import tempfile
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bimguard")

from . import ifc_engine
from .rules.door_width import check_door_width, summarize_door_results
from .rules.clash import detect_clashes
from .agent.tools import call_tool, route_message

app = FastAPI(title="BIMGuard API", version="1.0.0", description="AI-native IFC compliance checks")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    message: str
    min_width: float = 750
    use_llm: bool = False
    strict_llm: bool = False

@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": ifc_engine.get_current_model() is not None, "current_file": ifc_engine.get_current_path()}

@app.post("/api/upload")
async def upload_ifc(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".ifc"):
        raise HTTPException(400, "Only .ifc files accepted")
    # 20 MB limit
    content = await file.read()
    if len(content) > 20*1024*1024:
        raise HTTPException(400, "File too large (>20MB)")
    dest = os.path.join(UPLOAD_DIR, file.filename)
    with open(dest, "wb") as out:
        out.write(content)
    try:
        ifc_engine.set_current_file(dest)
        logger.info("Uploaded %s (%d bytes) -> %s", file.filename, len(content), dest)
        # Invalidate geometry cache on new upload
        global _geometry_cache, _geometry_cache_path
        _geometry_cache = {}
        _geometry_cache_path = None
    except Exception as e:
        logger.exception("Failed to parse %s", file.filename)
        raise HTTPException(400, str(e))
    model = ifc_engine.get_current_model()
    # quick stats (support fallback)
    counts = {}
    if isinstance(model, dict) and model.get("_fallback"):
        els = model.get("elements", [])
        for t in ["IfcDoor", "IfcWall", "IfcBeam", "IfcPipeSegment", "IfcFlowSegment"]:
            counts[t] = sum(1 for e in els if e.is_a()==t)
    else:
        for t in ["IfcDoor", "IfcWall", "IfcBeam", "IfcPipeSegment", "IfcFlowSegment"]:
            try:
                counts[t] = len(model.by_type(t))
            except:
                counts[t] = 0
    return {"filename": file.filename, "path": dest, "counts": counts, "message": "Uploaded and parsed"}

@app.get("/api/summary")
def summary(min_width: float = Query(750, description="Min door width mm")):
    model = ifc_engine.get_current_model()
    if model is None:
        raise HTTPException(400, "No IFC loaded. POST /api/upload first.")
    doors = check_door_width(model, min_width)
    stats = summarize_door_results(doors)
    clashes = detect_clashes(model)
    # score: None when no applicable elements (more honest than 100)
    total = stats["total"]
    passed = stats["passed"]
    if total == 0 and len(clashes) == 0:
        score = None
        score_status = "not_applicable"
    elif total == 0:
        score = max(0, 100 - len(clashes)*15)
        score_status = "no_doors"
    else:
        base = 100 * passed / total if total else 100
        score = int(base * 0.7) if clashes else int(base)
        score = max(0, score - len(clashes)*10)
        score = min(100, score)
        score_status = "ok"
    return {
        "min_width": min_width,
        "score": score,
        "score_status": score_status,
        "doors": {"results": doors, **stats},
        "clashes": {"results": clashes, "count": len(clashes)},
        "rule": "HK FS Code 2011 Table B2"
    }

@app.get("/api/doors")
def doors(min_width: float = 750):
    model = ifc_engine.get_current_model()
    if model is None:
        raise HTTPException(400, "No IFC loaded")
    return {"results": check_door_width(model, min_width)}

@app.get("/api/clashes")
def clashes():
    model = ifc_engine.get_current_model()
    if model is None:
        raise HTTPException(400, "No IFC loaded")
    res = detect_clashes(model)
    return {"results": res, "count": len(res)}

@app.get("/api/elements")
def elements(type: Optional[str] = None, limit: int = 50, guid: Optional[str] = None):
    model = ifc_engine.get_current_model()
    if model is None:
        raise HTTPException(400, "No IFC loaded")
    els = ifc_engine.list_elements(type, limit, guid)
    return {"elements": [ifc_engine.get_element_info(e) for e in els], "count": len(els)}

@app.get("/api/element/{guid}")
def element_props(guid: str):
    model = ifc_engine.get_current_model()
    if model is None:
        raise HTTPException(400, "No IFC loaded")
    if isinstance(model, dict) and model.get("_fallback"):
        els = [e for e in model.get("elements", []) if e.GlobalId==guid]
        info = ifc_engine.get_element_info(els[0]) if els else None
        return {"guid": guid, "psets": ifc_engine.get_psets(guid), "info": info}
    return {"guid": guid, "psets": ifc_engine.get_psets(guid), "info": ifc_engine.get_element_info(model.by_guid(guid)) if model.by_guid(guid) else None}

@app.post("/api/chat")
def chat(req: ChatRequest):
    model = ifc_engine.get_current_model()
    if model is None:
        raise HTTPException(400, "No IFC loaded. Upload first.")
    # Allow env-level strict as well inside route_message
    if req.strict_llm:
        # In strict mode, let LLM errors surface as 502, not silent mock
        try:
            result = route_message(req.message, req.min_width, req.use_llm, strict_llm=True)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM strict failure: {e}")
        return result
    # Normal mode (fallback allowed)
    try:
        result = route_message(req.message, req.min_width, req.use_llm, strict_llm=False)
    except RuntimeError as e:
        # Even normal mode may raise if strict_llm env is set and no key
        raise HTTPException(status_code=400, detail=str(e))
    return result

# Geometry API — real triangulated IFC geometry
_geometry_cache = {}
_geometry_cache_path = None

def _get_geometry_payload():
    global _geometry_cache, _geometry_cache_path
    model = ifc_engine.get_current_model()
    path = ifc_engine.get_current_path()
    if model is None or path is None:
        raise HTTPException(400, "No IFC loaded. POST /api/upload first.")
    # Use fallback check: if model is dict (regex), no real geometry
    if isinstance(model, dict) and model.get("_fallback"):
        return {"elements": [], "stats": {"elements": 0, "vertices": 0, "triangles": 0, "note": "synthetic demo has no shape, fallback"}}
    # Cache
    if _geometry_cache_path == path and _geometry_cache:
        return _geometry_cache
    # Try to extract real geometry
    try:
        import ifcopenshell.geom
        import ifcopenshell.util.shape
        import ifcopenshell.util.unit
    except Exception as e:
        raise HTTPException(500, f"IfcOpenShell geom not available: {e}")
    # Settings
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    # Limit threads
    import os as _os
    workers = max(1, min(4, _os.cpu_count() or 1))
    try:
        iterator = ifcopenshell.geom.iterator(settings, model, workers)
    except Exception as e:
        raise HTTPException(500, f"Failed to create geometry iterator: {e}")
    elements = []
    total_vertices = 0
    total_triangles = 0
    start = __import__("time").time()
    # For very large IFC, limit elements
    max_elements = 250
    max_triangles = 600000
    try:
        if not iterator.initialize():
            raise HTTPException(500, "Geometry iterator failed to initialize")
        count = 0
        while True:
            shape = iterator.get()
            try:
                el = shape.instance if hasattr(shape, "instance") else None
                # Fallback for older API
                if el is None:
                    try:
                        el = model.by_guid(shape.guid) if hasattr(shape, "guid") else None
                    except:
                        el = None
                if el is None:
                    if not iterator.next():
                        break
                    continue
                # Only renderable products
                if el.is_a() not in ("IfcWall", "IfcDoor", "IfcSlab", "IfcBeam", "IfcColumn", "IfcPipeSegment", "IfcFlowSegment", "IfcDuctSegment", "IfcWindow", "IfcDistributionElement", "IfcDistributionFlowElement"):
                    if not iterator.next():
                        break
                    continue
                # Get global vertices and faces — handle numpy arrays correctly
                try:
                    verts = ifcopenshell.util.shape.get_vertices(shape.geometry)
                    faces = ifcopenshell.util.shape.get_faces(shape.geometry)
                except Exception:
                    try:
                        verts = shape.geometry.verts
                        faces = shape.geometry.faces
                    except:
                        if not iterator.next():
                            break
                        continue
                # Normalize numpy arrays to lists
                try:
                    import numpy as np
                    if isinstance(verts, np.ndarray):
                        verts = verts.tolist()
                    if isinstance(faces, np.ndarray):
                        faces = faces.tolist()
                except:
                    pass
                # verts: list of [x,y,z] or flat list
                flat_verts = []
                verts_list = []
                try:
                    if isinstance(verts, (list, tuple)) and len(verts) > 0 and isinstance(verts[0], (list, tuple)):
                        verts_list = verts
                        flat_verts = [float(v) for tri in verts for v in tri]
                    else:
                        flat_verts = [float(v) for v in verts]
                        verts_list = [flat_verts[i:i+3] for i in range(0, len(flat_verts), 3)]
                except Exception as e:
                    logger.warning(f"verts parse failed: {e}")
                    if not iterator.next():
                        break
                    continue
                try:
                    if isinstance(faces, (list, tuple)) and len(faces) > 0 and isinstance(faces[0], (list, tuple)):
                        faces_list = faces
                        indices = [int(idx) for tri in faces for idx in tri]
                    else:
                        indices = [int(i) for i in faces]
                        faces_list = [indices[i:i+3] for i in range(0, len(indices), 3)]
                except Exception as e:
                    logger.warning(f"faces parse failed: {e}")
                    if not iterator.next():
                        break
                    continue
                # Limit payload
                if total_triangles + len(faces_list) > max_triangles:
                    logger.warning(f"Geometry limit reached: {total_triangles} triangles, skipping remaining")
                    break
                # Build element payload with flattened vertices and indices for Three.js
                # Use flattened for efficiency
                elements.append({
                    "guid": getattr(el, "GlobalId", ""),
                    "name": getattr(el, "Name", "") or getattr(el, "Tag", "") or el.is_a(),
                    "type": el.is_a(),
                    "vertices": flat_verts,
                    "indices": indices,
                    "vertex_count": len(verts_list),
                    "triangle_count": len(faces_list),
                })
                total_vertices += len(verts_list)
                total_triangles += len(faces_list)
                count += 1
                if count >= max_elements:
                    logger.warning(f"Element limit {max_elements} reached")
                    break
            except Exception as e:
                logger.warning(f"Failed to process shape: {e}")
            if not iterator.next():
                break
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Geometry extraction failed: {e}")
    elapsed = __import__("time").time() - start
    payload = {
        "elements": elements,
        "stats": {
            "elements": len(elements),
            "vertices": total_vertices,
            "triangles": total_triangles,
            "extraction_ms": int(elapsed * 1000),
            "payload_kb": int((sum(len(e["vertices"])*4 + len(e["indices"])*4 for e in elements))/1024),
        }
    }
    _geometry_cache = payload
    _geometry_cache_path = path
    return payload

@app.get("/api/geometry")
def geometry():
    return _get_geometry_payload()

# Tool-direct endpoints for Agent debugging
@app.post("/api/tools/{tool_name}")
def tool_call(tool_name: str, payload: dict = None):
    try:
        return call_tool(tool_name, payload or {})
    except Exception as e:
        raise HTTPException(400, str(e))

# Serve static demo if available
STATIC_HTML = os.path.join(os.path.dirname(__file__), "../../frontend/static.html")
REACT_DIST = os.path.join(os.path.dirname(__file__), "../../frontend/dist")

# Mount React dist if built
if os.path.exists(REACT_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(REACT_DIST, "assets")), name="react-assets")

@app.get("/", response_class=HTMLResponse)
def root():
    if os.path.exists(STATIC_HTML):
        return FileResponse(STATIC_HTML)
    return JSONResponse({"name": "BIMGuard API", "docs": "/docs", "health": "/api/health"})

@app.get("/app")
def react_app():
    # Serve Vite React app if built, else fallback to static
    index = os.path.join(REACT_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    if os.path.exists(STATIC_HTML):
        return FileResponse(STATIC_HTML)
    return JSONResponse({"error": "No frontend built. Use / for static demo or run npm run build"})

# mount sample-ifc for direct download
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "../../sample-ifc")
if os.path.exists(SAMPLE_DIR):
    app.mount("/sample-ifc", StaticFiles(directory=SAMPLE_DIR), name="sample-ifc")
