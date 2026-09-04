# Architecture — BIMGuard

## Data Flow

```
.ifc (STEP) ──► FastAPI /api/upload ──► ifc_engine (IfcOpenShell or fallback regex)
                                    │
                                    ├─► R1: door_width (OverallWidth + Qto) ──► HK FS 2011 Table B2
                                    └─► R2: clash (BVH tree → AABB) ──► penetration + severity
                                                      │
                                                      ▼
                                            Evidence JSON {doors, clashes, score}
                                                      │
                                   ┌──────────────────┼──────────────────┐
                                   │                  │                  │
                              /api/summary     /api/chat (tool-router)   3D Viewer
                                   │                  │                  │
                                   │         mock (deterministic)    Three.js boxes
                                   │         or OpenAI (evidence-injected)
                                   ▼                  ▼                  ▼
                              Score + Cards      Chat reply         Highlight
```

## Design Decisions

| Decision | Why | Alternative rejected |
|----------|-----|----------------------|
| Tool-router, not LLM-as-judge | Hallucination-free numeric checks; LLM only explains | “IFC text → GPT” (unreliable for 750mm) |
| 2 rules, high polish | Brief says 1–2; visual locate + explain > 20 shallow | 20 rules with no viz |
| BVH + AABB fallback | `clash_intersection_many` when available, else AABB (always works, CI-friendly) | Pure BVH (fails without kernel) |
| Fallback parser | Text regex for synthetic IFC; demo works without binary wheels (slow network) | Require IfcOpenShell strictly |
| Static fallback UI | CDN Tailwind+Three, served by FastAPI; no `npm` needed for evaluation | Vite-only (blocks reviewer if npm slow) |

## IFC Handling

- **With IfcOpenShell:** `ifcopenshell.open(path)`, `by_type`, `util.element.get_psets`, `util.placement.get_local_placement`, `geom.tree()` for clash
- **Without:** `MockElement` + regex `IFCDOOR('guid',...,'D-102',...)` + `// PLACEMENT` comments; AABB heuristic by type
- **Sample generation:** `generate_sample_ifc_fallback.py` writes STEP text directly; `generate_sample_ifc.py` uses `ifcopenshell.api` when available

## Frontend

- **React + R3F/Drei** (`frontend/src`): `App.jsx` orchestrates upload→summary→elements→viewer; `Viewer.jsx` maps `placement {x,y,z}` to `BoxGeometry` with type colors; `IssuesPanel` & `ChatPanel` call `/api/chat` and `/api/summary`
- **Static** (`frontend/static.html`): same API, importmap Three, no build; served at `/` by FastAPI

## Agent

- **Tools:** 5 JSON schemas in `prompts/tools.json`; `tools.py:call_tool` is single source
- **Mock:** keyword routing (`door` → R1, `clash` → R2, else summary) + templated evidence reply — deterministic, testable
- **LLM:** inject `Evidence JSON` into system prompt, `temperature=0.2`, `max_tokens=800`; fallback to mock on failure

## Scoring

```
if total==0: 100 - 15*clashes
else: base=100*passed/total; score = int(base*0.7)-10*clashes if clashes else int(base)
clamped 0..100
```

## Future Enhancements (out-of-scope for 7-day)

- IFC→GLB via `IfcConvert` → Three `GLTFLoader` (instead of boxes)
- IDS/bSDD rule packs
- Multi-storey + `IfcSpace` travel distance (graph + pathfinding)
