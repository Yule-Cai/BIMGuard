# BIMGuard — 3-Minute Walkthrough Script

Target: ~2:30, leaving ~30s buffer.

---

## 0:00–0:15 — Intro

Screen: README + app header.

- "Hi, I'm Yule Cai. This is BIMGuard, my HKU AI+BIM micro-prototype."
- "It performs two focused IFC checks: exit-door width and structural/MEP clash detection."
- "The design principle is deterministic checks first, AI explanation second."

## 0:15–0:45 — Upload controlled demo

Screen: `http://localhost:8000/`.

- Upload `sample-ifc/BIMGuard_Demo.ifc`.
- "This controlled sample contains three doors plus one beam/pipe demo conflict. D-102 is 680 mm, so it fails the selected 750 mm threshold."
- Point out that the left panel is a **schematic 3D element locator**, not full IFC shape rendering.

## 0:45–1:15 — Rule results + evidence

- Show `Exit Door Width 2 passed · 1 failed`.
- Show D-102: `680 mm < 750 mm`, deficit `70 mm`.
- Show the clash issue.
- Point to the clash method label: the tiny repository demo has no shape representation, so its conflict is explicitly labelled `synthetic_aabb_fallback`.
- Click `[Locate]` to highlight D-102, then the clash element.

Narration:

> "I deliberately label the synthetic fallback instead of pretending this demo file contains production geometry. For real IFC files with shape representations, BIMGuard uses IfcOpenShell's geometry iterator, builds a BVH tree, and calls `clash_intersection_many`."

## 1:15–1:45 — Explain with AI

- Click `[Explain]` on D-102.
- Show response containing measured value, selected threshold, rule, and proposed next action.
- Briefly show `prompts/system.md`.

Narration:

> "The language model never calculates the width or geometry. The backend runs deterministic checks first and supplies Evidence JSON. The model only explains that evidence."

## 1:45–2:10 — Natural-language interaction

Type one or two questions only:

```text
Why is D-102 a problem?
Show me all serious violations.
```

Point out that the reply preserves measured values / GUIDs from the rule outputs.

## 2:10–2:30 — Engineering decisions + close

Screen: README / source / API docs.

Mention three implementation decisions:

1. "IFC units are read from the project definition with `calculate_unit_scale()` instead of guessing from the magnitude."
2. "Real geometric clashes use the documented IfcOpenShell BVH path. The heuristic AABB path is restricted to the named synthetic sample only."
3. "The scope is intentionally two rules rather than many shallow checks."

Close:

> "The repository includes code, prompts, regression tests, an external-IFC smoke-test utility, and the demo data. Thank you."

---

## Recording tips

- Record at 1080p.
- Keep the browser zoom around 110–125% for readable evidence.
- Do not spend time scrolling through every file.
- Make the difference between **controlled synthetic demo** and **real IFC BVH geometry checking** explicit once; that is an engineering-strength point, not a weakness.
- Keep final video under 3 minutes.
