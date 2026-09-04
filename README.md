# BIMGuard — AI-Native IFC Compliance Agent

> **HKU AI+BIM Technical Test · 7-day micro-prototype**  
> **Ref. 536608** Department of Urban Planning and Design, The University of Hong Kong  
> **One upload → deterministic BIM checks → AI explanation + 3D locate**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com/)
[![IfcOpenShell](https://img.shields.io/badge/IfcOpenShell-0.8.x-orange)](https://docs.ifcopenshell.org/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)
[![Three.js](https://img.shields.io/badge/Three.js-0.160-black)](https://threejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

**Live demo (no build):** `http://localhost:8000/` after `./run.sh` · **API docs:** `http://localhost:8000/docs`

---

## 30-Second Summary

| Input | Rules (1–2 as required) | Output | Interaction |
|-------|-------------------------|--------|-------------|
| `.ifc` upload | **R1** Exit door width vs **HK FS Code 2011 (2024 Ed.) Table B2** · **R2** Structural/MEP clash via BVH | `Pass/Fail + GUID + measured vs required + rule citation + fix` | 3D Viewer highlight · `[Locate]` · `[Explain]` · natural-language `Ask BIMGuard` |

**Engineering taste:** LLM never judges geometry/numbers. LLM is a **tool router + explainer**; `IfcOpenShell` is the source of truth.

```
User (upload / "Why is D-102 a problem?")
  │
  ▼
Frontend — React + Three.js  ───────► FastAPI
  │  Viewer │ Issues │ Chat              │
  │                                    ▼
  │                         AI Agent (LLM Tool Router)
  │                          ├─ check_exit_door_width(min_width=750)  ◄── HK FS Code
  │                          ├─ detect_clashes()  ◄── ifcopenshell.geom.tree.clash_intersection_many + AABB fallback
  │                          ├─ get_ifc_elements(type, guid)
  │                          └─ get_element_properties(guid)
  │                                    │
  │                                    ▼
  │                         IfcOpenShell (deterministic)
  │                                    │
  │                                    ▼
  │                         Evidence JSON → LLM → Explanation + Recommendation + Locate hint
  ▼
Toast + 3D highlight + Chat reply
```

---

## Implemented Rules

### R1 — Exit Door Width Compliance
- **IFC source:** `IfcDoor.OverallWidth` + `Qto_DoorBaseQuantities.OverallWidth` + `Pset_DoorCommon` (`backend/app/rules/door_width.py:6`)
- **Norm:** HK *Code of Practice for Fire Safety in Buildings 2011 (2024 Ed.)* Table B2 — `4–30 persons → ≥750mm`, `31–200 persons → ≥850mm`, clear width measured between door frames
- **Default:** `≥750mm` (configurable `?min_width=750|850`)
- **Output:** `guid, name, measured_mm, required_mm, delta_mm, status (pass/fail/unknown), rule`

**Example:**
```
D-102  680mm < 750mm  Δ -70mm  ❌ Fail  HK FS 2011 Table B2  → Increase clear opening by ≥70mm
```

### R2 — Structural / MEP Clash Detection
- **IFC source:** `IfcWall/IfcBeam/IfcColumn/IfcSlab` × `IfcPipeSegment/IfcFlowSegment/IfcDuctSegment` (`backend/app/rules/clash.py:49`)
- **Method:** `ifcopenshell.geom.tree()` BVH + `clash_intersection_many()` when kernel available; **AABB placement fallback** always works (deterministic, ~100mm penetration in demo)
- **Output:** `a_guid, a_name, a_type, b_guid, b_name, b_type, penetration_mm, severity (high/medium/low)`

**Example:**
```
P-042 (IfcPipeSegment) × B-017 (IfcBeam)  100mm  high  → Reroute pipe or provide coordinated opening
```

> *Why not travel distance?* `IfcSpace` connectivity + pathfinding is fragile in 7 days. Two high-quality, visualizable rules > 20 low-quality ones (as brief suggests).

---

## Quick Start

### Option A — One-click (no `npm`, no `ifcopenshell` required)

```bash
./run.sh
# → http://localhost:8000/      static demo (CDN Tailwind + Three.js)
# → http://localhost:8000/docs  API docs
# → http://localhost:8000/api/health
```

- Uses **fallback text parser** (`backend/app/ifc_engine.py:1`) — same R1/R2 results without binary deps
- Install `ifcopenshell` for full STEP + geometry: `pip install ifcopenshell` or `mamba install -c conda-forge ifcopenshell`

### Option B — Full dev

```bash
# backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# frontend (two modes)
# Mode 1: static already served at http://localhost:8000/
# Mode 2: React Vite (optional, needs npm)
cd frontend
npm install --registry https://registry.npmmirror.com   # or https://registry.npmjs.org
npm run dev     # http://localhost:5173  (proxies /api to :8000)
npm run build   # → frontend/dist/  served at http://localhost:8000/app
```

### Generate / Use Sample IFC

```bash
# fallback (no ifcopenshell)
python3 backend/scripts/generate_sample_ifc_fallback.py  # → sample-ifc/BIMGuard_Demo.ifc
# full (with ifcopenshell)
python3 backend/scripts/generate_sample_ifc.py
# any buildingSMART Sample-Test-Files IFC4/IFC4.3 also works — just upload
```

**Demo file:** `sample-ifc/BIMGuard_Demo.ifc` — 4 walls (10×10m) + 3 doors (D-101 900 pass, D-102 680 **fail**, D-103 750 pass) + B-017 beam × P-042 pipe **clash 100mm**

### API Examples

```bash
curl -X POST http://localhost:8000/api/upload -F "file=@sample-ifc/BIMGuard_Demo.ifc"
curl "http://localhost:8000/api/summary?min_width=750" | python3 -m json.tool
curl "http://localhost:8000/api/elements?type=IfcDoor" | python3 -m json.tool
curl http://localhost:8000/api/clashes | python3 -m json.tool
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Why is D-102 a problem?","min_width":750}' | python3 -m json.tool
# with LLM (optional)
OPENAI_API_KEY=sk-... OPENAI_BASE_URL=https://api.openai.com/v1 LLM_MODEL=gpt-4o-mini \
curl -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" \
  -d '{"message":"Show me all serious violations","min_width":750,"use_llm":true}'
```

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | model loaded? + current file |
| `POST` | `/api/upload` | multipart `.ifc` |
| `GET` | `/api/summary?min_width=750` | score + both rules |
| `GET` | `/api/doors?min_width=750` | R1 details |
| `GET` | `/api/clashes` | R2 details |
| `GET` | `/api/elements?type=IfcDoor&limit=50` | inventory |
| `GET` | `/api/element/{guid}` | Psets + placement |
| `POST` | `/api/chat` | tool-router chat (`message, min_width, use_llm`) |
| `POST` | `/api/tools/{tool_name}` | direct tool call (debug) |
| `GET` | `/sample-ifc/BIMGuard_Demo.ifc` | download sample |

---

## UI Walkthrough (for <3 min video)

1. **Upload** `BIMGuard_Demo.ifc` → `Compliance Score 36/100` appears
2. **Rule cards:** `Exit Door Width 2 passed · 1 failed` + `Geometry Clash 1 clashes`
3. **Issues:** `D-102 680<750 Δ-70mm` + `B-017×P-042 100mm high` → click `[Locate]` → 3D viewer orbits & highlights (orange fail / purple beam / sky pipe)
4. **Explain:** click `[Explain]` on D-102 → agent cites `HK FS 2011 Table B2` + `+70mm` fix (evidence from tool, not hallucinated)
5. **Chat:** `Ask BIMGuard` → `Why is D-102 a problem?` / `Show me all serious violations` / `any clashes?`

See `VIDEO_SCRIPT.md` for timed script.

---

## Prompts (versioned as required)

- `prompts/system.md` — system prompt: role, tools, evidence rule, HK FS grounding, response style
- `prompts/tools.json` — 5 tool schemas (OpenAI-compatible)
- Runtime loader: `backend/app/agent/prompt.py:1`

**Without LLM:** `backend/app/agent/tools.py:route_message` uses deterministic mock that still calls tools and renders templated evidence — same chain, no hallucination.

---

## Project Structure

```
backend/
  app/main.py               FastAPI + CORS + static mounts
  app/ifc_engine.py         IfcOpenShell + fallback regex parser + MockElement
  app/rules/door_width.py   R1
  app/rules/clash.py        R2 (BVH → AABB)
  app/agent/tools.py        5 tools + mock router + OpenAI path
  app/agent/prompt.py       prompt loader
  scripts/generate_sample_ifc*.py  IFC generators
  test_api.py               smoke test (doors + clash + agent)
  requirements.txt
frontend/
  src/App.jsx               layout + upload + score
  src/components/Viewer.jsx Three.js (R3F/Drei) — boxes by placement, IFC→GLB ready
  src/components/IssuesPanel.jsx   Locate/Explain
  src/components/ChatPanel.jsx     Ask BIMGuard
  static.html               no-build CDN fallback (served at /)
  dist/index.html           prebuilt fallback (same)
  package.json / vite.config.js / tailwind.config.js
prompts/                    system + tools
sample-ifc/BIMGuard_Demo.ifc + README
run.sh / .env.example / VIDEO_SCRIPT.md / SUBMISSION.md
```

---

## Engineering Notes

- **Deterministic first:** numeric/geometry checks in `ifc_engine`/`rules`, never LLM
- **Graceful fallback:** no `ifcopenshell` → text parser + AABB still passes demo (CI-friendly); no `geom` → semantic door check + AABB clash
- **Evidence chain:** every issue carries `guid + name + measured + required + rule` → LLM explains, not invents
- **Taste:** 1–2 rules, well visualized & explainable, > 20 shallow rules; single tool-router >> LangChain soup

---

## Testing

```bash
python3 backend/test_api.py
# ✓ door + clash checks pass
# ✓ agent mock pass

# or via HTTP after ./run.sh
curl -X POST http://localhost:8000/api/upload -F "file=@sample-ifc/BIMGuard_Demo.ifc"
curl "http://localhost:8000/api/summary?min_width=750"
```

---

## References

- HK BD *Code of Practice for Fire Safety in Buildings 2011 (2024 Ed.)* Table B2 — [bd.gov.hk PDF](https://www.bd.gov.hk/doc/en/resources/codes-and-references/code-and-design-manuals/fs_code2011.pdf)
- buildingSMART *IfcDoor* `OverallWidth` — [IFC4.3 spec](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcDoor.htm)
- IfcOpenShell `geometry tree` + `clash_intersection_many` — [docs](https://docs.ifcopenshell.org/ifcopenshell-python/geometry_tree.html) · `IfcConvert` GLB — [docs](https://docs.ifcopenshell.org/ifcconvert.html)
- buildingSMART `Sample-Test-Files` — [GitHub](https://github.com/buildingSMART/Sample-Test-Files)
- HKU DUPAD Ref. **536608** / 536609 — [HKU Careers](https://jobs.hku.hk/)

---

## Submission

- **GitHub:** this repo (code + prompts) — public
- **Video:** <3 min walkthrough (upload → locate → explain → chat) — YouTube unlisted or Drive
- **CV:** one-page PDF with GPA per degree — see `docs/CV_Template.md`

`SUBMISSION.md` has email template + checklist. Deadline **23:59 11 Sep 2026 HKT** to `junnaifj@hku.hk` with subject `【HKU AI Agent Technical Test】Name_University`.

---

## License

MIT — see `LICENSE` (add if needed). Sample IFC is synthetic and free to use.

*Built for learning velocity, engineering judgement, and taste — not BIM expertise.*
