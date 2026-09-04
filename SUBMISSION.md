# Submission Checklist — HKU AI Agent Technical Test

**Deadline:** 11:59 pm 11 Sep 2026 (HKT)  
**To:** junnaifj@hku.hk  
**Subject:** `【HKU AI Agent Technical Test】Yule Cai_Universiti Utara Malaysia`

## Email Template

```text
Subject: 【HKU AI Agent Technical Test】Yule Cai_Universiti Utara Malaysia

Dear Jia,

Thank you for the opportunity. Please find my submission for the HKU AI Agent Technical Test below.

GitHub: https://github.com/Yule-Cai/BIMGuard
Video: <insert accessible video link>  (<3 min walkthrough)
CV: attached one-page PDF with undergraduate GPA stated explicitly

Prototype: BIMGuard — AI-Native IFC Compliance Assistant
- Stack: Python + FastAPI + IfcOpenShell + React/Three.js + evidence-grounded LLM explanation
- Rule 1: exit-door width check using IFC project units + HK FS Code 2011 (2024 Ed.) Table B2 threshold
- Rule 2: structural/MEP intersection checking using IfcOpenShell BVH geometry for real IFC models
- UI: issue evidence, schematic element locator, and natural-language explanations

The repository also includes a controlled demo IFC, regression tests, and an external-IFC smoke-test utility.

Thank you again for your time and consideration.

Best regards,
Yule Cai
Universiti Utara Malaysia
```

## Deliverables

1. **GitHub repository**
   - [x] `backend/` — FastAPI + deterministic IFC rules
   - [x] `frontend/` — React/Three.js + no-build UI
   - [x] `prompts/system.md` + `prompts/tools.json`
   - [x] `sample-ifc/BIMGuard_Demo.ifc`
   - [x] `README.md` — architecture, limitations, quick start
   - [x] `backend/test_api.py`
   - [x] `backend/test_external_ifc.py`
   - [x] `.github/workflows/ci.yml`

2. **Video** (<3 min)
   - [ ] Record walkthrough following `VIDEO_SCRIPT.md`
   - [ ] Upload to YouTube unlisted / Drive / another publicly accessible link
   - [ ] Verify the link works in a signed-out/private window

3. **CV** (one-page PDF)
   - [ ] GPA stated explicitly for undergraduate degree
   - [ ] Postgraduate GPA included only if applicable
   - [ ] One page only
   - [ ] Attach PDF to submission email

## Pre-send checks

- [ ] Full mode: `pip install -r backend/requirements.txt`
- [ ] `PYTHONPATH=backend python backend/test_api.py` passes
- [ ] `./run.sh` launches the lightweight demo UI
- [ ] Upload `sample-ifc/BIMGuard_Demo.ifc` and verify door result + labelled demo clash
- [ ] Run `backend/test_external_ifc.py` on at least one real external IFC with IfcOpenShell installed
- [ ] Confirm README does not call the schematic locator a production IFC geometry viewer
- [ ] Confirm real IFC clash results use `method=ifcopenshell_bvh`
- [ ] GitHub repository is public
- [ ] Video link works without requesting access
- [ ] CV attached and GPA visible
