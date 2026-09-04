# BIMGuard — 3-Minute Walkthrough Script (for screen recording)

Total target: 2:30, leave 30s buffer.

---

**0:00–0:15 — Intro (screen: README + header)**
- "Hi, I'm Yule Cai — this is BIMGuard, my HKU AI+BIM micro-prototype."
- "One upload → deterministic checks → AI explanation + 3D locate. Two rules, as requested."
- Show repo structure briefly, then open http://localhost:8000/

**0:15–0:45 — Upload (screen: http://localhost:8000/)**
- Click "Upload .ifc" → select `sample-ifc/BIMGuard_Demo.ifc`
- Narrate: "This is a synthetic IFC: 4 walls, 3 doors, 1 beam × 1 pipe. D-102 is 680mm (fail), others pass. Beam and pipe clash."
- Show counts appear: `Loaded: 9 elements`, Compliance Score pops.

**0:45–1:15 — Rule Cards + Issues (screen: right panel)**
- Point to `Compliance Score 36/100`, `Exit Door Width 2 passed · 1 failed`, `Geometry Clash 1 clashes`
- Scroll `Critical Issues`: D-102 680 < 750 (Δ -70), B-017 × P-042 100mm high.
- Click `[Locate]` on D-102 → 3D viewer highlights orange door, camera orbits.
- Click `[Locate]` on clash → highlights beam/pipe.

**1:15–1:45 — Explain via Agent (screen: Issues → Explain)**
- Click `[Explain]` on D-102 → show chat reply: "fails HK FS Code 2011 Table B2 ... increase by 70mm"
- Emphasize architecture: "LLM didn't judge width — IfcOpenShell did. LLM only explains with evidence."
- Show `prompts/system.md` for 2 seconds: tool-router, never hallucinate.

**1:45–2:15 — Chat (screen: Ask BIMGuard)**
- Type: `Show me all serious violations`
  → agent replies with summary table + both issues (tool: get_summary + check_exit_door_width + detect_clashes)
- Type: `Why is D-102 a problem?` → reply cites GUID, measured vs required, rule.
- Type: `any clashes?` → reply lists B-017 × P-042 penetration + fix suggestion.

**2:15–2:30 — Engineering Taste + Close (screen: API docs)**
- Quick show `http://localhost:8000/docs` → `/api/summary`, `/api/chat`, `/api/tools`
- Mention: "Clash via BVH `clash_intersection_many` with AABB fallback; door via OverallWidth + Qto; IFC→GLB ready for Three.js; fallback parser works without ifcopenshell."
- "Code + prompts + sample IFC are in the repo. Thanks!"

---

**Recording tips:**
- Use 1080p, no mic echo, add captions if needed.
- Keep mouse slow, zoom 125% for readability.
- Export <50MB, upload to YouTube unlisted or Drive.
