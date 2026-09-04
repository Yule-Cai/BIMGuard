# Prompts Log — BIMGuard (for HKU submission, code + prompts)

> All prompts used to build the prototype are versioned here. Primary agent prompt is `system.md`, tool schemas in `tools.json`.

## 1) System prompt (final, v1) — `prompts/system.md`
See `system.md` (23 lines). Key constraints: tool-router, HK FS 2011 Table B2 grounding, evidence-required, no hallucination.

## 2) Tool schemas (final) — `prompts/tools.json`
5 tools: `check_exit_door_width`, `detect_clashes`, `get_summary`, `get_ifc_elements`, `get_element_properties` — OpenAI-compatible JSON.

## 3) Generation prompts (used to scaffold)

**Initial scaffold:**
```
Build a web-based micro-prototype to perform basic compliance checks on IFC.
Stack: Python FastAPI + IfcOpenShell + React Three.js + LLM tool router.
Rules: 1) exit door width vs HK FS 2011 Table B2 (750/850), 2) structural/MEP clash via BVH.
Architecture: deterministic engine → LLM explanation, not LLM-as-judge.
Create backend/app/main.py, ifc_engine, rules, agent, frontend/src, prompts, sample IFC with D-102 fail.
```

**IFC generator:**
```
Write a fallback IFC generator that doesn't require ifcopenshell — STEP text with // PLACEMENT comments,
3 doors (0.9, 0.68, 0.75) at (2,0,0) (8,0,0) (5,10,0), beam at (2,2,2) and pipe at (2.5,2,2.1) to clash.
```

**Frontend static fallback:**
```
Create frontend/static.html single-file CDN demo (Tailwind + Three importmap) that calls same /api/* endpoints,
so demo works without npm install. Served by FastAPI at /.
```

**Agent mock:**
```
Implement route_message mock that still calls tools and returns templated evidence when no OPENAI_API_KEY,
keyword routing: door→R1, clash→R2, else summary. Always include GUID + measured + required.
```

## 4) Verification prompts
```
Test via python3 backend/test_api.py and curl /api/summary?min_width=750 → expect D-102 fail 680<750 and B-017×P-042 clash 100mm high.
```

All prompts are deterministic and committed. No hidden system prompts.
