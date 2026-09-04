# BIMGuard — AI-Native IFC Compliance Assistant

> **HKU AI+BIM Technical Test · 7-day micro-prototype**  
> Department of Urban Planning and Design, The University of Hong Kong · Ref. **536608**  
> **Upload IFC → deterministic checks → evidence-grounded explanation + schematic locate**

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)](https://fastapi.tiangolo.com/)
[![IfcOpenShell](https://img.shields.io/badge/IfcOpenShell-0.8.5-orange)](https://docs.ifcopenshell.org/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)
[![Three.js](https://img.shields.io/badge/Three.js-0.160-black)](https://threejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 30-second summary

BIMGuard intentionally implements only **two focused checks**:

| Rule | Deterministic source of truth | Output |
|---|---|---|
| **R1 — Exit door width** | `IfcDoor.OverallWidth` / door quantities + IFC project-unit conversion | pass / fail / unknown, measured width, threshold, delta, rule |
| **R2 — Structural ↔ MEP clash** | IfcOpenShell geometry iterator → BVH tree → `clash_intersection_many()` | element pair, GUIDs, clash type, penetration, severity |

The language model **does not calculate dimensions or geometry**. It receives evidence already produced by deterministic tools and turns that evidence into concise engineering explanations and recommendations.

```text
IFC upload
   │
   ▼
FastAPI + IfcOpenShell
   ├── check_exit_door_width()
   │      └── project units → SI → mm
   ├── detect_clashes()
   │      └── geometry iterator → BVH → clash_intersection_many()
   └── element/property tools
              │
              ▼
        Evidence JSON
              │
              ▼
      Grounded LLM explanation
              │
              ▼
 Issues panel · chat · schematic element locator
```

---

## Implemented rules

### R1 — Exit door width

**Scope:** the prototype implements the **minimum individual exit-door-width component** of HK *Code of Practice for Fire Safety in Buildings 2011 (2024 Ed.)*, Table B2. It does **not** claim to implement every Table B2 requirement.

- Default threshold: **750 mm** (`4–30` persons)
- Optional threshold: **850 mm** (`31–200` persons)
- IFC sources: `IfcDoor.OverallWidth`, then `Qto_DoorBaseQuantities`, then a relevant width property when available
- Units: converted with `ifcopenshell.util.unit.calculate_unit_scale(model)` instead of guessing from the numeric magnitude
- Missing width or unresolved units → `unknown`, never silently treated as `pass`

Example:

```text
D-102
Measured: 680 mm
Required: ≥750 mm
Delta: -70 mm
Status: FAIL
```

### R2 — Structural / MEP clash detection

For IFC files with geometric representations, BIMGuard follows IfcOpenShell's documented geometry-tree flow:

```python
tree = ifcopenshell.geom.tree()
iterator = ifcopenshell.geom.iterator(settings, model, workers)
# iterator.get() triangulation → BVH tree
tree.add_element(iterator.get())
clashes = tree.clash_intersection_many(group_a, group_b, tolerance=0.001, check_all=True)
```

Current groups:

- Structural: `IfcWall`, `IfcBeam`, `IfcColumn`, `IfcSlab`
- MEP: `IfcPipeSegment`, `IfcFlowSegment`, `IfcDuctSegment`, `IfcDistributionElement`, `IfcPipeFitting`

Each real-geometry result is labelled:

```json
{
  "method": "ifcopenshell_bvh",
  "penetration_mm": 63.0,
  "clash_type": "protrusion"
}
```

### Why the demo file has a labelled fallback

`sample-ifc/BIMGuard_Demo.ifc` is deliberately tiny and contains semantic entities + placements but **no actual shape representations**. It therefore cannot populate a BVH tree.

To keep the zero-dependency controlled demo usable, only this BIMGuard-owned sample may use a rough AABB fallback. Those results are explicitly labelled:

```json
{"method": "synthetic_aabb_fallback"}
```

**Arbitrary real IFC files never use guessed AABB dimensions.** If usable IFC geometry is unavailable, BIMGuard fails conservatively instead of fabricating a clash.

---

## Human-AI interaction

The UI contains:

- compliance score + two rule cards
- issue list with `[Locate]` and `[Explain]`
- natural-language `Ask BIMGuard`
- **3D Element Locator** — a schematic placement-aware Three.js view used to locate elements and highlight issues

The locator intentionally renders simple boxes from IFC placements. It is **not presented as full IFC shape rendering**.

Example questions:

```text
Why is D-102 a problem?
Show me all serious violations.
Are there any structural / MEP clashes?
```

The LLM path is an **evidence-grounded explainer**: the backend executes deterministic checks first, injects their JSON evidence, and instructs the model not to invent measurements. The tool schemas remain versioned in `prompts/tools.json` as the interface contract.

---

## Quick start

### A. Lightweight controlled demo

```bash
./run.sh
# http://localhost:8000/
# http://localhost:8000/docs
```

This launcher installs only lightweight web dependencies. If IfcOpenShell is absent, the repository's controlled synthetic sample can still demonstrate both rules through its clearly labelled fallback path.

**Do not use lightweight mode to claim real IFC geometry checking.**

### B. Full IFC geometry mode

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

`backend/requirements.txt` pins **IfcOpenShell 0.8.5** so real IFC project units and BVH geometry checks are available.

Optional React development frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## Demo data

Controlled sample:

```text
sample-ifc/BIMGuard_Demo.ifc
├── D-101  900 mm  pass
├── D-102  680 mm  fail
├── D-103  750 mm  pass
└── B-017 × P-042  labelled synthetic demo clash
```

For external validation, use a real IFC from the official buildingSMART `Sample-Test-Files` repository or another project IFC with geometric representations.

```bash
PYTHONPATH=backend python backend/test_external_ifc.py /path/to/model.ifc
```

The smoke-test utility verifies that:

- the external file is parsed by IfcOpenShell rather than the regex demo parser
- project length-unit scale is resolved
- both checks execute
- an arbitrary external file never receives `synthetic_aabb_fallback`

buildingSMART's current sample repository contains IFC 4 and IFC 4.3 PCERT sample scenes intended for implementation testing.

---

## API

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@sample-ifc/BIMGuard_Demo.ifc"

curl "http://localhost:8000/api/summary?min_width=750" | python3 -m json.tool
curl "http://localhost:8000/api/doors?min_width=750" | python3 -m json.tool
curl "http://localhost:8000/api/clashes" | python3 -m json.tool

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Why is D-102 a problem?","min_width":750}'
```

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | model state |
| `POST` | `/api/upload` | upload `.ifc` |
| `GET` | `/api/summary` | combined prototype summary |
| `GET` | `/api/doors` | R1 results |
| `GET` | `/api/clashes` | R2 results |
| `GET` | `/api/elements` | element inventory |
| `GET` | `/api/element/{guid}` | properties / quantities |
| `POST` | `/api/chat` | grounded explanation |
| `POST` | `/api/tools/{tool_name}` | direct deterministic tool call |

---

## Testing

Controlled regression tests:

```bash
PYTHONPATH=backend python backend/test_api.py
```

They verify:

- `D-102` is read as `680 mm` and fails `750 mm`
- controlled sample clash output is explicitly `synthetic_aabb_fallback`
- the evidence-based explanation includes measured + required values
- a temporary **millimetre-based IFC** converts `680 project-mm → 680 mm` through the IFC project-unit definition

External IFC smoke test:

```bash
PYTHONPATH=backend python backend/test_external_ifc.py real_model.ifc
```

---

## Repository structure

```text
backend/
  app/
    main.py
    ifc_engine.py
    rules/
      door_width.py      # IFC project-unit-aware semantic check
      clash.py           # real BVH clash + controlled-demo-only fallback
    agent/
      tools.py           # deterministic evidence tools + LLM path
      prompt.py
  test_api.py
  test_external_ifc.py
  requirements.txt

frontend/
  src/
    App.jsx
    components/
      Viewer.jsx         # schematic 3D element locator
      IssuesPanel.jsx
      ChatPanel.jsx
  static.html            # no-build demonstration UI

prompts/
  system.md              # grounded explanation contract
  tools.json             # versioned tool schemas

sample-ifc/
  BIMGuard_Demo.ifc

VIDEO_SCRIPT.md
SUBMISSION.md
Dockerfile / docker-compose.yml / run.sh
```

---

## Design decisions

1. **Deterministic first** — LLMs do not determine compliance measurements or geometry.
2. **No silent unit guessing** — IFC project units are explicitly resolved.
3. **No fabricated real-IFC clashes** — heuristic dimensions are restricted to the named synthetic demo.
4. **Unknown stays unknown** — missing data is not converted into a false pass.
5. **Narrow scope** — two well-explained checks rather than many shallow rules.
6. **Visible evidence chain** — GUIDs, measured values, thresholds, methods, and rule references remain inspectable.

---

## Known prototype boundaries

- The current exit-door rule is only one component of Table B2 and is not a complete fire-safety code checker.
- Occupant load is selected by the user through the threshold control; BIMGuard does not infer occupancy automatically.
- The Three.js UI is a schematic locator, not a production IFC renderer.
- The synthetic repository sample has no shape representation; only that controlled file uses the labelled AABB fallback.
- Final architectural / statutory decisions require qualified professional review.

These limitations are intentional for a 7-day micro-prototype and keep the implementation auditable.

---

## References

- HK Buildings Department — *Code of Practice for Fire Safety in Buildings 2011 (2024 Edition)*, Table B2  
  https://www.bd.gov.hk/doc/en/resources/codes-and-references/code-and-design-manuals/fs_code2011.pdf
- buildingSMART IFC 4.3 — `IfcDoor` / `OverallWidth`  
  https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/lexical/IfcDoor.htm
- IfcOpenShell — Geometry tree / clash detection  
  https://docs.ifcopenshell.org/ifcopenshell-python/geometry_tree.html
- IfcOpenShell — IFC unit utilities / `calculate_unit_scale()`  
  https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/unit/index.html
- buildingSMART — Sample-Test-Files  
  https://github.com/buildingSMART/Sample-Test-Files

---

## Submission

- GitHub repository: code + prompts
- demonstration / walkthrough video: under 3 minutes
- one-page CV: GPA explicitly stated for each degree

See `VIDEO_SCRIPT.md` and `SUBMISSION.md`.

*Built to demonstrate learning velocity, engineering judgement, and transparent AI-assisted software design — not pre-existing BIM expertise.*
