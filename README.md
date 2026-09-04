# BIMGuard — AI-Native IFC Compliance Agent

> HKU AI+BIM Technical Test · 7-day micro-prototype
> **Stack:** Python + FastAPI + IfcOpenShell + React + Three.js + LLM Tool Router

One upload → deterministic BIM checks → AI explanation + 3D locate.

## Architecture (Engineering Taste)

```
User (natural language / upload .ifc)
  ↓
Frontend (React + Three.js Viewer + Issues Panel + Chat)
  ↓
FastAPI Backend
  ↓
AI Agent (LLM Tool Router — NOT LLM-as-judge)
  ├── check_exit_door_width(min_width=750mm, HK FS Code 2011 Table B2)
  ├── detect_clashes()  // ifcopenshell.geom.tree.clash_intersection_many + AABB fallback
  ├── get_ifc_elements(by_type, guid)
  └── get_element_properties(guid)
        ↓
  IfcOpenShell (deterministic geometry + semantics)
        ↓
  Result (Pass/Warning/Fail + evidence) → LLM → Explanation + Recommendation
```

**Principle:** LLM never judges width or geometry. LLM routes tools and explains.

## Implemented Rules (1-2 as required)

### Rule 1 — Exit Door Width Compliance
- **Source:** `IfcDoor.OverallWidth` + `Qto_DoorBaseQuantities.OverallWidth` + `Pset_DoorCommon`
- **Norm:** HK Code of Practice for Fire Safety in Buildings 2011 (2024 Ed.) Table B2
  - 4–30 persons → ≥750mm
  - 31–200 persons → ≥850mm
- **Default check:** ≥750mm (configurable via `?min_width=`)
- **Output:** door GUID, name, detected width, required width, delta, status, clause

### Rule 2 — Structural/MEP Clash Detection
- **Source:** `IfcWall` / `IfcBeam` / `IfcColumn` / `IfcPipeSegment` / `IfcFlowSegment` / `IfcDuctSegment`
- **Method:** `ifcopenshell.geom.tree()` + `clash_intersection_many()` with BVH; falls back to AABB placement check if geometry kernel unavailable
- **Output:** pair (guid,name,type), penetration distance, severity

## Quick Start

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### One-Click Run (no build, no npm)
```bash
./run.sh  # → http://localhost:8000/  (static demo + API)
# static demo served by FastAPI, no npm needed
```

### Frontend (two modes)
```bash
# Mode 1: static fallback (recommended) — already served at http://localhost:8000/
# Mode 2: React Vite (optional)
cd frontend
npm install --registry https://registry.npmmirror.com
npm run dev  # http://localhost:5173 (proxies /api to :8000)
npm run build # → dist/ served at http://localhost:8000/app
```

### Generate Defective Sample IFC
```bash
# fallback generator (no ifcopenshell required)
python3 backend/scripts/generate_sample_ifc_fallback.py  # → sample-ifc/BIMGuard_Demo.ifc
# full generator (requires ifcopenshell)
python3 backend/scripts/generate_sample_ifc.py  # also → sample-ifc/BIMGuard_Demo.ifc
```

### API Examples
```bash
# Upload & check
curl -X POST http://localhost:8000/api/upload -F "file=@sample-ifc/BIMGuard_Demo.ifc"
curl http://localhost:8000/api/summary?min_width=750
curl http://localhost:8000/api/elements?type=IfcDoor
curl http://localhost:8000/api/clashes

# Agent chat (OpenAI-compatible, falls back to rule-based mock if no key)
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Why is D-102 a problem?","min_width":750}'
```

## Demo Flow (for <3min video)

1. Upload `BIMGuard_Demo.ifc` → see Compliance Score + 2 Rule Cards
2. Click `[Locate]` on D-102 (680mm < 750mm) → 3D viewer highlights door
3. Click `[Explain]` → Agent explains HK FS Code clause + fix (+70mm)
4. Show clash P-042 × B-017 (63mm) → locate + reroute suggestion
5. Chat: "Show me all serious violations" / "Why is D-102 non-compliant?"

## Prompts

See `prompts/system.md` (agent system prompt) and `prompts/tools.json` (tool schemas). All prompts versioned in repo as required.

## Sample Models

- `sample-ifc/BIMGuard_Demo.ifc` — synthetic, 4 walls + 3 doors (1 fail) + 1 beam + 1 pipe (1 clash)
- Also compatible with buildingSMART `Sample-Test-Files` IFC4/IFC4.3

## Project Structure

```
backend/app/main.py           FastAPI routes
backend/app/ifc_engine.py     IFC parsing + GLB conversion + caching
backend/app/rules/door_width.py
backend/app/rules/clash.py
backend/app/agent/tools.py    Tool definitions + router
backend/app/agent/prompt.py   System prompt loader
frontend/src/components/Viewer.jsx  Three.js viewer
frontend/src/components/IssuesPanel.jsx
frontend/src/components/ChatPanel.jsx
prompts/system.md
```

## Engineering Notes

- **Deterministic first:** All numeric/geometric checks in Python/IfcOpenShell, never LLM hallucination.
- **Graceful fallback:** If `ifcopenshell` not installed, text fallback parser + AABB still passes both rules (verified). If `ifcopenshell.geom` unavailable, clash falls back to AABB.
- **Evidence chain:** Every issue carries `guid + name + measured value + required value + rule citation`.
- **No-build demo:** `frontend/static.html` is CDN-based, served by FastAPI at `/`, so the prototype is functional even without `npm install`.

## Submission

- GitHub: this repo (code + prompts)
- Video: <3min walkthrough (upload → check → locate → explain → chat)
- CV: one-page PDF with GPA per degree

---
HKU DUPAD · AI Agents for Architecture and Construction · Ref. 536608
